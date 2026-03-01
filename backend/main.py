import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import OpenAI

from helper.analyze_scores import analyze_jump
from helper.find_jump_height import find_jump_height

load_dotenv()

app = FastAPI()

# ── Folders ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INPUT_VIDEOS_DIR = BASE_DIR / "input_videos"
OUTPUT_VIDEOS_DIR = BASE_DIR / "output_videos"
MODEL_PATH = BASE_DIR / "helper" / "pose_landmarker_heavy.task"

INPUT_VIDEOS_DIR.mkdir(exist_ok=True)
OUTPUT_VIDEOS_DIR.mkdir(exist_ok=True)

# ── Allowed video MIME types ───────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/avi",
    "video/quicktime",   # .mov
    "video/x-matroska",  # .mkv
    "video/x-msvideo",   # .avi (alternate)
    "video/mpeg",
}

# ── DB connection ──────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

# ── Create table on startup ────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS input_videos (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            original_filename TEXT NOT NULL,
            file_path         TEXT NOT NULL,
            content_type      TEXT NOT NULL,
            file_size         BIGINT NOT NULL,
            uploaded_at       TIMESTAMP NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS output_videos (
            id                              UUID PRIMARY KEY REFERENCES input_videos(id),
            original_filename               TEXT NOT NULL,
            file_path                       TEXT NOT NULL,
            hip_normalized_score            FLOAT,
            smallest_loading_min_hip_flexion FLOAT,
            knee_normalized_score           FLOAT,
            smallest_loading_min_knee_flexion FLOAT,
            angular_velocity                FLOAT,
            angular_velocity_score          FLOAT,
            jump_height                     FLOAT,
            llm_report                      TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables ready.")

# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Verticai API is running."}


@app.get("/input-videos")
def get_videos():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM input_videos ORDER BY uploaded_at DESC")
    records = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "total": len(records),
        "videos": [dict(r) for r in records]
    }


@app.get("/output-videos")
def get_output_videos():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM output_videos")
    records = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "total": len(records),
        "output_videos": [dict(r) for r in records]
    }


@app.post("/input-videos")
async def upload_video(file: UploadFile = File(...)):
    # Validate MIME type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: '{file.content_type}'. Only video files are allowed."
        )

    # Generate a unique filename to avoid collisions
    ext = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = INPUT_VIDEOS_DIR / unique_filename

    # Save file to disk
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    uploaded_at = datetime.utcnow()

    # ── Insert into input_videos ───────────────────────────────────────────
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO input_videos (original_filename, file_path, content_type, file_size, uploaded_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (file.filename, str(file_path), file.content_type, file_size, uploaded_at))
    input_record = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    # ── Run pose analysis & jump height concurrently ──────────────────────
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_analyze = loop.run_in_executor(
            executor,
            lambda: analyze_jump(
                model_path=str(MODEL_PATH),
                input_source=str(file_path),
                output_dir=str(OUTPUT_VIDEOS_DIR),
            )
        )
        future_height = loop.run_in_executor(
            executor,
            lambda: find_jump_height(str(file_path))
        )
        try:
            output, jump_height = await asyncio.gather(future_analyze, future_height)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    metrics = output["metrics"]
    annotated_video_path = output["annotated_video_path"]
    annotated_filename = Path(annotated_video_path).name

    # ── Generate LLM report ───────────────────────────────────────────
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"""
## Here is the reference to ideal ranges of 3 metrics:
smallest_loading_min_hip_flexion: 70° exactly
smallest_loading_min_knee_flexion: 83° – 90°
angular_velocity: ≥ 500

## Athlete's Metrics:
- smallest_loading_min_hip_flexion: {metrics['smallest_loading_min_hip_flexion']}
- hip_normalized_score: {metrics['hip_normalized_score']}
- smallest_loading_min_knee_flexion: {metrics['smallest_loading_min_knee_flexion']}
- knee_normalized_score: {metrics['knee_normalized_score']}
- angular_velocity: {metrics['angular_velocity']}
- angular_velocity_score: {metrics['angular_velocity_score']}
- jump_height: {jump_height}

## Instruction: Write me a report that includes:

### 1. Performance Summary (2–3 sentences)
Brief, encouraging overview of this jump's performance.

### 2. Top 3 Strengths
What the jumper is doing well biomechanically.

### 3. Top 3 Areas to Improve (Priority Order)
Be specific — reference exact metrics and what the ideal looks like.

### 4. Drill Recommendations
For each improvement area, give 1–2 specific drills or exercises (name them, explain briefly).

Keep the tone motivational but honest. Be specific, not generic.
"""
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )
        llm_report = response.output_text
    except Exception as e:
        print(f"❌ LLM report failed: {e}")
        llm_report = None

    # ── Insert into output_videos ──────────────────────────────────────────
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO output_videos (
            id, original_filename, file_path,
            hip_normalized_score, smallest_loading_min_hip_flexion,
            knee_normalized_score, smallest_loading_min_knee_flexion,
            angular_velocity, angular_velocity_score, jump_height, llm_report
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        input_record["id"],
        annotated_filename,
        annotated_video_path,
        metrics["hip_normalized_score"],
        metrics["smallest_loading_min_hip_flexion"],
        metrics["knee_normalized_score"],
        metrics["smallest_loading_min_knee_flexion"],
        metrics["angular_velocity"],
        metrics["angular_velocity_score"],
        jump_height,
        llm_report,
    ))
    output_record = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "Video uploaded and analyzed successfully.",
        "input_video": dict(input_record),
        "output_video": dict(output_record),
    }
