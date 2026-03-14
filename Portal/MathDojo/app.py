from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from math_engine import ProblemGenerator, FinancialProblemGenerator
from poker_engine import PokerProblemGenerator
import profile_store
import prediction_engine

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "https://math.linguadojo.com",
    "http://localhost:5000",
    "http://localhost:3000",
]}})

# Initialize problem generator
generator = ProblemGenerator()


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/api/problem', methods=['GET'])
def get_problem():
    """
    Get a single math problem.

    Query params:
        elo (int): User's current Elo rating (default: 1000)
        mode (str): Game mode (optional, for future use)

    Returns:
        JSON: { "id": str, "equation": str, "answer": int, "difficulty_rating": int }
    """
    try:
        elo = int(request.args.get('elo', 1000))
        mode = request.args.get('mode', 'standard')

        # Convert Elo to difficulty
        difficulty = generator.elo_to_difficulty(elo)

        # Generate problem
        problem = generator.get_problem(difficulty)

        return jsonify(problem)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/batch', methods=['POST'])
def get_batch():
    """
    Get a batch of math problems.

    Request body (JSON):
        count (int): Number of problems to generate
        elo (int): User's current Elo rating

    Returns:
        JSON: { "problems": [...] }
    """
    try:
        data = request.get_json()
        count = data.get('count', 50)
        options = data.get('options', None)
        difficulty = data.get('difficulty', None)

        financial = data.get('financial_options', None)

        poker = data.get('poker_options', None)

        if financial is not None:
            # Financial drill mode
            focus_tags = data.get('focus_tags', None)
            problems = FinancialProblemGenerator.generate_batch(count, financial, focus_tags=focus_tags)
        elif poker is not None:
            # Poker math drill mode
            focus_tags = data.get('focus_tags', None)
            problems = PokerProblemGenerator.generate_batch(count, poker, focus_tags=focus_tags)
        elif options is not None:
            # Custom drill mode (user-configured operations/digits)
            focus_tags = data.get('focus_tags', None)
            problems = generator.get_batch_custom(count, options, focus_tags=focus_tags)
        elif difficulty is not None:
            # Direct difficulty mode
            problems = generator.get_batch_by_difficulty(count, int(difficulty))
        else:
            # Elo mode (used by Time Trial, Space Defense)
            elo = data.get('elo', 1000)
            problems = generator.get_batch(count, elo)

        return jsonify({'problems': problems})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/profile/<name>/stats', methods=['GET'])
def get_profile_stats(name):
    """Get stats summary for a profile."""
    try:
        summary = profile_store.get_stats_summary(name)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/profile/<name>/record', methods=['POST'])
def record_profile_results(name):
    """
    Record problem results for a profile.

    Request body (JSON):
        results: [{tags: [...], correct: bool, time_ms: int}, ...]
        session: {mode, duration_s, problems_attempted, correct} (optional)
    """
    try:
        data = request.get_json()
        results = data.get('results', [])
        session_info = data.get('session', None)
        profile_store.record_results(name, results, session_info)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/profile/<name>/focus-tags', methods=['GET'])
def get_focus_tags(name):
    """
    Get prediction engine focus tags for a profile.

    Query params:
        mode (str): Game mode filter (optional)
    """
    try:
        mode = request.args.get('mode', None)
        profile_data = profile_store.load_profile(name)
        tag_stats = profile_data.get('tag_stats', {})
        result = prediction_engine.get_focus_tags(tag_stats, mode=mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
