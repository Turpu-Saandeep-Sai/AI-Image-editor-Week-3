"""
storage.py
----------
File-system image management for the AI-Powered Image Editing Platform.

Responsibilities:
    - save_image():   Persist uploaded image bytes to disk.
    - load_image():   Read an image from disk given its stored path.
    - delete_image(): Remove an image file from disk.
    - list_images():  Return metadata about all files in the image store.

Design notes:
    - All paths are managed via pathlib.Path — no string concatenation.
    - The module is completely side-effect-free at import time.
    - Callers are expected to pass the base data directory so that this
      module has zero hard-coded paths.

Author: AI Image Editor Platform
Version: 1.0.0
"""

import io
import logging
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dir(directory: Path) -> None:
    """Create *directory* (and all parents) if it does not yet exist.

    Args:
        directory: The directory path to create.
    """
    directory.mkdir(parents=True, exist_ok=True)


def _safe_path(base_dir: Path, filename: str) -> Path:
    """Build a safe, absolute path preventing path-traversal attacks.

    Args:
        base_dir: The trusted base directory.
        filename: The filename provided by the caller.

    Returns:
        Path: Resolved absolute path inside *base_dir*.

    Raises:
        ValueError: If the resolved path would escape *base_dir*.
    """
    candidate = (base_dir / Path(filename).name).resolve()
    if not str(candidate).startswith(str(base_dir.resolve())):
        raise ValueError(
            f"Path traversal detected: '{filename}' escapes '{base_dir}'."
        )
    return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_image(
    file_data: bytes,
    filename: str,
    images_dir: Path,
) -> Path:
    """Persist raw image bytes to *images_dir* under *filename*.

    If a file with the same name already exists it is **overwritten**
    (callers are expected to use UUID-prefixed filenames to avoid
    unintentional collisions).

    Args:
        file_data:  Raw bytes of the image to store.
        filename:   The target filename (basename only; any directory
                    components are stripped for safety).
        images_dir: Absolute path to the directory where images are stored.

    Returns:
        Path: The absolute path where the image was written.

    Raises:
        ValueError:   If a path-traversal attempt is detected.
        OSError:      If the file cannot be written to disk.
        RuntimeError: If *file_data* does not represent a valid image.
    """
    _ensure_dir(images_dir)
    target_path = _safe_path(images_dir, filename)

    # Validate that the bytes are actually an image before writing
    try:
        with Image.open(io.BytesIO(file_data)) as img:
            img.verify()
    except (UnidentifiedImageError, Exception) as exc:
        raise RuntimeError(
            f"Cannot save '{filename}': the data is not a valid image. "
            f"Detail: {exc}"
        ) from exc

    target_path.write_bytes(file_data)
    logger.info("Image saved: %s (%d bytes)", target_path, len(file_data))
    return target_path


def load_image(image_path: Path) -> Optional[Image.Image]:
    """Open and return a PIL Image from *image_path*.

    The image is opened in read mode; the file is closed after the
    object is returned (PIL loads pixel data lazily, so the caller
    should keep the returned object alive while using it).

    Args:
        image_path: Absolute path to the image file.

    Returns:
        PIL.Image.Image | None: The opened image, or ``None`` if the
        file does not exist or cannot be decoded.
    """
    if not image_path.exists():
        logger.warning("load_image: file not found at %s", image_path)
        return None

    try:
        img = Image.open(image_path)
        img.load()  # force read into memory so the file handle can be released
        return img
    except (UnidentifiedImageError, OSError) as exc:
        logger.error("load_image: failed to open %s — %s", image_path, exc)
        return None


def delete_image(image_path: Path) -> bool:
    """Delete the image file at *image_path*.

    Args:
        image_path: Absolute path to the image file to remove.

    Returns:
        bool: ``True`` if the file was deleted, ``False`` if it did not
        exist or could not be removed.
    """
    if not image_path.exists():
        logger.warning("delete_image: file not found at %s", image_path)
        return False

    try:
        image_path.unlink()
        logger.info("Image deleted: %s", image_path)
        return True
    except OSError as exc:
        logger.error("delete_image: failed to delete %s — %s", image_path, exc)
        return False


def list_images(images_dir: Path) -> list[dict]:
    """Return file-system metadata for every image in *images_dir*.

    Only files whose extension matches supported image types are included.
    Subdirectories are ignored.

    Args:
        images_dir: Directory to scan for image files.

    Returns:
        list[dict]: Each dict contains:
            - ``"filename"``  (str) — bare filename
            - ``"filepath"``  (str) — absolute path as a string
            - ``"size"``      (int) — file size in bytes
            - ``"modified"``  (float) — last-modified time (UNIX timestamp)
    """
    supported = {".png", ".jpg", ".jpeg"}

    if not images_dir.exists():
        logger.info("list_images: directory %s does not exist yet.", images_dir)
        return []

    results: list[dict] = []
    for entry in images_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() in supported:
            stat = entry.stat()
            results.append(
                {
                    "filename": entry.name,
                    "filepath": str(entry),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

    results.sort(key=lambda x: x["modified"], reverse=True)  # newest first
    return results


def get_image_bytes(image_path: Path) -> Optional[bytes]:
    """Return the raw bytes of the image at *image_path*.

    Useful for passing image data directly to API calls or re-encoding.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        bytes | None: File contents, or ``None`` if the file is missing
        or unreadable.
    """
    if not image_path.exists():
        logger.warning("get_image_bytes: file not found at %s", image_path)
        return None
    try:
        return image_path.read_bytes()
    except OSError as exc:
        logger.error("get_image_bytes: failed to read %s — %s", image_path, exc)
        return None


def copy_image(src: Path, dest_dir: Path, new_name: Optional[str] = None) -> Optional[Path]:
    """Copy an image file to *dest_dir*, optionally renaming it.

    Args:
        src:      Source image path.
        dest_dir: Destination directory.
        new_name: Optional new filename; if omitted the original name is used.

    Returns:
        Path | None: Path to the copied file, or ``None`` on failure.
    """
    _ensure_dir(dest_dir)
    dest_name = new_name if new_name else src.name
    dest_path = dest_dir / dest_name
    try:
        shutil.copy2(src, dest_path)
        logger.info("Image copied: %s → %s", src, dest_path)
        return dest_path
    except OSError as exc:
        logger.error("copy_image: failed to copy %s → %s — %s", src, dest_path, exc)
        return None


def save_version_image(
    file_data: bytes,
    image_id: str,
    version_num: int,
    images_dir: Path,
) -> Path:
    """Save edited image bytes with a versioned filename.

    Delegates to :func:`save_image` after constructing the version filename
    using :func:`backend.utils.version_name`.

    Args:
        file_data:    Raw bytes of the edited image.
        image_id:     UUID of the parent image record.
        version_num:  Integer version number (1, 2, 3, …).
        images_dir:   Directory where images are stored.

    Returns:
        Path: Absolute path where the versioned image was saved.

    Raises:
        ValueError:   If a path-traversal attempt is detected.
        OSError:      If the file cannot be written.
        RuntimeError: If *file_data* is not a valid image.
    """
    from backend.utils import version_name as _version_name

    filename = _version_name(image_id, version_num, ".png")
    return save_image(
        file_data=file_data,
        filename=filename,
        images_dir=images_dir,
    )
