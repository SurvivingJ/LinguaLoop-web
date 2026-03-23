import json
import os
import tempfile
import threading

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
BOOKS_FILE = os.path.join(DATA_DIR, "books.json")
VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")

_lock = threading.Lock()


def init_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    for filepath in (BOOKS_FILE, VIDEOS_FILE):
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                json.dump([], f)


def _load(filepath):
    with _lock:
        with open(filepath, "r") as f:
            return json.load(f)


def _save(filepath, data):
    with _lock:
        fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, filepath)
        except Exception:
            os.unlink(tmp_path)
            raise


def load_books():
    return _load(BOOKS_FILE)


def save_books(books):
    _save(BOOKS_FILE, books)


def load_videos():
    return _load(VIDEOS_FILE)


def save_videos(videos):
    _save(VIDEOS_FILE, videos)


init_storage()
