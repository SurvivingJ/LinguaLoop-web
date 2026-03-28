import random
from typing import List, Dict, Any


# ===== MUSIC DATA =====

CHROMATIC_KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

SCALE_DEFINITIONS = {
    # Diatonic Modes
    'Major': [0, 2, 4, 5, 7, 9, 11],
    'Natural Minor': [0, 2, 3, 5, 7, 8, 10],
    'Dorian': [0, 2, 3, 5, 7, 9, 10],
    'Phrygian': [0, 1, 3, 5, 7, 8, 10],
    'Lydian': [0, 2, 4, 6, 7, 9, 11],
    'Mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'Locrian': [0, 1, 3, 5, 6, 8, 10],
    # Minor Variants
    'Harmonic Minor': [0, 2, 3, 5, 7, 8, 11],
    'Melodic Minor': [0, 2, 3, 5, 7, 9, 11],
    'Jazz Minor': [0, 2, 3, 5, 7, 9, 11],
    # Jazz / Modern
    'Lydian Dominant': [0, 2, 4, 6, 7, 9, 10],
    'Altered': [0, 1, 3, 4, 6, 8, 10],
    'Phrygian Dominant': [0, 1, 4, 5, 7, 8, 10],
    'Dominant Bebop': [0, 2, 4, 5, 7, 9, 10, 11],
    # Symmetric
    'Whole Tone': [0, 2, 4, 6, 8, 10],
    'Diminished HW': [0, 1, 3, 4, 6, 7, 9, 10],
    # Pentatonic / Blues
    'Pentatonic Major': [0, 2, 4, 7, 9],
    'Pentatonic Minor': [0, 3, 5, 7, 10],
    'Blues': [0, 3, 5, 6, 7, 10],
    # Bebop
    'Major Bebop': [0, 2, 4, 5, 7, 8, 9, 11],
    'Minor Bebop': [0, 2, 3, 5, 7, 8, 9, 10],
    # Symmetric / Exotic Western
    'Whole-Half Diminished': [0, 2, 3, 5, 6, 8, 9, 11],
    'Prometheus': [0, 2, 4, 6, 9, 10],
    'Enigmatic': [0, 1, 4, 6, 8, 10, 11],
    'Persian': [0, 1, 4, 5, 6, 8, 11],
    'Byzantine': [0, 1, 4, 5, 7, 8, 11],
    'Neapolitan Minor': [0, 1, 3, 5, 7, 8, 11],
    'Neapolitan Major': [0, 1, 3, 5, 7, 9, 11],
    # World / Ethnic
    'Hungarian Minor': [0, 2, 3, 6, 7, 8, 11],
    'Hungarian Major': [0, 3, 4, 6, 7, 9, 10],
    'Romanian Major': [0, 1, 4, 6, 7, 9, 10],
    'Arabian': [0, 2, 4, 5, 6, 8, 10],
    'Asian': [0, 1, 4, 5, 6, 9, 10],
    'Javanese Pelog': [0, 1, 3, 5, 7, 9, 10],
    # Japanese Pentatonic
    'Hirajoshi': [0, 2, 3, 7, 8],
    'In Sen': [0, 1, 5, 7, 10],
    'Iwato': [0, 1, 5, 6, 10],
    'Kumoi': [0, 2, 5, 7, 8],
    'Balinese Pelog': [0, 1, 3, 7, 8],
    # Other Pentatonics
    'Dominant Pentatonic': [0, 2, 4, 7, 10],
    'Egyptian': [0, 2, 5, 7, 10],
    'Scottish Pentatonic': [0, 2, 5, 7, 9],
}

SCALE_CATEGORIES = {
    'beginner': ['Major', 'Natural Minor', 'Pentatonic Major', 'Pentatonic Minor'],
    'common': ['Major', 'Natural Minor', 'Harmonic Minor', 'Melodic Minor', 'Pentatonic Major', 'Pentatonic Minor', 'Blues'],
    'jazz': ['Dorian', 'Lydian', 'Mixolydian', 'Altered', 'Jazz Minor', 'Lydian Dominant', 'Whole Tone', 'Diminished HW'],
    'bebop': ['Dominant Bebop', 'Major Bebop', 'Minor Bebop'],
    'world': ['Hungarian Minor', 'Hungarian Major', 'Byzantine', 'Persian', 'Romanian Major',
              'Arabian', 'Asian', 'Javanese Pelog', 'Neapolitan Minor', 'Neapolitan Major'],
    'japanese': ['Hirajoshi', 'In Sen', 'Iwato', 'Kumoi', 'Balinese Pelog'],
    'symmetric': ['Whole Tone', 'Diminished HW', 'Whole-Half Diminished', 'Prometheus', 'Enigmatic'],
    'pentatonic_ext': ['Dominant Pentatonic', 'Egyptian', 'Scottish Pentatonic'],
}

SCALE_METADATA = {
    # Beginner
    'Major':              {'category': 'Beginner',  'mood': 'Bright, Happy',         'difficulty': 'beginner',      'chords': ['maj', 'maj7', 'maj9']},
    'Natural Minor':      {'category': 'Beginner',  'mood': 'Sad, Dark',             'difficulty': 'beginner',      'chords': ['min', 'min7']},
    'Pentatonic Major':   {'category': 'Beginner',  'mood': 'Open, Cheerful',        'difficulty': 'beginner',      'chords': ['maj', 'maj7', '6']},
    'Pentatonic Minor':   {'category': 'Beginner',  'mood': 'Bluesy, Soulful',       'difficulty': 'beginner',      'chords': ['min', 'min7', '7']},
    # Common
    'Harmonic Minor':     {'category': 'Common',    'mood': 'Classical, Dramatic',    'difficulty': 'intermediate',  'chords': ['min(maj7)', 'dim7']},
    'Melodic Minor':      {'category': 'Common',    'mood': 'Smooth, Jazz',           'difficulty': 'intermediate',  'chords': ['min(maj7)', 'min6']},
    'Blues':              {'category': 'Common',    'mood': 'Gritty, Expressive',     'difficulty': 'beginner',      'chords': ['7', 'min7', '9']},
    # Diatonic Modes
    'Dorian':            {'category': 'Jazz',       'mood': 'Cool, Mellow',           'difficulty': 'intermediate',  'chords': ['min7', 'min9', 'min13']},
    'Phrygian':          {'category': 'Jazz',       'mood': 'Spanish, Dark',          'difficulty': 'intermediate',  'chords': ['min7', 'sus4b9']},
    'Lydian':            {'category': 'Jazz',       'mood': 'Dreamy, Floating',       'difficulty': 'intermediate',  'chords': ['maj7#11', 'maj9']},
    'Mixolydian':        {'category': 'Jazz',       'mood': 'Bluesy, Rock',           'difficulty': 'intermediate',  'chords': ['7', '9', '13']},
    'Locrian':           {'category': 'Jazz',       'mood': 'Unstable, Tense',        'difficulty': 'advanced',      'chords': ['min7b5', 'dim']},
    # Jazz / Modern
    'Jazz Minor':        {'category': 'Jazz',       'mood': 'Smooth, Modern',         'difficulty': 'advanced',      'chords': ['min(maj7)']},
    'Lydian Dominant':   {'category': 'Jazz',       'mood': 'Bright, Tension',        'difficulty': 'advanced',      'chords': ['7#11', 'bII7']},
    'Altered':           {'category': 'Jazz',       'mood': 'Tense, Chromatic',       'difficulty': 'advanced',      'chords': ['7alt', '7#9b13']},
    'Phrygian Dominant': {'category': 'Jazz',       'mood': 'Flamenco, Exotic',       'difficulty': 'advanced',      'chords': ['V7', '7b9']},
    # Bebop
    'Dominant Bebop':    {'category': 'Bebop',      'mood': 'Swinging, Chromatic',    'difficulty': 'advanced',      'chords': ['7', '9', '13']},
    'Major Bebop':       {'category': 'Bebop',      'mood': 'Swinging, Bright',       'difficulty': 'advanced',      'chords': ['maj7', 'maj6']},
    'Minor Bebop':       {'category': 'Bebop',      'mood': 'Swinging, Dark',         'difficulty': 'advanced',      'chords': ['min7', 'min9']},
    # Symmetric
    'Whole Tone':        {'category': 'Symmetric',  'mood': 'Dreamy, Impressionist',  'difficulty': 'intermediate',  'chords': ['7#5', 'aug']},
    'Diminished HW':     {'category': 'Symmetric',  'mood': 'Tense, Angular',         'difficulty': 'advanced',      'chords': ['dim7', '7b9']},
    'Whole-Half Diminished': {'category': 'Symmetric', 'mood': 'Eerie, Symmetrical',  'difficulty': 'advanced',      'chords': ['dim7']},
    'Prometheus':        {'category': 'Symmetric',  'mood': 'Other-worldly, Mystic',  'difficulty': 'advanced',      'chords': ['7#11']},
    'Enigmatic':         {'category': 'Symmetric',  'mood': 'Chromatic, Intense',     'difficulty': 'advanced',      'chords': []},
    # World / Ethnic
    'Persian':           {'category': 'World',      'mood': 'Middle Eastern, Tense',  'difficulty': 'advanced',      'chords': ['maj', 'maj7']},
    'Byzantine':         {'category': 'World',      'mood': 'Majestic, Eastern',      'difficulty': 'advanced',      'chords': ['maj', '7b9']},
    'Neapolitan Minor':  {'category': 'World',      'mood': 'Dark, Classical',        'difficulty': 'advanced',      'chords': ['min(maj7)', 'dim']},
    'Neapolitan Major':  {'category': 'World',      'mood': 'Warm, Classical',        'difficulty': 'advanced',      'chords': ['maj7', 'bIImaj7']},
    'Hungarian Minor':   {'category': 'World',      'mood': 'Dark, Exotic',           'difficulty': 'advanced',      'chords': ['min(maj7)', 'dim7']},
    'Hungarian Major':   {'category': 'World',      'mood': 'Dominant, Exotic',       'difficulty': 'advanced',      'chords': ['7', '7b9']},
    'Romanian Major':    {'category': 'World',      'mood': 'Tense, Lydian',          'difficulty': 'advanced',      'chords': ['7', '7#11']},
    'Arabian':           {'category': 'World',      'mood': 'Desert, Mysterious',     'difficulty': 'advanced',      'chords': ['7b5', '7b13']},
    'Asian':             {'category': 'World',      'mood': 'Eastern, Minor',         'difficulty': 'advanced',      'chords': ['min', 'sus4']},
    'Javanese Pelog':    {'category': 'World',      'mood': 'Indonesian, Soft',       'difficulty': 'intermediate',  'chords': ['min7', 'sus2']},
    # Japanese Pentatonic
    'Hirajoshi':         {'category': 'Japanese',   'mood': 'Sparse, Mysterious',     'difficulty': 'intermediate',  'chords': ['min', 'min7', 'sus4']},
    'In Sen':            {'category': 'Japanese',   'mood': 'Dark, Stark',            'difficulty': 'intermediate',  'chords': ['min7', 'sus4']},
    'Iwato':             {'category': 'Japanese',   'mood': 'Dissonant, Haunting',    'difficulty': 'intermediate',  'chords': ['min7b5']},
    'Kumoi':             {'category': 'Japanese',   'mood': 'Gentle, Wistful',        'difficulty': 'intermediate',  'chords': ['min', 'sus4']},
    'Balinese Pelog':    {'category': 'Japanese',   'mood': 'Exotic, Mystical',       'difficulty': 'intermediate',  'chords': ['min', 'sus2']},
    # Other Pentatonics
    'Dominant Pentatonic': {'category': 'Pentatonic', 'mood': 'Bluesy, Dominant',     'difficulty': 'intermediate',  'chords': ['7', '9']},
    'Egyptian':          {'category': 'Pentatonic', 'mood': 'Open, Suspended',        'difficulty': 'beginner',      'chords': ['sus2', 'sus4']},
    'Scottish Pentatonic': {'category': 'Pentatonic', 'mood': 'Open, Folkloric',      'difficulty': 'beginner',      'chords': ['sus2', '5']},
}

PATTERN_DEFINITIONS = {
    # Classical / Beginner
    'Block Chords': {'sequence': [[1, 3, 5]], 'desc': 'All chord tones simultaneously', 'vibe': ['all']},
    'Alberti Bass': {'sequence': [1, 5, 3, 5], 'desc': 'Root-fifth-third-fifth pattern', 'vibe': ['classical', 'beginner']},
    'Waltz': {'sequence': [1, [3, 5], [3, 5]], 'desc': 'Classic 3/4 oom-pah-pah', 'vibe': ['classical', 'romantic']},
    'Arpeggio Up': {'sequence': [1, 3, 5, 8], 'desc': 'Rising broken chord', 'vibe': ['all']},
    'Arpeggio Down': {'sequence': [8, 5, 3, 1], 'desc': 'Falling broken chord', 'vibe': ['all']},
    # Jazz
    'Walking Bass': {'sequence': [1, 2, 3, 5], 'desc': 'Stepwise ascending movement', 'vibe': ['jazz', 'swing']},
    'Stride': {'sequence': [1, [3, 5, 8]], 'desc': 'Low bass then mid-range chord', 'vibe': ['jazz', 'ragtime']},
    'Shell Voicing': {'sequence': [[1, 7]], 'desc': 'Root + 7th only (Bud Powell style)', 'vibe': ['jazz', 'bebop']},
    'Shell Voicing Alt': {'sequence': [[1, 3]], 'desc': 'Root + 3rd shell variation', 'vibe': ['jazz', 'bebop']},
    'Rootless A': {'sequence': [[3, 5, 7, 9]], 'desc': 'Bill Evans-style 3-5-7-9 voicing', 'vibe': ['jazz', 'voicing']},
    'Rootless B': {'sequence': [[7, 9, 3, 5]], 'desc': 'Inverted rootless 7-9-3-5 voicing', 'vibe': ['jazz', 'voicing']},
    'Quartal Voicing': {'sequence': [[1, 4, 7]], 'desc': 'Stacked 4ths (McCoy Tyner)', 'vibe': ['jazz', 'modal', 'voicing']},
    'Quartal Quartal': {'sequence': [[4, 7, 3]], 'desc': 'Wider quartal stack', 'vibe': ['jazz', 'modal', 'voicing']},
    # Boogie / Blues
    'Boogie Shuffle': {'sequence': [1, 5, 6, 5], 'desc': 'Root-fifth-sixth-fifth swing pattern', 'vibe': ['boogie', 'blues']},
    'Boogie Chop': {'sequence': [1, 8, 1, 8], 'desc': 'Octave jump country/rock boogie', 'vibe': ['boogie', 'rock']},
    'Boogie Ascending': {'sequence': [1, 2, 3, 4, 5, 6, 5, 3], 'desc': 'Walking chromatic climb, back to 5', 'vibe': ['boogie', 'blues']},
    '12-Bar Groove': {'sequence': [1, 5, 1, 5, [1, 5], [1, 5]], 'desc': 'Alternating bass + power chord hits', 'vibe': ['boogie', 'blues', 'rock']},
    'Shuffle Split': {'sequence': [1, [3, 5], 1, [3, 5]], 'desc': 'Low root, staccato chord hits', 'vibe': ['boogie', 'blues']},
    # Funk / Gospel
    'Gospel Chop': {'sequence': [[1, 5], [3, 7], [1, 5], [3, 7, 9]], 'desc': 'Alternating bass chord + extension', 'vibe': ['gospel', 'soul']},
    'Funk Stab': {'sequence': [[1, 3, 7], 0, [1, 3, 7], 0], 'desc': 'Chord stabs with rests', 'vibe': ['funk', 'r&b']},
    'Syncopated Bass': {'sequence': [1, 0, 5, 1, 0, 5, 3, 5], 'desc': 'Off-beat bass movement', 'vibe': ['funk', 'pop']},
    'New Orleans': {'sequence': [1, 3, 5, 3, [1, 5], 3, 5, 3], 'desc': 'Circular bass phrase', 'vibe': ['blues', 'gospel']},
    # Latin
    'Bossa Nova': {'sequence': [1, 5, 8, 5, 1, 5, 3, 5], 'desc': 'Syncopated Latin rhythm', 'vibe': ['latin', 'jazz']},
    'Montuno': {'sequence': [1, 3, 5, 3, 8, 5, 3, 5], 'desc': 'Cuban repeated figure', 'vibe': ['latin', 'salsa']},
    'Songo': {'sequence': [1, 0, 5, 0, [1, 5], 0, 3, 0], 'desc': 'Afro-Cuban with rests', 'vibe': ['latin', 'afrocuban']},
    'Cha-Cha': {'sequence': [1, 1, 5, 5, 1, 0, 5, 0], 'desc': 'Steady cha-cha-cha feel', 'vibe': ['latin', 'pop']},
    'Mambo Bass': {'sequence': [1, 5, 8, 5, 1, 0, 8, 5], 'desc': 'Driving mambo left hand', 'vibe': ['latin', 'salsa']},
    # Ostinato / Drone
    'Open Fifth Ostinato': {'sequence': [[1, 5], [1, 5], [1, 5], [1, 5]], 'desc': 'Power-chord drone', 'vibe': ['modal', 'rock', 'drone']},
    'Two-Note Bass Vamp': {'sequence': [1, 0, 1, 0, 5, 0, 5, 0], 'desc': 'Alternating root/fifth pedal point', 'vibe': ['modal', 'drone']},
    'Pedal Bass': {'sequence': [1, 1, 1, 1], 'desc': 'Static bass note tension builder', 'vibe': ['modal', 'drone']},
    'Rhumba Clave': {'sequence': [1, 0, 0, 5, 0, 1, 0, 0], 'desc': '3-2 clave feel in bass', 'vibe': ['latin', 'afrocuban']},
}

PATTERN_CATEGORIES = {
    'Classical':    ['Block Chords', 'Alberti Bass', 'Waltz', 'Arpeggio Up', 'Arpeggio Down'],
    'Jazz':         ['Walking Bass', 'Stride', 'Shell Voicing', 'Shell Voicing Alt'],
    'Voicings':     ['Rootless A', 'Rootless B', 'Quartal Voicing', 'Quartal Quartal'],
    'Boogie/Blues': ['Boogie Shuffle', 'Boogie Chop', 'Boogie Ascending', '12-Bar Groove', 'Shuffle Split'],
    'Funk/Gospel':  ['Gospel Chop', 'Funk Stab', 'Syncopated Bass', 'New Orleans'],
    'Latin':        ['Bossa Nova', 'Montuno', 'Songo', 'Cha-Cha', 'Mambo Bass'],
    'Ostinato':     ['Open Fifth Ostinato', 'Two-Note Bass Vamp', 'Pedal Bass', 'Rhumba Clave'],
}

MOTIF_DEFINITIONS = {
    'Rising 3rd': {
        'intervals': [0, 2],
        'rhythm': [1.0, 1.0],
        'direction': 'up',
        'length': 2,
        'desc': 'Simple ascending 3rd — starting cell of hundreds of phrases',
        'style': ['all'],
    },
    'Call Riff': {
        'intervals': [1, 3, 2, 1],
        'rhythm': [0.5, 0.5, 0.5, 1.5],
        'direction': 'mixed',
        'length': 4,
        'desc': 'Classic jazz call figure — resolves back to root',
        'style': ['jazz', 'blues'],
    },
    'Pentatonic Drop': {
        'intervals': [5, 4, 3, 1],
        'rhythm': [0.5, 0.5, 0.5, 0.5],
        'direction': 'down',
        'length': 4,
        'desc': 'Falling pentatonic lick from 5th to root',
        'style': ['rock', 'blues', 'country'],
    },
    'Blues Wail': {
        'intervals': [5, 4, 3, 4, 3],
        'rhythm': [1.0, 0.5, 0.5, 0.5, 1.5],
        'direction': 'mixed',
        'length': 5,
        'desc': 'Bent blues cry — 5 to 4 with linger',
        'style': ['blues'],
    },
    'Jazz Enclosure': {
        'intervals': [3, 1, 2, 3],
        'rhythm': [0.5, 0.5, 0.5, 1.5],
        'direction': 'up',
        'length': 4,
        'desc': 'Approach target from chromatic above + below',
        'style': ['jazz', 'bebop'],
    },
    'Ascending Sequence': {
        'intervals': [1, 2, 3, 2, 3, 4, 3, 4, 5],
        'rhythm': [0.5] * 9,
        'direction': 'up',
        'length': 9,
        'desc': 'Stepwise sequence climbing the scale in overlapping 3rds',
        'style': ['jazz', 'classical'],
    },
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


# ===== MOTIF GENERATOR =====

class MotifGenerator:
    """Generate motifs with transformations for improvisation practice."""

    TRANSFORMATIONS = ['transpose', 'invert', 'retrograde', 'augment',
                       'diminish', 'fragment', 'displace']

    def generate(self, difficulty: int, style: str = 'all') -> Dict[str, Any]:
        """Generate a motif with difficulty-scaled transformations."""
        # Filter motifs by style
        pool = [k for k, v in MOTIF_DEFINITIONS.items()
                if style in v['style'] or 'all' in v['style']]
        if not pool:
            pool = list(MOTIF_DEFINITIONS.keys())

        base_name = random.choice(pool)
        base = MOTIF_DEFINITIONS[base_name]

        # Apply transformations based on difficulty
        n_transforms = min(difficulty // 3, len(self.TRANSFORMATIONS))
        transforms = random.sample(self.TRANSFORMATIONS, n_transforms) if n_transforms > 0 else []

        result_intervals = base['intervals'][:]
        result_rhythm = base['rhythm'][:]

        for t in transforms:
            if t == 'transpose':
                shift = random.choice([-2, -1, 1, 2])
                result_intervals = [x + shift for x in result_intervals]
            elif t == 'invert':
                result_intervals = [-x for x in result_intervals]
            elif t == 'retrograde':
                result_intervals = result_intervals[::-1]
                result_rhythm = result_rhythm[::-1]
            elif t == 'augment':
                result_rhythm = [r * 2 for r in result_rhythm]
            elif t == 'diminish':
                result_rhythm = [r / 2 for r in result_rhythm]
            elif t == 'fragment':
                n = max(2, len(result_intervals) // 2)
                result_intervals = result_intervals[:n]
                result_rhythm = result_rhythm[:n]
            elif t == 'displace':
                result_intervals = result_intervals[1:] + result_intervals[:1]

        return {
            'base_motif': base_name,
            'transforms_applied': transforms,
            'intervals': result_intervals,
            'rhythm': result_rhythm,
            'description': base['desc'],
            'direction': base['direction'],
            'style': style,
        }


# ===== SCALE/PATTERN GENERATOR =====

class ScalePatternGenerator:
    """Generate jazz improvisation scale/pattern combinations."""

    def __init__(self):
        self._motif_gen = MotifGenerator()

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

        result = {
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

        # Include motif for difficulty >= 4
        if difficulty >= 4:
            motif = self._motif_gen.generate(difficulty)
            result['motif'] = motif

        return result

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
