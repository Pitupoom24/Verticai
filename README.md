# Verticai

**AI-powered vertical jump analysis platform.** Upload a video of your jump and receive instant biomechanical scoring, jump height measurement, and an AI-generated coaching report — all from a single upload.

---

## Overview

Verticai processes athlete jump videos through a multi-stage computer vision pipeline and surfaces the results in a clean, real-time analytics dashboard. The system detects jump phases, measures key joint angles during the loading phase, calculates jump height using object tracking, and sends the aggregated metrics to an LLM via Modal's serverless infrastructure to generate a personalized coaching report.

---

## Demo

| Landing Page | Analytics Dashboard |
|---|---|
| Cinematic intro sequence with three athlete clips → single-video transition → animated stats landing screen | Split-panel layout: video preview on the left, live score breakdown on the right |

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────────────────────┐
│   Next.js 16    │  HTTP   │          FastAPI (Python)             │
│   Frontend      │ ──────► │  /input-videos  POST                 │
│   (port 3000)   │         │  /output-videos GET                  │
└─────────────────┘         │  /output-videos/file/:name GET       │
                            └──────────┬───────────────────────────┘
                                       │ concurrent
                            ┌──────────┴───────────────────────────┐
                            │                                      │
                    ┌───────▼──────┐                  ┌───────────▼──────┐
                    │ MediaPipe    │                  │   YOLOv8n-pose   │
                    │ Pose Analysis│                  │  Jump Height     │
                    │ (angle calc, │                  │  (ankle tracking │
                    │  phase det.) │                  │   + kinematics)  │
                    └───────┬──────┘                  └───────────┬──────┘
                            │                                     │
                            └──────────────┬──────────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Modal (remote) │
                                  │  GPT-4.1-mini   │
                                  │  Coaching Report│
                                  └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │   PostgreSQL    │
                                  │  (via Docker)   │
                                  └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python, asyncio, ThreadPoolExecutor |
| Pose Analysis | MediaPipe Pose Landmarker (heavy model) |
| Jump Height | YOLOv8n-pose (Ultralytics), physics kinematics |
| LLM | GPT-4.1-mini via OpenAI API, deployed on Modal (serverless) |
| Database | PostgreSQL 16 (Docker) |
| Containerization | Docker Compose |

---

## Features

- **Cinematic landing page** — Three athlete clips play simultaneously, fade into a single hero video, flash-transition to an animated stats image with live counters.
- **Video upload & analysis** — Drag-and-drop or click-to-browse. Supports MP4, MOV, AVI, WebM, MKV.
- **Jump phase detection** — Automatically identifies approach → loading → takeoff phases using hip flexion trajectory.
- **Biomechanical scoring** — Three independently scored components:
  - *Hip Flexion* — scored against an ideal loading angle of 70°.
  - *Knee Flexion* — scored against the optimal range of 83°–90°.
  - *Arm Swing Velocity* — angular velocity of the shoulder during loading-to-takeoff, benchmarked at ≥ 500°/s.
- **Jump height** — Measured via ankle keypoint displacement + ballistic kinematics (h = g·t²/8).
- **Overall score** — Composite weighted score: Jump Height 50% · Hip 20% · Arm Swing 20% · Knee 10%.
- **AI coaching report** — GPT-4.1-mini generates a concise, motivational report with strengths, improvement priorities, and drill recommendations.
- **Annotated video output** — MediaPipe skeleton overlay rendered frame-by-frame with live phase and angle annotations.
- **Analytics dashboard** — Split-panel UI with expandable component detail cards, ideal value comparisons, and research paper links.

---

## Project Structure

```
Verticai/
├── docker-compose.yml          # PostgreSQL service
├── backend/
│   ├── main.py                 # FastAPI app + Modal LLM function
│   ├── yolov8n-pose.pt         # YOLOv8 pose weights
│   ├── helper/
│   │   ├── analyze_scores.py   # MediaPipe pipeline, phase detection, scoring
│   │   ├── angle_calculation.py# Vector-based joint angle calculation
│   │   ├── pose_extraction.py  # Landmark extraction & angle assembly
│   │   ├── find_jump_height.py # YOLOv8 ankle tracking + kinematics
│   │   └── pose_landmarker_heavy.task  # MediaPipe model file
│   ├── input_videos/           # Uploaded raw videos (auto-created)
│   └── output_videos/          # Annotated output videos (auto-created)
└── frontend/
    ├── app/
    │   ├── page.tsx            # Landing / intro sequence
    │   ├── layout.tsx          # Root layout
    │   └── analytics/
    │       └── page.tsx        # Analytics dashboard page
    └── components/
        └── analytics/
            ├── AnalyticsPanel.tsx  # Score display, subtabs, feedback
            ├── VideoUploader.tsx   # Drag-and-drop video input
            └── ScoreBar.tsx        # Reusable animated score bar
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- A [Modal](https://modal.com) account with a secret named `openai-secret` containing `OPENAI_API_KEY`

---

### 1. Database

```bash
docker compose up -d
```

This starts a PostgreSQL 16 instance on port `5432`. Tables are created automatically on first backend startup.

---

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary python-dotenv \
            mediapipe opencv-python ultralytics modal openai
```

Create a `.env` file in `backend/`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=verticai
DB_USER=verticai_user
DB_PASSWORD=verticai_pass
```

Authenticate with Modal (one-time):

```bash
modal setup
```

Make sure your Modal account has a secret named `openai-secret` with `OPENAI_API_KEY` set. You can create it at [modal.com/secrets](https://modal.com/secrets) or via:

```bash
modal secret create openai-secret OPENAI_API_KEY=sk-...
```

Start the backend:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

---

## API Reference

### `POST /input-videos`

Upload a video for analysis.

**Request:** `multipart/form-data` with a `file` field.

**Response:**
```json
{
  "message": "Video uploaded and analyzed successfully.",
  "input_video": { "id": "...", "original_filename": "...", "uploaded_at": "..." },
  "output_video": {
    "score": 72.4,
    "jump_height": 0.48,
    "hip_normalized_score": 85.0,
    "smallest_loading_min_hip_flexion": 72.3,
    "knee_normalized_score": 91.0,
    "smallest_loading_min_knee_flexion": 86.5,
    "angular_velocity_score": 78.0,
    "angular_velocity": 390.0,
    "llm_report": "Great explosiveness off the floor...",
    "annotated_video_url": "http://127.0.0.1:8000/output-videos/file/annotated_abc123.mp4"
  }
}
```

### `GET /output-videos`

Returns all previously analyzed jump records.

### `GET /output-videos/file/{filename}`

Streams the annotated output video.

### `GET /input-videos`

Returns all uploaded video records ordered by upload time.

---

## Scoring Details

| Metric | Ideal | Method |
|---|---|---|
| Hip Flexion Angle | 70° | `max(0, 100 − |measured − 70|)` |
| Knee Flexion Angle | 83°–90° | `max(0, 100 − distance_from_range)` |
| Arm Swing Velocity | ≥ 500°/s | `min(100, velocity / 500 × 100)` |
| Jump Height | Higher is better | Normalized to 0–100, weighted ×0.5 |

**Overall Score** = `height_score × 0.50 + hip × 0.20 + arm × 0.20 + knee × 0.10`, capped at 100.

---

## How Jump Height Is Measured

1. **Side detection** — The first 5 frames vote on whether the athlete is facing left or right, selecting the more visible ankle.
2. **Ground calibration** — The ankle Y-position is averaged over 30 frames to establish the baseline ground level.
3. **Airborne detection** — When the ankle rises more than 7 pixels above baseline, the jump state activates.
4. **Height calculation** — Air time (frames) is converted to seconds and fed into the ballistic formula `h = g · t² / 8`, accounting for a 0.15 s reaction offset.

---

## How the AI Report Works

After scoring, the backend constructs a structured prompt containing all biomechanical metrics and ideal reference ranges, then calls `generate_llm_report.remote(prompt)` — a Modal-deployed serverless function that runs GPT-4.1-mini in an isolated cloud container. The function returns a plain-text report (≤ 100 words) covering a performance summary, top 3 strengths, top 3 improvement areas, and drill recommendations.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DB_HOST` | PostgreSQL host (default: `localhost`) |
| `DB_PORT` | PostgreSQL port (default: `5432`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `OPENAI_API_KEY` | Set via Modal secret `openai-secret`, not in `.env` |

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push and open a pull request.

---

## License

MIT
