#!/usr/bin/env python3
"""
AI Things Considered - Daily Comic Strip Generator

Fetches NPR All Things Considered stories, generates vintage comic panels,
and composes them into a daily strip.
"""

import os
import sys
import json
import time
import feedparser
from datetime import datetime
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds

# Load environment
load_dotenv()

# Configuration
RSS_FEED = "https://feeds.npr.org/2/rss.xml"
WEB_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent.parent / "output"))
FULLRES_DIR = Path(__file__).parent.parent / "output"  # Local archive, gitignored
TEMP_DIR = Path(__file__).parent.parent / ".tmp"
NUM_PANELS = 6
MIN_PANELS_REQUIRED = 4  # Fail if fewer than this many panels succeed

# Web optimization settings
WEB_MAX_WIDTH = 1000
WEB_QUALITY = 85

# Style constants
STYLE_PREFIX = """Vintage comic panel illustration. Muted earth tone palette - cream, warm brown, dusty blue, sage green, faded ochre. Flat geometric shapes with clean precise linework. Diagrammatic, nostalgic mid-century newspaper illustration aesthetic. Hand-drawn feel with architectural precision."""

# Initialize Gemini client
api_key = os.getenv("GOOGLE_AI_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_AI_API_KEY not found in .env")
client = genai.Client(api_key=api_key)


def fetch_stories():
    """Fetch latest stories from NPR All Things Considered RSS feed."""
    print("Fetching NPR stories...")
    feed = feedparser.parse(RSS_FEED)

    stories = []
    for entry in feed.entries:
        stories.append({
            "title": entry.title,
            "description": entry.get("description", ""),
            "link": entry.link,
            "published": entry.get("published", ""),
        })

    print(f"  Found {len(stories)} stories")
    return stories


def select_stories(stories):
    """Use Gemini Flash to select 6 best stories for visual representation."""
    print("Selecting 6 stories with Gemini Flash...")

    stories_text = "\n\n".join([
        f"[{i+1}] {s['title']}\n{s['description']}"
        for i, s in enumerate(stories)
    ])

    prompt = f"""You are selecting stories for a daily comic strip called "AI Things Considered" based on NPR's All Things Considered.

From these {len(stories)} stories, select exactly 6 that will make the best comic panels. Consider:
1. Visual potential - can this translate to a compelling image? Concrete events > abstract policy debates
2. Topic diversity - mix politics, culture, science, international, human interest
3. Significance - major breaking news takes priority
4. Tonal variety - balance serious with lighter stories

STORIES:
{stories_text}

Return ONLY a JSON array of the 6 selected story numbers (1-indexed), in the order they should appear in the comic. Example: [3, 7, 1, 12, 5, 9]"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    # Parse the response to get story indices
    response_text = response.text.strip()
    # Extract JSON array from response
    import re
    match = re.search(r'\[[\d,\s]+\]', response_text)
    if match:
        indices = json.loads(match.group())
        selected = [stories[i-1] for i in indices[:NUM_PANELS]]
        print(f"  Selected: {[s['title'][:40] + '...' for s in selected]}")
        return selected
    else:
        # Fallback to first 6
        print("  Warning: Could not parse selection, using first 6")
        return stories[:NUM_PANELS]


def generate_image_prompt(story):
    """Use Gemini Flash to create an image generation prompt from a story."""

    prompt = f"""You are a visual translator. Given a news story, create an image prompt that captures its essence in a vintage comic panel aesthetic.

STORY:
Title: {story['title']}
Description: {story['description']}

RULES:
- Capture the FEELING and MEANING, not literal events
- One clear visual idea
- Use symbolic imagery over literal portraits
- Focus on: scenes, objects, silhouettes, symbols, architecture
- Vary composition: bird's eye, worm's eye, medium shot, wide shot
- Text: ONE key word/phrase max, integrated naturally (sign, headline) - or skip entirely

Return ONLY the image prompt, no explanation. Start with the style, then the scene."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    image_prompt = response.text.strip()

    # Ensure style prefix is included
    if not image_prompt.lower().startswith("vintage"):
        image_prompt = f"{STYLE_PREFIX} {image_prompt}"

    return image_prompt


def generate_panel_image(prompt, panel_num):
    """Generate a single comic panel image using Gemini 3 Pro with retries."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Generating panel {panel_num}..." + (f" (attempt {attempt})" if attempt > 1 else ""))

            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="2:3",
                        image_size="1K"
                    ),
                ),
            )

            # Check for valid response
            if not response.candidates:
                raise ValueError("No candidates in response")

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    print(f"    ✓ Panel {panel_num} generated successfully")
                    return Image.open(BytesIO(part.inline_data.data))

            raise ValueError("No image data in response")

        except Exception as e:
            print(f"    ✗ Panel {panel_num} failed: {type(e).__name__}: {e}")

            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                print(f"    Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"    ✗ Panel {panel_num} failed after {MAX_RETRIES} attempts")

    return None


def optimize_for_web(image, max_width=WEB_MAX_WIDTH, quality=WEB_QUALITY):
    """Resize and compress image for web delivery."""
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image.convert('RGB')


def compose_comic_strip(panels, date_str):
    """Compose 6 panels into a final comic strip with title and date."""
    print("Composing final comic strip...")

    # Layout constants
    PANEL_WIDTH = 400
    PANEL_HEIGHT = 600  # 2:3 aspect ratio
    COLS = 3
    ROWS = 2
    GUTTER = 12
    BORDER = 3
    HEADER_HEIGHT = 100
    MARGIN = 30

    # Colors
    BG_COLOR = (252, 249, 242)  # Cream
    BORDER_COLOR = (40, 35, 30)  # Dark brown/black
    TEXT_COLOR = (40, 35, 30)

    # Calculate dimensions
    strip_width = MARGIN * 2 + COLS * PANEL_WIDTH + (COLS - 1) * GUTTER
    strip_height = MARGIN * 2 + HEADER_HEIGHT + ROWS * PANEL_HEIGHT + (ROWS - 1) * GUTTER

    # Create canvas
    strip = Image.new('RGB', (strip_width, strip_height), BG_COLOR)
    draw = ImageDraw.Draw(strip)

    # Load Oswald font (same as website)
    font_dir = Path(__file__).parent / "fonts"
    try:
        title_font = ImageFont.truetype(str(font_dir / "Oswald-Bold.ttf"), 48)
        date_font = ImageFont.truetype(str(font_dir / "Oswald-Regular.ttf"), 22)
    except:
        title_font = ImageFont.load_default()
        date_font = ImageFont.load_default()

    # Draw title - left justified
    title = "AI THINGS CONSIDERED"
    draw.text((MARGIN, MARGIN), title, font=title_font, fill=TEXT_COLOR)

    # Draw date - left justified, below title
    draw.text((MARGIN, MARGIN + 55), date_str, font=date_font, fill=TEXT_COLOR)

    # Place panels
    for i, panel in enumerate(panels):
        if panel is None:
            continue

        col = i % COLS
        row = i // COLS

        x = MARGIN + col * (PANEL_WIDTH + GUTTER)
        y = MARGIN + HEADER_HEIGHT + row * (PANEL_HEIGHT + GUTTER)

        # Resize panel to fit
        panel_resized = panel.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)

        # Draw border
        draw.rectangle(
            [x - BORDER, y - BORDER, x + PANEL_WIDTH + BORDER, y + PANEL_HEIGHT + BORDER],
            outline=BORDER_COLOR,
            width=BORDER
        )

        # Paste panel
        strip.paste(panel_resized, (x, y))

    return strip


def save_metadata(stories, date_str):
    """Save metadata JSON for the comic and update latest.json."""
    metadata = {
        "date": date_str,
        "image": f"{date_str}.jpg",
        "stories": [
            {
                "panel": i + 1,
                "title": s["title"],
                "summary": s["description"],
                "source_url": s["link"]
            }
            for i, s in enumerate(stories)
        ]
    }

    # Save dated metadata file
    metadata_path = WEB_OUTPUT_DIR / f"{date_str}.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to: {metadata_path}")

    # Update latest.json to point to current comic
    latest_path = WEB_OUTPUT_DIR / "latest.json"
    with open(latest_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Latest pointer updated: {latest_path}")

    return metadata


def update_latest_images():
    """Copy the 2 most recent comics to latest-1.jpg and latest-2.jpg."""
    import shutil

    # Find all comic images, sorted by date descending
    comics = sorted(WEB_OUTPUT_DIR.glob("????-??-??.jpg"), reverse=True)

    if len(comics) >= 1:
        shutil.copy(comics[0], WEB_OUTPUT_DIR / "latest-1.jpg")
        print(f"Copied {comics[0].name} → latest-1.jpg")

    if len(comics) >= 2:
        shutil.copy(comics[1], WEB_OUTPUT_DIR / "latest-2.jpg")
        print(f"Copied {comics[1].name} → latest-2.jpg")


def update_archive(date_str):
    """Update archive.json with the new comic entry."""
    archive_path = WEB_OUTPUT_DIR / "archive.json"

    # Load existing archive or create new one
    if archive_path.exists():
        with open(archive_path, "r") as f:
            archive = json.load(f)
    else:
        archive = {"comics": []}

    new_entry = {"date": date_str, "image": f"{date_str}.jpg"}

    # Check if entry already exists (avoid duplicates on re-runs)
    existing_dates = [c["date"] for c in archive["comics"]]
    if date_str not in existing_dates:
        # Insert at beginning (newest first)
        archive["comics"].insert(0, new_entry)

        with open(archive_path, "w") as f:
            json.dump(archive, f, indent=2)
        print(f"Archive updated: {archive_path}")
    else:
        print(f"Archive already contains {date_str}, skipping")


def main():
    """Run the full pipeline."""
    WEB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FULLRES_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    # Allow date override via command line: python ai_things_considered.py 2026-01-16
    if len(sys.argv) > 1:
        today = sys.argv[1]
        today_display = datetime.strptime(today, "%Y-%m-%d").strftime("%B %d, %Y")
        print(f"Using override date: {today}")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        today_display = datetime.now().strftime("%B %d, %Y")

    print(f"\n{'='*60}")
    print(f"AI THINGS CONSIDERED - {today_display}")
    print(f"{'='*60}\n")

    # Step 1: Fetch stories
    all_stories = fetch_stories()

    # Step 2: Select best 6 stories
    selected_stories = select_stories(all_stories)

    # Step 3: Generate image prompts
    print("\nGenerating image prompts...")
    prompts = []
    for i, story in enumerate(selected_stories):
        print(f"  [{i+1}] {story['title'][:50]}...")
        prompt = generate_image_prompt(story)
        prompts.append(prompt)
        print(f"      → {prompt[:80]}...")

    # Step 4: Generate panel images
    print("\nGenerating panel images...")
    panels = []
    for i, prompt in enumerate(prompts):
        panel = generate_panel_image(prompt, i + 1)
        panels.append(panel)

        # Save individual panel to temp
        if panel:
            panel_path = TEMP_DIR / f"panel_{i+1}.png"
            panel.save(panel_path)

    # Check panel success rate
    successful_panels = sum(1 for p in panels if p is not None)
    print(f"\nPanel generation: {successful_panels}/{NUM_PANELS} succeeded")

    if successful_panels < MIN_PANELS_REQUIRED:
        raise RuntimeError(
            f"Only {successful_panels}/{NUM_PANELS} panels generated. "
            f"Minimum required: {MIN_PANELS_REQUIRED}. Aborting."
        )

    # Step 5: Compose final strip
    strip = compose_comic_strip(panels, today_display)

    # Save full-res PNG locally (gitignored)
    fullres_path = FULLRES_DIR / f"{today}.png"
    strip.save(fullres_path)
    print(f"Full-res saved to: {fullres_path}")

    # Save web-optimized JPG to website
    web_strip = optimize_for_web(strip)
    web_path = WEB_OUTPUT_DIR / f"{today}.jpg"
    web_strip.save(web_path, "JPEG", quality=WEB_QUALITY, optimize=True)
    print(f"Web version saved to: {web_path}")

    # Step 6: Save metadata
    metadata = save_metadata(selected_stories, today)

    # Step 7: Update latest-1.png and latest-2.png
    update_latest_images()

    # Step 8: Update archive.json
    update_archive(today)

    print(f"\n{'='*60}")
    print("COMPLETE!")
    print(f"Full-res archived: output/{today}.png")
    print(f"Files ready to commit:")
    print(f"  - comics/ai-things-considered/{today}.jpg")
    print(f"  - comics/ai-things-considered/{today}.json")
    print(f"  - comics/ai-things-considered/latest.json")
    print(f"  - comics/ai-things-considered/latest-1.jpg")
    print(f"  - comics/ai-things-considered/latest-2.jpg")
    print(f"  - comics/ai-things-considered/archive.json")
    print(f"{'='*60}\n")

    return metadata


if __name__ == "__main__":
    main()
