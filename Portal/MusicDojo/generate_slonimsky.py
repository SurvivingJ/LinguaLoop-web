"""
One-time script to generate slonimsky_library.json.
Run: python generate_slonimsky.py
Output: static/data/slonimsky_library.json
"""
import json
import os
from slonimsky_generator import generate_all_patterns

def main():
    print("Generating Slonimsky patterns...")
    patterns = generate_all_patterns(start_midi=48)  # Start at C3

    # Ensure output directory exists
    output_dir = os.path.join('static', 'data')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'slonimsky_library.json')

    with open(output_path, 'w') as f:
        json.dump({
            "version": "1.0",
            "root_midi": 48,
            "root_note": "C3",
            "total_patterns": len(patterns),
            "patterns": patterns
        }, f, indent=2)

    print(f"Generated {len(patterns)} patterns -> {output_path}")

    # Print summary
    for p in patterns:
        fingering_count = len(p['guitar_fingering'])
        notes_count = len(p['midi_sequence'])
        print(f"  {p['id']}: {p['name']} ({notes_count} notes, {fingering_count} fingerings)")

if __name__ == '__main__':
    main()
