#!/usr/bin/env python3
import click
import yaml
import json
import csv
from pathlib import Path
from typing import Optional

from database import Database
from llm_providers import get_provider
from image_processor import ImageProcessor
from album_manager import AlbumManager


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save configuration to config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_managers():
    """Initialize and return database, LLM provider, and album manager."""
    config = load_config()

    # Validate API key
    provider_name = config['llm']['provider']
    api_key_field = f"{provider_name}_api_key"

    if config['llm'][api_key_field] == f"your-{provider_name}-api-key-here":
        click.echo(f"Error: Please configure your {provider_name.upper()} API key in config.yaml", err=True)
        raise click.Abort()

    db = Database(config['database']['path'])
    llm_provider = get_provider(config)
    album_manager = AlbumManager(db, llm_provider, config)

    return config, db, llm_provider, album_manager


@click.group()
def cli():
    """Album Tracker - Track your music album collection with AI-powered metadata."""
    pass


@cli.command()
@click.option('--directory', type=click.Choice(['albums_owned', 'albums_wishlist', 'all']), default='all',
              help='Directory to scan for images')
def scan(directory):
    """Scan directories for album cover images and extract information."""
    config, db, llm_provider, album_manager = get_managers()
    image_processor = ImageProcessor(config, db)

    directories = []
    if directory == 'all':
        directories = [config['directories']['albums_owned'], config['directories']['albums_wishlist']]
    else:
        directories = [config['directories'][directory]]

    total_albums_added = 0

    for dir_name in directories:
        click.echo(f"\nScanning directory: {dir_name}")
        unprocessed_images = image_processor.scan_directory(dir_name)

        if not unprocessed_images:
            click.echo(f"No new images found in {dir_name}")
            continue

        click.echo(f"Found {len(unprocessed_images)} unprocessed image(s)")

        for image_path in unprocessed_images:
            click.echo(f"\nProcessing: {Path(image_path).name}")

            try:
                # Extract albums from image
                albums = llm_provider.extract_albums_from_image(image_path)

                if not albums:
                    click.echo("  No albums detected in image")
                    db.mark_image_processed(image_path, 0)
                    continue

                click.echo(f"  Detected {len(albums)} album(s)")

                albums_added = 0
                for album_data in albums:
                    album_name = album_data['album_name']
                    artists = album_data['artists']

                    click.echo(f"  - {album_name} by {', '.join(artists)}")

                    # Prompt for genre (required)
                    predefined_genres = config['settings'].get('predefined_genres', [])
                    click.echo(f"    Available genres: {', '.join(predefined_genres)}")
                    genre = click.prompt("    Genre", type=str)

                    # Prompt for rating (optional)
                    rating = click.prompt("    Rating (1-10, or 0 to skip)", type=int, default=0)

                    # Prepare album data
                    album_entry = {
                        'album_name': album_name,
                        'artists': artists,
                        'genre': genre,
                        'source_image_path': image_path
                    }

                    if rating > 0:
                        album_entry['rating'] = rating

                    # Add album
                    album_id, status = album_manager.add_album(album_entry)

                    if status == 'duplicate':
                        click.echo(f"    Already in database (ID: {album_id})")
                    elif status == 'added':
                        click.echo(f"    Added to database (ID: {album_id})")
                        albums_added += 1

                total_albums_added += albums_added

                # Mark image as processed
                db.mark_image_processed(image_path, albums_added)

            except Exception as e:
                click.echo(f"  Error processing image: {e}", err=True)
                continue

    click.echo(f"\n✓ Scan complete. Added {total_albums_added} new album(s).")


@cli.command()
@click.option('--name', required=True, help='Album name')
@click.option('--artist', 'artists', multiple=True, required=True, help='Artist name(s)')
@click.option('--genre', required=True, help='Genre')
@click.option('--rating', type=click.IntRange(1, 10), help='Rating (1-10)')
@click.option('--notes', help='Personal notes')
def add(name, artists, genre, rating, notes):
    """Manually add an album to the database."""
    config, db, llm_provider, album_manager = get_managers()

    # Prepare album data
    album_data = {
        'album_name': name,
        'artists': list(artists),
        'genre': genre
    }

    if rating:
        album_data['rating'] = rating

    if notes:
        album_data['personal_notes'] = notes

    # Add album
    try:
        album_id, status = album_manager.add_album(album_data)

        if status == 'duplicate':
            click.echo(f"Album already exists in database (ID: {album_id})")
            if click.confirm("Do you want to update it?"):
                updates = {}
                if rating:
                    updates['rating'] = rating
                if notes:
                    updates['personal_notes'] = notes
                if updates:
                    album_manager.update_album(album_id, updates)
                    click.echo("✓ Album updated")
        elif status == 'added':
            click.echo(f"✓ Album added successfully (ID: {album_id})")

    except Exception as e:
        click.echo(f"Error adding album: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--name', help='Filter by album name (partial match)')
@click.option('--artist', help='Filter by artist (partial match)')
@click.option('--genre', help='Filter by genre (partial match)')
@click.option('--category', help='Filter by category')
@click.option('--rating-min', type=click.IntRange(1, 10), help='Minimum rating')
@click.option('--rating-max', type=click.IntRange(1, 10), help='Maximum rating')
def search(name, artist, genre, category, rating_min, rating_max):
    """Search for albums with various filters."""
    config, db, llm_provider, album_manager = get_managers()

    filters = {}

    if name:
        filters['name'] = name
    if artist:
        filters['artist'] = artist
    if genre:
        filters['genre'] = genre
    if category:
        filters['category'] = category
    if rating_min:
        filters['rating_min'] = rating_min
    if rating_max:
        filters['rating_max'] = rating_max

    albums = album_manager.search_albums(filters)

    if not albums:
        click.echo("No albums found matching the criteria.")
        return

    click.echo(f"\nFound {len(albums)} album(s):\n")

    for album in albums:
        click.echo(album_manager.format_album_display(album))
        click.echo()


@cli.command(name='list')
@click.option('--genre', help='Filter by genre')
@click.option('--sort-by', type=click.Choice(['name', 'artist', 'rating', 'date_added']), default='date_added',
              help='Sort by field')
def list_albums(genre, sort_by):
    """List all albums in the database."""
    config, db, llm_provider, album_manager = get_managers()

    filters = {}
    if genre:
        filters['genre'] = genre

    filters['sort_by'] = sort_by

    albums = album_manager.search_albums(filters)

    if not albums:
        click.echo("No albums in database.")
        return

    click.echo(f"\n{len(albums)} album(s) in database:\n")

    for album in albums:
        click.echo(album_manager.format_album_display(album))
        click.echo()


@cli.command()
@click.argument('album_identifier')
def show(album_identifier):
    """Show detailed information about an album (by ID or name)."""
    config, db, llm_provider, album_manager = get_managers()

    # Try to parse as ID first
    album = None
    try:
        album_id = int(album_identifier)
        album = album_manager.get_album(album_id)
    except ValueError:
        # Not an ID, try name
        album = album_manager.get_album_by_name(album_identifier)

    if not album:
        click.echo(f"Album not found: {album_identifier}", err=True)
        raise click.Abort()

    click.echo("\n" + album_manager.format_album_display(album, detailed=True) + "\n")


@cli.command()
@click.argument('album_id', type=int)
@click.option('--rating', type=click.IntRange(1, 10), help='Update rating')
@click.option('--notes', help='Update personal notes')
@click.option('--genre', help='Update genre')
def update(album_id, rating, notes, genre):
    """Update album information."""
    config, db, llm_provider, album_manager = get_managers()

    album = album_manager.get_album(album_id)
    if not album:
        click.echo(f"Album not found: {album_id}", err=True)
        raise click.Abort()

    updates = {}

    if rating:
        updates['rating'] = rating
    if notes:
        updates['personal_notes'] = notes
    if genre:
        updates['genre'] = genre

    if not updates:
        click.echo("No updates specified.")
        return

    album_manager.update_album(album_id, updates)
    click.echo("✓ Album updated successfully")


@cli.command()
@click.argument('album_identifier')
@click.option('--force', is_flag=True, help='Re-fetch all fields, overwriting existing data')
def enrich(album_identifier, force):
    """Enrich an album with detailed metadata from LLM."""
    config, db, llm_provider, album_manager = get_managers()

    # Try to parse as ID first
    album = None
    try:
        album_id = int(album_identifier)
        album = album_manager.get_album(album_id)
    except ValueError:
        # Not an ID, try name
        album = album_manager.get_album_by_name(album_identifier)
        if album:
            album_id = album['id']

    if not album:
        click.echo(f"Album not found: {album_identifier}", err=True)
        raise click.Abort()

    try:
        if force:
            click.echo("Re-fetching all metadata fields...")
        else:
            click.echo("Fetching missing metadata fields...")

        updated_album = album_manager.enrich_album(album_id, force=force)
        click.echo("✓ Album enriched successfully\n")
        click.echo(album_manager.format_album_display(updated_album, detailed=True))

    except Exception as e:
        click.echo(f"Error enriching album: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['csv', 'json']), required=True, help='Export format')
@click.option('--output', required=True, help='Output file path')
def export(output_format, output):
    """Export all albums to CSV or JSON."""
    config, db, llm_provider, album_manager = get_managers()

    albums = album_manager.search_albums({})

    if not albums:
        click.echo("No albums to export.")
        return

    try:
        if output_format == 'json':
            with open(output, 'w') as f:
                json.dump(albums, f, indent=2)
        elif output_format == 'csv':
            with open(output, 'w', newline='') as f:
                # Get all possible fields
                fieldnames = ['id', 'album_name', 'artists', 'genre', 'rating', 'date_added',
                              'personal_notes', 'release_date', 'label', 'producer', 'total_duration',
                              'track_count', 'track_listing', 'album_review', 'musical_style',
                              'similar_artists', 'awards', 'llm_categories', 'user_categories',
                              'source_image_path', 'last_updated']

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for album in albums:
                    # Convert lists to comma-separated strings for CSV
                    row = album.copy()
                    for field in ['artists', 'track_listing', 'similar_artists', 'awards', 'llm_categories', 'user_categories']:
                        if isinstance(row.get(field), list):
                            row[field] = ', '.join(row[field])
                    writer.writerow(row)

        click.echo(f"✓ Exported {len(albums)} album(s) to {output}")

    except Exception as e:
        click.echo(f"Error exporting albums: {e}", err=True)
        raise click.Abort()


@cli.group()
def categories():
    """Manage predefined user categories."""
    pass


@categories.command(name='list')
def list_categories():
    """List all predefined user categories."""
    config = load_config()
    user_categories = config['settings'].get('user_categories', [])

    if not user_categories:
        click.echo("No user categories defined.")
        return

    click.echo("\nPredefined user categories:")
    for i, category in enumerate(user_categories, 1):
        click.echo(f"  {i}. {category}")
    click.echo()


@categories.command(name='add')
@click.argument('category')
def add_category(category):
    """Add a new predefined user category."""
    config = load_config()

    # Normalize category (lowercase, trim)
    category = category.lower().strip()

    if not category:
        click.echo("Category name cannot be empty.", err=True)
        raise click.Abort()

    user_categories = config['settings'].get('user_categories', [])

    if category in user_categories:
        click.echo(f"Category '{category}' already exists.")
        return

    user_categories.append(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Added category: {category}")


@categories.command(name='remove')
@click.argument('category')
def remove_category(category):
    """Remove a predefined user category."""
    config = load_config()

    category = category.lower().strip()
    user_categories = config['settings'].get('user_categories', [])

    if category not in user_categories:
        click.echo(f"Category '{category}' not found.")
        return

    user_categories.remove(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Removed category: {category}")


if __name__ == '__main__':
    cli()
