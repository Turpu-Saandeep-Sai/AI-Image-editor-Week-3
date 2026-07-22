"""
prompt_templates.py
-------------------
Reusable prompt engineering templates for the AI-Powered Image Editing Platform.

Responsibilities:
    - Define the **system prompt** that frames every editing request.
    - Provide a dictionary of **preset prompts** for one-click editing operations.
    - Offer ``build_edit_prompt()`` to combine system context and user instructions
      into a single, structured prompt string for the image editing API.

Design notes:
    - All prompts are stored as plain strings — no runtime formatting until
      ``build_edit_prompt()`` is called.
    - Preset keys use human-readable labels that double as button text in the UI.
    - The module is side-effect-free at import time.

Author: AI Image Editor Platform
Version: 2.0.0
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# System prompt — framing context sent with every editing request
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    "You are a professional AI image editor. "
    "Follow the editing instruction exactly. "
    "Preserve image quality. "
    "Do not modify unrelated objects. "
    "Maintain perspective. "
    "Maintain lighting. "
    "Return only the edited image."
)

# ---------------------------------------------------------------------------
# Preset prompts — one-click editing operations
# ---------------------------------------------------------------------------

PRESET_PROMPTS: dict[str, dict[str, str]] = {
    "Remove Background": {
        "prompt": (
            "Remove the entire background from this image. "
            "Keep only the main foreground subject(s) intact. "
            "Replace the background with a clean, transparent or plain white surface."
        ),
        "icon": "🗑️",
        "description": "Remove the background, keeping only the subject",
    },
    "Remove All Objects": {
        "prompt": (
            "Remove all objects from the scene, leaving only the background "
            "environment intact. Fill the removed areas naturally so the "
            "background looks clean and seamless."
        ),
        "icon": "🧹",
        "description": "Remove all objects, keep only the background",
    },
    "Replace Background": {
        "prompt": (
            "Replace the background of this image with a beautiful natural "
            "landscape featuring rolling green hills under a bright blue sky "
            "with scattered white clouds. Keep the foreground subject unchanged."
        ),
        "icon": "🏞️",
        "description": "Replace background with a scenic landscape",
    },
    "Blur Background": {
        "prompt": (
            "Apply a strong professional bokeh blur to the background while "
            "keeping the main foreground subject perfectly sharp and in focus. "
            "Create a pleasing depth-of-field effect."
        ),
        "icon": "🔍",
        "description": "Apply bokeh blur to the background",
    },
    "Change Sky": {
        "prompt": (
            "Replace the sky in this image with a dramatic golden-hour sunset "
            "sky featuring warm orange, pink, and purple tones. Blend the new "
            "sky naturally with the rest of the scene."
        ),
        "icon": "🌅",
        "description": "Replace the sky with a sunset",
    },
    "Convert to Black and White": {
        "prompt": (
            "Convert this image to a high-contrast black and white photograph. "
            "Preserve fine details and tonal range. Apply a subtle film-grain "
            "texture for an artistic, classic look."
        ),
        "icon": "🖤",
        "description": "Convert to artistic black & white",
    },
    "Increase Brightness": {
        "prompt": (
            "Increase the overall brightness and exposure of this image. "
            "Brighten shadows and midtones while preserving highlights. "
            "Make the image look well-lit and vibrant without washing out colors."
        ),
        "icon": "☀️",
        "description": "Brighten the image naturally",
    },
    "Vintage Style": {
        "prompt": (
            "Apply a warm vintage film photography style to this image. "
            "Add faded colors, warm amber tones, slight vignetting, and a "
            "soft film-grain texture reminiscent of 1970s analog photography."
        ),
        "icon": "📷",
        "description": "Apply warm vintage film aesthetic",
    },
    "Cartoon Style": {
        "prompt": (
            "Transform this image into a vibrant cartoon or illustrated style. "
            "Use bold outlines, flat vivid colors, and simplified details while "
            "keeping the overall composition and subjects recognisable."
        ),
        "icon": "🎨",
        "description": "Transform into cartoon illustration",
    },
    "Sharpen Image": {
        "prompt": (
            "Sharpen this image to enhance fine details and clarity. "
            "Apply intelligent sharpening that improves texture and edge "
            "definition without introducing noise or haloing artifacts."
        ),
        "icon": "🔬",
        "description": "Enhance sharpness and detail",
    },
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_edit_prompt(
    user_prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """Combine the system context and a user instruction into a single prompt.

    This function produces the final text that accompanies the image when
    sent to the editing API.  The system prompt provides general editing
    guidelines; the user prompt carries the specific instruction.

    Args:
        user_prompt:    The user's natural-language editing instruction.
        system_prompt:  Optional override for the default system prompt.
                        Falls back to :data:`SYSTEM_PROMPT` when ``None``.

    Returns:
        str: A formatted prompt string ready for the image editing API.

    Example::

        >>> build_edit_prompt("Remove the person from the left side")
        'You are a professional AI image editor. ... \\n\\nUser Instruction:\\nRemove the person from the left side'
    """
    sys = system_prompt or SYSTEM_PROMPT
    return f"{sys}\n\nUser Instruction:\n{user_prompt}"


def get_preset_names() -> list[str]:
    """Return the ordered list of preset edit names (used for UI buttons).

    Returns:
        list[str]: Preset name strings in insertion order.
    """
    return list(PRESET_PROMPTS.keys())


def get_preset_prompt(name: str) -> str:
    """Look up and return the prompt text for a named preset.

    Args:
        name: One of the keys in :data:`PRESET_PROMPTS`.

    Returns:
        str: The preset's editing prompt.

    Raises:
        KeyError: If *name* is not a valid preset.
    """
    entry = PRESET_PROMPTS.get(name)
    if entry is None:
        raise KeyError(
            f"Unknown preset '{name}'. "
            f"Available presets: {', '.join(PRESET_PROMPTS.keys())}"
        )
    return entry["prompt"]
