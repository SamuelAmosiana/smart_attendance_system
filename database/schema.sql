-- ============================================================
-- database/schema.sql — Smart Attendance System (PostgreSQL)
-- ============================================================
-- Run ONCE to initialise the database.
-- On Render: tables are auto-created via the init_db route.
-- Local usage:
--   psql -h <host> -U <user> -d smart_attendance_db -f database/schema.sql
-- ============================================================

-- ============================================================
-- TABLE: users
-- ============================================================
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
);

-- ============================================================
-- TABLE: face_encodings
-- ============================================================
CREATE TABLE IF NOT EXISTS face_encodings (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    encoding    BYTEA           NOT NULL,
    captured_at TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_encoding_user ON face_encodings (user_id);

-- ============================================================
-- TABLE: attendance
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    date        DATE            NOT NULL,
    time_in     TIME            NOT NULL,
    status      VARCHAR(10)     NOT NULL DEFAULT 'present'
                                CHECK (status IN ('present','late','absent')),
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_attendance_user_date UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance (date);
CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance (user_id);

-- ============================================================
-- TABLE: admin_users
-- Default login: admin / admin123  ← CHANGE IN PRODUCTION
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL          PRIMARY KEY,
    username      VARCHAR(50)     NOT NULL UNIQUE,
    password_hash VARCHAR(255)    NOT NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin (password: admin123)
-- Hash generated with: bcrypt.hashpw(b"admin123", bcrypt.gensalt(12))
INSERT INTO admin_users (username, password_hash)
VALUES (
    'admin',
    '$2b$12$5x8Fi4Bh0JeAbEbYgwITY.ZOaYpjdFpNBatr/DFWxfZEyEgEKZva6'
)
ON CONFLICT (username) DO UPDATE
    SET password_hash = EXCLUDED.password_hash;
