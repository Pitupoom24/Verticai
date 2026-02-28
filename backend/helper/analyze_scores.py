import argparse
import json
import time
import uuid
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_styles
from mediapipe.tasks.python.vision import drawing_utils

from pose_extraction import extract_landmarks


def draw_landmarks_on_image(rgb_image, detection_result):
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
    pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

    for pose_landmarks in pose_landmarks_list:
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=pose_landmark_style,
            connection_drawing_spec=pose_connection_style,
        )
    return annotated_image


def normalize_target_score(value, target):
    if value is None:
        return None
    return max(0.0, 100.0 - abs(value - target))


def normalize_range_score(value, min_value, max_value):
    if value is None:
        return None
    distance_from_range = max(min_value - value, value - max_value, 0.0)
    return max(0.0, 100.0 - distance_from_range)


def parse_input_source(input_value):
    if isinstance(input_value, int):
        return input_value
    if isinstance(input_value, str) and input_value.isdigit():
        return int(input_value)
    return input_value


def analyze_jump(model_path, input_source, output_dir, video_base_url=None, show_window=False):
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        output_segmentation_masks=True,
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(input_source)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open input source: {input_source}")

    frame_index = 0
    all_landmark_frames = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None:
        fps = 30

    phase_state = "approach"
    prev_avg_hip_flexion = None
    loading_min_hip_flexion = None
    smallest_loading_min_hip_flexion = None
    smallest_loading_min_knee_flexion = None
    largest_loading_max_knee_flexion = None
    largest_loading_max_shoulder_angle = None
    loading_max_shoulder_timestamp = None
    largest_takeoff_max_shoulder_angle = None
    takeoff_max_shoulder_timestamp = None
    analysis_side = None
    side_locked = False
    left_shoulder_valid_count = 0
    right_shoulder_valid_count = 0
    dramatic_increase_deg = 6.0
    rebound_margin_deg = 4.0

    angle_lines = [
        "Dominant side: not detected!",
        "Knee flexion: not detected!",
        "Hip flexion: not detected!",
        "Ankle angle: not detected!",
        "Shoulder angle: not detected!",
    ]

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    writer = None
    output_video_path = output_dir_path / f"annotated_{uuid.uuid4().hex}.mp4"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_frame_rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        timestamp_ms = int(time.monotonic() * 1000)
        detection_results = detector.detect_for_video(mp_frame_rgb, timestamp_ms)

        frame_height, frame_width, _ = frame.shape
        min_frame_dim = min(frame_height, frame_width)
        phase_font_scale = max(0.4, min(1.2, min_frame_dim / 900.0))
        metric_font_scale = max(0.35, min(1.0, min_frame_dim / 1100.0))
        phase_text_thickness = max(1, int(round(phase_font_scale * 2)))
        metric_text_thickness = max(1, int(round(metric_font_scale * 2)))
        metric_line_spacing = max(18, int(round(26 * metric_font_scale)))
        phase_y = max(22, int(round(35 * phase_font_scale)))
        metrics_start_y = phase_y + max(20, int(round(30 * metric_font_scale)))
        primary_frame_data = None

        if detection_results.pose_landmarks:
            for pose_landmarks in detection_results.pose_landmarks:
                frame_data = extract_landmarks(
                    frame_index, fps, pose_landmarks, frame_height, frame_width
                )
                all_landmark_frames.append(frame_data)
                if primary_frame_data is None:
                    primary_frame_data = frame_data

        frame_index += 1

        annotated_frame = draw_landmarks_on_image(frame_rgb, detection_results)
        annotated_frame_BGR = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)

        if writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                str(output_video_path), fourcc, fps, (frame_width, frame_height)
            )

        phase_text = "Jump phase: not detected!"

        if primary_frame_data is not None:
            angles = primary_frame_data["landmarks"]["angles"]
            right_angles = angles["right"]
            left_angles = angles["left"]

            hip_flexion_values = [
                value
                for value in [right_angles["hip_flexion"], left_angles["hip_flexion"]]
                if value is not None
            ]
            knee_flexion_values = [
                value
                for value in [right_angles["knee_flexion"], left_angles["knee_flexion"]]
                if value is not None
            ]
            current_left_shoulder_angle = left_angles["shoulder_angle"]
            current_right_shoulder_angle = right_angles["shoulder_angle"]

            if current_left_shoulder_angle is not None:
                left_shoulder_valid_count += 1
            if current_right_shoulder_angle is not None:
                right_shoulder_valid_count += 1

            if not side_locked:
                if (
                    current_left_shoulder_angle is not None
                    and current_right_shoulder_angle is None
                ):
                    analysis_side = "left"
                elif (
                    current_right_shoulder_angle is not None
                    and current_left_shoulder_angle is None
                ):
                    analysis_side = "right"
                elif (
                    current_left_shoulder_angle is not None
                    and current_right_shoulder_angle is not None
                ):
                    analysis_side = (
                        "left"
                        if left_shoulder_valid_count >= right_shoulder_valid_count
                        else "right"
                    )

            selected_shoulder_angle = None
            if analysis_side == "left":
                selected_shoulder_angle = current_left_shoulder_angle
            elif analysis_side == "right":
                selected_shoulder_angle = current_right_shoulder_angle
            elif current_left_shoulder_angle is not None:
                selected_shoulder_angle = current_left_shoulder_angle
            elif current_right_shoulder_angle is not None:
                selected_shoulder_angle = current_right_shoulder_angle

            display_side = analysis_side
            if display_side is None:
                if (
                    current_left_shoulder_angle is not None
                    and current_right_shoulder_angle is None
                ):
                    display_side = "left"
                elif (
                    current_right_shoulder_angle is not None
                    and current_left_shoulder_angle is None
                ):
                    display_side = "right"
                elif (
                    current_left_shoulder_angle is not None
                    and current_right_shoulder_angle is not None
                ):
                    display_side = (
                        "left"
                        if left_shoulder_valid_count >= right_shoulder_valid_count
                        else "right"
                    )

            if display_side == "left":
                side_angles = left_angles
            elif display_side == "right":
                side_angles = right_angles
            else:
                side_angles = None

            if side_angles is not None:
                angle_lines = [
                    f"Dominant side: {display_side}",
                    f"Knee flexion: {side_angles['knee_flexion']:.1f}" if side_angles["knee_flexion"] is not None else "Knee flexion: not detected!",
                    f"Hip flexion: {side_angles['hip_flexion']:.1f}" if side_angles["hip_flexion"] is not None else "Hip flexion: not detected!",
                    f"Ankle angle: {side_angles['ankle_angle']:.1f}" if side_angles["ankle_angle"] is not None else "Ankle angle: not detected!",
                    f"Shoulder angle: {side_angles['shoulder_angle']:.1f}" if side_angles["shoulder_angle"] is not None else "Shoulder angle: not detected!",
                ]
            else:
                angle_lines = [
                    "Dominant side: not detected!",
                    "Knee flexion: not detected!",
                    "Hip flexion: not detected!",
                    "Ankle angle: not detected!",
                    "Shoulder angle: not detected!",
                ]

            if hip_flexion_values:
                avg_hip_flexion = sum(hip_flexion_values) / len(hip_flexion_values)
                current_knee_flexion = (
                    min(knee_flexion_values) if knee_flexion_values else None
                )

                if prev_avg_hip_flexion is None:
                    phase_state = "loading" if avg_hip_flexion <= 90 else "approach"
                    if phase_state == "loading":
                        loading_min_hip_flexion = avg_hip_flexion
                        if (
                            smallest_loading_min_hip_flexion is None
                            or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                        ):
                            smallest_loading_min_hip_flexion = loading_min_hip_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                smallest_loading_min_knee_flexion is None
                                or current_knee_flexion < smallest_loading_min_knee_flexion
                            )
                        ):
                            smallest_loading_min_knee_flexion = current_knee_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                largest_loading_max_knee_flexion is None
                                or current_knee_flexion > largest_loading_max_knee_flexion
                            )
                        ):
                            largest_loading_max_knee_flexion = current_knee_flexion
                else:
                    if phase_state == "approach" and avg_hip_flexion <= 90:
                        phase_state = "loading"
                        loading_min_hip_flexion = avg_hip_flexion
                        if (
                            smallest_loading_min_hip_flexion is None
                            or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                        ):
                            smallest_loading_min_hip_flexion = loading_min_hip_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                smallest_loading_min_knee_flexion is None
                                or current_knee_flexion < smallest_loading_min_knee_flexion
                            )
                        ):
                            smallest_loading_min_knee_flexion = current_knee_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                largest_loading_max_knee_flexion is None
                                or current_knee_flexion > largest_loading_max_knee_flexion
                            )
                        ):
                            largest_loading_max_knee_flexion = current_knee_flexion
                    elif phase_state == "loading":
                        if loading_min_hip_flexion is None:
                            loading_min_hip_flexion = avg_hip_flexion
                        else:
                            loading_min_hip_flexion = min(
                                loading_min_hip_flexion, avg_hip_flexion
                            )
                        if (
                            smallest_loading_min_hip_flexion is None
                            or loading_min_hip_flexion < smallest_loading_min_hip_flexion
                        ):
                            smallest_loading_min_hip_flexion = loading_min_hip_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                smallest_loading_min_knee_flexion is None
                                or current_knee_flexion < smallest_loading_min_knee_flexion
                            )
                        ):
                            smallest_loading_min_knee_flexion = current_knee_flexion
                        if (
                            current_knee_flexion is not None
                            and (
                                largest_loading_max_knee_flexion is None
                                or current_knee_flexion > largest_loading_max_knee_flexion
                            )
                        ):
                            largest_loading_max_knee_flexion = current_knee_flexion

                        if (
                            avg_hip_flexion >= loading_min_hip_flexion + rebound_margin_deg
                            and (
                                avg_hip_flexion - prev_avg_hip_flexion
                            ) >= dramatic_increase_deg
                        ):
                            phase_state = "takeoff"

                prev_avg_hip_flexion = avg_hip_flexion
                phase_text = f"Jump phase: {phase_state}"

                if phase_state == "loading" and not side_locked and analysis_side is not None:
                    side_locked = True

                if phase_state == "loading" and selected_shoulder_angle is not None:
                    if (
                        largest_loading_max_shoulder_angle is None
                        or selected_shoulder_angle > largest_loading_max_shoulder_angle
                    ):
                        largest_loading_max_shoulder_angle = selected_shoulder_angle
                        loading_max_shoulder_timestamp = primary_frame_data["timestamp"]

                if phase_state == "takeoff" and selected_shoulder_angle is not None:
                    if (
                        largest_takeoff_max_shoulder_angle is None
                        or selected_shoulder_angle > largest_takeoff_max_shoulder_angle
                    ):
                        largest_takeoff_max_shoulder_angle = selected_shoulder_angle
                        takeoff_max_shoulder_timestamp = primary_frame_data["timestamp"]

        cv2.putText(
            annotated_frame_BGR,
            phase_text,
            (10, phase_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            phase_font_scale,
            (0, 255, 255),
            phase_text_thickness,
            cv2.LINE_AA,
        )

        for idx, text in enumerate(angle_lines):
            cv2.putText(
                annotated_frame_BGR,
                text,
                (10, metrics_start_y + idx * metric_line_spacing),
                cv2.FONT_HERSHEY_SIMPLEX,
                metric_font_scale,
                (255, 255, 255),
                metric_text_thickness,
                cv2.LINE_AA,
            )

        writer.write(annotated_frame_BGR)

        if show_window:
            cv2.imshow("Frames", annotated_frame_BGR)
            if cv2.waitKey(1) == ord("q"):
                break

    cap.release()
    if writer is not None:
        writer.release()
    if show_window:
        cv2.destroyAllWindows()

    hip_flexion_score = normalize_target_score(smallest_loading_min_hip_flexion, 70.0)
    knee_flexion_score = normalize_range_score(
        smallest_loading_min_knee_flexion, 83.0, 90.0
    )
    shoulder_loading_score = normalize_target_score(
        largest_loading_max_shoulder_angle, 90.0
    )

    angular_velocity = None
    angular_velocity_score = None
    if (
        largest_loading_max_shoulder_angle is not None
        and largest_takeoff_max_shoulder_angle is not None
        and loading_max_shoulder_timestamp is not None
        and takeoff_max_shoulder_timestamp is not None
    ):
        delta_angle = (
            largest_takeoff_max_shoulder_angle - largest_loading_max_shoulder_angle
        )
        delta_time = takeoff_max_shoulder_timestamp - loading_max_shoulder_timestamp
        if delta_time > 0:
            angular_velocity = delta_angle / delta_time
            angular_velocity_score = max(
                0.0, min(100.0, (angular_velocity / 500.0) * 100.0)
            )

    if output_video_path is not None and video_base_url:
        annotated_video_url = f"{video_base_url.rstrip('/')}/{output_video_path.name}"
    else:
        annotated_video_url = None

    metrics = {
        "hip_normalized_score": hip_flexion_score,
        "smallest_loading_min_hip_flexion": smallest_loading_min_hip_flexion,
        "knee_normalized_score": knee_flexion_score,
        "smallest_loading_min_knee_flexion": smallest_loading_min_knee_flexion,
        "angular_velocity": angular_velocity,
        "angular_velocity_score": angular_velocity_score,
    }

    return {
        "metrics": metrics,
        "annotated_video_url": annotated_video_url,
        "annotated_video_path": str(output_video_path),
    }


def main():
    parser = argparse.ArgumentParser(description="A testing model for mediapipe")
    parser.add_argument(
        "--model", default="pose_landmarker_heavy.task", help="Path to the model file."
    )
    parser.add_argument("--input", default="0", help="Path to input file or camera index")
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where annotated video is written.",
    )
    parser.add_argument(
        "--video-base-url",
        default="",
        help="Base URL used to build annotated_video_url (optional).",
    )
    parser.add_argument(
        "--show-window",
        action="store_true",
        help="Show OpenCV preview window while processing.",
    )
    args = parser.parse_args()

    payload = analyze_jump(
        model_path=args.model,
        input_source=parse_input_source(args.input),
        output_dir=args.output_dir,
        video_base_url=args.video_base_url,
        show_window=args.show_window,
    )
    print(json.dumps(payload))


if __name__ == "__main__":
    main()