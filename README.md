# Album Tracker

A CLI application for tracking your music album collection with AI-powered metadata extraction and enrichment.

## Features

- 📸 **Image-based album entry**: Take photos of album covers and automatically extract album information
- 📝 **Manual entry**: Add albums manually with name, artist(s), and genre
- 🤖 **AI-powered enrichment**: Automatically gather detailed metadata using OpenAI, Anthropic Claude, or Google Gemini
  - Track listings, album reviews, musical style descriptions
  - Similar artists, awards, producer and label information
  - Release dates, duration, and more
- 🔍 **Flexible search**: Search and filter by album name, artist, genre, category, rating, and more
- 📊 **Export**: Export your album database to CSV or JSON
- 🌐 **Static website generator**: Generate a beautiful browseable website of your collection
  - Organized by Artists, Genres, Years, and Categories
  - Responsive design with genre-colored badges
- 🏷️ **Dual categorization**: Both open-ended LLM categories and user-defined categories
- ⭐ **Smart refresh**: Only fetch missing metadata fields, or force re-fetch all fields

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your API key in `config.yaml`:
```yaml
llm:
  provider: "openai"  # or "anthropic" or "google"
  openai_api_key: "your-api-key-here"
  # ... other settings
```

4. Create directories for your album cover images:
```bash
mkdir albums_owned albums_wishlist
```

## Usage

### Scan Images

Place images of album covers in the appropriate directories:
- `albums_owned/` - Albums you currently own
- `albums_wishlist/` - Albums on your wishlist

Then scan them:
```bash
python album_tracker.py scan
python album_tracker.py scan --directory albums_owned
python album_tracker.py scan --directory albums_wishlist
```

You'll be prompted to enter the genre and optionally rate each detected album.

### Manual Entry

Add an album manually:
```bash
python album_tracker.py add --name "Dark Side of the Moon" --artist "Pink Floyd" --genre "rock" --rating 10
python album_tracker.py add --name "Kind of Blue" --artist "Miles Davis" --genre "jazz" --notes "Essential jazz album"
```

### Search and List

Search for albums:
```bash
# Search by album name
python album_tracker.py search --name "dark side"

# Search by artist
python album_tracker.py search --artist "Pink Floyd"

# Search by genre
python album_tracker.py search --genre "rock"

# Search by category
python album_tracker.py search --category "concept album"

# Filter by rating
python album_tracker.py search --rating-min 8
```

List all albums:
```bash
python album_tracker.py list
python album_tracker.py list --genre rock
python album_tracker.py list --sort-by rating
```

### View Album Details

Show detailed information about an album:
```bash
python album_tracker.py show 1
python album_tracker.py show "Dark Side of the Moon"
```

### Update Albums

Update album information:
```bash
python album_tracker.py update 1 --rating 10
python album_tracker.py update 1 --notes "Re-listened in 2024"
python album_tracker.py update 1 --genre "progressive rock"
```

### Enrich Metadata

Enrich an album with AI-generated metadata:
```bash
# Fetch only missing fields
python album_tracker.py enrich 1

# Re-fetch all fields (overwrites existing data)
python album_tracker.py enrich 1 --force

# By album name
python album_tracker.py enrich "Dark Side of the Moon"
```

### Manage Categories

Manage your predefined user categories:
```bash
# List categories
python album_tracker.py categories list

# Add a category
python album_tracker.py categories add "road trip music"

# Remove a category
python album_tracker.py categories remove "workout music"
```

### Export Data

Export your album database:
```bash
python album_tracker.py export --format csv --output albums.csv
python album_tracker.py export --format json --output albums.json
```

### Generate Website

Generate a static website of your collection:
```bash
python generate_site.py
```

This creates a `site/` directory with a complete browseable website featuring:
- Dashboard with collection statistics
- Albums organized by Artists, Genres, Years, and Categories
- Detailed pages for each album with track listings, reviews, and more
- Responsive design with genre-colored badges

Open `site/index.html` in your browser to view.

## Configuration

Edit `config.yaml` to customize:

- **LLM Provider**: Choose between OpenAI, Anthropic, or Google
- **API Keys**: Configure your API keys for each provider
- **Models**: Specify which model to use for each provider
- **Auto-enrichment**: Enable/disable automatic metadata enrichment
- **Predefined Genres**: List of common genres for quick selection
- **User Categories**: Define your custom category list for classification

## Database Schema

The application uses SQLite to store album information with the following fields:

**Core Fields (User-entered):**
- ID, Album Name, Artists, Genre, Date Added, Rating, Personal Notes

**Enhanced Metadata (from LLM):**
- Release Date, Label, Producer, Duration, Track Count
- Track Listing, Album Review, Musical Style
- Similar Artists, Awards
- LLM Categories (open-ended)
- User Categories (matched against predefined list)

**Metadata:**
- Source Image Path, Last Updated

## How It Works

1. **Image Scanning**: Place album cover images in `albums_owned/` or `albums_wishlist/`
2. **LLM Extraction**: The LLM analyzes images and extracts album name and artist information
3. **Manual Entry**: You provide genre (required) and optionally rating
4. **Auto-enrichment**: If enabled, the application automatically fetches detailed metadata
5. **Category Matching**: Albums are matched against your predefined categories
6. **Database Storage**: All information is stored in a local SQLite database
7. **Smart Updates**: Use the `enrich` command to update missing fields without overwriting existing data
8. **Website Generation**: Generate a static site to browse your collection beautifully

## Tips

- Use high-quality images of album covers for best results
- The `--force` flag on `enrich` will overwrite existing data - use with caution
- User categories are matched semantically by the LLM, so related terms will work
- Export to CSV for spreadsheet analysis or JSON for programmatic access
- Set `auto_enrich: false` in config to disable automatic metadata fetching
- The website generator only regenerates when the database changes

## Enriched Metadata Examples

When you enrich an album, the LLM provides:

- **Track Listing**: Complete list of tracks in order
- **Album Review**: 2-3 sentence critical reception summary
- **Musical Style**: Detailed description of the album's sound and influences
- **Similar Artists**: List of artists with similar styles
- **Awards**: Major awards won (Grammy, etc.)
- **Release Info**: Release date, record label, producer
- **Categories**: Auto-detected categories like "concept album", "live recording", "debut album"

## Troubleshooting

**"API key not configured" error:**
- Edit `config.yaml` and replace the placeholder with your actual API key

**Images not being processed:**
- Check that images are in the correct directories
- Verify image format is .jpg, .jpeg, .png, or .webp
- Run `scan` command to process new images

**Album not found in enrichment:**
- Try the `--force` flag to re-fetch all information
- Verify the album name and artist are correct in the database

**Website not updating:**
- The site generator detects database changes automatically
- Use `python generate_site.py --force` to force regeneration

## Cost Considerations

This application makes API calls to LLM providers which may incur costs:
- 1 API call per image for album extraction
- 1 API call per album for metadata enrichment
- 1 API call per album for user category matching

With auto-enrichment enabled, expect 3 API calls per new album added from images.

## Security

- API keys are stored in `config.yaml` - set file permissions to 600
- The database contains only album information, no sensitive personal data
- All data is stored locally on your machine

## License

This project is provided as-is for personal use.
