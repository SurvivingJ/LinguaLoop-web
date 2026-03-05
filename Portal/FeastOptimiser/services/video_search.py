"""YouTube Data API v3 integration for technique and recipe videos."""

import re
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)

PREFERRED_CHANNELS = [
    'Chinese Cooking Demystified',
    'Serious Eats',
    'J. Kenji López-Alt',
    'RecipeTin Eats',
    'Ethan Chlebowski',
    'Adam Ragusea',
    'Internet Shaquille',
    'Joshua Weissman',
    'Babish Culinary Universe',
]

YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3'


def search_technique_video(technique, duration='short'):
    """Search YouTube for technique tutorial videos.

    Args:
        technique: technique name (e.g., "stir_frying")
        duration: YouTube duration filter ("short", "medium", "long")
    Returns:
        list of video dicts
    """
    if not Config.YOUTUBE_API_KEY:
        return []

    query = f"{technique.replace('_', ' ')} cooking technique tutorial"
    return _search_youtube(query, duration=duration, max_results=5)


def search_recipe_video(recipe_name, cuisine=None):
    """Search for a full recipe walkthrough video.

    Returns:
        dict with video info, or None
    """
    if not Config.YOUTUBE_API_KEY:
        return None

    query = recipe_name
    if cuisine:
        query = f"{recipe_name} {cuisine} recipe"

    results = _search_youtube(query, duration='medium', max_results=5)
    return results[0] if results else None


def extract_timestamps(video_id):
    """Fetch video description and parse timestamp patterns.

    Returns:
        dict mapping step index to {time, seconds, description}
    """
    if not Config.YOUTUBE_API_KEY:
        return {}

    try:
        resp = requests.get(f'{YOUTUBE_API_BASE}/videos', params={
            'part': 'snippet',
            'id': video_id,
            'key': Config.YOUTUBE_API_KEY,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get('items', [])
        if not items:
            return {}

        description = items[0].get('snippet', {}).get('description', '')
        return _parse_timestamps(description)
    except Exception as e:
        logger.warning(f"Failed to get timestamps for {video_id}: {e}")
        return {}


def _search_youtube(query, duration='medium', max_results=5):
    """Execute YouTube search and return sorted results."""
    try:
        resp = requests.get(f'{YOUTUBE_API_BASE}/search', params={
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'videoDuration': duration,
            'maxResults': max_results,
            'key': Config.YOUTUBE_API_KEY,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get('items', []):
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId', '')
            channel = snippet.get('channelTitle', '')

            results.append({
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'channel': channel,
                'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'embed_url': f'https://www.youtube.com/embed/{video_id}',
                'watch_url': f'https://www.youtube.com/watch?v={video_id}',
                '_preferred': channel in PREFERRED_CHANNELS,
            })

        # Sort: preferred channels first, then by original order
        results.sort(key=lambda r: (not r['_preferred'],))
        return results
    except Exception as e:
        logger.warning(f"YouTube search failed for '{query}': {e}")
        return []


def _parse_timestamps(description):
    """Parse timestamp patterns from video description.

    Matches patterns like:
        1:23 - Prep vegetables
        01:23:45 Searing the meat
        0:30 Making the sauce
    """
    timestamps = {}
    pattern = re.compile(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-–]?\s*(.+)')

    step = 0
    for line in description.split('\n'):
        match = pattern.match(line.strip())
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            desc = match.group(4).strip()

            time_str = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

            timestamps[step] = {
                'time': time_str,
                'seconds': total_seconds,
                'description': desc,
            }
            step += 1

    return timestamps
