# AI Things Considered

A daily comic strip generator inspired by NPR's All Things Considered.

Every day, this system reads the latest stories from NPR's All Things Considered, selects six with visual potential, and renders them as a vintage newspaper-style comic strip.

## Latest Comic

See the output at [benolsen.com](https://benolsen.com) or in the [benolsen.com repo](https://github.com/benol5en/benolsen.com/tree/main/comics/ai-things-considered).

## How It Works

1. **Fetch** - Pull stories from NPR's All Things Considered RSS feed
2. **Select** - Gemini Flash picks 6 stories based on visual potential and topic diversity
3. **Prompt** - Generate image prompts in a vintage comic aesthetic
4. **Render** - Gemini 3 Pro creates each panel image
5. **Compose** - Panels assembled into a 3x2 grid with title and date

## Setup

1. Clone this repo
2. Copy `.env.example` to `.env` and add your Google AI API key
3. Install dependencies:
   ```bash
   pip install google-genai python-dotenv feedparser Pillow
   ```

## Usage

```bash
python execution/ai_things_considered.py
```

Output goes to `../benolsen.com/comics/ai-things-considered/` by default.
Set `OUTPUT_DIR` in `.env` to change this.

## Output

Each run produces:
- `{date}.png` - The composite comic strip
- `{date}.json` - Metadata with story titles, summaries, and NPR links

## Free to Use

The generated comics and metadata are free for anyone to use. Each comic includes links back to the original NPR stories.

## Style

The comic uses a vintage newspaper aesthetic:
- Muted earth tone palette (cream, brown, dusty blue, sage green)
- Flat geometric shapes with clean linework
- Diagrammatic, mid-century illustration style
- Oswald font for titles (matching benolsen.com)

## Structure

```
AI-Things-Considered/
├── execution/
│   ├── ai_things_considered.py   # Main generation script
│   ├── test_gemini_image.py      # API test script
│   └── fonts/                    # Oswald font files
├── prompts/
│   └── story_to_image_prompt.md  # LLM prompt for image generation
├── .env.example
└── README.md
```

## License

MIT
