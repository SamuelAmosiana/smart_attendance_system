# ============================================================
# attendance/attendance.py
# ============================================================
# PURPOSE:
#   Handles all attendance-related logic:
#     • mark_attendance()   — records a check-in (prevents dups)
#     • get_attendance()    — queries logs with optional filters
#     • get_summary()       — per-user totals for the dashboard
# ============================================================

import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.db import execute_query


def mark_attendance(student_id: str, status: str = "present") -> dict | None:
    """
    Marks attendance for a given student, but only ONCE per day.

    Args:
        student_id : The student's unique ID string.
        status     : 'present' | 'late' | 'absent'  (default: 'present')

    Returns:
        dict with attendance info if newly marked, or None if already marked.
    """
    # 1. Look up the user_id from the student_id string
    rows = execute_query(
        "SELECT id, full_name FROM users WHERE student_id = %s AND is_active = 1",
        (student_id,),
        fetch=True
    )

    if not rows:
        print(f"[WARN] mark_attendance: student '{student_id}' not found.")
        return None

    user_id   = rows[0]["id"]
    full_name = rows[0]["full_name"]
    today     = date.today()
    now_time  = datetime.now().strftime("%H:%M:%S")

    # 2. Check for existing record today
    existing = execute_query(
        "SELECT id FROM attendance WHERE user_id = %s AND date = %s",
        (user_id, today),
        fetch=True
    )

    if existing:
        # Already marked — silently skip (normal in a live recognition loop)
        return None

    # 3. Insert new attendance record
    execute_query(
        """
        INSERT INTO attendance (user_id, date, time_in, status)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, today, now_time, status)
    )

    return {
        "student_id": student_id,
        "full_name" : full_name,
        "date"      : str(today),
        "time_in"   : now_time,
        "status"    : status,
    }


def get_attendance(start_date=None, end_date=None, student_id: str = None) -> list:
    """
    Fetches attendance records with optional filters.

    Args:
        start_date  : 'YYYY-MM-DD' string or date object. Defaults to today.
        end_date    : 'YYYY-MM-DD' string or date object. Defaults to today.
        student_id  : Filter by a specific student (optional).

    Returns:
        list[dict]: Each dict has keys:
            full_name, student_id, course, date, time_in, status
    """
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = date.today()

    query = """
        SELECT
            u.full_name,
            u.student_id,
            u.course,
            a.date,
            a.time_in,
            a.status
        FROM attendance a
        JOIN users u ON u.id = a.user_id
        WHERE a.date BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if student_id:
        query  += " AND u.student_id = %s"
        params.append(student_id)

    query += " ORDER BY a.date DESC, a.time_in DESC"

    rows = execute_query(query, tuple(params), fetch=True)
    return rows if rows else []


def get_summary(month: int = None, year: int = None) -> list:
    """
    Returns per-student attendance totals for the dashboard overview.

    Args:
        month : Calendar month (1-12). Defaults to current month.
        year  : Calendar year.      Defaults to current year.

    Returns:
        list[dict]: Each dict has:
            student_id, full_name, course, present_count, late_count, total_days
    """
    today = date.today()
    month = month or today.month
    year  = year  or today.year

    query = """
        SELECT
            u.student_id,
            u.full_name,
            u.course,
            SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN a.status = 'late'    THEN 1 ELSE 0 END) AS late_count,
            COUNT(a.id) AS total_days
        FROM users u
        LEFT JOIN attendance a
            ON a.user_id = u.id
            AND EXTRACT(MONTH FROM a.date) = %s
            AND EXTRACT(YEAR  FROM a.date) = %s
        WHERE u.is_active = 1
        GROUP BY u.id, u.student_id, u.full_name, u.course
        ORDER BY u.full_name ASC
    """
    rows = execute_query(query, (month, year), fetch=True)
    return rows if rows else []
