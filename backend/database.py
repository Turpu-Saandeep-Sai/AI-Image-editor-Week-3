"""
database.py
-----------
JSON-based metadata persistence for the AI-Powered Image Editing Platform.

Responsibilities:
    - load_metadata():  Read and deserialise the metadata store.
    - save_metadata():  Serialise and write the metadata store to disk.
    - add_metadata():   Append a new image record to the store.
    - find_by_id():     Retrieve a single record by its UUID.
    - find_all():       Return all records, with optional filtering.
    - update_metadata(): Update fields on an existing record.
    - delete_metadata(): Remove a record by UUID.

Schema (per record):
    {
        "id":          str,   # UUID4
        "filename":    str,   # original filename
        "filepath":    str,   # absolute path on disk
        "caption":     str,   # AI-generated caption (or "" if pending)
        "uploaded_at": str,   # ISO-8601 UTC timestamp
        "versions":    list   # reserved for Week 2+ version history
    }

Design notes:
    - Thread safety is intentionally kept simple for the MVP: the JSON
      file is read fully on every read and written fully on every write.
      Future iterations should replace this with SQLite or PostgreSQL.
    - The ``data_dir`` parameter is always threaded through the public
      API to keep the module stateless at import time.

Author: AI Image Editor Platform
Version: 1.0.0
"""

import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Name of the metadata file inside *data_dir*
METADATA_FILENAME: str = "metadata.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _metadata_path(data_dir: Path) -> Path:
    """Return the absolute path to the metadata JSON file.

    Args:
        data_dir: Root data directory for the application.

    Returns:
        Path: Absolute path to ``metadata.json``.
    """
    return data_dir / METADATA_FILENAME


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically using a temporary file.

    Prevents data loss if the process is interrupted mid-write.

    Args:
        path:    Target file path.
        content: JSON string to write.

    Raises:
        OSError: If the temporary file cannot be created or renamed.
    """
    dir_ = path.parent
    dir_.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        # Clean up the temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_metadata(data_dir: Path) -> list[dict[str, Any]]:
    """Read and return all image records from the metadata store.

    If the metadata file does not exist, an empty list is returned and
    the file is **not** created (creation happens on the first write).

    Args:
        data_dir: Root data directory containing ``metadata.json``.

    Returns:
        list[dict]: All image metadata records (may be empty).
    """
    path = _metadata_path(data_dir)
    if not path.exists():
        logger.info("load_metadata: no metadata file found at %s, returning [].", path)
        return []

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            logger.warning(
                "load_metadata: expected JSON array, got %s. Resetting to [].",
                type(data).__name__,
            )
            return []
        return data
    except json.JSONDecodeError as exc:
        logger.error("load_metadata: JSON parse error in %s — %s", path, exc)
        return []
    except OSError as exc:
        logger.error("load_metadata: cannot read %s — %s", path, exc)
        return []


def save_metadata(data_dir: Path, records: list[dict[str, Any]]) -> bool:
    """Serialise *records* and write them to the metadata store.

    Args:
        data_dir: Root data directory.
        records:  Complete list of image metadata records to persist.

    Returns:
        bool: ``True`` on success, ``False`` on failure.
    """
    path = _metadata_path(data_dir)
    try:
        content = json.dumps(records, indent=2, ensure_ascii=False)
        _atomic_write(path, content)
        logger.debug("save_metadata: wrote %d records to %s", len(records), path)
        return True
    except (OSError, TypeError) as exc:
        logger.error("save_metadata: failed to write %s — %s", path, exc)
        return False


def add_metadata(
    data_dir: Path,
    record: dict[str, Any],
) -> bool:
    """Append a new image *record* to the metadata store.

    If a record with the same ``"id"`` already exists, the operation is
    rejected and ``False`` is returned.

    Args:
        data_dir: Root data directory.
        record:   Image metadata dict. Must contain an ``"id"`` key.

    Returns:
        bool: ``True`` if the record was added, ``False`` otherwise.
    """
    if "id" not in record:
        logger.error("add_metadata: record is missing the 'id' field.")
        return False

    records = load_metadata(data_dir)

    # Duplicate guard
    if any(r.get("id") == record["id"] for r in records):
        logger.warning("add_metadata: record with id=%s already exists.", record["id"])
        return False

    records.append(deepcopy(record))
    return save_metadata(data_dir, records)


def find_by_id(data_dir: Path, image_id: str) -> Optional[dict[str, Any]]:
    """Return the metadata record matching *image_id*, or ``None``.

    Args:
        data_dir:  Root data directory.
        image_id:  UUID of the image to look up.

    Returns:
        dict | None: A *copy* of the matching record, or ``None``.
    """
    for record in load_metadata(data_dir):
        if record.get("id") == image_id:
            return deepcopy(record)
    return None


def find_all(
    data_dir: Path,
    sort_by: str = "uploaded_at",
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Return all metadata records, sorted by *sort_by*.

    Args:
        data_dir:   Root data directory.
        sort_by:    Field name to sort by (default: ``"uploaded_at"``).
        descending: If ``True``, newest-first ordering is applied.

    Returns:
        list[dict]: Deep-copied, sorted list of all records.
    """
    records = load_metadata(data_dir)
    try:
        records.sort(key=lambda r: r.get(sort_by, ""), reverse=descending)
    except TypeError:
        logger.warning("find_all: could not sort by field '%s'.", sort_by)
    return [deepcopy(r) for r in records]


def update_metadata(
    data_dir: Path,
    image_id: str,
    updates: dict[str, Any],
) -> bool:
    """Apply *updates* to the record identified by *image_id*.

    Only the keys present in *updates* are changed; all other fields are
    left untouched.  The ``"id"`` field cannot be overwritten.

    Args:
        data_dir:  Root data directory.
        image_id:  UUID of the record to update.
        updates:   Dict of field-value pairs to apply.

    Returns:
        bool: ``True`` if the record was found and updated.
    """
    records = load_metadata(data_dir)
    updated = False

    for record in records:
        if record.get("id") == image_id:
            for key, value in updates.items():
                if key == "id":
                    continue  # never allow overwriting the primary key
                record[key] = value
            updated = True
            break

    if not updated:
        logger.warning("update_metadata: no record found with id=%s.", image_id)
        return False

    return save_metadata(data_dir, records)


def delete_metadata(data_dir: Path, image_id: str) -> bool:
    """Remove the record identified by *image_id* from the metadata store.

    Args:
        data_dir:  Root data directory.
        image_id:  UUID of the record to remove.

    Returns:
        bool: ``True`` if the record was found and removed.
    """
    records = load_metadata(data_dir)
    original_count = len(records)
    records = [r for r in records if r.get("id") != image_id]

    if len(records) == original_count:
        logger.warning("delete_metadata: no record found with id=%s.", image_id)
        return False

    return save_metadata(data_dir, records)


def build_record(
    image_id: str,
    filename: str,
    filepath: str,
    caption: str,
    uploaded_at: str,
) -> dict[str, Any]:
    """Construct a new image metadata record with the canonical schema.

    Args:
        image_id:    UUID4 string.
        filename:    Original filename of the image.
        filepath:    Absolute path to the stored image on disk.
        caption:     AI-generated (or empty) caption string.
        uploaded_at: ISO-8601 UTC timestamp string.

    Returns:
        dict: A fully-formed metadata record ready to pass to
        :func:`add_metadata`.
    """
    return {
        "id": image_id,
        "filename": filename,
        "filepath": filepath,
        "caption": caption,
        "uploaded_at": uploaded_at,
        "versions": [],  # reserved for Week 2+ version history
    }
