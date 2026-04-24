-- ============================================================
-- database/schema_aiven.sql — Aiven (defaultdb) version
-- ============================================================
-- Same schema as schema.sql but WITHOUT the CREATE DATABASE
-- and USE statements — Aiven's defaultdb already exists.
-- Run via XAMPP CLI (see README or setup guide).
-- ============================================================

-- ============================================================
-- TABLE: users
-- Stores registered students / staff.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    student_id  VARCHAR(20)     NOT NULL UNIQUE,
    full_name   VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)        NULL UNIQUE,
    course      VARCHAR(100)        NULL,
    year_level  TINYINT UNSIGNED    NULL,
    photo_path  VARCHAR(255)        NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1
);

-- ============================================================
-- TABLE: face_encodings
-- ============================================================
CREATE TABLE IF NOT EXISTS face_encodings (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED    NOT NULL,
    encoding    BLOB            NOT NULL,
    captured_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_encoding_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_encoding_user ON face_encodings (user_id);

-- ============================================================
-- TABLE: attendance
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED    NOT NULL,
    date        DATE            NOT NULL,
    time_in     TIME            NOT NULL,
    status      ENUM('present','late','absent')
                                NOT NULL DEFAULT 'present',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_attendance_user_date UNIQUE (user_id, date),

    CONSTRAINT fk_attendance_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_attendance_date ON attendance (date);
CREATE INDEX idx_attendance_user ON attendance (user_id);

-- ============================================================
-- TABLE: admin_users
-- Default password: admin123
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_users (
    id            INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)    NOT NULL UNIQUE,
    password_hash VARCHAR(255)   NOT NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO admin_users (username, password_hash)
VALUES (
    'admin',
    '$2b$12$KIXbR7hM3z6bK3n5b7x5VObmQVXwH.5UMkOZqsPO.JH3oCj8S5n.2'
);
