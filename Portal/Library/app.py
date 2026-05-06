from datetime import datetime, timezone
import uuid

from flask import Flask, render_template, request, jsonify, Response
import os
import requests as http_requests

import storage

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "healthy"}


# ── Books API ────────────────────────────────────────────────────────

@app.route("/api/books", methods=["GET"])
def get_books():
    return jsonify(storage.load_books())


@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json(silent=True)
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    books = storage.load_books()

    isbn = data.get("isbn")
    if isbn and any(b.get("isbn") == isbn for b in books):
        return jsonify({"error": "Book with this ISBN already exists"}), 409

    if "added_at" not in data:
        data["added_at"] = datetime.now(timezone.utc).isoformat()

    books.append(data)
    storage.save_books(books)
    return jsonify(data), 201


@app.route("/api/books/<isbn>/color", methods=["PATCH"])
def update_book_color(isbn):
    data = request.get_json(silent=True)
    color = data.get("spine_color", "") if data else ""
    if not color:
        return jsonify({"error": "spine_color is required"}), 400
    books = storage.load_books()
    for book in books:
        if book.get("isbn") == isbn:
            book["spine_color"] = color
            storage.save_books(books)
            return jsonify({"isbn": isbn, "spine_color": color})
    return jsonify({"error": "Book not found"}), 404


@app.route("/api/books/<isbn>/cover", methods=["PATCH"])
def update_book_cover(isbn):
    data = request.get_json(silent=True)
    cover_url = data.get("cover_url", "") if data else ""
    if not cover_url:
        return jsonify({"error": "cover_url is required"}), 400
    books = storage.load_books()
    for book in books:
        if book.get("isbn") == isbn:
            book["cover_url"] = cover_url
            # Reset spine color so it gets re-extracted from the new cover
            if "spine_color" in book:
                del book["spine_color"]
            storage.save_books(books)
            return jsonify({"isbn": isbn, "cover_url": cover_url})
    return jsonify({"error": "Book not found"}), 404


# ── Cover image search ──────────────────────────────────────────────

def _google_books_covers(title, author, limit=20):
    """Search Google Books by title+author and return cover URLs."""
    parts = []
    if title:
        parts.append(f'intitle:"{title}"')
    if author:
        parts.append(f'inauthor:"{author}"')
    if not parts:
        return []
    q = "+".join(parts)
    url = (
        "https://www.googleapis.com/books/v1/volumes"
        f"?q={q}&maxResults={min(limit, 40)}&printType=books"
    )
    try:
        r = http_requests.get(url, timeout=8)
        r.raise_for_status()
        items = (r.json() or {}).get("items") or []
    except Exception:
        return []

    covers = []
    for it in items:
        v = it.get("volumeInfo", {}) or {}
        links = v.get("imageLinks") or {}
        # Prefer larger images when available
        thumb = (
            links.get("extraLarge")
            or links.get("large")
            or links.get("medium")
            or links.get("thumbnail")
            or links.get("smallThumbnail")
            or ""
        )
        if not thumb:
            continue
        thumb = thumb.replace("http:", "https:").replace("&edge=curl", "")
        covers.append({
            "url": thumb,
            "title": v.get("title", ""),
            "author": ", ".join(v.get("authors") or []),
            "source": "google",
        })
    return covers


def _openlibrary_covers(title, author, limit=20):
    """Search Open Library by title+author and return cover URLs."""
    if not (title or author):
        return []
    params = []
    if title:
        params.append(f"title={http_requests.utils.quote(title)}")
    if author:
        params.append(f"author={http_requests.utils.quote(author)}")
    params.append(f"limit={min(limit, 40)}")
    url = "https://openlibrary.org/search.json?" + "&".join(params)
    try:
        r = http_requests.get(url, timeout=8)
        r.raise_for_status()
        docs = (r.json() or {}).get("docs") or []
    except Exception:
        return []

    covers = []
    for d in docs:
        cover_id = d.get("cover_i")
        if not cover_id:
            continue
        covers.append({
            "url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
            "title": d.get("title", ""),
            "author": ", ".join(d.get("author_name") or []),
            "source": "openlibrary",
        })
    return covers


@app.route("/api/cover-search")
def cover_search():
    title = (request.args.get("title") or "").strip()
    author = (request.args.get("author") or "").strip()
    limit = int(request.args.get("limit") or 10)
    if not title and not author:
        return jsonify({"error": "title or author is required"}), 400

    g_covers = _google_books_covers(title, author, limit=limit * 2)
    ol_covers = _openlibrary_covers(title, author, limit=limit * 2)

    # Interleave so the user sees diversity from both sources at the top
    merged = []
    for pair in zip(g_covers, ol_covers):
        merged.extend(pair)
    merged.extend(g_covers[len(ol_covers):])
    merged.extend(ol_covers[len(g_covers):])

    seen = set()
    out = []
    for c in merged:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        out.append(c)
        if len(out) >= limit:
            break

    return jsonify({"covers": out})


@app.route("/api/books/<isbn>", methods=["DELETE"])
def delete_book(isbn):
    books = storage.load_books()
    updated = [b for b in books if b.get("isbn") != isbn]
    if len(updated) == len(books):
        return jsonify({"error": "Book not found"}), 404
    storage.save_books(updated)
    return jsonify({"deleted": isbn})


@app.route("/api/books/export")
def export_books():
    resp = jsonify(storage.load_books())
    resp.headers["Content-Disposition"] = "attachment; filename=books.json"
    return resp


# ── Image Proxy (for CORS-safe color extraction) ────────────────────

@app.route("/api/proxy-image")
def proxy_image():
    url = request.args.get("url", "")
    if not url or not url.startswith("https://"):
        return jsonify({"error": "Invalid URL"}), 400
    try:
        resp = http_requests.get(url, timeout=10, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(resp.content, content_type=content_type)
    except Exception:
        return jsonify({"error": "Failed to fetch image"}), 502


# ── Videos API ───────────────────────────────────────────────────────

@app.route("/api/videos", methods=["GET"])
def get_videos():
    return jsonify(storage.load_videos())


@app.route("/api/videos/sync", methods=["POST"])
def sync_videos():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array"}), 400

    storage.save_videos(data)
    return jsonify({"synced": len(data)})


# ── Watched API ──────────────────────────────────────────────────────

@app.route("/api/watched", methods=["GET"])
def get_watched():
    return jsonify(storage.load_watched())


@app.route("/api/watched", methods=["POST"])
def add_watched():
    data = request.get_json(silent=True)
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    watched = storage.load_watched()

    if "added_at" not in data:
        data["added_at"] = datetime.now(timezone.utc).isoformat()
    if "id" not in data:
        data["id"] = str(uuid.uuid4())

    watched.append(data)
    storage.save_watched(watched)
    return jsonify(data), 201


@app.route("/api/watched/<item_id>", methods=["DELETE"])
def delete_watched(item_id):
    watched = storage.load_watched()
    updated = [w for w in watched if w.get("id") != item_id]
    if len(updated) == len(watched):
        return jsonify({"error": "Item not found"}), 404
    storage.save_watched(updated)
    return jsonify({"deleted": item_id})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
