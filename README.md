# AI-Powered Image Editing Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT_Image-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-quality, modular AI-powered image management and editing platform built with Streamlit, OpenAI GPT Image API, and Google Gemini.**

[Features](#features) · [Architecture](#architecture) · [Installation](#installation) · [Usage](#usage) · [Roadmap](#roadmap)

</div>

---

## Overview

The **AI-Powered Image Editing Platform** is a multi-week project building towards a full-stack AI image editor with semantic search, version history, and intelligent editing.

**Week 1** delivered the **image management foundation**:
- Upload PNG / JPG / JPEG images with full validation
- Automatic AI caption generation via OpenAI GPT-4o Vision (or Gemini)
- JSON-backed metadata persistence with atomic writes
- Responsive library view with search, sort, and filter
- Detailed image view with full technical metadata

**Week 2** adds **AI-powered image editing and version history**:
- Edit images using natural language instructions
- 10 one-click preset editing operations
- Non-destructive version history (every edit creates a new version)
- Side-by-side comparison of original vs edited
- Version history timeline with thumbnails and prompts
- Reusable prompt engineering templates
- Support for both OpenAI GPT Image API and Gemini Image Editing API

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
| AI Image Editing (natural language) | ✅ Week 2 |
| 10 Preset Edit Operations | ✅ Week 2 |
| Custom Prompt Editing | ✅ Week 2 |
| Non-destructive Version History | ✅ Week 2 |
| Version History Timeline UI | ✅ Week 2 |
| Side-by-side Comparison | ✅ Week 2 |
| Prompt Engineering Templates | ✅ Week 2 |
| Semantic search (embeddings) | 🔜 Week 3 |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Streamlit UI Layer                      │
│  ┌────────┐  ┌──────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ app.py │  │ Library  │  │ Image Detail│  │ Image Edit│  │
│  │(Upload)│  │  (Grid)  │  │ (Metadata)  │  │ (AI Edit) │  │
│  └───┬────┘  └────┬─────┘  └──────┬──────┘  └─────┬─────┘  │
└──────┼────────────┼───────────────┼────────────────┼────────┘
       │            │               │                │
┌──────▼────────────▼───────────────▼────────────────▼────────┐
│                      Backend Layer                           │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐ │
│  │storage │ │database│ │caption │ │image_edit│ │ prompt  │ │
│  │  .py   │ │  .py   │ │  .py   │ │   .py    │ │templates│ │
│  └───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └─────────┘ │
└──────┼──────────┼──────────┼───────────┼────────────────────┘
       │          │          │           │
  data/images/ metadata.json  OpenAI / Gemini APIs
```

### Design Principles

- **Separation of concerns**: UI layer never touches the filesystem directly; all I/O goes through `backend/`.
- **Stateless modules**: Every backend function accepts all its dependencies as arguments — no module-level globals, no hidden state.
- **Non-destructive editing**: Every edit creates a new version file; originals are never overwritten.
- **Extensibility**: The metadata schema and storage layer support unlimited version chains. The database module can be swapped for SQLite with minimal interface changes.
- **Safety**: Path traversal prevention in `storage.py`; atomic JSON writes in `database.py`.

---

## Project Structure

```
ai-image-editor/
│
├── app.py                        # Entry point — Upload page + global config
├── pages/
│   ├── 1_Library.py              # Image grid with search & sort
│   ├── 2_Image_Detail.py         # Full metadata + action panel
│   └── 3_Image_Edit.py           # AI editing + presets + version history
│
├── backend/
│   ├── __init__.py
│   ├── storage.py                # File-system image management
│   ├── database.py               # JSON metadata persistence
│   ├── caption.py                # OpenAI / Gemini Vision API (captioning)
│   ├── image_edit.py             # AI image editing engine (Week 2)
│   ├── prompt_templates.py       # Reusable prompt templates (Week 2)
│   └── utils.py                  # UUID, timestamps, validation, thumbnails
│
├── data/
│   ├── images/                   # Uploaded + versioned images (UUID-named)
│   └── metadata.json             # Auto-created on first upload
│
├── assets/                       # Static assets (logos, icons — future)
│
├── requirements.txt
├── .env.example
├── .gitignore
├── sample_metadata.json          # Example metadata with version history
├── WEEK2_REPORT.md               # Week 2 project report
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

> **Note**: Only one provider needs to be configured. The same provider is used for both captioning and image editing.

---

## Running Locally

```bash
streamlit run app.py
```

The app will open at **http://localhost:8501** in your default browser.

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
- Click **🔍 View** on any card to open the Detail View.
- Click **✏️ Edit** on any card to open the Image Editor.

### Detail View

- See the full-resolution image alongside all technical metadata.
- Copy the UUID for programmatic access.
- Navigate between images using the **Previous / Next** controls.
- Click **✏️ Edit Image** to start editing.
- View the **Version History** section to see all edits.

### Image Editing (Week 2)

1. Open any image in the **Edit** page.
2. **Custom edit**: Type a natural language instruction (e.g., "Remove the background").
3. **Preset edit**: Click one of the 10 preset buttons for one-click editing.
4. Click **🚀 Generate Edit** and wait 15–30 seconds.
5. The edited image appears in a **side-by-side comparison**.
6. A new version is automatically saved and tracked.

### Preset Edit Operations

| Preset | What it does |
|--------|-------------|
| 🗑️ Remove Background | Remove background, keep subject |
| 🧹 Remove All Objects | Remove objects, keep background |
| 🏞️ Replace Background | Replace with scenic landscape |
| 🔍 Blur Background | Apply bokeh blur effect |
| 🌅 Change Sky | Replace sky with sunset |
| 🖤 Black & White | High-contrast B&W with film grain |
| ☀️ Increase Brightness | Brighten naturally |
| 📷 Vintage Style | Warm vintage film look |
| 🎨 Cartoon Style | Transform into illustration |
| 🔬 Sharpen Image | Enhance detail and clarity |

### Version History

- Every edit creates a new version; originals are never overwritten.
- The **sidebar timeline** shows all versions with prompts and timestamps.
- Click **Open** on any version to view it.
- The **inline timeline** on the edit page shows the full edit chain.

---

## API Reference

### Backend Modules

#### `backend/utils.py`

| Function | Description |
|---|---|
| `generate_uuid()` | Generates a UUID4 string |
| `timestamp()` | Returns current UTC timestamp |
| `image_validation(bytes, str)` | Validates format & integrity |
| `thumbnail_creation(Path, tuple)` | Creates in-memory thumbnail |
| `format_file_size(int)` | Formats bytes as human-readable |
| `get_image_dimensions(Path)` | Returns (width, height) |
| `version_name(str, int, str)` | Generates versioned filename (Week 2) |
| `create_thumbnail(Path, Path, tuple)` | Saves thumbnail to disk (Week 2) |

#### `backend/storage.py`

| Function | Description |
|---|---|
| `save_image(bytes, str, Path)` | Persists image bytes to disk |
| `load_image(Path)` | Opens image from disk |
| `delete_image(Path)` | Removes image file |
| `list_images(Path)` | Lists all stored images |
| `save_version_image(bytes, str, int, Path)` | Saves versioned image (Week 2) |

#### `backend/database.py`

| Function | Description |
|---|---|
| `load_metadata(Path)` | Reads JSON metadata store |
| `save_metadata(Path, list)` | Writes JSON metadata store |
| `add_metadata(Path, dict)` | Appends a new record |
| `find_by_id(Path, str)` | Finds record by UUID |
| `find_all(Path, ...)` | Returns all records, sorted |
| `update_metadata(Path, str, dict)` | Updates fields on a record |
| `delete_metadata(Path, str)` | Removes a record |
| `add_version(Path, str, dict)` | Appends version to record (Week 2) |
| `load_versions(Path, str)` | Returns version list (Week 2) |

#### `backend/caption.py`

| Function | Description |
|---|---|
| `generate_caption(Path, ...)` | Full caption pipeline |
| `vision_api(bytes, str, str, str)` | Dispatches to provider |
| `retry_logic(...)` | Exponential back-off retry decorator |

#### `backend/image_edit.py` (Week 2)

| Function | Description |
|---|---|
| `edit_image(Path, str, str, int, Path, Path, ...)` | Full edit pipeline |
| `call_edit_api(bytes, str, str, str)` | Dispatches to editing provider |
| `save_version(bytes, str, int, Path)` | Saves edited version to disk |

#### `backend/prompt_templates.py` (Week 2)

| Function | Description |
|---|---|
| `build_edit_prompt(str, str)` | Combines system + user prompt |
| `get_preset_names()` | Returns preset name list |
| `get_preset_prompt(str)` | Returns prompt for a preset |

---

## Testing Instructions

1. **Start the app**: `streamlit run app.py`
2. **Upload an image**: Go to the Upload page and upload a PNG/JPG file.
3. **Verify caption**: Check that an AI caption is generated.
4. **Browse library**: Go to the Library and verify the image card appears.
5. **Edit an image**: Click ✏️ Edit → type "Remove the background" → click 🚀 Generate Edit.
6. **Check comparison**: Verify the before/after comparison appears.
7. **Check versions**: Look at the sidebar timeline — Version 1 should appear.
8. **Try presets**: Click any preset button and verify a new version is created.
9. **Check metadata**: Open `data/metadata.json` and verify the versions array is populated.
10. **Error handling**: Remove the API key from `.env` and verify a clear error message appears.

---

## Future Roadmap

### Week 3 — Semantic Search
- [ ] Generate image embeddings (OpenAI `text-embedding-3-small`)
- [ ] FAISS or ChromaDB vector store integration
- [ ] Natural language image search ("show me photos of cats outdoors")
- [ ] Similar image recommendations

### Week 4 — Production Features
- [ ] PostgreSQL / SQLite backend (replace JSON)
- [ ] User authentication
- [ ] Export / download edited images
- [ ] Performance optimisations (lazy loading, pagination)
- [ ] Deployment guide (Docker, Streamlit Cloud, AWS)

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
