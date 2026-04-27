# ============================================================
# app.py — Main Flask Application
# ============================================================
# Run with:  python app.py
# Default URL: http://127.0.0.1:5000
# ============================================================

import os
import pickle
import threading
import bcrypt

from datetime import date, datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)
from functools import wraps

from config import Config
from models.db import execute_query, get_connection
from attendance.attendance import mark_attendance, get_attendance, get_summary

# ── Optional heavy imports (face recognition) ──────────────
# These are guarded so the app can still start and serve the
# landing page / login even if dlib or OpenCV is unavailable.
try:
    import cv2
    import numpy as np
    import face_recognition
    from face_recognition_module.capture_faces import capture_faces
    from face_recognition_module.encode_faces import (
        encode_all_faces, save_encodings_to_pickle, save_encodings_to_db
    )
    FACE_RECOGNITION_AVAILABLE = True
except Exception as _fr_err:  # noqa: BLE001
    print(f"[WARN] face_recognition not available: {_fr_err}")
    print("[WARN] Face-related API endpoints will return 503 until the package is installed.")
    FACE_RECOGNITION_AVAILABLE = False

# ── App Initialisation ─────────────────────────────────────
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

os.makedirs(Config.DATASET_DIR,              exist_ok=True)
os.makedirs(os.path.dirname(Config.ENCODINGS_FILE), exist_ok=True)


def init_db():
    """
    Creates all tables and seeds the default admin account.
    - Executes each statement individually (psycopg2 requirement).
    - Retries up to 5 times (Render DB may not be ready at cold-start).
    - Admin upsert uses ON CONFLICT DO UPDATE so it fixes wrong hashes too.
    """
    import time

    STATEMENTS = [
        # ── users ────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL          PRIMARY KEY,
            student_id  VARCHAR(20)     NOT NULL UNIQUE,
            full_name   VARCHAR(100)    NOT NULL,
            email       VARCHAR(150)        NULL UNIQUE,
            course      VARCHAR(100)        NULL,
            year_level  SMALLINT            NULL,
            photo_path  VARCHAR(255)        NULL,
            created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active   SMALLINT        NOT NULL DEFAULT 1
        )
        """,
        # ── face_encodings ───────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS face_encodings (
            id          SERIAL      PRIMARY KEY,
            user_id     INTEGER     NOT NULL REFERENCES users(id)
                                    ON DELETE CASCADE ON UPDATE CASCADE,
            encoding    BYTEA       NOT NULL,
            captured_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_encoding_user ON face_encodings (user_id)",
        # ── attendance ───────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id          SERIAL      PRIMARY KEY,
            user_id     INTEGER     NOT NULL REFERENCES users(id)
                                    ON DELETE CASCADE ON UPDATE CASCADE,
            date        DATE        NOT NULL,
            time_in     TIME        NOT NULL,
            status      VARCHAR(10) NOT NULL DEFAULT 'present'
                                    CHECK (status IN ('present','late','absent')),
            created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_attendance_user_date UNIQUE (user_id, date)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance (date)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance (user_id)",
        # ── admin_users ──────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id            SERIAL        PRIMARY KEY,
            username      VARCHAR(50)   NOT NULL UNIQUE,
            password_hash VARCHAR(255)  NOT NULL,
            created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Always upsert admin so a wrong/missing hash is always fixed
        """
        INSERT INTO admin_users (username, password_hash)
        VALUES ('admin', '$2b$12$5x8Fi4Bh0JeAbEbYgwITY.ZOaYpjdFpNBatr/DFWxfZEyEgEKZva6')
        ON CONFLICT (username) DO UPDATE
            SET password_hash = EXCLUDED.password_hash
        """,
    ]

    for attempt in range(1, 6):
        try:
            conn = get_connection()
            if not conn:
                raise RuntimeError("get_connection() returned None")

            with conn.cursor() as cur:
                for stmt in STATEMENTS:
                    cur.execute(stmt)
            conn.commit()
            conn.close()
            print("[INFO] ✅ Database schema initialised and admin seeded successfully.")
            return
        except Exception as e:
            print(f"[WARN] DB init attempt {attempt}/5 failed: {e}")
            if attempt < 5:
                time.sleep(3)

    print("[ERROR] ❌ Could not initialise the database after 5 attempts.")


init_db()   # Auto-run on every startup (all statements are idempotent)


# ── In-memory cache for fast recognition ──────────────────
_known_encodings = []
_known_ids       = []
_encodings_lock  = threading.Lock()


def reload_encodings():
    """
    Reloads face encodings from the pickle file into memory.
    Thread-safe — uses a lock so live recognition isn't disrupted.
    No-ops safely if face_recognition is unavailable.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return
    global _known_encodings, _known_ids
    if not os.path.exists(Config.ENCODINGS_FILE):
        return
    try:
        with open(Config.ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
        with _encodings_lock:
            _known_encodings = []
            _known_ids       = []
            for student_id, enc_list in data.items():
                for enc in enc_list:
                    _known_encodings.append(enc)
                    _known_ids.append(student_id)
    except Exception as e:
        print(f"[WARN] Could not load encodings: {e}")


reload_encodings()   # Load on startup (safe no-op if unavailable)

# Make Python's built-in enumerate available in all Jinja2 templates
app.jinja_env.globals.update(enumerate=enumerate)


# ── Auth Helpers ───────────────────────────────────────────
def login_required(f):
    """Decorator: redirects unauthenticated requests to the login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ============================================================
# AUTH ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def index():
    """Home / landing page."""
    return render_template("index.html")


@app.route("/setup-admin")
def setup_admin():
    """
    One-time route: upserts the default admin account with a verified
    bcrypt hash for 'admin123'.  Call this ONCE after deploy to fix
    the admin login, then it becomes a no-op on subsequent calls.
    Remove this route after you have successfully logged in.
    """
    verified_hash = "$2b$12$5x8Fi4Bh0JeAbEbYgwITY.ZOaYpjdFpNBatr/DFWxfZEyEgEKZva6"
    result = execute_query(
        """
        INSERT INTO admin_users (username, password_hash)
        VALUES (%s, %s)
        ON CONFLICT (username) DO UPDATE
            SET password_hash = EXCLUDED.password_hash
        """,
        ("admin", verified_hash)
    )
    status = "✅ Success" if result is not None else "❌ Failed — check DB connection"
    return (
        f"<h2>{status}</h2>"
        "<p>Username: <strong>admin</strong> &nbsp;|&nbsp; "
        "Password: <strong>admin123</strong></p>"
        "<p><a href='/login'>Go to Login &rarr;</a></p>"
        "<p><a href='/db-check'>Check DB Status &rarr;</a></p>"
    )


@app.route("/db-check")
def db_check():
    """Diagnostic route — shows DB connectivity and table status."""
    from models.db import get_connection
    lines = ["<h2>🔍 DB Diagnostics</h2><pre>"]
    try:
        conn = get_connection()
        if not conn:
            lines.append("❌ Could not connect to database.\n")
        else:
            lines.append("✅ Database connection OK\n\n")
            cur = conn.cursor()

            # Check which tables exist
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [r[0] for r in cur.fetchall()]
            lines.append(f"Tables found: {tables}\n\n")

            # Show admin_users rows (mask password)
            if "admin_users" in tables:
                cur.execute("SELECT id, username, LEFT(password_hash,20) AS hash_prefix, created_at FROM admin_users")
                admins = cur.fetchall()
                lines.append(f"admin_users rows: {admins}\n")
            else:
                lines.append("⚠️  admin_users table does NOT exist!\n")

            cur.close()
            conn.close()
    except Exception as e:
        lines.append(f"❌ Error: {e}\n")
    lines.append("</pre>")
    lines.append("<p><a href='/setup-admin'>Run Setup Admin &rarr;</a></p>")
    lines.append("<p><a href='/login'>Go to Login &rarr;</a></p>")
    return "".join(lines)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Admin login handler."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        rows = execute_query(
            "SELECT id, password_hash FROM admin_users WHERE username = %s",
            (username,),
            fetch=True
        )

        if rows:
            stored_hash = rows[0]["password_hash"].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                session["admin_id"]   = rows[0]["id"]
                session["admin_user"] = username
                flash("Welcome back, " + username + "!", "success")
                return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Admin logout."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ============================================================
# ADMIN PAGES
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Admin overview dashboard."""
    today        = date.today()
    summary      = get_summary()
    today_logs   = get_attendance(today, today)
    total_users  = execute_query("SELECT COUNT(*) AS cnt FROM users WHERE is_active=1",
                                 fetch=True)
    total_today  = len(today_logs)

    return render_template(
        "dashboard.html",
        summary     = summary,
        today_logs  = today_logs,
        total_users = total_users[0]["cnt"] if total_users else 0,
        total_today = total_today,
        today       = today,
        now         = datetime.now(),
    )


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """Student registration page."""
    if request.method == "POST":
        student_id  = request.form.get("student_id",  "").strip()
        full_name   = request.form.get("full_name",   "").strip()
        email       = request.form.get("email",       "").strip() or None
        course      = request.form.get("course",      "").strip() or None
        year_level  = request.form.get("year_level",  "").strip() or None

        if not student_id or not full_name:
            flash("Student ID and Full Name are required.", "danger")
            return redirect(url_for("register"))

        # Check for duplicate student_id
        existing = execute_query(
            "SELECT id FROM users WHERE student_id = %s",
            (student_id,), fetch=True
        )
        if existing:
            flash(f"Student ID '{student_id}' is already registered.", "warning")
            return redirect(url_for("register"))

        execute_query(
            """
            INSERT INTO users (student_id, full_name, email, course, year_level)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (student_id, full_name, email, course, year_level)
        )
        flash(f"Student '{full_name}' registered successfully! "
              "Now capture their face.", "success")
        return redirect(url_for("register"))

    users = execute_query(
        "SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC",
        fetch=True
    ) or []
    return render_template("register.html", users=users)


@app.route("/attendance-log")
@login_required
def attendance_log():
    """View paginated attendance records with date filter."""
    start = request.args.get("start", str(date.today()))
    end   = request.args.get("end",   str(date.today()))
    sid   = request.args.get("student_id", None)

    logs = get_attendance(start, end, sid)
    users = execute_query(
        "SELECT student_id, full_name FROM users WHERE is_active=1 ORDER BY full_name",
        fetch=True
    ) or []

    return render_template(
        "attendance_log.html",
        logs        = logs,
        start       = start,
        end         = end,
        student_id  = sid,
        users       = users,
    )


# ============================================================
# API ENDPOINTS (called by JavaScript on the frontend)
# ============================================================

@app.route("/api/capture-faces", methods=["POST"])
@login_required
def api_capture_faces():
    """
    POST /api/capture-faces
    Body: {"student_id": "2024/BCS/001", "num_samples": 10}

    Starts face capture in a background thread (non-blocking).
    The webcam window opens on the server machine.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify({"success": False,
                        "message": "Face recognition is not available on this server."}), 503

    data       = request.json or {}
    student_id = data.get("student_id", "").strip()
    num_samples = int(data.get("num_samples", 10))

    if not student_id:
        return jsonify({"success": False, "message": "student_id is required."}), 400

    def _run_capture():
        capture_faces(student_id, num_samples, show_window=True)

    thread = threading.Thread(target=_run_capture, daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "message": f"Face capture started for {student_id}. "
                   "Check the webcam window on the server."
    })


@app.route("/api/encode-faces", methods=["POST"])
@login_required
def api_encode_faces():
    """
    POST /api/encode-faces
    Encodes all face images in dataset/faces/ and reloads into memory.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify({"success": False,
                        "message": "Face recognition is not available on this server."}), 503

    encodings = encode_all_faces()
    if not encodings:
        return jsonify({"success": False, "message": "No images found to encode."}), 400

    save_encodings_to_pickle(encodings)
    save_encodings_to_db(encodings)
    reload_encodings()   # Hot-reload into the recognition memory

    return jsonify({
        "success" : True,
        "message" : f"Encoded {sum(len(v) for v in encodings.values())} "
                    f"image(s) for {len(encodings)} student(s).",
        "students": list(encodings.keys()),
    })


@app.route("/api/start-recognition", methods=["POST"])
@login_required
def api_start_recognition():
    """
    POST /api/start-recognition
    Starts the live recognition loop in a background thread.
    The webcam window opens on the server machine.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify({"success": False,
                        "message": "Face recognition is not available on this server."}), 503

    from face_recognition_module.recognize_faces import recognize_faces_live

    def _run():
        recognize_faces_live(show_window=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"success": True, "message": "Recognition started. Check the webcam window."})


@app.route("/api/recognize-frame", methods=["POST"])
def api_recognize_frame():
    """
    POST /api/recognize-frame
    Accepts a single JPEG frame as multipart/form-data and returns
    recognition results.  Used by the browser-based live view.

    Body (form-data):
        frame : binary JPEG/PNG image file
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify({"success": False,
                        "message": "Face recognition is not available on this server."}), 503

    if "frame" not in request.files:
        return jsonify({"success": False, "message": "No frame provided."}), 400

    file_bytes = request.files["frame"].read()
    np_arr     = np.frombuffer(file_bytes, np.uint8)
    frame      = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"success": False, "message": "Invalid image data."}), 400

    # Resize for speed
    small = cv2.resize(frame, (0, 0),
                       fx=Config.FRAME_RESIZE_SCALE,
                       fy=Config.FRAME_RESIZE_SCALE)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(
        rgb_small, model=Config.FACE_DETECTION_MODEL
    )
    face_encs = face_recognition.face_encodings(rgb_small, face_locations)

    results = []
    with _encodings_lock:
        ke = list(_known_encodings)
        ki = list(_known_ids)

    for face_enc, (top, right, bottom, left) in zip(face_encs, face_locations):
        name      = "Unknown"
        student   = None

        if ke:
            matches   = face_recognition.compare_faces(
                ke, face_enc, tolerance=Config.FACE_RECOGNITION_TOLERANCE
            )
            distances = face_recognition.face_distance(ke, face_enc)

            if True in matches:
                best = int(np.argmin(distances))
                if matches[best]:
                    student_id = ki[best]
                    name       = student_id

                    # Mark attendance
                    rec = mark_attendance(student_id)
                    if rec:
                        student = rec

                    # Fetch display name
                    row = execute_query(
                        "SELECT full_name FROM users WHERE student_id=%s",
                        (student_id,), fetch=True
                    )
                    if row:
                        name = row[0]["full_name"]

        scale = 1 / Config.FRAME_RESIZE_SCALE
        results.append({
            "name"   : name,
            "student": student,
            "box"    : {
                "top"   : int(top    * scale),
                "right" : int(right  * scale),
                "bottom": int(bottom * scale),
                "left"  : int(left   * scale),
            }
        })

    return jsonify({"success": True, "faces": results})


@app.route("/api/attendance/today")
@login_required
def api_today_attendance():
    """GET /api/attendance/today — Returns today's attendance as JSON."""
    today = date.today()
    logs  = get_attendance(today, today)
    return jsonify({"success": True, "data": logs, "count": len(logs)})


@app.route("/api/users")
@login_required
def api_users():
    """GET /api/users — Returns all active users as JSON."""
    users = execute_query(
        "SELECT id, student_id, full_name, course, year_level, created_at "
        "FROM users WHERE is_active=1 ORDER BY full_name",
        fetch=True
    ) or []
    # Convert datetime objects to strings
    for u in users:
        u["created_at"] = str(u.get("created_at", ""))
    return jsonify({"success": True, "data": users})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
def api_delete_user(user_id):
    """DELETE /api/users/<id> — Soft-deletes a user."""
    execute_query(
        "UPDATE users SET is_active = 0 WHERE id = %s", (user_id,)
    )
    return jsonify({"success": True, "message": "User deactivated."})


# ── Error handlers ─────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({"success": False, "message": "File too large (max 16 MB)."}), 413


# ── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  Smart Attendance System — Flask Server")
    print(f"  URL: http://0.0.0.0:{port}")
    print("=" * 55)
    # debug=False for production (Render sets DEBUG env if needed)
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode, threaded=True)
