"""
streamlit_app.py — Steel Eye
ระบบ AI นับและแยกประเภทเหล็ก (เหล็กเส้น / เหล็กกล่อง)
"""

import streamlit as st
from ultralytics import YOLO
from PIL import Image
from core import MainSystem, UniqueRuntimeSystem
import os, time, io, zipfile, json
from datetime import datetime
from setup import setup_directories, setup_user_history
from state_manager import initialize_runtime
from auth import AuthManager

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Steel Eye",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* base */
.stApp { background: #0F1117; }
h1,h2,h3,h4 { color: #F0F0F0 !important; font-weight: 600; }
p, span, label, div { color: #C8C8C8 !important; }

/* buttons */
.stButton > button {
    background: #E07B00; color: #fff !important;
    border: none; border-radius: 6px;
    padding: 10px 22px; font-weight: 600; font-size: 14px;
    transition: background 0.2s;
}
.stButton > button:hover { background: #C06A00; }
.stDownloadButton > button {
    background: #1E6641; color: #fff !important;
    border: none; border-radius: 6px;
    padding: 10px 22px; font-weight: 600; font-size: 14px;
    transition: background 0.2s;
}
.stDownloadButton > button:hover { background: #174F33; }

/* cards */
.se-card {
    background: #1C1F27; border: 1px solid #2A2D36;
    border-radius: 10px; padding: 18px 20px; margin-bottom: 10px;
}
.se-stat-num { font-size: 32px; font-weight: 700; color: #F0F0F0 !important; margin: 0; line-height: 1; }
.se-stat-label { font-size: 12px; color: #777 !important; margin: 4px 0 0 0; }

/* chips */
.chip-bar { background:#E07B00; color:#fff !important; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:600; display:inline-block; }
.chip-rod { background:#2563EB; color:#fff !important; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:600; display:inline-block; }
.chip-ok  { background:#1E6641; color:#fff !important; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:600; display:inline-block; }

/* history table */
.hist-head {
    display: grid; grid-template-columns: 140px 1fr 120px 100px 80px;
    align-items: center; gap: 12px; padding: 8px 16px;
    background: #14161D; border-radius: 8px 8px 0 0;
    font-size: 11px; font-weight: 600; color: #555 !important;
    text-transform: uppercase; letter-spacing: 0.06em;
}
.hist-row {
    display: grid; grid-template-columns: 140px 1fr 120px 100px 80px;
    align-items: center; gap: 12px; padding: 10px 16px;
    border-bottom: 1px solid #252830; font-size: 13px;
}
.hist-row:hover { background: #1E2130; }

/* live dot */
.live-dot {
    display:inline-block; width:8px; height:8px; border-radius:50%;
    background:#EF4444; animation:blink 1.2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* notice box สำหรับคำแนะนำกล้อง */
.camera-guide {
    background: #1C1F27; border: 1px solid #3A3D4A;
    border-left: 3px solid #E07B00;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;
}
.camera-guide p { margin: 0; font-size: 13px; color: #C8C8C8 !important; }
.camera-guide .step { color: #E07B00 !important; font-weight: 700; }

/* page title */
.se-title {
    font-size: 22px; font-weight: 700; color: #F0F0F0 !important;
    border-left: 3px solid #E07B00; padding-left: 12px; margin-bottom: 20px;
}

/* login */
.login-wrap { max-width: 380px; margin: 60px auto 0; }
.login-logo { font-size: 36px; font-weight: 800; color: #E07B00 !important; letter-spacing: -1px; }
.login-sub  { font-size: 13px; color: #666 !important; margin: 4px 0 32px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# GLOBAL INIT
# ─────────────────────────────────────────────────────────────
auth = AuthManager("steel_eye_users.json")
setup_directories()
setup_user_history()

for _k, _v in {
    "authenticated": False, "username": None,
    "user_data": None, "model": None, "live_running": False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────
# MODEL HELPERS
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    for path in ["steel_model_yolo11/weights/best.pt", "weights/best.pt", "best.pt"]:
        if os.path.exists(path):
            try:
                return YOLO(path)
            except Exception as e:
                st.warning(f"โหลด {path} ไม่ได้: {e}")
    try:
        return YOLO("yolo11n.pt")
    except Exception as e:
        st.error(f"ไม่พบ model: {e}")
        return None


def ensure_runtime() -> bool:
    if not st.session_state.get("model"):
        st.session_state.model = load_model()
    if st.session_state.model is None:
        st.error("โหลด model ไม่ได้ — กรุณาตรวจสอบไฟล์ weight")
        return False
    if "main_system" not in st.session_state or "unique_runtime" not in st.session_state:
        initialize_runtime(st.session_state.model)
    return True


# ─────────────────────────────────────────────────────────────
# ANALYSIS RUNNERS
# ─────────────────────────────────────────────────────────────
def _collect_output_images(image_names: list, output_basket: str) -> list:
    """โหลดรูป annotated จาก output basket"""
    images = []
    for name in image_names:
        path = os.path.join(output_basket, name)
        if os.path.exists(path):
            try:
                images.append(Image.open(path).copy())
            except Exception:
                pass
    return images


def run_analysis_files(uploaded_files: list) -> tuple:
    """วิเคราะห์จากไฟล์ที่ upload → (list[PIL.Image], dict)"""
    if not ensure_runtime():
        raise RuntimeError("Runtime not ready")
    main_sys: MainSystem         = st.session_state.main_system
    runtime:  UniqueRuntimeSystem = st.session_state.unique_runtime

    file_names = []
    for uf in uploaded_files:
        dest = os.path.join(main_sys.input_basket, uf.name)
        with open(dest, "wb") as f:
            f.write(uf.getbuffer())
        file_names.append(uf.name)

    runtime.input_basket_tracker.clear()
    runtime.receive_image(file_names)
    runtime.predict()

    raw_names   = runtime.recall_newest_history_image()
    image_names = [n for n in raw_names if n != "avg_confident"]
    return _collect_output_images(image_names, main_sys.output_basket), runtime.get_newest_history()


def run_analysis_pil(pil_image: Image.Image, filename: str = "webcam_frame.jpg") -> tuple:
    """วิเคราะห์จาก PIL Image (ใช้กับกล้อง) → (list[PIL.Image], dict)"""
    if not ensure_runtime():
        raise RuntimeError("Runtime not ready")
    main_sys: MainSystem         = st.session_state.main_system
    runtime:  UniqueRuntimeSystem = st.session_state.unique_runtime

    if pil_image.mode in ("RGBA", "P"):
        pil_image = pil_image.convert("RGB")
    dest = os.path.join(main_sys.input_basket, filename)
    pil_image.save(dest, format="JPEG", quality=95)

    runtime.input_basket_tracker.clear()
    runtime.receive_image([filename])
    runtime.predict()

    raw_names   = runtime.recall_newest_history_image()
    image_names = [n for n in raw_names if n != "avg_confident"]
    return _collect_output_images(image_names, main_sys.output_basket), runtime.get_newest_history()


# ─────────────────────────────────────────────────────────────
# ZIP / HISTORY HELPERS
# ─────────────────────────────────────────────────────────────
def build_zip(images: list, result_dict: dict, label: str = "result") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, img in enumerate(images):
            try:
                if isinstance(img, str):
                    if os.path.exists(img):
                        ext = os.path.splitext(img)[1] or ".jpg"
                        with open(img, "rb") as f:
                            zf.writestr(f"{label}_{idx+1}{ext}", f.read())
                else:
                    ib = io.BytesIO()
                    img.save(ib, format="JPEG", quality=95)
                    zf.writestr(f"{label}_{idx+1}.jpg", ib.getvalue())
            except Exception:
                pass
        zf.writestr("results.json", json.dumps(result_dict, indent=2, ensure_ascii=False))
    buf.seek(0)
    return buf.getvalue()


def load_output_images_for_history(result_dict: dict) -> list:
    """โหลดรูป annotated จาก output basket สำหรับ history download"""
    output_dir = "image_basket/output"
    images = []
    for filename in result_dict.keys():
        if filename == "avg_confident":
            continue
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            try:
                images.append(Image.open(path).copy())
            except Exception:
                pass
    return images


def save_analysis(username: str, filename: str, raw: dict):
    """บันทึกผลลงประวัติ"""
    auth.save_user_analysis(username, {
        "filename":  filename,
        "results":   raw,
        "timestamp": datetime.now().isoformat(),
    })


# ─────────────────────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────────────────────
def _count_chips(counts: dict) -> str:
    """สร้าง HTML chip สำหรับแต่ละประเภทเหล็ก"""
    parts = []
    for cls, cnt in counts.items():
        css = "chip-bar" if "กล่อง" in cls else "chip-rod"
        parts.append(f'<span class="{css}">{cls}&nbsp;{cnt}</span>')
    return "&nbsp; ".join(parts) if parts else '<span class="chip-ok">ไม่พบเหล็ก</span>'


def render_result_stats(raw: dict):
    """แสดง card สรุปผลการนับแต่ละภาพ"""
    for img_name, det in raw.items():
        conf   = det.get("avg_confident", 0)
        counts = {k: v for k, v in det.items() if k != "avg_confident"}
        chips  = _count_chips(counts)
        total  = sum(counts.values())
        st.markdown(f"""
        <div class="se-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;">
                <div>
                    <p style="font-size:12px;color:#666!important;margin:0 0 6px 0;">{img_name}</p>
                    <div>{chips}</div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <p class="se-stat-num">{total}</p>
                    <p class="se-stat-label">ชิ้นรวม</p>
                    <p style="font-size:11px;color:#555!important;margin:6px 0 0 0;">ความแม่นยำ {conf:.0%}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_result_block(result_imgs: list, result_raw: dict, key_prefix: str):
    """แสดงรูป annotated + stats card + ปุ่ม download"""
    st.divider()
    st.markdown('<p class="se-title">ผลการตรวจนับ</p>', unsafe_allow_html=True)
    img_col, stat_col = st.columns([1.4, 0.6])

    with img_col:
        if result_imgs:
            cols = st.columns(min(len(result_imgs), 3))
            for idx, img in enumerate(result_imgs):
                with cols[idx % 3]:
                    st.image(img, use_container_width=True)
        else:
            st.info("ไม่มีรูป output")

        zip_bytes = build_zip(result_imgs, result_raw, key_prefix)
        st.download_button(
            label="ดาวน์โหลดผล (ZIP)",
            data=zip_bytes,
            file_name=f"steel_eye_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            key=f"dl_{key_prefix}_{id(result_raw)}",
            use_container_width=True,
        )

    with stat_col:
        render_result_stats(result_raw)


# ─────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────
def show_login_page():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        st.markdown('<p class="login-logo">Steel Eye</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-sub">ระบบ AI นับและแยกประเภทเหล็ก</p>', unsafe_allow_html=True)

        tab_in, tab_reg = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])

        with tab_in:
            uname = st.text_input("ชื่อผู้ใช้", placeholder="Username", key="login_uname")
            pwd   = st.text_input("รหัสผ่าน",   type="password", placeholder="Password", key="login_pwd")
            if st.button("เข้าสู่ระบบ", use_container_width=True, key="btn_login"):
                if uname and pwd:
                    res = auth.login(uname, pwd)
                    if res["success"]:
                        st.session_state.authenticated = True
                        st.session_state.username      = uname
                        st.session_state.user_data     = res["user_data"]
                        st.rerun()
                    else:
                        st.error(res["message"])
                else:
                    st.warning("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")

        with tab_reg:
            ru = st.text_input("ชื่อผู้ใช้",    placeholder="เลือก username",     key="reg_u")
            rp = st.text_input("รหัสผ่าน",      type="password", placeholder="อย่างน้อย 6 ตัว", key="reg_p")
            rf = st.text_input("ชื่อ-นามสกุล", placeholder="ชื่อของคุณ",          key="reg_f")
            if st.button("สมัครสมาชิก", use_container_width=True, key="btn_reg"):
                if ru and rp and rf:
                    res = auth.register(ru, rp, rf)
                    if res["success"]:
                        st.success("สมัครสำเร็จ — กรุณาเข้าสู่ระบบ")
                    else:
                        st.error(res["message"])
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบ")

        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CAMERA MODES
# ─────────────────────────────────────────────────────────────
def _render_snapshot_mode(result_key_imgs: str, result_key_raw: str, page_label: str):
    """
    โหมดถ่ายภาพ — user กดปุ่มกล้องใน widget แล้วกด 'ตรวจนับ'
    แสดงคำแนะนำให้ชัดเจนว่าต้องทำอะไร
    """
    st.markdown("""
    <div class="camera-guide">
        <p><span class="step">วิธีใช้</span> &nbsp;
        1. กดปุ่ม <b>Take photo</b> ในกล้องด้านล่าง &nbsp;→&nbsp;
        2. กดปุ่ม <b>ตรวจนับ</b> เพื่อวิเคราะห์</p>
    </div>
    """, unsafe_allow_html=True)

    cam_img = st.camera_input(
        "กดปุ่ม Take photo เพื่อถ่ายภาพ",
        key=f"{page_label}_snap_input",
    )

    if cam_img is None:
        st.caption("หากกล้องไม่ขึ้น ให้อนุญาต Camera permission ในเบราว์เซอร์")
        st.session_state.pop(result_key_imgs, None)
        st.session_state.pop(result_key_raw,  None)
        return

    # มีภาพแล้ว — แสดงปุ่ม ตรวจนับ
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        if st.button("ตรวจนับ", use_container_width=True, key=f"{page_label}_snap_btn"):
            with st.spinner("กำลังประมวลผล..."):
                try:
                    fname = f"snap_{page_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    imgs, raw = run_analysis_pil(Image.open(cam_img), fname)
                    st.session_state[result_key_imgs] = imgs
                    st.session_state[result_key_raw]  = raw
                    save_analysis(st.session_state.username, fname, raw)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    # แสดงผล
    if st.session_state.get(result_key_imgs) is not None and \
            st.session_state.get(result_key_raw) is not None:
        render_result_block(
            st.session_state[result_key_imgs],
            st.session_state[result_key_raw],
            f"{page_label}_snap",
        )


def _render_live_mode(result_key_imgs: str, result_key_raw: str, page_label: str):
    """
    โหมด Live — กล้องถ่ายต่อเนื่อง วิเคราะห์อัตโนมัติทุก N วินาที
    user ต้องกด Take photo ใน widget ทุกรอบ (ข้อจำกัดของ st.camera_input)
    แสดงคำแนะนำให้ชัดเพื่อไม่ให้สับสน
    """
    # Live badge
    st.markdown("""
    <div style="display:inline-flex;align-items:center;gap:8px;
                background:#1C1F27;border:1px solid #3A1515;
                border-radius:8px;padding:8px 14px;margin-bottom:4px;">
        <span class="live-dot"></span>
        <span style="font-size:13px;font-weight:600;color:#EF4444!important;">LIVE</span>
        <span style="font-size:12px;color:#888!important;">โหมดวิเคราะห์ต่อเนื่อง</span>
    </div>
    """, unsafe_allow_html=True)

    # คำแนะนำ
    st.markdown("""
    <div class="camera-guide">
        <p><span class="step">วิธีใช้</span> &nbsp;
        1. กด <b>เริ่ม</b> &nbsp;→&nbsp;
        2. กดปุ่ม <b>Take photo</b> ในกล้องด้านล่าง &nbsp;→&nbsp;
        3. ระบบวิเคราะห์อัตโนมัติ ทำซ้ำได้เรื่อยๆ &nbsp;→&nbsp;
        4. กด <b>หยุด</b> เมื่อเสร็จ</p>
        <p style="margin:6px 0 0 0;font-size:12px;color:#666!important;">
        หมายเหตุ: ต้องกด Take photo ทุกรอบเนื่องจากข้อจำกัดของเบราว์เซอร์
        — ระบบจะวิเคราะห์ให้อัตโนมัติหลังกด</p>
    </div>
    """, unsafe_allow_html=True)

    interval = st.slider(
        "ความถี่วิเคราะห์ (วินาที/ครั้ง)", 1, 10, 3,
        key=f"{page_label}_live_interval",
    )

    col_s, col_e = st.columns(2)
    with col_s:
        if st.button("เริ่ม", use_container_width=True,
                     key=f"{page_label}_live_start",
                     disabled=st.session_state.live_running):
            st.session_state.live_running = True
            st.rerun()
    with col_e:
        if st.button("หยุด", use_container_width=True,
                     key=f"{page_label}_live_stop",
                     disabled=not st.session_state.live_running):
            st.session_state.live_running = False
            st.rerun()

    frame_ph  = st.empty()
    stats_ph  = st.empty()
    status_ph = st.empty()

    if not st.session_state.live_running:
        # หยุดอยู่ — แสดงผลล่าสุดถ้ามี
        if st.session_state.get(result_key_imgs):
            frame_ph.image(
                st.session_state[result_key_imgs],
                use_container_width=True,
                caption="ผลล่าสุด",
            )
        else:
            status_ph.info("กด 'เริ่ม' เพื่อเริ่มวิเคราะห์")
        return

    # กำลัง live อยู่
    status_ph.info("กำลังรอภาพ — กด Take photo ในกล้องด้านล่าง")

    # key เปลี่ยนทุก interval วินาที → Streamlit reset widget → รับภาพใหม่ได้
    live_frame = st.camera_input(
        "กด Take photo เพื่อส่งภาพวิเคราะห์",
        key=f"{page_label}_live_cam_{int(time.time() // interval)}",
    )

    if live_frame is not None:
        try:
            fname = f"live_{page_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            imgs, raw = run_analysis_pil(Image.open(live_frame), fname)

            # แสดงรูป annotated
            with frame_ph.container():
                if imgs:
                    c = st.columns(min(len(imgs), 3))
                    for i, img in enumerate(imgs):
                        with c[i % 3]:
                            st.image(img, use_container_width=True)
                else:
                    st.image(Image.open(live_frame), use_container_width=True)

            # แสดง stats
            with stats_ph.container():
                render_result_stats(raw)

            status_ph.success(
                f"วิเคราะห์เสร็จ {datetime.now().strftime('%H:%M:%S')} "
                f"— กด Take photo อีกครั้งเพื่อวิเคราะห์รอบถัดไป"
            )

            # บันทึกเฉพาะรอบที่พบเหล็ก
            has_steel = any(
                any(k != "avg_confident" for k in det)
                for det in raw.values()
            )
            if has_steel:
                save_analysis(st.session_state.username, fname, raw)
                st.session_state[result_key_imgs] = imgs
                st.session_state[result_key_raw]  = raw

        except Exception as e:
            status_ph.error(f"เกิดข้อผิดพลาด: {e}")

    # rerun หลัง interval เพื่อ reset camera widget ให้ถ่ายรูปใหม่ได้
    time.sleep(interval)
    st.rerun()


def render_camera_section(result_key_imgs: str, result_key_raw: str, page_label: str):
    """entry point สำหรับ section กล้อง — เลือก mode แล้ว dispatch"""
    mode = st.radio(
        "เลือกโหมด",
        ["ถ่ายภาพ", "สตรีมสด"],
        horizontal=True,
        key=f"{page_label}_cam_mode",
        captions=["ถ่ายครั้งเดียว กด ตรวจนับ", "วิเคราะห์ต่อเนื่องอัตโนมัติ"],
    )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if mode == "ถ่ายภาพ":
        _render_snapshot_mode(result_key_imgs, result_key_raw, page_label)
    else:
        _render_live_mode(result_key_imgs, result_key_raw, page_label)


# ─────────────────────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────────────────────
def page_home():
    st.markdown('<p class="se-title">ตรวจนับเหล็ก</p>', unsafe_allow_html=True)

    input_mode = st.radio(
        "วิธีนำเข้าภาพ",
        ["อัปโหลดไฟล์", "ถ่ายภาพ", "สตรีมสด"],
        horizontal=True,
        key="home_input_mode",
        captions=["เลือกไฟล์จากเครื่อง", "ถ่ายครั้งเดียว", "วิเคราะห์ต่อเนื่อง"],
    )

    if input_mode == "อัปโหลดไฟล์":
        uploaded_files = st.file_uploader(
            "เลือกรูป PNG/JPG (เลือกได้หลายรูป)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="home_uploader",
        )

        # ล้างผลเก่าถ้ายังไม่มีไฟล์
        if not uploaded_files:
            st.session_state.pop("home_result_images", None)
            st.session_state.pop("home_result_raw",    None)
            return

        # preview
        st.caption(f"เลือก {len(uploaded_files)} ไฟล์")
        prev_cols = st.columns(min(len(uploaded_files), 4))
        for idx, uf in enumerate(uploaded_files):
            with prev_cols[idx % 4]:
                st.image(uf, caption=uf.name, use_container_width=True)

        _, btn_col, _ = st.columns([1, 1, 1])
        with btn_col:
            if st.button("ตรวจนับ", use_container_width=True, key="home_btn_analyze"):
                with st.spinner("กำลังประมวลผล..."):
                    try:
                        imgs, raw = run_analysis_files(uploaded_files)
                        st.session_state.home_result_images = imgs
                        st.session_state.home_result_raw    = raw
                        save_analysis(
                            st.session_state.username,
                            ", ".join(f.name for f in uploaded_files),
                            raw,
                        )
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

        if st.session_state.get("home_result_images") is not None and \
                st.session_state.get("home_result_raw") is not None:
            render_result_block(
                st.session_state["home_result_images"],
                st.session_state["home_result_raw"],
                "home_upload",
            )

    else:
        # ถ่ายภาพ หรือ สตรีมสด — ส่งตรงไป render_camera_section พร้อม force mode
        forced_mode = "ถ่ายภาพ" if input_mode == "ถ่ายภาพ" else "สตรีมสด"

        # สร้าง radio hidden ที่ค่าถูก force แล้ว (ป้องกัน key ชน)
        if forced_mode == "ถ่ายภาพ":
            _render_snapshot_mode("home_result_images", "home_result_raw", "home")
        else:
            _render_live_mode("home_result_images", "home_result_raw", "home")


def page_history():
    st.markdown('<p class="se-title">ประวัติการตรวจนับ</p>', unsafe_allow_html=True)

    # ── filter ──
    f1, f2, f3 = st.columns([2, 1.5, 1.5])
    with f1:
        filter_type = st.selectbox(
            "ช่วงเวลา",
            ["ทั้งหมด", "7 วันล่าสุด", "30 วันล่าสุด", "กำหนดเอง"],
            label_visibility="collapsed",
        )
    with f2:
        start_date = st.date_input("วันเริ่มต้น") if filter_type == "กำหนดเอง" else None
    with f3:
        end_date = st.date_input("วันสิ้นสุด") if filter_type == "กำหนดเอง" else None

    if filter_type == "ทั้งหมด":
        analyses = auth.get_user_analyses(st.session_state.username)
    elif filter_type == "7 วันล่าสุด":
        analyses = auth.get_user_analyses(st.session_state.username, days=7)
    elif filter_type == "30 วันล่าสุด":
        analyses = auth.get_user_analyses(st.session_state.username, days=30)
    elif filter_type == "กำหนดเอง" and start_date and end_date:
        analyses = auth.get_user_analyses_by_date_range(
            st.session_state.username,
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date,   datetime.max.time()),
        )
    else:
        analyses = []

    if not analyses:
        st.markdown(
            '<div class="se-card" style="text-align:center;padding:40px;">'
            '<p style="color:#555!important;">ยังไม่มีประวัติในช่วงเวลานี้</p></div>',
            unsafe_allow_html=True,
        )
        return

    # ── summary cards ──
    total_bar = total_rod = 0
    for _, ad in analyses:
        for det in ad.get("data", {}).get("results", {}).values():
            for k, v in det.items():
                if k == "avg_confident":
                    continue
                if "กล่อง" in k:
                    total_bar += v
                elif "เส้น" in k:
                    total_rod += v

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="se-card"><p class="se-stat-num">{len(analyses)}</p>'
                    '<p class="se-stat-label">ครั้งที่ตรวจ</p></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="se-card"><p class="se-stat-num" style="color:#E07B00!important;">{total_bar}</p>'
                    '<p class="se-stat-label">เหล็กกล่องรวม (ชิ้น)</p></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="se-card"><p class="se-stat-num" style="color:#2563EB!important;">{total_rod}</p>'
                    '<p class="se-stat-label">เหล็กเส้นรวม (ชิ้น)</p></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── table ──
    st.markdown("""
    <div class="hist-head">
        <span>วันที่ / เวลา</span><span>ไฟล์</span>
        <span>เหล็กกล่อง</span><span>เหล็กเส้น</span><span>ความแม่นยำ</span>
    </div>
    """, unsafe_allow_html=True)

    for ts, analysis_data in analyses:
        record   = analysis_data.get("data", {})
        filename = record.get("filename", "—")
        results  = record.get("results", {})

        bar_cnt = rod_cnt = 0
        conf_vals = []
        for det in results.values():
            c = det.get("avg_confident", 0)
            if c > 0:
                conf_vals.append(c)
            for k, v in det.items():
                if k == "avg_confident":
                    continue
                if "กล่อง" in k:
                    bar_cnt += v
                elif "เส้น" in k:
                    rod_cnt += v

        avg_conf    = sum(conf_vals) / len(conf_vals) if conf_vals else 0
        date_str    = datetime.fromisoformat(ts).strftime("%d/%m/%y %H:%M")
        fname_short = filename if len(filename) <= 30 else filename[:27] + "…"
        bar_cell    = f'<span class="chip-bar">{bar_cnt}</span>' if bar_cnt else '<span style="color:#444!important;">—</span>'
        rod_cell    = f'<span class="chip-rod">{rod_cnt}</span>'  if rod_cnt else '<span style="color:#444!important;">—</span>'

        st.markdown(f"""
        <div class="hist-row">
            <span style="color:#999!important;font-size:12px;">{date_str}</span>
            <span style="color:#C8C8C8!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                  title="{filename}">{fname_short}</span>
            <span>{bar_cell}</span>
            <span>{rod_cell}</span>
            <span style="color:#888!important;">{avg_conf:.0%}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── download รายการล่าสุด ──
    last_ts, last_ad = analyses[0]
    last_results = last_ad.get("data", {}).get("results", {})
    saved_imgs   = load_output_images_for_history(last_results)
    c_dl, _ = st.columns([1, 3])
    with c_dl:
        st.download_button(
            label="ดาวน์โหลดล่าสุด (ZIP)",
            data=build_zip(saved_imgs, last_results, "history_latest"),
            file_name=f"steel_eye_{last_ts[:10]}.zip",
            mime="application/zip",
            key="dl_hist_latest",
            use_container_width=True,
        )

    # ── download ทีละรายการ ──
    with st.expander("ดาวน์โหลดรายการอื่น"):
        for ts, analysis_data in analyses:
            record     = analysis_data.get("data", {})
            filename   = record.get("filename", "—")
            results    = record.get("results", {})
            dt_obj     = datetime.fromisoformat(ts)
            saved_imgs = load_output_images_for_history(results)
            img_note   = f"{len(saved_imgs)} ภาพ" if saved_imgs else "JSON only"
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(f"{dt_obj.strftime('%d/%m/%y %H:%M')}  —  {filename}")
            with c2:
                st.caption(img_note)
            with c3:
                st.download_button(
                    label="โหลด ZIP",
                    data=build_zip(saved_imgs, results, f"history_{ts[:10]}"),
                    file_name=f"steel_eye_{ts[:10]}_{ts[11:13]}{ts[14:16]}.zip",
                    mime="application/zip",
                    key=f"dl_hist_{ts}",
                    use_container_width=True,
                )


def page_settings():
    st.markdown('<p class="se-title">ตั้งค่าบัญชี</p>', unsafe_allow_html=True)

    col_acc, col_pwd = st.columns(2)
    udata = st.session_state.user_data

    with col_acc:
        st.markdown("#### ข้อมูลบัญชี")
        st.markdown(f"""
        <div class="se-card">
            <p style="color:#888!important;font-size:12px;margin:0 0 2px;">ชื่อผู้ใช้</p>
            <p style="color:#F0F0F0!important;margin:0 0 12px;font-weight:600;">{st.session_state.username}</p>
            <p style="color:#888!important;font-size:12px;margin:0 0 2px;">ชื่อ-นามสกุล</p>
            <p style="color:#F0F0F0!important;margin:0 0 12px;font-weight:600;">{udata['full_name']}</p>
            <p style="color:#888!important;font-size:12px;margin:0 0 2px;">สมัครเมื่อ</p>
            <p style="color:#F0F0F0!important;margin:0;font-weight:600;">{udata['created_at'][:10]}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_pwd:
        st.markdown("#### เปลี่ยนรหัสผ่าน")
        old_p  = st.text_input("รหัสผ่านเดิม",      type="password", key="pwd_old")
        new_p  = st.text_input("รหัสผ่านใหม่",       type="password", key="pwd_new")
        conf_p = st.text_input("ยืนยันรหัสผ่านใหม่", type="password", key="pwd_conf")
        if st.button("บันทึก", use_container_width=True, key="btn_update_pwd"):
            if not (old_p and new_p and conf_p):
                st.warning("กรุณากรอกข้อมูลให้ครบ")
            elif new_p != conf_p:
                st.error("รหัสผ่านใหม่ไม่ตรงกัน")
            else:
                res = auth.change_password(st.session_state.username, old_p, new_p)
                if res["success"]:
                    st.success("เปลี่ยนรหัสผ่านสำเร็จ")
                else:
                    st.error(res["message"])


# ─────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────
def show_main_app():
    # ── sidebar ──
    with st.sidebar:
        udata = st.session_state.user_data
        st.markdown(f"""
        <div class="se-card" style="margin-bottom:16px;">
            <p style="font-weight:700;font-size:15px;color:#F0F0F0!important;margin:0;">{udata['full_name']}</p>
            <p style="font-size:12px;color:#555!important;margin:4px 0 0 0;">@{st.session_state.username}</p>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio("เมนู", ["หน้าหลัก", "ประวัติ", "ตั้งค่า"], label_visibility="collapsed")
        st.divider()

        all_analyses = auth.get_user_analyses(st.session_state.username)
        today_count  = sum(
            1 for ts, _ in all_analyses
            if datetime.fromisoformat(ts).date() == datetime.now().date()
        )
        st.markdown(f"""
        <div style="padding:0 4px;">
            <p style="font-size:11px;color:#555!important;margin:0 0 2px;">วันนี้</p>
            <p style="font-size:22px;font-weight:700;color:#E07B00!important;margin:0;">{today_count}</p>
            <p style="font-size:11px;color:#555!important;margin:6px 0 2px;">ทั้งหมด</p>
            <p style="font-size:16px;font-weight:600;color:#C8C8C8!important;margin:0;">{len(all_analyses)}</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        if st.button("ออกจากระบบ", use_container_width=True, key="btn_logout"):
            st.session_state.live_running = False
            for k in ["authenticated", "username", "user_data", "model",
                      "main_system", "unique_runtime", "live_running",
                      "home_result_images", "home_result_raw"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── header ──
    st.markdown(
        '<h2 style="color:#E07B00!important;font-size:26px;font-weight:800;'
        'letter-spacing:-0.5px;margin-bottom:24px;">Steel Eye</h2>',
        unsafe_allow_html=True,
    )

    # ── route ──
    if page == "หน้าหลัก":
        page_home()
    elif page == "ประวัติ":
        page_history()
    elif page == "ตั้งค่า":
        page_settings()


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
def main():
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()