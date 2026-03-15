"""
auth.py - Authentication System for Steel Eye
ระบบ login สำหรับ Steel Eye
- สนับสนุน multi-user
- เก็บ user data แยก
- Session management
"""

import json
import os
from datetime import datetime
import hashlib

class AuthManager:
    """จัดการ authentication และ user data"""
    
    def __init__(self, db_file="users.json"):
        self.db_file = db_file
        self._ensure_db()
    
    def _ensure_db(self):
        """สร้าง database file ถ้ายังไม่มี"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, "w") as f:
                json.dump({}, f)
    
    def _hash_password(self, password):
        """Hash password ด้วย SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_users(self):
        """โหลด users จาก database"""
        try:
            with open(self.db_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def _save_users(self, users):
        """บันทึก users ลง database"""
        with open(self.db_file, "w") as f:
            json.dump(users, f, indent=4)
    
    def register(self, username, password, full_name=""):
        """สมัครสมาชิก
        
        Args:
            username: ชื่อผู้ใช้ (unique)
            password: รหัสผ่าน
            full_name: ชื่อเต็ม (optional)
        
        Returns:
            dict: {"success": bool, "message": str}
        """
        users = self._load_users()
        
        # ตรวจสอบว่า username มีอยู่แล้ว
        if username in users:
            return {
                "success": False,
                "message": "Username already exists"
            }
        
        # ตรวจสอบ username length
        if len(username) < 3:
            return {
                "success": False,
                "message": "Username must be at least 3 characters"
            }
        
        # ตรวจสอบ password length
        if len(password) < 6:
            return {
                "success": False,
                "message": "Password must be at least 6 characters"
            }
        
        # เก็บ user data
        users[username] = {
            "password": self._hash_password(password),
            "full_name": full_name,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "analyses": {}  # เก็บประวัติ analysis ของ user นี้
        }
        
        self._save_users(users)
        
        return {
            "success": True,
            "message": f"User '{username}' registered successfully"
        }
    
    def login(self, username, password):
        """เข้าสู่ระบบ
        
        Args:
            username: ชื่อผู้ใช้
            password: รหัสผ่าน
        
        Returns:
            dict: {"success": bool, "message": str, "user_data": dict or None}
        """
        users = self._load_users()
        
        # ตรวจสอบว่า username มีอยู่
        if username not in users:
            return {
                "success": False,
                "message": "Username not found"
            }
        
        # ตรวจสอบ password
        user = users[username]
        if user["password"] != self._hash_password(password):
            return {
                "success": False,
                "message": "Incorrect password"
            }
        
        # Update last login
        user["last_login"] = datetime.now().isoformat()
        self._save_users(users)
        
        return {
            "success": True,
            "message": f"Welcome {user.get('full_name', username)}!",
            "user_data": {
                "username": username,
                "full_name": user.get("full_name", username),
                "created_at": user["created_at"]
            }
        }
    
    def save_user_analysis(self, username, analysis_data):
        """บันทึก analysis สำหรับ user
        
        Args:
            username: ชื่อผู้ใช้
            analysis_data: dict ของ analysis
        """
        users = self._load_users()
        
        if username not in users:
            return {"success": False, "message": "User not found"}
        
        timestamp = datetime.now().isoformat()
        
        # เก็บ analysis พร้อม timestamp
        users[username]["analyses"][timestamp] = {
            "data": analysis_data,
            "timestamp": timestamp
        }
        
        self._save_users(users)
        
        return {
            "success": True,
            "message": "Analysis saved"
        }
    
    def get_user_analyses(self, username, days=None):
        """ดึง analyses ของ user
        
        Args:
            username: ชื่อผู้ใช้
            days: กี่วันที่ผ่านมา (None = ทั้งหมด)
        
        Returns:
            list: list ของ analyses
        """
        from datetime import datetime, timedelta
        
        users = self._load_users()
        
        if username not in users:
            return []
        
        analyses = users[username].get("analyses", {})
        
        # ถ้ากำหนด days ให้ filter เฉพาะช่วงวันนั้น
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = {}
            
            for timestamp, data in analyses.items():
                try:
                    dt = datetime.fromisoformat(timestamp)
                    if dt >= cutoff_date:
                        filtered[timestamp] = data
                except:
                    pass
            
            return sorted(
                filtered.items(),
                key=lambda x: x[0],
                reverse=True
            )
        
        return sorted(
            analyses.items(),
            key=lambda x: x[0],
            reverse=True
        )
    
    def get_user_analyses_by_date_range(self, username, start_date, end_date):
        """ดึง analyses ในช่วงวันที่เฉพาะ
        
        Args:
            username: ชื่อผู้ใช้
            start_date: วันเริ่มต้น (datetime object)
            end_date: วันสิ้นสุด (datetime object)
        
        Returns:
            list: list ของ analyses ในช่วงนั้น
        """
        from datetime import datetime
        
        users = self._load_users()
        
        if username not in users:
            return []
        
        analyses = users[username].get("analyses", {})
        filtered = {}
        
        for timestamp, data in analyses.items():
            try:
                dt = datetime.fromisoformat(timestamp)
                if start_date <= dt <= end_date:
                    filtered[timestamp] = data
            except:
                pass
        
        return sorted(
            filtered.items(),
            key=lambda x: x[0],
            reverse=True
        )
    
    def get_all_usernames(self):
        """ดึงรายชื่อ users ทั้งหมด"""
        return list(self._load_users().keys())
    
    def user_exists(self, username):
        """ตรวจสอบว่า user มีอยู่หรือไม่"""
        users = self._load_users()
        return username in users
    
    def delete_user(self, username):
        """ลบ user"""
        users = self._load_users()
        
        if username in users:
            del users[username]
            self._save_users(users)
            return {"success": True, "message": "User deleted"}
        
        return {"success": False, "message": "User not found"}
    
    def change_password(self, username, old_password, new_password):
        """เปลี่ยนรหัสผ่าน"""
        users = self._load_users()
        
        if username not in users:
            return {"success": False, "message": "User not found"}
        
        user = users[username]
        
        # ตรวจสอบ old password
        if user["password"] != self._hash_password(old_password):
            return {"success": False, "message": "Incorrect current password"}
        
        # Update password
        user["password"] = self._hash_password(new_password)
        self._save_users(users)
        
        return {"success": True, "message": "Password changed successfully"}


# Demo usage
if __name__ == "__main__":
    auth = AuthManager()
    
    # Register
    print(auth.register("john", "password123", "John Doe"))
    
    # Login
    print(auth.login("john", "password123"))
    
    # Save analysis
    print(auth.save_user_analysis("john", {"detection": "test"}))
    
    # Get analyses
    print(auth.get_user_analyses("john"))
