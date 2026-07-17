# AI-Powered Image Editing Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-quality, modular AI-powered image management platform built with Streamlit and the OpenAI Vision API.**

[Features](#features) · [Architecture](#architecture) · [Installation](#installation) · [Usage](#usage) · [Roadmap](#roadmap)

</div>

---

## Overview

The **AI-Powered Image Editing Platform** is a multi-week project building towards a full-stack AI image editor with semantic search, version history, and intelligent editing.

**Week 1** delivers the **image management foundation**:
- Upload PNG / JPG / JPEG images with full validation
- Automatic AI caption generation via OpenAI GPT-4o Vision (or Gemini)
- JSON-backed metadata persistence with atomic writes
- Responsive library view with search, sort, and filter
- Detailed image view with full technical metadata

---

## Features

| Feature | Status |
|---|---|
| Image Upload (PNG, JPG, JPEG) | ✅ Week 1 |
| Format & integrity validation | ✅ Week 1 |
| UUID-based storage | ✅ Week 1 |
| AI Caption Generation (OpenAI / Gemini) | ✅ Week 1 |
| Retry logic with exponential back-off | ✅ Week 1 |
| JSON metadata persistence (atomic writes) | ✅ Week 1 |
| Library View (search, sort, filter) | ✅ Week 1 |
| Detail View (dimensions, size, UUID) | ✅ Week 1 |
| Glassmorphism UI with dark gradient theme | ✅ Week 1 |
| Image editing (AI-powered) | 🔜 Week 2 |
| Version history | 🔜 Week 2 |
| Semantic search (embeddings) | 🔜 Week 3 |
| Delete / batch operations | 🔜 Week 2 |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI Layer                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  app.py  │  │  1_Library   │  │ 2_Image_Detail│ │
│  │ (Upload) │  │   (Grid)     │  │  (Metadata)   │ │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘ │
└───────┼───────────────┼──────────────────┼─────────┘
        │               │                  │
┌───────▼───────────────▼──────────────────▼─────────┐
│                  Backend Layer                      │
│  ┌───────────┐ ┌───────────┐ ┌────────┐ ┌────────┐ │
│  │ storage.py│ │database.py│ │caption │ │ utils  │ │
│  │  (Files)  │ │  (JSON)   │ │  .py   │ │  .py   │ │
│  └─────┬─────┘ └─────┬─────┘ └───┬────┘ └────────┘ │
└────────┼─────────────┼───────────┼─────────────────┘
         │             │           │
    data/images/   metadata.json  OpenAI / Gemini API
```

### Design Principles

- **Separation of concerns**: UI layer never touches the filesystem directly; all I/O goes through `backend/`.
- **Stateless modules**: Every backend function accepts all its dependencies as arguments — no module-level globals, no hidden state.
- **Extensibility**: The metadata schema (`versions: []`) and storage layer are designed for Week 2 version history. The database module can be swapped for SQLite with minimal interface changes.
- **Safety**: Path traversal prevention in `storage.py`; atomic JSON writes in `database.py`.

---

## Project Structure

```
ai-image-editor/
│
├── app.py                  # Entry point — Upload page + global config
├── pages/
│   ├── 1_Library.py        # Image grid with search & sort
│   └── 2_Image_Detail.py   # Full metadata + action panel
│
├── backend/
│   ├── __init__.py
│   ├── storage.py          # File-system image management
│   ├── database.py         # JSON metadata persistence
│   ├── caption.py          # OpenAI / Gemini Vision API
│   └── utils.py            # UUID, timestamps, validation, thumbnails
│
├── data/
│   ├── images/             # Uploaded images (UUID-named)
│   └── metadata.json       # Auto-created on first upload
│
├── assets/                 # Static assets (logos, icons — future)
│
├── requirements.txt
├── .env.example
├── .gitignore
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
git clone https://github.com/your-username/ai-image-editor.git
cd ai-image-editor

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API key
```

---

## Environment Setup

Edit `.env` (copy from `.env.example`):

```dotenv
# Choose your Vision provider: "openai" or "gemini"
VISION_PROVIDER=openai

# OpenAI (default)
OPENAI_API_KEY=sk-...

# Google Gemini (alternative)
GOOGLE_API_KEY=AIza...
```

> **Note**: Only one provider needs to be configured. The app will fall back to an empty caption with a clear error message if the API key is missing.

---

## Running Locally

```bash
streamlit run app.py
```

The app will open at **http://localhost:8501** in your default browser.

---

## Screenshots

> _Screenshots will be added after the first deployment._

| Upload Page | Library View | Detail View |
|---|---|---|
| _(screenshot)_ | _(screenshot)_ | _(screenshot)_ |

---

## Usage Guide

### Uploading an Image

1. Navigate to the **Upload** page (default home).
2. Drag & drop or browse for a PNG, JPG, or JPEG file.
3. A preview is shown immediately.
4. The app validates the file format and integrity.
5. An AI caption is generated automatically (10–30 seconds).
6. The image appears in the **Library** once complete.

### Library View

- Browse all uploaded images as responsive cards.
- Use the **search bar** to filter by filename or caption text.
- Sort by **newest, oldest, or filename**.
- Click **View Details** on any card to open the Detail View.

### Detail View

- See the full-resolution image alongside all technical metadata.
- Copy the UUID for programmatic access.
- Navigate between images using the **Previous / Next** controls.
- Action buttons (Edit, Versions, Delete, Semantic Search) are placeholders for future weeks.

---

## API Reference

### Backend Modules

#### `backend/utils.py`

| Function | Signature | Description |
|---|---|---|
| `generate_uuid` | `() → str` | Generates a UUID4 string |
| `timestamp` | `() → str` | Returns current UTC timestamp |
| `image_validation` | `(bytes, str) → (bool, str)` | Validates format & integrity |
| `thumbnail_creation` | `(Path, tuple) → Image` | Creates in-memory thumbnail |
| `format_file_size` | `(int) → str` | Formats bytes as human-readable |
| `get_image_dimensions` | `(Path) → tuple` | Returns (width, height) |

#### `backend/storage.py`

| Function | Signature | Description |
|---|---|---|
| `save_image` | `(bytes, str, Path) → Path` | Persists image bytes to disk |
| `load_image` | `(Path) → Image` | Opens image from disk |
| `delete_image` | `(Path) → bool` | Removes image file |
| `list_images` | `(Path) → list[dict]` | Lists all stored images |

#### `backend/database.py`

| Function | Signature | Description |
|---|---|---|
| `load_metadata` | `(Path) → list[dict]` | Reads JSON metadata store |
| `save_metadata` | `(Path, list) → bool` | Writes JSON metadata store |
| `add_metadata` | `(Path, dict) → bool` | Appends a new record |
| `find_by_id` | `(Path, str) → dict` | Finds record by UUID |
| `find_all` | `(Path, ...) → list[dict]` | Returns all records, sorted |
| `update_metadata` | `(Path, str, dict) → bool` | Updates fields on a record |
| `delete_metadata` | `(Path, str) → bool` | Removes a record |

#### `backend/caption.py`

| Function | Signature | Description |
|---|---|---|
| `generate_caption` | `(Path, ...) → (str, str\|None)` | Full caption pipeline |
| `vision_api` | `(bytes, str, str, str) → str` | Dispatches to provider |
| `retry_logic` | `decorator` | Exponential back-off retry |

---

## Future Roadmap

### Week 2 — AI Image Editing
- [ ] Edit images using AI (OpenAI DALL-E 3 inpainting or Gemini Imagen)
- [ ] Version history with diff viewer
- [ ] Delete & batch operations
- [ ] Streamlit-based editing canvas

### Week 3 — Semantic Search
- [ ] Generate image embeddings (OpenAI `text-embedding-3-small`)
- [ ] FAISS or ChromaDB vector store integration
- [ ] Natural language image search ("show me photos of cats outdoors")
- [ ] Similar image recommendations

### Week 4 — Production Features
- [ ] PostgreSQL / SQLite backend (replace JSON)
- [ ] User authentication (Streamlit Community Cloud secrets)
- [ ] Export / download edited images
- [ ] Performance optimisations (lazy loading, pagination)
- [ ] Deployment guide (Docker, Streamlit Cloud, AWS)

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
