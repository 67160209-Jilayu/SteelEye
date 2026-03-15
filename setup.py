"""
setup.py - Initialize project structure for Streamlit Cloud
สร้าง directories และ initialize files ที่จำเป็น
"""

import os
import json


def setup_directories():
    """สร้าง directories ที่โปรเจค Steel Eye ต้องใช้"""
    directories = [
        "image_basket/input",
        "image_basket/output",
        "package"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Directory '{directory}' is ready")


def setup_user_history():
    """
    Initialize user_history.json ถ้ายังไม่มี
    หรือถ้าไฟล์ว่างเปล่า
    """
    file_path = "steel_eye_users.json"

    # ตรวจสอบว่าไฟล์มีอยู่และไม่ว่าง
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        with open(file_path, "w") as f:
            json.dump({}, f, indent=4)
        print(f"✅ File '{file_path}' initialized")
    else:
        print(f"✅ File '{file_path}' already exists")


def main():
    """รัน setup ทั้งหมด"""
    print("🔧 Initializing Steel Eye project structure...")
    setup_directories()
    setup_user_history()
    print("✅ Setup completed!")


if __name__ == "__main__":
    main()
