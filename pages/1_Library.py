"""
1_Library.py
------------
Library page for the AI-Powered Image Editing Platform.

Displays all uploaded images as responsive glass-morphism cards, each showing:
    - Thumbnail
    - Filename
    - Caption (truncated)
    - Upload date
    - "View" button linking to the Detail View

Author: AI Image Editor Platform
Version: 1.0.0
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

from backend.database import find_all
from backend.utils import format_file_size, format_timestamp_display

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR: Path = ROOT_DIR / "data"
IMAGES_DIR: Path = DATA_DIR / "images"

CARDS_PER_ROW: int = 3
CAPTION_PREVIEW_LENGTH: int = 120  # characters

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Image Editor — Library",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS (mirrors app.py global styles — injected on every page)
# ---------------------------------------------------------------------------

def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
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

        /* ── Image card ──────────────────────────────────────────────── */
        .img-card {
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            overflow: hidden;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .img-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(167,139,250,0.25);
            border-color: rgba(167,139,250,0.4);
        }
        .img-card-body {
            padding: 1rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        .img-card-title {
            color: #ffffff;
            font-weight: 600;
            font-size: 0.875rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .img-card-caption {
            color: rgba(255,255,255,0.55);
            font-size: 0.78rem;
            line-height: 1.5;
            flex: 1;
        }
        .img-card-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.5rem;
        }
        .meta-badge {
            background: rgba(167,139,250,0.15);
            border: 1px solid rgba(167,139,250,0.25);
            border-radius: 6px;
            padding: 0.15rem 0.5rem;
            font-size: 0.7rem;
            color: #a78bfa;
        }
        .date-label {
            color: rgba(255,255,255,0.3);
            font-size: 0.7rem;
        }

        /* ── Buttons ─────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #7c3aed, #4f46e5);
            color: white !important; border: none; border-radius: 8px;
            padding: 0.4rem 1rem; font-weight: 600; font-size: 0.8rem;
            width: 100%;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 0 4px 20px rgba(124,58,237,0.5);
            transform: translateY(-1px);
        }

        /* ── Search & filter bar ─────────────────────────────────────── */
        .filter-bar {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        /* ── Metric ──────────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 1rem;
        }
        [data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; }
        [data-testid="stMetricValue"] { color: #a78bfa !important; font-weight: 600; }

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
        all_records = find_all(DATA_DIR)
        captioned = sum(1 for r in all_records if r.get("caption"))
        c1, c2 = st.columns(2)
        c1.metric("Images", len(all_records))
        c2.metric("Captioned", captioned)
        st.markdown("---")
        st.markdown(
            "<p style='color:rgba(255,255,255,0.3);font-size:0.7rem;text-align:center;'>"
            "v3.0.0 · Built with Streamlit</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Filter / search bar
# ---------------------------------------------------------------------------
def _render_filter_bar(total: int) -> tuple[str, str]:
    """Render the search and sort controls above the image grid.

    Args:
        total: Total number of images (displayed as a subtitle).

    Returns:
        tuple[str, str]: (search_query, sort_option)
    """
    col_search, col_sort, col_info = st.columns([3, 2, 1])

    with col_search:
        search_query = st.text_input(
            "🔍 Search",
            placeholder="Search by filename or caption …",
            label_visibility="collapsed",
            key="lib_search",
        )
    with col_sort:
        sort_option = st.selectbox(
            "Sort",
            options=["Newest first", "Oldest first", "Filename A→Z", "Filename Z→A"],
            label_visibility="collapsed",
            key="lib_sort",
        )
    with col_info:
        st.markdown(
            f"<p style='color:rgba(255,255,255,0.4);font-size:0.85rem;"
            f"text-align:right;margin-top:0.5rem;'>{total} image(s)</p>",
            unsafe_allow_html=True,
        )

    return search_query, sort_option


# ---------------------------------------------------------------------------
# Card helpers
# ---------------------------------------------------------------------------
def _truncate(text: str, length: int) -> str:
    """Return *text* truncated to *length* characters with an ellipsis."""
    return text if len(text) <= length else text[:length].rstrip() + " …"


def _render_image_card(col, record: dict) -> None:
    """Render a single image card inside *col*.

    Args:
        col:    Streamlit column object.
        record: Image metadata dict from the database.
    """
    with col:
        fp = Path(record.get("filepath", ""))
        caption_text = record.get("caption", "")
        filename = record.get("filename", "Unknown")
        uploaded_at = record.get("uploaded_at", "")
        image_id = record.get("id", "")

        # Card HTML shell (body content is injected via st.* calls)
        st.markdown('<div class="img-card">', unsafe_allow_html=True)

        # Thumbnail
        if fp.exists():
            st.image(str(fp), use_container_width=True)
        else:
            st.markdown(
                "<div style='height:180px;background:rgba(255,255,255,0.05);"
                "border-bottom:1px solid rgba(255,255,255,0.08);"
                "display:flex;align-items:center;justify-content:center;"
                "color:rgba(255,255,255,0.25);font-size:2rem;'>🖼️</div>",
                unsafe_allow_html=True,
            )

        # Card body
        display_date = format_timestamp_display(uploaded_at) if uploaded_at else "—"
        short_caption = _truncate(caption_text, CAPTION_PREVIEW_LENGTH) if caption_text else "*(no caption)*"
        size_info = ""
        if fp.exists():
            size_info = format_file_size(fp.stat().st_size)

        st.markdown(
            f"""
            <div class="img-card-body">
                <div class="img-card-title" title="{filename}">{filename}</div>
                <div class="img-card-caption">{short_caption}</div>
                <div class="img-card-meta">
                    <span class="date-label">📅 {display_date[:12]}</span>
                    {"<span class='meta-badge'>"+size_info+"</span>" if size_info else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # View button
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🔍 View", key=f"view_{image_id}"):
                st.session_state["selected_image_id"] = image_id
                st.switch_page("pages/2_Image_Detail.py")
        with btn_c2:
            if st.button("✏️ Edit", key=f"edit_{image_id}"):
                st.session_state["selected_image_id"] = image_id
                st.switch_page("pages/3_Image_Edit.py")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main library grid
# ---------------------------------------------------------------------------
def _render_library_grid(records: list[dict]) -> None:
    """Render the responsive image card grid.

    Args:
        records: Filtered and sorted list of image metadata dicts.
    """
    if not records:
        st.markdown(
            """
            <div style="text-align:center; padding:4rem; opacity:0.5;">
                <span style="font-size:4rem;">🗂️</span>
                <h3 style="color:rgba(255,255,255,0.6); margin-top:1rem;">
                    No images found
                </h3>
                <p style="color:rgba(255,255,255,0.35);">
                    Upload an image to get started.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Build rows of CARDS_PER_ROW
    for row_start in range(0, len(records), CARDS_PER_ROW):
        row_records = records[row_start: row_start + CARDS_PER_ROW]
        cols = st.columns(CARDS_PER_ROW, gap="medium")

        for col, record in zip(cols, row_records):
            _render_image_card(col, record)

        # Pad empty columns in the last row
        for empty_col in cols[len(row_records):]:
            with empty_col:
                st.empty()

        st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Filtering & sorting logic
# ---------------------------------------------------------------------------
def _apply_filters(
    records: list[dict],
    search_query: str,
    sort_option: str,
) -> list[dict]:
    """Filter and sort *records* based on the user's controls.

    Args:
        records:      Raw list from the database.
        search_query: Text to match against filename and caption.
        sort_option:  One of the sort option strings from the UI.

    Returns:
        list[dict]: Filtered and sorted records.
    """
    # Search filter
    if search_query.strip():
        q = search_query.strip().lower()
        records = [
            r for r in records
            if q in r.get("filename", "").lower()
            or q in r.get("caption", "").lower()
        ]

    # Sort
    if sort_option == "Oldest first":
        records = sorted(records, key=lambda r: r.get("uploaded_at", ""))
    elif sort_option == "Filename A→Z":
        records = sorted(records, key=lambda r: r.get("filename", "").lower())
    elif sort_option == "Filename Z→A":
        records = sorted(records, key=lambda r: r.get("filename", "").lower(), reverse=True)
    else:  # "Newest first" (default)
        records = sorted(records, key=lambda r: r.get("uploaded_at", ""), reverse=True)

    return records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Library page."""
    # Ensure session state keys exist
    if "selected_image_id" not in st.session_state:
        st.session_state["selected_image_id"] = None

    _inject_css()
    _render_sidebar()

    # Page header
    st.markdown(
        """
        <div class="page-header">
            <h1>🖼️ Image Library</h1>
            <p>Browse, search, and manage all your uploaded images.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load all records
    all_records = find_all(DATA_DIR)

    # Stats row
    total = len(all_records)
    captioned = sum(1 for r in all_records if r.get("caption"))
    no_caption = total - captioned

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📸 Total Images", total)
    m2.metric("🤖 Captioned", captioned)
    m3.metric("⏳ Pending Caption", no_caption)
    m4.metric("📁 Storage", _total_storage_size())

    st.markdown("---")

    # Search & sort
    search_query, sort_option = _render_filter_bar(total)

    # Apply filters
    filtered_records = _apply_filters(all_records, search_query, sort_option)

    st.markdown(f"<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    # Grid
    _render_library_grid(filtered_records)

    # Upload CTA when library is empty
    if not all_records:
        if st.button("⬆️ Upload your first image", use_container_width=True):
            st.switch_page("app.py")


def _total_storage_size() -> str:
    """Calculate and format the total disk space used by stored images."""
    from backend.utils import format_file_size
    if not IMAGES_DIR.exists():
        return "0 B"
    total_bytes = sum(f.stat().st_size for f in IMAGES_DIR.iterdir() if f.is_file())
    return format_file_size(total_bytes)


main()
