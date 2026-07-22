# AI-Powered Image Editing Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT_Image_&_Embeddings-412991?style=for-the-badge&logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB_|_FAISS-FF6F61?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-quality, modular AI-powered image management, editing, and semantic search platform built with Streamlit, OpenAI, Google Gemini, ChromaDB, and FAISS.**

[Features](#features) · [Architecture](#architecture) · [Installation](#installation) · [Usage](#usage) · [Deployment](#deployment-guide-streamlit-community-cloud) · [Roadmap](#future-roadmap)

</div>

---

## Overview

The **AI-Powered Image Editing Platform** is an end-to-end full-stack AI media management solution featuring semantic natural language search, AI image editing, version control, and multi-tiered vector search.

- **Week 1 Foundation**: Image upload, format validation, UUID storage, automatic AI captioning (GPT-4o / Gemini), JSON metadata, library grid view, and technical detail view.
- **Week 2 AI Editing & Version History**: Natural language image editing (`gpt-image-1` / Gemini), 10 one-click preset operations, non-destructive versioning history, side-by-side comparison, and prompt templates.
- **Week 3 Semantic Search & Backend Enhancements**: Natural language vector search, embeddings (`text-embedding-3-small` / Gemini), 3-tiered vector DB engine (**ChromaDB** → **FAISS** → **NumPy Cosine Similarity**), search suggestion chips, match percentage badges, and performance caching.

---

## Features

| Feature | Status |
|---|---|
| Image Upload (PNG, JPG, JPEG) & Integrity Validation | ✅ Week 1 |
| Automatic AI Caption Generation (OpenAI / Gemini) | ✅ Week 1 |
| JSON Metadata Persistence & Atomic File Writes | ✅ Week 1 |
| Responsive Library Grid View (search, sort, filter) | ✅ Week 1 |
| Technical Detail View (dimensions, size, UUID) | ✅ Week 1 |
| Natural Language AI Image Editing (OpenAI / Gemini) | ✅ Week 2 |
| 10 One-Click Preset Edit Operations | ✅ Week 2 |
| Non-Destructive Version History (never overwrites originals) | ✅ Week 2 |
| Side-by-Side Image Edit Comparison View | ✅ Week 2 |
| Version History Timeline with Timestamps & Prompts | ✅ Week 2 |
| Reusable Prompt Engineering Templates | ✅ Week 2 |
| Natural Language Semantic Search ("beach", "dog", "sunset") | ✅ Week 3 |
| Text & Caption Embeddings (`text-embedding-3-small` / Gemini) | ✅ Week 3 |
| Multi-Tier Vector Search Engine (**ChromaDB** / **FAISS** / **NumPy**) | ✅ Week 3 |
| Dedicated Search UI (`pages/4_Search.py`) & Preset Chips | ✅ Week 3 |
| Similarity Percentage Match Badges (`🎯 94.2% Match`) | ✅ Week 3 |
| Vector Embedding Caching (zero duplicate API charges) | ✅ Week 3 |

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      Streamlit UI Layer                       │
│ ┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌──────┐ │
│ │ app.py  │ │ Library │ │Image Detail │ │Image Edit│ │Search│ │
│ │(Upload) │ │ (Grid)  │ │ (Metadata)  │ │(AI Edit) │ │ (AI) │ │
│ └────┬────┘ └────┬────┘ └──────┬──────┘ └────┬─────┘ └──┬───┘ │
└──────┼───────────┼─────────────┼─────────────┼──────────┼─────┘
       │           │             │             │          │
┌──────▼───────────▼─────────────▼─────────────▼──────────▼─────┐
│                       Backend Layer                           │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ │
│ │ storage │ │database │ │ caption │ │image_edit│ │ embedding│ │
│ │   .py   │ │   .py   │ │   .py   │ │   .py    │ │   .py    │ │
│ └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘ └────┬─────┘ │
└──────┼───────────┼───────────┼───────────┼────────────┼───────┘
       │           │           │           │            │
  data/images/ metadata.json Vision API Image Edit API  Vector Store
                                                       (ChromaDB/
                                                        FAISS/NumPy)
```

### Design Principles

- **Separation of Concerns**: UI layer never touches disk directly; all storage and AI logic flow through `backend/`.
- **Stateless & Resilient**: All services receive root directory paths explicitly; imports trigger zero global state side effects.
- **Multi-Tiered Vector Search**: Automatically selects ChromaDB if available, falls back to FAISS, and guarantees execution via NumPy Cosine Similarity.
- **Non-Destructive Versioning**: Every edit creates a new version file (`{image_id}_v{N}.png`). Original files are never modified.

---

## Project Structure

```
ai-image-editor/
│
├── app.py                        # Entry point — Upload page + global config
├── pages/
│   ├── 1_Library.py              # Image grid with search & sort
│   ├── 2_Image_Detail.py         # Technical metadata + quick actions
│   ├── 3_Image_Edit.py           # AI editing + presets + version timeline
│   └── 4_Search.py               # Semantic vector search page (Week 3)
│
├── backend/
│   ├── __init__.py               # Package exports & docstring
│   ├── storage.py                # File-system image storage & path safety
│   ├── database.py               # JSON metadata persistence & atomic writes
│   ├── caption.py                # Vision API captioning & retry logic
│   ├── image_edit.py             # AI image editing engine (OpenAI & Gemini)
│   ├── prompt_templates.py       # Reusable prompt engineering templates
│   ├── embedding.py              # Vector embedding generation & caching (Week 3)
│   └── search.py                 # Multi-tiered vector search engine (Week 3)
│
├── data/
│   ├── images/                   # Uploaded & edited version images
│   ├── embeddings/               # Cached vector embeddings (JSON)
│   ├── chromadb/                 # Persistent ChromaDB vector index
│   ├── faiss/                    # FAISS binary vector index
│   └── metadata.json             # Application metadata store
│
├── requirements.txt
├── .env.example
├── .gitignore
├── sample_metadata.json          # Example metadata with embeddings
├── WEEK2_REPORT.md               # Week 2 project report
├── WEEK3_REPORT.md               # Week 3 project report
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip
- An OpenAI API key **or** a Google AI (Gemini) API key

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Turpu-Saandeep-Sai/AI-Image-editor-Week-2.git
cd AI-Image-editor-Week-2

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and paste your API key
```

---

## Environment Setup

Edit `.env` (copied from `.env.example`):

```dotenv
# Select provider: "openai" (default) or "gemini"
VISION_PROVIDER=openai

# OpenAI API Key (required when VISION_PROVIDER=openai)
OPENAI_API_KEY=sk-proj-...

# Google Gemini API Key (required when VISION_PROVIDER=gemini)
GOOGLE_API_KEY=AIza...
```

---

## Running Locally

```bash
streamlit run app.py
```

The application will open at **http://localhost:8501** in your web browser.

---

## Usage Guide

### 1. Uploading & Auto-Indexing

1. Navigate to the **Upload** page.
2. Drag & drop or browse for a PNG, JPG, or JPEG file.
3. The platform validates file integrity, assigns a UUID, saves the file to disk, generates a 40–60 word AI caption, generates a vector embedding, and indexes it into the vector database.

### 2. Library & Detail View

- Browse all uploaded images as responsive glassmorphism cards.
- Search by filename or text caption in the Library.
- Open **Detail View** to inspect dimensions, format, UUID, storage path, and version history.

### 3. AI Image Editing & Versions

- Open the **Edit** page for any image.
- Type a custom natural language instruction (e.g. *"Remove the background"*, *"Make it look like sunset"*, *"Turn into watercolor"*).
- Or click any of the **10 preset edit buttons** (*Remove Background*, *Replace Background*, *Blur Background*, *Change Sky*, *B&W*, *Vintage*, *Cartoon*, *Sharpen*, etc.).
- The edited result appears side-by-side with the original and is saved as a new version (`_v1.png`, `_v2.png`).

### 4. Semantic Natural Language Search (Week 3)

- Open **Semantic Search** (`pages/4_Search.py`).
- Type natural language concept queries such as *"beach"*, *"dog"*, *"sunset"*, *"people on mountain"*, *"night city"*, *"cars"*, or *"snow"*.
- Or click any of the **suggestion chips** for instant testing.
- View matching images ranked by similarity score percentage (`🎯 94.2% Match`).
- Filter by `Most Similar`, `Newest`, `Oldest`, or `Recently Edited`.

---

## API Reference

### `backend/embedding.py`

| Function | Signature | Description |
|---|---|---|
| `generate_embedding` | `(text, api_key, provider) → (list[float], str\|None)` | Generates float vector embedding |
| `save_embedding` | `(data_dir, image_id, vector) → bool` | Saves vector JSON to disk |
| `load_embedding` | `(data_dir, image_id) → list[float]\|None` | Loads cached vector from disk |
| `get_or_create_image_embedding` | `(data_dir, image_id, caption) → (list[float], str\|None)` | Retrieves cached or creates new vector |

### `backend/search.py`

| Function | Signature | Description |
|---|---|---|
| `get_active_vector_engine` | `() → str` | Returns `"ChromaDB"`, `"FAISS"`, or `"NumPy Cosine Similarity"` |
| `index_image` | `(data_dir, image_id, caption, metadata) → bool` | Indexes image into active vector store |
| `reindex_all_images` | `(data_dir) → int` | Reindexes missing items in bulk |
| `semantic_search` | `(query, data_dir, top_k, filter_option) → (list[dict], str\|None)` | Executes vector search & returns ranked results |

---

## Deployment Guide (Streamlit Community Cloud)

To deploy this application to **Streamlit Community Cloud**:

1. **Push your repository to GitHub**:
   ```bash
   git add .
   git commit -m "Deploy Week 3 AI Image Editing Platform"
   git push origin main
   ```

2. **Sign in to Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.

3. **Deploy New App**:
   - Click **New app**.
   - Select your repository: `Turpu-Saandeep-Sai/AI-Image-editor-Week-2` (or Week 3 repo).
   - Set **Branch**: `main`.
   - Set **Main file path**: `app.py`.

4. **Configure Secrets**:
   - In the deployment setup page, click **Advanced settings...** or open **Secrets** in app settings.
   - Add your API keys in TOML format:
     ```toml
     VISION_PROVIDER = "openai"
     OPENAI_API_KEY = "sk-proj-your-openai-api-key"
     GOOGLE_API_KEY = "your-google-api-key"
     ```

5. **Click Deploy**:
   - Streamlit will automatically install dependencies from `requirements.txt` and launch the app live at `https://<your-app-name>.streamlit.app`.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
