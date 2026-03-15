"""
auth.py — Steel Eye
ระบบ Authentication เชื่อมต่อ Supabase (PostgreSQL)
"""

import hashlib
import re
import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import json


def _get_conn():
    s = st.secrets["supabase"]
    return psycopg2.connect(
        host=str(s["host"]),
        port=int(s["port"]),
        dbname=str(s["dbname"]),
        user=str(s["user"]),
        password=str(s["password"])
    )


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _sanitize_username(username: str) -> str:
    """อนุญาตเฉพาะ a-z, A-Z, 0-9, _ และ - เท่านั้น"""
    return re.sub(r"[^\w\-]", "", username)


class AuthManager:
    def __init__(self, db_file=None):
        pass

    # ──────────────────────────────────────────
    # AUTH
    # ──────────────────────────────────────────
    def register(self, username: str, password: str, full_name: str = "") -> dict:
        # trim whitespace
        username  = username.strip()
        full_name = full_name.strip()

        # validation
        if len(username) < 3:
            return {"success": False, "message": "Username ต้องมีอย่างน้อย 3 ตัวอักษร"}
        if len(username) > 30:
            return {"success": False, "message": "Username ยาวเกินไป (สูงสุด 30 ตัวอักษร)"}

        # sanitize — ป้องกัน username แปลกๆ
        clean = _sanitize_username(username)
        if clean != username:
            return {"success": False, "message": "Username ใช้ได้เฉพาะตัวอักษร ตัวเลข _ และ -"}

        if len(password) < 6:
            return {"success": False, "message": "Password ต้องมีอย่างน้อย 6 ตัวอักษร"}
        if len(password) > 128:
            return {"success": False, "message": "Password ยาวเกินไป"}
        if not full_name:
            return {"success": False, "message": "กรุณากรอกชื่อ-นามสกุล"}
        if len(full_name) > 100:
            return {"success": False, "message": "ชื่อ-นามสกุลยาวเกินไป"}

        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor()

            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return {"success": False, "message": "Username นี้มีอยู่แล้ว"}

            cur.execute(
                """INSERT INTO users (username, password_hash, full_name, created_at)
                   VALUES (%s, %s, %s, %s)""",
                (username, _hash_password(password), full_name, datetime.now().isoformat()),
            )
            conn.commit()
            return {"success": True, "message": "สมัครสมาชิกสำเร็จ"}

        except Exception as e:
            return {"success": False, "message": f"เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn is not None:
                conn.close()

    def login(self, username: str, password: str) -> dict:
        username = username.strip()

        if not username or not password:
            return {"success": False, "message": "กรุณากรอกข้อมูลให้ครบ"}

        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

            # ใช้ข้อความเดียวกันเพื่อป้องกัน username enumeration
            if not user or user["password_hash"] != _hash_password(password):
                return {"success": False, "message": "Username หรือรหัสผ่านไม่ถูกต้อง"}

            cur.execute(
                "UPDATE users SET last_login = %s WHERE username = %s",
                (datetime.now().isoformat(), username),
            )
            conn.commit()
            return {
                "success": True,
                "message": f"ยินดีต้อนรับ {user['full_name']}",
                "user_data": {
                    "username":   username,
                    "full_name":  user["full_name"],
                    "created_at": user["created_at"],
                },
            }

        except Exception as e:
            return {"success": False, "message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn is not None:
                conn.close()

    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        if len(new_password) < 6:
            return {"success": False, "message": "รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร"}
        if len(new_password) > 128:
            return {"success": False, "message": "รหัสผ่านยาวเกินไป"}
        if old_password == new_password:
            return {"success": False, "message": "รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม"}

        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if not user:
                return {"success": False, "message": "ไม่พบ user"}
            if user["password_hash"] != _hash_password(old_password):
                return {"success": False, "message": "รหัสผ่านเดิมไม่ถูกต้อง"}

            cur.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (_hash_password(new_password), username),
            )
            conn.commit()
            return {"success": True, "message": "เปลี่ยนรหัสผ่านสำเร็จ"}

        except Exception as e:
            return {"success": False, "message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn is not None:
                conn.close()

    # ──────────────────────────────────────────
    # ANALYSES
    # ──────────────────────────────────────────
    def save_user_analysis(self, username: str, analysis_data: dict) -> dict:
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor()

            # จำกัด filename ไม่ให้ยาวเกิน
            filename = str(analysis_data.get("filename", ""))[:500]

            cur.execute(
                """INSERT INTO analyses (username, filename, results, timestamp)
                   VALUES (%s, %s, %s, %s)""",
                (
                    username,
                    filename,
                    json.dumps(analysis_data.get("results", {}), ensure_ascii=False),
                    analysis_data.get("timestamp", datetime.now().isoformat()),
                ),
            )
            conn.commit()
            return {"success": True}

        except Exception as e:
            return {"success": False, "message": str(e)}
        finally:
            if conn is not None:
                conn.close()

    def get_user_analyses(self, username: str, days: int = None) -> list:
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            if days:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cur.execute(
                    """SELECT timestamp, filename, results FROM analyses
                       WHERE username = %s AND timestamp >= %s
                       ORDER BY timestamp DESC LIMIT 500""",
                    (username, cutoff),
                )
            else:
                cur.execute(
                    """SELECT timestamp, filename, results FROM analyses
                       WHERE username = %s
                       ORDER BY timestamp DESC LIMIT 500""",
                    (username,),
                )

            rows = cur.fetchall()
            return [
                (
                    row["timestamp"],
                    {"data": {
                        "filename":  row["filename"],
                        "results":   row["results"] if isinstance(row["results"], dict)
                        else json.loads(row["results"]),
                        "timestamp": row["timestamp"],
                    }},
                )
                for row in rows
            ]

        except Exception as e:
            st.error(f"โหลดประวัติไม่ได้: {e}")
            return []
        finally:
            if conn is not None:
                conn.close()

    def get_user_analyses_by_date_range(
            self, username: str, start_date: datetime, end_date: datetime
    ) -> list:
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(
                """SELECT timestamp, filename, results FROM analyses
                   WHERE username = %s AND timestamp >= %s AND timestamp <= %s
                   ORDER BY timestamp DESC LIMIT 500""",
                (username, start_date.isoformat(), end_date.isoformat()),
            )
            rows = cur.fetchall()
            return [
                (
                    row["timestamp"],
                    {"data": {
                        "filename":  row["filename"],
                        "results":   row["results"] if isinstance(row["results"], dict)
                        else json.loads(row["results"]),
                        "timestamp": row["timestamp"],
                    }},
                )
                for row in rows
            ]

        except Exception as e:
            st.error(f"โหลดประวัติไม่ได้: {e}")
            return []
        finally:
            if conn is not None:
                conn.close()
