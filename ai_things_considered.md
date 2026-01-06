# AI Things Considered

> Daily comic strip displayed on benolsen.com, inspired by NPR's All Things Considered. 6 panels illustrating the day's news in a vintage comic aesthetic.

## Overview

The comic generation happens **externally** (separate system with better image generation). This directive covers the **benolsen.com side**: receiving, displaying, and archiving the finished comics.

## Architecture

```
┌─────────────────────────────────────┐
│  EXTERNAL SYSTEM (runs elsewhere)   │
│  - Fetch NPR stories                │
│  - Generate prompts (LLM)           │
│  - Generate images (good models)    │
│  - Compose final strip              │
└──────────────┬──────────────────────┘
               │
               │ Finished comic + metadata
               ▼
┌─────────────────────────────────────┐
│  BENOLSEN.COM (this repo)           │
│  - Receive comic via Cloudinary     │
│  - Display on website               │
│  - Archive previous editions        │
└─────────────────────────────────────┘
```

## News Source

**RSS Feed**: `https://feeds.npr.org/2/rss.xml`
- All Things Considered stories
- Fields: title, description, link, author, pubDate
- Descriptions: 1-2 sentences (15-50 words)

**Transcripts**: Available same-day on story pages

## Story Selection

ATC publishes ~20 stories daily. The LLM selects 6 based on:

1. **Visual potential** - Can this translate to a compelling image? Abstract policy debates rank lower than concrete events.
2. **Topic diversity** - Avoid 6 politics stories. Mix: politics, culture, science, international, human interest, etc.
3. **Significance** - Major breaking news takes priority over evergreen features.
4. **Variety of tone** - Balance serious/heavy with lighter stories when available.

Selection happens before prompt generation. Input: all RSS items. Output: 6 ranked stories with brief rationale (for debugging/review).

**Transcripts** (if RSS description isn't enough context):
- ATC transcripts appear to publish shortly after audio
- Can scrape full transcript from story URL
- Transcript page: `https://npr.org/transcripts`

## Inputs (from external system)

The external system delivers:

1. **Comic image**: Final composed strip (PNG/JPG)
   - Uploaded to Cloudinary with consistent naming: `ai-things-considered/{date}.png`

2. **Metadata JSON**: Story details for captions/tooltips
   ```json
   {
     "date": "2026-01-05",
     "stories": [
       {
         "panel": 1,
         "title": "Venezuelan President Captured",
         "summary": "Brief description...",
         "source_url": "https://npr.org/..."
       },
       // ... 5 more
     ]
   }
   ```

## Website Integration

### Display Location
- New section on benolsen.com: "AI Things Considered"
- Shows latest comic prominently
- Archive/gallery of previous editions

### Components Needed

1. **Section HTML**: Panel in index.html for displaying comic
2. **Data source**: JSON file or API endpoint with comic metadata
3. **Archive page**: Optional - gallery of past comics

### Panel Hyperlinks

Each comic panel links to its original NPR story. Implementation options:

1. **Image map**: Define clickable regions over the composite image
2. **Overlay grid**: CSS grid of transparent links positioned over panels
3. **Tooltip + click**: Show story title on hover, link on click

The `source_url` in metadata provides the link destination for each panel.

### Update Mechanism

Options (TBD based on external system):

1. **Manual**: External system uploads to Cloudinary, manually update site
2. **Cloudinary webhook**: Trigger site rebuild on new upload
3. **Scheduled fetch**: Site pulls latest from known Cloudinary path
4. **GitHub Action**: External system commits metadata, triggers deploy

## Storage (GitHub)

Comics are stored in the repo and version controlled:

```
benolsen.com/
└── comics/
    └── ai-things-considered/
        ├── 2026-01-05.png      ← Comic strip image
        ├── 2026-01-05.json     ← Metadata (stories, links)
        ├── 2026-01-04.png
        ├── 2026-01-04.json
        └── ...
```

After generating a new comic, commit and push to publish.

## Image Generation Settings

```python
image_config=types.ImageConfig(
    aspect_ratio="2:3",  # Portrait orientation
    image_size="1K"      # Smaller, faster
)
```

## Style Guide (for external system reference)

### Visual Style
- Muted, earthy color palette (creams, browns, muted blues/greens)
- Flat, geometric design
- Hand-drawn feel with clean lines
- Nostalgic newspaper/vintage comic aesthetic
- No photorealism - stylized and diagrammatic

### Content Guidelines
- Symbolic imagery over literal portraits (unless reference image available)
- Focus on: scenes, objects, silhouettes, symbols
- Sparse text integrated naturally (signs, headlines)
- No violent or graphic content

## Comic Strip Template

After generating 6 panels, composite them into a final strip.

### Layout
```
┌──────────────────────────────────────┐
│      AI THINGS CONSIDERED            │
│         January 5, 2026              │
├────────────┬────────────┬────────────┤
│            │            │            │
│  Panel 1   │  Panel 2   │  Panel 3   │
│            │            │            │
├────────────┼────────────┼────────────┤
│            │            │            │
│  Panel 4   │  Panel 5   │  Panel 6   │
│            │            │            │
└────────────┴────────────┴────────────┘
```

### Specs
- **Grid**: 3x2 (3 columns, 2 rows)
- **Panel borders**: Black outlines (2-3px)
- **Title**: "AI THINGS CONSIDERED" - bold, vintage typeface
- **Date**: Below title, smaller
- **Background**: Cream/off-white (matches site palette)
- **Gutter**: Small gap between panels

### Implementation
- Use Python PIL/Pillow or similar
- Script: `execution/compose_comic_strip.py` (in AI-Things-Considered repo)
- Output: Single PNG ready for Cloudinary upload

## Implementation Steps

### Phase 1: Static Display
- [ ] Add "AI Things Considered" section to index.html
- [ ] Hardcode first comic for testing layout
- [ ] Style to match site aesthetic

### Phase 2: Dynamic Updates
- [ ] Determine update mechanism (webhook, fetch, etc.)
- [ ] Implement metadata loading for captions
- [ ] Add archive/gallery view

### Phase 3: Full Automation
- [ ] Connect to external generation system
- [ ] Automated daily updates
- [ ] Error handling for missing comics

## External System

**Repo**: `AI-Things-Considered`

The generation pipeline lives in a separate repository and includes:
- NPR story fetching
- LLM: **Gemini 3 Flash** (prompt generation, story processing)
- Image generation: **Gemini 3 Pro**
- Reference image lookup (for public figures)
- Comic composition
- Cloudinary upload

**Access**: Google Ultra subscription

See that repo for generation-side documentation.

## Reference Image Library

Gemini won't generate recognizable politicians from text prompts alone. Workaround: use reference images.

### Structure

```
AI-Things-Considered/
└── reference_images/
    ├── manifest.json
    ├── trump.jpg
    ├── maduro.jpg
    ├── walz.jpg
    └── ...
```

### Manifest Format

```json
{
  "donald trump": {
    "file": "trump.jpg",
    "aliases": ["trump", "president trump", "the president"],
    "features": "man with distinctive swept-back blonde hair, heavy brow, long red tie, dark suit"
  },
  "nicolás maduro": {
    "file": "maduro.jpg",
    "aliases": ["maduro", "venezuelan president"],
    "features": "heavyset man with thick black mustache, dark slicked hair, military-style jacket"
  },
  "tim walz": {
    "file": "walz.jpg",
    "aliases": ["walz", "governor walz", "minnesota governor"],
    "features": "balding man with short gray beard, glasses, friendly midwestern appearance"
  }
}
```

The `features` field provides distinctive visual traits for the prompt. Reference image gives likeness; features ensure Gemini generates a new stylized image (not copy-pasting the portrait).

### Lookup Pipeline

1. LLM extracts person names from story
2. Check manifest for name or alias match
3. **Match found** → attach reference image to Gemini generation call
4. **No match** → fall back to contextual description ("a figure in a suit")

### Image Sources (public domain / CC)

- **US Government officials**: Official portraits (public domain)
- **World leaders**: Wikimedia Commons (CC licensed)
- **UN photos**: Often freely available

### Maintenance

- Start with 20-30 key figures
- Add new faces as they become newsworthy
- Update when officials change roles

---

*Last updated: 2026-01-05*
