import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    def __init__(self, db_path: str = "albums.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database with schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create albums table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                album_name TEXT NOT NULL,
                artists TEXT NOT NULL,
                genre TEXT,
                date_added TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 10),
                personal_notes TEXT,

                release_date TEXT,
                label TEXT,
                producer TEXT,
                total_duration TEXT,
                track_count INTEGER,
                track_listing TEXT,
                album_review TEXT,
                musical_style TEXT,
                similar_artists TEXT,
                awards TEXT,
                llm_categories TEXT,
                user_categories TEXT,

                source_image_path TEXT,
                last_updated TEXT NOT NULL,

                UNIQUE(album_name, artists)
            )
        """)

        # Create processed_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT UNIQUE NOT NULL,
                processed_date TEXT NOT NULL,
                albums_extracted INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def add_album(self, album_data: Dict[str, Any]) -> int:
        """Add a new album to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        album_data['date_added'] = now
        album_data['last_updated'] = now

        # Convert lists to JSON strings
        for field in ['artists', 'track_listing', 'similar_artists', 'awards', 'llm_categories', 'user_categories']:
            if field in album_data and isinstance(album_data[field], list):
                album_data[field] = json.dumps(album_data[field])

        columns = ', '.join(album_data.keys())
        placeholders = ', '.join(['?' for _ in album_data])

        cursor.execute(
            f"INSERT INTO albums ({columns}) VALUES ({placeholders})",
            list(album_data.values())
        )

        album_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return album_id

    def update_album(self, album_id: int, updates: Dict[str, Any]):
        """Update an existing album."""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates['last_updated'] = datetime.now().isoformat()

        # Convert lists to JSON strings
        for field in ['artists', 'track_listing', 'similar_artists', 'awards', 'llm_categories', 'user_categories']:
            if field in updates and isinstance(updates[field], list):
                updates[field] = json.dumps(updates[field])

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])

        cursor.execute(
            f"UPDATE albums SET {set_clause} WHERE id = ?",
            list(updates.values()) + [album_id]
        )

        conn.commit()
        conn.close()

    def get_album(self, album_id: int) -> Optional[Dict[str, Any]]:
        """Get an album by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM albums WHERE id = ?", (album_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def get_album_by_name(self, album_name: str) -> Optional[Dict[str, Any]]:
        """Get an album by name (exact match)."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM albums WHERE album_name = ?", (album_name,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def search_albums(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search albums with various filters."""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM albums WHERE 1=1"
        params = []

        if 'name' in filters:
            query += " AND album_name LIKE ?"
            params.append(f"%{filters['name']}%")

        if 'artist' in filters:
            query += " AND artists LIKE ?"
            params.append(f"%{filters['artist']}%")

        if 'genre' in filters:
            query += " AND genre LIKE ?"
            params.append(f"%{filters['genre']}%")

        if 'rating_min' in filters:
            query += " AND rating >= ?"
            params.append(filters['rating_min'])

        if 'rating_max' in filters:
            query += " AND rating <= ?"
            params.append(filters['rating_max'])

        if 'category' in filters:
            query += " AND (llm_categories LIKE ? OR user_categories LIKE ?)"
            params.append(f"%{filters['category']}%")
            params.append(f"%{filters['category']}%")

        if 'sort_by' in filters:
            sort_field = filters['sort_by']
            # Map user-friendly names to database columns
            sort_mapping = {
                'name': 'album_name',
                'artist': 'artists',
                'rating': 'rating',
                'date_added': 'date_added'
            }
            db_field = sort_mapping.get(sort_field, sort_field)
            query += f" ORDER BY {db_field}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def list_albums(self, sort_by: str = 'date_added') -> List[Dict[str, Any]]:
        """List all albums with optional sorting."""
        return self.search_albums({'sort_by': sort_by})

    def mark_image_processed(self, image_path: str, albums_extracted: int):
        """Mark an image as processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO processed_images (image_path, processed_date, albums_extracted) VALUES (?, ?, ?)",
            (image_path, datetime.now().isoformat(), albums_extracted)
        )

        conn.commit()
        conn.close()

    def is_image_processed(self, image_path: str) -> bool:
        """Check if an image has been processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM processed_images WHERE image_path = ?", (image_path,))
        result = cursor.fetchone()

        conn.close()

        return result is not None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary with JSON fields parsed."""
        album = dict(row)

        # Parse JSON fields
        for field in ['artists', 'track_listing', 'similar_artists', 'awards', 'llm_categories', 'user_categories']:
            if album.get(field):
                try:
                    album[field] = json.loads(album[field])
                except json.JSONDecodeError:
                    album[field] = []

        return album
