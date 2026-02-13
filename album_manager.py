import re
from typing import Dict, Any, List, Optional, Tuple
from database import Database
from llm_providers import LLMProvider


class AlbumManager:
    def __init__(self, db: Database, llm_provider: LLMProvider, config: Dict[str, Any]):
        self.db = db
        self.llm_provider = llm_provider
        self.config = config

    def normalize_string(self, s: str) -> str:
        """Normalize string for comparison (lowercase, remove punctuation, trim)."""
        s = s.lower().strip()
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'\s+', ' ', s)
        return s

    def find_duplicate(self, album_name: str, artists: List[str]) -> Optional[Dict[str, Any]]:
        """Check if album already exists using fuzzy matching."""
        normalized_name = self.normalize_string(album_name)
        normalized_artists = sorted([self.normalize_string(a) for a in artists])

        all_albums = self.db.search_albums({})

        for album in all_albums:
            album_name_norm = self.normalize_string(album['album_name'])
            album_artists = sorted([self.normalize_string(a) for a in album['artists']])

            if album_name_norm == normalized_name and album_artists == normalized_artists:
                return album

        return None

    def add_album(self, album_data: Dict[str, Any], source: str = 'manual', auto_enrich: bool = None) -> Tuple[int, str]:
        """
        Add a new album to the database.
        Returns (album_id, status) where status is 'added' or 'duplicate'.
        """
        # Check for duplicates
        duplicate = self.find_duplicate(album_data['album_name'], album_data['artists'])

        if duplicate:
            return duplicate['id'], 'duplicate'

        # Add the album
        album_id = self.db.add_album(album_data)

        # Auto-enrich if enabled
        should_enrich = auto_enrich if auto_enrich is not None else self.config['settings'].get('auto_enrich', True)

        if should_enrich:
            try:
                self.enrich_album(album_id, force=False)
            except Exception as e:
                print(f"Warning: Failed to enrich album: {e}")

        return album_id, 'added'

    def enrich_album(self, album_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Enrich an album with LLM metadata.
        If force=False, only fetch fields that are empty/null.
        If force=True, re-fetch all fields.
        """
        album = self.db.get_album(album_id)
        if not album:
            raise ValueError(f"Album with ID {album_id} not found")

        # Determine which fields need enrichment
        enrichable_fields = [
            'release_date', 'label', 'producer', 'total_duration',
            'track_count', 'track_listing', 'album_review', 'musical_style',
            'similar_artists', 'awards', 'llm_categories'
        ]

        if force:
            missing_fields = None  # Fetch all fields
        else:
            missing_fields = []
            for field in enrichable_fields:
                value = album.get(field)
                if value is None or value == '' or (isinstance(value, list) and len(value) == 0):
                    missing_fields.append(field)

            if not missing_fields:
                return album  # Nothing to enrich

        # Call LLM for enrichment
        print(f"Enriching album: {album['album_name']} by {', '.join(album['artists'])}")
        enriched_data = self.llm_provider.enrich_album_info(
            album['album_name'],
            album['artists'],
            missing_fields=missing_fields
        )

        # Update only the fields that were fetched
        updates = {}
        for field, value in enriched_data.items():
            if force or field in (missing_fields or enrichable_fields):
                updates[field] = value

        # Match against user categories if we have album_review or musical_style
        album_review = updates.get('album_review') or album.get('album_review')
        musical_style = updates.get('musical_style') or album.get('musical_style')
        genre = album.get('genre') or ''

        if (album_review or musical_style) and self.config['settings'].get('user_categories'):
            print("Matching user categories...")
            user_cats = self.llm_provider.match_user_categories(
                album['album_name'],
                album['artists'],
                album_review or '',
                genre,
                musical_style or '',
                self.config['settings']['user_categories']
            )
            updates['user_categories'] = user_cats

        # Update the database
        if updates:
            self.db.update_album(album_id, updates)

        # Return updated album
        return self.db.get_album(album_id)

    def update_album(self, album_id: int, updates: Dict[str, Any]):
        """Update an existing album."""
        self.db.update_album(album_id, updates)

    def get_album(self, album_id: int) -> Optional[Dict[str, Any]]:
        """Get an album by ID."""
        return self.db.get_album(album_id)

    def get_album_by_name(self, album_name: str) -> Optional[Dict[str, Any]]:
        """Get an album by name."""
        return self.db.get_album_by_name(album_name)

    def search_albums(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search albums with filters."""
        return self.db.search_albums(filters)

    def format_album_display(self, album: Dict[str, Any], detailed: bool = False) -> str:
        """Format album information for display."""
        output = []
        output.append(f"ID: {album['id']}")
        output.append(f"Album: {album['album_name']}")
        output.append(f"Artists: {', '.join(album['artists'])}")

        if album.get('genre'):
            output.append(f"Genre: {album['genre']}")

        if album.get('rating'):
            stars = '★' * album['rating'] + '☆' * (10 - album['rating'])
            output.append(f"Rating: {stars} ({album['rating']}/10)")

        if detailed:
            if album.get('release_date'):
                output.append(f"Release Date: {album['release_date']}")

            if album.get('label'):
                output.append(f"Label: {album['label']}")

            if album.get('producer'):
                output.append(f"Producer: {album['producer']}")

            if album.get('total_duration'):
                output.append(f"Duration: {album['total_duration']}")

            if album.get('track_count'):
                output.append(f"Track Count: {album['track_count']}")

            if album.get('track_listing') and len(album['track_listing']) > 0:
                output.append("Track Listing:")
                for i, track in enumerate(album['track_listing'], 1):
                    output.append(f"  {i}. {track}")

            if album.get('album_review'):
                output.append(f"Review: {album['album_review']}")

            if album.get('musical_style'):
                output.append(f"Musical Style: {album['musical_style']}")

            if album.get('similar_artists') and len(album['similar_artists']) > 0:
                output.append(f"Similar Artists: {', '.join(album['similar_artists'])}")

            if album.get('awards') and len(album['awards']) > 0:
                output.append(f"Awards: {', '.join(album['awards'])}")

            if album.get('llm_categories') and len(album['llm_categories']) > 0:
                output.append(f"Categories: {', '.join(album['llm_categories'])}")

            if album.get('user_categories') and len(album['user_categories']) > 0:
                output.append(f"User Categories: {', '.join(album['user_categories'])}")

            if album.get('personal_notes'):
                output.append(f"Notes: {album['personal_notes']}")

            if album.get('source_image_path'):
                output.append(f"Source Image: {album['source_image_path']}")

            output.append(f"Date Added: {album['date_added']}")

        return "\n".join(output)
