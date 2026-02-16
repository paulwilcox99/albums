#!/usr/bin/env python3
"""
Generate a static website from the albums database.
Only regenerates if the database has changed since last run.
"""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html import escape

# Configuration
DB_PATH = "albums.db"
OUTPUT_DIR = "site"
STATE_FILE = ".site_state.json"

# Genre colors for badges
GENRE_COLORS = {
    'pop': '#e91e63',
    'rock': '#9c27b0',
    'jazz': '#3f51b5',
    'classical': '#2196f3',
    'electronic': '#00bcd4',
    'hip-hop': '#ff9800',
    'country': '#795548',
    'folk': '#8bc34a',
    'metal': '#607d8b',
    'blues': '#5c6bc0',
    'r&b': '#ec407a',
    'world': '#26a69a'
}


def get_db_hash(db_path):
    """Get hash of database file to detect changes."""
    with open(db_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def load_state():
    """Load previous generation state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save generation state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def parse_json_field(value):
    """Parse a JSON field, returning empty list if invalid."""
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
        return [result]
    except:
        return [value] if value else []


def slugify(text):
    """Convert text to URL-safe slug."""
    if not text:
        return "unknown"
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:50]


def get_genre_color(genre):
    """Get color for genre badge."""
    if not genre:
        return '#999'
    return GENRE_COLORS.get(genre.lower(), '#999')


def get_year_from_date(date_str):
    """Extract year from release date."""
    if not date_str:
        return None
    try:
        return date_str.split('-')[0]
    except:
        return None


def get_all_albums(db_path):
    """Fetch all albums from database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM albums ORDER BY album_name")
    albums = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for album in albums:
        album['artists_list'] = parse_json_field(album['artists'])
        album['track_listing_list'] = parse_json_field(album['track_listing'])
        album['similar_artists_list'] = parse_json_field(album['similar_artists'])
        album['awards_list'] = parse_json_field(album['awards'])
        album['llm_categories_list'] = parse_json_field(album['llm_categories'])
        album['user_categories_list'] = parse_json_field(album['user_categories'])
        album['release_year'] = get_year_from_date(album['release_date'])

    return albums


# HTML Templates
def html_header(title, breadcrumbs=None, base=None):
    """Generate HTML header."""
    bc_html = ""
    if breadcrumbs:
        bc_parts = ['<a href="index.html">Home</a>']
        for name, link in breadcrumbs:
            if link:
                bc_parts.append(f'<a href="{link}">{escape(name)}</a>')
            else:
                bc_parts.append(escape(name))
        bc_html = f'<nav class="breadcrumbs">{" → ".join(bc_parts)}</nav>'

    base_tag = f'<base href="{base}">' if base else ''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {base_tag}
    <title>{escape(title)} - Album Collection</title>
    <style>
        :root {{
            --bg: #faf8f5;
            --bg-card: #ffffff;
            --text: #2c2c2c;
            --text-muted: #666666;
            --accent: #e91e63;
            --accent-hover: #c2185b;
            --link: #1a4a6e;
            --link-hover: #0d2d44;
            --border: #d4cfc7;
            --border-light: #e8e4dd;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            padding: 2.5rem;
            max-width: 960px;
            margin: 0 auto;
        }}
        a {{ color: var(--link); text-decoration: underline; text-decoration-color: var(--border); text-underline-offset: 2px; }}
        a:hover {{ color: var(--link-hover); text-decoration-color: var(--link-hover); }}
        h1 {{
            color: var(--text);
            margin-bottom: 1.5rem;
            font-size: 2.2rem;
            font-weight: normal;
            letter-spacing: -0.02em;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 0.75rem;
        }}
        h2 {{
            color: var(--text);
            margin: 2rem 0 1rem;
            font-size: 1.4rem;
            font-weight: normal;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        h3 {{ color: var(--text); margin: 1.25rem 0 0.75rem; font-size: 1.1rem; font-weight: 600; }}
        .breadcrumbs {{ margin-bottom: 2rem; color: var(--text-muted); font-size: 0.9rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .breadcrumbs a {{ color: var(--link); }}
        .card {{
            background: var(--bg-card);
            padding: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-light);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}
        .album-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
        }}
        .album-card {{
            background: var(--bg-card);
            padding: 1.25rem;
            border: 1px solid var(--border-light);
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .album-card:hover {{ border-color: var(--accent); box-shadow: 0 2px 8px rgba(233,30,99,0.08); }}
        .album-card h3 {{ margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600; }}
        .album-card h3 a {{ text-decoration: none; }}
        .album-card h3 a:hover {{ text-decoration: underline; }}
        .album-card .artist {{ color: var(--text-muted); font-size: 0.95rem; font-style: italic; }}
        .album-card .meta {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .rating {{ color: var(--accent); }}
        .genre-badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-weight: 500;
            color: white;
            border-radius: 3px;
        }}
        .tag {{
            display: inline-block;
            background: var(--bg);
            color: var(--text-muted);
            padding: 0.2rem 0.6rem;
            font-size: 0.85rem;
            margin: 0.25rem;
            border: 1px solid var(--border);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            text-decoration: none;
        }}
        .tag:hover {{ background: var(--accent); color: white; border-color: var(--accent); text-decoration: none; }}
        .track-list {{
            list-style-position: inside;
            margin: 0.5rem 0;
            line-height: 1.6;
        }}
        .track-list li {{ margin: 0.25rem 0; }}
        .nav-sections {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .nav-section {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 1px solid var(--border-light);
        }}
        .nav-section h3 {{ margin-bottom: 1rem; color: var(--accent); font-size: 1rem; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .nav-section ul {{ list-style: none; }}
        .nav-section li {{ margin: 0.4rem 0; font-size: 0.95rem; }}
        .nav-section a {{ text-decoration: none; }}
        .nav-section a:hover {{ text-decoration: underline; }}
        .stats {{ display: flex; gap: 3rem; margin-bottom: 2.5rem; flex-wrap: wrap; padding: 1.5rem 0; border-bottom: 1px solid var(--border-light); }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 2.5rem; color: var(--accent); font-weight: normal; font-family: Georgia, serif; }}
        .stat-label {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        dl {{ margin: 1.25rem 0; }}
        dt {{ color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem; text-transform: uppercase; letter-spacing: 0.03em; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        dd {{ margin-left: 0; margin-top: 0.25rem; }}
        .back-to-collections {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
        }}
        .back-to-collections a {{
            color: var(--text-muted);
            text-decoration: none;
        }}
        .back-to-collections a:hover {{
            color: var(--link);
        }}
    </style>
</head>
<body>
<div class="back-to-collections"><a href="https://pauls-collections.vercel.app">← All Collections</a></div>
{bc_html}
<h1>{escape(title)}</h1>
'''


def html_footer():
    """Generate HTML footer."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f'''
<footer style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.8rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; text-align: center;">
    Generated on {timestamp}
</footer>
</body>
</html>
'''


def generate_album_page(album, output_dir):
    """Generate individual album page."""
    slug = f"album-{album['id']}-{slugify(album['album_name'])}"
    filepath = os.path.join(output_dir, "albums", f"{slug}.html")

    artists = ", ".join(album['artists_list']) if album['artists_list'] else album['artists']

    html = html_header(album['album_name'], [("Albums", "albums.html"), (album['album_name'], None)], base="../")

    html += '<div class="card">'
    html += f'<p class="artist">by {escape(artists)}</p>'

    # Genre and rating
    html += '<p style="margin: 1rem 0;">'
    if album['genre']:
        genre_color = get_genre_color(album['genre'])
        html += f'<span class="genre-badge" style="background:{genre_color};">{escape(album["genre"])}</span> '
    if album['rating']:
        html += f'<span class="rating">{"★" * album["rating"]}{"☆" * (10 - album["rating"])}</span> {album["rating"]}/10'
    html += '</p>'

    html += '<dl>'

    if album['release_date']:
        html += f'<dt>Release Date</dt><dd>{escape(str(album["release_date"]))}</dd>'

    if album['label']:
        html += f'<dt>Label</dt><dd>{escape(album["label"])}</dd>'

    if album['producer']:
        html += f'<dt>Producer</dt><dd>{escape(album["producer"])}</dd>'

    if album['total_duration']:
        html += f'<dt>Duration</dt><dd>{escape(album["total_duration"])}</dd>'

    if album['track_count']:
        html += f'<dt>Tracks</dt><dd>{album["track_count"]}</dd>'

    html += '</dl>'

    if album['track_listing_list']:
        html += '<h2>Track Listing</h2><ol class="track-list">'
        for track in album['track_listing_list']:
            if track:
                html += f'<li>{escape(track)}</li>'
        html += '</ol>'

    if album['album_review']:
        html += f'<h2>Review</h2><p>{escape(album["album_review"])}</p>'

    if album['musical_style']:
        html += f'<h2>Musical Style</h2><p>{escape(album["musical_style"])}</p>'

    if album['similar_artists_list']:
        html += '<h2>Similar Artists</h2><p>'
        html += ", ".join(escape(a) for a in album['similar_artists_list'])
        html += '</p>'

    if album['awards_list']:
        html += '<h2>Awards</h2><ul>'
        for award in album['awards_list']:
            html += f'<li>{escape(award)}</li>'
        html += '</ul>'

    if album['llm_categories_list'] or album['user_categories_list']:
        html += '<h2>Categories</h2><p>'
        all_cats = album['llm_categories_list'] + album['user_categories_list']
        for cat in all_cats:
            cat_slug = slugify(cat)
            html += f'<a href="../categories/{cat_slug}.html" class="tag">{escape(cat)}</a>'
        html += '</p>'

    if album['personal_notes']:
        html += f'<h2>Personal Notes</h2><p>{escape(album["personal_notes"])}</p>'

    html += f'<p style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted);">Added: {album["date_added"][:10]}</p>'

    html += '</div>'
    html += html_footer()

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(html)

    return slug


def generate_list_page(title, items, output_path, breadcrumbs, intro=""):
    """Generate a list page (artists, genres, years, categories index)."""
    html = html_header(title, breadcrumbs)

    if intro:
        html += f'<p style="margin-bottom: 1.5rem; color: var(--text-muted);">{intro}</p>'

    html += '<ul style="list-style: none; columns: 2; column-gap: 2rem;">'
    for name, link, count in sorted(items, key=lambda x: x[0].lower()):
        html += f'<li style="margin: 0.5rem 0;"><a href="{link}">{escape(name)}</a> <span style="color: var(--text-muted);">({count})</span></li>'
    html += '</ul>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_group_page(title, albums, output_path, breadcrumbs, base=None):
    """Generate a page showing a group of albums."""
    html = html_header(title, breadcrumbs, base=base)

    html += f'<p style="margin-bottom: 1.5rem; color: var(--text-muted);">{len(albums)} album(s)</p>'

    html += '<div class="album-grid">'
    for album in sorted(albums, key=lambda a: a['album_name'].lower()):
        slug = f"album-{album['id']}-{slugify(album['album_name'])}"
        artists = ", ".join(album['artists_list']) if album['artists_list'] else album['artists']

        html += f'''<div class="album-card">
            <h3><a href="../albums/{slug}.html">{escape(album['album_name'])}</a></h3>
            <p class="artist">{escape(artists)}</p>
            <p class="meta">'''

        if album['genre']:
            genre_color = get_genre_color(album['genre'])
            html += f'<span class="genre-badge" style="background:{genre_color};">{escape(album["genre"])}</span> '

        if album['rating']:
            html += f'<span class="rating">{"★" * album["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_albums_index(albums, output_dir):
    """Generate all albums index page."""
    html = html_header("All Albums", [("All Albums", None)])

    rated_albums = [a for a in albums if a['rating']]
    avg_rating = sum(a['rating'] for a in rated_albums) / len(rated_albums) if rated_albums else 0

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(albums)}</div><div class="stat-label">Total Albums</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
    </div>'''

    html += '<div class="album-grid">'
    for album in sorted(albums, key=lambda a: a['album_name'].lower()):
        slug = f"album-{album['id']}-{slugify(album['album_name'])}"
        artists = ", ".join(album['artists_list']) if album['artists_list'] else album['artists']

        html += f'''<div class="album-card">
            <h3><a href="albums/{slug}.html">{escape(album['album_name'])}</a></h3>
            <p class="artist">{escape(artists)}</p>
            <p class="meta">'''

        if album['genre']:
            genre_color = get_genre_color(album['genre'])
            html += f'<span class="genre-badge" style="background:{genre_color};">{escape(album["genre"])}</span> '

        if album['rating']:
            html += f'<span class="rating">{"★" * album["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "albums.html"), 'w') as f:
        f.write(html)


def generate_index(albums, artists_count, genres_count, years_count, categories_count, output_dir):
    """Generate main index page."""
    html = html_header("Album Collection")

    rated_albums = [a for a in albums if a['rating']]
    avg_rating = sum(a['rating'] for a in rated_albums) / len(rated_albums) if rated_albums else 0

    # Count unique artists
    all_artists = set()
    for album in albums:
        all_artists.update(album['artists_list'])

    # Find most common genre
    genre_counts = defaultdict(int)
    for album in albums:
        if album['genre']:
            genre_counts[album['genre']] += 1
    most_common_genre = max(genre_counts.items(), key=lambda x: x[1])[0] if genre_counts else "N/A"

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(albums)}</div><div class="stat-label">Total Albums</div></div>
        <div class="stat"><div class="stat-value">{len(all_artists)}</div><div class="stat-label">Total Artists</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
        <div class="stat"><div class="stat-value">{most_common_genre}</div><div class="stat-label">Top Genre</div></div>
    </div>'''

    html += '<div class="nav-sections">'

    html += f'''<div class="nav-section">
        <h3>🎵 Browse</h3>
        <ul>
            <li><a href="albums.html">All Albums ({len(albums)})</a></li>
            <li><a href="artists.html">By Artist ({artists_count})</a></li>
            <li><a href="genres.html">By Genre ({genres_count})</a></li>
            <li><a href="years.html">By Year ({years_count})</a></li>
            <li><a href="categories.html">By Category ({categories_count})</a></li>
        </ul>
    </div>'''

    # Recently added
    recent = sorted(albums, key=lambda a: a['date_added'], reverse=True)[:5]
    html += '<div class="nav-section"><h3>🕐 Recently Added</h3><ul>'
    for album in recent:
        slug = f"album-{album['id']}-{slugify(album['album_name'])}"
        html += f'<li><a href="albums/{slug}.html">{escape(album["album_name"])}</a></li>'
    html += '</ul></div>'

    # Top rated
    top_rated = sorted([a for a in albums if a['rating']], key=lambda a: a['rating'], reverse=True)[:5]
    if top_rated:
        html += '<div class="nav-section"><h3>⭐ Top Rated</h3><ul>'
        for album in top_rated:
            slug = f"album-{album['id']}-{slugify(album['album_name'])}"
            html += f'<li><a href="albums/{slug}.html">{escape(album["album_name"])}</a> ({album["rating"]}/10)</li>'
        html += '</ul></div>'

    html += '</div>'
    html += html_footer()

    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(html)


def generate_site(force=False):
    """Generate the complete static site."""
    # Check if regeneration needed
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False

    current_hash = get_db_hash(DB_PATH)
    state = load_state()

    if not force and state.get('db_hash') == current_hash:
        print("Database unchanged. Use --force to regenerate anyway.")
        return True

    print("Generating site...")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "albums"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "artists"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "genres"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "years"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "categories"), exist_ok=True)

    # Get all albums
    albums = get_all_albums(DB_PATH)
    print(f"Found {len(albums)} albums")

    # Generate individual album pages
    for album in albums:
        generate_album_page(album, OUTPUT_DIR)
    print(f"Generated {len(albums)} album pages")

    # Build indexes
    artists_index = defaultdict(list)
    genres_index = defaultdict(list)
    years_index = defaultdict(list)
    categories_index = defaultdict(list)

    for album in albums:
        for artist in album['artists_list']:
            if artist:
                artists_index[artist].append(album)
        if album['genre']:
            genres_index[album['genre']].append(album)
        if album['release_year']:
            years_index[album['release_year']].append(album)
        for cat in album['llm_categories_list'] + album['user_categories_list']:
            if cat:
                categories_index[cat].append(album)

    # Generate artist pages
    artist_items = []
    for artist, artist_albums in artists_index.items():
        slug = slugify(artist)
        filepath = os.path.join(OUTPUT_DIR, "artists", f"{slug}.html")
        generate_group_page(artist, artist_albums, filepath, [("Artists", "artists.html"), (artist, None)], base="../")
        artist_items.append((artist, f"artists/{slug}.html", len(artist_albums)))

    generate_list_page("Artists", artist_items,
                      os.path.join(OUTPUT_DIR, "artists.html"),
                      [("Artists", None)],
                      f"{len(artists_index)} artists in your collection")
    print(f"Generated {len(artists_index)} artist pages")

    # Generate genre pages
    genre_items = []
    for genre, genre_albums in genres_index.items():
        slug = slugify(genre)
        filepath = os.path.join(OUTPUT_DIR, "genres", f"{slug}.html")
        generate_group_page(genre, genre_albums, filepath, [("Genres", "genres.html"), (genre, None)], base="../")
        genre_items.append((genre, f"genres/{slug}.html", len(genre_albums)))

    generate_list_page("Genres", genre_items,
                      os.path.join(OUTPUT_DIR, "genres.html"),
                      [("Genres", None)],
                      f"{len(genres_index)} genres in your collection")
    print(f"Generated {len(genres_index)} genre pages")

    # Generate year pages
    year_items = []
    for year, year_albums in years_index.items():
        slug = year
        filepath = os.path.join(OUTPUT_DIR, "years", f"{slug}.html")
        generate_group_page(year, year_albums, filepath, [("Years", "years.html"), (year, None)], base="../")
        year_items.append((year, f"years/{slug}.html", len(year_albums)))

    # Sort years in reverse chronological order
    year_items_sorted = sorted(year_items, key=lambda x: x[0], reverse=True)
    generate_list_page("Years", year_items_sorted,
                      os.path.join(OUTPUT_DIR, "years.html"),
                      [("Years", None)],
                      f"{len(years_index)} years represented")
    print(f"Generated {len(years_index)} year pages")

    # Generate category pages
    category_items = []
    for cat, cat_albums in categories_index.items():
        slug = slugify(cat)
        filepath = os.path.join(OUTPUT_DIR, "categories", f"{slug}.html")
        generate_group_page(cat, cat_albums, filepath, [("Categories", "categories.html"), (cat, None)], base="../")
        category_items.append((cat, f"categories/{slug}.html", len(cat_albums)))

    generate_list_page("Categories", category_items,
                      os.path.join(OUTPUT_DIR, "categories.html"),
                      [("Categories", None)],
                      f"{len(categories_index)} categories")
    print(f"Generated {len(categories_index)} category pages")

    # Generate all albums page
    generate_albums_index(albums, OUTPUT_DIR)

    # Generate main index
    generate_index(albums, len(artists_index), len(genres_index), len(years_index), len(categories_index), OUTPUT_DIR)

    # Save state
    save_state({'db_hash': current_hash, 'generated_at': datetime.now().isoformat()})

    print(f"\n✓ Site generated in '{OUTPUT_DIR}/'")
    print(f"  Open {OUTPUT_DIR}/index.html to view")

    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    success = generate_site(force=force)
    sys.exit(0 if success else 1)
