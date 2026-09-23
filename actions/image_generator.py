"""
Jarvis image generation action using Stability AI.

Backend:
    Stability AI - Stable Image Core
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# Output directory
# ---------------------------------------------------------

OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "generated_images"
)


# ---------------------------------------------------------
# Plugin definition
# ---------------------------------------------------------

PLUGIN = {
    "name": "image_generator",

    "description": (
        "Generate an image from a text description using "
        "Stability AI. Use this when the user explicitly "
        "asks Jarvis to create, generate, draw, design, "
        "visualize, or make an image."
    ),

    "parameters": {
        "type": "OBJECT",

        "properties": {

            "prompt": {
                "type": "STRING",
                "description": (
                    "Detailed visual description of the image "
                    "to generate."
                ),
            },

            "aspect_ratio": {
                "type": "STRING",
                "description": (
                    "Image aspect ratio. Examples: "
                    "1:1, 16:9, 9:16, 4:5, 3:2."
                ),
            },
        },

        "required": ["prompt"],
    },
}


# ---------------------------------------------------------
# Stability AI generation
# ---------------------------------------------------------

def generate_with_stability(
    prompt: str,
    aspect_ratio: str = "1:1",
) -> str:

    api_key = os.environ.get(
        "STABILITY_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "STABILITY_API_KEY is not set. "
            "Add it to your .env file."
        )

    # -----------------------------------------------------
    # Stability AI Stable Image Core
    # -----------------------------------------------------

    url = (
        "https://api.stability.ai/"
        "v2beta/stable-image/generate/core"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*",
    }

    data = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": aspect_ratio,
    }

    # -----------------------------------------------------
    # API request
    # -----------------------------------------------------

    response = requests.post(
        url,
        headers=headers,
        files={
            "none": ""
        },
        data=data,
        timeout=120,
    )

    # -----------------------------------------------------
    # Error handling
    # -----------------------------------------------------

    if response.status_code != 200:

        try:
            error_message = response.text
        except Exception:
            error_message = "Unknown Stability API error."

        raise RuntimeError(
            f"Stability API error "
            f"{response.status_code}: "
            f"{error_message}"
        )

    # -----------------------------------------------------
    # Save image
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = int(
        time.time()
    )

    image_path = (
        OUTPUT_DIR
        / f"jarvis_image_{timestamp}.png"
    )

    image_path.write_bytes(
        response.content
    )

    return str(
        image_path.resolve()
    )


# ---------------------------------------------------------
# Jarvis action entry point
# ---------------------------------------------------------

def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> dict:

    parameters = parameters or {}

    # -----------------------------------------------------
    # Extract prompt
    # -----------------------------------------------------

    prompt = (
        parameters.get("prompt")
        or ""
    ).strip()

    if not prompt:

        return {
            "type": "text",
            "content": (
                "I need an image description "
                "before I can generate it."
            ),
        }

    # -----------------------------------------------------
    # Extract aspect ratio
    # -----------------------------------------------------

    aspect_ratio = (
        parameters.get("aspect_ratio")
        or "1:1"
    ).strip()

    # Supported ratios for Stable Image Core
    allowed_ratios = {
        "1:1",
        "16:9",
        "21:9",
        "2:3",
        "3:2",
        "4:5",
        "5:4",
        "9:16",
        "9:21",
    }

    if aspect_ratio not in allowed_ratios:

        aspect_ratio = "1:1"

    # -----------------------------------------------------
    # Generate
    # -----------------------------------------------------

    try:

        image_path = generate_with_stability(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )

    except Exception as exc:

        return {
            "type": "text",
            "content": (
                f"Image generation failed: {exc}"
            ),
        }

    # -----------------------------------------------------
    # Return structured result
    # -----------------------------------------------------

    return {
        "type": "image",
        "path": image_path,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
    }