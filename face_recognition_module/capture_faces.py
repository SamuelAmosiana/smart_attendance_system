# ============================================================
# face_recognition_module/capture_faces.py
# ============================================================
# PURPOSE:
#   Opens the webcam, captures N face photos for a student,
#   and saves them under dataset/faces/<student_id>/.
#   Called both from the CLI and via the Flask API endpoint.
#
# CLI USAGE:
#   python face_recognition_module/capture_faces.py --student_id 2024/BCS/001 --count 10
# ============================================================

import os
import sys
import cv2
import argparse
import time

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config


def capture_faces(student_id: str, num_samples: int = 10, show_window: bool = True):
    """
    Captures face images for a given student via the webcam.

    Args:
        student_id  : Unique student identifier (used as folder name).
        num_samples : How many images to capture.
        show_window : Whether to show the live preview window.

    Returns:
        list[str]: Paths to the saved image files.
    """
    # Build save directory
    # Note: os.path.join can't handle forward slashes in IDs on Windows,
    # so we replace '/' with '_' for the directory name.
    safe_id   = student_id.replace("/", "_").replace("\\", "_")
    save_dir  = os.path.join(Config.DATASET_DIR, safe_id)
    os.makedirs(save_dir, exist_ok=True)

    # Load OpenCV's built-in Haar Cascade for fast face detection
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture(0)   # 0 = default webcam
    if not cap.isOpened():
        print("[ERROR] Cannot access webcam.")
        return []

    print(f"\n[INFO] Capturing {num_samples} face samples for: {student_id}")
    print("[INFO] Press 'q' to quit early.\n")

    saved_paths  = []
    sample_count = 0
    last_save_time = 0

    while sample_count < num_samples:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame.")
            break

        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces   = face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
        )

        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 0), 2)

        # Save one frame per second (avoids near-duplicate captures)
        current_time = time.time()
        if len(faces) > 0 and (current_time - last_save_time) >= 0.5:
            sample_count += 1
            filename  = f"{safe_id}_{sample_count:03d}.jpg"
            save_path = os.path.join(save_dir, filename)
            cv2.imwrite(save_path, frame)
            saved_paths.append(save_path)
            last_save_time = current_time
            print(f"  Saved sample {sample_count}/{num_samples}: {filename}")

        # Overlay counter on the frame
        cv2.putText(
            frame,
            f"Samples: {sample_count}/{num_samples}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2
        )
        cv2.putText(
            frame,
            f"ID: {student_id}",
            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1
        )

        if show_window:
            cv2.imshow("Face Capture — Press Q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Capture cancelled by user.")
                break

    cap.release()
    if show_window:
        cv2.destroyAllWindows()

    print(f"\n[DONE] Captured {len(saved_paths)} images in: {save_dir}")
    return saved_paths


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture face images for a student.")
    parser.add_argument(
        "--student_id", required=True,
        help="Unique student ID (e.g. 2024/BCS/001)"
    )
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of images to capture (default: 10)"
    )
    args = parser.parse_args()

    paths = capture_faces(args.student_id, args.count, show_window=True)
    if paths:
        print("\nNext step: run encode_faces.py to generate face embeddings.")
