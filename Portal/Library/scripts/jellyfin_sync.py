#!/usr/bin/env python3
"""Sync Jellyfin library to the Library cloud app.

Optional env vars:
    JELLYFIN_HOST      - Jellyfin URL (default: http://localhost:8096)
    LIBRARY_URL        - Library app URL (default: https://library.linguadojo.com)
"""

import base64
import io
import os
import sys

import requests
from PIL import Image

JELLYFIN_HOST = os.environ.get("JELLYFIN_HOST", "http://localhost:8096")
JELLYFIN_API_KEY = "e560ff1b5dbf47f18694a0f8cd59f4ab"
JELLYFIN_USER_ID = "7a95b519700540bf82c201d8aa50abe1"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "https://library.linguadojo.com")


def fetch_jellyfin_library():
    """Fetch all movies and series from Jellyfin."""
    url = (
        f"{JELLYFIN_HOST}/Users/{JELLYFIN_USER_ID}/Items"
        f"?api_key={JELLYFIN_API_KEY}"
        f"&IncludeItemTypes=Movie,Series"
        f"&Recursive=true"
        f"&Fields=ProductionYear,Overview"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("Items", [])
    print(f"Fetched {len(items)} items from Jellyfin")
    return items


def get_cover_base64(item_id):
    """Download a Jellyfin cover image and return as a base64 data URI."""
    url = (
        f"{JELLYFIN_HOST}/Items/{item_id}/Images/Primary"
        f"?maxWidth=200&quality=80&api_key={JELLYFIN_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()

        img = Image.open(io.BytesIO(resp.content))
        img.thumbnail((200, 300))

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=70)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return ""


def format_video_data(raw_items):
    """Extract and clean video data from Jellyfin items."""
    total = len(raw_items)
    clean = []
    for i, item in enumerate(raw_items, 1):
        title = item.get("Name", "Unknown")
        print(f"Processing {i}/{total}: {title}")
        clean.append({
            "title": title,
            "year": item.get("ProductionYear"),
            "jellyfin_id": item.get("Id", ""),
            "type": item.get("Type", ""),
            "cover_base64": get_cover_base64(item.get("Id", "")),
        })
    return clean


def push_to_cloud(clean_data):
    """Push the formatted video list to the Library cloud app."""
    resp = requests.post(
        f"{LIBRARY_URL}/api/videos/sync",
        json=clean_data,
        headers={
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    if resp.ok:
        result = resp.json()
        print(f"Synced {result.get('synced', '?')} videos to cloud")
    else:
        print(f"Sync failed: {resp.status_code} — {resp.text}")
        sys.exit(1)


def main():
    raw = fetch_jellyfin_library()
    clean = format_video_data(raw)
    push_to_cloud(clean)
    print("Done!")


if __name__ == "__main__":
    main()
