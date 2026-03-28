# Improv Generator Expansion: Scales, Patterns & Motifs

## Executive Summary

Your improvisation generator currently covers the essentials — 6 scales in the JS frontend (`IMPROV_SCALES`) and 19 in the Python backend (`SCALE_DEFINITIONS`), paired with 8 left-hand/accompaniment patterns. This research identifies **40+ additional scales across 7 categories**, **15+ new piano left-hand patterns across 5 style families**, **12+ guitar-specific accompaniment patterns**, and a full **motif generation system** with transformation rules. Each expansion is mapped directly to your existing data structures so additions are drop-in.

***

## Code Audit: What You Already Have

### Scales

The Python `music_engine.py` has a solid jazz foundation:[^1]

| Category | Scales Already Defined |
|---|---|
| Diatonic Modes | Major, Natural Minor, Dorian, Phrygian, Lydian, Mixolydian, Locrian |
| Minor Variants | Harmonic Minor, Melodic Minor, Jazz Minor |
| Jazz / Modern | Lydian Dominant, Altered, Phrygian Dominant, Dominant Bebop |
| Symmetric | Whole Tone, Diminished HW |
| Pentatonic / Blues | Pentatonic Major, Pentatonic Minor, Blues |

The `improv-generator.js` only exposes a subset (6 scales) to the frontend, so the first quick win is syncing the JS `IMPROV_SCALES` object with everything already in `SCALE_DEFINITIONS`.

### Patterns (Piano)

Current `PATTERN_DEFINITIONS` include Block Chords, Alberti Bass, Walking Bass, Stride, Bossa Nova, Waltz, Arpeggio Up, Arpeggio Down. The `improv-generator.js` only exposes 5 of these. Plenty of room to grow both sides.

### Guitar Patterns

The JS guitar view renders scale notes as fret positions on `GUITAR_OPEN = [40,45,50,55,59,64]` but has no equivalent pattern system to `PATTERN_DEFINITIONS` — this is the largest gap.

### Missing: Motifs

Neither file has any motif generation system. This is the highest-value addition.

***

## Part 1: Scale Expansions

### 1.1 Bebop Scales

Bebop scales add a chromatic passing tone to common 7-note scales, keeping chord tones on the downbeats of 8th-note lines. They are foundational for jazz vocabulary.[^2]

| Scale | Intervals (semitones) | Use Over |
|---|---|---|
| Major Bebop | `[0,2,4,5,7,8,9,11]` | Maj7 chords (chromatic between b6 and 5) |
| Minor Bebop | `[0,2,3,5,7,8,9,10]` | Min7 chords |
| Dominant Bebop | `[0,2,4,5,7,9,10,11]` | Dominant 7th chords (V9) |

The dominant bebop scale is the most essential for jazz. By placing a chromatic passing tone between the 8th and b7th, the chord tones always fall on the downbeats of a descending 8th-note run — a built-in mechanism for musical phrasing.[^2]

### 1.2 Symmetric & Exotic Western Scales

These go beyond modes and generate unusual, ear-catching sounds.[^3]

| Scale | Intervals (semitones) | Character |
|---|---|---|
| Whole-Half Diminished | `[0,2,3,5,6,8,9,11]` | Over dim7 chords — symmetrical, eerie |
| Prometheus / Mystic | `[0,2,4,6,9,10]` | Scriabin — other-worldly, #11 flavour |
| Enigmatic (Ascending) | `[0,1,4,6,8,10,11]` | Verdi — intensely chromatic, ascending |
| Persian | `[0,1,4,5,6,8,11]` | Middle Eastern tension |
| Byzantine | `[0,1,4,5,7,8,11]` | Double harmonic major; "Flamenco mode" |
| Neapolitan Minor | `[0,1,3,5,7,8,11]` | Dark and classical |
| Neapolitan Major | `[0,1,3,5,7,9,11]` | Same but with natural 6 |

The symmetrical diminished scales are particularly important for jazz — the whole-tone scale implies a natural 9, #11, b13, and b7, making it ideal over V7b13 chords when there's no b9 or #9.[^2]

### 1.3 World / Ethnic Scales

These provide strong cultural flavour and are highly motivating for students exploring non-Western sounds.[^4]

| Scale | Intervals | Origin / Flavour |
|---|---|---|
| Hungarian Minor (Gypsy Minor) | `[0,2,3,6,7,8,11]` | Eastern European — two augmented 2nds, exotic and dark[^5] |
| Hungarian Major | `[0,3,4,6,7,9,10]` | More dominant flavour |
| Spanish Gipsy (Phrygian Dominant) | `[0,1,4,5,7,8,10]` | Flamenco; 5th mode of harmonic minor |
| Romanian Major | `[0,1,4,6,7,9,10]` | Lydian Dominant b2; adds tension on dom7 |
| Arabian (Major Locrian) | `[0,2,4,5,6,8,10]` | Over 7b5b13 chords |
| Asian / Oriental | `[0,1,4,5,6,9,10]` | "Minor Romani Inversed" |
| Javanese Pelog | `[0,1,3,5,7,9,10]` | Indonesian; Dorian b2 |

The Hungarian minor is a perfectly balanced seven-note scale — when its pitches are represented as points on a circle, their average position is the centre. This gives it a subtly ambiguous tonal centre, which makes it exceptionally useful for improvisation that wants to feel suspended between keys.[^5]

### 1.4 Japanese Pentatonic Scales

These 5-note scales are enormously popular in guitar and keyboard improvisation for their stark, minimal beauty.[^6][^7]

| Scale | Intervals | Formula |
|---|---|---|
| Hirajoshi | `[0,2,3,7,8]` | 1-2-b3-5-b6 |
| In Sen (Kokin-joshi) | `[0,1,5,7,10]` | 1-b2-4-5-b7 |
| Iwato | `[0,1,5,6,10]` | 1-b2-4-b5-b7 |
| Kumoi | `[0,2,5,7,8]` | 1-2-4-5-b6 |
| Han-Kumoi | `[0,2,5,7,8]` | 1-2-4-5-b6 (minor flavour) |
| Balinese Pelog | `[0,1,3,7,8]` | 1-b2-b3-5-b6 |

The Hirajoshi scale originated from Japanese shamisen music and was used for accurately tuning the Koto. Its 5-note structure makes it highly practical for improvisation — with fewer notes to navigate, players can focus on phrasing and rhythm.[^6]

### 1.5 Other Essential Pentatonics

| Scale | Intervals | Character |
|---|---|---|
| Dominant Pentatonic | `[0,2,4,7,10]` | 1-2-3-5-b7; excellent over dom7 chords |
| Egyptian (Suspended) | `[0,2,5,7,10]` | 1-2-4-5-b7; 2nd mode of major pentatonic |
| Scottish Pentatonic | `[0,2,5,7,9]` | 1-2-4-5-6; folkloric, open sound |
| Mongolian | `[0,2,4,7,9]` | Same as Major Pentatonic; included for context labelling |

### 1.6 Suggested `SCALE_CATEGORIES` Additions

The generator currently uses `'beginner'`, `'common'`, and `'jazz'` categories. Suggest adding:

```python
'bebop': ['Dominant Bebop', 'Major Bebop', 'Minor Bebop'],
'world': ['Hungarian Minor', 'Phrygian Dominant', 'Byzantine', 'Persian', 'Spanish Gipsy',
          'Romanian Major', 'Neapolitan Minor'],
'japanese': ['Hirajoshi', 'In Sen', 'Iwato', 'Kumoi', 'Balinese Pelog'],
'symmetric': ['Whole Tone', 'Diminished HW', 'Whole-Half Diminished', 'Prometheus'],
'pentatonic_ext': ['Dominant Pentatonic', 'Egyptian', 'Scottish Pentatonic'],
```

***

## Part 2: Piano Left-Hand Pattern Expansions

### 2.1 Current Gap Analysis

The current 8 patterns skew toward classical (Alberti, Waltz) and basic jazz (Stride, Walking Bass). Missing families: **boogie-woogie ostinatos**, **funk/gospel**, **rootless voicings**, **quartal/open voicings**, **ostinato drones**.

### 2.2 Boogie-Woogie & Blues Ostinatos

Boogie-woogie derives from a left hand that plays a set ostinato figure while the right hand freely improvises. The key is maintaining the pattern unconsciously so the right hand can roam.[^8]

| Pattern Name | Sequence | Description |
|---|---|---|
| Boogie Shuffle | `[1, 5, 6, 5]` | Root-fifth-sixth-fifth swing pattern |
| Boogie Chop | `[1, 8, 1, 8]` | Octave jump — country / rock boogie feel |
| Boogie Ascending | `[1, 2, 3, 4, 5, 6, 5, 3]` | Walking chromatic climb, back to 5 |
| 12-Bar Groove | `[1, 5, 1, 5, [1,5], [1,5]]` | Alternating bass + power chord hits |
| Shuffle Split | `[1, [3,5], 1, [3,5]]` | Low root, staccato chord hits |

### 2.3 Funk / Gospel / R&B Patterns

| Pattern Name | Sequence | Description | Vibe |
|---|---|---|---|
| Gospel Chop | `[[1,5], [3,7], [1,5], [3,7,9]]` | Alternating bass chord + extension | gospel, soul |
| Funk Stab | `[[1,3,7], 0, [1,3,7], 0]` | Chord stabs with rests (0=rest) | funk, R&B |
| Syncopated Bass | `[1, 0, 5, 1, 0, 5, 3, 5]` | Off-beat bass movement | funk, pop |
| New Orleans | `[1, 3, 5, 3, [1,5], 3, 5, 3]` | Circular bass phrase | blues, Creole |

### 2.4 Jazz Voicing Patterns

These are more advanced: the left hand plays harmonically rich voicings rather than just chord tones.[^9][^10]

| Pattern Name | Sequence / Voicing | Description | Vibe |
|---|---|---|---|
| Shell Voicing | `[[1,7]]` | Root + 7th only (Bud Powell style) | bebop, straightahead |
| Shell Voicing Alt | `[[1,3]]` | Root + 3rd variation | bebop |
| Rootless A | `[[3,5,7,9]]` | Bill Evans-style — 3-5-7-9 in LH | modern jazz |
| Rootless B | `[[7,9,3,5]]` | Inversion of Rootless A — 7-9-3-5 | modern jazz |
| Quartal Voicing | `[[1,4,7]]` | Stacked 4ths — McCoy Tyner | modal jazz |
| Quartal Quartal | `[[4,7,3]]` | Wider quartal stack | modal, contemporary |

Rootless voicings, popularised by Bill Evans, Red Garland, and Wynton Kelly in the late 1950s, exclude the root and replace it with chord extensions (9ths, 11ths, 13ths), producing a jazz sound with smooth voice-leading between chords. The 3rds turn into 7ths and 7ths turn into 3rds across a II-V-I, which can be made explicit in the pattern description.[^10][^11]

### 2.5 Ostinato / Drone Patterns

| Pattern Name | Sequence | Description |
|---|---|---|
| Open Fifth Ostinato | `[[1,5], [1,5], [1,5], [1,5]]` | Power-chord drone — modal or rock improv |
| Two-Note Bass Vamp | `[1, 0, 1, 0, 5, 0, 5, 0]` | Alternating root/fifth pedal point |
| Pedal Bass | `[1, 1, 1, 1]` | Static bass note — tension builder |
| Rhumba Clave | `[1, 0, 0, 5, 0, 1, 0, 0]` | 3-2 clave feel in bass | 

### 2.6 Latin Expansions

The existing Bossa Nova pattern is a good start, but Latin piano is enormously varied.[^12]

| Pattern Name | Sequence | Description | Style |
|---|---|---|---|
| Montuno | `[1, 3, 5, 3, 8, 5, 3, 5]` | Cuban pianist's repeated figure | Son, Salsa |
| Songo | `[1, 0, 5, 0, [1,5], 0, 3, 0]` | Afro-Cuban with rests | Songo, Timba |
| Cha-Cha | `[1, 1, 5, 5, 1, 0, 5, 0]` | Steady chachacha feel | Cha-cha, Latin pop |
| Mambo Bass | `[1, 5, 8, 5, 1, 0, 8, 5]` | Driving mambo left hand | Mambo, Salsa |

### 2.7 Updated `vibe` Tags for Filtering

Add these vibes to the `PATTERN_DEFINITIONS` dict alongside the new entries:
`'boogie'`, `'funk'`, `'gospel'`, `'soul'`, `'modal'`, `'latin_extended'`, `'voicing'`, `'drone'`, `'r&b'`.

***

## Part 3: Guitar-Specific Pattern System

### 3.1 Why Guitar Needs Its Own Pattern System

The current JS frontend renders guitar fret positions correctly but provides no accompaniment pattern equivalent to `IMPROV_PATTERNS`. Guitar patterns are inherently different: they involve **string skipping**, **position playing**, **bending**, and **hybrid picking** — not just interval sequences.[^13][^14]

### 3.2 Proposed `GUITAR_PATTERNS` Object Structure

```js
const GUITAR_PATTERNS = {
  'Box Pentatonic': {
    type: 'position',          // plays within a CAGED position box
    position: 1,               // box 1 = root at 6th string
    direction: 'up-down',
    technique: 'alternate',
    desc: 'Classic box shape, up and down'
  },
  'String Skip': {
    type: 'skip',
    skip_size: 1,              // skip 1 string
    direction: 'up',
    desc: 'Skip every other string for wider intervals'
  },
  // etc.
}
```

### 3.3 Pattern Library for Guitar

| Pattern Name | Type | Description | Style |
|---|---|---|---|
| Box Pattern I | Position | Standard pentatonic box 1 ascending | Blues, Rock |
| Box Pattern II | Position | Box 2 — extends range up the neck | Blues, Rock |
| Three-Note-Per-String | NPS | 3 notes per string across all 6 | Shred, Metal |
| String Skip Ascending | Skip | Jump strings for intervallic leaps[^13] | Modern, Jazz |
| String Skip Descending | Skip | Reverse string skip | Modern |
| Horizontal 1-String | Single | All notes on one string — slide feel | Country, Blues |
| CAGED Arpeggios | CAGED | Arpeggiate chord shape across neck[^15] | All styles |
| Enclosure Lick | Melodic | Half-step above + below chord tone → target[^16] | Jazz, Bebop |
| Chord Tone Target | Melodic | Land on R/3/5/7 on downbeat each bar[^17] | Jazz, Blues |
| Repeated Motif | Motif | 2–3-note idea repeated at different scale positions | All |
| Pedal Tone | Melodic | Repeated open/fretted note under melody | Country, Bluegrass |
| Double Stops | Harmonic | Two-note harmonies (3rds, 6ths) throughout scale[^18] | Country, Soul, Blues |
| Harmonised 6ths | Harmonic | Scale in parallel 6ths — two strings | Country, Blues |
| Unison Bend | Technique | Bend lower string to pitch of adjacent string | Rock, Blues |

### 3.4 CAGED Position Labels

Add CAGED position data to the guitar view for visual framing:[^19][^15]

```js
const CAGED_POSITIONS = {
  'E Shape': { root_string: 6, root_fret_offset: 0 },
  'D Shape': { root_string: 4, root_fret_offset: 0 },
  'C Shape': { root_string: 5, root_fret_offset: 3 },
  'A Shape': { root_string: 5, root_fret_offset: 0 },
  'G Shape': { root_string: 6, root_fret_offset: 5 },
}
```

Each CAGED shape provides a different visual "window" on the same scale notes, and the generator can randomly assign one of the five positions for the generated key + scale combination, telling the player where to anchor their hand.[^20]

***

## Part 4: Motif Generation System

### 4.1 What Is a Motif?

A motif is a short musical idea — typically 2–4 notes with a defined rhythm — that can be repeated, varied, and developed across an improvisation to create structure and coherence. Unlike playing random scale notes, a motif-based approach gives solos a narrative arc: statement, development, resolution. This is the single most musically valuable addition.[^21][^22]

### 4.2 Motif Data Structure (Python / JS)

```python
MOTIF_DEFINITIONS = {
    'Rising 3rd': {
        'intervals': [0, 2],           # scale degrees (1-indexed)
        'rhythm': [1.0, 1.0],          # note durations (quarter = 1.0)
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
        'intervals': [3, 1, 2, 3],     # surround the 3rd from above and below
        'rhythm': [0.5, 0.5, 0.5, 1.5],
        'direction': 'up',
        'length': 4,
        'desc': 'Approach target from chromatic above + below',
        'style': ['jazz', 'bebop'],
    },
    'Ascending Sequence': {
        'intervals': [1, 2, 3, 2, 3, 4, 3, 4, 5],
        'rhythm': [0.5]*9,
        'direction': 'up',
        'length': 9,
        'desc': 'Stepwise sequence climbing the scale in overlapping 3rds',
        'style': ['jazz', 'classical'],
    },
}
```

### 4.3 Motif Transformations

Motivic development is the cornerstone of structured improvisation. Generate a base motif and apply transformations:[^23][^24][^21]

| Transformation | Definition | Code Hint |
|---|---|---|
| **Transposition** | Move every note up/down by N scale steps[^22] | `[x + n for x in intervals]` |
| **Inversion** | Flip the direction of each interval[^23] | `[-x for x in intervals]` |
| **Retrograde** | Play the motif backwards[^21] | `intervals[::-1]` |
| **Augmentation** | Double all note durations[^21] | `[r * 2 for r in rhythm]` |
| **Diminution** | Halve all note durations[^21] | `[r / 2 for r in rhythm]` |
| **Fragmentation** | Use only the first N notes[^21] | `intervals[:n]` |
| **Displacement** | Shift rhythmic start point by 1 beat[^25] | Offset sequence start |
| **Chromatic Approach** | Add semitone above/below target notes[^22] | Insert ±1 MIDI before target |
| **Sequence** | Repeat at successively higher/lower scale positions[^23] | Iterate transposition |

A practical generator should pick a base motif, then apply 1–3 random transformations from this list to produce the "challenge motif of the session."

### 4.4 Motif Generator Class (Python)

```python
class MotifGenerator:
    TRANSFORMATIONS = ['transpose', 'invert', 'retrograde', 'augment', 
                       'diminish', 'fragment', 'displace']

    def generate(self, difficulty: int, style: str = 'all') -> Dict[str, Any]:
        # Filter motifs by style
        pool = [k for k, v in MOTIF_DEFINITIONS.items() 
                if style in v['style'] or 'all' in v['style']]
        base_name = random.choice(pool)
        base = MOTIF_DEFINITIONS[base_name].copy()
        
        # Apply transformations based on difficulty
        n_transforms = min(difficulty // 3, len(self.TRANSFORMATIONS))
        transforms = random.sample(self.TRANSFORMATIONS, n_transforms)
        
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
            'id': generate_id(),
            'mode': 'improv',
            'base_motif': base_name,
            'transforms_applied': transforms,
            'intervals': result_intervals,
            'rhythm': result_rhythm,
            'description': base['desc'],
            'style': style,
        }
```

### 4.5 JS Motif Display

In `improv-generator.js`, motifs can be displayed as:
- **Scale degree numbers** (e.g., `1 – 3 – 2 – 1`) with the highlighted piano/guitar notes
- **Rhythmic notation** as a simple sequence of filled/hollow note symbols
- **A "seed phrase"**: one bar of notation shown at the top of the display, for the player to use as their starting idea before improvising freely

***

## Part 5: Display & UX Enhancements

### 5.1 Scale Categorisation Tags

Add a `category` and `mood` label to each scale definition for display purposes:

```python
SCALE_METADATA = {
    'Hungarian Minor': {'category': 'World', 'mood': 'Dark, Exotic', 'difficulty': 'advanced'},
    'Hirajoshi':       {'category': 'Japanese', 'mood': 'Sparse, Mysterious', 'difficulty': 'intermediate'},
    'Dominant Bebop':  {'category': 'Bebop', 'mood': 'Swinging, Chromatic', 'difficulty': 'advanced'},
    'Byzantine':       {'category': 'World', 'mood': 'Majestic, Eastern', 'difficulty': 'advanced'},
    'Scottish Pentatonic': {'category': 'World', 'mood': 'Open, Folkloric', 'difficulty': 'beginner'},
    # ... etc
}
```

### 5.2 Chord Compatibility Tags

Each scale should carry a list of compatible chord types. This enables future "play over this chord" mode and helps students understand why a scale is suggested.[^26][^2]

```python
'Altered':         {'chords': ['7alt', '7#9b13', '7b9#11']},
'Lydian Dominant': {'chords': ['7#11', 'bII7', 'IV7']},
'Hirajoshi':       {'chords': ['min', 'min7', 'sus4']},
'Phrygian Dominant': {'chords': ['V7', '7b9']},
```

### 5.3 "Vibe Filter" for Random Generation

Instead of purely random selection, offer filter presets that the generator respects:

| Vibe Preset | Scales Included | Pattern Vibes | Motif Styles |
|---|---|---|---|
| Jazzy | Dorian, Altered, Lydian Dom, Bebop | Walking Bass, Stride, Rootless | Jazz Enclosure, Ascending Sequence |
| Bluesy | Blues, Pentatonic Minor, Dom Pent | Boogie Shuffle, New Orleans | Blues Wail, Pentatonic Drop |
| World / Exotic | Hungarian Minor, Byzantine, Hirajoshi, In Sen | Ostinato, Rhumba Clave | Transposition, Fragmentation |
| Classical | Major, Harmonic Minor, Neapolitan | Alberti Bass, Waltz, Arpeggio | Rising 3rd, Sequence |
| Modal / Meditative | Dorian, Lydian, Whole Tone | Open Fifth Ostinato, Pedal Bass | Displacement, Inversion |

### 5.4 Motif Display Panel

Add a third panel to the existing piano/guitar display that shows the current motif as:
1. **Scale degree notation** (e.g., `1 – b3 – 4 – 5 – b3 – 1`)
2. **Rhythm dots** (filled dot = beat, open dot = off-beat, dash = rest)
3. **Transformation history** (e.g., "Retrograde of 'Call Riff'")
4. **Highlighted notes** on the piano/guitar diagram

***

## Implementation Roadmap

### Phase 1 — Scale Sync (Low Effort, High Value)
- Sync `improv-generator.js` `IMPROV_SCALES` with all entries in `music_engine.py` `SCALE_DEFINITIONS`
- Add the 15 new scales above to `SCALE_DEFINITIONS` in `music_engine.py`
- Add `SCALE_CATEGORIES` entries for `'bebop'`, `'world'`, `'japanese'`, `'symmetric'`, `'pentatonic_ext'`
- Add `SCALE_METADATA` dict with `category`, `mood`, and `difficulty`

### Phase 2 — Pattern Expansion (Medium Effort)
- Add boogie, gospel, funk, and Latin patterns to `PATTERN_DEFINITIONS` in `music_engine.py`
- Add rootless and quartal voicing patterns (display as chord symbols for the left hand, not sequences)
- Implement `GUITAR_PATTERNS` object in `improv-generator.js`
- Add CAGED position labels to guitar view

### Phase 3 — Motif System (High Value, Medium-High Effort)
- Implement `MOTIF_DEFINITIONS` dict in `music_engine.py`
- Implement `MotifGenerator` class with transformation logic
- Add motif output fields to `ScalePatternGenerator.generate()` return value
- Add motif display panel to `improv-generator.js` UI
- Highlight motif notes on piano keyboard and guitar fretboard

### Phase 4 — Vibe Filtering & UX
- Add vibe preset buttons to the generator UI
- Implement filter logic in `ScalePatternGenerator.generate()` using the `vibe` tags
- Add `chord_compatibility` tags to scale metadata
- Add optional "Suggest a chord" feature alongside scale display

***

## Quick-Reference Scale Addition Tables

### New Scales: `SCALE_DEFINITIONS` Additions

```python
# Bebop
'Major Bebop':           [0, 2, 4, 5, 7, 8, 9, 11],
'Minor Bebop':           [0, 2, 3, 5, 7, 8, 9, 10],
# Dominant Bebop already in codebase

# Symmetric / Exotic Western  
'Whole-Half Diminished': [0, 2, 3, 5, 6, 8, 9, 11],
'Prometheus':            [0, 2, 4, 6, 9, 10],
'Enigmatic':             [0, 1, 4, 6, 8, 10, 11],
'Persian':               [0, 1, 4, 5, 6, 8, 11],
'Byzantine':             [0, 1, 4, 5, 7, 8, 11],
'Neapolitan Minor':      [0, 1, 3, 5, 7, 8, 11],
'Neapolitan Major':      [0, 1, 3, 5, 7, 9, 11],

# World / Ethnic
'Hungarian Minor':       [0, 2, 3, 6, 7, 8, 11],
'Hungarian Major':       [0, 3, 4, 6, 7, 9, 10],
'Romanian Major':        [0, 1, 4, 6, 7, 9, 10],
'Arabian':               [0, 2, 4, 5, 6, 8, 10],
'Asian':                 [0, 1, 4, 5, 6, 9, 10],
'Javanese Pelog':        [0, 1, 3, 5, 7, 9, 10],

# Japanese Pentatonic
'Hirajoshi':             [0, 2, 3, 7, 8],
'In Sen':                [0, 1, 5, 7, 10],
'Iwato':                 [0, 1, 5, 6, 10],
'Kumoi':                 [0, 2, 5, 7, 8],
'Balinese Pelog':        [0, 1, 3, 7, 8],

# Other Pentatonics
'Dominant Pentatonic':   [0, 2, 4, 7, 10],
'Egyptian':              [0, 2, 5, 7, 10],
'Scottish Pentatonic':   [0, 2, 5, 7, 9],
```

---

## References

1. [music_engine.py](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/7798530/369fc41d-94f7-4c1f-b5e5-97a2b50bb1e3/music_engine.py?AWSAccessKeyId=ASIA2F3EMEYEWMIPCEY7&Signature=gej3gRG7YIaNitdBFexmPrdV4lo%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEC0aCXVzLWVhc3QtMSJIMEYCIQCs8THN4uf%2BSI6aYREAFHGNSBnjbB88cv4X9wknCV40VgIhAIyagtDq86iXqGFjNA5jXcpEiTUyJVQZZiZsLRuV1hYUKvwECPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igzggf4D%2FxqoQVW4TIEq0ARsnANGOep72G8S%2FR2vFVJ6sUrI895iBoMzsTb8n900oscFMKFfNMzaT5k9DxxXS6XpErX1jUOJzeUYwyl2AJkgaTeN4EgbyfH%2F0Kfw%2BYHHR7a2fvWmFil8CsQdgZSxCv3LC7WISNTTicohSpy0ZN%2FdWK4K3hXTLFAEvTEDqnYM1km32OytZ2z17H4RRaKOE2zWOxuRfzFNS87byQJDcIrgZ%2Bkl8vvqeuoK3Zq%2BUTLue3dRRmM0DJTULaZcUwc5tln%2FcUBgHZ3rQO5cBQOmTnwtUVf%2Fd0%2BapObljaqcjSgBt9MbXmTS0pPkTPjrC3f5M1M%2Bqlq3O8oxjj8JiQZ9tIVNPQ0L%2B3IWt4EO%2FaImmVK4GwQL2VXMmkuN4ZjTNOUdOU1qWtQfcpLEBr1uezi0ghfmdgmPtZ2hCbgq4dGo%2FF3PmBhVUEGGIBiWPa%2BbEKVweuH%2Bqrvlt9cG3f8d1YvCi5z7%2BSI0mO8G%2B4pRw%2FTvVs9ECvW3D0G880e%2BFNK1fZaiJGrmcLCsIipJyrlekf9EDTTo%2FftW48CSuNtrXlAn6bYy6JCh0IcCsOK20dV5d4Cr1rzqHcFOBlLDpIpuHug6RcZPgdoud%2FPM7IlVGNvydDB6OsydPZ%2B5og8i%2B9%2FXMXXvVqrE1U6GyyjhqrDmSkHva45S4C%2B9UVJl%2B2olEkuN7yWgxxwMdVL49gdadFh8rUnItiB%2FC7VJoNiz55a%2BzGTjPbahJNq2U9E%2BABkerbCek3SRvIi%2BL1mAqSGlDK6xoNmJZDYjEh%2F%2B%2ByBeNHWld33XgFdfMNmcn84GOpcBrBTBBN7NxPZb6fnAODA8RoZoUIz5UgGUECchy7QJ9LWQVRltlYMteT3IkDqgPoKbUPYZMJ9b7yBCSd%2BqcA9AiyIW%2BGQVoQQGKzzvnTiQK%2BiPZ%2FBE0qQTI54pxk2glZkVRgYxSwCUeawBmBHPvWjGaizYUqNLRzAN36hlsh7%2BkF1LWG4P2fAuxrhm8E5I197kbikm2OqZoA%3D%3D&Expires=1774705708) - import random
from typing import List, Dict, Any

# ===== MUSIC DATA =====

CHROMATIC_KEYS = ['C'...

2. [16 Important Jazz Scales You Need To Know](https://www.learnjazzstandards.com/blog/16-important-jazz-scales/) - In this post, we will explore 16 common jazz scales and reveal important tips and tricks for learnin...

3. [How To Improvise With Symmetrical Scales](https://www.freejazzlessons.com/symmetrical-scales/) - Improve your jazz improvisation with this symmetrical scales tutorial. Free notation of scales inclu...

4. [25 Exotic Scales For Guitar - Charts, Diagrams And Audio](https://www.jazz-guitar-licks.com/blog/exotic-scales-guitar.html) - This guitar lesson provides formula charts, diagrams and audio files for a better understanding of t...

5. [Hungarian minor scale - Wikipedia](https://en.wikipedia.org/wiki/Hungarian_minor_scale) - Chords that may be derived from the B Hungarian minor scale are Bm(maj7), C♯7♭5, Dmaj7♯5, E♯6sus2♭5,...

6. [Shinobi Reverse: Master The 'Hirajōshi' Scale & It's Modes](https://stringsofrage.com/scales-modes/shinobi-reverse-hirajoshi-pentatonic-scale-its-modes/) - こんにちは!! In this lesson you'll learn to master the exotic sounds of the Japanese Hirajoshi Pentatonic...

7. [Japanese Exotic Scales | Shredaholic.com | Mobile Version](http://www.shredaholic.com/user48.html) - Hi this time I wish to talk about five scales that have become more or less known among guitarists; ...

8. [Boogie Woogie Left Hand - Mike Taylor Piano](http://www.miketaylorpiano.co.uk/boogie-left-hand/)

9. [Shell Voicings For Jazz Piano](https://www.pianogroove.com/jazz-piano-lessons/shell-voicings-for-jazz-piano/) - Learn how to play shell voicings which contain just the root, 3rd, and 7th of the chord. We take the...

10. [Rootless Chord Voicings - TJPS](https://www.thejazzpianosite.com/jazz-piano-lessons/jazz-chord-voicings/rootless-voicings/) - A popular Jazz Chord Voicings are the (Bill Evans style) Rootless Chord Voicings. As the name sugges...

11. [Jazz Piano Chord Voicings - The Complete Guide](https://pianowithjonny.com/piano-lessons/jazz-piano-chord-voicings-the-complete-guide/) - In small group settings that include a bass player, rootless voicings enable the jazz pianist to gen...

12. [10 WAYS TO COMP WITH LEFT HAND #latin #jazz #piano - YouTube](https://www.youtube.com/watch?v=WmuoFb-8Xfc) - In this video I am demonstrating left hand comping ideas for latin jazz piano. You can apply this me...

13. [String Skipping - A Minor Pentatonic Scale - Ex 1 - Fret Success](https://fretsuccess.com/free-guitar-lessons/techniques/string-skipping-a-minor-pentatonic-scale-ex-1/) - It's exactly what it sounds like: instead of playing every string in order, you “jump over” one or m...

14. [21 pentatonic licks to spice up your solos - Guitar Pro Blog](https://www.guitar-pro.com/blog/p/34480-21-pentatonic-licks-to-spice-up-your-solos) - In this article, you will discover 21 licks using the pentatonic scale that will inspire new concept...

15. [Improvising With Caged...](https://www.pickupmusic.com/blog/what-is-the-caged-system) - The CAGED system is a popular method for learning and playing the guitar. It helps you to visualize ...

16. [JAZZ Enclosure/Approach notes/ Chromatics: TARGET ...](https://jazzimproviser.com/enclosure-approach-notes-jazz-chromatics/) - Enclosure,Target tones,Approach notes in jazz improvisation: See chord tones are “on” the beat [Stro...

17. [[QUESTION] How did you transition to targeting chord tones from playing through scales while improvising](https://www.reddit.com/r/Guitar/comments/ujrv4f/question_how_did_you_transition_to_targeting/)

18. [5 Guitar lick ideas to up your game when improvising. Guitar Lesson - EP581](https://www.youtube.com/watch?v=WYj6UdEg1wg) - In this week's guitar lesson, you'll learn 5 guitar lick ideas that can make you sound like a pro! Y...

19. [Sean McGowan | How I Play | Improvising with CAGED](https://www.youtube.com/watch?v=D_egrxV24HQ) - This free lesson is brought to you by the Acoustic Guitar Teaching Artists. Patreon members at the t...

20. [The CAGED System for Guitar – Unlock the Entire Fretboard](https://www.youtube.com/watch?v=65s8eIkfwNg) - Want to unlock the entire guitar fretboard? This lesson breaks down the CAGED system for guitar — on...

21. [Motif Development: Techniques & Examples - Music - StudySmarter](https://www.studysmarter.co.uk/explanations/music/music-composition/motif-development/) - Techniques for motif development include augmentation, diminution, inversion, retrograde, fragmentat...

22. [Jazz Guitar Improvisation Using Motivic Development](https://www.jazzguitarlessons.net/blog/jazz-guitar-improvisation-motivic-development) - Jazz guitar improvisation lesson using motivic development (by Matt Warnock) includes TABS.

23. [Motivic Development - YouTube](https://www.youtube.com/watch?v=_25VW6Q8aDI) - How Do I Practice Motivic Development for Jazz Improvisation? Jeremy ... How to Develop a Motive in ...

24. [Motivic development in jazz improvisation - YouTube](https://www.youtube.com/watch?v=_P53hN1vDJo) - In this lesson i show a few variations on the same motive using motivic development techniques like ...

25. [Motivic Improv, Part 3: More Melodic Variation + Rhythmic Variation](https://www.youtube.com/watch?v=AFwhvR-OIgc) - 0:00 Intro/Recap 0:39 Exercise #5 1:54 Rhythmic Variation 3:42 Exercise #6 4:42 Rhythmic Var. Demo 5...

26. [Scales - Music Theory for the 21st-Century Classroom](https://musictheory.pugetsound.edu/mt21c/JazzScales.html) - In this section on scales, our primary concern will be understanding how scales relate to correspond...

