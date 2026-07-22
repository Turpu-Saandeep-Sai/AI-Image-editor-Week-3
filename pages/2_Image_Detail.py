"""
2_Image_Detail.py
-----------------
Detail View page for the AI-Powered Image Editing Platform.

Displays full technical information about a selected image:
    - Large image preview
    - Filename, UUID, caption, upload date
    - Image dimensions and file size
    - Placeholder action buttons (Edit, Versions, Delete — disabled for Week 1)

Author: AI Image Editor Platform
Version: 1.0.0
"""

import sys
from pathlib import Path

import streamlit as st
from PIL import Image as PilImage

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from backend.database import find_all, find_by_id
from backend.utils import (
    format_file_size,
    format_timestamp_display,
    get_image_dimensions,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR: Path = ROOT_DIR / "data"
IMAGES_DIR: Path = DATA_DIR / "images"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Image Editor — Detail View",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .stApp {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
        }
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.04);
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

        .page-header {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 2rem 2.5rem;
            margin-bottom: 2rem;
        }
        .page-header h1 {
            font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0;
            background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .page-header p { color: rgba(255,255,255,0.55); font-size: 0.95rem; margin: 0; }

        /* ── Info panel ──────────────────────────────────────────────── */
        .info-panel {
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.75rem;
        }
        .info-section-title {
            color: rgba(255,255,255,0.4);
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }
        .info-row {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            margin-bottom: 1.25rem;
        }
        .info-label {
            color: rgba(255,255,255,0.35);
            font-size: 0.72rem;
            font-weight: 500;
        }
        .info-value {
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 500;
            word-break: break-all;
        }
        .info-value.mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: #a78bfa;
        }

        /* ── Caption box ─────────────────────────────────────────────── */
        .caption-box {
            background: rgba(167,139,250,0.08);
            border: 1px solid rgba(167,139,250,0.25);
            border-radius: 12px;
            padding: 1.25rem;
            margin: 1rem 0;
        }
        .caption-box p {
            color: rgba(255,255,255,0.8);
            font-size: 0.9rem;
            line-height: 1.7;
            margin: 0;
            font-style: italic;
        }

        /* ── Action buttons ──────────────────────────────────────────── */
        .action-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-top: 1.5rem;
        }
        .action-btn {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 0.75rem;
            text-align: center;
            color: rgba(255,255,255,0.35);
            font-size: 0.8rem;
            cursor: not-allowed;
            transition: all 0.2s ease;
        }
        .action-btn.active {
            background: linear-gradient(135deg, #7c3aed, #4f46e5);
            border-color: transparent;
            color: white;
            cursor: pointer;
        }
        .action-btn.active:hover {
            box-shadow: 0 4px 20px rgba(124,58,237,0.5);
            transform: translateY(-1px);
        }
        .action-btn .btn-icon { font-size: 1.2rem; display: block; margin-bottom: 0.2rem; }
        .action-btn .btn-label { font-weight: 600; }
        .action-btn .btn-sub { font-size: 0.65rem; opacity: 0.6; }

        /* ── Image preview panel ─────────────────────────────────────── */
        .image-panel {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            overflow: hidden;
        }

        /* ── Tag ─────────────────────────────────────────────────────── */
        .tag {
            display: inline-block;
            background: rgba(96,165,250,0.15);
            border: 1px solid rgba(96,165,250,0.3);
            border-radius: 20px;
            padding: 0.2rem 0.6rem;
            font-size: 0.7rem;
            color: #60a5fa;
            margin-right: 0.3rem;
        }

        /* ── Buttons ─────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #7c3aed, #4f46e5);
            color: white !important; border: none; border-radius: 8px;
            padding: 0.5rem 1.25rem; font-weight: 600; font-size: 0.875rem;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 0 4px 20px rgba(124,58,237,0.5);
            transform: translateY(-1px);
        }

        /* ── Metric ──────────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 0.75rem;
        }
        [data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; font-size:0.7rem!important;}
        [data-testid="stMetricValue"] { color: #a78bfa !important; font-weight: 600; font-size:1.1rem!important; }

        hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.5rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding:1rem 0 0.5rem;">
                <span style="font-size:2.5rem;">🎨</span>
                <h2 style="color:#a78bfa; margin:0.25rem 0 0; font-size:1.1rem; font-weight:700;">
                    AI Image Editor
                </h2>
                <p style="color:rgba(255,255,255,0.35); font-size:0.75rem; margin:0;">
                    Week 2 · AI Editing & Versions
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("**📁 Navigation**")
        st.page_link("app.py", label="⬆️  Upload")
        st.page_link("pages/1_Library.py", label="🖼️  Library")
        st.page_link("pages/2_Image_Detail.py", label="🔍  Detail View")
        st.page_link("pages/3_Image_Edit.py", label="✏️  Edit Image")
        st.markdown("---")

        # Image selector dropdown
        all_records = find_all(DATA_DIR)
        if all_records:
            st.markdown("**🔎 Jump to image**")
            options = {r["id"]: r.get("filename", r["id"]) for r in all_records}
            current_id = st.session_state.get("selected_image_id")
            selected = st.selectbox(
                "Select image",
                options=list(options.keys()),
                format_func=lambda x: options[x],
                index=(
                    list(options.keys()).index(current_id)
                    if current_id in options
                    else 0
                ),
                label_visibility="collapsed",
                key="detail_selector",
            )
            if selected != current_id:
                st.session_state["selected_image_id"] = selected
                st.rerun()

        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("Images", len(all_records))
        c2.metric("Captioned", sum(1 for r in all_records if r.get("caption")))
        st.markdown("---")
        st.markdown(
            "<p style='color:rgba(255,255,255,0.3);font-size:0.7rem;text-align:center;'>"
            "v2.0.0 · Built with Streamlit</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Detail view
# ---------------------------------------------------------------------------
def _render_no_selection() -> None:
    """Shown when no image is selected."""
    st.markdown(
        """
        <div style="text-align:center; padding:5rem; opacity:0.5;">
            <span style="font-size:5rem;">🔍</span>
            <h3 style="color:rgba(255,255,255,0.6); margin-top:1rem;">
                No image selected
            </h3>
            <p style="color:rgba(255,255,255,0.35);">
                Go to the Library and click <b>View Details</b> on any image,<br>
                or use the sidebar dropdown to select one.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🖼️ Go to Library"):
        st.switch_page("pages/1_Library.py")


def _render_image_detail(record: dict) -> None:
    """Render the full detail view for *record*.

    Args:
        record: Image metadata dict from the database.
    """
    image_id: str = record.get("id", "—")
    filename: str = record.get("filename", "Unknown")
    filepath_str: str = record.get("filepath", "")
    caption: str = record.get("caption", "")
    uploaded_at: str = record.get("uploaded_at", "—")

    filepath = Path(filepath_str) if filepath_str else None

    # ── Page header ────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="page-header">
            <h1>🔍 {filename}</h1>
            <p>Image Detail View — Technical metadata and AI caption.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Two-column layout ──────────────────────────────────────────────────
    col_img, col_info = st.columns([3, 2], gap="large")

    # ── Left: image preview ────────────────────────────────────────────────
    with col_img:
        st.markdown('<div class="image-panel">', unsafe_allow_html=True)
        if filepath and filepath.exists():
            st.image(str(filepath), use_container_width=True, caption=filename)
        else:
            st.markdown(
                "<div style='height:400px;display:flex;align-items:center;"
                "justify-content:center;color:rgba(255,255,255,0.2);font-size:3rem;'>"
                "🖼️<br><small style='font-size:1rem;'>File not found on disk</small></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # AI Caption
        st.markdown("---")
        st.markdown("##### 🤖 AI-Generated Caption")
        if caption:
            st.markdown(
                f'<div class="caption-box"><p>"{caption}"</p></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No caption available. Caption generation may have failed.")

    # ── Right: metadata ────────────────────────────────────────────────────
    with col_info:
        st.markdown('<div class="info-panel">', unsafe_allow_html=True)

        # ── File info section ──────────────────────────────────────────────
        st.markdown('<div class="info-section-title">📄 File Information</div>', unsafe_allow_html=True)

        file_size_str = "—"
        width_str = "—"
        height_str = "—"
        if filepath and filepath.exists():
            file_size_str = format_file_size(filepath.stat().st_size)
            dims = get_image_dimensions(filepath)
            if dims:
                width_str, height_str = str(dims[0]), str(dims[1])

        info_fields = [
            ("Filename", filename, False),
            ("File Size", file_size_str, False),
            ("Dimensions", f"{width_str} × {height_str} px", False),
            ("Format", Path(filename).suffix.upper().lstrip("."), False),
        ]
        for label, value, mono in info_fields:
            st.markdown(
                f"""
                <div class="info-row">
                    <span class="info-label">{label}</span>
                    <span class="info-value {'mono' if mono else ''}">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)

        # ── Upload info section ────────────────────────────────────────────
        st.markdown('<div class="info-section-title">📅 Upload Information</div>', unsafe_allow_html=True)
        upload_display = format_timestamp_display(uploaded_at) if uploaded_at != "—" else "—"
        st.markdown(
            f"""
            <div class="info-row">
                <span class="info-label">Uploaded At</span>
                <span class="info-value">{upload_display}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)

        # ── Identifier section ─────────────────────────────────────────────
        st.markdown('<div class="info-section-title">🔑 Identifier</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="info-row">
                <span class="info-label">UUID</span>
                <span class="info-value mono">{image_id}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Storage Path</span>
                <span class="info-value mono" style="font-size:0.68rem;">{filepath_str}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)

        # ── Version history section (Week 2 placeholder) ───────────────────
        versions = record.get("versions", [])
        st.markdown('<div class="info-section-title">🕐 Version History</div>', unsafe_allow_html=True)
        if versions:
            for v in versions:
                ver_num = v.get('version', '?')
                ver_prompt = v.get('prompt', '—')
                ver_ts = v.get('timestamp', '—')
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);"
                    f"border-radius:8px;padding:0.5rem;margin-bottom:0.4rem;'>"
                    f"<span style='color:#a78bfa;font-weight:700;font-size:0.75rem;'>✏️ v{ver_num}</span>"
                    f"<br><span style='color:rgba(255,255,255,0.6);font-size:0.7rem;'>{ver_prompt}</span>"
                    f"<br><span style='color:rgba(255,255,255,0.3);font-size:0.6rem;'>{ver_ts[:16] if len(str(ver_ts)) > 16 else ver_ts}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='color:rgba(255,255,255,0.3);font-size:0.78rem;'>"
                "No versions yet. Use the Edit page to create versions.</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)  # end info-panel

        # ── Action buttons ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### ⚡ Actions")

        act_c1, act_c2 = st.columns(2)
        with act_c1:
            if st.button("✏️ Edit Image", key="action_edit", use_container_width=True):
                st.switch_page("pages/3_Image_Edit.py")
        with act_c2:
            if st.button(f"🕐 Versions ({len(versions)})", key="action_versions", use_container_width=True):
                st.switch_page("pages/3_Image_Edit.py")

    # ── Quick metrics strip ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 📊 Quick Stats")
    q1, q2, q3, q4, q5 = st.columns(5)
    q1.metric("Width", f"{width_str} px")
    q2.metric("Height", f"{height_str} px")
    q3.metric("File Size", file_size_str)
    q4.metric("Format", Path(filename).suffix.upper().lstrip(".") or "—")
    q5.metric("Versions", str(len(versions)))

    # ── Navigation strip ───────────────────────────────────────────────────
    st.markdown("---")
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
    with nav_col1:
        if st.button("⬅️ Back to Library"):
            st.switch_page("pages/1_Library.py")
    with nav_col2:
        if st.button("⬆️ Upload New"):
            st.switch_page("app.py")
    with nav_col3:
        # Previous / Next navigation within library
        all_ids = [r["id"] for r in find_all(DATA_DIR)]
        if image_id in all_ids:
            idx = all_ids.index(image_id)
            nc1, nc2 = nav_col3.columns(2)
            if idx > 0 and nc1.button("◀ Previous"):
                st.session_state["selected_image_id"] = all_ids[idx - 1]
                st.rerun()
            if idx < len(all_ids) - 1 and nc2.button("Next ▶"):
                st.session_state["selected_image_id"] = all_ids[idx + 1]
                st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Detail View page."""
    if "selected_image_id" not in st.session_state:
        st.session_state["selected_image_id"] = None

    _inject_css()
    _render_sidebar()

    image_id: str | None = st.session_state.get("selected_image_id")

    if not image_id:
        st.markdown(
            """
            <div class="page-header">
                <h1>🔍 Image Detail View</h1>
                <p>Select an image from the Library to see its full details.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_no_selection()
        return

    record = find_by_id(DATA_DIR, image_id)
    if record is None:
        st.error(
            f"❌ Image with ID `{image_id}` not found in the database. "
            "It may have been deleted."
        )
        if st.button("🖼️ Go to Library"):
            st.switch_page("pages/1_Library.py")
        return

    _render_image_detail(record)


main()
