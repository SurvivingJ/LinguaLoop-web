import os
from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from music_engine import (
    DirectionExerciseGenerator,
    PolyrhythmGenerator,
    SwingExerciseGenerator,
    TempoRampGenerator,
    ScalePatternGenerator,
    GhostMetronomeGenerator,
    EarTrainingGenerator,
    RhythmDictationGenerator
)
from guitar_exercise_engine import guitar_generator
from sight_reading_engine import SightReadingGenerator
import guitar100k_service

app = Flask(__name__)

# Initialize Guitar 100K data files on startup
guitar100k_service.init_files()
CORS(app, resources={r"/api/*": {"origins": [
    "https://music.linguadojo.com",
    "http://localhost:5000",
    "http://localhost:3000",
]}})

# Initialize generators
direction_gen = DirectionExerciseGenerator()
polyrhythm_gen = PolyrhythmGenerator()
swing_gen = SwingExerciseGenerator()
tempo_ramp_gen = TempoRampGenerator()
scale_pattern_gen = ScalePatternGenerator()
ghost_gen = GhostMetronomeGenerator()
ear_training_gen = EarTrainingGenerator()
rhythm_dictation_gen = RhythmDictationGenerator()
sight_reading_gen = SightReadingGenerator()


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/api/exercise', methods=['GET'])
def get_exercise():
    """
    Get a single music exercise.

    Query params:
        mode (str): Exercise mode (direction, polyrhythm, swing, etc.)
        elo (int): User's current Elo rating (default: 1000)

    Returns:
        JSON: Exercise data specific to mode
    """
    try:
        mode = request.args.get('mode', 'direction')
        elo = int(request.args.get('elo', 1000))

        # Convert Elo to difficulty
        difficulty = elo_to_difficulty(elo)

        # Generate exercise based on mode
        if mode == 'direction':
            exercise = direction_gen.generate(difficulty)
        elif mode == 'polyrhythm':
            exercise = polyrhythm_gen.generate(difficulty)
        elif mode == 'swing':
            exercise = swing_gen.generate(difficulty)
        elif mode == 'tempo_ramp':
            exercise = tempo_ramp_gen.generate(difficulty)
        elif mode == 'improv':
            exercise = scale_pattern_gen.generate(difficulty)
        elif mode == 'ghost':
            exercise = ghost_gen.generate(difficulty)
        elif mode == 'ear_training':
            exercise = ear_training_gen.generate(difficulty)
        elif mode == 'rhythm_dictation':
            exercise = rhythm_dictation_gen.generate(difficulty)
        elif mode == 'sight_reading':
            exercise = sight_reading_gen.generate(difficulty, request.args.to_dict())
        else:
            return jsonify({'error': f'Unknown mode: {mode}'}), 400

        return jsonify(exercise)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/batch', methods=['POST'])
def get_batch():
    """
    Get a batch of music exercises.

    Request body (JSON):
        mode (str): Exercise mode
        count (int): Number of exercises to generate
        elo (int): User's current Elo rating
        options (dict): Optional mode-specific configuration

    Returns:
        JSON: { "exercises": [...] }
    """
    try:
        data = request.get_json()
        mode = data.get('mode', 'direction')
        count = data.get('count', 10)
        elo = data.get('elo', 1000)
        options = data.get('options', {})

        difficulty = elo_to_difficulty(elo)
        exercises = []

        # Generate batch based on mode
        if mode == 'direction':
            exercises = direction_gen.generate_batch(count, difficulty, options)
        elif mode == 'polyrhythm':
            exercises = polyrhythm_gen.generate_batch(count, difficulty, options)
        elif mode == 'swing':
            exercises = swing_gen.generate_batch(count, difficulty, options)
        elif mode == 'tempo_ramp':
            exercises = tempo_ramp_gen.generate_batch(count, difficulty, options)
        elif mode == 'improv':
            exercises = scale_pattern_gen.generate_batch(count, difficulty, options)
        elif mode == 'ghost':
            exercises = ghost_gen.generate_batch(count, difficulty, options)
        elif mode == 'ear_training':
            exercises = ear_training_gen.generate_batch(count, difficulty, options)
        elif mode == 'rhythm_dictation':
            exercises = rhythm_dictation_gen.generate_batch(count, difficulty, options)
        elif mode == 'sight_reading':
            exercises = sight_reading_gen.generate_batch(count, difficulty, options)
        else:
            return jsonify({'error': f'Unknown mode: {mode}'}), 400

        return jsonify({'exercises': exercises})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/scale-info', methods=['GET'])
def get_scale_info():
    """
    Get information about a musical scale.

    Query params:
        key (str): Root key (C, D, etc.)
        scale_type (str): Scale type (Major, Minor, etc.)

    Returns:
        JSON: Scale information including notes, intervals, etc.
    """
    try:
        key = request.args.get('key', 'C')
        scale_type = request.args.get('scale_type', 'Major')

        info = scale_pattern_gen.get_scale_info(key, scale_type)
        return jsonify(info)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/sight-reading/generate', methods=['POST'])
def generate_sight_reading():
    """
    Generate a sight reading exercise with instrument-specific options.

    Request body (JSON):
        instrument (str): 'guitar' or 'piano'
        elo (int): User's current Elo rating (default: 1000)
        scales (list): Scale names or ['random']
        tempo (int|null): Specific BPM or null for random
        note_types (list): Duration codes or ['random']
        measures (int): Number of measures (default: 4)

    Returns:
        JSON: Sight reading exercise data
    """
    try:
        data = request.get_json()
        elo = data.get('elo', 1000)
        difficulty = elo_to_difficulty(elo)

        options = {
            'instrument': data.get('instrument', 'piano'),
            'scales': data.get('scales', ['random']),
            'tempo': data.get('tempo', None),
            'note_types': data.get('note_types', ['random']),
            'measures': data.get('measures', 4),
        }

        exercise = sight_reading_gen.generate(difficulty, options)
        return jsonify(exercise)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/sight-reading/scales', methods=['GET'])
def get_available_scales():
    """
    Get scales available at a given difficulty level.

    Query params:
        elo (int): User's Elo rating (default: 1000)

    Returns:
        JSON: { "scales": [...] }
    """
    try:
        elo = int(request.args.get('elo', 1000))
        difficulty = elo_to_difficulty(elo)
        scales = sight_reading_gen.get_available_scales(difficulty)
        return jsonify({'scales': scales, 'difficulty': difficulty})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/guitar/exercises', methods=['GET'])
def get_guitar_exercises():
    """
    Get all guitar exercises or filter by category.

    Query params:
        category (str, optional): Filter by category (chromatic, scales, etc.)

    Returns:
        JSON: { "exercises": [...] }
    """
    try:
        category = request.args.get('category', None)

        if category:
            exercises = guitar_generator.get_exercises_by_category(category)
        else:
            exercises = guitar_generator.get_all_exercises()

        return jsonify({'exercises': exercises})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/guitar/exercises/<exercise_id>', methods=['GET'])
def get_guitar_exercise(exercise_id):
    """
    Get specific guitar exercise with full details.

    Path params:
        exercise_id (str): Exercise ID

    Returns:
        JSON: Exercise object
    """
    try:
        exercise = guitar_generator.get_exercise_by_id(exercise_id)

        if not exercise:
            return jsonify({'error': f'Exercise not found: {exercise_id}'}), 404

        return jsonify(exercise)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/guitar/bpm-ladder/<exercise_id>', methods=['GET'])
def get_guitar_bpm_ladder(exercise_id):
    """
    Get BPM practice ladder for an exercise.

    Path params:
        exercise_id (str): Exercise ID

    Query params:
        start_bpm (int): Starting BPM (default: exercise floor)
        ceiling_bpm (int, optional): Target ceiling BPM (default: exercise ceiling)

    Returns:
        JSON: { "ladder": [60, 66, 73, ...], "exercise_name": "...", "default_subdivision": "..." }
    """
    try:
        exercise = guitar_generator.get_exercise_by_id(exercise_id)

        if not exercise:
            return jsonify({'error': f'Exercise not found: {exercise_id}'}), 404

        start_bpm = int(request.args.get('start_bpm', exercise['bpm_floor']))
        ceiling_bpm = int(request.args.get('ceiling_bpm', exercise['bpm_ceiling']))

        ladder = guitar_generator.get_bpm_ladder(start_bpm, ceiling_bpm)

        return jsonify({
            'ladder': ladder,
            'exercise_name': exercise['name'],
            'exercise_id': exercise['id'],
            'default_subdivision': exercise['subdivision_default'],
            'start_bpm': start_bpm,
            'ceiling_bpm': ceiling_bpm
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ===== GUITAR 100K ENDPOINTS =====

@app.route('/api/guitar100k/exercises/<instrument>', methods=['GET'])
def get_100k_exercises(instrument):
    """Get exercises state for an instrument (guitar or piano)."""
    try:
        data = guitar100k_service.get_exercises(instrument)
        return jsonify(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guitar100k/log', methods=['POST'])
def log_100k_practice():
    """Log a practice session. Body: {instrument, exercise_id, reps, bpm}."""
    try:
        data = request.get_json()
        instrument = data['instrument']
        exercise_id = data['exercise_id']
        reps = int(data['reps'])
        bpm = int(data['bpm'])

        result = guitar100k_service.log_practice(instrument, exercise_id, reps, bpm)
        if result is None:
            return jsonify({'error': f'Exercise not found: {exercise_id}'}), 404

        return jsonify({'success': True, 'data': result})
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid request: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guitar100k/exercises', methods=['POST'])
def add_100k_exercise():
    """Add a new exercise. Body: {instrument, id, name, category?, target_reps?, source?}."""
    try:
        data = request.get_json()
        instrument = data.pop('instrument', 'guitar')
        result = guitar100k_service.add_exercise(instrument, data)
        if result is None:
            return jsonify({'error': 'Exercise ID already exists'}), 409

        return jsonify({'success': True, 'exercise': result}), 201
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid request: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guitar100k/exercises/<instrument>/<exercise_id>', methods=['DELETE'])
def delete_100k_exercise(instrument, exercise_id):
    """Remove an exercise from the tracker."""
    try:
        removed = guitar100k_service.remove_exercise(instrument, exercise_id)
        if not removed:
            return jsonify({'error': 'Exercise not found'}), 404

        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guitar100k/export', methods=['GET'])
def export_100k_data():
    """Download a zip of all Guitar 100K data files."""
    try:
        buffer = guitar100k_service.export_data()
        return send_file(buffer, mimetype='application/zip',
                         as_attachment=True, download_name='guitar100k_backup.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guitar100k/library', methods=['GET'])
def get_slonimsky_library():
    """Serve the pre-generated Slonimsky pattern library."""
    try:
        library_path = os.path.join(app.static_folder, 'data', 'slonimsky_library.json')
        return send_file(library_path, mimetype='application/json')
    except FileNotFoundError:
        return jsonify({'error': 'Slonimsky library not yet generated'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


def elo_to_difficulty(elo):
    """
    Convert Elo rating to difficulty level (1-10).

    Elo ranges:
        < 800: 1-2 (Beginner)
        800-1000: 3-4 (Intermediate)
        1000-1200: 5-6 (Advanced)
        1200-1400: 7-8 (Expert)
        > 1400: 9-10 (Master)
    """
    if elo < 800:
        return max(1, min(2, 1 + (elo - 600) // 100))
    elif elo < 1000:
        return 3 + (elo - 800) // 100
    elif elo < 1200:
        return 5 + (elo - 1000) // 100
    elif elo < 1400:
        return 7 + (elo - 1200) // 100
    else:
        return min(10, 9 + (elo - 1400) // 100)


if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
