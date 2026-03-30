"""
Guitar 100,000 - Flat File I/O Service
Manages exercises.json state files and practice_logs.csv on Railway Volume.
"""
import os
import json
import csv
import zipfile
import io
from datetime import datetime, timezone

DATA_DIR = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', './local_data')

GUITAR_EXERCISES_FILE = os.path.join(DATA_DIR, 'guitar_exercises.json')
PIANO_EXERCISES_FILE = os.path.join(DATA_DIR, 'piano_exercises.json')
GUITAR_LOGS_FILE = os.path.join(DATA_DIR, 'guitar_logs.csv')
PIANO_LOGS_FILE = os.path.join(DATA_DIR, 'piano_logs.csv')

CSV_HEADER = ['timestamp', 'exercise_id', 'reps', 'bpm']

DEFAULT_GUITAR_EXERCISES = [
    {"id": "spider_walk_1234", "name": "Spider Walk - 1234", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "spider_walk_1324", "name": "Spider Walk - 1324", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "spider_walk_4321", "name": "Spider Walk - 4321 (Reverse)", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "chromatic_run_asc", "name": "Chromatic Run - Ascending", "category": "chromatic", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "chromatic_run_desc", "name": "Chromatic Run - Descending", "category": "chromatic", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "pentatonic_box1", "name": "Pentatonic - Box 1", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "pentatonic_box2", "name": "Pentatonic - Box 2", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "pentatonic_5boxes", "name": "Pentatonic - All 5 Boxes", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "major_scale_3nps", "name": "Major Scale - 3 Notes/String", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "legato_hammer_pull", "name": "Legato - Hammer-On / Pull-Off", "category": "legato", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "legato_trills", "name": "Legato - Trill Endurance", "category": "legato", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "alt_pick_single", "name": "Alternate Picking - Single String", "category": "picking", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "alt_pick_cross", "name": "Alternate Picking - String Crossing", "category": "picking", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "string_skip_basic", "name": "String Skipping - Basic", "category": "picking", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "sweep_3string", "name": "Sweep Arpeggio - 3 String", "category": "sweep", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "sweep_5string", "name": "Sweep Arpeggio - 5 String", "category": "sweep", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "bend_whole_step", "name": "Bending - Whole Step Accuracy", "category": "expression", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "vibrato_control", "name": "Vibrato - Speed & Width Control", "category": "expression", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "palm_mute_gallop", "name": "Palm Mute - Gallop Pattern", "category": "rhythm", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "chord_transition_open", "name": "Chord Transitions - Open Chords", "category": "rhythm", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
]

DEFAULT_PIANO_EXERCISES = [
    {"id": "hanon_1", "name": "Hanon - Exercise 1", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "hanon_2", "name": "Hanon - Exercise 2", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "hanon_3", "name": "Hanon - Exercise 3", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "cmaj_scale_2oct", "name": "C Major Scale - 2 Octaves", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "gmaj_scale_2oct", "name": "G Major Scale - 2 Octaves", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "chromatic_scale_piano", "name": "Chromatic Scale - Both Hands", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "arpeggios_maj", "name": "Arpeggios - Major Triads", "category": "arpeggios", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "arpeggios_min", "name": "Arpeggios - Minor Triads", "category": "arpeggios", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "thirds_parallel", "name": "Parallel Thirds", "category": "intervals", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "sixths_parallel", "name": "Parallel Sixths", "category": "intervals", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "octave_jumps", "name": "Octave Jumps", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "staccato_etude", "name": "Staccato Etude", "category": "articulation", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "legato_etude_piano", "name": "Legato Etude", "category": "articulation", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "trill_exercise_piano", "name": "Trill Exercise", "category": "technique", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "contrary_motion", "name": "Contrary Motion Scales", "category": "scales", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "broken_chords", "name": "Broken Chords - I IV V I", "category": "chords", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "cadence_patterns", "name": "Cadence Patterns", "category": "chords", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "alberti_bass", "name": "Alberti Bass Pattern", "category": "accompaniment", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "independence_rh_melody", "name": "Hand Independence - RH Melody", "category": "independence", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
    {"id": "independence_lh_melody", "name": "Hand Independence - LH Melody", "category": "independence", "target_reps": 5000, "total_reps": 0, "latest_bpm": 0, "best_bpm": 0, "source": "default"},
]


def _get_files(instrument):
    """Return (exercises_file, logs_file) paths for an instrument."""
    if instrument == 'guitar':
        return GUITAR_EXERCISES_FILE, GUITAR_LOGS_FILE
    elif instrument == 'piano':
        return PIANO_EXERCISES_FILE, PIANO_LOGS_FILE
    else:
        raise ValueError(f"Unknown instrument: {instrument}")


def _get_defaults(instrument):
    """Return default exercise list for an instrument."""
    if instrument == 'guitar':
        return DEFAULT_GUITAR_EXERCISES
    elif instrument == 'piano':
        return DEFAULT_PIANO_EXERCISES
    else:
        raise ValueError(f"Unknown instrument: {instrument}")


def init_files():
    """Create data directory and default files if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)

    for instrument in ('guitar', 'piano'):
        ex_file, log_file = _get_files(instrument)
        defaults = _get_defaults(instrument)

        if not os.path.exists(ex_file):
            now = datetime.now(timezone.utc).isoformat()
            exercises = []
            for ex in defaults:
                exercises.append({**ex, "created_at": now})
            with open(ex_file, 'w') as f:
                json.dump({"exercises": exercises}, f, indent=2)

        if not os.path.exists(log_file):
            with open(log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)


def get_exercises(instrument):
    """Read and return exercises JSON for an instrument."""
    ex_file, _ = _get_files(instrument)
    with open(ex_file, 'r') as f:
        return json.load(f)


def log_practice(instrument, exercise_id, reps, bpm):
    """Log a practice session: append CSV row and update JSON totals."""
    ex_file, log_file = _get_files(instrument)
    now = datetime.now(timezone.utc).isoformat()

    # Append to CSV
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([now, exercise_id, reps, bpm])

    # Update JSON state
    with open(ex_file, 'r') as f:
        data = json.load(f)

    for ex in data['exercises']:
        if ex['id'] == exercise_id:
            ex['total_reps'] = ex.get('total_reps', 0) + int(reps)
            ex['latest_bpm'] = int(bpm)
            if int(bpm) > ex.get('best_bpm', 0):
                ex['best_bpm'] = int(bpm)
            break
    else:
        return None  # Exercise not found

    with open(ex_file, 'w') as f:
        json.dump(data, f, indent=2)

    return data


def add_exercise(instrument, exercise_data):
    """Add a new exercise to the instrument's JSON file."""
    ex_file, _ = _get_files(instrument)

    with open(ex_file, 'r') as f:
        data = json.load(f)

    # Check for duplicate ID
    existing_ids = {ex['id'] for ex in data['exercises']}
    if exercise_data['id'] in existing_ids:
        return None  # Already exists

    now = datetime.now(timezone.utc).isoformat()
    new_exercise = {
        "id": exercise_data['id'],
        "name": exercise_data['name'],
        "category": exercise_data.get('category', 'slonimsky'),
        "target_reps": exercise_data.get('target_reps', 5000),
        "total_reps": 0,
        "latest_bpm": 0,
        "best_bpm": 0,
        "source": exercise_data.get('source', 'slonimsky_lab'),
        "created_at": now,
    }
    data['exercises'].append(new_exercise)

    with open(ex_file, 'w') as f:
        json.dump(data, f, indent=2)

    return new_exercise


def remove_exercise(instrument, exercise_id):
    """Remove an exercise from the instrument's JSON file."""
    ex_file, _ = _get_files(instrument)

    with open(ex_file, 'r') as f:
        data = json.load(f)

    original_len = len(data['exercises'])
    data['exercises'] = [ex for ex in data['exercises'] if ex['id'] != exercise_id]

    if len(data['exercises']) == original_len:
        return False  # Not found

    with open(ex_file, 'w') as f:
        json.dump(data, f, indent=2)

    return True


def export_data():
    """Zip all data files and return bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filepath in [GUITAR_EXERCISES_FILE, PIANO_EXERCISES_FILE, GUITAR_LOGS_FILE, PIANO_LOGS_FILE]:
            if os.path.exists(filepath):
                zf.write(filepath, os.path.basename(filepath))
    buffer.seek(0)
    return buffer
