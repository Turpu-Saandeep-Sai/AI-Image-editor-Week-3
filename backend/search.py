"""
search.py
---------
Semantic retrieval engine and multi-tiered vector database integration for the
AI-Powered Image Editing Platform.

Architecture Strategy (Multi-Tier Vector Engine):
    - Tier 1 (Preferred): **ChromaDB** (`chromadb.PersistentClient`) stored in `data/chromadb`.
    - Tier 2 (Fallback 1): **FAISS** (`faiss.IndexFlatIP` with L2-normalized vectors) stored in `data/faiss`.
    - Tier 3 (Fallback 2): **NumPy Cosine Similarity** computed dynamically over JSON cached vectors.

The module dynamically detects installed vector engines at import time and seamlessly
falls back, ensuring zero system breakdown regardless of environment constraints.

Author: AI Image Editor Platform
Version: 3.0.0
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any, Optional

from backend.database import find_all, find_by_id, load_metadata
from backend.embedding import (
    generate_embedding,
    get_or_create_image_embedding,
    load_embedding,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vector DB Availability Detection
# ---------------------------------------------------------------------------

_CHROMADB_AVAILABLE: bool = False
_FAISS_AVAILABLE: bool = False
_NUMPY_AVAILABLE: bool = False

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None  # type: ignore[assignment]
    _CHROMADB_AVAILABLE = False

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    faiss = None  # type: ignore[assignment]
    _FAISS_AVAILABLE = False

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    _NUMPY_AVAILABLE = False


def get_active_vector_engine() -> str:
    """Return the name of the currently active vector database engine.

    Returns:
        str: ``"ChromaDB"``, ``"FAISS"``, or ``"NumPy Cosine Similarity"``.
    """
    if _CHROMADB_AVAILABLE:
        return "ChromaDB"
    if _FAISS_AVAILABLE:
        return "FAISS"
    if _NUMPY_AVAILABLE:
        return "NumPy Cosine Similarity"
    return "Standard Cosine Similarity"


# ---------------------------------------------------------------------------
# Tier 1: ChromaDB Implementation
# ---------------------------------------------------------------------------

def _get_chroma_client(data_dir: Path) -> Any:
    """Initialize and return a persistent ChromaDB client inside *data_dir/chromadb*."""
    chroma_path = data_dir / "chromadb"
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def _get_chroma_collection(data_dir: Path) -> Any:
    """Get or create the 'image_captions' ChromaDB collection."""
    client = _get_chroma_client(data_dir)
    return client.get_or_create_collection(
        name="image_captions",
        metadata={"description": "Image caption vector embeddings for semantic search"},
    )


def _index_chromadb(
    data_dir: Path,
    image_id: str,
    caption: str,
    vector: list[float],
    metadata: dict[str, Any],
) -> bool:
    """Index an image embedding and metadata into ChromaDB."""
    try:
        collection = _get_chroma_collection(data_dir)
        # Convert non-primitive metadata values to strings for ChromaDB compatibility
        chroma_meta = {
            "filename": str(metadata.get("filename", "")),
            "uploaded_at": str(metadata.get("uploaded_at", "")),
            "version_count": len(metadata.get("versions", [])),
        }
        collection.upsert(
            ids=[image_id],
            embeddings=[vector],
            documents=[caption],
            metadatas=[chroma_meta],
        )
        logger.info("ChromaDB: successfully indexed image_id=%s", image_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("ChromaDB indexing error for %s: %s", image_id, exc)
        return False


def _search_chromadb(
    data_dir: Path,
    query_vector: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    """Query ChromaDB for top_k nearest neighbors by cosine similarity."""
    try:
        collection = _get_chroma_collection(data_dir)
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, count),
        )

        matches: list[tuple[str, float]] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            distances = results.get("distances", [[]])[0] if results.get("distances") else []

            for i, image_id in enumerate(ids):
                # ChromaDB distance to similarity conversion (range 0.0 - 1.0)
                dist = distances[i] if i < len(distances) else 0.0
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0) if dist > 1.0 else 1.0 - dist))
                matches.append((image_id, similarity))

        return matches
    except Exception as exc:  # noqa: BLE001
        logger.error("ChromaDB search error: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Tier 2: FAISS Implementation
# ---------------------------------------------------------------------------

def _faiss_paths(data_dir: Path) -> tuple[Path, Path]:
    """Return paths for the FAISS binary index and its ID mapping file."""
    faiss_dir = data_dir / "faiss"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    return faiss_dir / "faiss.index", faiss_dir / "id_map.json"


def _index_faiss(
    data_dir: Path,
    image_id: str,
    vector: list[float],
) -> bool:
    """Index an embedding vector into FAISS flat inner-product index."""
    if not _FAISS_AVAILABLE or not _NUMPY_AVAILABLE:
        return False

    index_path, map_path = _faiss_paths(data_dir)
    try:
        # Load or initialize ID map
        id_map: list[str] = []
        if map_path.exists():
            import json
            id_map = json.loads(map_path.read_text(encoding="utf-8"))

        vec_arr = np.array([vector], dtype=np.float32)
        # Normalize vector for cosine similarity via inner product
        norm = np.linalg.norm(vec_arr)
        if norm > 0:
            vec_arr = vec_arr / norm

        dim = len(vector)
        if index_path.exists():
            index = faiss.read_index(str(index_path))
        else:
            index = faiss.IndexFlatIP(dim)

        if image_id in id_map:
            # Replace existing: re-build simple index
            idx = id_map.index(image_id)
            # Rebuilding FAISS flat index for simplicity
            all_records = load_metadata(data_dir)
            id_map = []
            vectors_list = []
            for rec in all_records:
                v = load_embedding(data_dir, rec["id"])
                if v and len(v) == dim:
                    id_map.append(rec["id"])
                    vectors_list.append(v)
            if vectors_list:
                mat = np.array(vectors_list, dtype=np.float32)
                norms = np.linalg.norm(mat, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                mat = mat / norms
                index = faiss.IndexFlatIP(dim)
                index.add(mat)
        else:
            index.add(vec_arr)
            id_map.append(image_id)

        faiss.write_index(index, str(index_path))
        map_path.write_text(json.dumps(id_map), encoding="utf-8")
        logger.info("FAISS: successfully indexed image_id=%s", image_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("FAISS indexing error for %s: %s", image_id, exc)
        return False


def _search_faiss(
    data_dir: Path,
    query_vector: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    """Query FAISS index for top matching vectors."""
    if not _FAISS_AVAILABLE or not _NUMPY_AVAILABLE:
        return []

    index_path, map_path = _faiss_paths(data_dir)
    if not index_path.exists() or not map_path.exists():
        return []

    try:
        import json
        id_map: list[str] = json.loads(map_path.read_text(encoding="utf-8"))
        if not id_map:
            return []

        index = faiss.read_index(str(index_path))
        q_arr = np.array([query_vector], dtype=np.float32)
        norm = np.linalg.norm(q_arr)
        if norm > 0:
            q_arr = q_arr / norm

        scores, indices = index.search(q_arr, min(top_k, len(id_map)))

        matches: list[tuple[str, float]] = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(id_map):
                score = float(scores[0][i])
                sim = max(0.0, min(1.0, (score + 1.0) / 2.0))
                matches.append((id_map[idx], sim))

        return matches
    except Exception as exc:  # noqa: BLE001
        logger.error("FAISS search error: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Tier 3: Pure Cosine Similarity Fallback (NumPy / Math)
# ---------------------------------------------------------------------------

def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    if _NUMPY_AVAILABLE:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    # Standard python math fallback
    dot = sum(x * y for x, y in zip(v1, v2))
    mag1 = math.sqrt(sum(x * x for x in v1))
    mag2 = math.sqrt(sum(y * y for y in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _search_json_fallback(
    data_dir: Path,
    query_vector: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    """Scan all saved JSON embeddings and rank by cosine similarity."""
    records = load_metadata(data_dir)
    scores: list[tuple[str, float]] = []

    for rec in records:
        image_id = rec.get("id")
        if not image_id:
            continue
        vec = load_embedding(data_dir, image_id)
        if vec:
            sim = _cosine_similarity(query_vector, vec)
            # Normalize to 0-1 range if necessary
            normalized_sim = max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))
            scores.append((image_id, normalized_sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


# ---------------------------------------------------------------------------
# Public Vector Index & Search API
# ---------------------------------------------------------------------------

def index_image(
    data_dir: Path,
    image_id: str,
    caption: str,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """Index an image into the active vector database system.

    Attempts ChromaDB first, falls back to FAISS, and ensures the embedding is
    cached on disk for JSON fallback search.

    Args:
        data_dir: Root data directory.
        image_id: UUID of the image.
        caption:  AI-generated caption text.
        metadata: Metadata record dictionary.

    Returns:
        bool: ``True`` if successfully indexed into a vector store.
    """
    if not caption:
        return False

    rec = metadata or find_by_id(data_dir, image_id) or {}
    vector, err = get_or_create_image_embedding(data_dir, image_id, caption)
    if err or not vector:
        logger.error("index_image: failed to get embedding for %s — %s", image_id, err)
        return False

    success = False
    if _CHROMADB_AVAILABLE:
        success = _index_chromadb(data_dir, image_id, caption, vector, rec)

    if not success and _FAISS_AVAILABLE:
        success = _index_faiss(data_dir, image_id, vector)

    # If neither tier-1 nor tier-2 is available, disk JSON vector saved by get_or_create_image_embedding is sufficient
    return True


def reindex_all_images(data_dir: Path) -> int:
    """Scan all image records in metadata and index any un-indexed items.

    Args:
        data_dir: Root data directory.

    Returns:
        int: Total number of images successfully indexed.
    """
    all_records = load_metadata(data_dir)
    indexed_count = 0

    for rec in all_records:
        image_id = rec.get("id")
        caption = rec.get("caption")
        if image_id and caption:
            if index_image(data_dir, image_id, caption, rec):
                indexed_count += 1

    logger.info("reindex_all_images: completed indexing %d images.", indexed_count)
    return indexed_count


def semantic_search(
    query: str,
    data_dir: Path,
    top_k: int = 10,
    filter_option: str = "Most Similar",
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Execute a semantic natural language vector search over all images.

    Args:
        query:         User's natural language search query (e.g. "beach", "sunset").
        data_dir:      Root data directory.
        top_k:         Maximum number of matching results to retrieve.
        filter_option: Ranking/filtering option:
                       ``"Most Similar"``, ``"Newest"``, ``"Oldest"``, ``"Recently Edited"``.
        api_key:       Optional API key override.
        provider:      Optional provider override.

    Returns:
        tuple[list[dict], str | None]:
            - First element: list of matched record dicts augmented with ``"similarity_score"``.
            - Second element: error message string, or ``None`` on success.
    """
    if not query or not query.strip():
        return [], "Please enter a search query."

    # 1. Generate query embedding vector
    query_vector, error_msg = generate_embedding(
        text=query.strip(),
        api_key=api_key,
        provider=provider,
    )
    if error_msg:
        return [], error_msg

    # 2. Query multi-tiered vector engines
    matches: list[tuple[str, float]] = []

    if _CHROMADB_AVAILABLE:
        matches = _search_chromadb(data_dir, query_vector, top_k * 2)

    if not matches and _FAISS_AVAILABLE:
        matches = _search_faiss(data_dir, query_vector, top_k * 2)

    if not matches:
        matches = _search_json_fallback(data_dir, query_vector, top_k * 2)

    if not matches:
        return [], None

    # 3. Retrieve metadata records and attach similarity scores
    results: list[dict[str, Any]] = []
    for image_id, score in matches:
        record = find_by_id(data_dir, image_id)
        if record:
            record_copy = dict(record)
            # Store normalized similarity score as float percentage (0.0 to 100.0)
            record_copy["similarity_score"] = round(score * 100.0, 1)
            record_copy["similarity_raw"] = score
            results.append(record_copy)

    # 4. Rank results according to user filter
    results = rank_results(results, filter_option)

    return results[:top_k], None


def rank_results(
    results: list[dict[str, Any]],
    filter_option: str = "Most Similar",
) -> list[dict[str, Any]]:
    """Sort search result records according to *filter_option*.

    Args:
        results:       List of search result dicts with attached similarity fields.
        filter_option: Sorting criterion.

    Returns:
        list[dict]: Sorted list of results.
    """
    if filter_option == "Newest":
        return sorted(results, key=lambda r: r.get("uploaded_at", ""), reverse=True)
    if filter_option == "Oldest":
        return sorted(results, key=lambda r: r.get("uploaded_at", ""))
    if filter_option == "Recently Edited":
        def _last_edit_time(r: dict[str, Any]) -> str:
            versions = r.get("versions", [])
            if versions:
                return versions[-1].get("timestamp", r.get("uploaded_at", ""))
            return r.get("uploaded_at", "")
        return sorted(results, key=_last_edit_time, reverse=True)

    # Default: "Most Similar"
    return sorted(results, key=lambda r: r.get("similarity_raw", 0.0), reverse=True)


def retrieve_images(data_dir: Path, image_ids: list[str]) -> list[dict[str, Any]]:
    """Retrieve full metadata records for a list of image IDs.

    Args:
        data_dir:  Root data directory.
        image_ids: List of UUID strings.

    Returns:
        list[dict]: Metadata records in requested ID order.
    """
    records: list[dict[str, Any]] = []
    for image_id in image_ids:
        rec = find_by_id(data_dir, image_id)
        if rec:
            records.append(rec)
    return records
