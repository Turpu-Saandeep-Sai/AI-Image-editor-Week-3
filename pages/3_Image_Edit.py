"""
3_Image_Edit.py
---------------
Image Editing page for the AI-Powered Image Editing Platform.

Features:
    - Large image preview with current caption
    - Natural language prompt input for custom edits
    - 10 preset one-click editing buttons
    - Side-by-side comparison: original vs edited
    - Version history timeline in sidebar
    - Loading animations and error handling

Author: AI Image Editor Platform
Version: 2.0.0
"""

import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from backend.database import find_all, find_by_id, load_versions
from backend.image_edit import edit_image
from backend.prompt_templates import PRESET_PROMPTS, get_preset_prompt
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
    page_title="AI Image Editor — Edit",
    page_icon="✏️",
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

        /* ── Glass card ─────────────────────────────────────────── */
        .glass-card {
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: box-shadow 0.3s ease, border-color 0.3s ease;
        }
        .glass-card:hover {
            box-shadow: 0 8px 32px rgba(167,139,250,0.15);
            border-color: rgba(167,139,250,0.25);
        }

        /* ── Preset button grid ─────────────────────────────────── */
        .preset-btn {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 12px;
            padding: 0.75rem 0.5rem;
            text-align: center;
            transition: all 0.25s ease;
            cursor: pointer;
        }
        .preset-btn:hover {
            background: rgba(167,139,250,0.15);
            border-color: rgba(167,139,250,0.4);
            box-shadow: 0 4px 20px rgba(167,139,250,0.2);
            transform: translateY(-2px);
        }
        .preset-btn .preset-icon { font-size: 1.4rem; display: block; margin-bottom: 0.25rem; }
        .preset-btn .preset-label {
            color: #ffffff; font-weight: 600; font-size: 0.72rem;
            display: block; margin-bottom: 0.15rem;
        }
        .preset-btn .preset-desc {
            color: rgba(255,255,255,0.4); font-size: 0.62rem;
        }

        /* ── Caption box ────────────────────────────────────────── */
        .caption-box {
            background: rgba(167,139,250,0.08);
            border: 1px solid rgba(167,139,250,0.25);
            border-radius: 12px;
            padding: 1rem;
            margin: 0.75rem 0;
        }
        .caption-box p {
            color: rgba(255,255,255,0.8); font-size: 0.85rem;
            line-height: 1.6; margin: 0; font-style: italic;
        }

        /* ── Comparison panel ───────────────────────────────────── */
        .comparison-label {
            text-align: center;
            color: rgba(255,255,255,0.5);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.5rem;
        }

        /* ── Timeline ───────────────────────────────────────────── */
        .timeline-item {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 0.65rem;
            margin-bottom: 0.5rem;
            transition: all 0.2s ease;
        }
        .timeline-item:hover {
            background: rgba(167,139,250,0.1);
            border-color: rgba(167,139,250,0.3);
        }
        .timeline-version {
            color: #a78bfa; font-weight: 700; font-size: 0.75rem;
        }
        .timeline-prompt {
            color: rgba(255,255,255,0.6); font-size: 0.68rem;
            margin: 0.2rem 0; line-height: 1.4;
            overflow: hidden; text-overflow: ellipsis;
            display: -webkit-box; -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .timeline-time {
            color: rgba(255,255,255,0.3); font-size: 0.6rem;
        }
        .timeline-connector {
            text-align: center;
            color: rgba(167,139,250,0.4);
            font-size: 0.8rem;
            margin: 0.15rem 0;
        }

        /* ── Buttons ────────────────────────────────────────────── */
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

        /* ── Metric ─────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 0.75rem;
        }
        [data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; font-size:0.7rem!important; }
        [data-testid="stMetricValue"] { color: #a78bfa !important; font-weight: 600; font-size:1.1rem!important; }

        hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.5rem 0; }
        .stSpinner > div { color: #a78bfa !important; }

        /* ── Success / result banner ────────────────────────────── */
        .edit-result-banner {
            background: rgba(52,211,153,0.1);
            border: 1px solid rgba(52,211,153,0.3);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin: 1rem 0;
        }
        .edit-result-banner p {
            color: #34d399; font-weight: 600; margin: 0; font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_session_state() -> None:
    """Initialise edit-page-specific session state keys."""
    defaults = {
        "selected_image_id": None,
        "edit_prompt": "",
        "edit_result_path": None,
        "edit_error": None,
        "edit_in_progress": False,
        "edit_version_view": None,  # version filepath to display
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar with version history
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
                    Week 3 · Search & AI Platform
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
        st.page_link("pages/4_Search.py", label="🔎  Semantic Search")
        st.markdown("---")

        # ── Version history timeline ──────────────────────────────────────
        image_id = st.session_state.get("selected_image_id")
        if image_id:
            record = find_by_id(DATA_DIR, image_id)
            if record:
                _render_version_timeline(record)

        st.markdown("---")
        all_records = find_all(DATA_DIR)
        c1, c2 = st.columns(2)
        c1.metric("Images", len(all_records))
        c2.metric("Captioned", sum(1 for r in all_records if r.get("caption")))
        st.markdown("---")
        st.markdown(
            "<p style='color:rgba(255,255,255,0.3);font-size:0.7rem;text-align:center;'>"
            "v3.0.0 · Built with Streamlit</p>",
            unsafe_allow_html=True,
        )


def _render_version_timeline(record: dict) -> None:
    """Render the version history timeline in the sidebar.

    Args:
        record: The image metadata dict with a 'versions' list.
    """
    st.markdown("**🕐 Version History**")
    versions = record.get("versions", [])

    # Original entry
    st.markdown(
        f"""
        <div class="timeline-item">
            <div class="timeline-version">📌 Original</div>
            <div class="timeline-prompt">Original Upload</div>
            <div class="timeline-time">{record.get('uploaded_at', '—')[:16]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Open Original", key="open_original", use_container_width=True):
        st.session_state["edit_version_view"] = record.get("filepath")
        st.rerun()

    for v in versions:
        ver_num = v.get("version", "?")
        prompt_text = v.get("prompt", "—")
        ts = v.get("timestamp", "—")

        st.markdown('<div class="timeline-connector">↓</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="timeline-item">
                <div class="timeline-version">✏️ Version {ver_num}</div>
                <div class="timeline-prompt">{prompt_text}</div>
                <div class="timeline-time">{ts[:16] if len(ts) > 16 else ts}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ver_filepath = v.get("filepath", "")
        if ver_filepath and Path(ver_filepath).exists():
            if st.button(f"Open V{ver_num}", key=f"open_v{ver_num}", use_container_width=True):
                st.session_state["edit_version_view"] = ver_filepath
                st.rerun()


# ---------------------------------------------------------------------------
# No selection
# ---------------------------------------------------------------------------
def _render_no_selection() -> None:
    """Show when no image is selected."""
    st.markdown(
        """
        <div style="text-align:center; padding:5rem; opacity:0.5;">
            <span style="font-size:5rem;">✏️</span>
            <h3 style="color:rgba(255,255,255,0.6); margin-top:1rem;">
                No image selected for editing
            </h3>
            <p style="color:rgba(255,255,255,0.35);">
                Go to the Library and click <b>Edit</b> on any image,<br>
                or use the Detail View to start editing.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🖼️ Go to Library"):
        st.switch_page("pages/1_Library.py")


# ---------------------------------------------------------------------------
# Preset buttons
# ---------------------------------------------------------------------------
def _render_preset_buttons() -> str | None:
    """Render the 10 preset edit buttons in a grid layout.

    Returns:
        str | None: The selected preset prompt text, or None if nothing clicked.
    """
    st.markdown("##### ⚡ Quick Presets")
    st.markdown(
        "<p style='color:rgba(255,255,255,0.4);font-size:0.8rem;margin-bottom:1rem;'>"
        "One-click AI editing operations</p>",
        unsafe_allow_html=True,
    )

    preset_names = list(PRESET_PROMPTS.keys())
    selected_prompt = None

    # Render in rows of 5
    for row_start in range(0, len(preset_names), 5):
        row = preset_names[row_start: row_start + 5]
        cols = st.columns(len(row))
        for col, name in zip(cols, row):
            info = PRESET_PROMPTS[name]
            with col:
                st.markdown(
                    f"""
                    <div class="preset-btn">
                        <span class="preset-icon">{info['icon']}</span>
                        <span class="preset-label">{name}</span>
                        <span class="preset-desc">{info['description']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"{info['icon']} Go",
                    key=f"preset_{name.replace(' ', '_')}",
                    use_container_width=True,
                ):
                    selected_prompt = get_preset_prompt(name)

    return selected_prompt


# ---------------------------------------------------------------------------
# Edit page
# ---------------------------------------------------------------------------
def _render_edit_page(record: dict) -> None:
    """Render the full image editing interface.

    Args:
        record: Image metadata dict from the database.
    """
    image_id: str = record.get("id", "")
    filename: str = record.get("filename", "Unknown")
    filepath_str: str = record.get("filepath", "")
    caption: str = record.get("caption", "")
    versions: list = record.get("versions", [])
    filepath = Path(filepath_str) if filepath_str else None

    # ── Page header ──────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="page-header">
            <h1>✏️ Edit: {filename}</h1>
            <p>Use AI to edit this image with natural language or presets. Every edit creates a new version.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Determine which image to show ────────────────────────────────────
    # If user selected a version from timeline, show that; otherwise show latest
    display_path = filepath
    display_label = "Original"

    version_view = st.session_state.get("edit_version_view")
    if version_view and Path(version_view).exists():
        display_path = Path(version_view)
        display_label = f"Version ({Path(version_view).stem})"

    # Latest version for editing (always edit from latest)
    if versions:
        latest_version = versions[-1]
        latest_path = Path(latest_version.get("filepath", ""))
        if latest_path.exists():
            edit_source_path = latest_path
        else:
            edit_source_path = filepath
    else:
        edit_source_path = filepath

    # ── Top section: Image + Info + Prompt ────────────────────────────────
    col_img, col_edit = st.columns([3, 2], gap="large")

    with col_img:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        # Image preview
        if display_path and display_path.exists():
            st.image(str(display_path), use_container_width=True, caption=display_label)
        else:
            st.markdown(
                "<div style='height:350px;display:flex;align-items:center;"
                "justify-content:center;color:rgba(255,255,255,0.2);font-size:3rem;'>"
                "🖼️</div>",
                unsafe_allow_html=True,
            )

        # Caption
        if caption:
            st.markdown(
                f'<div class="caption-box"><p>🤖 "{caption}"</p></div>',
                unsafe_allow_html=True,
            )

        # Image info
        if display_path and display_path.exists():
            dims = get_image_dimensions(display_path)
            size_str = format_file_size(display_path.stat().st_size)
            dim_str = f"{dims[0]} × {dims[1]} px" if dims else "—"
            st.markdown(
                f"<p style='color:rgba(255,255,255,0.4);font-size:0.75rem;'>"
                f"📐 {dim_str} &nbsp;|&nbsp; 💾 {size_str} &nbsp;|&nbsp; "
                f"📁 {display_path.suffix.upper().lstrip('.')} &nbsp;|&nbsp; "
                f"🔄 {len(versions)} version(s)</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with col_edit:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        st.markdown("##### 💬 Custom Editing Prompt")
        st.markdown(
            "<p style='color:rgba(255,255,255,0.4);font-size:0.8rem;'>"
            "Describe what you want to change in natural language</p>",
            unsafe_allow_html=True,
        )

        # Prompt input
        user_prompt = st.text_area(
            "Edit instruction",
            placeholder="Remove the background",
            height=120,
            label_visibility="collapsed",
            key="edit_prompt_input",
        )

        st.markdown(
            "<p style='color:rgba(255,255,255,0.3);font-size:0.7rem;margin-top:0.25rem;'>"
            "💡 Examples: \"Remove the person\" · \"Replace background with mountains\" · "
            "\"Make it look like sunset\" · \"Add flowers\" · \"Turn into watercolor\"</p>",
            unsafe_allow_html=True,
        )

        # Buttons
        btn_col1, btn_col2 = st.columns(2)
        generate_clicked = btn_col1.button(
            "🚀 Generate Edit",
            use_container_width=True,
            key="btn_generate",
        )
        cancel_clicked = btn_col2.button(
            "❌ Cancel",
            use_container_width=True,
            key="btn_cancel",
        )

        if cancel_clicked:
            st.session_state["edit_result_path"] = None
            st.session_state["edit_error"] = None
            st.session_state["edit_version_view"] = None
            st.rerun()

        # ── Process edit ──────────────────────────────────────────────────
        if generate_clicked and user_prompt.strip():
            _execute_edit(
                image_id=image_id,
                edit_source_path=edit_source_path,
                user_prompt=user_prompt.strip(),
                versions=versions,
            )
        elif generate_clicked and not user_prompt.strip():
            st.error("❌ Please enter an editing instruction.")

        # ── Show error if present ─────────────────────────────────────────
        edit_error = st.session_state.get("edit_error")
        if edit_error:
            st.error(f"❌ {edit_error}")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Preset buttons ────────────────────────────────────────────────────
    st.markdown("---")
    preset_prompt = _render_preset_buttons()
    if preset_prompt:
        _execute_edit(
            image_id=image_id,
            edit_source_path=edit_source_path,
            user_prompt=preset_prompt,
            versions=versions,
        )

    # ── Comparison view ───────────────────────────────────────────────────
    edit_result = st.session_state.get("edit_result_path")
    if edit_result and Path(edit_result).exists():
        st.markdown("---")
        st.markdown("##### 🔄 Comparison — Original vs Edited")

        st.markdown(
            '<div class="edit-result-banner"><p>✅ Edit applied successfully! '
            'A new version has been saved.</p></div>',
            unsafe_allow_html=True,
        )

        comp_col1, comp_col2 = st.columns(2, gap="medium")

        with comp_col1:
            st.markdown('<div class="comparison-label">Before</div>', unsafe_allow_html=True)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if filepath and filepath.exists():
                st.image(str(filepath), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with comp_col2:
            st.markdown('<div class="comparison-label">After</div>', unsafe_allow_html=True)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.image(edit_result, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Version history (inline) ──────────────────────────────────────────
    if versions:
        st.markdown("---")
        st.markdown("##### 🕐 Version History Timeline")

        # Original
        st.markdown(
            f"""
            <div class="timeline-item" style="max-width:600px;">
                <div class="timeline-version">📌 Original</div>
                <div class="timeline-prompt">Original Upload</div>
                <div class="timeline-time">{record.get('uploaded_at', '—')[:16]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for v in versions:
            ver_num = v.get("version", "?")
            prompt_text = v.get("prompt", "—")
            ts = v.get("timestamp", "—")

            st.markdown(
                '<div class="timeline-connector" style="max-width:600px;">↓</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="timeline-item" style="max-width:600px;">
                    <div class="timeline-version">✏️ Version {ver_num}</div>
                    <div class="timeline-prompt">{prompt_text}</div>
                    <div class="timeline-time">{ts[:16] if len(ts) > 16 else ts}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Navigation ────────────────────────────────────────────────────────
    st.markdown("---")
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("⬅️ Back to Library"):
            st.switch_page("pages/1_Library.py")
    with nav2:
        if st.button("🔍 View Details"):
            st.switch_page("pages/2_Image_Detail.py")
    with nav3:
        if st.button("⬆️ Upload New"):
            st.switch_page("app.py")


def _execute_edit(
    image_id: str,
    edit_source_path: Path | None,
    user_prompt: str,
    versions: list,
) -> None:
    """Execute an image edit operation with spinner and error handling.

    Args:
        image_id:         UUID of the image.
        edit_source_path: Path to the image to edit (original or latest version).
        user_prompt:      The editing prompt.
        versions:         Current list of versions (to calculate next version num).
    """
    if not edit_source_path or not edit_source_path.exists():
        st.error("❌ Source image not found on disk.")
        return

    next_version = len(versions) + 1

    with st.spinner(f"🤖 Applying edit (Version {next_version}) … this may take 15–30 seconds"):
        result_path, error = edit_image(
            image_path=edit_source_path,
            user_prompt=user_prompt,
            image_id=image_id,
            version_num=next_version,
            images_dir=IMAGES_DIR,
            data_dir=DATA_DIR,
        )

    if error:
        st.session_state["edit_error"] = error
        st.session_state["edit_result_path"] = None
    else:
        st.session_state["edit_result_path"] = str(result_path)
        st.session_state["edit_error"] = None
        st.session_state["edit_version_view"] = str(result_path)

    st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Image Edit page."""
    _init_session_state()
    _inject_css()
    _render_sidebar()

    image_id = st.session_state.get("selected_image_id")

    if not image_id:
        st.markdown(
            """
            <div class="page-header">
                <h1>✏️ AI Image Editor</h1>
                <p>Select an image from the Library to start editing with AI.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_no_selection()
        return

    record = find_by_id(DATA_DIR, image_id)
    if record is None:
        st.error(
            f"❌ Image with ID `{image_id}` not found. "
            "It may have been deleted."
        )
        if st.button("🖼️ Go to Library"):
            st.switch_page("pages/1_Library.py")
        return

    _render_edit_page(record)


main()
