"""
embedding.py
------------
Vector embedding generation and persistence for the AI-Powered Image Editing Platform.

Responsibilities:
    - generate_embedding():          Generates vector embeddings for text via OpenAI or Gemini.
    - save_embedding():              Persists vector embeddings to disk as JSON files.
    - load_embedding():              Loads cached vector embeddings from disk.
    - get_or_create_image_embedding(): High-level helper that checks cache before calling API,
                                     preventing duplicate API charges and redundant computation.

Supported embedding providers:
    - OpenAI (default): ``text-embedding-3-small`` (1536 dimensions)
    - Gemini (alternative): ``text-embedding-004`` (768 dimensions)

Provider resolution follows the project standard: ``VISION_PROVIDER`` env var or explicit param.

Author: AI Image Editor Platform
Version: 3.0.0
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from backend.caption import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_RETRIES,
    retry_logic,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
EMBEDDINGS_DIR_NAME: str = "embeddings"

# In-memory cache to prevent re-reading disk unnecessarily during a single process run
_EMBEDDING_CACHE: dict[str, list[float]] = {}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _embeddings_dir(data_dir: Path) -> Path:
    """Return the absolute path to the embeddings directory, ensuring it exists."""
    path = data_dir / EMBEDDINGS_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _embedding_file_path(data_dir: Path, image_id: str) -> Path:
    """Return the file path for a specific image's embedding JSON file."""
    return _embeddings_dir(data_dir) / f"{image_id}.json"


# ---------------------------------------------------------------------------
# OpenAI Embedding Call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_openai_embedding(
    api_key: str,
    text: str,
) -> list[float]:
    """Call OpenAI Embedding API and return float vector list.

    Args:
        api_key: OpenAI API Key.
        text: Input text string (e.g. image caption or search query).

    Returns:
        list[float]: Embedding vector (1536 float values).
    """
    try:
        import openai
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for OpenAI embeddings. "
            "Install it with: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text,
    )

    if not response.data or len(response.data) == 0:
        raise RuntimeError("OpenAI Embedding API returned empty data response.")

    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Gemini Embedding Call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_gemini_embedding(
    api_key: str,
    text: str,
) -> list[float]:
    """Call Google Gemini Embedding API and return float vector list.

    Args:
        api_key: Google AI Studio API Key.
        text: Input text string.

    Returns:
        list[float]: Embedding vector (768 float values).
    """
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "The 'google-genai' package is required for Gemini embeddings. "
            "Install it with: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
    )

    if not hasattr(response, "embedding") or not response.embedding:
        raise RuntimeError("Gemini Embedding API returned an empty embedding response.")

    if hasattr(response.embedding, "values"):
        return list(response.embedding.values)

    return list(response.embedding)


# ---------------------------------------------------------------------------
# Public Embedding Generation API
# ---------------------------------------------------------------------------

def generate_embedding(
    text: str,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[list[float], Optional[str]]:
    """Generate a high-dimensional vector embedding for *text*.

    Args:
        text:     The text string to convert to a vector (e.g. caption or search query).
        api_key:  Optional API key override.
        provider: Optional provider override (``"openai"`` or ``"gemini"``).

    Returns:
        tuple[list[float], str | None]:
            - First element: list of float vector values (empty list on error).
            - Second element: error message string, or ``None`` on success.
    """
    if not text or not text.strip():
        return [], "Cannot generate embedding for empty text."

    # --- Resolve provider ---
    resolved_provider = (
        provider or os.getenv("VISION_PROVIDER", "openai").lower()
    )

    # --- Resolve API key ---
    env_key_name = (
        "GOOGLE_API_KEY" if resolved_provider == "gemini" else "OPENAI_API_KEY"
    )
    resolved_key = api_key or os.getenv(env_key_name, "")

    if not resolved_key:
        error_msg = (
            f"API key not found. Set the '{env_key_name}' environment variable "
            f"in your .env file."
        )
        logger.error("generate_embedding: %s", error_msg)
        return [], error_msg

    try:
        if resolved_provider == "gemini":
            vector = _call_gemini_embedding(api_key=resolved_key, text=text.strip())
        else:
            vector = _call_openai_embedding(api_key=resolved_key, text=text.strip())

        logger.info(
            "generate_embedding: successfully created vector (%d dim) via %s.",
            len(vector),
            resolved_provider,
        )
        return vector, None

    except Exception as exc:  # noqa: BLE001
        error_msg = f"Embedding generation failed via {resolved_provider}: {exc}"
        logger.error("generate_embedding: %s", error_msg)
        return [], error_msg


# ---------------------------------------------------------------------------
# Storage & Cache API
# ---------------------------------------------------------------------------

def save_embedding(
    data_dir: Path,
    image_id: str,
    embedding: list[float],
) -> bool:
    """Save an embedding vector to disk as a JSON file.

    Args:
        data_dir:  Root data directory.
        image_id:  UUID of the image.
        embedding: List of float values representing the vector.

    Returns:
        bool: ``True`` on success, ``False`` on failure.
    """
    if not image_id or not embedding:
        logger.error("save_embedding: invalid image_id or empty embedding vector.")
        return False

    file_path = _embedding_file_path(data_dir, image_id)
    try:
        payload = {
            "image_id": image_id,
            "dimension": len(embedding),
            "vector": embedding,
        }
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _EMBEDDING_CACHE[image_id] = embedding
        logger.debug("save_embedding: saved %d-dim vector for %s", len(embedding), image_id)
        return True
    except OSError as exc:
        logger.error("save_embedding: failed to save %s — %s", file_path, exc)
        return False


def load_embedding(data_dir: Path, image_id: str) -> Optional[list[float]]:
    """Load an embedding vector from in-memory cache or disk.

    Args:
        data_dir: Root data directory.
        image_id: UUID of the image.

    Returns:
        list[float] | None: Float vector list, or ``None`` if missing/unreadable.
    """
    if image_id in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[image_id]

    file_path = _embedding_file_path(data_dir, image_id)
    if not file_path.exists():
        return None

    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        vector = data.get("vector")
        if isinstance(vector, list) and len(vector) > 0:
            _EMBEDDING_CACHE[image_id] = vector
            return vector
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("load_embedding: failed to load %s — %s", file_path, exc)

    return None


def get_or_create_image_embedding(
    data_dir: Path,
    image_id: str,
    caption: str,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[Optional[list[float]], Optional[str]]:
    """Retrieve an existing embedding from cache/disk or generate a new one.

    This function enforces performance optimization by guaranteeing that an
    embedding is generated **at most once** per image caption.

    Args:
        data_dir: Root data directory.
        image_id: UUID of the image.
        caption:  Image caption text to embed.
        api_key:  Optional API key override.
        provider: Optional provider override.

    Returns:
        tuple[list[float] | None, str | None]:
            - First element: embedding vector list (or None on failure).
            - Second element: error message (or None on success).
    """
    # 1. Check existing disk / memory cache
    existing = load_embedding(data_dir, image_id)
    if existing:
        logger.debug("get_or_create_image_embedding: loaded cached embedding for %s", image_id)
        return existing, None

    if not caption or not caption.strip():
        return None, "Image has no caption to generate an embedding from."

    # 2. Generate new vector via API
    vector, error_msg = generate_embedding(text=caption, api_key=api_key, provider=provider)
    if error_msg:
        return None, error_msg

    # 3. Save to disk and update database record
    save_embedding(data_dir, image_id, vector)
    from backend.database import update_metadata
    update_metadata(data_dir, image_id, {"has_embedding": True})

    return vector, None
