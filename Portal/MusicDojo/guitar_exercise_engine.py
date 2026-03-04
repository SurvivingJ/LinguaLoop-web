"""
Guitar Exercise Engine - 52 Exercises with BPM Progression
Implements 10% BPM rule and advancement logic
"""

import math
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class DifficultyTier(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Subdivision(Enum):
    QUARTER = "quarter"
    EIGHTH = "eighth"
    SIXTEENTH = "sixteenth"
    SEXTUPLET = "sextuplet"


class Category(Enum):
    CHROMATIC = "chromatic"
    SCALES = "scales"
    LEGATO = "legato"
    TRILLS = "trills"
    ALTERNATE_PICKING = "alternate_picking"
    ECONOMY_SWEEP = "economy_sweep"
    STRING_SKIPPING = "string_skipping"
    BENDING_VIBRATO = "bending_vibrato"
    CHORD_TRANSITIONS = "chord_transitions"
    PALM_MUTING = "palm_muting"


@dataclass
class GuitarExercise:
    """Individual guitar exercise definition"""
    id: str
    name: str
    category: str
    description: str
    difficulty_tier: str
    subdivision_default: str
    bpm_floor: int
    bpm_ceiling: int
    specific_params: Dict
    benchmark_table: Dict


class GuitarExerciseGenerator:
    """Generate and manage guitar exercises with progression logic"""

    def __init__(self):
        self.exercises = self._initialize_exercises()

    def _initialize_exercises(self) -> List[GuitarExercise]:
        """Define all 52 exercises"""
        exercises = []

        # ===== CATEGORY 1: CHROMATIC/SPIDER WALKS (6 exercises) =====
        exercises.append(GuitarExercise(
            id="chromatic-1234",
            name="Standard Chromatic Walk (1-2-3-4)",
            category=Category.CHROMATIC.value,
            description="Place fingers on four consecutive frets. Play each fret ascending on the low E string, move to the A string, continue across all six strings, then reverse descending. Keep all fingers planted until they need to move.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"pattern": "1-2-3-4", "strings": 6, "fret_position": "1-4"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chromatic-1243",
            name="Chromatic Variation (1-2-4-3)",
            category=Category.CHROMATIC.value,
            description="Strengthens pinky independence by playing it before the ring finger. Same pattern as standard walk but with 1-2-4-3 sequence.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"pattern": "1-2-4-3", "strings": 6, "fret_position": "1-4"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "75-95", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "95-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chromatic-1324",
            name="Chromatic Variation (1-3-2-4)",
            category=Category.CHROMATIC.value,
            description="Targets ring finger independence. Out-of-order sequence challenges coordination.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"pattern": "1-3-2-4", "strings": 6, "fret_position": "1-4"},
            benchmark_table={
                "beginner": {"quarter": "60-70", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "70-90", "sixteenth": "60-70"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "90-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chromatic-4321",
            name="Reverse Chromatic (4-3-2-1)",
            category=Category.CHROMATIC.value,
            description="Descending pattern starting with pinky. Builds pinky strength and reverse motion fluency.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"pattern": "4-3-2-1", "strings": 6, "fret_position": "1-4"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "75-95", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "95-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chromatic-spider-wide",
            name="Wide Spider (1-2-3-4 with stretches)",
            category=Category.CHROMATIC.value,
            description="One-finger-per-fret exercise covering 5+ frets. Builds left-hand stretch and finger independence.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=90,
            specific_params={"pattern": "1-2-3-4", "strings": 6, "fret_position": "1-5"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "65-85", "sixteenth": "50-65"},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "85-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chromatic-spider-ascending",
            name="Ascending Spider (position shifts)",
            category=Category.CHROMATIC.value,
            description="Play 1-2-3-4 on low E, shift up one fret, repeat on A string, continue ascending both strings and frets across the fretboard.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=100,
            specific_params={"pattern": "1-2-3-4", "strings": 6, "fret_position": "shifting"},
            benchmark_table={
                "beginner": {"quarter": "50-70", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "70-90", "sixteenth": "50-70"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "90-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        # ===== CATEGORY 2: SCALE RUNS (5 exercises) =====
        exercises.append(GuitarExercise(
            id="scale-c-major-3nps",
            name="C Major Scale (3-notes-per-string)",
            category=Category.SCALES.value,
            description="Three-octave C major scale using 3-note-per-string fingering. Ascending and descending.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=140,
            specific_params={"scale": "C Major", "pattern": "3nps", "octaves": 3},
            benchmark_table={
                "beginner": {"quarter": "60-90", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "140-170", "eighth": "90-120", "sixteenth": "60-90"},
                "advanced": {"quarter": None, "eighth": "140-170", "sixteenth": "120-140"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "140+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="scale-a-minor-pentatonic",
            name="A Minor Pentatonic (box 1)",
            category=Category.SCALES.value,
            description="Standard box 1 position of A minor pentatonic. Essential for blues/rock improvisation.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=70,
            bpm_ceiling=150,
            specific_params={"scale": "A Minor Pentatonic", "pattern": "box1", "octaves": 2},
            benchmark_table={
                "beginner": {"quarter": "70-100", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "150-180", "eighth": "100-130", "sixteenth": "70-100"},
                "advanced": {"quarter": None, "eighth": "150-180", "sixteenth": "130-150"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "150+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="scale-modes-positions",
            name="Modal Scales (all 7 modes)",
            category=Category.SCALES.value,
            description="Practice Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian in same key.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"scale": "Modes", "pattern": "3nps", "modes": 7},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="scale-harmonic-minor",
            name="Harmonic Minor Scale",
            category=Category.SCALES.value,
            description="Three-octave harmonic minor with characteristic augmented 2nd interval. Essential for neoclassical playing.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=130,
            specific_params={"scale": "Harmonic Minor", "pattern": "3nps", "octaves": 3},
            benchmark_table={
                "beginner": {"quarter": "60-85", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "130-160", "eighth": "85-115", "sixteenth": "60-85"},
                "advanced": {"quarter": None, "eighth": "130-160", "sixteenth": "115-130"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "130+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="scale-symmetrical",
            name="Symmetrical Scales (diminished, whole tone)",
            category=Category.SCALES.value,
            description="Practice diminished (whole-half, half-whole) and whole tone scales for jazz vocabulary.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"scale": "Symmetrical", "pattern": "varied", "octaves": 2},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        # ===== CATEGORY 3: LEGATO (5 exercises) =====
        exercises.append(GuitarExercise(
            id="legato-hammer-on-basic",
            name="Basic Hammer-Ons (single string)",
            category=Category.LEGATO.value,
            description="Hammer-on from open string or fretted note to higher fret on same string. Focus on volume consistency.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"technique": "hammer-on", "strings": 1, "pattern": "ascending"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="legato-pull-off-basic",
            name="Basic Pull-Offs (single string)",
            category=Category.LEGATO.value,
            description="Pull-off from higher to lower fret. Pluck the string downward/sideways with fretting finger for clear tone.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"technique": "pull-off", "strings": 1, "pattern": "descending"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="legato-scale-runs",
            name="Legato Scale Runs (hammer/pull combinations)",
            category=Category.LEGATO.value,
            description="Ascend scale with hammer-ons, descend with pull-offs. Minimal picking, maximum legato flow.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=130,
            specific_params={"technique": "hammer-pull", "scale": "minor pentatonic", "pattern": "full"},
            benchmark_table={
                "beginner": {"quarter": "60-85", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "130-160", "eighth": "85-115", "sixteenth": "60-85"},
                "advanced": {"quarter": None, "eighth": "130-160", "sixteenth": "115-130"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "130+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="legato-triplet-groups",
            name="Triplet Legato Groups",
            category=Category.LEGATO.value,
            description="Three-note groups (pick-hammer-pull) in triplet feel. Common in fusion/shred vocabulary.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"technique": "pick-hammer-pull", "grouping": "triplets", "pattern": "sequential"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "100-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="legato-slide-hybrid",
            name="Slides + Legato Hybrid",
            category=Category.LEGATO.value,
            description="Combine slides with hammer-ons and pull-offs for fluid multi-octave lines.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=110,
            specific_params={"technique": "slide-hammer-pull", "range": "multi-octave", "pattern": "mixed"},
            benchmark_table={
                "beginner": {"quarter": "50-70", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "70-90", "sixteenth": "50-70"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "90-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        # ===== CATEGORY 4: TRILLS (5 exercises) =====
        exercises.append(GuitarExercise(
            id="trill-1-2-basic",
            name="Basic Trill (1-2 fingers)",
            category=Category.TRILLS.value,
            description="Rapid alternation between index and middle finger on adjacent frets. Start slowly, build endurance.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"fingers": "1-2", "duration": "4 beats", "pattern": "sustained"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": "40-60", "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "75-95", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "95-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="trill-2-3-basic",
            name="Basic Trill (2-3 fingers)",
            category=Category.TRILLS.value,
            description="Middle and ring finger trill. Challenges ring finger strength and speed.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=50,
            bpm_ceiling=90,
            specific_params={"fingers": "2-3", "duration": "4 beats", "pattern": "sustained"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": "35-50", "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "65-85", "sixteenth": "50-65"},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "85-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="trill-3-4-advanced",
            name="Advanced Trill (3-4 fingers)",
            category=Category.TRILLS.value,
            description="Ring and pinky trill. Most challenging due to pinky weakness. Limit duration to prevent injury.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=40,
            bpm_ceiling=80,
            specific_params={"fingers": "3-4", "duration": "4 beats", "pattern": "sustained", "safety": "rest recommended"},
            benchmark_table={
                "beginner": {"quarter": "40-55", "eighth": "30-40", "sixteenth": None},
                "intermediate": {"quarter": "80-95", "eighth": "55-70", "sixteenth": "40-55"},
                "advanced": {"quarter": None, "eighth": "80-95", "sixteenth": "70-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="trill-cross-string",
            name="Cross-String Trill",
            category=Category.TRILLS.value,
            description="Trill between notes on different strings. Synchronizes left and right hand for string changes during trills.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=40,
            bpm_ceiling=70,
            specific_params={"fingers": "varied", "strings": 2, "pattern": "cross-string"},
            benchmark_table={
                "beginner": {"quarter": "40-50", "eighth": "30-40", "sixteenth": None},
                "intermediate": {"quarter": "70-85", "eighth": "50-65", "sixteenth": "40-50"},
                "advanced": {"quarter": None, "eighth": "70-85", "sixteenth": "65-70"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "70+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="trill-endurance",
            name="Trill Endurance Challenge",
            category=Category.TRILLS.value,
            description="Sustain 1-2 trill for 8+ bars. Builds stamina and independence for musical application.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=60,
            bpm_ceiling=90,
            specific_params={"fingers": "1-2", "duration": "8+ bars", "pattern": "endurance"},
            benchmark_table={
                "beginner": {"quarter": "60-70", "eighth": "40-60", "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "70-85", "sixteenth": "60-70"},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "85-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        # ===== CATEGORY 5: ALTERNATE PICKING (5 exercises) =====
        exercises.append(GuitarExercise(
            id="alt-pick-single-string",
            name="Single String Alternate Picking",
            category=Category.ALTERNATE_PICKING.value,
            description="Strict down-up motion on one string. Foundation for all picking technique.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=140,
            specific_params={"pattern": "down-up", "strings": 1, "motion": "strict"},
            benchmark_table={
                "beginner": {"quarter": "60-90", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "140-170", "eighth": "90-120", "sixteenth": "60-90"},
                "advanced": {"quarter": None, "eighth": "140-170", "sixteenth": "120-140"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "140+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="alt-pick-chromatic",
            name="Alternate Picking Chromatic",
            category=Category.ALTERNATE_PICKING.value,
            description="1-2-3-4 chromatic with strict alternate picking. Synchronizes left-right hand.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=130,
            specific_params={"pattern": "1-2-3-4", "strings": 6, "motion": "alternate"},
            benchmark_table={
                "beginner": {"quarter": "60-85", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "130-160", "eighth": "85-115", "sixteenth": "60-85"},
                "advanced": {"quarter": None, "eighth": "130-160", "sixteenth": "115-130"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "130+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="alt-pick-scale-3nps",
            name="3-Notes-Per-String Alternate Picking",
            category=Category.ALTERNATE_PICKING.value,
            description="Alternate picking on 3nps scale patterns. Odd number of notes per string changes pick direction on string change.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"pattern": "3nps", "scale": "major", "motion": "alternate"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-145", "eighth": "80-105", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-145", "sixteenth": "105-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="alt-pick-string-change",
            name="Controlled String Changes",
            category=Category.ALTERNATE_PICKING.value,
            description="Focus on smooth string transitions with alternate picking. Critical for fluid playing.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"pattern": "string-changes", "focus": "accuracy", "motion": "alternate"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "75-95", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "95-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="alt-pick-tremolo",
            name="Tremolo Picking",
            category=Category.ALTERNATE_PICKING.value,
            description="Rapid alternate picking on single note. Extreme speed and control exercise.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=80,
            bpm_ceiling=160,
            specific_params={"pattern": "tremolo", "duration": "sustained", "motion": "micro"},
            benchmark_table={
                "beginner": {"quarter": "80-100", "eighth": "60-80", "sixteenth": None},
                "intermediate": {"quarter": "160-190", "eighth": "100-130", "sixteenth": "80-100"},
                "advanced": {"quarter": None, "eighth": "160-190", "sixteenth": "130-160"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "160+"}
            }
        ))

        # ===== CATEGORY 6: ECONOMY/SWEEP PICKING (5 exercises) =====
        exercises.append(GuitarExercise(
            id="economy-simple-arpeggios",
            name="Simple Arpeggio Sweeps (3-string)",
            category=Category.ECONOMY_SWEEP.value,
            description="Downstroke sweep across 3 strings (major/minor triads). Foundation of economy picking.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=100,
            specific_params={"pattern": "3-string", "chord": "triad", "direction": "down"},
            benchmark_table={
                "beginner": {"quarter": "50-70", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "70-90", "sixteenth": "50-70"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "90-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="economy-5-string-sweep",
            name="5-String Sweep Arpeggios",
            category=Category.ECONOMY_SWEEP.value,
            description="Full 5-string sweep (major, minor, diminished). Requires precise muting and timing.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=40,
            bpm_ceiling=80,
            specific_params={"pattern": "5-string", "chord": "extended", "direction": "bidirectional"},
            benchmark_table={
                "beginner": {"quarter": "40-55", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "80-100", "eighth": "55-75", "sixteenth": "40-55"},
                "advanced": {"quarter": None, "eighth": "80-100", "sixteenth": "75-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="economy-tap-sweep-hybrid",
            name="Tapping + Sweep Hybrid",
            category=Category.ECONOMY_SWEEP.value,
            description="Combine right-hand tapping with sweep picking for extended arpeggios.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=40,
            bpm_ceiling=70,
            specific_params={"pattern": "tap-sweep", "technique": "hybrid", "strings": 6},
            benchmark_table={
                "beginner": {"quarter": "40-50", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "70-85", "eighth": "50-65", "sixteenth": "40-50"},
                "advanced": {"quarter": None, "eighth": "70-85", "sixteenth": "65-70"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "70+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="economy-scale-sequences",
            name="Economy Picking Scale Sequences",
            category=Category.ECONOMY_SWEEP.value,
            description="Scale runs using economy motion (down on string change when descending, up when ascending).",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"pattern": "scale-run", "motion": "economy", "scale": "major"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "100-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="economy-muting-control",
            name="Sweep with String Muting",
            category=Category.ECONOMY_SWEEP.value,
            description="Practice precise left-hand muting to prevent unwanted ringing during sweeps.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=40,
            bpm_ceiling=80,
            specific_params={"pattern": "sweep", "focus": "muting", "strings": 5},
            benchmark_table={
                "beginner": {"quarter": "40-55", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "80-100", "eighth": "55-75", "sixteenth": "40-55"},
                "advanced": {"quarter": None, "eighth": "80-100", "sixteenth": "75-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        # ===== CATEGORY 7: STRING SKIPPING (5 exercises) =====
        exercises.append(GuitarExercise(
            id="skip-pentatonic-basic",
            name="Pentatonic String Skips",
            category=Category.STRING_SKIPPING.value,
            description="Skip one string between notes in pentatonic box. Improves pick accuracy and melodic range.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"pattern": "pentatonic", "skip": 1, "scale": "minor pentatonic"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "80-100", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "100-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="skip-two-string-octaves",
            name="Two-String Skip Octaves",
            category=Category.STRING_SKIPPING.value,
            description="Skip two strings to play octaves. Common in melodic rock/fusion lines.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"pattern": "octaves", "skip": 2, "interval": "octave"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "75-95", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "95-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="skip-arpeggios-wide",
            name="Wide-Interval Arpeggio Skips",
            category=Category.STRING_SKIPPING.value,
            description="Arpeggios with large string skips (e.g., root on E, 3rd on D, 5th on B). Challenges coordination.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=90,
            specific_params={"pattern": "arpeggio", "skip": "varied", "chord": "extended"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "65-85", "sixteenth": "50-65"},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "85-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="skip-alternate-pick-sync",
            name="String Skip with Alternate Picking",
            category=Category.STRING_SKIPPING.value,
            description="Strict alternate picking while skipping strings. Synchronizes pick motion with large jumps.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"pattern": "alternate-skip", "motion": "strict", "skip": 1},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "75-90", "sixteenth": "60-75"},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "90-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="skip-chromatic-sequence",
            name="Chromatic String Skip Sequences",
            category=Category.STRING_SKIPPING.value,
            description="Chromatic patterns with systematic string skipping. Extreme coordination challenge.",
            difficulty_tier=DifficultyTier.EXPERT.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=50,
            bpm_ceiling=80,
            specific_params={"pattern": "chromatic", "skip": "systematic", "sequence": "1-2-3-4"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "80-95", "eighth": "65-75", "sixteenth": "50-65"},
                "advanced": {"quarter": None, "eighth": "80-95", "sixteenth": "75-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        # ===== CATEGORY 8: BENDING & VIBRATO (6 exercises) =====
        exercises.append(GuitarExercise(
            id="bend-half-step",
            name="Half-Step Bends",
            category=Category.BENDING_VIBRATO.value,
            description="Bend string up half step and match target pitch. Use reference note to check intonation.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"bend": "half-step", "strings": "all", "accuracy": "pitch-match"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "80-100", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "80-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="bend-full-step",
            name="Full-Step Bends",
            category=Category.BENDING_VIBRATO.value,
            description="Bend up one full tone. Requires finger strength and pitch accuracy.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=90,
            specific_params={"bend": "full-step", "strings": "G-B-E", "accuracy": "pitch-match"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "75-90", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "75-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="bend-pre-bend-release",
            name="Pre-Bend and Release",
            category=Category.BENDING_VIBRATO.value,
            description="Bend string silently, pick, then release to target pitch. Requires control and pitch memory.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=50,
            bpm_ceiling=80,
            specific_params={"bend": "pre-bend-release", "technique": "silent-bend", "accuracy": "pitch-match"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "80-95", "eighth": "65-80", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "80-95", "sixteenth": "65-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="vibrato-slow-wide",
            name="Slow Wide Vibrato",
            category=Category.BENDING_VIBRATO.value,
            description="Controlled vibrato with wide pitch variation. Blues/rock style.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"vibrato": "wide", "speed": "slow", "control": "even"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "80-100", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "80-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="vibrato-fast-narrow",
            name="Fast Narrow Vibrato",
            category=Category.BENDING_VIBRATO.value,
            description="Rapid subtle vibrato. Classical/jazz style for sustained notes.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"vibrato": "narrow", "speed": "fast", "control": "even"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "80-100", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "80-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="bend-unison",
            name="Unison Bends",
            category=Category.BENDING_VIBRATO.value,
            description="Bend one string to match pitch of adjacent fretted string. Perfect for pitch training.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=50,
            bpm_ceiling=80,
            specific_params={"bend": "unison", "strings": 2, "accuracy": "perfect-match"},
            benchmark_table={
                "beginner": {"quarter": "50-65", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "80-95", "eighth": "65-80", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "80-95", "sixteenth": "65-80"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "80+"}
            }
        ))

        # ===== CATEGORY 9: CHORD TRANSITIONS (5 exercises) =====
        exercises.append(GuitarExercise(
            id="chord-open-basic",
            name="Basic Open Chord Changes",
            category=Category.CHORD_TRANSITIONS.value,
            description="Practice G-C-D, Em-Am-C, etc. Foundation for rhythm guitar.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"chords": "open", "progression": "I-IV-V", "rhythm": "quarter-strums"},
            benchmark_table={
                "beginner": {"quarter": "60-90", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-150", "eighth": "90-120", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "120-150", "sixteenth": "90-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chord-barre-major-minor",
            name="Barre Chord Transitions",
            category=Category.CHORD_TRANSITIONS.value,
            description="Switch between major and minor barre shapes (E and A forms). Builds hand strength.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=110,
            specific_params={"chords": "barre", "shapes": "E-A-forms", "rhythm": "quarter-strums"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "110-130", "eighth": "80-100", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "110-130", "sixteenth": "100-110"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "110+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chord-jazz-voicings",
            name="Jazz Chord Voicings",
            category=Category.CHORD_TRANSITIONS.value,
            description="Practice maj7, min7, dom7, half-diminished changes. Essential for jazz comping.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=100,
            specific_params={"chords": "jazz", "extensions": "7ths-9ths", "rhythm": "comping"},
            benchmark_table={
                "beginner": {"quarter": "60-75", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "100-120", "eighth": "75-95", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "100-120", "sixteenth": "95-100"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "100+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chord-speed-changes",
            name="Speed Chord Changes",
            category=Category.CHORD_TRANSITIONS.value,
            description="Rapid chord changes on eighth notes. Punk/pop rhythm training.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=80,
            bpm_ceiling=140,
            specific_params={"chords": "power-chords", "speed": "eighth-notes", "style": "punk"},
            benchmark_table={
                "beginner": {"quarter": "80-100", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "140-170", "eighth": "100-130", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "140-170", "sixteenth": "130-140"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "140+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="chord-position-jumps",
            name="Position Jump Chord Changes",
            category=Category.CHORD_TRANSITIONS.value,
            description="Large fretboard jumps between chord positions. Develops spatial awareness.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.QUARTER.value,
            bpm_floor=60,
            bpm_ceiling=90,
            specific_params={"chords": "varied", "jumps": "large", "positions": "distant"},
            benchmark_table={
                "beginner": {"quarter": "60-70", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "90-110", "eighth": "70-85", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "90-110", "sixteenth": "85-90"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "90+"}
            }
        ))

        # ===== CATEGORY 10: PALM MUTING & RHYTHM (5 exercises) =====
        exercises.append(GuitarExercise(
            id="palm-mute-basic",
            name="Basic Palm Muting",
            category=Category.PALM_MUTING.value,
            description="Consistent palm muting on power chords. Foundation for rock/metal rhythm.",
            difficulty_tier=DifficultyTier.BEGINNER.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=80,
            bpm_ceiling=140,
            specific_params={"technique": "palm-mute", "pattern": "eighth-notes", "chords": "power"},
            benchmark_table={
                "beginner": {"quarter": "80-110", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "140-170", "eighth": "110-140", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "140-170", "sixteenth": "110-140"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "140+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="palm-mute-gallop",
            name="Gallop Rhythm (triplet palm muting)",
            category=Category.PALM_MUTING.value,
            description="Triplet-feel palm muting pattern. Common in metal (Iron Maiden style).",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=80,
            bpm_ceiling=130,
            specific_params={"technique": "palm-mute", "pattern": "gallop-triplet", "feel": "triplet"},
            benchmark_table={
                "beginner": {"quarter": "80-100", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "130-160", "eighth": "100-125", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "130-160", "sixteenth": "125-130"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "130+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="palm-mute-16ths",
            name="16th Note Palm Muting",
            category=Category.PALM_MUTING.value,
            description="Rapid 16th-note palm-muted chugging. Endurance and precision challenge.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.SIXTEENTH.value,
            bpm_floor=60,
            bpm_ceiling=120,
            specific_params={"technique": "palm-mute", "pattern": "16ths", "endurance": "sustained"},
            benchmark_table={
                "beginner": {"quarter": "60-80", "eighth": "40-60", "sixteenth": None},
                "intermediate": {"quarter": "120-140", "eighth": "80-110", "sixteenth": "60-80"},
                "advanced": {"quarter": None, "eighth": "120-140", "sixteenth": "110-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="palm-mute-accent-pattern",
            name="Accent Pattern Palm Muting",
            category=Category.PALM_MUTING.value,
            description="Palm mute with accents on specific beats. Develops dynamic control.",
            difficulty_tier=DifficultyTier.INTERMEDIATE.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=80,
            bpm_ceiling=130,
            specific_params={"technique": "palm-mute", "pattern": "accented", "dynamics": "varied"},
            benchmark_table={
                "beginner": {"quarter": "80-100", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "130-160", "eighth": "100-125", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "130-160", "sixteenth": "125-130"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "130+"}
            }
        ))

        exercises.append(GuitarExercise(
            id="palm-mute-hybrid-open",
            name="Palm Mute + Open String Hybrid",
            category=Category.PALM_MUTING.value,
            description="Alternate between palm-muted and open strings. Creates contrast in rhythm playing.",
            difficulty_tier=DifficultyTier.ADVANCED.value,
            subdivision_default=Subdivision.EIGHTH.value,
            bpm_floor=80,
            bpm_ceiling=120,
            specific_params={"technique": "hybrid", "pattern": "mute-open", "contrast": "dynamic"},
            benchmark_table={
                "beginner": {"quarter": "80-95", "eighth": None, "sixteenth": None},
                "intermediate": {"quarter": "120-145", "eighth": "95-115", "sixteenth": None},
                "advanced": {"quarter": None, "eighth": "120-145", "sixteenth": "115-120"},
                "expert": {"quarter": None, "eighth": None, "sixteenth": "120+"}
            }
        ))

        return exercises

    def get_all_exercises(self) -> List[Dict]:
        """Return all exercises as dictionaries"""
        return [self._exercise_to_dict(ex) for ex in self.exercises]

    def get_exercises_by_category(self, category: str) -> List[Dict]:
        """Filter exercises by category"""
        filtered = [ex for ex in self.exercises if ex.category == category]
        return [self._exercise_to_dict(ex) for ex in filtered]

    def get_exercise_by_id(self, exercise_id: str) -> Optional[Dict]:
        """Get specific exercise by ID"""
        for ex in self.exercises:
            if ex.id == exercise_id:
                return self._exercise_to_dict(ex)
        return None

    def _exercise_to_dict(self, exercise: GuitarExercise) -> Dict:
        """Convert exercise object to dictionary"""
        return {
            "id": exercise.id,
            "name": exercise.name,
            "category": exercise.category,
            "description": exercise.description,
            "difficulty_tier": exercise.difficulty_tier,
            "subdivision_default": exercise.subdivision_default,
            "bpm_floor": exercise.bpm_floor,
            "bpm_ceiling": exercise.bpm_ceiling,
            "specific_params": exercise.specific_params,
            "benchmark_table": exercise.benchmark_table
        }

    # ===== PROGRESSION LOGIC =====

    def get_next_bpm(self, current_bpm: int) -> int:
        """Calculate next BPM using 10% rule"""
        return math.ceil(current_bpm * 1.10)

    def get_bpm_ladder(self, start_bpm: int, ceiling_bpm: int) -> List[int]:
        """Generate practice BPM ladder with 10% increments"""
        ladder = []
        bpm = start_bpm

        while bpm < ceiling_bpm:
            ladder.append(bpm)
            bpm = self.get_next_bpm(bpm)

        ladder.append(ceiling_bpm)
        return ladder

    def calculate_advancement_ready(self, practice_logs: List[Dict]) -> bool:
        """
        Check if user is ready to advance BPM
        Criteria: Last 3 sessions all rated "Gold" (≥90% accuracy)
        """
        if len(practice_logs) < 3:
            return False

        last_three = practice_logs[-3:]
        return all(log.get("accuracy_tier") == "gold" for log in last_three)

    def suggest_next_subdivision(self, current_subdivision: str, current_bpm: int, ceiling_bpm: int) -> Optional[str]:
        """
        Suggest subdivision upgrade when BPM ceiling reached
        Progression: quarter → eighth → sixteenth → sextuplet
        """
        if current_bpm < ceiling_bpm:
            return None  # Not at ceiling yet

        subdivision_progression = {
            Subdivision.QUARTER.value: Subdivision.EIGHTH.value,
            Subdivision.EIGHTH.value: Subdivision.SIXTEENTH.value,
            Subdivision.SIXTEENTH.value: Subdivision.SEXTUPLET.value,
            Subdivision.SEXTUPLET.value: None  # Max subdivision reached
        }

        return subdivision_progression.get(current_subdivision)

    def check_regression_needed(self, practice_logs: List[Dict]) -> bool:
        """
        Check if BPM regression recommended
        Criteria: Last 3 sessions all rated "Bronze" (<70% accuracy)
        """
        if len(practice_logs) < 3:
            return False

        last_three = practice_logs[-3:]
        return all(log.get("accuracy_tier") == "bronze" for log in last_three)

    def get_previous_bpm(self, current_bpm: int) -> int:
        """Calculate previous BPM (reverse of 10% rule)"""
        return math.floor(current_bpm / 1.10)

    def suggest_rest_day(self, practice_logs: List[Dict]) -> bool:
        """
        Suggest rest day based on quality trend
        Criteria: Quality ratings decreasing over 3+ sessions (3→2→1→1)
        """
        if len(practice_logs) < 3:
            return False

        last_four = practice_logs[-4:] if len(practice_logs) >= 4 else practice_logs[-3:]
        quality_ratings = [log.get("quality_rating", 2) for log in last_four]

        # Check for decreasing trend
        for i in range(len(quality_ratings) - 1):
            if quality_ratings[i] < quality_ratings[i + 1]:
                return False  # Not consistently decreasing

        return True  # Trend is flat or decreasing

    def get_stale_exercises(self, all_progress_snapshots: Dict, days_threshold: int = 7) -> List[str]:
        """
        Get list of exercise IDs not practiced in N days
        """
        from datetime import datetime, timedelta

        stale = []
        cutoff = datetime.now() - timedelta(days=days_threshold)

        for exercise_id, snapshot in all_progress_snapshots.items():
            last_practiced = snapshot.get("last_practiced")
            if not last_practiced:
                stale.append(exercise_id)
            else:
                last_date = datetime.fromisoformat(last_practiced.replace('Z', '+00:00'))
                if last_date < cutoff:
                    stale.append(exercise_id)

        return stale

    def get_category_stats(self, practice_logs: List[Dict]) -> Dict[str, Dict]:
        """Calculate statistics per category from practice logs"""
        category_data = {}

        for log in practice_logs:
            exercise_id = log.get("exercise_id")
            exercise = self.get_exercise_by_id(exercise_id)

            if not exercise:
                continue

            category = exercise["category"]

            if category not in category_data:
                category_data[category] = {
                    "sessions": 0,
                    "total_time": 0,
                    "total_bpm": 0,
                    "count": 0
                }

            category_data[category]["sessions"] += 1
            category_data[category]["total_time"] += log.get("duration_seconds", 0)
            category_data[category]["total_bpm"] += log.get("bpm_achieved", 0)
            category_data[category]["count"] += 1

        # Calculate averages
        for category in category_data:
            count = category_data[category]["count"]
            if count > 0:
                category_data[category]["avg_bpm"] = category_data[category]["total_bpm"] / count
            else:
                category_data[category]["avg_bpm"] = 0

        return category_data


# Singleton instance
guitar_generator = GuitarExerciseGenerator()
