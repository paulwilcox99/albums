import base64
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def extract_albums_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract album information from an image."""
        pass

    @abstractmethod
    def enrich_album_info(self, album_name: str, artists: List[str], missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich album information with detailed metadata."""
        pass

    @abstractmethod
    def match_user_categories(self, album_name: str, artists: List[str], album_review: str, genre: str, musical_style: str, predefined_categories: List[str]) -> List[str]:
        """Match album against predefined user categories."""
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_albums_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract album information from an image using GPT-4 Vision."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        prompt = """Analyze this image of album covers. Extract the album name and artist(s) for each album visible.
Return ONLY a JSON array in this exact format, with no additional text:
[{"album_name": "Album Name", "artists": ["Artist Name"]}, ...]

If you cannot clearly read an album's information, skip it."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting albums from image: {e}")
            return []

    def enrich_album_info(self, album_name: str, artists: List[str], missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich album information with detailed metadata."""
        artists_str = ", ".join(artists)

        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- release_date (YYYY or YYYY-MM-DD format)
- label (record label)
- producer (producer name(s))
- total_duration (MM:SS format)
- track_count (number of tracks)
- track_listing (list of track names in order)
- album_review (2-3 sentence critical reception summary)
- musical_style (detailed style description with influences)
- similar_artists (list of similar artists)
- awards (list of major awards won)
- categories (list of categories like "concept album", "live recording", "debut album", etc.)"""

        prompt = f"""Provide detailed information about the album "{album_name}" by {artists_str}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "release_date": "YYYY or YYYY-MM-DD",
    "label": "record label",
    "producer": "producer name(s)",
    "total_duration": "MM:SS",
    "track_count": 12,
    "track_listing": ["track1", "track2", ...],
    "album_review": "2-3 sentence critical reception summary",
    "musical_style": "detailed style description with influences",
    "similar_artists": ["artist1", "artist2"],
    "awards": ["award1", "award2"],
    "categories": ["concept album", "live recording", etc.]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching album info: {e}")
            return {}

    def match_user_categories(self, album_name: str, artists: List[str], album_review: str, genre: str, musical_style: str, predefined_categories: List[str]) -> List[str]:
        """Match album against predefined user categories."""
        artists_str = ", ".join(artists)
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this album:
Album: {album_name}
Artists: {artists_str}
Review: {album_review}
Genre: {genre}
Style: {musical_style}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def extract_albums_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract album information from an image using Claude Vision."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Detect image type
        suffix = Path(image_path).suffix.lower()
        media_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"

        prompt = """Analyze this image of album covers. Extract the album name and artist(s) for each album visible.
Return ONLY a JSON array in this exact format, with no additional text:
[{"album_name": "Album Name", "artists": ["Artist Name"]}, ...]

If you cannot clearly read an album's information, skip it."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting albums from image: {e}")
            return []

    def enrich_album_info(self, album_name: str, artists: List[str], missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich album information with detailed metadata."""
        artists_str = ", ".join(artists)

        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- release_date (YYYY or YYYY-MM-DD format)
- label (record label)
- producer (producer name(s))
- total_duration (MM:SS format)
- track_count (number of tracks)
- track_listing (list of track names in order)
- album_review (2-3 sentence critical reception summary)
- musical_style (detailed style description with influences)
- similar_artists (list of similar artists)
- awards (list of major awards won)
- categories (list of categories like "concept album", "live recording", "debut album", etc.)"""

        prompt = f"""Provide detailed information about the album "{album_name}" by {artists_str}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "release_date": "YYYY or YYYY-MM-DD",
    "label": "record label",
    "producer": "producer name(s)",
    "total_duration": "MM:SS",
    "track_count": 12,
    "track_listing": ["track1", "track2", ...],
    "album_review": "2-3 sentence critical reception summary",
    "musical_style": "detailed style description with influences",
    "similar_artists": ["artist1", "artist2"],
    "awards": ["award1", "award2"],
    "categories": ["concept album", "live recording", etc.]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching album info: {e}")
            return {}

    def match_user_categories(self, album_name: str, artists: List[str], album_review: str, genre: str, musical_style: str, predefined_categories: List[str]) -> List[str]:
        """Match album against predefined user categories."""
        artists_str = ", ".join(artists)
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this album:
Album: {album_name}
Artists: {artists_str}
Review: {album_review}
Genre: {genre}
Style: {musical_style}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


class GoogleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def extract_albums_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract album information from an image using Gemini Vision."""
        from PIL import Image

        prompt = """Analyze this image of album covers. Extract the album name and artist(s) for each album visible.
Return ONLY a JSON array in this exact format, with no additional text:
[{"album_name": "Album Name", "artists": ["Artist Name"]}, ...]

If you cannot clearly read an album's information, skip it."""

        try:
            image = Image.open(image_path)
            response = self.model.generate_content([prompt, image])

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting albums from image: {e}")
            return []

    def enrich_album_info(self, album_name: str, artists: List[str], missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich album information with detailed metadata."""
        artists_str = ", ".join(artists)

        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- release_date (YYYY or YYYY-MM-DD format)
- label (record label)
- producer (producer name(s))
- total_duration (MM:SS format)
- track_count (number of tracks)
- track_listing (list of track names in order)
- album_review (2-3 sentence critical reception summary)
- musical_style (detailed style description with influences)
- similar_artists (list of similar artists)
- awards (list of major awards won)
- categories (list of categories like "concept album", "live recording", "debut album", etc.)"""

        prompt = f"""Provide detailed information about the album "{album_name}" by {artists_str}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "release_date": "YYYY or YYYY-MM-DD",
    "label": "record label",
    "producer": "producer name(s)",
    "total_duration": "MM:SS",
    "track_count": 12,
    "track_listing": ["track1", "track2", ...],
    "album_review": "2-3 sentence critical reception summary",
    "musical_style": "detailed style description with influences",
    "similar_artists": ["artist1", "artist2"],
    "awards": ["award1", "award2"],
    "categories": ["concept album", "live recording", etc.]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.model.generate_content(prompt)

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching album info: {e}")
            return {}

    def match_user_categories(self, album_name: str, artists: List[str], album_review: str, genre: str, musical_style: str, predefined_categories: List[str]) -> List[str]:
        """Match album against predefined user categories."""
        artists_str = ", ".join(artists)
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this album:
Album: {album_name}
Artists: {artists_str}
Review: {album_review}
Genre: {genre}
Style: {musical_style}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.model.generate_content(prompt)

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


def get_provider(config: Dict[str, Any]) -> LLMProvider:
    """Factory function to get the appropriate LLM provider."""
    provider_name = config['llm']['provider']

    if provider_name == 'openai':
        return OpenAIProvider(
            api_key=config['llm']['openai_api_key'],
            model=config['llm']['model']['openai']
        )
    elif provider_name == 'anthropic':
        return AnthropicProvider(
            api_key=config['llm']['anthropic_api_key'],
            model=config['llm']['model']['anthropic']
        )
    elif provider_name == 'google':
        return GoogleProvider(
            api_key=config['llm']['google_api_key'],
            model=config['llm']['model']['google']
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
