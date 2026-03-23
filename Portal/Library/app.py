from datetime import datetime, timezone

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


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
