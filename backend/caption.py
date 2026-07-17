"""
caption.py
----------
AI-powered image caption generation for the AI-Powered Image Editing Platform.

Responsibilities:
    - generate_caption(): High-level entry point that orchestrates the
                          full caption pipeline (encode → call API → retry).
    - vision_api():       Low-level call to the OpenAI Vision API.
    - retry_logic():      Decorator / helper that wraps any callable with
                          exponential-backoff retry behaviour.

Supported providers:
    - OpenAI  (default): ``gpt-4o`` with vision capabilities.
    - Gemini  (opt-in):  ``gemini-1.5-flash`` via google-generativeai SDK.

Provider selection:
    Set ``VISION_PROVIDER=gemini`` in ``.env`` to use Gemini.
    Defaults to OpenAI when the variable is absent or set to ``openai``.

Author: AI Image Editor Platform
Version: 1.0.0
"""

import base64
import io
import logging
import os
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAPTION_PROMPT: str = (
    "You are an expert image captioning assistant. " 
    "Describe the image in 40-60 words. "
    "Include: main objects, environment, people, colors, background, and "
    "important details. Output only the caption."
)

OPENAI_MODEL: str = "gpt-4o"
GEMINI_MODEL: str = "gemini-2.5-flash"  # uses new google-genai SDK

DEFAULT_MAX_RETRIES: int = 3
DEFAULT_INITIAL_DELAY: float = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR: float = 2.0
MAX_IMAGE_PIXELS: int = 2048  # longest side for API submission

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry_logic(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retriable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator that retries a function with exponential back-off.

    Args:
        max_retries:           Maximum number of *additional* attempts after
                               the first failure (total calls = max_retries + 1).
        initial_delay:         Seconds to wait before the first retry.
        backoff_factor:        Multiplier applied to the delay on each retry.
        retriable_exceptions:  Exception types that trigger a retry; all others
                               are re-raised immediately.

    Returns:
        Callable: The wrapped function.

    Example::

        @retry_logic(max_retries=3, initial_delay=1.0)
        def flaky_api_call():
            ...
    """
    def decorator(func: F) -> F:  # type: ignore[return]
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exc: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retriable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        logger.warning(
                            "retry_logic: attempt %d/%d failed for '%s' — %s. "
                            "Retrying in %.1fs …",
                            attempt + 1,
                            max_retries + 1,
                            func.__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            "retry_logic: all %d attempts failed for '%s'.",
                            max_retries + 1,
                            func.__name__,
                        )

            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resize_for_api(image_bytes: bytes) -> bytes:
    """Shrink the image so its longest side is ≤ MAX_IMAGE_PIXELS.

    This keeps Vision API costs predictable and avoids payload-size limits.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        bytes: Resized (if necessary) JPEG-encoded image bytes.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        w, h = img.size
        if max(w, h) > MAX_IMAGE_PIXELS:
            scale = MAX_IMAGE_PIXELS / max(w, h)
            img = img.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS,
            )

        # Normalise to JPEG for consistent API behaviour
        if img.mode not in ("RGB",):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def _encode_image_base64(image_bytes: bytes) -> str:
    """Base64-encode *image_bytes* for embedding in an API request.

    Args:
        image_bytes: Raw (possibly pre-resized) image bytes.

    Returns:
        str: Base64-encoded string.
    """
    return base64.b64encode(image_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# OpenAI Vision call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_openai_vision(
    api_key: str,
    image_b64: str,
    prompt: str,
) -> str:
    """Send one request to the OpenAI Vision API and return the caption.

    Args:
        api_key:    OpenAI secret key.
        image_b64:  Base64-encoded JPEG image.
        prompt:     System/user prompt for caption generation.

    Returns:
        str: The generated caption text.

    Raises:
        ImportError:  If the ``openai`` package is not installed.
        RuntimeError: If the API returns an unexpected response.
        openai.OpenAIError: On network / API errors (triggers retry).
    """
    try:
        import openai  # lazy import — not everyone uses OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for OpenAI Vision. "
            "Install it with: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        max_tokens=200,
        temperature=0.4,
    )

    choices = response.choices
    if not choices:
        raise RuntimeError("OpenAI Vision returned an empty choices list.")

    caption = choices[0].message.content
    if not caption:
        raise RuntimeError("OpenAI Vision returned an empty caption.")

    return caption.strip()


# ---------------------------------------------------------------------------
# Gemini Vision call
# ---------------------------------------------------------------------------

@retry_logic(
    max_retries=DEFAULT_MAX_RETRIES,
    initial_delay=DEFAULT_INITIAL_DELAY,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
)
def _call_gemini_vision(
    api_key: str,
    image_bytes: bytes,
    prompt: str,
) -> str:
    """Send one request to the Gemini Vision API and return the caption.

    Uses the new **google-genai** SDK (``google-genai`` pip package) with
    the ``gemini-2.5-flash`` model and its ``Client``-based API.

    Note on ``thinking_budget=0``:
        Gemini 2.5 Flash enables chain-of-thought thinking by default.
        Thinking tokens count against ``max_output_tokens``, so a low
        limit (e.g. 200) leaves almost no room for the actual caption
        text.  For deterministic, short caption generation we disable
        thinking entirely — it is unnecessary overhead here.

    Args:
        api_key:      Google AI Studio API key.
        image_bytes:  Raw image bytes (JPEG preferred after pre-processing).
        prompt:       Caption generation prompt.

    Returns:
        str: The generated caption text.

    Raises:
        ImportError:  If ``google-genai`` is not installed.
        RuntimeError: If the API returns an unexpected or empty response.
    """
    try:
        from google import genai  # new SDK: pip install google-genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise ImportError(
            "The 'google-genai' package is required for Gemini Vision. "
            "Install it with: pip install google-genai"
        ) from exc

    # Instantiate a client — no global configure() call needed
    client = genai.Client(api_key=api_key)

    # Build an inline image Part from raw bytes
    image_part = genai_types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
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
            temperature=0.4,
            # 8192 tokens — generous budget so thinking never starves the
            # actual caption output, regardless of thinking_budget behaviour
            # in the installed SDK version.
            max_output_tokens=8192,
            # Attempt to disable thinking (Gemini 2.5 Flash default).
            # If ThinkingConfig is unavailable in the installed SDK version
            # the exception is caught and the large max_output_tokens above
            # acts as the safety net.
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        ),
    )

    # Use the SDK's built-in .text helper — it aggregates only the real
    # output parts (not thinking parts) from the first candidate.
    text: str = ""
    if response.text:
        text = response.text.strip()
    elif response.candidates:
        # Fallback: manually join non-thinking parts
        candidate = response.candidates[0]
        finish = getattr(candidate, "finish_reason", None)
        logger.warning(
            "_call_gemini_vision: response.text is empty "
            "(finish_reason=%s). Attempting part-level extraction.",
            finish,
        )
        if candidate.content and candidate.content.parts:
            text = "".join(
                p.text
                for p in candidate.content.parts
                if hasattr(p, "text") and not getattr(p, "thought", False)
            ).strip()

    if not text:
        raise RuntimeError(
            "Gemini Vision returned an empty response. "
            "Check your API key and model availability."
        )

    return text



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def vision_api(
    image_bytes: bytes,
    api_key: str,
    prompt: str = CAPTION_PROMPT,
    provider: str = "openai",
) -> str:
    """Call the configured Vision API and return the generated caption.

    This function is the single dispatch point for all provider calls.
    It handles image pre-processing (resize + encode) before delegating
    to the provider-specific implementation.

    Args:
        image_bytes: Raw image bytes (any format supported by PIL).
        api_key:     API key for the chosen provider.
        prompt:      Caption generation prompt.
        provider:    ``"openai"`` or ``"gemini"``.

    Returns:
        str: The generated caption string.

    Raises:
        ValueError:   If an unsupported provider is specified.
        RuntimeError: If the API call fails after all retries.
    """
    # Resize to keep API costs low and avoid payload limits
    processed_bytes = _resize_for_api(image_bytes)

    if provider.lower() == "gemini":
        return _call_gemini_vision(
            api_key=api_key,
            image_bytes=processed_bytes,
            prompt=prompt,
        )

    if provider.lower() in ("openai", ""):
        image_b64 = _encode_image_base64(processed_bytes)
        return _call_openai_vision(
            api_key=api_key,
            image_b64=image_b64,
            prompt=prompt,
        )

    raise ValueError(
        f"Unsupported vision provider: '{provider}'. "
        "Choose 'openai' or 'gemini'."
    )


def generate_caption(
    image_path: Path,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Generate an AI caption for the image at *image_path*.

    This is the top-level entry point called by the UI layer.  It reads
    configuration from the environment if not supplied explicitly, then
    delegates to :func:`vision_api`.

    Args:
        image_path: Absolute path to the stored image file.
        api_key:    API key override (falls back to environment variable).
        provider:   Provider override (falls back to ``VISION_PROVIDER``
                    env var, or ``"openai"`` by default).

    Returns:
        tuple[str, str | None]:
            - First element: the caption string (empty string on failure).
            - Second element: an error message string, or ``None`` on success.
    """
    # --- Resolve provider --------------------------------------------------
    resolved_provider = (
        provider
        or os.getenv("VISION_PROVIDER", "openai").lower()
    )

    # --- Resolve API key ---------------------------------------------------
    env_key_name = (
        "GOOGLE_API_KEY" if resolved_provider == "gemini" else "OPENAI_API_KEY"
    )
    resolved_key = api_key or os.getenv(env_key_name, "")

    if not resolved_key:
        error_msg = (
            f"API key not found. Set the '{env_key_name}' environment variable "
            f"in your .env file."
        )
        logger.error("generate_caption: %s", error_msg)
        return "", error_msg

    # --- Read image bytes --------------------------------------------------
    if not image_path.exists():
        error_msg = f"Image file not found: {image_path}"
        logger.error("generate_caption: %s", error_msg)
        return "", error_msg

    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        error_msg = f"Cannot read image file: {exc}"
        logger.error("generate_caption: %s", error_msg)
        return "", error_msg

    # --- Call Vision API ---------------------------------------------------
    try:
        caption = vision_api(
            image_bytes=image_bytes,
            api_key=resolved_key,
            prompt=CAPTION_PROMPT,
            provider=resolved_provider,
        )
        logger.info(
            "generate_caption: caption generated for %s (%d chars).",
            image_path.name,
            len(caption),
        )
        return caption, None

    except Exception as exc:  # noqa: BLE001
        error_msg = f"Caption generation failed: {exc}"
        logger.error("generate_caption: %s", error_msg)
        return "", error_msg
