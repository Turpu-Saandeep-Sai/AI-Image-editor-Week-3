"""
app.py
------
Entry point for the AI-Powered Image Editing Platform.

This module:
    - Configures the Streamlit page (title, layout, sidebar).
    - Loads environment variables from ``.env``.
    - Sets up the application's data directories.
    - Renders the Upload page (the default / home view).
    - Provides shared session-state initialisation used by all pages.

Navigation is handled via Streamlit's multi-page app mechanism
(``pages/`` directory).  This file renders the Home / Upload page.

Author: AI Image Editor Platform
Version: 1.0.0
"""

import hashlib
import logging
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path bootstrap — ensure ``backend/`` is importable
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ---------------------------------------------------------------------------
# Environment & Logging
# ---------------------------------------------------------------------------
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application-level constants (no hardcoded strings beyond this block)
# ---------------------------------------------------------------------------
DATA_DIR: Path = ROOT_DIR / "data"
IMAGES_DIR: Path = DATA_DIR / "images"
ASSETS_DIR: Path = ROOT_DIR / "assets"

# ---------------------------------------------------------------------------
# Lazy imports of backend modules (after sys.path is set)
# ---------------------------------------------------------------------------
from backend.database import add_metadata, build_record, find_all  # noqa: E402
from backend.storage import save_image  # noqa: E402
from backend.caption import generate_caption  # noqa: E402
from backend.search import index_image  # noqa: E402
from backend.utils import (  # noqa: E402
    generate_uuid,
    image_validation,
    timestamp,
    format_file_size,
)

# ---------------------------------------------------------------------------
# Streamlit page configuration — MUST be the first st call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Image Editor — Upload",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "**AI-Powered Image Editing Platform** · Week 2",
    },
)


# ---------------------------------------------------------------------------
# Shared CSS injected once at startup
# ---------------------------------------------------------------------------
def _inject_global_css() -> None:
    """Inject shared CSS for consistent styling across all pages."""
    st.markdown(
        """
        <style>
        /* ── Google Font ─────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── Background ──────────────────────────────────────────────── */
        .stApp {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
        }

        /* ── Sidebar ─────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        [data-testid="stSidebar"] * {
            color: #e0e0e0 !important;
        }

        /* ── Main content area ───────────────────────────────────────── */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* ── Page header ─────────────────────────────────────────────── */
        .page-header {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 2rem 2.5rem;
            margin-bottom: 2rem;
        }
        .page-header h1 {
            color: #ffffff;
            font-size: 2rem;
            font-weight: 700;
            margin: 0 0 0.4rem 0;
            background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .page-header p {
            color: rgba(255,255,255,0.55);
            font-size: 0.95rem;
            margin: 0;
        }

        /* ── Glass card ──────────────────────────────────────────────── */
        .glass-card {
            background: rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: box-shadow 0.3s ease, border-color 0.3s ease;
        }
        .glass-card:hover {
            box-shadow: 0 8px 32px rgba(167, 139, 250, 0.2);
            border-color: rgba(167, 139, 250, 0.35);
        }

        /* ── Upload drop zone ────────────────────────────────────────── */
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(167, 139, 250, 0.08) !important;
            border: 2px dashed rgba(167, 139, 250, 0.4) !important;
            border-radius: 12px !important;
            padding: 2rem !important;
            transition: border-color 0.3s ease !important;
        }
        [data-testid="stFileUploaderDropzone"]:hover {
            border-color: rgba(167, 139, 250, 0.8) !important;
            background: rgba(167, 139, 250, 0.12) !important;
        }

        /* ── Metric labels ───────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 1rem;
        }
        [data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; }
        [data-testid="stMetricValue"] { color: #a78bfa !important; font-weight: 600; }

        /* ── Buttons ─────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #7c3aed, #4f46e5);
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.25rem;
            font-weight: 600;
            font-size: 0.875rem;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 0 4px 20px rgba(124, 58, 237, 0.5);
            transform: translateY(-1px);
        }

        /* ── Alerts ──────────────────────────────────────────────────── */
        .stSuccess, .stError, .stWarning, .stInfo {
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }

        /* ── Spinner ─────────────────────────────────────────────────── */
        .stSpinner > div { color: #a78bfa !important; }

        /* ── Divider ─────────────────────────────────────────────────── */
        hr {
            border: none;
            border-top: 1px solid rgba(255,255,255,0.08);
            margin: 1.5rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_session_state() -> None:
    """Initialise all shared session-state keys once per session."""
    defaults: dict = {
        "selected_image_id": None,   # UUID of the image open in Detail View
        "upload_success": False,     # flag used to show the success banner
        "last_uploaded_id": None,    # UUID of the most recently uploaded image
        # ── Upload deduplication ──────────────────────────────────────────
        # Maps SHA-256 fingerprint → image_id so we never call the Vision
        # API more than once per unique file, even across Streamlit reruns.
        "processed_file_hashes": {},
        "last_caption": "",          # caption from the most recent upload
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    """Render the sidebar with navigation links and application info."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0 0.5rem;">
                <span style="font-size:2.5rem;">🎨</span>
                <h2 style="color:#a78bfa; margin:0.25rem 0 0; font-size:1.1rem; font-weight:700;">
                    AI Image Editor
                </h2>
                <p style="color:rgba(255,255,255,0.35); font-size:0.75rem; margin:0;">
                    Week 3 · Search & AI Platform
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")

        st.markdown("**📁 Navigation**")
        st.page_link("app.py", label="⬆️  Upload", icon=None)
        st.page_link("pages/1_Library.py", label="🖼️  Library", icon=None)
        st.page_link("pages/2_Image_Detail.py", label="🔍  Detail View", icon=None)
        st.page_link("pages/3_Image_Edit.py", label="✏️  Edit Image", icon=None)
        st.page_link("pages/4_Search.py", label="🔎  Semantic Search", icon=None)

        st.markdown("---")

        # Live stats
        all_records = find_all(DATA_DIR)
        total = len(all_records)
        captioned = sum(1 for r in all_records if r.get("caption"))

        st.markdown("**📊 Stats**")
        col_a, col_b = st.columns(2)
        col_a.metric("Images", total)
        col_b.metric("Captioned", captioned)

        st.markdown("---")
        st.markdown(
            "<p style='color:rgba(255,255,255,0.3); font-size:0.7rem; text-align:center;'>"
            "v3.0.0 · Built with Streamlit</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Upload page
# ---------------------------------------------------------------------------
def _render_upload_page() -> None:
    """Render the main Upload page UI and handle file processing."""
    st.markdown(
        """
        <div class="page-header">
            <h1>⬆️ Upload Image</h1>
            <p>Upload PNG, JPG or JPEG images. An AI caption is generated automatically.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Success banner (shown after a successful upload) ───────────────────
    if st.session_state.get("upload_success"):
        st.success(
            "✅ Image uploaded and captioned successfully! "
            "Head to the **Library** to view it.",
            icon="🎉",
        )
        st.session_state["upload_success"] = False

    # ── Two-column layout ──────────────────────────────────────────────────
    col_upload, col_guide = st.columns([3, 2], gap="large")

    with col_upload:
        st.markdown(
            '<div class="glass-card">',
            unsafe_allow_html=True,
        )
        st.markdown("#### 📂 Select an image")

        uploaded_file = st.file_uploader(
            label="Drag & drop or browse",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=False,
            help="Supported formats: PNG, JPG, JPEG",
            key="file_uploader",
        )

        if uploaded_file is not None:
            _handle_upload(uploaded_file)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_guide:
        st.markdown(
            '<div class="glass-card">',
            unsafe_allow_html=True,
        )
        st.markdown("#### ℹ️ How it works")
        st.markdown(
            """
            1. **Select** a PNG / JPG / JPEG image
            2. The file is **validated** for format & integrity
            3. A **unique ID** (UUID) is assigned
            4. The image is **stored** safely on disk
            5. The **Vision AI** generates a 40–60-word caption
            6. Metadata is **saved** to `metadata.json`
            7. The image appears in the **Library** instantly

            ---
            **Tip:** After uploading, visit the
            **Library** page to browse your images, or the
            **Detail View** for technical information.
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Recent uploads preview ─────────────────────────────────────────────
    _render_recent_uploads()


def _handle_upload(uploaded_file) -> None:  # type: ignore[no-untyped-def]
    """Process the uploaded file: validate → save → caption → persist.

    Uses a SHA-256 fingerprint stored in session state to ensure the
    full pipeline (including the Vision API call) runs **exactly once**
    per unique file, regardless of how many times Streamlit reruns the
    script while the file is still loaded in the uploader widget.

    Args:
        uploaded_file: The ``UploadedFile`` object from ``st.file_uploader``.
    """
    file_bytes: bytes = uploaded_file.read()
    original_name: str = uploaded_file.name

    # ── Fingerprint ────────────────────────────────────────────────────────
    # Compute BEFORE any processing so we can bail out on reruns.
    file_hash: str = hashlib.sha256(file_bytes).hexdigest()

    # ── Always show the preview (safe on every rerun) ──────────────────────
    st.markdown("---")
    st.markdown("##### 🖼️ Preview")
    st.image(file_bytes, caption=original_name, use_container_width=True)
    st.markdown(
        f"**Size:** {format_file_size(len(file_bytes))}  &nbsp;|&nbsp;  "
        f"**Format:** {Path(original_name).suffix.upper().lstrip('.')}",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Already processed guard ────────────────────────────────────────────
    # If this exact file was already saved + captioned in this session,
    # just show the cached caption and stop — no API call.
    processed: dict = st.session_state.get("processed_file_hashes", {})
    if file_hash in processed:
        cached_caption = st.session_state.get("last_caption", "")
        if cached_caption:
            st.info(f'🤖 **Caption (cached):** "{cached_caption}"')
        else:
            st.info("✅ File already uploaded in this session.")
        return

    # ── Validate ───────────────────────────────────────────────────────────
    valid, error_msg = image_validation(file_bytes, original_name)
    if not valid:
        st.error(f"❌ Validation failed: {error_msg}")
        return

    # ── Duplicate guard ────────────────────────────────────────────────────
    existing = find_all(DATA_DIR)
    suffix = Path(original_name).suffix.lower()

    # ── Assign UUID & build filename ───────────────────────────────────────
    image_id: str = generate_uuid()
    stored_filename: str = f"{image_id}{suffix}"

    # ── Save to disk ───────────────────────────────────────────────────────
    try:
        saved_path: Path = save_image(
            file_data=file_bytes,
            filename=stored_filename,
            images_dir=IMAGES_DIR,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        st.error(f"❌ Storage error: {exc}")
        return

    # ── Mark as processed BEFORE the API call ─────────────────────────────
    # Prevents a second API call if Streamlit reruns mid-spinner.
    if "processed_file_hashes" not in st.session_state:
        st.session_state["processed_file_hashes"] = {}
    st.session_state["processed_file_hashes"][file_hash] = image_id

    # ── Generate AI caption (called exactly once per unique file) ──────────
    caption: str = ""
    caption_error: str | None = None

    with st.spinner("🤖 Generating AI caption … this may take a few seconds"):
        caption, caption_error = generate_caption(image_path=saved_path)

    # Cache for display on subsequent reruns
    st.session_state["last_caption"] = caption

    if caption_error:
        st.warning(
            f"⚠️ Caption generation failed: {caption_error}\n\n"
            "The image was still saved. You can retry from the Detail View."
        )
    else:
        st.info(f'🤖 **Generated caption:** "{caption}"')

    # ── Persist metadata ───────────────────────────────────────────────────
    record = build_record(
        image_id=image_id,
        filename=original_name,
        filepath=str(saved_path),
        caption=caption,
        uploaded_at=timestamp(),
    )
    success = add_metadata(DATA_DIR, record)
    if not success:
        st.error("❌ Failed to save metadata. Please try again.")
        return

    # ── Generate vector embedding & index into Vector DB ───────────────────
    if caption:
        index_image(DATA_DIR, image_id, caption, record)

    # ── Mark success & trigger rerun to show banner ────────────────────────
    st.session_state["upload_success"] = True
    st.session_state["last_uploaded_id"] = image_id
    logger.info("Upload complete: id=%s filename=%s", image_id, original_name)
    st.rerun()


def _render_recent_uploads() -> None:
    """Render a compact preview of the three most recently uploaded images."""
    all_records = find_all(DATA_DIR)
    if not all_records:
        return

    recent = all_records[:3]
    st.markdown("---")
    st.markdown("#### 🕐 Recently Uploaded")

    cols = st.columns(len(recent))
    for col, record in zip(cols, recent):
        fp = Path(record.get("filepath", ""))
        with col:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if fp.exists():
                st.image(str(fp), use_container_width=True)
            st.markdown(
                f"**{record.get('filename', 'Unknown')}**  \n"
                f"<span style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>"
                f"{record.get('uploaded_at', '')[:10]}</span>",
                unsafe_allow_html=True,
            )
            if st.button("View", key=f"recent_{record['id']}"):
                st.session_state["selected_image_id"] = record["id"]
                st.switch_page("pages/2_Image_Detail.py")
            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Application entry point."""
    # Ensure data directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    _inject_global_css()
    _init_session_state()
    _render_sidebar()
    _render_upload_page()


if __name__ == "__main__":
    main()
else:
    # Called by Streamlit's multi-page runner
    main()
