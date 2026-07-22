"""
utils.py
--------
Core utility functions for the AI-Powered Image Editing Platform.

Responsibilities:
    - UUID generation
    - Timestamp creation
    - Image format validation
    - Thumbnail creation
    - File size formatting

Author: AI Image Editor Platform
Version: 1.0.0
"""

import uuid
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

# ---------------------------------------------------------------------------
# Module-level logger — no global state, just a named logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"png", "jpg", "jpeg"})
THUMBNAIL_SIZE: tuple[int, int] = (300, 300)
TIMESTAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"


# ---------------------------------------------------------------------------
# UUID
# ---------------------------------------------------------------------------

def generate_uuid() -> str:
    """Generate a cryptographically random UUID4 string.

    Returns:
        str: A unique identifier string in standard UUID4 format.

    Example:
        >>> uid = generate_uuid()
        >>> len(uid)
        36
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format.

    Returns:
        str: UTC timestamp, e.g. ``"2025-01-15T12:34:56Z"``.
    """
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 UTC timestamp string back into a datetime object.

    Args:
        ts: Timestamp string produced by :func:`timestamp`.

    Returns:
        datetime | None: Parsed datetime (timezone-aware, UTC), or ``None``
        on failure.
    """
    try:
        return datetime.strptime(ts, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as exc:
        logger.warning("Could not parse timestamp %r: %s", ts, exc)
        return None


def format_timestamp_display(ts: str) -> str:
    """Convert a stored UTC timestamp to a human-readable local display string.

    Args:
        ts: Timestamp string produced by :func:`timestamp`.

    Returns:
        str: Formatted display string, e.g. ``"Jan 15, 2025 at 12:34 UTC"``.
    """
    dt = parse_timestamp(ts)
    if dt is None:
        return ts  # fall back to raw string
    return dt.strftime("%b %d, %Y at %H:%M UTC")


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------

def image_validation(file_data: bytes, filename: str) -> tuple[bool, str]:
    """Validate that *file_data* represents an allowed image.

    Checks performed:
    1. File extension is in :data:`ALLOWED_EXTENSIONS`.
    2. File data is non-empty.
    3. PIL can successfully open and verify the image.

    Args:
        file_data: Raw bytes of the uploaded file.
        filename:  Original filename (used to extract the extension).

    Returns:
        tuple[bool, str]: ``(True, "")`` when valid, or
        ``(False, "<error message>")`` when invalid.
    """
    # --- Extension check ---------------------------------------------------
    suffix = Path(filename).suffix.lstrip(".").lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return False, (
            f"Unsupported file type '.{suffix}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # --- Empty file check --------------------------------------------------
    if not file_data:
        return False, "The uploaded file is empty."

    # --- PIL integrity check -----------------------------------------------
    try:
        with Image.open(io.BytesIO(file_data)) as img:
            img.verify()  # raises for truncated / corrupted images
    except UnidentifiedImageError:
        return False, "Cannot identify image format. The file may be corrupted."
    except Exception as exc:  # noqa: BLE001
        return False, f"Image validation failed: {exc}"

    return True, ""


# ---------------------------------------------------------------------------
# Thumbnail creation
# ---------------------------------------------------------------------------

def thumbnail_creation(
    image_path: Path,
    size: tuple[int, int] = THUMBNAIL_SIZE,
) -> Optional[Image.Image]:
    """Create an in-memory thumbnail of the image at *image_path*.

    Uses ``Image.LANCZOS`` resampling for high-quality downscaling.
    The thumbnail preserves the original aspect ratio.

    Args:
        image_path: Absolute path to the source image file.
        size:       Maximum (width, height) bounding box for the thumbnail.

    Returns:
        PIL.Image.Image | None: The thumbnail image object (RGB mode),
        or ``None`` if the image could not be opened.
    """
    try:
        with Image.open(image_path) as img:
            img_copy = img.copy()
            # Ensure consistent colour mode for display
            if img_copy.mode not in ("RGB", "RGBA"):
                img_copy = img_copy.convert("RGB")
            img_copy.thumbnail(size, Image.LANCZOS)
            return img_copy
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create thumbnail for %s: %s", image_path, exc)
        return None


# ---------------------------------------------------------------------------
# File size formatting
# ---------------------------------------------------------------------------

def format_file_size(size_bytes: int) -> str:
    """Convert a raw byte count into a human-readable string.

    Uses binary prefixes (1 KB = 1024 bytes).

    Args:
        size_bytes: File size in bytes.

    Returns:
        str: Formatted string, e.g. ``"1.23 MB"``, ``"512 KB"``, ``"42 B"``.

    Example:
        >>> format_file_size(1_048_576)
        '1.00 MB'
    """
    if size_bytes < 0:
        return "Unknown"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"


# ---------------------------------------------------------------------------
# Image dimension helper
# ---------------------------------------------------------------------------

def get_image_dimensions(image_path: Path) -> Optional[tuple[int, int]]:
    """Return the (width, height) of the image at *image_path*.

    Args:
        image_path: Path to the image file.

    Returns:
        tuple[int, int] | None: ``(width, height)`` in pixels, or ``None``
        on failure.
    """
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not read dimensions of %s: %s", image_path, exc)
        return None


# ---------------------------------------------------------------------------
# Version naming (Week 2)
# ---------------------------------------------------------------------------

def version_name(image_id: str, version_num: int, ext: str = ".png") -> str:
    """Generate a consistent versioned filename for an edited image.

    Args:
        image_id:    UUID of the parent image.
        version_num: Integer version number (1, 2, 3, …).
        ext:         File extension including the leading dot.

    Returns:
        str: A filename of the form ``{image_id}_v{version_num}{ext}``.

    Example:
        >>> version_name("abc123", 2, ".png")
        'abc123_v2.png'
    """
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"{image_id}_v{version_num}{ext}"


# ---------------------------------------------------------------------------
# Thumbnail creation to disk (Week 2)
# ---------------------------------------------------------------------------

THUMBNAIL_DISK_SIZE: tuple[int, int] = (200, 200)


def create_thumbnail(
    image_path: Path,
    thumb_dir: Path,
    size: tuple[int, int] = THUMBNAIL_DISK_SIZE,
) -> Optional[Path]:
    """Create a thumbnail of the image and save it to *thumb_dir*.

    The thumbnail file is named ``thumb_{original_stem}.png``.

    Args:
        image_path: Path to the source image.
        thumb_dir:  Directory where the thumbnail will be saved.
        size:       Maximum (width, height) bounding box.

    Returns:
        Path | None: Path to the saved thumbnail, or ``None`` on failure.
    """
    try:
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"thumb_{image_path.stem}.png"

        with Image.open(image_path) as img:
            img_copy = img.copy()
            if img_copy.mode not in ("RGB", "RGBA"):
                img_copy = img_copy.convert("RGB")
            img_copy.thumbnail(size, Image.LANCZOS)
            img_copy.save(thumb_path, format="PNG")

        logger.info("Thumbnail saved: %s", thumb_path)
        return thumb_path
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create thumbnail for %s: %s", image_path, exc)
        return None
