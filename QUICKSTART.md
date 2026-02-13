# Quick Start Guide

Get started with Album Tracker in 5 minutes!

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure API key:**

Copy the example config:
```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and add your API key:
```yaml
llm:
  provider: "openai"  # or "anthropic" or "google"
  openai_api_key: "your-actual-api-key-here"
```

3. **Create directories:**
```bash
mkdir albums_owned albums_wishlist
```

## Quick Workflow

### Option 1: Scan Album Covers

1. Place album cover images in `albums_owned/` directory

2. Run the scanner:
```bash
python album_tracker.py scan
```

3. For each album detected:
   - Confirm the album name and artist
   - Enter the genre (e.g., "rock", "jazz", "pop")
   - Optionally rate it (1-10)

4. The app will automatically enrich albums with metadata!

### Option 2: Manual Entry

Add an album directly:
```bash
python album_tracker.py add \
  --name "Dark Side of the Moon" \
  --artist "Pink Floyd" \
  --genre "rock" \
  --rating 10 \
  --notes "One of the greatest albums ever"
```

## View Your Collection

**List all albums:**
```bash
python album_tracker.py list
```

**View details:**
```bash
python album_tracker.py show 1
```

**Search:**
```bash
python album_tracker.py search --artist "Pink Floyd"
```

## Generate a Website

Create a beautiful website of your collection:
```bash
python generate_site.py
```

Then open `site/index.html` in your browser!

## What Gets Enriched?

When you add an album (with auto-enrichment enabled), the LLM fetches:

- ✅ Track listing
- ✅ Album review
- ✅ Musical style and influences
- ✅ Similar artists
- ✅ Awards
- ✅ Release date, label, producer
- ✅ Duration and track count

## Common Commands

```bash
# Scan images
python album_tracker.py scan

# Add album manually
python album_tracker.py add --name "Album" --artist "Artist" --genre "Genre"

# List all albums
python album_tracker.py list

# Search by artist
python album_tracker.py search --artist "Artist Name"

# View album details
python album_tracker.py show 1

# Update rating
python album_tracker.py update 1 --rating 9

# Enrich metadata
python album_tracker.py enrich 1

# Export to CSV
python album_tracker.py export --format csv --output albums.csv

# Generate website
python generate_site.py
```

## Tips for Success

1. **High-quality images**: Use clear photos of album covers for best extraction results

2. **Genre list**: Check `config.yaml` for predefined genres - you can add your own

3. **Smart enrichment**: By default, enrichment only fetches missing fields. Use `--force` to refresh all fields

4. **Multiple artists**: Use `--artist` multiple times for collaborations:
   ```bash
   python album_tracker.py add --name "Album" --artist "Artist 1" --artist "Artist 2" --genre "Genre"
   ```

5. **Website updates**: The site generator automatically detects database changes - just run it again after adding albums

## Need Help?

- See full documentation in `README.md`
- Check `config.yaml` for all settings
- Try `python album_tracker.py --help` for command reference

Happy collecting! 🎵
