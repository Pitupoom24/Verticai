import os
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile

load_dotenv()

app = FastAPI()

# ── Folders ────────────────────────────────────────────────────────────────
INPUT_VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "input_videos")
os.makedirs(INPUT_VIDEOS_DIR, exist_ok=True)

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
            jump_height                      FLOAT
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
    file_path = os.path.join(INPUT_VIDEOS_DIR, unique_filename)

    # Save file to disk
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    uploaded_at = datetime.utcnow()

    # Insert metadata into PostgreSQL
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO input_videos (original_filename, file_path, content_type, file_size, uploaded_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (file.filename, file_path, file.content_type, file_size, uploaded_at))
    record = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "Video uploaded successfully.",
        "video": dict(record)
    }
