# ============================================================
# face_recognition_module/recognize_faces.py
# ============================================================
# PURPOSE:
#   Opens the webcam, recognises faces in real-time using the
#   pre-built encodings, and triggers attendance marking when
#   a known face is detected.
#
# PERFORMANCE NOTES (optimised for low-end / Celeron CPUs):
#   • Frames are RESIZED to 50% before processing.
#   • Only every Nth frame is analysed (FRAME_SKIP in config).
#   • HOG model (not CNN) is used for detection.
#   • Results are cached across skipped frames to keep the
#     overlay smooth without re-computing every frame.
# ============================================================

import os
import sys
import pickle
import cv2
import face_recognition
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from attendance.attendance import mark_attendance


def load_known_encodings():
    """
    Loads pre-computed face encodings from the pickle file.

    Returns:
        tuple: (known_encodings: list, known_ids: list)
    """
    if not os.path.exists(Config.ENCODINGS_FILE):
        print("[ERROR] Encodings file missing. Run encode_faces.py first.")
        return [], []

    with open(Config.ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)   # dict: {student_id: [enc, ...]}

    known_encodings = []
    known_ids       = []

    for student_id, enc_list in data.items():
        for enc in enc_list:
            known_encodings.append(enc)
            known_ids.append(student_id)

    print(f"[INFO] Loaded {len(known_encodings)} encoding(s) for "
          f"{len(data)} student(s).")
    return known_encodings, known_ids


def recognize_faces_live(show_window: bool = True):
    """
    Main recognition loop.  Opens the webcam and recognises faces
    continuously until the user presses 'q'.

    Args:
        show_window: Display the live annotated video feed.

    Returns:
        list[dict]: Records of attendance marked in this session.
    """
    known_encodings, known_ids = load_known_encodings()
    if not known_encodings:
        return []

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot access webcam.")
        return []

    print("\n[INFO] Starting face recognition. Press 'q' to quit.\n")

    frame_counter       = 0
    attendance_session  = []     # attendance marked this session

    # Cache last-frame results so skipped frames still show labels
    cached_face_locations = []
    cached_face_names     = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_counter += 1

        # ── Only process every Nth frame ───────────────────────
        if frame_counter % Config.FRAME_SKIP == 0:

            # Resize frame for faster processing
            small_frame = cv2.resize(
                frame, (0, 0),
                fx=Config.FRAME_RESIZE_SCALE,
                fy=Config.FRAME_RESIZE_SCALE
            )
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Detect face locations (HOG model)
            face_locations = face_recognition.face_locations(
                rgb_small, model=Config.FACE_DETECTION_MODEL
            )

            # Compute 128-d encodings for all detected faces
            face_encodings_found = face_recognition.face_encodings(
                rgb_small, face_locations
            )

            face_names = []
            for face_enc in face_encodings_found:
                # Compare against known encodings
                matches   = face_recognition.compare_faces(
                    known_encodings, face_enc,
                    tolerance=Config.FACE_RECOGNITION_TOLERANCE
                )
                distances = face_recognition.face_distance(known_encodings, face_enc)

                name = "Unknown"
                if True in matches:
                    best_match_idx = int(np.argmin(distances))
                    if matches[best_match_idx]:
                        student_id = known_ids[best_match_idx]
                        name       = student_id

                        # Mark attendance (de-duplicated inside the function)
                        result = mark_attendance(student_id)
                        if result and result not in attendance_session:
                            attendance_session.append(result)
                            print(f"  ✔ Attendance marked: {result}")

                face_names.append(name)

            # Scale locations back to original frame size
            scale = 1 / Config.FRAME_RESIZE_SCALE
            cached_face_locations = [
                (int(top * scale), int(right * scale),
                 int(bottom * scale), int(left * scale))
                for (top, right, bottom, left) in face_locations
            ]
            cached_face_names = face_names

        # ── Draw bounding boxes & labels ───────────────────────
        for (top, right, bottom, left), name in zip(
            cached_face_locations, cached_face_names
        ):
            colour = (0, 200, 0) if name != "Unknown" else (0, 0, 220)

            # Box
            cv2.rectangle(frame, (left, top), (right, bottom), colour, 2)

            # Label background
            cv2.rectangle(
                frame, (left, bottom - 30), (right, bottom),
                colour, cv2.FILLED
            )

            # Name text
            cv2.putText(
                frame, name,
                (left + 4, bottom - 8),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1
            )

        if show_window:
            cv2.imshow("Smart Attendance — Face Recognition (Q: quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\n[INFO] Recognition stopped by user.")
                break

    cap.release()
    if show_window:
        cv2.destroyAllWindows()

    print(f"\n[DONE] Session complete. Attendance marked: {len(attendance_session)}")
    return attendance_session


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    recognize_faces_live(show_window=True)
