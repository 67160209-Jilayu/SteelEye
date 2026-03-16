import streamlit as st
from ultralytics import YOLO
from PIL import Image
from core import MainSystem, UniqueRuntimeSystem
import os, io, zipfile, json, re
from datetime import datetime
from setup import setup_directories, setup_user_history
from state_manager import initialize_runtime
from auth import AuthManager

st.set_page_config(page_title="Steel Eye", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

MAX_FILE_SIZE_MB = 10
MAX_FILES = 10

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
*, *::before, *::after { box-sizing: border-box; }
.stApp { background: #0d0d0d; font-family: 'DM Sans', -apple-system, sans-serif; }
section[data-testid="stSidebar"] { background: #0a0a0a; border-right: 0.5px solid rgba(255,255,255,0.06); }
section[data-testid="stSidebar"] > div { padding: 24px 16px; }
.stRadio > div { gap: 2px; }
.stRadio label { background: transparent; border-radius: 8px; padding: 8px 12px; font-size: 13px; color: rgba(240,240,240,0.4) !important; transition: color .15s, background .15s; cursor: pointer; }
.stRadio label:hover { color: rgba(240,240,240,0.8) !important; background: rgba(255,255,255,0.04); }
.stButton > button { background: #E07B00 !important; color: #fff !important; border: none; border-radius: 9px; padding: 11px 20px; font-size: 13px; font-weight: 600; font-family: 'DM Sans', sans-serif; letter-spacing: -0.1px; transition: opacity .15s, transform .1s; width: 100%; }
.stButton > button:hover { opacity: .88; border: none; }
.stButton > button:active { transform: scale(.98); }
.stButton > button:disabled { opacity: 0.35 !important; cursor: not-allowed; }
.stDownloadButton > button { background: rgba(255,255,255,0.05) !important; color: rgba(240,240,240,0.7) !important; border: 0.5px solid rgba(255,255,255,0.1) !important; border-radius: 9px; padding: 11px 20px; font-size: 13px; font-weight: 500; font-family: 'DM Sans', sans-serif; transition: background .15s; }
.stDownloadButton > button:hover { background: rgba(255,255,255,0.08) !important; }
.stTextInput input { background: rgba(255,255,255,0.04) !important; border: 0.5px solid rgba(255,255,255,0.08) !important; border-radius: 8px; color: #f0f0f0 !important; font-family: 'DM Sans', sans-serif; font-size: 13px; padding: 10px 12px; transition: border-color .15s, background .15s; }
.stTextInput input:focus { border-color: rgba(224,123,0,0.5) !important; background: rgba(224,123,0,0.03) !important; box-shadow: none !important; }
.stTextInput label { font-size: 11px !important; color: rgba(240,240,240,0.35) !important; letter-spacing: 0.04em; }
.stFileUploader { background: rgba(255,255,255,0.02); border: 0.5px dashed rgba(255,255,255,0.1); border-radius: 12px; padding: 8px; transition: border-color .2s, background .2s; }
.stFileUploader:hover { border-color: rgba(224,123,0,0.4); background: rgba(224,123,0,0.02); }
.stFileUploader label { color: rgba(240,240,240,0.5) !important; font-size: 13px !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 0.5px solid rgba(255,255,255,0.06); gap: 0; }
.stTabs [data-baseweb="tab"] { background: transparent; color: rgba(240,240,240,0.35) !important; font-size: 13px; font-weight: 500; padding: 10px 16px; border-bottom: 1.5px solid transparent; transition: color .15s; }
.stTabs [aria-selected="true"] { color: #f0f0f0 !important; border-bottom-color: #E07B00 !important; background: transparent !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 20px 0 0; }
div[data-testid="stHorizontalRadio"] > div { background: rgba(255,255,255,0.04); border-radius: 9px; padding: 3px; width: fit-content; gap: 0 !important; display: flex; }
div[data-testid="stHorizontalRadio"] div[role="radiogroup"] label { border-radius: 7px !important; padding: 6px 18px !important; background: transparent !important; gap: 0 !important; }
div[data-testid="stHorizontalRadio"] div[role="radiogroup"] label::before { display: none !important; }
div[data-testid="stHorizontalRadio"] div[data-baseweb="radio"]:has(input:checked) label { background: rgba(255,255,255,0.10) !important; }
.stSelectbox > div > div { background: rgba(255,255,255,0.04) !important; border: 0.5px solid rgba(255,255,255,0.08) !important; border-radius: 8px; color: #f0f0f0 !important; font-size: 13px; }
.stAlert { border-radius: 8px; font-size: 13px; border: none; }
.stSpinner > div { border-top-color: #E07B00 !important; }
.stDivider { border-color: rgba(255,255,255,0.06) !important; }
.stImage img { border-radius: 8px; }
.stCaption { color: rgba(240,240,240,0.3) !important; font-size: 12px !important; }
h1,h2,h3,h4 { color: #f0f0f0 !important; }
p, span, label, div { color: #c8c8c8; }
.streamlit-expanderHeader { background: rgba(255,255,255,0.03) !important; border: 0.5px solid rgba(255,255,255,0.07) !important; border-radius: 8px !important; font-size: 13px !important; color: rgba(240,240,240,0.5) !important; }
.streamlit-expanderContent { border: 0.5px solid rgba(255,255,255,0.07) !important; border-top: none !important; background: rgba(255,255,255,0.01) !important; }
.stCameraInput > div { border: 0.5px solid rgba(255,255,255,0.1) !important; border-radius: 12px !important; background: #1a1a1a !important; }
.brand { display:flex; align-items:center; gap:8px; padding:0 4px 20px; border-bottom:0.5px solid rgba(255,255,255,0.06); margin-bottom:16px; }
.brand-dot { width:6px; height:6px; border-radius:50%; background:#E07B00; flex-shrink:0; }
.brand-name { font-size:14px; font-weight:600; color:#f0f0f0 !important; letter-spacing:-0.2px; }
.user-info { padding-top:16px; border-top:0.5px solid rgba(255,255,255,0.07); }
.user-name { font-size:13px; font-weight:500; color:#f0f0f0 !important; }
.user-handle { font-size:11px; color:rgba(240,240,240,0.25) !important; margin-top:2px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }
.page-title { font-size:18px; font-weight:600; color:#f0f0f0 !important; letter-spacing:-0.4px; margin:0 0 20px 0; }
.today-badge { font-size:12px; color:rgba(240,240,240,0.45) !important; background:rgba(255,255,255,0.05); border:0.5px solid rgba(255,255,255,0.1); border-radius:20px; padding:4px 12px; white-space:nowrap; }
.stat-cards-row { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px; }
.stat-card-item { background:#141414; border:0.5px solid rgba(255,255,255,0.07); border-radius:10px; padding:14px 16px; display:flex; flex-direction:column; gap:10px; }
.stat-card-line { height:2.5px; border-radius:2px; width:36px; }
.stat-card-label { font-size:12px; color:rgba(240,240,240,0.45) !important; }
.stat-card-num { font-size:22px; font-weight:700; letter-spacing:-0.5px; line-height:1; }
.result-card { background:#141414; border:0.5px solid rgba(255,255,255,0.07); border-radius:10px; padding:16px 18px; margin-bottom:8px; }
.result-filename { font-size:11px; color:rgba(240,240,240,0.3) !important; margin-bottom:10px; }
.result-row { display:flex; justify-content:space-between; align-items:flex-end; }
.result-tags { display:flex; gap:6px; flex-wrap:wrap; }
.tag { font-size:11px; font-weight:500; padding:3px 9px; border-radius:4px; display:inline-block; letter-spacing:-0.1px; }
.tag-bar { background:rgba(224,123,0,0.12); color:#E07B00 !important; }
.tag-rod { background:rgba(78,156,255,0.1); color:#4e9cff !important; }
.tag-none { background:rgba(255,255,255,0.05); color:rgba(240,240,240,0.3) !important; }
.result-total { text-align:right; }
.result-num { font-size:30px; font-weight:700; color:#f0f0f0 !important; line-height:1; letter-spacing:-1px; }
.result-conf { font-size:11px; color:rgba(240,240,240,0.25) !important; margin-top:3px; }
.section-title { font-size:11px; color:rgba(240,240,240,0.25) !important; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:12px; }
.summary-row { display:flex; gap:10px; margin-bottom:20px; }
.summary-card { flex:1; background:#141414; border:0.5px solid rgba(255,255,255,0.07); border-radius:10px; padding:14px 16px; }
.summary-n { font-size:26px; font-weight:700; line-height:1; letter-spacing:-0.8px; }
.summary-l { font-size:11px; color:rgba(240,240,240,0.3) !important; margin-top:4px; }
.n-white { color:#f0f0f0 !important; } .n-orange { color:#E07B00 !important; } .n-blue { color:#4e9cff !important; }
.hist-table { border:0.5px solid rgba(255,255,255,0.06); border-radius:10px; overflow:hidden; }
.hist-head { display:grid; grid-template-columns:130px 1fr 100px 100px 64px; gap:12px; padding:9px 16px; background:rgba(255,255,255,0.03); font-size:10px; font-weight:500; color:rgba(240,240,240,0.25) !important; letter-spacing:0.06em; text-transform:uppercase; }
.hist-row { display:grid; grid-template-columns:130px 1fr 100px 100px 64px; gap:12px; padding:11px 16px; border-top:0.5px solid rgba(255,255,255,0.05); font-size:13px; transition:background .1s; }
.hist-row:hover { background:rgba(255,255,255,0.02); }
.hist-time { color:rgba(240,240,240,0.35) !important; font-size:12px; font-variant-numeric:tabular-nums; }
.hist-file { color:#f0f0f0 !important; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hist-conf { color:rgba(240,240,240,0.3) !important; font-size:12px; font-variant-numeric:tabular-nums; }
.cam-tip { background:rgba(224,123,0,0.06); border:0.5px solid rgba(224,123,0,0.15); border-radius:8px; padding:11px 14px; font-size:13px; color:rgba(240,240,240,0.6) !important; margin-bottom:16px; }
.acct-row { display:flex; justify-content:space-between; align-items:center; padding:13px 0; border-bottom:0.5px solid rgba(255,255,255,0.05); }
.acct-key { font-size:12px; color:rgba(240,240,240,0.35) !important; }
.acct-val { font-size:13px; font-weight:500; color:#f0f0f0 !important; }
.pwd-bar-wrap { margin:4px 0 10px; }
.pwd-bar-track { height:3px; background:rgba(255,255,255,0.07); border-radius:2px; }
.pwd-bar-fill { height:3px; border-radius:2px; transition:width .25s, background .25s; }
.pwd-hint { font-size:11px; margin-top:4px; }
.match-ok { font-size:11px; color:#4ade80 !important; }
.match-no { font-size:11px; color:#f87171 !important; }
.login-title { font-size:22px; font-weight:700; color:#f0f0f0 !important; letter-spacing:-0.7px; margin-bottom:3px; }
.login-sub { font-size:13px; color:rgba(240,240,240,0.28) !important; margin-bottom:28px; }
.empty-state { text-align:center; padding:48px 24px; color:rgba(240,240,240,0.2) !important; font-size:13px; }
.about-hero { background:linear-gradient(135deg,rgba(224,123,0,0.08) 0%,rgba(255,255,255,0.02) 100%); border:0.5px solid rgba(224,123,0,0.12); border-radius:14px; padding:28px 24px; margin-bottom:24px; display:flex; flex-direction:column; gap:6px; }
.about-hero-dot { width:8px; height:8px; border-radius:50%; background:#E07B00; margin-bottom:4px; }
.about-hero-title { font-size:28px; font-weight:700; color:#f0f0f0 !important; letter-spacing:-0.8px; line-height:1; }
.about-hero-sub { font-size:14px; color:rgba(240,240,240,0.4) !important; margin-top:2px; }
.about-section { margin-bottom:10px; }
.about-section-label { font-size:10px; font-weight:600; color:rgba(240,240,240,0.25) !important; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:10px; }
.about-body { font-size:14px; color:rgba(240,240,240,0.6) !important; line-height:1.7; margin:0; }
.about-body b { color:rgba(240,240,240,0.85) !important; font-weight:500; }
.about-tags-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }
.about-tag { background:rgba(255,255,255,0.04); border:0.5px solid rgba(255,255,255,0.08); border-radius:6px; padding:5px 11px; font-size:12px; color:rgba(240,240,240,0.45) !important; }
.how-list { display:flex; flex-direction:column; gap:2px; }
.how-step { display:flex; gap:16px; padding:14px 16px; border-radius:10px; transition:background .15s; }
.how-step:hover { background:rgba(255,255,255,0.02); }
.how-num { width:28px; height:28px; border-radius:8px; background:rgba(224,123,0,0.12); color:#E07B00 !important; font-size:13px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.how-content { flex:1; }
.how-title { font-size:13px; font-weight:600; color:#f0f0f0 !important; margin-bottom:3px; }
.how-desc { font-size:12px; color:rgba(240,240,240,0.4) !important; line-height:1.6; }
.how-desc b { color:rgba(240,240,240,0.65) !important; font-weight:500; }
.tips-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px; }
.tip-card { background:#141414; border:0.5px solid rgba(255,255,255,0.07); border-radius:10px; padding:14px; }
.tip-icon { font-size:20px; margin-bottom:8px; }
.tip-text { font-size:12px; color:rgba(240,240,240,0.45) !important; line-height:1.6; }
.tip-text b { color:rgba(240,240,240,0.75) !important; font-weight:500; display:block; margin-bottom:2px; }
</style>
""", unsafe_allow_html=True)

auth = AuthManager("steel_eye_users.json")
setup_directories()
setup_user_history()

for k, v in {"authenticated": False, "username": None, "user_data": None, "model": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


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
        st.error("โหลด model ไม่ได้")
        return False
    if "main_system" not in st.session_state or "unique_runtime" not in st.session_state:
        initialize_runtime(st.session_state.model)
    return True


def validate_files(files) -> tuple[bool, str]:
    if not files:
        return False, "กรุณาเลือกไฟล์"
    if len(files) > MAX_FILES:
        return False, f"อัปโหลดได้สูงสุด {MAX_FILES} ไฟล์ต่อครั้ง"
    for f in files:
        if os.path.splitext(f.name)[1].lower() not in {".jpg", ".jpeg", ".png"}:
            return False, f"'{f.name}' ไม่รองรับ"
        if f.size / 1024 / 1024 > MAX_FILE_SIZE_MB:
            return False, f"'{f.name}' ขนาดเกิน {MAX_FILE_SIZE_MB} MB"
        hdr = f.read(12); f.seek(0)
        if not (hdr[:3] == b'\xff\xd8\xff' or hdr[:8] == b'\x89PNG\r\n\x1a\n'):
            return False, f"'{f.name}' ไม่ใช่รูปภาพที่ถูกต้อง"
    return True, ""


def _collect_outputs(names, basket):
    imgs = []
    for n in names:
        p = os.path.join(basket, n)
        if os.path.exists(p):
            try: imgs.append(Image.open(p).copy())
            except: pass
    return imgs


def run_files(files):
    if not ensure_runtime(): raise RuntimeError("Runtime not ready")
    ms = st.session_state.main_system
    rt = st.session_state.unique_runtime
    names = []
    for f in files:
        dest = os.path.join(ms.input_basket, f.name)
        with open(dest, "wb") as out: out.write(f.getbuffer())
        names.append(f.name)
    rt.input_basket_tracker.clear()
    rt.receive_image(names); rt.predict()
    raw = [n for n in rt.recall_newest_history_image() if n != "avg_confident"]
    return _collect_outputs(raw, ms.output_basket), rt.get_newest_history()


def run_pil(img, fname="snap.jpg"):
    if not ensure_runtime(): raise RuntimeError("Runtime not ready")
    ms = st.session_state.main_system
    rt = st.session_state.unique_runtime
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.save(os.path.join(ms.input_basket, fname), format="JPEG", quality=95)
    rt.input_basket_tracker.clear()
    rt.receive_image([fname]); rt.predict()
    raw = [n for n in rt.recall_newest_history_image() if n != "avg_confident"]
    return _collect_outputs(raw, ms.output_basket), rt.get_newest_history()


def build_zip(imgs, data, label="result"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(imgs):
            try:
                ib = io.BytesIO(); img.save(ib, format="JPEG", quality=95)
                zf.writestr(f"{label}_{i+1}.jpg", ib.getvalue())
            except: pass
        zf.writestr("results.json", json.dumps(data, indent=2, ensure_ascii=False))
    buf.seek(0); return buf.getvalue()


def load_history_imgs(results):
    imgs = []
    for fname in results:
        if fname == "avg_confident": continue
        p = os.path.join("image_basket/output", fname)
        if os.path.exists(p):
            try: imgs.append(Image.open(p).copy())
            except: pass
    return imgs


def save_analysis(username, filename, raw):
    auth.save_user_analysis(username, {"filename": filename, "results": raw, "timestamp": datetime.now().isoformat()})


def _tags(counts):
    if not counts:
        return '<span class="tag tag-none">ไม่พบเหล็ก</span>'
    parts = []
    for cls, cnt in counts.items():
        t = "tag-bar" if "กล่อง" in cls else "tag-rod"
        parts.append(f'<span class="tag {t}">{cls} {cnt}</span>')
    return " ".join(parts)


def render_stats(raw):
    for img_name, det in raw.items():
        conf = det.get("avg_confident", 0)
        counts = {k: v for k, v in det.items() if k != "avg_confident"}
        total = sum(counts.values())
        st.markdown(f"""
        <div class="result-card">
            <div class="result-filename">{img_name}</div>
            <div class="result-row">
                <div class="result-tags">{_tags(counts)}</div>
                <div class="result-total">
                    <div class="result-num">{total}</div>
                    <div class="result-conf">{conf:.0%}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_stat_cards(raw=None):
    if raw:
        total = bar = rod = 0
        confs = []
        for det in raw.values():
            c = det.get("avg_confident", 0)
            if c: confs.append(c)
            for k, v in det.items():
                if k == "avg_confident": continue
                total += v
                if "กล่อง" in k: bar += v
                elif "เส้น" in k: rod += v
        avg_conf = sum(confs) / len(confs) if confs else 0
        cards = [
            ("rgba(240,240,240,0.5)", f'<div class="stat-card-num" style="color:#f0f0f0">{total}</div>', "จำนวนรวม"),
            ("#E07B00", f'<div class="stat-card-num" style="color:#E07B00">{bar}</div>', "เหล็กกล่อง"),
            ("#4e9cff", f'<div class="stat-card-num" style="color:#4e9cff">{rod}</div>', "เหล็กเส้น"),
            ("rgba(240,240,240,0.2)", f'<div class="stat-card-num" style="color:rgba(240,240,240,0.5)">{avg_conf:.0%}</div>', "ความแม่นยำ"),
        ]
    else:
        cards = [
            ("rgba(240,240,240,0.5)", "", "จำนวนรวม"),
            ("#E07B00", "", "เหล็กกล่อง"),
            ("#4e9cff", "", "เหล็กเส้น"),
            ("rgba(240,240,240,0.2)", "", "ความแม่นยำ"),
        ]
    items = "".join(
        f'<div class="stat-card-item"><div class="stat-card-line" style="background:{col}"></div>'
        f'<div>{num}<div class="stat-card-label">{lbl}</div></div></div>'
        for col, num, lbl in cards
    )
    st.markdown(f'<div class="stat-cards-row">{items}</div>', unsafe_allow_html=True)


def render_result(imgs, raw, prefix):
    st.divider()
    img_col, stat_col = st.columns([1.6, 0.85])
    with img_col:
        if imgs:
            cols = st.columns(min(len(imgs), 3))
            for i, img in enumerate(imgs):
                with cols[i % 3]: st.image(img, use_container_width=True)
        else:
            st.info("ไม่มีรูป output")
        st.download_button(
            "ดาวน์โหลดผล (ZIP)", build_zip(imgs, raw, prefix),
            file_name=f"steel_eye_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip", key=f"dl_{prefix}_{id(raw)}", use_container_width=True,
        )
    with stat_col:
        render_stats(raw)


def pwd_strength_html(pwd):
    l = len(pwd)
    score = min(4, (l >= 6) + (l >= 10) + any(c.isdigit() for c in pwd) + any(not c.isalnum() for c in pwd))
    colors = ["#f87171", "#fb923c", "#facc15", "#4ade80", "#60a5fa"]
    labels = ["อ่อนมาก", "อ่อน", "พอใช้", "ดี", "แข็งแกร่ง"]
    w = [20, 40, 60, 80, 100]
    return f"""<div class="pwd-bar-wrap">
        <div class="pwd-bar-track"><div class="pwd-bar-fill" style="width:{w[score]}%;background:{colors[score]};"></div></div>
        <div class="pwd-hint" style="color:{colors[score]}!important;">{labels[score]}</div>
    </div>"""


def show_login_page():
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown('<div class="login-title">Steel Eye</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">ระบบ AI นับและแยกประเภทเหล็ก</div>', unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
        with tab_in:
            uname = st.text_input("ชื่อผู้ใช้", placeholder="username", key="login_uname")
            pwd = st.text_input("รหัสผ่าน", type="password", placeholder="••••••••", key="login_pwd")
            if st.button("เข้าสู่ระบบ", key="btn_login"):
                if uname and pwd:
                    with st.spinner(""):
                        res = auth.login(uname, pwd)
                    if res["success"]:
                        st.session_state.update(authenticated=True, username=uname, user_data=res["user_data"])
                        st.rerun()
                    else:
                        st.error(res["message"])
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบ")
        with tab_reg:
            ru = st.text_input("ชื่อผู้ใช้", placeholder="ตัวอักษร ตัวเลข _ -", key="reg_u")
            rp = st.text_input("รหัสผ่าน", type="password", placeholder="อย่างน้อย 6 ตัวอักษร", key="reg_p")
            if rp:
                st.markdown(pwd_strength_html(rp), unsafe_allow_html=True)
            rf = st.text_input("ชื่อ-นามสกุล", placeholder="ชื่อของคุณ", key="reg_f")
            if st.button("สมัครสมาชิก", key="btn_reg"):
                if ru and rp and rf:
                    with st.spinner(""):
                        res = auth.register(ru, rp, rf)
                    if res["success"]:
                        st.success("สมัครสำเร็จ — ไปที่แท็บ เข้าสู่ระบบ")
                    else:
                        st.error(res["message"])
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบ")


def page_home():
    all_a = auth.get_user_analyses(st.session_state.username)
    today_count = sum(1 for ts, _ in all_a if datetime.fromisoformat(ts).date() == datetime.now().date())
    st.markdown(f"""
    <div class="page-header">
        <div class="page-title">ตรวจนับ</div>
        <div class="today-badge">{today_count} ครั้งวันนี้</div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("", ["อัปโหลดไฟล์", "ถ่ายภาพ"], horizontal=True, key="home_mode", label_visibility="collapsed")
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if mode == "อัปโหลดไฟล์":
        files = st.file_uploader(
            "", type=["jpg", "jpeg", "png"], accept_multiple_files=True,
            key="home_uploader", label_visibility="collapsed",
        )
        if not files:
            st.session_state.pop("home_imgs", None); st.session_state.pop("home_raw", None)
            render_stat_cards()
            st.button("ตรวจนับ", key="btn_analyze_off", disabled=True)
            return
        ok, err = validate_files(files)
        if not ok:
            st.error(err); return
        st.caption(f"{len(files)} ไฟล์")
        preview_cols = st.columns(min(len(files), 4))
        for i, f in enumerate(files):
            with preview_cols[i % 4]: st.image(f, caption=f.name, use_container_width=True)
        render_stat_cards(st.session_state.get("home_raw"))
        if st.button("ตรวจนับ", key="btn_analyze"):
            with st.spinner("กำลังประมวลผล..."):
                try:
                    imgs, raw = run_files(files)
                    st.session_state.home_imgs = imgs
                    st.session_state.home_raw = raw
                    save_analysis(st.session_state.username, ", ".join(f.name for f in files), raw)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get("home_imgs") is not None:
            render_result(st.session_state["home_imgs"], st.session_state["home_raw"], "upload")
    else:
        st.markdown('<div class="cam-tip">กด <strong>Take photo</strong> แล้วกดปุ่ม <strong>ตรวจนับ</strong></div>', unsafe_allow_html=True)
        cam = st.camera_input("", key="home_cam", label_visibility="collapsed")
        if cam is None:
            st.caption("หากกล้องไม่ขึ้น ให้อนุญาต Camera permission ในเบราว์เซอร์")
            st.session_state.pop("home_imgs", None); st.session_state.pop("home_raw", None)
            render_stat_cards()
            st.button("ตรวจนับ", key="btn_snap_off", disabled=True)
        else:
            render_stat_cards(st.session_state.get("home_raw"))
            if st.button("ตรวจนับ", key="btn_snap"):
                with st.spinner("กำลังประมวลผล..."):
                    try:
                        fname = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        imgs, raw = run_pil(Image.open(cam), fname)
                        st.session_state.home_imgs = imgs
                        st.session_state.home_raw = raw
                        save_analysis(st.session_state.username, fname, raw)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get("home_imgs") is not None:
                render_result(st.session_state["home_imgs"], st.session_state["home_raw"], "snap")


def page_history():
    st.markdown('<div class="page-header"><div class="page-title">ประวัติ</div></div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([2, 1.5, 1.5])
    with f1:
        ftype = st.selectbox("", ["ทั้งหมด", "7 วันล่าสุด", "30 วันล่าสุด", "กำหนดเอง"], label_visibility="collapsed")
    with f2:
        sd = st.date_input("เริ่ม") if ftype == "กำหนดเอง" else None
    with f3:
        ed = st.date_input("สิ้นสุด") if ftype == "กำหนดเอง" else None
    if ftype == "กำหนดเอง" and sd and ed and sd > ed:
        st.error("วันเริ่มต้นต้องไม่เกินวันสิ้นสุด"); return
    u = st.session_state.username
    if ftype == "ทั้งหมด":         analyses = auth.get_user_analyses(u)
    elif ftype == "7 วันล่าสุด":   analyses = auth.get_user_analyses(u, days=7)
    elif ftype == "30 วันล่าสุด":  analyses = auth.get_user_analyses(u, days=30)
    elif ftype == "กำหนดเอง" and sd and ed:
        analyses = auth.get_user_analyses_by_date_range(u, datetime.combine(sd, datetime.min.time()), datetime.combine(ed, datetime.max.time()))
    else:
        analyses = []
    if not analyses:
        st.markdown('<div class="empty-state">ยังไม่มีประวัติในช่วงเวลานี้</div>', unsafe_allow_html=True)
        return
    total_bar = total_rod = 0
    for _, ad in analyses:
        for det in ad.get("data", {}).get("results", {}).values():
            for k, v in det.items():
                if k == "avg_confident": continue
                if "กล่อง" in k: total_bar += v
                elif "เส้น" in k: total_rod += v
    st.markdown(f"""
    <div class="summary-row">
        <div class="summary-card"><div class="summary-n n-white">{len(analyses)}</div><div class="summary-l">ครั้งที่ตรวจ</div></div>
        <div class="summary-card"><div class="summary-n n-orange">{total_bar}</div><div class="summary-l">เหล็กกล่อง</div></div>
        <div class="summary-card"><div class="summary-n n-blue">{total_rod}</div><div class="summary-l">เหล็กเส้น</div></div>
    </div>
    """, unsafe_allow_html=True)
    rows = ""
    for ts, ad in analyses:
        rec = ad.get("data", {}); fname = rec.get("filename", "—"); results = rec.get("results", {})
        bar = rod = 0; confs = []
        for det in results.values():
            c = det.get("avg_confident", 0)
            if c: confs.append(c)
            for k, v in det.items():
                if k == "avg_confident": continue
                if "กล่อง" in k: bar += v
                elif "เส้น" in k: rod += v
        conf = sum(confs) / len(confs) if confs else 0
        dstr = datetime.fromisoformat(ts).strftime("%d/%m/%y %H:%M")
        fshort = fname[:28] + "…" if len(fname) > 28 else fname
        btag = f'<span class="tag tag-bar">กล่อง {bar}</span>' if bar else '<span style="color:rgba(240,240,240,0.2)">—</span>'
        rtag = f'<span class="tag tag-rod">เส้น {rod}</span>' if rod else '<span style="color:rgba(240,240,240,0.2)">—</span>'
        rows += f"""<div class="hist-row">
            <span class="hist-time">{dstr}</span>
            <span class="hist-file" title="{fname}">{fshort}</span>
            <span>{btag}</span><span>{rtag}</span>
            <span class="hist-conf">{conf:.0%}</span>
        </div>"""
    st.markdown(f"""<div class="hist-table">
        <div class="hist-head"><span>วันที่</span><span>ไฟล์</span><span>กล่อง</span><span>เส้น</span><span>แม่นยำ</span></div>
        {rows}
    </div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    last_ts, last_ad = analyses[0]
    last_results = last_ad.get("data", {}).get("results", {})
    saved = load_history_imgs(last_results)
    c1, _ = st.columns([1, 3])
    with c1:
        st.download_button("ดาวน์โหลดล่าสุด (ZIP)", build_zip(saved, last_results, "latest"),
                           file_name=f"steel_eye_{last_ts[:10]}.zip", mime="application/zip", key="dl_latest", use_container_width=True)
    with st.expander("รายการอื่น"):
        for ts, ad in analyses:
            rec = ad.get("data", {}); fname = rec.get("filename", "—"); results = rec.get("results", {})
            saved = load_history_imgs(results)
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.caption(f"{datetime.fromisoformat(ts).strftime('%d/%m/%y %H:%M')} — {fname}")
            with c2: st.caption(f"{len(saved)} ภาพ" if saved else "JSON only")
            with c3: st.download_button("ZIP", build_zip(saved, results, f"h_{ts[:10]}"),
                                        file_name=f"steel_eye_{ts[:10]}_{ts[11:13]}{ts[14:16]}.zip",
                                        mime="application/zip", key=f"dl_{ts}", use_container_width=True)


def page_settings():
    st.markdown('<div class="page-header"><div class="page-title">บัญชี</div></div>', unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    udata = st.session_state.user_data
    with col_l:
        st.markdown('<div class="section-title">ข้อมูล</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="acct-row"><span class="acct-key">ชื่อผู้ใช้</span><span class="acct-val">{st.session_state.username}</span></div>
        <div class="acct-row"><span class="acct-key">ชื่อ-นามสกุล</span><span class="acct-val">{udata['full_name']}</span></div>
        <div class="acct-row" style="border:none"><span class="acct-key">สมัครเมื่อ</span><span class="acct-val">{udata['created_at'][:10]}</span></div>
        """, unsafe_allow_html=True)
    with col_r:
        st.markdown('<div class="section-title">เปลี่ยนรหัสผ่าน</div>', unsafe_allow_html=True)
        old_p = st.text_input("รหัสผ่านเดิม", type="password", key="pwd_old")
        new_p = st.text_input("รหัสผ่านใหม่", type="password", key="pwd_new")
        if new_p:
            st.markdown(pwd_strength_html(new_p), unsafe_allow_html=True)
        conf_p = st.text_input("ยืนยันรหัสผ่านใหม่", type="password", key="pwd_conf")
        if new_p and conf_p:
            if new_p == conf_p:
                st.markdown('<div class="match-ok">✓ ตรงกัน</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="match-no">✗ ไม่ตรงกัน</div>', unsafe_allow_html=True)
        if st.button("บันทึก", key="btn_pwd"):
            if not (old_p and new_p and conf_p): st.warning("กรุณากรอกข้อมูลให้ครบ")
            elif new_p != conf_p: st.error("รหัสผ่านใหม่ไม่ตรงกัน")
            elif len(new_p) < 6: st.error("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
            else:
                res = auth.change_password(st.session_state.username, old_p, new_p)
                st.success("เปลี่ยนรหัสผ่านสำเร็จ") if res["success"] else st.error(res["message"])


def page_about():
    st.markdown('<div class="page-title">เกี่ยวกับโปรแกรม</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="about-hero">
      <div class="about-hero-dot"></div>
      <div class="about-hero-title">Steel Eye</div>
      <div class="about-hero-sub">ระบบ AI นับและแยกประเภทเหล็กอัตโนมัติ</div>
    </div>

    <div class="about-section">
      <div class="about-section-label">เกี่ยวกับโครงงาน</div>
      <p class="about-body">
        Steel Eye พัฒนาขึ้นเพื่อใช้ในโครงงานอุตสาหกรรมแบบบูรณาการ
        โดยมีวัตถุประสงค์เพื่อ<b>แก้ปัญหาการนับวัสดุเหล็กด้วยมือ</b>ซึ่งเสียเวลาและมีโอกาสผิดพลาดสูง
        ระบบนี้ใช้โมเดล <b>YOLO v11</b> ที่ผ่านการ train ด้วยชุดข้อมูลเหล็กจริงในโรงงาน
        สามารถตรวจจับและแยกแยะ <b>เหล็กกล่อง</b> กับ <b>เหล็กเส้น</b> ได้จากภาพถ่ายเดียว
        ช่วยลดเวลาการนับจากหลายนาทีเหลือเพียงไม่กี่วินาที
      </p>
    </div>

    <div class="about-tags-row">
      <span class="about-tag">🎓 โปรเจกต์การศึกษา</span>
      <span class="about-tag">🤖 YOLO v11</span>
      <span class="about-tag">🐍 Python · Streamlit</span>
      <span class="about-tag">☁️ Supabase</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-section" style="margin-top:28px;">
      <div class="about-section-label">วิธีใช้งาน</div>
    </div>
    """, unsafe_allow_html=True)

    steps = [
        ("เข้าสู่ระบบ", "สมัครบัญชีหรือ login ด้วย username และรหัสผ่าน ระบบจะจำ session ไว้แม้รีเฟรชหน้า"),
        ("เลือกวิธีนำเข้ารูป", "ไปที่หน้า <b>ตรวจนับ</b> — เลือก <b>อัปโหลดไฟล์</b> (JPG/PNG ≤10 MB สูงสุด 10 ไฟล์) หรือ <b>ถ่ายภาพ</b> ผ่านกล้องมือถือ/เว็บแคม"),
        ("ตรวจนับ", "กดปุ่ม <b>ตรวจนับ</b> — AI จะประมวลผลและแสดงจำนวน เหล็กกล่อง / เหล็กเส้น พร้อมภาพที่ทำ annotation ให้ดูทันที"),
        ("ดาวน์โหลดผล", "กด <b>ดาวน์โหลด ZIP</b> เพื่อรับไฟล์รูปผลลัพธ์พร้อมรายงานสรุปตัวเลขในรูปแบบ .txt"),
        ("ดูประวัติ", "ไปที่หน้า <b>ประวัติ</b> เพื่อดูสถิติสะสม กรองตามช่วงเวลา และดาวน์โหลดผลเก่าย้อนหลัง"),
    ]

    steps_html = ""
    for i, (title, desc) in enumerate(steps, 1):
        steps_html += f"""
        <div class="how-step">
          <div class="how-num">{i}</div>
          <div class="how-content">
            <div class="how-title">{title}</div>
            <div class="how-desc">{desc}</div>
          </div>
        </div>"""

    st.markdown(f'<div class="how-list">{steps_html}</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="about-section" style="margin-top:28px;">
      <div class="about-section-label">ข้อจำกัดและคำแนะนำ</div>
    </div>
    <div class="tips-grid">
      <div class="tip-card">
        <div class="tip-icon">📸</div>
        <div class="tip-text"><b>แสงพอเพียง</b><br>ถ่ายในที่มีแสงสว่างเพียงพอ หลีกเลี่ยงแสงย้อนหรือเงา</div>
      </div>
      <div class="tip-card">
        <div class="tip-icon">📐</div>
        <div class="tip-text"><b>มุมตั้งฉาก</b><br>ถ่ายจากมุมตรงเหนือกองเหล็ก ได้ผลแม่นยำกว่ามุมเฉียง</div>
      </div>
      <div class="tip-card">
        <div class="tip-icon">✂️</div>
        <div class="tip-text"><b>ใช้ Crop</b><br>ตัดพื้นหลังออกให้เหลือแต่เหล็ก ลดการนับผิดพลาด</div>
      </div>
      <div class="tip-card">
        <div class="tip-icon">📁</div>
        <div class="tip-text"><b>หลายไฟล์พร้อมกัน</b><br>อัปโหลดได้สูงสุด 10 ไฟล์ต่อครั้งสำหรับการนับแบบ batch</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def show_main_app():
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-dot"></div><span class="brand-name">Steel Eye</span></div>', unsafe_allow_html=True)
        page = st.radio("", ["ตรวจนับ", "ประวัติ", "บัญชี", "เกี่ยวกับ"], key="nav", label_visibility="collapsed")
        st.divider()
        udata = st.session_state.user_data
        st.markdown(f'<div class="user-info"><div class="user-name">{udata["full_name"]}</div><div class="user-handle">@{st.session_state.username}</div></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("ออกจากระบบ", key="btn_logout"):
            for k in ["authenticated", "username", "user_data", "model", "main_system", "unique_runtime", "home_imgs", "home_raw"]:
                st.session_state.pop(k, None)
            st.rerun()

    if page == "ตรวจนับ":   page_home()
    elif page == "ประวัติ":  page_history()
    elif page == "บัญชี":    page_settings()
    elif page == "เกี่ยวกับ": page_about()


def main():
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()