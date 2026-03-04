import random
from typing import List, Dict, Any, Optional, Tuple


# ===== MUSIC DATA =====

# VexFlow duration codes mapped to beat values (in quarter notes)
DURATION_MAP = {
    'w': 4.0,    # whole
    'h': 2.0,    # half
    'q': 1.0,    # quarter
    '8': 0.5,    # eighth
    '16': 0.25,  # sixteenth
}

DOT_MULTIPLIER = 1.5

# Scale definitions
SCALE_INTERVALS = {
    'C Major': {'root': 'C', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 0},
    'G Major': {'root': 'G', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 1},
    'D Major': {'root': 'D', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 2},
    'F Major': {'root': 'F', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': -1},
    'Bb Major': {'root': 'Bb', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': -2},
    'A Major': {'root': 'A', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 3},
    'Eb Major': {'root': 'Eb', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': -3},
    'Ab Major': {'root': 'Ab', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': -4},
    'E Major': {'root': 'E', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 4},
    'B Major': {'root': 'B', 'type': 'Major', 'intervals': [0, 2, 4, 5, 7, 9, 11], 'sharps_flats': 5},
    'A Minor': {'root': 'A', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': 0},
    'E Minor': {'root': 'E', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': 1},
    'D Minor': {'root': 'D', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': -1},
    'C Minor': {'root': 'C', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': -3},
    'G Minor': {'root': 'G', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': -2},
    'B Minor': {'root': 'B', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': 2},
    'F# Minor': {'root': 'F#', 'type': 'Natural Minor', 'intervals': [0, 2, 3, 5, 7, 8, 10], 'sharps_flats': 3},
    'D Dorian': {'root': 'D', 'type': 'Dorian', 'intervals': [0, 2, 3, 5, 7, 9, 10], 'sharps_flats': 0},
    'E Phrygian': {'root': 'E', 'type': 'Phrygian', 'intervals': [0, 1, 3, 5, 7, 8, 10], 'sharps_flats': 0},
    'F Lydian': {'root': 'F', 'type': 'Lydian', 'intervals': [0, 2, 4, 6, 7, 9, 11], 'sharps_flats': 0},
    'G Mixolydian': {'root': 'G', 'type': 'Mixolydian', 'intervals': [0, 2, 4, 5, 7, 9, 10], 'sharps_flats': 0},
}

SCALES_BY_DIFFICULTY = {
    1: ['C Major'],
    2: ['C Major', 'A Minor'],
    3: ['C Major', 'G Major', 'F Major', 'A Minor'],
    4: ['C Major', 'G Major', 'F Major', 'D Major', 'A Minor', 'E Minor'],
    5: ['C Major', 'G Major', 'F Major', 'D Major', 'Bb Major', 'A Minor', 'E Minor', 'D Minor'],
    6: ['C Major', 'G Major', 'F Major', 'D Major', 'Bb Major', 'A Major', 'A Minor', 'E Minor', 'D Minor', 'G Minor'],
    7: ['C Major', 'G Major', 'F Major', 'D Major', 'Bb Major', 'A Major', 'Eb Major', 'A Minor', 'E Minor', 'D Minor', 'C Minor', 'G Minor', 'B Minor'],
    8: ['C Major', 'G Major', 'F Major', 'D Major', 'Bb Major', 'A Major', 'Eb Major', 'Ab Major', 'A Minor', 'E Minor', 'D Minor', 'C Minor', 'G Minor', 'B Minor', 'F# Minor'],
    9: ['C Major', 'G Major', 'F Major', 'D Major', 'Bb Major', 'A Major', 'Eb Major', 'Ab Major', 'E Major', 'A Minor', 'E Minor', 'D Minor', 'C Minor', 'G Minor', 'B Minor', 'F# Minor', 'D Dorian', 'G Mixolydian'],
    10: list(SCALE_INTERVALS.keys()),
}

# Durations available per difficulty
DURATIONS_BY_DIFFICULTY = {
    1: ['w', 'h', 'q'],
    2: ['w', 'h', 'q'],
    3: ['h', 'q', '8'],
    4: ['h', 'q', '8'],
    5: ['h', 'q', '8'],
    6: ['h', 'q', '8'],
    7: ['q', '8', '16'],
    8: ['q', '8', '16'],
    9: ['q', '8', '16'],
    10: ['q', '8', '16'],
}

# Tempo ranges per difficulty
TEMPO_RANGES = {
    1: (60, 72), 2: (60, 80), 3: (70, 90), 4: (70, 100),
    5: (80, 110), 6: (80, 120), 7: (90, 130), 8: (90, 140),
    9: (100, 160), 10: (100, 180),
}

# ===== TIGHTER PITCH RANGES (centered on staves) =====
# Treble staff lines: E4(64), G4(67), B4(71), D5(74), F5(77)
# So the "on-staff" sweet spot is roughly 62-77 (D4 to F5)

TREBLE_RANGE_BY_DIFFICULTY = {
    1: (60, 72),   # C4 to C5 — includes tonic, middle C has 1 ledger line
    2: (60, 74),   # C4 to D5 — includes tonic both ends for C Major
    3: (60, 74),   # C4 to D5 — middle C (1 ledger line) to above stave
    4: (60, 76),   # C4 to E5
    5: (59, 77),   # B3 to F5 — 1 ledger line below
    6: (57, 77),   # A3 to F5
    7: (57, 79),   # A3 to G5 — 2 ledger lines max
    8: (55, 79),   # G3 to G5
    9: (53, 81),   # F3 to A5
    10: (53, 81),  # F3 to A5
}

# Bass staff lines: G2(43), B2(47), D3(50), F3(53), A3(57)
# Sweet spot: 43-57
BASS_RANGE_BY_DIFFICULTY = {
    5: (43, 52),   # G2 to E3 — entirely on stave
    6: (43, 55),   # G2 to G3
    7: (40, 57),   # E2 to A3 — 1 ledger line below
    8: (40, 57),   # E2 to A3
    9: (36, 60),   # C2 to C4
    10: (36, 60),  # C2 to C4
}

# Guitar ranges (centered on treble staff readable area)
GUITAR_RANGE_BY_DIFFICULTY = {
    1: (52, 64),   # E3 to E4 — open strings, on/near stave
    2: (52, 67),   # E3 to G4
    3: (50, 69),   # D3 to A4
    4: (48, 71),   # C3 to B4
    5: (48, 74),   # C3 to D5
    6: (45, 76),   # A2 to E5
    7: (43, 77),   # G2 to F5
    8: (40, 79),   # E2 to G5
    9: (40, 81),   # E2 to A5
    10: (40, 84),  # E2 to C6
}

# Guitar string data
GUITAR_STRINGS = [
    {'open_midi': 64, 'string_num': 1},  # High E
    {'open_midi': 59, 'string_num': 2},  # B
    {'open_midi': 55, 'string_num': 3},  # G
    {'open_midi': 50, 'string_num': 4},  # D
    {'open_midi': 45, 'string_num': 5},  # A
    {'open_midi': 40, 'string_num': 6},  # Low E
]

NOTE_NAMES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']

VEXFLOW_KEY_SIGNATURES = {
    'C Major': 'C', 'G Major': 'G', 'D Major': 'D', 'A Major': 'A',
    'E Major': 'E', 'B Major': 'B', 'F Major': 'F', 'Bb Major': 'Bb',
    'Eb Major': 'Eb', 'Ab Major': 'Ab',
    'A Minor': 'Am', 'E Minor': 'Em', 'D Minor': 'Dm', 'B Minor': 'Bm',
    'F# Minor': 'F#m', 'C Minor': 'Cm', 'G Minor': 'Gm',
    'D Dorian': 'C', 'E Phrygian': 'C', 'F Lydian': 'C', 'G Mixolydian': 'C',
}

# ===== RHYTHMIC CELLS =====
# Pre-composed rhythmic patterns that fill exactly 4 beats (one 4/4 bar)
# Each cell is a list of (duration_code, dots) tuples

RHYTHMIC_CELLS_BY_DIFFICULTY = {
    # Difficulty 1-2: simple, mostly quarters and halves
    1: [
        [('h', 0), ('h', 0)],                          # half half
        [('q', 0), ('q', 0), ('h', 0)],                # q q h
        [('h', 0), ('q', 0), ('q', 0)],                # h q q
        [('q', 0), ('q', 0), ('q', 0), ('q', 0)],      # q q q q
        [('w', 0)],                                      # whole
    ],
    # Difficulty 3-4: add eighths
    3: [
        [('q', 0), ('q', 0), ('q', 0), ('q', 0)],
        [('h', 0), ('q', 0), ('q', 0)],
        [('q', 0), ('q', 0), ('h', 0)],
        [('8', 0), ('8', 0), ('q', 0), ('h', 0)],
        [('h', 0), ('8', 0), ('8', 0), ('q', 0)],
        [('q', 0), ('8', 0), ('8', 0), ('q', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('8', 0), ('8', 0), ('h', 0)],
    ],
    # Difficulty 5-6: dotted rhythms
    5: [
        [('q', 0), ('q', 0), ('q', 0), ('q', 0)],
        [('q', 1), ('8', 0), ('q', 0), ('q', 0)],      # dotted quarter + eighth
        [('h', 0), ('q', 1), ('8', 0)],
        [('8', 0), ('8', 0), ('q', 0), ('q', 1), ('8', 0)],
        [('q', 0), ('q', 0), ('h', 0)],
        [('q', 1), ('8', 0), ('h', 0)],
        [('h', 1), ('q', 0)],                            # dotted half + quarter
    ],
    # Difficulty 7-8: sixteenths
    7: [
        [('q', 0), ('q', 0), ('q', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('q', 0), ('8', 0), ('8', 0), ('q', 0)],
        [('q', 0), ('16', 0), ('16', 0), ('8', 0), ('q', 0), ('q', 0)],
        [('q', 1), ('8', 0), ('q', 1), ('8', 0)],
        [('8', 0), ('16', 0), ('16', 0), ('q', 0), ('h', 0)],
        [('q', 0), ('8', 0), ('8', 0), ('q', 0), ('8', 0), ('8', 0)],
    ],
    # Difficulty 9-10: complex
    9: [
        [('16', 0), ('16', 0), ('8', 0), ('q', 0), ('8', 0), ('16', 0), ('16', 0), ('q', 0)],
        [('q', 1), ('8', 0), ('16', 0), ('16', 0), ('8', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('8', 0), ('8', 0), ('q', 0), ('q', 0)],
        [('q', 0), ('8', 0), ('16', 0), ('16', 0), ('q', 1), ('8', 0)],
        [('8', 0), ('q', 0), ('8', 0), ('8', 0), ('q', 0), ('8', 0)],
    ],
}

# 3/4 time cells (3 beats)
RHYTHMIC_CELLS_3_4 = {
    1: [
        [('h', 0), ('q', 0)],
        [('q', 0), ('q', 0), ('q', 0)],
        [('h', 1)],                                      # dotted half = 3 beats
    ],
    3: [
        [('q', 0), ('q', 0), ('q', 0)],
        [('h', 0), ('q', 0)],
        [('q', 0), ('8', 0), ('8', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('q', 0), ('q', 0)],
    ],
    5: [
        [('q', 1), ('8', 0), ('q', 0)],
        [('q', 0), ('q', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('q', 1), ('8', 0)],
    ],
    7: [
        [('8', 0), ('8', 0), ('8', 0), ('8', 0), ('q', 0)],
        [('q', 0), ('16', 0), ('16', 0), ('8', 0), ('q', 0)],
        [('q', 1), ('8', 0), ('q', 0)],
    ],
    9: [
        [('16', 0), ('16', 0), ('8', 0), ('q', 0), ('q', 0)],
        [('8', 0), ('8', 0), ('q', 0), ('8', 0), ('8', 0)],
    ],
}

# ===== CHORD SYSTEM =====
# Per-MEASURE probability of containing a chord, and chord types per difficulty
# This is the chance each measure gets a chord (not per-note)
CHORD_CONFIG = {
    1: {'prob': 0.0, 'types': []},
    2: {'prob': 0.0, 'types': []},
    3: {'prob': 0.35, 'types': ['dyad']},                    # thirds only
    4: {'prob': 0.40, 'types': ['dyad']},
    5: {'prob': 0.55, 'types': ['triad_root']},              # root position triads
    6: {'prob': 0.60, 'types': ['triad_root']},
    7: {'prob': 0.65, 'types': ['triad_root', 'triad_inv']}, # add inversions
    8: {'prob': 0.70, 'types': ['triad_root', 'triad_inv']},
    9: {'prob': 0.75, 'types': ['triad_root', 'triad_inv', 'seventh']},
    10: {'prob': 0.80, 'types': ['triad_root', 'triad_inv', 'seventh', 'sus']},
}

# Scale degree chord qualities (for major keys)
# I=maj, ii=min, iii=min, IV=maj, V=maj, vi=min, vii°=dim
DIATONIC_CHORD_DEGREES_MAJOR = {
    0: [0, 4, 7],     # I  - major
    1: [0, 3, 7],     # ii - minor
    2: [0, 3, 7],     # iii - minor
    3: [0, 4, 7],     # IV - major
    4: [0, 4, 7],     # V  - major
    5: [0, 3, 7],     # vi - minor
    6: [0, 3, 6],     # vii° - diminished
}

DIATONIC_CHORD_DEGREES_MINOR = {
    0: [0, 3, 7],     # i  - minor
    1: [0, 3, 6],     # ii° - diminished
    2: [0, 4, 7],     # III - major
    3: [0, 3, 7],     # iv - minor
    4: [0, 3, 7],     # v  - minor (natural minor)
    5: [0, 4, 7],     # VI - major
    6: [0, 4, 7],     # VII - major
}


# ===== HELPER FUNCTIONS =====

def generate_id():
    return f"sr_{random.randint(100000, 999999)}"


def midi_to_vexflow_key(midi_num: int) -> str:
    octave = (midi_num // 12) - 1
    note = NOTE_NAMES[midi_num % 12]
    return f"{note}/{octave}"


def get_scale_pitches(scale_name: str, midi_low: int, midi_high: int) -> List[int]:
    scale_info = SCALE_INTERVALS[scale_name]
    root_name = scale_info['root'].lower()
    # Handle enharmonic lookups
    root_midi_class = NOTE_NAMES.index(root_name) if root_name in NOTE_NAMES else 0

    pitches = []
    for octave_start in range(0, 128, 12):
        for interval in scale_info['intervals']:
            midi = octave_start + root_midi_class + interval
            if midi_low <= midi <= midi_high:
                pitches.append(midi)

    return sorted(set(pitches))


def get_chord_tones(scale_pitches: List[int], root_midi_class: int) -> List[int]:
    """Get pitches that are chord tones (degrees 1, 3, 5) of the key."""
    return [p for p in scale_pitches
            if (p - root_midi_class) % 12 in (0, 4, 7, 3)]  # major + minor 3rds and 5ths


def midi_to_guitar_tab(midi_num: int, max_fret: int = 12) -> Optional[Dict[str, int]]:
    best = None
    for gs in GUITAR_STRINGS:
        fret = midi_num - gs['open_midi']
        if 0 <= fret <= max_fret:
            if best is None or fret < best['fret']:
                best = {'string': gs['string_num'], 'fret': fret}
    return best


def get_accidentals_for_note(midi_num: int, scale_pitches: List[int]) -> List[Dict]:
    note_class = midi_num % 12
    note_name = NOTE_NAMES[note_class]
    accidentals = []
    if '#' in note_name:
        accidentals.append({'index': 0, 'type': '#'})
    elif 'b' in note_name:
        accidentals.append({'index': 0, 'type': 'b'})
    return accidentals


def get_root_midi_class(scale_name: str) -> int:
    root_name = SCALE_INTERVALS[scale_name]['root'].lower()
    return NOTE_NAMES.index(root_name) if root_name in NOTE_NAMES else 0


def is_chord_tone(midi_num: int, root_midi_class: int) -> bool:
    """Check if a pitch is a chord tone (1, 3, or 5) of the key."""
    interval = (midi_num - root_midi_class) % 12
    return interval in (0, 3, 4, 7)


def get_tonic_pitches(scale_pitches: List[int], root_midi_class: int) -> List[int]:
    """Get all pitches that are the tonic (root) of the scale."""
    return [p for p in scale_pitches if p % 12 == root_midi_class]


def get_dominant_pitches(scale_pitches: List[int], root_midi_class: int) -> List[int]:
    """Get all pitches that are the dominant (5th) of the scale."""
    dom_class = (root_midi_class + 7) % 12
    return [p for p in scale_pitches if p % 12 == dom_class]


def nearest_pitch(target: int, candidates: List[int]) -> int:
    """Find the pitch in candidates nearest to target."""
    if not candidates:
        return target
    return min(candidates, key=lambda p: abs(p - target))


# ===== MAIN GENERATOR =====

class SightReadingGenerator:
    """Generates musically coherent sight reading exercises."""

    def generate(self, difficulty: int, options: Dict[str, Any] = None) -> Dict[str, Any]:
        options = options or {}
        difficulty = max(1, min(10, difficulty))

        instrument = options.get('instrument', 'piano')
        measure_count = options.get('measures', 4)
        user_scales = options.get('scales', ['random'])
        user_tempo = options.get('tempo', None)
        user_note_types = options.get('note_types', ['random'])

        scale_name = self._pick_scale(difficulty, user_scales)
        key_sig = VEXFLOW_KEY_SIGNATURES.get(scale_name, 'C')
        time_sig = self._pick_time_signature(difficulty)
        tempo = self._pick_tempo(difficulty, user_tempo)
        available_durations = self._get_available_durations(difficulty, user_note_types)

        # Pitch range
        if instrument == 'guitar':
            midi_low, midi_high = GUITAR_RANGE_BY_DIFFICULTY.get(difficulty, (52, 64))
            max_fret = min(3 + (difficulty - 1) * 2, 22)
        else:
            midi_low, midi_high = TREBLE_RANGE_BY_DIFFICULTY.get(difficulty, (62, 71))
            max_fret = None

        scale_pitches = get_scale_pitches(scale_name, midi_low, midi_high)
        if not scale_pitches:
            scale_pitches = get_scale_pitches('C Major', midi_low, midi_high)

        root_class = get_root_midi_class(scale_name)
        is_minor = 'Minor' in scale_name or SCALE_INTERVALS[scale_name]['type'] in ('Natural Minor', 'Dorian', 'Phrygian')

        # Bass clef for piano
        use_bass = instrument == 'piano' and difficulty >= 5
        staves = 2 if use_bass else 1

        beats_per_measure = time_sig[0] * (4 / time_sig[1])

        # ===== GENERATE THE PIECE =====
        measures = self._generate_piece(
            difficulty, scale_pitches, root_class, is_minor,
            available_durations, beats_per_measure, time_sig,
            measure_count, instrument, max_fret
        )

        # Generate bass measures
        bass_measures = []
        if use_bass:
            bass_low, bass_high = BASS_RANGE_BY_DIFFICULTY.get(difficulty, (43, 52))
            bass_pitches = get_scale_pitches(scale_name, bass_low, bass_high)
            if not bass_pitches:
                bass_pitches = get_scale_pitches('C Major', bass_low, bass_high)
            bass_measures = self._generate_bass(
                difficulty, bass_pitches, root_class, is_minor,
                beats_per_measure, measure_count, measures
            )

        return {
            'id': generate_id(),
            'mode': 'sight_reading',
            'difficulty': difficulty,
            'instrument': instrument,
            'time_signature': time_sig,
            'key_signature': key_sig,
            'scale_name': scale_name,
            'tempo': tempo,
            'staves': staves,
            'measures': measures,
            'bass_measures': bass_measures,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return [self.generate(difficulty, options) for _ in range(count)]

    def get_available_scales(self, difficulty: int) -> List[str]:
        difficulty = max(1, min(10, difficulty))
        return SCALES_BY_DIFFICULTY.get(difficulty, SCALES_BY_DIFFICULTY[10])

    # ===== PIECE-LEVEL GENERATION =====

    def _generate_piece(
        self, difficulty, scale_pitches, root_class, is_minor,
        available_durations, beats_per_measure, time_sig,
        measure_count, instrument, max_fret
    ) -> List[Dict]:
        """Generate all treble measures with musical structure."""

        # Determine the center pitch (tonic nearest to middle of range)
        tonic_pitches = get_tonic_pitches(scale_pitches, root_class)
        center = scale_pitches[len(scale_pitches) // 2]
        home_pitch = nearest_pitch(center, tonic_pitches) if tonic_pitches else center

        # Get rhythmic cells for this difficulty and time signature
        cells = self._get_rhythmic_cells(difficulty, time_sig, available_durations)

        # Generate a motif (first measure's rhythm + melody)
        motif_rhythm = random.choice(cells)
        motif_pitches = self._generate_motif_melody(
            motif_rhythm, scale_pitches, home_pitch, root_class, difficulty
        )

        # Chord config
        chord_cfg = CHORD_CONFIG.get(difficulty, CHORD_CONFIG[1])

        measures = []
        prev_pitch = home_pitch

        for m_idx in range(measure_count):
            is_first = m_idx == 0
            is_last = m_idx == measure_count - 1
            is_penultimate = m_idx == measure_count - 2

            # === Rule G: Motif / Repetition ===
            if is_first:
                # Measure 1: use the motif directly
                rhythm = motif_rhythm
                pitches = motif_pitches
            elif m_idx == 2 and measure_count >= 4:
                # Measure 3: repeat motif (exact or transposed)
                rhythm = motif_rhythm
                # Transpose up or down a step
                transpose = random.choice([0, 2, -2])
                pitches = []
                for p in motif_pitches:
                    tp = p + transpose
                    # Snap to nearest scale pitch
                    pitches.append(nearest_pitch(tp, scale_pitches))
            else:
                # Other measures: pick a fresh rhythm, generate melody
                rhythm = random.choice(cells)
                pitches = self._generate_measure_melody(
                    rhythm, scale_pitches, prev_pitch, root_class, difficulty,
                    is_last, is_penultimate
                )

            # === Rule E: Cadence ===
            if is_last:
                pitches = self._apply_cadence(pitches, scale_pitches, root_class)
                # Make last note longer
                rhythm = self._lengthen_final_note(rhythm, beats_per_measure)

            if is_penultimate:
                pitches = self._approach_cadence(pitches, scale_pitches, root_class)

            # === Decide if this measure gets a chord ===
            measure_gets_chord = (
                chord_cfg['prob'] > 0
                and not is_last  # no chords in cadence measure
                and random.random() < chord_cfg['prob']
            )
            chord_placed = False

            # === Build note objects ===
            beat_pos = 0.0
            notes = []
            has_rest = False

            for note_idx, ((dur_code, dots), pitch) in enumerate(zip(rhythm, pitches)):
                beat_value = DURATION_MAP[dur_code]
                if dots:
                    beat_value *= DOT_MULTIPLIER

                is_strong_beat = beat_pos < 0.01 or abs(beat_pos - 2.0) < 0.01  # beat 1 or 3

                # === Rule F: Rests ===
                is_rest = False
                if (not is_first and not is_last and not has_rest
                        and difficulty >= 3 and not is_strong_beat
                        and random.random() < 0.08 * difficulty
                        and dur_code in ('q', '8')):
                    is_rest = True
                    has_rest = True

                # === Rule: Chords on strong beats (per-measure decision) ===
                # Allow 8th notes for chords at difficulty 7+
                chord_eligible_durs = ('w', 'h', 'q', '8') if difficulty >= 7 else ('w', 'h', 'q')
                chord_pitches_list = None
                if (measure_gets_chord and not chord_placed
                        and is_strong_beat and not is_rest
                        and dur_code in chord_eligible_durs):
                    chord_pitches_list = self._build_chord(
                        pitch, scale_pitches, root_class, is_minor,
                        chord_cfg['types'], difficulty
                    )
                    if chord_pitches_list:
                        chord_placed = True

                # Build note dict
                if is_rest:
                    note = {
                        'keys': ['b/4'],
                        'duration': dur_code,
                        'midi': [],
                        'is_rest': True,
                        'dots': dots,
                        'accidentals': [],
                    }
                elif chord_pitches_list:
                    keys = [midi_to_vexflow_key(p) for p in chord_pitches_list]
                    accidentals = []
                    for ci, cp in enumerate(chord_pitches_list):
                        for acc in get_accidentals_for_note(cp, scale_pitches):
                            accidentals.append({'index': ci, 'type': acc['type']})
                    note = {
                        'keys': keys,
                        'duration': dur_code,
                        'midi': chord_pitches_list,
                        'is_rest': False,
                        'dots': dots,
                        'accidentals': accidentals,
                    }
                else:
                    note = {
                        'keys': [midi_to_vexflow_key(pitch)],
                        'duration': dur_code,
                        'midi': [pitch],
                        'is_rest': False,
                        'dots': dots,
                        'accidentals': get_accidentals_for_note(pitch, scale_pitches),
                    }

                # Guitar TAB
                if instrument == 'guitar' and not is_rest:
                    tab = midi_to_guitar_tab(pitch, max_fret or 12)
                    if tab:
                        note['tab'] = tab

                notes.append(note)
                beat_pos += beat_value

            if pitches:
                prev_pitch = pitches[-1]

            measures.append({'clef': 'treble', 'notes': notes})

        # === Rule C: Post-pass to fix melodic violations ===
        self._fix_melodic_violations(measures, scale_pitches)

        return measures

    # ===== MELODY GENERATION =====

    def _generate_motif_melody(
        self, rhythm, scale_pitches, home_pitch, root_class, difficulty
    ) -> List[int]:
        """Generate a melodic motif starting from home pitch.
        Rule A: Start on a chord tone. Arc shape."""
        pitches = []
        prev = home_pitch

        for i, (dur_code, dots) in enumerate(rhythm):
            if i == 0:
                # Start on a chord tone near home
                chord_tones = [p for p in scale_pitches if is_chord_tone(p, root_class)]
                pitch = nearest_pitch(home_pitch, chord_tones) if chord_tones else home_pitch
            else:
                pitch = self._pick_melodic_pitch(scale_pitches, prev, root_class, difficulty, i, len(rhythm))
            pitches.append(pitch)
            prev = pitch

        return pitches

    def _generate_measure_melody(
        self, rhythm, scale_pitches, prev_pitch, root_class, difficulty,
        is_last, is_penultimate
    ) -> List[int]:
        """Generate melody for a non-motif measure."""
        pitches = []
        prev = prev_pitch

        for i, (dur_code, dots) in enumerate(rhythm):
            is_strong = (i == 0)

            if is_strong:
                # Rule B: strong beats prefer chord tones
                chord_tones = [p for p in scale_pitches if is_chord_tone(p, root_class)]
                nearby_ct = [p for p in chord_tones if abs(p - prev) <= 7]
                if nearby_ct and random.random() < 0.7:
                    pitch = random.choice(nearby_ct)
                else:
                    pitch = self._pick_melodic_pitch(scale_pitches, prev, root_class, difficulty, i, len(rhythm))
            else:
                pitch = self._pick_melodic_pitch(scale_pitches, prev, root_class, difficulty, i, len(rhythm))

            pitches.append(pitch)
            prev = pitch

        return pitches

    def _pick_melodic_pitch(
        self, scale_pitches, prev_pitch, root_class, difficulty, note_idx, total_notes
    ) -> int:
        """Pick next pitch with melodic contour rules.
        Rule C: stepwise preference, leap-then-step-back, arch shape."""
        if prev_pitch not in scale_pitches:
            prev_pitch = nearest_pitch(prev_pitch, scale_pitches)

        prev_idx = scale_pitches.index(prev_pitch)

        # Max interval in scale steps
        max_step = min(2 + difficulty // 2, 7)

        # Build weighted candidates
        candidates = []
        weights = []

        # Arch shape: rise in first half, fall in second half
        in_first_half = note_idx < total_notes / 2
        direction_bias = 1 if in_first_half else -1

        for i, pitch in enumerate(scale_pitches):
            step_dist = abs(i - prev_idx)
            if step_dist > max_step:
                continue

            direction = 1 if i > prev_idx else (-1 if i < prev_idx else 0)

            # Base weight by distance
            if step_dist == 0:
                w = 0.2
            elif step_dist == 1:
                w = 4.0    # stepwise strongly preferred
            elif step_dist == 2:
                w = 2.0    # third
            elif step_dist == 3:
                w = 0.8    # fourth
            else:
                w = 0.3    # larger leaps rare

            # Arch bias
            if direction == direction_bias:
                w *= 1.3
            elif direction == -direction_bias and step_dist <= 1:
                w *= 0.9  # allow step-back even against arch

            # Bonus for chord tones
            if is_chord_tone(pitch, root_class):
                w *= 1.2

            candidates.append(pitch)
            weights.append(w)

        if not candidates:
            return prev_pitch

        return random.choices(candidates, weights=weights, k=1)[0]

    # ===== CADENCE RULES =====

    def _apply_cadence(self, pitches, scale_pitches, root_class) -> List[int]:
        """Rule E: Last measure ends on tonic."""
        if not pitches:
            return pitches
        tonic_pitches = get_tonic_pitches(scale_pitches, root_class)
        if not tonic_pitches:
            # No tonic in range — find nearest tonic across all octaves
            all_tonics = [root_class + (12 * octave) for octave in range(1, 9)]
            tonic_pitches = all_tonics
        pitches[-1] = nearest_pitch(pitches[-1], tonic_pitches)
        return pitches

    def _approach_cadence(self, pitches, scale_pitches, root_class) -> List[int]:
        """Rule E: Penultimate measure approaches tonic stepwise (land on 2nd or 7th degree)."""
        if not pitches:
            return pitches
        # Find scale degree 2 (supertonic) near the last pitch
        tonic_pitches = get_tonic_pitches(scale_pitches, root_class)
        if tonic_pitches:
            nearest_tonic = nearest_pitch(pitches[-1], tonic_pitches)
            # Approach from above (step down) or below (step up)
            approach_above = nearest_tonic + 2  # whole step above
            approach_below = nearest_tonic - 1  # half step below (leading tone)
            candidates = [nearest_pitch(approach_above, scale_pitches),
                          nearest_pitch(approach_below, scale_pitches)]
            pitches[-1] = nearest_pitch(pitches[-1], candidates)
        return pitches

    def _lengthen_final_note(self, rhythm, beats_per_measure) -> List[Tuple]:
        """Rule E: Make the last note of the piece a longer duration."""
        if not rhythm:
            return rhythm
        rhythm = list(rhythm)
        last_dur, last_dots = rhythm[-1]
        last_beats = DURATION_MAP[last_dur] * (DOT_MULTIPLIER if last_dots else 1)

        # Try to make it at least a half note
        if last_beats < 2.0:
            # Calculate beats used by all but last
            used = sum(DURATION_MAP[d] * (DOT_MULTIPLIER if dt else 1) for d, dt in rhythm[:-1])
            remaining = beats_per_measure - used
            if remaining >= 2.0:
                rhythm[-1] = ('h', 0)
            elif remaining >= 1.0:
                rhythm[-1] = ('q', 0)

        return rhythm

    # ===== CHORD BUILDING =====

    def _build_chord(
        self, root_midi, scale_pitches, root_class, is_minor,
        chord_types, difficulty
    ) -> Optional[List[int]]:
        """Build a chord on the given root from scale tones.
        If the root is near the top of the range and we can't build upward,
        try building downward (using notes below the root)."""
        if root_midi not in scale_pitches:
            # Snap to nearest scale pitch
            root_midi = nearest_pitch(root_midi, scale_pitches)
            if root_midi not in scale_pitches:
                return None

        root_idx = scale_pitches.index(root_midi)
        chord_type = random.choice(chord_types)
        n = len(scale_pitches)

        if chord_type == 'dyad':
            # Third above root (2 scale steps), or below if at top
            if root_idx + 2 < n:
                return sorted([root_midi, scale_pitches[root_idx + 2]])
            elif root_idx - 2 >= 0:
                return sorted([scale_pitches[root_idx - 2], root_midi])
            return None

        elif chord_type in ('triad_root', 'triad_inv'):
            third_idx = root_idx + 2
            fifth_idx = root_idx + 4

            if fifth_idx < n:
                triad = [root_midi, scale_pitches[third_idx], scale_pitches[fifth_idx]]
            elif root_idx - 4 >= 0:
                # Build downward: root is the 5th, go 4 and 2 steps below
                triad = [scale_pitches[root_idx - 4], scale_pitches[root_idx - 2], root_midi]
            elif root_idx - 2 >= 0 and root_idx + 2 < n:
                # Partial: use note below as root
                triad = [scale_pitches[root_idx - 2], root_midi, scale_pitches[root_idx + 2]]
            else:
                return None

            if chord_type == 'triad_inv' and difficulty >= 7:
                inv = random.choice(['first', 'second'])
                if inv == 'first':
                    triad[0] += 12
                elif inv == 'second':
                    triad[0] += 12
                    triad[1] += 12

            return sorted(triad)

        elif chord_type == 'seventh':
            third_idx = root_idx + 2
            fifth_idx = root_idx + 4
            seventh_idx = root_idx + 6

            if seventh_idx < n:
                return sorted([root_midi, scale_pitches[third_idx],
                               scale_pitches[fifth_idx], scale_pitches[seventh_idx]])
            elif root_idx - 6 >= 0:
                # Build downward
                return sorted([scale_pitches[root_idx - 6], scale_pitches[root_idx - 4],
                               scale_pitches[root_idx - 2], root_midi])
            elif fifth_idx < n:
                # Fall back to triad if 7th doesn't fit
                return sorted([root_midi, scale_pitches[third_idx], scale_pitches[fifth_idx]])
            return None

        elif chord_type == 'sus':
            fourth_idx = root_idx + 3
            fifth_idx = root_idx + 4
            if fifth_idx < n:
                return sorted([root_midi, scale_pitches[fourth_idx], scale_pitches[fifth_idx]])
            elif root_idx - 4 >= 0:
                return sorted([scale_pitches[root_idx - 4], scale_pitches[root_idx - 1], root_midi])
            return None

        return None

    # ===== BASS LINE =====

    def _generate_bass(
        self, difficulty, bass_pitches, root_class, is_minor,
        beats_per_measure, measure_count, treble_measures
    ) -> List[Dict]:
        """Rule H: Bass plays chord tones, mostly whole/half notes, contrary motion."""
        bass_measures = []
        bass_durations = ['w', 'h'] if difficulty <= 7 else ['h', 'q']

        for m_idx in range(measure_count):
            notes = []

            if beats_per_measure >= 4 and 'w' in bass_durations:
                # Simple: one whole note on root/5th
                if m_idx == measure_count - 1:
                    # Last measure: tonic
                    tonic = get_tonic_pitches(bass_pitches, root_class)
                    pitch = random.choice(tonic) if tonic else bass_pitches[len(bass_pitches) // 2]
                elif m_idx == measure_count - 2:
                    # Penultimate: dominant
                    dom = get_dominant_pitches(bass_pitches, root_class)
                    pitch = random.choice(dom) if dom else bass_pitches[len(bass_pitches) // 2]
                else:
                    # Pick a chord tone
                    chord_tones = [p for p in bass_pitches if is_chord_tone(p, root_class)]
                    pitch = random.choice(chord_tones) if chord_tones else random.choice(bass_pitches)

                notes.append({
                    'keys': [midi_to_vexflow_key(pitch)],
                    'duration': 'w',
                    'midi': [pitch],
                    'is_rest': False,
                    'dots': 0,
                    'accidentals': get_accidentals_for_note(pitch, bass_pitches),
                })
            else:
                # Two half notes
                remaining = beats_per_measure
                prev_bass = bass_pitches[len(bass_pitches) // 2]
                while remaining > 0.01:
                    dur = 'h' if remaining >= 2.0 else 'q'
                    bv = DURATION_MAP[dur]
                    chord_tones = [p for p in bass_pitches if is_chord_tone(p, root_class)]
                    pitch = nearest_pitch(prev_bass, chord_tones) if chord_tones else prev_bass
                    # Vary slightly
                    nearby = [p for p in chord_tones if abs(p - prev_bass) <= 7]
                    if nearby:
                        pitch = random.choice(nearby)
                    notes.append({
                        'keys': [midi_to_vexflow_key(pitch)],
                        'duration': dur,
                        'midi': [pitch],
                        'is_rest': False,
                        'dots': 0,
                        'accidentals': get_accidentals_for_note(pitch, bass_pitches),
                    })
                    prev_bass = pitch
                    remaining -= bv

            bass_measures.append({'clef': 'bass', 'notes': notes})

        return bass_measures

    # ===== POST-PASS FIXES =====

    def _fix_melodic_violations(self, measures, scale_pitches):
        """Rule C: Fix consecutive leaps, too many repeated pitches, etc."""
        all_pitches = []
        for m in measures:
            for n in m['notes']:
                if not n['is_rest'] and n['midi']:
                    all_pitches.append((n, n['midi'][0] if len(n['midi']) == 1 else None))

        # Check for 3+ repeated pitches
        for i in range(2, len(all_pitches)):
            note_obj, pitch = all_pitches[i]
            if pitch is None:
                continue
            _, prev1 = all_pitches[i - 1]
            _, prev2 = all_pitches[i - 2]
            if prev1 is not None and prev2 is not None and pitch == prev1 == prev2:
                # Move this pitch by a step
                idx = scale_pitches.index(pitch) if pitch in scale_pitches else -1
                if idx >= 0:
                    new_idx = idx + random.choice([1, -1])
                    new_idx = max(0, min(len(scale_pitches) - 1, new_idx))
                    new_pitch = scale_pitches[new_idx]
                    note_obj['midi'] = [new_pitch]
                    note_obj['keys'] = [midi_to_vexflow_key(new_pitch)]
                    note_obj['accidentals'] = get_accidentals_for_note(new_pitch, scale_pitches)
                    all_pitches[i] = (note_obj, new_pitch)

    # ===== RHYTHM HELPERS =====

    def _get_rhythmic_cells(self, difficulty, time_sig, available_durations) -> List[List[Tuple]]:
        """Get rhythmic cells appropriate for the difficulty and time signature."""
        is_3_4 = time_sig == [3, 4]
        cell_bank = RHYTHMIC_CELLS_3_4 if is_3_4 else RHYTHMIC_CELLS_BY_DIFFICULTY

        # Find the highest difficulty tier <= current difficulty
        tier = 1
        for t in sorted(cell_bank.keys()):
            if t <= difficulty:
                tier = t

        cells = cell_bank[tier]

        # Filter cells to only use available durations
        filtered = []
        for cell in cells:
            if all(dur in available_durations or dur in ('w', 'h', 'q', '8', '16') for dur, _ in cell):
                filtered.append(cell)

        return filtered if filtered else cells

    # ===== CONFIG PICKERS =====

    def _pick_scale(self, difficulty, user_scales):
        if user_scales and user_scales != ['random']:
            valid = [s for s in user_scales if s in SCALE_INTERVALS]
            if valid:
                return random.choice(valid)
        return random.choice(SCALES_BY_DIFFICULTY.get(difficulty, SCALES_BY_DIFFICULTY[10]))

    def _pick_time_signature(self, difficulty):
        if difficulty <= 4:
            return [4, 4]
        elif difficulty <= 6:
            return random.choice([[4, 4], [4, 4], [3, 4]])
        elif difficulty <= 8:
            return random.choice([[4, 4], [3, 4], [3, 4], [6, 8]])
        else:
            return random.choice([[4, 4], [3, 4], [6, 8], [5, 4]])

    def _pick_tempo(self, difficulty, user_tempo):
        if user_tempo is not None:
            return max(40, min(200, user_tempo))
        low, high = TEMPO_RANGES.get(difficulty, (80, 120))
        return random.randint(low, high)

    def _get_available_durations(self, difficulty, user_note_types):
        if user_note_types and user_note_types != ['random']:
            valid = [d for d in user_note_types if d in DURATION_MAP]
            if valid:
                return valid
        return DURATIONS_BY_DIFFICULTY.get(difficulty, ['q', '8'])
