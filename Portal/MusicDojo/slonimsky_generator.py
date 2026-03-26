"""
Slonimsky Pattern Generator
Generates musical patterns based on Nicolas Slonimsky's Thesaurus of Scales
and Melodic Patterns, with optimal guitar fingering via Viterbi algorithm.
"""

# Standard tuning open string MIDI values: E2, A2, D3, G3, B3, E4
OPEN_STRINGS = [40, 45, 50, 55, 59, 64]
STRING_NAMES = ['E2', 'A2', 'D3', 'G3', 'B3', 'E4']
MAX_FRET = 24

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

DIVISIONS = {
    'tritone':    {'semitones': 6,  'name': 'Tritone'},
    'ditone':     {'semitones': 4,  'name': 'Ditone'},
    'sesquitone': {'semitones': 3,  'name': 'Sesquitone'},
    'whole_tone': {'semitones': 2,  'name': 'Whole Tone'},
    'semitone':   {'semitones': 1,  'name': 'Semitone'},
}

# Interpolation types: list of semitone offsets inserted between principal tones
INTERPOLATIONS = {
    '1':  {'offsets': [1],     'name': '+1 Ascending'},
    '2':  {'offsets': [1, 2],  'name': '+2 Ascending'},
    '3':  {'offsets': [1, 2, 3], 'name': '+3 Ascending'},
    '-1': {'offsets': [-1],    'name': '-1 Descending'},
    '-2': {'offsets': [-1, -2], 'name': '-2 Descending'},
}


def midi_to_note_name(midi):
    """Convert MIDI number to note name with octave (e.g., 60 -> 'C4')."""
    octave = (midi // 12) - 1
    note = NOTE_NAMES[midi % 12]
    return f"{note}{octave}"


def midi_to_vex_key(midi):
    """Convert MIDI number to VexFlow key format (e.g., 60 -> 'c/4')."""
    octave = (midi // 12) - 1
    note = NOTE_NAMES[midi % 12].lower().replace('#', '#')
    return f"{note}/{octave}"


def generate_pitch_sequence(start_midi, division_semitones, interpolation_offsets):
    """
    Generate a pitch sequence using Slonimsky's system.

    Args:
        start_midi: Starting MIDI note number
        division_semitones: Interval between principal tones
        interpolation_offsets: List of semitone offsets to insert between principals

    Returns:
        List of MIDI note numbers
    """
    sequence = []
    # Generate principal tones spanning 2 octaves (24 semitones)
    current = start_midi
    principals = []
    while current <= start_midi + 24:
        principals.append(current)
        current += division_semitones

    # Insert interpolation notes between each pair of principal tones
    for i, principal in enumerate(principals):
        sequence.append(principal)
        # Add interpolation notes (except after the last principal)
        if i < len(principals) - 1:
            for offset in interpolation_offsets:
                interp_note = principal + offset
                # Keep interpolation within range
                if start_midi - 12 <= interp_note <= start_midi + 36:
                    sequence.append(interp_note)

    return sequence


def get_fretboard_positions(midi_note):
    """
    Find all (string, fret) positions for a MIDI note on the guitar.

    Returns:
        List of (string_index, fret) tuples
    """
    positions = []
    for s, open_midi in enumerate(OPEN_STRINGS):
        fret = midi_note - open_midi
        if 0 <= fret <= MAX_FRET:
            positions.append((s, fret))
    return positions


def optimize_fingering(midi_sequence):
    """
    Find the optimal guitar fingering using Viterbi (dynamic programming).

    Cost function penalizes:
    - Large fret jumps (especially > 4 frets)
    - String skipping
    - Leaving a 4-fret position box

    Returns:
        List of {"midi": N, "string": S, "fret": F} dicts
    """
    if not midi_sequence:
        return []

    # Build states: for each note, list all possible positions
    all_positions = []
    for midi in midi_sequence:
        positions = get_fretboard_positions(midi)
        if not positions:
            # Note not playable on guitar - skip it
            continue
        all_positions.append((midi, positions))

    if not all_positions:
        return []

    # Viterbi forward pass
    n = len(all_positions)

    # cost[i][j] = minimum cost to reach position j of note i
    # prev[i][j] = index of best previous position
    cost = [{} for _ in range(n)]
    prev = [{} for _ in range(n)]

    # Initialize first note (all positions have 0 cost)
    for j, pos in enumerate(all_positions[0][1]):
        cost[0][j] = 0
        prev[0][j] = -1

    # Fill forward
    for i in range(1, n):
        for j, (s_j, f_j) in enumerate(all_positions[i][1]):
            best_cost = float('inf')
            best_prev = 0

            for k, (s_k, f_k) in enumerate(all_positions[i - 1][1]):
                # Fret distance cost
                fret_dist = abs(f_j - f_k)
                if fret_dist <= 4:
                    fret_cost = fret_dist * 1.0
                elif fret_dist <= 7:
                    fret_cost = fret_dist * 3.0
                else:
                    fret_cost = fret_dist * 8.0

                # String skip cost
                string_dist = abs(s_j - s_k)
                string_cost = string_dist * 2.0
                if string_dist > 2:
                    string_cost += (string_dist - 2) * 5.0

                # Position box reward (same 4-fret span)
                box_start = max(0, f_k - 1)
                box_end = box_start + 4
                if box_start <= f_j <= box_end:
                    box_bonus = -1.0
                else:
                    box_bonus = 2.0

                total = cost[i - 1][k] + fret_cost + string_cost + box_bonus

                if total < best_cost:
                    best_cost = total
                    best_prev = k

            cost[i][j] = best_cost
            prev[i][j] = best_prev

    # Backtrace
    # Find best ending position
    last_costs = cost[n - 1]
    best_end = min(last_costs, key=last_costs.get)

    path = [0] * n
    path[n - 1] = best_end
    for i in range(n - 2, -1, -1):
        path[i] = prev[i + 1][path[i + 1]]

    # Build result
    result = []
    for i in range(n):
        midi = all_positions[i][0]
        s, f = all_positions[i][1][path[i]]
        result.append({
            "midi": midi,
            "string": s,
            "fret": f,
            "note_name": midi_to_note_name(midi),
            "vex_key": midi_to_vex_key(midi),
            "string_name": STRING_NAMES[s]
        })

    return result


def generate_pattern(division_key, interpolation_key, start_midi=48):
    """
    Generate a complete Slonimsky pattern with optimal guitar fingering.

    Args:
        division_key: Key into DIVISIONS dict (e.g., 'tritone')
        interpolation_key: Key into INTERPOLATIONS dict (e.g., '1')
        start_midi: Starting MIDI note (default 48 = C3)

    Returns:
        Dict with pattern metadata, MIDI sequence, and guitar fingering
    """
    division = DIVISIONS[division_key]
    interpolation = INTERPOLATIONS[interpolation_key]

    midi_sequence = generate_pitch_sequence(
        start_midi,
        division['semitones'],
        interpolation['offsets']
    )

    guitar_fingering = optimize_fingering(midi_sequence)

    pattern_id = f"{division_key}_{interpolation_key.replace('-', 'neg')}"

    return {
        "id": pattern_id,
        "name": f"{division['name']} Progression, {interpolation['name']}",
        "division": division_key,
        "division_semitones": division['semitones'],
        "interpolation": interpolation['offsets'],
        "interpolation_key": interpolation_key,
        "direction": "descending" if interpolation['offsets'][0] < 0 else "ascending",
        "midi_sequence": midi_sequence,
        "note_names": [midi_to_note_name(m) for m in midi_sequence],
        "vex_keys": [midi_to_vex_key(m) for m in midi_sequence],
        "guitar_fingering": guitar_fingering,
    }


def generate_all_patterns(start_midi=48):
    """Generate all division × interpolation combinations."""
    patterns = []
    for div_key in DIVISIONS:
        for interp_key in INTERPOLATIONS:
            pattern = generate_pattern(div_key, interp_key, start_midi)
            patterns.append(pattern)
    return patterns
