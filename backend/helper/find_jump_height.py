from ultralytics import YOLO
import cv2
import os
from collections import deque

# ── Constants ────────────────────────────────────────────────────────────────
G = 9.81
SIDE_DETECT_FRAMES = 5
GROUND_CALIBRATION_FRAMES = 30
AIRBORNE_THRESHOLD = 7
SMOOTH_WINDOW = 5

LEFT_ANKLE  = 16
RIGHT_ANKLE = 17

skeleton_connections = [
    (16, 14), (14, 12), (17, 15), (15, 13), (12, 13),
    (6, 12), (7, 13), (6, 7), (6, 8), (7, 9), (8, 10), (9, 11)
]


def isLeftSide(keypoints):
    ls, rs = keypoints[4], keypoints[5]
    lh, rh = keypoints[11], keypoints[12]
    pts = [(ls[0], rs[0]), (lh[0], rh[0])]
    scores = [r - l for l, r in pts if l > 0 and r > 0]
    if not scores:
        return None
    return sum(scores) / len(scores) > 0


def get_ankle_y_single(keypoints, use_left):
    idx = (LEFT_ANKLE - 1) if use_left else (RIGHT_ANKLE - 1)
    x, y = keypoints[idx]
    return float(y) if x > 0 and y > 0 else None


def smooth_y(buffer, new_y, frame_num):
    buffer.append((new_y, frame_num))


def find_max_y(buffer):
    max_y, frame_num = float('-inf'), None
    for y, f in buffer:
        if y > max_y:
            max_y, frame_num = y, f
    return max_y, frame_num


def find_jump_height(video_path: str) -> float | None:
    """Analyze a video and return the best jump height in meters, or None if no jump detected."""
    model = YOLO('yolov8n-pose.pt')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    ground_y = None
    calibration_ys = []
    ankle_y_buffer = deque(maxlen=SMOOTH_WINDOW)
    state = 'SIDE_DETECT'
    jump_results = []
    side_detect_votes = []
    use_left_ankle = None
    y1 = None
    max_frame1 = None
    processed = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model(frame, conf=0.5, verbose=False)

        ankle_y_raw = None
        person_kpts = None
        if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
            person_kpts = results[0].keypoints.xy[0].cpu().numpy()
            if use_left_ankle is not None:
                ankle_y_raw = get_ankle_y_single(person_kpts, use_left_ankle)

        if state == 'SIDE_DETECT':
            if person_kpts is not None:
                vote = isLeftSide(person_kpts)
                if vote is not None:
                    side_detect_votes.append(vote)
            if processed >= SIDE_DETECT_FRAMES - 1:
                use_left_ankle = (side_detect_votes.count(True) >= side_detect_votes.count(False)) if side_detect_votes else True
                state = 'CALIBRATING'

        elif state == 'CALIBRATING':
            if ankle_y_raw is not None:
                calibration_ys.append(ankle_y_raw)
            if len(calibration_ys) >= GROUND_CALIBRATION_FRAMES:
                ground_y = sum(calibration_ys) / len(calibration_ys)
                state = 'STANDING'

        elif ankle_y_raw is not None:
            smooth_y(ankle_y_buffer, ankle_y_raw, processed)

            if state == 'STANDING':
                is_airborne = ankle_y_raw < (ground_y - AIRBORNE_THRESHOLD)
            elif state == 'AIRBORNE':
                is_airborne = ankle_y_raw <= y1
            else:
                is_airborne = False

            if state == 'STANDING' and is_airborne:
                y1, max_frame1 = find_max_y(ankle_y_buffer)
                state = 'AIRBORNE'

            elif state == 'AIRBORNE' and not is_airborne:
                state = 'STANDING'
                air_frames = processed - max_frame1
                t = air_frames / fps
                h = G * t**2 / 8
                ankle_y_buffer.clear()
                y1 = None
                max_frame1 = None
                if h >= 0.05:
                    jump_results.append(h)

        processed += 1

    cap.release()
    return max(jump_results) if jump_results else None
