# ============================================================
# face_recognition_module/encode_faces.py
# ============================================================
# PURPOSE:
#   Scans the dataset/faces/<student_id>/ directories, generates
#   128-d face encodings for every image found, then stores them
#   both in a local pickle file (for fast startup) AND in MySQL.
#
# USAGE:
#   python face_recognition_module/encode_faces.py
# ============================================================

import os
import sys
import pickle
import face_recognition
import cv2

# Allow imports from the project root when running this script directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from models.db import execute_query


def load_image_with_opencv(image_path: str):
    """
    Loads an image via OpenCV and converts it from BGR → RGB,
    which is what the face_recognition library expects.
    """
    bgr_image = cv2.imread(image_path)
    if bgr_image is None:
        print(f"  [WARN] Could not load image: {image_path}")
        return None
    return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)


def encode_single_image(image_path: str):
    """
    Detects and encodes the FIRST face found in an image.

    Returns:
        numpy.ndarray (128,) | None
    """
    rgb_image = load_image_with_opencv(image_path)
    if rgb_image is None:
        return None

    # face_locations uses HOG model (faster, no GPU needed)
    face_locations = face_recognition.face_locations(
        rgb_image, model=Config.FACE_DETECTION_MODEL
    )

    if not face_locations:
        print(f"  [WARN] No face detected in: {os.path.basename(image_path)}")
        return None

    # Encode only the first detected face
    encodings = face_recognition.face_encodings(rgb_image, [face_locations[0]])
    return encodings[0] if encodings else None


def encode_all_faces():
    """
    Walks dataset/faces/ and encodes all images.
    Each sub-directory name must match the student_id in the DB.

    Returns:
        dict: {"student_id": [encoding, ...], ...}
    """
    all_encodings = {}   # student_id → list of encodings

    if not os.path.exists(Config.DATASET_DIR):
        print(f"[ERROR] Dataset directory not found: {Config.DATASET_DIR}")
        return all_encodings

    student_dirs = [
        d for d in os.listdir(Config.DATASET_DIR)
        if os.path.isdir(os.path.join(Config.DATASET_DIR, d))
    ]

    if not student_dirs:
        print("[INFO] No student directories found in dataset/faces/")
        return all_encodings

    print(f"[INFO] Found {len(student_dirs)} student directory(s). Starting encoding …\n")

    for student_id in student_dirs:
        student_path = os.path.join(Config.DATASET_DIR, student_id)
        image_files  = [
            f for f in os.listdir(student_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        print(f"  → Processing [{student_id}] — {len(image_files)} image(s)")

        encodings_for_student = []
        for img_file in image_files:
            img_path = os.path.join(student_path, img_file)
            enc      = encode_single_image(img_path)
            if enc is not None:
                encodings_for_student.append(enc)

        if encodings_for_student:
            all_encodings[student_id] = encodings_for_student
            print(f"     ✔ {len(encodings_for_student)} encoding(s) generated.")
        else:
            print(f"     ✘ No valid encodings — skipping.")

    return all_encodings


def save_encodings_to_pickle(encodings: dict):
    """Serialises the encodings dict to disk using pickle."""
    os.makedirs(os.path.dirname(Config.ENCODINGS_FILE), exist_ok=True)
    with open(Config.ENCODINGS_FILE, "wb") as f:
        pickle.dump(encodings, f)
    print(f"\n[INFO] Encodings saved to: {Config.ENCODINGS_FILE}")


def save_encodings_to_db(encodings: dict):
    """
    Persists each encoding to the face_encodings table.
    Looks up the user_id from the users table by student_id.
    Clears old encodings for the student first to avoid duplicates.
    """
    print("\n[INFO] Saving encodings to MySQL …")

    for student_id, enc_list in encodings.items():
        # Find user_id
        rows = execute_query(
            "SELECT id FROM users WHERE student_id = %s AND is_active = 1",
            (student_id,),
            fetch=True
        )

        if not rows:
            print(f"  [WARN] Student '{student_id}' not found in DB. Skipping.")
            continue

        user_id = rows[0]["id"]

        # Remove stale encodings for this user
        execute_query("DELETE FROM face_encodings WHERE user_id = %s", (user_id,))

        # Insert each new encoding
        for enc in enc_list:
            enc_blob = pickle.dumps(enc)
            execute_query(
                "INSERT INTO face_encodings (user_id, encoding) VALUES (%s, %s)",
                (user_id, enc_blob)
            )

        print(f"  ✔ Stored {len(enc_list)} encoding(s) for {student_id}")


def load_encodings_from_pickle():
    """
    Loads the pickle file created by encode_all_faces().
    Used by the recognition module at runtime for fast lookup.

    Returns:
        dict | {}
    """
    if not os.path.exists(Config.ENCODINGS_FILE):
        print("[WARN] Encodings file not found. Run encode_faces.py first.")
        return {}

    with open(Config.ENCODINGS_FILE, "rb") as f:
        return pickle.load(f)


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Smart Attendance — Face Encoding Script")
    print("=" * 55)

    encodings = encode_all_faces()

    if encodings:
        save_encodings_to_pickle(encodings)
        save_encodings_to_db(encodings)
        print("\n[DONE] Encoding complete.")
    else:
        print("\n[DONE] Nothing to encode.")
