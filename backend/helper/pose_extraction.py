# Mapping index with body parts (the index is defined by MediaPipe docs)
from helper.angle_calculation import calculate_angle
import math

KEYPOINT_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index"
]

def extract_landmarks(frame_index, fps, landmark_results, frame_height, frame_width):
    landmarks_dict = {}
    for landmark_idx, landmark in enumerate(landmark_results): 
        x_normalized = landmark.x
        y_normalized = landmark.y

        x_pixel = x_normalized * frame_width
        y_pixel = y_normalized * frame_height

        # IF the confidence is below 50%, then x-pixel and y_pixel would be 0
        # if landmark.visibility < 0.5:
        #     x_pixel = 0
        #     y_pixel = 0

        landmarks_dict[KEYPOINT_NAMES[landmark_idx]] = {
            "x_pixel": x_pixel,
            "y_pixel": y_pixel,
            "z_pixel": landmark.z, # Z = depth
            "visibility": landmark.visibility
        }

    def calculate_joint_angle(point_a, point_b, point_c):
        a = landmarks_dict.get(point_a)
        b = landmarks_dict.get(point_b)
        c = landmarks_dict.get(point_c)

        if not a or not b or not c:
            return None

        if (
            a["visibility"] < 0.5
            or b["visibility"] < 0.5
            or c["visibility"] < 0.5
        ):
            return None

        angle = calculate_angle(
            (a["x_pixel"], a["y_pixel"]),
            (b["x_pixel"], b["y_pixel"]),
            (c["x_pixel"], c["y_pixel"]),
        )
        return float(angle) if math.isfinite(angle) else None

    landmarks_dict["angles"] = {
        "left": {
            "knee_flexion": calculate_joint_angle("left_hip", "left_knee", "left_ankle"),
            "hip_flexion": calculate_joint_angle("left_shoulder", "left_hip", "left_knee"),
            "ankle_angle": calculate_joint_angle("left_knee", "left_ankle", "left_foot_index"),
            "shoulder_angle": calculate_joint_angle("left_hip", "left_shoulder", "left_elbow"),
        },
        "right": {
            "knee_flexion": calculate_joint_angle("right_hip", "right_knee", "right_ankle"),
            "hip_flexion": calculate_joint_angle("right_shoulder", "right_hip", "right_knee"),
            "ankle_angle": calculate_joint_angle("right_knee", "right_ankle", "right_foot_index"),
            "shoulder_angle": calculate_joint_angle("right_hip", "right_shoulder", "right_elbow"),
        },
    }

    frame_data = {
        "frame_index": frame_index,
        "timestamp": frame_index / fps,
        "landmarks": landmarks_dict
    }
    return frame_data