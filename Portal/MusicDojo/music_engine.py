import random
from typing import List, Dict, Any


# ===== MUSIC DATA =====

CHROMATIC_KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

SCALE_DEFINITIONS = {
    'Major': [0, 2, 4, 5, 7, 9, 11],
    'Natural Minor': [0, 2, 3, 5, 7, 8, 10],
    'Dorian': [0, 2, 3, 5, 7, 9, 10],
    'Phrygian': [0, 1, 3, 5, 7, 8, 10],
    'Lydian': [0, 2, 4, 6, 7, 9, 11],
    'Mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'Locrian': [0, 1, 3, 5, 6, 8, 10],
    'Harmonic Minor': [0, 2, 3, 5, 7, 8, 11],
    'Melodic Minor': [0, 2, 3, 5, 7, 9, 11],
    'Jazz Minor': [0, 2, 3, 5, 7, 9, 11],
    'Lydian Dominant': [0, 2, 4, 6, 7, 9, 10],
    'Altered': [0, 1, 3, 4, 6, 8, 10],
    'Phrygian Dominant': [0, 1, 4, 5, 7, 8, 10],
    'Dominant Bebop': [0, 2, 4, 5, 7, 9, 10, 11],
    'Whole Tone': [0, 2, 4, 6, 8, 10],
    'Diminished HW': [0, 1, 3, 4, 6, 7, 9, 10],
    'Pentatonic Major': [0, 2, 4, 7, 9],
    'Pentatonic Minor': [0, 3, 5, 7, 10],
    'Blues': [0, 3, 5, 6, 7, 10],
}

SCALE_CATEGORIES = {
    'beginner': ['Major', 'Natural Minor', 'Pentatonic Major', 'Pentatonic Minor'],
    'jazz': ['Dorian', 'Lydian', 'Mixolydian', 'Altered', 'Jazz Minor', 'Lydian Dominant', 'Whole Tone', 'Diminished HW'],
    'common': ['Major', 'Natural Minor', 'Harmonic Minor', 'Melodic Minor', 'Pentatonic Major', 'Pentatonic Minor', 'Blues'],
}

PATTERN_DEFINITIONS = {
    'Block Chords': {'sequence': [[1, 3, 5]], 'desc': 'All chord tones simultaneously', 'vibe': ['all']},
    'Alberti Bass': {'sequence': [1, 5, 3, 5], 'desc': 'Root-fifth-third-fifth pattern', 'vibe': ['classical', 'beginner']},
    'Walking Bass': {'sequence': [1, 2, 3, 5], 'desc': 'Stepwise ascending movement', 'vibe': ['jazz', 'swing']},
    'Stride': {'sequence': [1, [3, 5, 8]], 'desc': 'Low bass then mid-range chord', 'vibe': ['jazz', 'ragtime']},
    'Bossa Nova': {'sequence': [1, 5, 8, 5, 1, 5, 3, 5], 'desc': 'Syncopated Latin rhythm', 'vibe': ['latin', 'jazz']},
    'Waltz': {'sequence': [1, [3, 5], [3, 5]], 'desc': 'Classic 3/4 oom-pah-pah', 'vibe': ['classical', 'romantic']},
    'Arpeggio Up': {'sequence': [1, 3, 5, 8], 'desc': 'Rising broken chord', 'vibe': ['all']},
    'Arpeggio Down': {'sequence': [8, 5, 3, 1], 'desc': 'Falling broken chord', 'vibe': ['all']},
}

# Interval data for ear training
INTERVALS = {
    'Perfect Unison': 0,
    'Minor 2nd': 1,
    'Major 2nd': 2,
    'Minor 3rd': 3,
    'Major 3rd': 4,
    'Perfect 4th': 5,
    'Tritone': 6,
    'Perfect 5th': 7,
    'Minor 6th': 8,
    'Major 6th': 9,
    'Minor 7th': 10,
    'Major 7th': 11,
    'Perfect Octave': 12,
}

# Chord quality data
CHORD_QUALITIES = {
    'Major': [0, 4, 7],
    'Minor': [0, 3, 7],
    'Diminished': [0, 3, 6],
    'Augmented': [0, 4, 8],
    'Major 7th': [0, 4, 7, 11],
    'Minor 7th': [0, 3, 7, 10],
    'Dominant 7th': [0, 4, 7, 10],
    'Diminished 7th': [0, 3, 6, 9],
}


# ===== HELPER FUNCTIONS =====

def generate_id():
    """Generate a unique exercise ID."""
    return f"ex_{random.randint(100000, 999999)}"


def get_note_from_midi(midi_num):
    """Convert MIDI number to note name with octave."""
    notes = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    octave = (midi_num // 12) - 1
    note = notes[midi_num % 12]
    return f"{note}{octave}"


def midi_to_frequency(midi_num):
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi_num - 69) / 12.0))


# ===== DIRECTION EXERCISE GENERATOR =====

class DirectionExerciseGenerator:
    """Generate hand coordination exercises for Direction Trainer."""

    MOTION_TYPES = ['similar', 'contrary', 'oblique']
    DIRECTIONS = ['up', 'down', 'stay']

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """
        Generate a single direction exercise.

        Args:
            difficulty: 1-10, affects complexity and speed

        Returns:
            Exercise dict with motion type, tempo, and pattern
        """
        # Higher difficulty = faster tempo and more complex motions
        base_tempo = 60 + (difficulty * 15)
        tempo = random.randint(base_tempo - 10, base_tempo + 10)

        # Choose motion type based on difficulty
        if difficulty <= 3:
            motion_type = 'similar'
        elif difficulty <= 6:
            motion_type = random.choice(['similar', 'contrary'])
        else:
            motion_type = random.choice(self.MOTION_TYPES)

        # Generate pattern
        pattern_length = min(4 + difficulty // 2, 12)
        pattern = self._generate_pattern(motion_type, pattern_length)

        return {
            'id': generate_id(),
            'mode': 'direction',
            'difficulty': difficulty,
            'tempo': tempo,
            'motion_type': motion_type,
            'pattern': pattern,
            'note_range': 8,
        }

    def _generate_pattern(self, motion_type: str, length: int) -> List[Dict[str, str]]:
        """Generate a pattern of hand movements."""
        pattern = []
        for _ in range(length):
            if motion_type == 'similar':
                direction = random.choice(['up', 'down'])
                pattern.append({'left': direction, 'right': direction})
            elif motion_type == 'contrary':
                direction = random.choice(['up', 'down'])
                pattern.append({'left': direction, 'right': 'down' if direction == 'up' else 'up'})
            else:  # oblique
                moving_hand = random.choice(['left', 'right'])
                direction = random.choice(['up', 'down'])
                if moving_hand == 'left':
                    pattern.append({'left': direction, 'right': 'stay'})
                else:
                    pattern.append({'left': 'stay', 'right': direction})
        return pattern

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple direction exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== POLYRHYTHM GENERATOR =====

class PolyrhythmGenerator:
    """Generate polyrhythm exercises."""

    RATIOS_BY_DIFFICULTY = {
        1: [(2, 1), (3, 1)],
        2: [(2, 1), (3, 1), (3, 2)],
        3: [(3, 2), (4, 3)],
        4: [(3, 2), (4, 3), (5, 4)],
        5: [(4, 3), (5, 4), (5, 3)],
        6: [(5, 4), (5, 3), (7, 4)],
        7: [(5, 3), (7, 4), (7, 5)],
        8: [(7, 5), (8, 5), (9, 8)],
        9: [(8, 5), (9, 8), (11, 8)],
        10: [(11, 8), (13, 8), (5, 2)],
    }

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a polyrhythm exercise."""
        difficulty = max(1, min(10, difficulty))
        ratios = self.RATIOS_BY_DIFFICULTY.get(difficulty, [(3, 2)])
        left, right = random.choice(ratios)

        base_tempo = 60 + (difficulty * 10)
        tempo = random.randint(base_tempo - 10, base_tempo + 10)

        return {
            'id': generate_id(),
            'mode': 'polyrhythm',
            'difficulty': difficulty,
            'tempo': tempo,
            'ratio_left': left,
            'ratio_right': right,
            'duration_bars': 4,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple polyrhythm exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== SWING EXERCISE GENERATOR =====

class SwingExerciseGenerator:
    """Generate swing feel exercises."""

    SWING_STYLES = ['straight', 'light', 'heavy', 'shuffle']
    SWING_PERCENTAGES = {
        'straight': 50,
        'light': 58,
        'heavy': 66,
        'shuffle': 75,
    }

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a swing exercise."""
        # Lower difficulty = fewer swing styles
        if difficulty <= 3:
            styles = ['straight', 'light']
        elif difficulty <= 6:
            styles = ['straight', 'light', 'heavy']
        else:
            styles = self.SWING_STYLES

        style = random.choice(styles)
        swing_pct = self.SWING_PERCENTAGES[style]

        base_tempo = 80 + (difficulty * 10)
        tempo = random.randint(base_tempo - 10, base_tempo + 10)

        return {
            'id': generate_id(),
            'mode': 'swing',
            'difficulty': difficulty,
            'tempo': tempo,
            'swing_style': style,
            'swing_percentage': swing_pct,
            'beats_per_measure': 4,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple swing exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== TEMPO RAMP GENERATOR =====

class TempoRampGenerator:
    """Generate tempo ramp progression exercises."""

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a tempo ramp exercise."""
        # Start tempo decreases with difficulty (makes it harder)
        start_tempo = max(60, 120 - (difficulty * 5))

        # Max tempo increases with difficulty
        max_tempo = min(200, 120 + (difficulty * 10))

        # Increment size increases with difficulty
        increment = 2 + (difficulty // 2)

        # Interval decreases with difficulty (ramps faster)
        interval_seconds = max(15, 45 - (difficulty * 3))

        return {
            'id': generate_id(),
            'mode': 'tempo_ramp',
            'difficulty': difficulty,
            'start_tempo': start_tempo,
            'max_tempo': max_tempo,
            'bpm_increment': increment,
            'ramp_interval_seconds': interval_seconds,
            'warning_beats': 4,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple tempo ramp exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== SCALE/PATTERN GENERATOR =====

class ScalePatternGenerator:
    """Generate jazz improvisation scale/pattern combinations."""

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a scale/pattern exercise."""
        # Choose scale category based on difficulty
        if difficulty <= 3:
            category = 'beginner'
        elif difficulty <= 7:
            category = 'common'
        else:
            category = 'jazz'

        scales = SCALE_CATEGORIES.get(category, SCALE_CATEGORIES['beginner'])
        scale_type = random.choice(scales)
        key = random.choice(CHROMATIC_KEYS)

        # Choose pattern
        pattern_name = random.choice(list(PATTERN_DEFINITIONS.keys()))
        pattern = PATTERN_DEFINITIONS[pattern_name]

        return {
            'id': generate_id(),
            'mode': 'improv',
            'difficulty': difficulty,
            'key': key,
            'scale_type': scale_type,
            'scale_notes': self._get_scale_notes(key, scale_type),
            'pattern_name': pattern_name,
            'pattern_sequence': pattern['sequence'],
            'pattern_description': pattern['desc'],
        }

    def _get_scale_notes(self, key: str, scale_type: str) -> List[str]:
        """Get the notes of a scale."""
        root_idx = CHROMATIC_KEYS.index(key)
        intervals = SCALE_DEFINITIONS.get(scale_type, [0, 2, 4, 5, 7, 9, 11])

        notes = []
        for interval in intervals:
            note_idx = (root_idx + interval) % 12
            notes.append(CHROMATIC_KEYS[note_idx])
        return notes

    def get_scale_info(self, key: str, scale_type: str) -> Dict[str, Any]:
        """Get detailed information about a scale."""
        notes = self._get_scale_notes(key, scale_type)
        intervals = SCALE_DEFINITIONS.get(scale_type, [0, 2, 4, 5, 7, 9, 11])

        return {
            'key': key,
            'scale_type': scale_type,
            'notes': notes,
            'intervals': intervals,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple scale/pattern exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== GHOST METRONOME GENERATOR =====

class GhostMetronomeGenerator:
    """Generate ghost metronome exercises."""

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a ghost metronome exercise."""
        base_tempo = 60 + (difficulty * 12)
        tempo = random.randint(base_tempo - 10, base_tempo + 10)

        # More difficult = more ghost bars
        if difficulty <= 3:
            active_bars = 4
            ghost_bars = 1
        elif difficulty <= 6:
            active_bars = 4
            ghost_bars = 2
        else:
            active_bars = random.choice([2, 4])
            ghost_bars = random.choice([2, 4])

        beats_per_bar = random.choice([3, 4]) if difficulty > 5 else 4

        return {
            'id': generate_id(),
            'mode': 'ghost',
            'difficulty': difficulty,
            'tempo': tempo,
            'beats_per_bar': beats_per_bar,
            'active_bars': active_bars,
            'ghost_bars': ghost_bars,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple ghost metronome exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== EAR TRAINING GENERATOR =====

class EarTrainingGenerator:
    """Generate ear training exercises (intervals, chords, progressions)."""

    EXERCISE_TYPES = {
        'beginner': ['interval'],
        'intermediate': ['interval', 'chord'],
        'advanced': ['interval', 'chord', 'progression'],
    }

    SIMPLE_INTERVALS = ['Perfect Unison', 'Perfect 5th', 'Perfect Octave', 'Major 3rd', 'Perfect 4th']
    ALL_INTERVALS = list(INTERVALS.keys())

    SIMPLE_CHORDS = ['Major', 'Minor']
    INTERMEDIATE_CHORDS = ['Major', 'Minor', 'Diminished', 'Augmented']
    ALL_CHORDS = list(CHORD_QUALITIES.keys())

    PROGRESSIONS = {
        'I-V-I': ['I', 'V', 'I'],
        'I-IV-V-I': ['I', 'IV', 'V', 'I'],
        'I-vi-IV-V': ['I', 'vi', 'IV', 'V'],
        'ii-V-I': ['ii', 'V', 'I'],
        'I-vi-ii-V': ['I', 'vi', 'ii', 'V'],
    }

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate an ear training exercise."""
        # Choose exercise type based on difficulty
        if difficulty <= 3:
            level = 'beginner'
        elif difficulty <= 7:
            level = 'intermediate'
        else:
            level = 'advanced'

        exercise_types = self.EXERCISE_TYPES[level]
        exercise_type = random.choice(exercise_types)

        if exercise_type == 'interval':
            return self._generate_interval_exercise(difficulty)
        elif exercise_type == 'chord':
            return self._generate_chord_exercise(difficulty)
        else:  # progression
            return self._generate_progression_exercise(difficulty)

    def _generate_interval_exercise(self, difficulty: int) -> Dict[str, Any]:
        """Generate an interval recognition exercise."""
        # Choose interval pool based on difficulty
        if difficulty <= 3:
            interval_pool = self.SIMPLE_INTERVALS
        elif difficulty <= 7:
            # Add some harder intervals
            interval_pool = self.SIMPLE_INTERVALS + ['Minor 3rd', 'Major 6th', 'Minor 7th']
        else:
            interval_pool = self.ALL_INTERVALS

        interval_name = random.choice(interval_pool)
        semitones = INTERVALS[interval_name]

        # Generate random root note (MIDI 48-72, C3-C5)
        root_midi = random.randint(48, 72)
        top_midi = root_midi + semitones

        # Direction: ascending or descending
        direction = random.choice(['ascending', 'descending'])
        if direction == 'descending':
            root_midi, top_midi = top_midi, root_midi

        # Harmonic or melodic
        play_style = random.choice(['harmonic', 'melodic']) if difficulty > 3 else 'melodic'

        # Create answer choices (interval name is correct, plus 3 distractors)
        all_intervals = list(set(interval_pool))
        choices = [interval_name]
        while len(choices) < 4:
            distractor = random.choice(all_intervals)
            if distractor not in choices:
                choices.append(distractor)
        random.shuffle(choices)

        return {
            'id': generate_id(),
            'mode': 'ear_training',
            'exercise_type': 'interval',
            'difficulty': difficulty,
            'interval_name': interval_name,
            'root_note': get_note_from_midi(root_midi),
            'top_note': get_note_from_midi(top_midi),
            'root_midi': root_midi,
            'top_midi': top_midi,
            'direction': direction,
            'play_style': play_style,
            'choices': choices,
            'correct_answer': interval_name,
        }

    def _generate_chord_exercise(self, difficulty: int) -> Dict[str, Any]:
        """Generate a chord quality recognition exercise."""
        # Choose chord pool based on difficulty
        if difficulty <= 4:
            chord_pool = self.SIMPLE_CHORDS
        elif difficulty <= 7:
            chord_pool = self.INTERMEDIATE_CHORDS
        else:
            chord_pool = self.ALL_CHORDS

        chord_quality = random.choice(chord_pool)
        intervals = CHORD_QUALITIES[chord_quality]

        # Generate random root note (MIDI 36-60)
        root_midi = random.randint(36, 60)
        chord_midis = [root_midi + interval for interval in intervals]

        # Create answer choices
        all_chords = list(set(chord_pool))
        choices = [chord_quality]
        while len(choices) < 4:
            distractor = random.choice(all_chords)
            if distractor not in choices:
                choices.append(distractor)
        random.shuffle(choices)

        return {
            'id': generate_id(),
            'mode': 'ear_training',
            'exercise_type': 'chord',
            'difficulty': difficulty,
            'chord_quality': chord_quality,
            'root_note': get_note_from_midi(root_midi),
            'root_midi': root_midi,
            'chord_midis': chord_midis,
            'choices': choices,
            'correct_answer': chord_quality,
        }

    def _generate_progression_exercise(self, difficulty: int) -> Dict[str, Any]:
        """Generate a chord progression recognition exercise."""
        progression_name = random.choice(list(self.PROGRESSIONS.keys()))
        progression = self.PROGRESSIONS[progression_name]

        # Random key
        key = random.choice(CHROMATIC_KEYS)
        root_midi = random.randint(36, 60)

        # Create answer choices
        all_progressions = list(self.PROGRESSIONS.keys())
        choices = [progression_name]
        while len(choices) < 4:
            distractor = random.choice(all_progressions)
            if distractor not in choices:
                choices.append(distractor)
        random.shuffle(choices)

        return {
            'id': generate_id(),
            'mode': 'ear_training',
            'exercise_type': 'progression',
            'difficulty': difficulty,
            'progression_name': progression_name,
            'progression': progression,
            'key': key,
            'root_midi': root_midi,
            'choices': choices,
            'correct_answer': progression_name,
        }

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple ear training exercises."""
        return [self.generate(difficulty) for _ in range(count)]


# ===== RHYTHM DICTATION GENERATOR =====

class RhythmDictationGenerator:
    """Generate rhythm dictation exercises."""

    # Rhythm notation: 1.0 = quarter note, 0.5 = eighth, 2.0 = half, etc.
    SIMPLE_PATTERNS = [
        [1.0, 1.0, 1.0, 1.0],  # Four quarters
        [2.0, 2.0],  # Two halves
        [0.5, 0.5, 1.0, 1.0, 1.0],  # Two eighths, three quarters
        [1.0, 0.5, 0.5, 1.0, 1.0],  # Quarter, two eighths, two quarters
    ]

    INTERMEDIATE_PATTERNS = [
        [1.0, 0.5, 0.5, 0.5, 0.5, 1.0],  # Syncopation
        [0.5, 0.5, 0.5, 0.5, 1.0, 1.0],  # Four eighths, two quarters
        [1.5, 0.5, 1.0, 1.0],  # Dotted quarter patterns
        [0.25, 0.25, 0.5, 1.0, 1.0, 1.0],  # Sixteenth note intro
    ]

    ADVANCED_PATTERNS = [
        [0.25, 0.25, 0.25, 0.25, 0.5, 0.5, 1.0, 1.0],  # Complex sixteenths
        [1.0, 0.333, 0.333, 0.333, 1.0],  # Triplet pattern
        [0.5, 1.0, 0.5, 0.5, 0.5, 1.0],  # Syncopated eighths
        [1.5, 0.25, 0.25, 1.0, 1.0],  # Mixed dotted/sixteenths
    ]

    def generate(self, difficulty: int) -> Dict[str, Any]:
        """Generate a rhythm dictation exercise."""
        # Choose pattern pool based on difficulty
        if difficulty <= 3:
            pattern_pool = self.SIMPLE_PATTERNS
        elif difficulty <= 7:
            pattern_pool = self.SIMPLE_PATTERNS + self.INTERMEDIATE_PATTERNS
        else:
            pattern_pool = self.INTERMEDIATE_PATTERNS + self.ADVANCED_PATTERNS

        pattern = random.choice(pattern_pool)

        # Tempo scales with difficulty
        base_tempo = max(60, 100 - (difficulty * 5))
        tempo = random.randint(base_tempo - 10, base_tempo + 10)

        # Generate answer choices (correct pattern + 3 similar distractors)
        choices = [pattern]

        # Create distractors by slightly modifying the pattern
        for _ in range(3):
            distractor = self._create_distractor(pattern)
            if distractor not in choices:
                choices.append(distractor)

        # Pad to 4 choices if needed
        while len(choices) < 4:
            distractor = random.choice(pattern_pool)
            if distractor not in choices:
                choices.append(distractor)

        random.shuffle(choices)

        return {
            'id': generate_id(),
            'mode': 'rhythm_dictation',
            'difficulty': difficulty,
            'tempo': tempo,
            'pattern': pattern,
            'beats_per_measure': 4,
            'choices': choices,
            'correct_answer': choices.index(pattern),
        }

    def _create_distractor(self, pattern: List[float]) -> List[float]:
        """Create a similar but different rhythm pattern."""
        distractor = pattern.copy()

        # Randomly swap two adjacent notes
        if len(distractor) > 1:
            idx = random.randint(0, len(distractor) - 2)
            distractor[idx], distractor[idx + 1] = distractor[idx + 1], distractor[idx]

        return distractor

    def generate_batch(self, count: int, difficulty: int, options: Dict = None) -> List[Dict[str, Any]]:
        """Generate multiple rhythm dictation exercises."""
        return [self.generate(difficulty) for _ in range(count)]
