"""
image_edit.py
-------------
AI-powered image editing engine for the AI-Powered Image Editing Platform.

Responsibilities:
    - edit_image():       High-level orchestrator — reads image, calls API,
                          saves the edited version, updates metadata.
    - _call_openai_edit(): Calls OpenAI GPT Image API (``gpt-image-1``) with
                           image + prompt and returns the edited image bytes.
    - _call_gemini_edit(): Calls Gemini Image Editing API
                           (``gemini-2.0-flash-preview-image-generation``)
                           as a fallback provider.
    - save_version():      Persists edited image bytes to disk under a
                           versioned filename and returns the filepath.

Supported providers:
    - OpenAI  (default): ``gpt-image-1`` image generation/editing model.
    - Gemini  (opt-in):  ``gemini-2.0-flash-preview-image-generation``.

Provider selection mirrors ``caption.py``: set ``VISION_PROVIDER=gemini``
in ``.env`` to use Gemini; defaults to OpenAI otherwise.

Author: AI Image Editor Platform
Version: 2.0.0
"""

from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from backend.caption import retry_logic, DEFAULT_MAX_RETRIES, DEFAULT_INITIAL_DELAY, DEFAULT_BACKOFF_FACTOR
from backend.prompt_templates import build_edit_prompt
from backend.utils import version_name, timestamp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENAI_EDIT_MODEL: str = "gpt-image-1"
GEMINI_EDIT_MODEL: str = "gemini-2.0-flash-preview-image-generation"
MAX_IMAGE_PIXELS: int = 2048  # longest side for API submission
MAX_IMAGE_SIZE_MB: int = 20   # maximum file size in MB


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_image_for_edit(image_bytes: bytes) -> tuple[bool, str]:
    """Validate that *image_bytes* is a valid, editable image.

    Checks:
        1. Non-empty data.
        2. PIL can open and verify the data.
        3. File size is within the API limit.

    Args:
        image_bytes: Raw image data.

    Returns:
        tuple[bool, str]: ``(True, "")`` if valid, ``(False, error_msg)`` otherwise.
    """
    if not image_bytes:
        return False, "Image data is empty."

    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        return False, (
            f"Image is too large ({size_mb:.1f} MB). "
            f"Maximum allowed size is {MAX_IMAGE_SIZE_MB} MB."
        )

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except Exception as exc:
        return False, f"Image appears to be corrupted or unsupported: {exc}"

    return True, ""


def _resize_for_api(image_bytes: bytes) -> bytes:
    """Shrink the image so its longest side is ≤ MAX_IMAGE_PIXELS.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        bytes: Resized (if necessary) PNG-encoded image bytes.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        w, h = img.size
        if max(w, h) > MAX_IMAGE_PIXELS:
            scale = MAX_IMAGE_PIXELS / max(w, h)
            img = img.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS,
            )

        if img.mode == "RGBA":
            pass  # preserve alpha for PNG
        elif img.mode != "RGB":
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="PNG", quality=95)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# OpenAI Image Edit call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_openai_edit(
    api_key: str,
    image_bytes: bytes,
    prompt: str,
) -> bytes:
    """Send an image + prompt to the OpenAI GPT Image API and return edited bytes.

    Uses the ``gpt-image-1`` model with the ``images.edit`` endpoint.

    Args:
        api_key:      OpenAI secret key.
        image_bytes:  PNG-encoded image bytes.
        prompt:       The full editing prompt (system + user combined).

    Returns:
        bytes: The edited image as PNG bytes.

    Raises:
        ImportError:  If the ``openai`` package is not installed.
        RuntimeError: If the API returns an unexpected response.
    """
    try:
        import openai
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for OpenAI image editing. "
            "Install it with: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=api_key)

    # Write image bytes to a BytesIO for the API
    image_file = io.BytesIO(image_bytes)
    image_file.name = "input.png"

    response = client.images.edit(
        model=OPENAI_EDIT_MODEL,
        image=image_file,
        prompt=prompt,
        n=1,
        size="auto",
    )

    if not response.data:
        raise RuntimeError("OpenAI image edit returned an empty data list.")

    # The response contains base64-encoded image data
    image_data = response.data[0]

    if hasattr(image_data, "b64_json") and image_data.b64_json:
        return base64.b64decode(image_data.b64_json)
    elif hasattr(image_data, "url") and image_data.url:
        # Download from URL
        import urllib.request
        with urllib.request.urlopen(image_data.url) as resp:
            return resp.read()
    else:
        raise RuntimeError(
            "OpenAI image edit returned neither b64_json nor url."
        )


# ---------------------------------------------------------------------------
# Gemini Image Edit call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_gemini_edit(
    api_key: str,
    image_bytes: bytes,
    prompt: str,
) -> bytes:
    """Send an image + prompt to the Gemini Image Editing API.

    Uses ``gemini-2.0-flash-preview-image-generation`` with image generation
    capability enabled via ``response_modalities``.

    Args:
        api_key:      Google AI Studio API key.
        image_bytes:  PNG-encoded image bytes.
        prompt:       The full editing prompt (system + user combined).

    Returns:
        bytes: The edited image as PNG bytes.

    Raises:
        ImportError:  If ``google-genai`` is not installed.
        RuntimeError: If the API returns an unexpected or empty response.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise ImportError(
            "The 'google-genai' package is required for Gemini image editing. "
            "Install it with: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)

    # Build an inline image Part from raw bytes
    image_part = genai_types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png",
    )

    response = client.models.generate_content(
        model=GEMINI_EDIT_MODEL,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    image_part,
                    genai_types.Part.from_text(text=prompt),
                ],
            )
        ],
        config=genai_types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            temperature=0.4,
            max_output_tokens=8192,
        ),
    )

    # Extract image data from the response
    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

    raise RuntimeError(
        "Gemini image edit returned no image data. "
        "Check your API key and model availability."
    )


# ---------------------------------------------------------------------------
# Version persistence
# ---------------------------------------------------------------------------

def save_version(
    image_bytes: bytes,
    image_id: str,
    version_num: int,
    images_dir: Path,
) -> Path:
    """Save edited image bytes to disk with a versioned filename.

    Args:
        image_bytes: The edited image data (PNG).
        image_id:    UUID of the parent image record.
        version_num: The version number (1, 2, 3, …).
        images_dir:  Directory where images are stored.

    Returns:
        Path: Absolute path where the versioned image was saved.

    Raises:
        OSError: If the file cannot be written.
    """
    filename = version_name(image_id, version_num, ".png")
    target_path = images_dir / filename

    images_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(image_bytes)

    logger.info(
        "Version saved: %s (%d bytes)", target_path, len(image_bytes)
    )
    return target_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_edit_api(
    image_bytes: bytes,
    prompt: str,
    api_key: str,
    provider: str = "openai",
) -> bytes:
    """Call the configured image editing API and return edited image bytes.

    This function is the single dispatch point for all provider calls.
    It handles image pre-processing (resize) before delegating to the
    provider-specific implementation.

    Args:
        image_bytes: Raw image bytes.
        prompt:      The full editing prompt.
        api_key:     API key for the chosen provider.
        provider:    ``"openai"`` or ``"gemini"``.

    Returns:
        bytes: The edited image as PNG bytes.

    Raises:
        ValueError:   If an unsupported provider is specified.
        RuntimeError: If the API call fails after all retries.
    """
    processed_bytes = _resize_for_api(image_bytes)

    if provider.lower() == "gemini":
        return _call_gemini_edit(
            api_key=api_key,
            image_bytes=processed_bytes,
            prompt=prompt,
        )

    if provider.lower() in ("openai", ""):
        return _call_openai_edit(
            api_key=api_key,
            image_bytes=processed_bytes,
            prompt=prompt,
        )

    raise ValueError(
        f"Unsupported editing provider: '{provider}'. "
        "Choose 'openai' or 'gemini'."
    )


def edit_image(
    image_path: Path,
    user_prompt: str,
    image_id: str,
    version_num: int,
    images_dir: Path,
    data_dir: Path,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[Optional[Path], Optional[str]]:
    """Orchestrate the full image editing pipeline.

    Steps:
        1. Validate the source image.
        2. Read image bytes from disk.
        3. Build the full prompt (system + user).
        4. Call the editing API.
        5. Save the edited image as a new version.
        6. Update the metadata database with the version record.

    Args:
        image_path:   Path to the source image (original or previous version).
        user_prompt:  The user's natural-language editing instruction.
        image_id:     UUID of the parent image record.
        version_num:  The version number to assign.
        images_dir:   Directory where images are stored.
        data_dir:     Root data directory for metadata persistence.
        api_key:      API key override (falls back to environment variable).
        provider:     Provider override (falls back to ``VISION_PROVIDER``).

    Returns:
        tuple[Path | None, str | None]:
            - First element: path to the saved edited image, or ``None``.
            - Second element: error message, or ``None`` on success.
    """
    # --- Resolve provider ---
    resolved_provider = (
        provider
        or os.getenv("VISION_PROVIDER", "openai").lower()
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
        logger.error("edit_image: %s", error_msg)
        return None, error_msg

    # --- Read source image ---
    if not image_path.exists():
        error_msg = f"Source image not found: {image_path}"
        logger.error("edit_image: %s", error_msg)
        return None, error_msg

    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        error_msg = f"Cannot read source image: {exc}"
        logger.error("edit_image: %s", error_msg)
        return None, error_msg

    # --- Validate ---
    valid, validation_error = _validate_image_for_edit(image_bytes)
    if not valid:
        return None, validation_error

    # --- Validate prompt ---
    if not user_prompt or not user_prompt.strip():
        return None, "Please provide an editing instruction."

    # --- Build full prompt ---
    full_prompt = build_edit_prompt(user_prompt.strip())

    # --- Call editing API ---
    try:
        edited_bytes = call_edit_api(
            image_bytes=image_bytes,
            prompt=full_prompt,
            api_key=resolved_key,
            provider=resolved_provider,
        )
    except Exception as exc:
        error_msg = f"Image editing failed: {exc}"
        logger.error("edit_image: %s", error_msg)
        return None, error_msg

    if not edited_bytes:
        return None, "The editing API returned empty data."

    # --- Save version to disk ---
    try:
        saved_path = save_version(
            image_bytes=edited_bytes,
            image_id=image_id,
            version_num=version_num,
            images_dir=images_dir,
        )
    except OSError as exc:
        error_msg = f"Failed to save edited image: {exc}"
        logger.error("edit_image: %s", error_msg)
        return None, error_msg

    # --- Update metadata ---
    from backend.database import add_version

    ts = timestamp()
    version_record: dict[str, Any] = {
        "version": version_num,
        "type": "edited",
        "filepath": str(saved_path),
        "prompt": user_prompt.strip(),
        "timestamp": ts,
    }

    add_success = add_version(data_dir, image_id, version_record)
    if not add_success:
        logger.warning(
            "edit_image: metadata update failed for %s v%d (image saved OK).",
            image_id, version_num,
        )

    logger.info(
        "edit_image: completed editing for %s → v%d at %s",
        image_id, version_num, saved_path,
    )
    return saved_path, None
