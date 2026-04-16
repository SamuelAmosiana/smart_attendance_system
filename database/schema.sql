-- ============================================================
-- database/schema.sql — Smart Attendance System DB Schema
-- ============================================================
-- Run this script ONCE to initialise the database.
-- Usage:  mysql -u root -p < database/schema.sql
-- ============================================================

-- 1. Create the database (if it doesn't exist)
CREATE DATABASE IF NOT EXISTS smart_attendance_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_attendance_db;

-- ============================================================
-- TABLE: users
-- Stores registered students / staff.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    student_id  VARCHAR(20)     NOT NULL UNIQUE,        -- e.g. "2024/BCS/001"
    full_name   VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)        NULL UNIQUE,
    course      VARCHAR(100)        NULL,
    year_level  TINYINT UNSIGNED    NULL,               -- Year 1, 2, 3 …
    photo_path  VARCHAR(255)        NULL,               -- Relative path to stored photo
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1      -- Soft-delete flag
);

-- ============================================================
-- TABLE: face_encodings
-- Stores the 128-d face encoding vector (pickled numpy array)
-- as a BLOB.  Each user may have multiple encodings captured
-- from different angles / lighting conditions.
-- ============================================================
CREATE TABLE IF NOT EXISTS face_encodings (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED    NOT NULL,
    encoding    BLOB            NOT NULL,               -- Pickled numpy array (128 floats)
    captured_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_encoding_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Index speeds up loading ALL encodings on startup
CREATE INDEX idx_encoding_user ON face_encodings (user_id);

-- ============================================================
-- TABLE: attendance
-- One row per user per calendar day (unique constraint prevents
-- duplicate check-ins for the same user on the same date).
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED    NOT NULL,
    date        DATE            NOT NULL,
    time_in     TIME            NOT NULL,               -- First check-in time
    status      ENUM('present','late','absent')
                                NOT NULL DEFAULT 'present',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate attendance for same user on same day
    CONSTRAINT uq_attendance_user_date UNIQUE (user_id, date),

    CONSTRAINT fk_attendance_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Index for fast date-range queries on the dashboard
CREATE INDEX idx_attendance_date    ON attendance (date);
CREATE INDEX idx_attendance_user    ON attendance (user_id);

-- ============================================================
-- TABLE: admin_users
-- Simple admin credential store.
-- Default password (hashed): admin123  ← CHANGE IN PRODUCTION
-- Generate a bcrypt hash via Python:
--   import bcrypt; bcrypt.hashpw(b"yourpassword", bcrypt.gensalt())
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_users (
    id           INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50)    NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    created_at   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert a default admin account (password: admin123)
-- Replace the hash with your own bcrypt hash before going live.
INSERT IGNORE INTO admin_users (username, password_hash)
VALUES (
    'admin',
    '$2b$12$KIXbR7hM3z6bK3n5b7x5VObmQVXwH.5UMkOZqsPO.JH3oCj8S5n.2'
);
