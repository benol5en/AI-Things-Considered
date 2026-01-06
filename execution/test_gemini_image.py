#!/usr/bin/env python3
"""Test Gemini 3 Pro image generation with free tier API."""

import os
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# Load environment
load_dotenv()
api_key = os.getenv("GOOGLE_AI_API_KEY")

if not api_key:
    print("ERROR: GOOGLE_AI_API_KEY not found in .env")
    exit(1)

# Initialize client
client = genai.Client(api_key=api_key)

# Test prompt in the vintage comic style
test_prompt = """Vintage comic panel illustration. Muted earth tone palette - cream, warm brown, dusty blue, sage green. Flat geometric shapes with clean precise linework. Diagrammatic, nostalgic mid-century newspaper illustration aesthetic. A single microphone at a radio broadcast desk, warm amber studio lighting, geometric art deco patterns on the wall behind, bird's eye view looking down at the desk surface with scattered papers and a coffee cup."""

print("Testing Gemini 3 Pro image generation...")
print(f"Prompt: {test_prompt[:100]}...")

try:
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=test_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="2:3",
                image_size="1K"
            ),
        ),
    )

    # Save the image
    output_dir = Path(__file__).parent.parent / ".tmp"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_comic_panel.png"

    for part in response.candidates[0].content.parts:
        if part.text:
            print(f"Model response: {part.text}")
        elif part.inline_data:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"SUCCESS! Image saved to: {output_path}")

except Exception as e:
    print(f"ERROR: {e}")
