"""
state_manager.py - Manage Streamlit session state and file persistence
จัดการ state ของ runtime เพื่อให้ persist ข้อมูลระหว่างการใช้งาน
"""

import streamlit as st
import json
import os
from core import MainSystem, UniqueRuntimeSystem


def load_user_history():
    """
    โหลด user_history.json เข้า session_state
    เพื่อให้สามารถเข้าถึงได้ในตัวแปร st.session_state.user_history
    """
    if "user_history" not in st.session_state:
        try:
            with open("user_history.json", "r") as f:
                content = f.read().strip()
                if content:
                    st.session_state.user_history = json.loads(content)
                else:
                    st.session_state.user_history = {}
        except FileNotFoundError:
            st.session_state.user_history = {}
        except json.JSONDecodeError:
            st.session_state.user_history = {}


def save_user_history():
    """
    บันทึก session_state.user_history ลงไป user_history.json
    เรียกใช้เมื่อต้องการเซฟข้อมูล
    """
    if "user_history" in st.session_state:
        with open("user_history.json", "w") as f:
            json.dump(st.session_state.user_history, f, indent=4)


def initialize_runtime(model):
    """
    ตั้งค่า runtime เครื่องมือหลัก

    Args:
        model: YOLO model object ที่โหลดเรียบร้อย
    """
    if "main_system" not in st.session_state:
        st.session_state.main_system = MainSystem(model, 0.5)

    if "unique_runtime" not in st.session_state:
        # สร้าง runtime_id จาก session
        runtime_id = st.session_state.get("runtime_id", "default")
        st.session_state.unique_runtime = UniqueRuntimeSystem(
            st.session_state.main_system,
            runtime_id
        )


def get_runtime():
    """ส่งคืน unique_runtime ปัจจุบัน"""
    if "unique_runtime" not in st.session_state:
        return None
    return st.session_state.unique_runtime


def get_main_system():
    """ส่งคืน main_system ปัจจุบัน"""
    if "main_system" not in st.session_state:
        return None
    return st.session_state.main_system


def clear_image_baskets():
    """ล้างไฟล์ที่อัปโหลด (ถ้าต้องการ reset)"""
    import shutil
    if os.path.exists("image_basket/input"):
        shutil.rmtree("image_basket/input")
    if os.path.exists("image_basket/output"):
        shutil.rmtree("image_basket/output")
    os.makedirs("image_basket/input", exist_ok=True)
    os.makedirs("image_basket/output", exist_ok=True)


def reset_session():
    """Reset ทั้ง session state (สำหรับปุ่ม Reset)"""
    for key in list(st.session_state.keys()):
        if key not in ["user_history"]:
            del st.session_state[key]
    clear_image_baskets()
