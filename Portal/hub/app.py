from flask import Flask, render_template

app = Flask(__name__)

PROJECTS = [
    {
        "name": "LinguaDojo",
        "description": "AI-powered language learning with adaptive tests",
        "url": "https://linguadojo.com",
        "icon": "fa-language",
        "tags": ["Language", "AI", "Education"],
    },
    {
        "name": "MathDojo",
        "description": "Retro arcade mental arithmetic trainer",
        "url": "https://math.linguadojo.com",
        "icon": "fa-calculator",
        "tags": ["Math", "Games", "Practice"],
    },
    {
        "name": "MusicDojo",
        "description": "Master rhythm, timing, and guitar technique with 52 exercises",
        "url": "https://music.linguadojo.com",
        "icon": "fa-guitar",
        "tags": ["Music", "Guitar", "Practice"],
    },
]


@app.route("/")
def index():
    return render_template("index.html", projects=PROJECTS)


@app.route("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
