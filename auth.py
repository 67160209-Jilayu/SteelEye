import re
import html
import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import json
import uuid

try:
    import bcrypt
    _BCRYPT = True
except ImportError:
    import hashlib
    _BCRYPT = False

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES     = 15


def _get_conn():
    s = st.secrets["supabase"]
    return psycopg2.connect(
        host=str(s["host"]), port=int(s["port"]),
        dbname=str(s["dbname"]), user=str(s["user"]),
        password=str(s["password"])
    )


def _hash_password(password: str) -> str:
    if _BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    return hashlib.sha256(password.encode()).hexdigest()

def _verify_password(password: str, stored: str) -> bool:
    if _BCRYPT:
        try:
            return bcrypt.checkpw(password.encode(), stored.encode())
        except Exception:
            return False
    return hashlib.sha256(password.encode()).hexdigest() == stored

def _sanitize_username(u: str) -> str:
    return re.sub(r"[^\w\-]", "", u)

def _safe(text: str) -> str:
    return html.escape(str(text))


def _ensure_attempts_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            username       TEXT PRIMARY KEY,
            failed_count   INTEGER NOT NULL DEFAULT 0,
            last_failed_at TIMESTAMPTZ,
            locked_until   TIMESTAMPTZ
        )
    """)

def _check_lockout(cur, username: str) -> tuple:
    cur.execute("SELECT locked_until FROM login_attempts WHERE username = %s", (username,))
    row = cur.fetchone()
    if row and row["locked_until"]:
        lu = row["locked_until"]
        if hasattr(lu, "tzinfo") and lu.tzinfo is None:
            from datetime import timezone
            lu = lu.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=lu.tzinfo)
        if now < lu:
            remaining = int((lu - now).total_seconds() / 60) + 1
            return True, f"บัญชีถูกล็อกชั่วคราว กรุณารอ {remaining} นาที"
    return False, ""

def _record_failed(cur, username: str):
    cur.execute("""
        INSERT INTO login_attempts (username, failed_count, last_failed_at)
        VALUES (%s, 1, NOW())
        ON CONFLICT (username) DO UPDATE
          SET failed_count   = login_attempts.failed_count + 1,
              last_failed_at = NOW(),
              locked_until   = CASE
                WHEN login_attempts.failed_count + 1 >= %s
                THEN NOW() + (%s * INTERVAL '1 minute')
                ELSE NULL
              END
    """, (username, MAX_FAILED_ATTEMPTS, LOCKOUT_MINUTES))

def _clear_attempts(cur, username: str):
    cur.execute("DELETE FROM login_attempts WHERE username = %s", (username,))


SESSION_TOKEN_DAYS = 7   # token หมดอายุใน 7 วัน


def _ensure_sessions_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token       TEXT PRIMARY KEY,
            username    TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at  TIMESTAMPTZ NOT NULL
        )
    """)


class AuthManager:
    def __init__(self, db_file=None):
        pass

    def register(self, username: str, password: str, full_name: str = "") -> dict:
        username  = username.strip()
        full_name = full_name.strip()
        if len(username) < 3:
            return {"success": False, "message": "Username ต้องมีอย่างน้อย 3 ตัวอักษร"}
        if len(username) > 30:
            return {"success": False, "message": "Username ยาวเกินไป (สูงสุด 30 ตัวอักษร)"}
        if _sanitize_username(username) != username:
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
            conn = _get_conn(); cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return {"success": False, "message": "Username นี้มีอยู่แล้ว"}
            cur.execute(
                "INSERT INTO users (username, password_hash, full_name, created_at) VALUES (%s, %s, %s, %s)",
                (username, _hash_password(password), full_name, datetime.now().isoformat()),
            )
            conn.commit()
            return {"success": True, "message": "สมัครสมาชิกสำเร็จ"}
        except Exception:
            return {"success": False, "message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn: conn.close()

    def login(self, username: str, password: str) -> dict:
        username = username.strip()
        if not username or not password:
            return {"success": False, "message": "กรุณากรอกข้อมูลให้ครบ"}
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            _ensure_attempts_table(cur); conn.commit()
            locked, msg = _check_lockout(cur, username)
            if locked:
                return {"success": False, "message": msg}
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if not user or not _verify_password(password, user["password_hash"]):
                _record_failed(cur, username); conn.commit()
                return {"success": False, "message": "Username หรือรหัสผ่านไม่ถูกต้อง"}
            _clear_attempts(cur, username)
            cur.execute("UPDATE users SET last_login = %s WHERE username = %s",
                        (datetime.now().isoformat(), username))
            conn.commit()
            return {
                "success": True,
                "message": f"ยินดีต้อนรับ {_safe(user['full_name'])}",
                "user_data": {
                    "username":   _safe(username),
                    "full_name":  _safe(user["full_name"]),
                    "created_at": _safe(str(user["created_at"])),
                },
            }
        except Exception:
            return {"success": False, "message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn: conn.close()

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
            if not _verify_password(old_password, user["password_hash"]):
                return {"success": False, "message": "รหัสผ่านเดิมไม่ถูกต้อง"}
            cur.execute("UPDATE users SET password_hash = %s WHERE username = %s",
                        (_hash_password(new_password), username))
            conn.commit()
            return {"success": True, "message": "เปลี่ยนรหัสผ่านสำเร็จ"}
        except Exception:
            return {"success": False, "message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}
        finally:
            if conn: conn.close()

    def create_session(self, username: str) -> str | None:
        """สร้าง session token และบันทึกใน DB — คืนค่า token string"""
        token = uuid.uuid4().hex + uuid.uuid4().hex   # 64-char hex
        expires = datetime.now() + timedelta(days=SESSION_TOKEN_DAYS)
        conn = None
        try:
            conn = _get_conn(); cur = conn.cursor()
            _ensure_sessions_table(cur)
            cur.execute(
                "INSERT INTO user_sessions (token, username, expires_at) VALUES (%s, %s, %s)",
                (token, username, expires.isoformat()),
            )
            conn.commit()
            return token
        except Exception:
            return None
        finally:
            if conn: conn.close()

    def verify_session(self, token: str) -> dict | None:
        """ตรวจสอบ token — ถ้า valid คืน user_data dict, ถ้าไม่ valid คืน None"""
        if not token or len(token) != 128:
            return None
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            _ensure_sessions_table(cur); conn.commit()
            cur.execute(
                """SELECT s.username, u.full_name, u.created_at
                   FROM user_sessions s
                   JOIN users u ON u.username = s.username
                   WHERE s.token = %s AND s.expires_at > NOW()""",
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "username":   _safe(row["username"]),
                "full_name":  _safe(row["full_name"]),
                "created_at": _safe(str(row["created_at"])),
            }
        except Exception:
            return None
        finally:
            if conn: conn.close()

    def delete_session(self, token: str):
        """ลบ token ออกจาก DB (ใช้ตอน logout)"""
        if not token:
            return
        conn = None
        try:
            conn = _get_conn(); cur = conn.cursor()
            _ensure_sessions_table(cur)
            cur.execute("DELETE FROM user_sessions WHERE token = %s", (token,))
            conn.commit()
        except Exception:
            pass
        finally:
            if conn: conn.close()

    def save_user_analysis(self, username: str, analysis_data: dict) -> dict:
        conn = None
        try:
            conn = _get_conn(); cur = conn.cursor()
            filename  = _safe(str(analysis_data.get("filename", ""))[:500])
            results   = json.dumps(analysis_data.get("results", {}), ensure_ascii=False)
            timestamp = analysis_data.get("timestamp", datetime.now().isoformat())
            # images_zip เป็น bytes หรือ None
            images_zip = analysis_data.get("images_zip")

            # เพิ่ม column images_zip ถ้ายังไม่มี (idempotent)
            cur.execute("""
                ALTER TABLE analyses
                ADD COLUMN IF NOT EXISTS images_zip BYTEA
            """)

            cur.execute(
                """INSERT INTO analyses (username, filename, results, timestamp, images_zip)
                   VALUES (%s, %s, %s, %s, %s)""",
                (username, filename, results, timestamp,
                 psycopg2.Binary(images_zip) if images_zip else None),
            )
            conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}
        finally:
            if conn: conn.close()

    def _fetch_rows(self, cur) -> list:
        rows = cur.fetchall()
        return [
            (row["timestamp"], {
                "data": {
                    "filename":   row["filename"],
                    "results":    row["results"] if isinstance(row["results"], dict)
                    else json.loads(row["results"]),
                    "timestamp":  row["timestamp"],
                    "images_zip": bytes(row["images_zip"]) if row["images_zip"] else None,
                }
            })
            for row in rows
        ]

    def get_user_analyses(self, username: str, days: int = None) -> list:
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # เพิ่ม column ถ้ายังไม่มี
            cur.execute("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS images_zip BYTEA")
            conn.commit()
            if days:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cur.execute(
                    """SELECT timestamp, filename, results, images_zip FROM analyses
                       WHERE username = %s AND timestamp >= %s
                       ORDER BY timestamp DESC LIMIT 500""",
                    (username, cutoff),
                )
            else:
                cur.execute(
                    """SELECT timestamp, filename, results, images_zip FROM analyses
                       WHERE username = %s
                       ORDER BY timestamp DESC LIMIT 500""",
                    (username,),
                )
            return self._fetch_rows(cur)
        except Exception as e:
            st.error(f"โหลดประวัติไม่ได้: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_user_analyses_by_date_range(self, username: str, start_date: datetime, end_date: datetime) -> list:
        conn = None
        try:
            conn = _get_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS images_zip BYTEA")
            conn.commit()
            cur.execute(
                """SELECT timestamp, filename, results, images_zip FROM analyses
                   WHERE username = %s AND timestamp >= %s AND timestamp <= %s
                   ORDER BY timestamp DESC LIMIT 500""",
                (username, start_date.isoformat(), end_date.isoformat()),
            )
            return self._fetch_rows(cur)
        except Exception as e:
            st.error(f"โหลดประวัติไม่ได้: {e}")
            return []
        finally:
            if conn: conn.close()