"""
4_Search.py
-----------
Semantic Search page for the AI-Powered Image Editing Platform.

Features:
    - Natural language query box ("beach", "dog", "people on mountain", "sunset", etc.)
    - 8 quick suggestion chips for one-click testing
    - Multi-tiered vector database query execution (ChromaDB -> FAISS -> NumPy Cosine Similarity)
    - Active Vector Engine status indicator badge
    - Sort & filter options ("Most Similar", "Newest", "Oldest", "Recently Edited")
    - Recent searches history tracker
    - Responsive card grid displaying image thumbnails, similarity score percentages, captions,
      and quick navigation buttons to Detail View & Image Editor.

Author: AI Image Editor Platform
Version: 3.0.0
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
from backend.search import (
    get_active_vector_engine,
    reindex_all_images,
    semantic_search,
)
from backend.utils import format_file_size, format_timestamp_display

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR: Path = ROOT_DIR / "data"
IMAGES_DIR: Path = DATA_DIR / "images"
CARDS_PER_ROW: int = 3
SEARCH_SUGGESTIONS: list[str] = [
    "beach",
    "dog",
    "people on mountain",
    "sunset",
    "red flowers",
    "night city",
    "cars",
    "snow",
]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Image Editor — Semantic Search",
    page_icon="🔎",
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

        /* ── Image card ─────────────────────────────────────────── */
        .search-card {
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
        .search-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(167,139,250,0.25);
            border-color: rgba(167,139,250,0.4);
        }
        .search-card-body {
            padding: 1rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        .search-card-title {
            color: #ffffff;
            font-weight: 600;
            font-size: 0.875rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .search-card-caption {
            color: rgba(255,255,255,0.65);
            font-size: 0.78rem;
            line-height: 1.5;
            flex: 1;
        }
        .score-badge {
            background: linear-gradient(90deg, rgba(52,211,153,0.2), rgba(96,165,250,0.2));
            border: 1px solid rgba(52,211,153,0.4);
            border-radius: 20px;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 700;
            color: #34d399;
            display: inline-block;
        }
        .engine-badge {
            background: rgba(167,139,250,0.15);
            border: 1px solid rgba(167,139,250,0.3);
            border-radius: 20px;
            padding: 0.3rem 0.8rem;
            font-size: 0.75rem;
            color: #a78bfa;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        /* ── Suggestion chips ───────────────────────────────────── */
        .suggestion-chip {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 20px;
            padding: 0.3rem 0.75rem;
            font-size: 0.78rem;
            color: rgba(255,255,255,0.8);
            cursor: pointer;
            transition: all 0.2s ease;
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
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_session_state() -> None:
    defaults = {
        "selected_image_id": None,
        "search_query": "",
        "recent_searches": [],
        "search_results": None,
        "search_error": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


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
                    Week 3 · Semantic Search & AI Platform
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

        # Vector Engine Info
        engine_name = get_active_vector_engine()
        st.markdown("**⚡ Vector Engine**")
        st.markdown(
            f"""
            <div class="engine-badge">
                <span>⚡</span> {engine_name}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

        if st.button("🔄 Sync / Reindex Vectors", use_container_width=True, key="reindex_btn"):
            with st.spinner("Reindexing vector embeddings..."):
                count = reindex_all_images(DATA_DIR)
                st.success(f"Indexed {count} image(s)!")

        # Recent searches
        recent = st.session_state.get("recent_searches", [])
        if recent:
            st.markdown("---")
            st.markdown("**🕐 Recent Searches**")
            for q in recent[:5]:
                if st.button(f"🔍 {q}", key=f"recent_q_{q}", use_container_width=True):
                    st.session_state["search_query"] = q
                    st.rerun()

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


# ---------------------------------------------------------------------------
# Search card renderer
# ---------------------------------------------------------------------------
def _render_search_card(col, record: dict) -> None:
    """Render a search result card inside *col*."""
    with col:
        fp = Path(record.get("filepath", ""))
        caption_text = record.get("caption", "")
        filename = record.get("filename", "Unknown")
        uploaded_at = record.get("uploaded_at", "")
        image_id = record.get("id", "")
        score = record.get("similarity_score", 0.0)

        st.markdown('<div class="search-card">', unsafe_allow_html=True)

        # Thumbnail preview
        if fp.exists():
            st.image(str(fp), use_container_width=True)
        else:
            st.markdown(
                "<div style='height:180px;background:rgba(255,255,255,0.05);"
                "display:flex;align-items:center;justify-content:center;"
                "color:rgba(255,255,255,0.25);font-size:2rem;'>🖼️</div>",
                unsafe_allow_html=True,
            )

        # Card body
        display_date = format_timestamp_display(uploaded_at) if uploaded_at else "—"
        ver_count = len(record.get("versions", []))

        st.markdown(
            f"""
            <div class="search-card-body">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
                    <span class="score-badge">🎯 {score}% Match</span>
                    <span style="color:rgba(255,255,255,0.35); font-size:0.7rem;">📅 {display_date[:12]}</span>
                </div>
                <div class="search-card-title" title="{filename}">{filename}</div>
                <div class="search-card-caption">"{caption_text}"</div>
                <div style="color:rgba(255,255,255,0.4); font-size:0.7rem; margin-top:0.2rem;">
                    🔄 {ver_count} version(s)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick action buttons
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🔍 View", key=f"s_view_{image_id}"):
                st.session_state["selected_image_id"] = image_id
                st.switch_page("pages/2_Image_Detail.py")
        with btn_c2:
            if st.button("✏️ Edit", key=f"s_edit_{image_id}"):
                st.session_state["selected_image_id"] = image_id
                st.switch_page("pages/3_Image_Edit.py")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results Grid
# ---------------------------------------------------------------------------
def _render_results_grid(records: list[dict]) -> None:
    """Render search result cards in a grid."""
    if not records:
        st.markdown(
            """
            <div style="text-align:center; padding:4rem; opacity:0.5;">
                <span style="font-size:4rem;">🔎</span>
                <h3 style="color:rgba(255,255,255,0.6); margin-top:1rem;">
                    No matching images found
                </h3>
                <p style="color:rgba(255,255,255,0.35);">
                    Try adjusting your natural language query or selecting a suggestion above.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for row_start in range(0, len(records), CARDS_PER_ROW):
        row_records = records[row_start: row_start + CARDS_PER_ROW]
        cols = st.columns(CARDS_PER_ROW, gap="medium")

        for col, record in zip(cols, row_records):
            _render_search_card(col, record)

        for empty_col in cols[len(row_records):]:
            with empty_col:
                st.empty()

        st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Semantic Search page UI."""
    _init_session_state()
    _inject_css()
    _render_sidebar()

    # Header
    st.markdown(
        """
        <div class="page-header">
            <h1>🔎 Natural Language Image Search</h1>
            <p>Search your entire image library semantically using AI embeddings. Search by concept, scene, object, or style.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Search & Filter Controls ──────────────────────────────────────────
    col_input, col_filter = st.columns([3, 1], gap="medium")

    with col_input:
        current_query_val = st.session_state.get("search_query", "")
        query_input = st.text_input(
            "Natural Language Query",
            value=current_query_val,
            placeholder="Type 'beach', 'dog', 'sunset', 'night city', 'people on mountain'...",
            label_visibility="collapsed",
            key="main_search_input",
        )

    with col_filter:
        filter_option = st.selectbox(
            "Sort & Rank By",
            options=["Most Similar", "Newest", "Oldest", "Recently Edited"],
            label_visibility="collapsed",
            key="search_filter_opt",
        )

    # ── Quick Suggestion Chips ────────────────────────────────────────────
    st.markdown("##### 💡 Try searching for:")
    chip_cols = st.columns(len(SEARCH_SUGGESTIONS))
    for col, tag in zip(chip_cols, SEARCH_SUGGESTIONS):
        with col:
            if st.button(tag, key=f"chip_{tag}", use_container_width=True):
                st.session_state["search_query"] = tag
                st.rerun()

    st.markdown("---")

    # ── Execute Search ────────────────────────────────────────────────────
    search_term = query_input.strip()

    if search_term:
        # Save search to recent list
        recent = st.session_state.get("recent_searches", [])
        if search_term not in recent:
            recent.insert(0, search_term)
            st.session_state["recent_searches"] = recent[:10]

        with st.spinner("🤖 Computing vector embeddings and querying index..."):
            results, error_msg = semantic_search(
                query=search_term,
                data_dir=DATA_DIR,
                top_k=12,
                filter_option=filter_option,
            )

        if error_msg:
            st.error(f"❌ Search Error: {error_msg}")
        else:
            st.markdown(
                f"<p style='color:rgba(255,255,255,0.6); font-size:0.9rem; margin-bottom:1.5rem;'>"
                f"Showing top matches for: <b style='color:#a78bfa;'>\"{search_term}\"</b> "
                f"({len(results)} results found using {get_active_vector_engine()})</p>",
                unsafe_allow_html=True,
            )
            _render_results_grid(results)

    else:
        st.info("💡 Enter a query above or click any suggestion chip to search your images using AI embeddings.")
        # Show all images as initial view
        all_records = find_all(DATA_DIR)
        if all_records:
            st.markdown("##### 🖼️ All Images in Library")
            _render_results_grid(all_records)


main()
