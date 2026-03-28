/**
 * Improv Generator Mode
 * Piano keyboard with scale highlighting, guitar fretboard, tab display, pattern animation
 */

const IMPROV_CHROMATIC = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
const IMPROV_SCALES = {
    // Diatonic Modes
    'Major':            [0,2,4,5,7,9,11],
    'Natural Minor':    [0,2,3,5,7,8,10],
    'Dorian':           [0,2,3,5,7,9,10],
    'Phrygian':         [0,1,3,5,7,8,10],
    'Lydian':           [0,2,4,6,7,9,11],
    'Mixolydian':       [0,2,4,5,7,9,10],
    'Locrian':          [0,1,3,5,6,8,10],
    // Minor Variants
    'Harmonic Minor':   [0,2,3,5,7,8,11],
    'Melodic Minor':    [0,2,3,5,7,9,11],
    'Jazz Minor':       [0,2,3,5,7,9,11],
    // Jazz / Modern
    'Lydian Dominant':  [0,2,4,6,7,9,10],
    'Altered':          [0,1,3,4,6,8,10],
    'Phrygian Dominant':[0,1,4,5,7,8,10],
    // Bebop
    'Dominant Bebop':   [0,2,4,5,7,9,10,11],
    'Major Bebop':      [0,2,4,5,7,8,9,11],
    'Minor Bebop':      [0,2,3,5,7,8,9,10],
    // Symmetric
    'Whole Tone':       [0,2,4,6,8,10],
    'Diminished HW':    [0,1,3,4,6,7,9,10],
    'Whole-Half Diminished': [0,2,3,5,6,8,9,11],
    'Prometheus':       [0,2,4,6,9,10],
    'Enigmatic':        [0,1,4,6,8,10,11],
    // Pentatonic / Blues
    'Pentatonic Major': [0,2,4,7,9],
    'Pentatonic Minor': [0,3,5,7,10],
    'Blues':             [0,3,5,6,7,10],
    'Dominant Pentatonic': [0,2,4,7,10],
    'Egyptian':         [0,2,5,7,10],
    'Scottish Pentatonic': [0,2,5,7,9],
    // World / Ethnic
    'Persian':          [0,1,4,5,6,8,11],
    'Byzantine':        [0,1,4,5,7,8,11],
    'Neapolitan Minor': [0,1,3,5,7,8,11],
    'Neapolitan Major': [0,1,3,5,7,9,11],
    'Hungarian Minor':  [0,2,3,6,7,8,11],
    'Hungarian Major':  [0,3,4,6,7,9,10],
    'Romanian Major':   [0,1,4,6,7,9,10],
    'Arabian':          [0,2,4,5,6,8,10],
    'Asian':            [0,1,4,5,6,9,10],
    'Javanese Pelog':   [0,1,3,5,7,9,10],
    // Japanese Pentatonic
    'Hirajoshi':        [0,2,3,7,8],
    'In Sen':           [0,1,5,7,10],
    'Iwato':            [0,1,5,6,10],
    'Kumoi':            [0,2,5,7,8],
    'Balinese Pelog':   [0,1,3,7,8],
};

const SCALE_CATEGORIES = {
    'Beginner':    ['Major', 'Natural Minor', 'Pentatonic Major', 'Pentatonic Minor', 'Blues'],
    'Common':      ['Harmonic Minor', 'Melodic Minor', 'Jazz Minor'],
    'Modes':       ['Dorian', 'Phrygian', 'Lydian', 'Mixolydian', 'Locrian'],
    'Jazz':        ['Lydian Dominant', 'Altered', 'Phrygian Dominant'],
    'Bebop':       ['Dominant Bebop', 'Major Bebop', 'Minor Bebop'],
    'Symmetric':   ['Whole Tone', 'Diminished HW', 'Whole-Half Diminished', 'Prometheus', 'Enigmatic'],
    'Pentatonic':  ['Dominant Pentatonic', 'Egyptian', 'Scottish Pentatonic'],
    'World':       ['Persian', 'Byzantine', 'Neapolitan Minor', 'Neapolitan Major', 'Hungarian Minor',
                    'Hungarian Major', 'Romanian Major', 'Arabian', 'Asian', 'Javanese Pelog'],
    'Japanese':    ['Hirajoshi', 'In Sen', 'Iwato', 'Kumoi', 'Balinese Pelog'],
};

const SCALE_METADATA = {
    'Major':              {mood: 'Bright, Happy',         category: 'Beginner',  chords: ['maj','maj7']},
    'Natural Minor':      {mood: 'Sad, Dark',             category: 'Beginner',  chords: ['min','min7']},
    'Pentatonic Major':   {mood: 'Open, Cheerful',        category: 'Beginner',  chords: ['maj','6']},
    'Pentatonic Minor':   {mood: 'Bluesy, Soulful',       category: 'Beginner',  chords: ['min','7']},
    'Blues':              {mood: 'Gritty, Expressive',     category: 'Common',    chords: ['7','min7']},
    'Harmonic Minor':     {mood: 'Classical, Dramatic',    category: 'Common',    chords: ['min(maj7)','dim7']},
    'Melodic Minor':      {mood: 'Smooth, Jazz',           category: 'Common',    chords: ['min(maj7)']},
    'Jazz Minor':        {mood: 'Smooth, Modern',         category: 'Jazz',      chords: ['min(maj7)']},
    'Dorian':            {mood: 'Cool, Mellow',           category: 'Modes',     chords: ['min7','min9']},
    'Phrygian':          {mood: 'Spanish, Dark',          category: 'Modes',     chords: ['min7','sus4b9']},
    'Lydian':            {mood: 'Dreamy, Floating',       category: 'Modes',     chords: ['maj7#11']},
    'Mixolydian':        {mood: 'Bluesy, Rock',           category: 'Modes',     chords: ['7','9','13']},
    'Locrian':           {mood: 'Unstable, Tense',        category: 'Modes',     chords: ['min7b5']},
    'Lydian Dominant':   {mood: 'Bright, Tension',        category: 'Jazz',      chords: ['7#11']},
    'Altered':           {mood: 'Tense, Chromatic',       category: 'Jazz',      chords: ['7alt','7#9b13']},
    'Phrygian Dominant': {mood: 'Flamenco, Exotic',       category: 'Jazz',      chords: ['V7','7b9']},
    'Dominant Bebop':    {mood: 'Swinging, Chromatic',     category: 'Bebop',     chords: ['7','9']},
    'Major Bebop':       {mood: 'Swinging, Bright',       category: 'Bebop',     chords: ['maj7','6']},
    'Minor Bebop':       {mood: 'Swinging, Dark',         category: 'Bebop',     chords: ['min7']},
    'Whole Tone':        {mood: 'Dreamy, Impressionist',  category: 'Symmetric', chords: ['7#5','aug']},
    'Diminished HW':     {mood: 'Tense, Angular',         category: 'Symmetric', chords: ['dim7','7b9']},
    'Whole-Half Diminished': {mood: 'Eerie, Symmetrical', category: 'Symmetric', chords: ['dim7']},
    'Prometheus':        {mood: 'Other-worldly, Mystic',  category: 'Symmetric', chords: ['7#11']},
    'Enigmatic':         {mood: 'Chromatic, Intense',     category: 'Symmetric', chords: []},
    'Dominant Pentatonic': {mood: 'Bluesy, Dominant',     category: 'Pentatonic',chords: ['7','9']},
    'Egyptian':          {mood: 'Open, Suspended',        category: 'Pentatonic',chords: ['sus2','sus4']},
    'Scottish Pentatonic': {mood: 'Open, Folkloric',      category: 'Pentatonic',chords: ['sus2']},
    'Persian':           {mood: 'Middle Eastern, Tense',  category: 'World',     chords: ['maj','maj7']},
    'Byzantine':         {mood: 'Majestic, Eastern',      category: 'World',     chords: ['maj','7b9']},
    'Neapolitan Minor':  {mood: 'Dark, Classical',        category: 'World',     chords: ['min(maj7)']},
    'Neapolitan Major':  {mood: 'Warm, Classical',        category: 'World',     chords: ['maj7']},
    'Hungarian Minor':   {mood: 'Dark, Exotic',           category: 'World',     chords: ['min(maj7)','dim7']},
    'Hungarian Major':   {mood: 'Dominant, Exotic',       category: 'World',     chords: ['7','7b9']},
    'Romanian Major':    {mood: 'Tense, Lydian',          category: 'World',     chords: ['7','7#11']},
    'Arabian':           {mood: 'Desert, Mysterious',     category: 'World',     chords: ['7b5']},
    'Asian':             {mood: 'Eastern, Minor',         category: 'World',     chords: ['min','sus4']},
    'Javanese Pelog':    {mood: 'Indonesian, Soft',       category: 'World',     chords: ['min7','sus2']},
    'Hirajoshi':         {mood: 'Sparse, Mysterious',     category: 'Japanese',  chords: ['min','min7']},
    'In Sen':            {mood: 'Dark, Stark',            category: 'Japanese',  chords: ['min7','sus4']},
    'Iwato':             {mood: 'Dissonant, Haunting',    category: 'Japanese',  chords: ['min7b5']},
    'Kumoi':             {mood: 'Gentle, Wistful',        category: 'Japanese',  chords: ['min','sus4']},
    'Balinese Pelog':    {mood: 'Exotic, Mystical',       category: 'Japanese',  chords: ['min','sus2']},
};
const IMPROV_PATTERNS = {
    // Classical / Beginner
    'Block Chords':    { seq: [[1,3,5]], desc: 'All chord tones simultaneously', vibe: ['all'] },
    'Alberti Bass':    { seq: [1,5,3,5], desc: 'Root-fifth-third-fifth pattern', vibe: ['classical','beginner'] },
    'Waltz':           { seq: [1,[3,5],[3,5]], desc: 'Classic 3/4 oom-pah-pah', vibe: ['classical','romantic'] },
    'Arpeggio Up':     { seq: [1,3,5,8], desc: 'Rising broken chord', vibe: ['all'] },
    'Arpeggio Down':   { seq: [8,5,3,1], desc: 'Falling broken chord', vibe: ['all'] },
    // Jazz
    'Walking Bass':    { seq: [1,2,3,5], desc: 'Stepwise ascending movement', vibe: ['jazz','swing'] },
    'Stride':          { seq: [1,[3,5,8]], desc: 'Low bass then mid-range chord', vibe: ['jazz','ragtime'] },
    'Shell Voicing':   { seq: [[1,7]], desc: 'Root + 7th only (Bud Powell style)', vibe: ['jazz','bebop'] },
    'Shell Voicing Alt': { seq: [[1,3]], desc: 'Root + 3rd shell variation', vibe: ['jazz','bebop'] },
    'Rootless A':      { seq: [[3,5,7,9]], desc: 'Bill Evans-style 3-5-7-9 voicing', vibe: ['jazz','voicing'] },
    'Rootless B':      { seq: [[7,9,3,5]], desc: 'Inverted rootless 7-9-3-5 voicing', vibe: ['jazz','voicing'] },
    'Quartal Voicing': { seq: [[1,4,7]], desc: 'Stacked 4ths (McCoy Tyner)', vibe: ['jazz','modal','voicing'] },
    'Quartal Quartal': { seq: [[4,7,3]], desc: 'Wider quartal stack', vibe: ['jazz','modal','voicing'] },
    // Boogie / Blues
    'Boogie Shuffle':  { seq: [1,5,6,5], desc: 'Root-fifth-sixth-fifth swing', vibe: ['boogie','blues'] },
    'Boogie Chop':     { seq: [1,8,1,8], desc: 'Octave jump country/rock boogie', vibe: ['boogie','rock'] },
    'Boogie Ascending':{ seq: [1,2,3,4,5,6,5,3], desc: 'Walking chromatic climb', vibe: ['boogie','blues'] },
    '12-Bar Groove':   { seq: [1,5,1,5,[1,5],[1,5]], desc: 'Alternating bass + power chords', vibe: ['boogie','blues','rock'] },
    'Shuffle Split':   { seq: [1,[3,5],1,[3,5]], desc: 'Low root, staccato chord hits', vibe: ['boogie','blues'] },
    // Funk / Gospel
    'Gospel Chop':     { seq: [[1,5],[3,7],[1,5],[3,7,9]], desc: 'Alternating bass chord + extension', vibe: ['gospel','soul'] },
    'Funk Stab':       { seq: [[1,3,7],0,[1,3,7],0], desc: 'Chord stabs with rests', vibe: ['funk','r&b'] },
    'Syncopated Bass': { seq: [1,0,5,1,0,5,3,5], desc: 'Off-beat bass movement', vibe: ['funk','pop'] },
    'New Orleans':     { seq: [1,3,5,3,[1,5],3,5,3], desc: 'Circular bass phrase', vibe: ['blues','gospel'] },
    // Latin
    'Bossa Nova':      { seq: [1,5,8,5,1,5,3,5], desc: 'Syncopated Latin rhythm', vibe: ['latin','jazz'] },
    'Montuno':         { seq: [1,3,5,3,8,5,3,5], desc: 'Cuban repeated figure', vibe: ['latin','salsa'] },
    'Songo':           { seq: [1,0,5,0,[1,5],0,3,0], desc: 'Afro-Cuban with rests', vibe: ['latin','afrocuban'] },
    'Cha-Cha':         { seq: [1,1,5,5,1,0,5,0], desc: 'Steady cha-cha-cha feel', vibe: ['latin','pop'] },
    'Mambo Bass':      { seq: [1,5,8,5,1,0,8,5], desc: 'Driving mambo left hand', vibe: ['latin','salsa'] },
    // Ostinato / Drone
    'Open Fifth Ostinato': { seq: [[1,5],[1,5],[1,5],[1,5]], desc: 'Power-chord drone', vibe: ['modal','rock','drone'] },
    'Two-Note Bass Vamp':  { seq: [1,0,1,0,5,0,5,0], desc: 'Alternating root/fifth pedal', vibe: ['modal','drone'] },
    'Pedal Bass':      { seq: [1,1,1,1], desc: 'Static bass note tension builder', vibe: ['modal','drone'] },
    'Rhumba Clave':    { seq: [1,0,0,5,0,1,0,0], desc: '3-2 clave feel in bass', vibe: ['latin','afrocuban'] },
};

const PIANO_PATTERN_CATEGORIES = {
    'Classical':    ['Block Chords', 'Alberti Bass', 'Waltz', 'Arpeggio Up', 'Arpeggio Down'],
    'Jazz':         ['Walking Bass', 'Stride', 'Shell Voicing', 'Shell Voicing Alt'],
    'Voicings':     ['Rootless A', 'Rootless B', 'Quartal Voicing', 'Quartal Quartal'],
    'Boogie/Blues': ['Boogie Shuffle', 'Boogie Chop', 'Boogie Ascending', '12-Bar Groove', 'Shuffle Split'],
    'Funk/Gospel':  ['Gospel Chop', 'Funk Stab', 'Syncopated Bass', 'New Orleans'],
    'Latin':        ['Bossa Nova', 'Montuno', 'Songo', 'Cha-Cha', 'Mambo Bass'],
    'Ostinato':     ['Open Fifth Ostinato', 'Two-Note Bass Vamp', 'Pedal Bass', 'Rhumba Clave'],
};
const GUITAR_PATTERNS = {
    // Position / Box
    'Box Pattern I':       { type: 'position', position: 1, direction: 'up-down', technique: 'alternate', desc: 'Standard pentatonic box 1 ascending/descending', style: ['blues','rock'] },
    'Box Pattern II':      { type: 'position', position: 2, direction: 'up-down', technique: 'alternate', desc: 'Box 2 — extends range up the neck', style: ['blues','rock'] },
    // Three-Note-Per-String
    '3 Note Per String':   { type: 'nps', notes_per_string: 3, direction: 'up', technique: 'alternate', desc: '3 notes per string across all 6 strings', style: ['shred','metal'] },
    // String Skipping
    'String Skip Up':      { type: 'skip', skip_size: 1, direction: 'up', desc: 'Skip every other string ascending for wider intervals', style: ['modern','jazz'] },
    'String Skip Down':    { type: 'skip', skip_size: 1, direction: 'down', desc: 'Reverse string skip descending', style: ['modern'] },
    // Single String
    'Horizontal 1-String': { type: 'single', string: 1, direction: 'up', desc: 'All notes on one string — slide feel', style: ['country','blues'] },
    // CAGED
    'CAGED Arpeggios':     { type: 'caged', direction: 'up-down', desc: 'Arpeggiate chord shape across neck', style: ['all'] },
    // Melodic
    'Enclosure Lick':      { type: 'melodic', pattern: 'enclosure', desc: 'Half-step above + below chord tone to target', style: ['jazz','bebop'] },
    'Chord Tone Target':   { type: 'melodic', pattern: 'target', desc: 'Land on R/3/5/7 on downbeat each bar', style: ['jazz','blues'] },
    'Repeated Motif':      { type: 'motif', desc: '2-3 note idea repeated at different scale positions', style: ['all'] },
    'Pedal Tone':          { type: 'melodic', pattern: 'pedal', desc: 'Repeated open/fretted note under melody', style: ['country','bluegrass'] },
    // Harmonic
    'Double Stops':        { type: 'harmonic', interval: 3, desc: 'Two-note harmonies (3rds) throughout scale', style: ['country','soul','blues'] },
    'Harmonised 6ths':     { type: 'harmonic', interval: 6, desc: 'Scale in parallel 6ths — two strings', style: ['country','blues'] },
};

const GUITAR_PATTERN_CATEGORIES = {
    'Box/Position': ['Box Pattern I', 'Box Pattern II', '3 Note Per String'],
    'String Skip':  ['String Skip Up', 'String Skip Down', 'Horizontal 1-String'],
    'CAGED':        ['CAGED Arpeggios'],
    'Melodic':      ['Enclosure Lick', 'Chord Tone Target', 'Repeated Motif', 'Pedal Tone'],
    'Harmonic':     ['Double Stops', 'Harmonised 6ths'],
};

const CAGED_POSITIONS = {
    'E Shape': { root_string: 6, root_fret_offset: 0 },
    'D Shape': { root_string: 4, root_fret_offset: 0 },
    'C Shape': { root_string: 5, root_fret_offset: 3 },
    'A Shape': { root_string: 5, root_fret_offset: 0 },
    'G Shape': { root_string: 6, root_fret_offset: 5 },
};

const MOTIF_DEFINITIONS = {
    'Rising 3rd':         { intervals: [0, 2], rhythm: [1.0, 1.0], direction: 'up', desc: 'Simple ascending 3rd', style: ['all'] },
    'Call Riff':          { intervals: [1, 3, 2, 1], rhythm: [0.5, 0.5, 0.5, 1.5], direction: 'mixed', desc: 'Classic jazz call figure — resolves to root', style: ['jazz', 'blues'] },
    'Pentatonic Drop':    { intervals: [5, 4, 3, 1], rhythm: [0.5, 0.5, 0.5, 0.5], direction: 'down', desc: 'Falling pentatonic lick from 5th to root', style: ['rock', 'blues', 'country'] },
    'Blues Wail':         { intervals: [5, 4, 3, 4, 3], rhythm: [1.0, 0.5, 0.5, 0.5, 1.5], direction: 'mixed', desc: 'Bent blues cry — 5 to 4 with linger', style: ['blues'] },
    'Jazz Enclosure':     { intervals: [3, 1, 2, 3], rhythm: [0.5, 0.5, 0.5, 1.5], direction: 'up', desc: 'Approach target from chromatic above + below', style: ['jazz', 'bebop'] },
    'Ascending Sequence': { intervals: [1, 2, 3, 2, 3, 4, 3, 4, 5], rhythm: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], direction: 'up', desc: 'Stepwise sequence climbing in overlapping 3rds', style: ['jazz', 'classical'] },
};

const MOTIF_TRANSFORMATIONS = ['transpose', 'invert', 'retrograde', 'augment', 'diminish', 'fragment', 'displace'];

function generateMotif(difficulty) {
    const pool = Object.keys(MOTIF_DEFINITIONS);
    const baseName = pool[Math.floor(Math.random() * pool.length)];
    const base = MOTIF_DEFINITIONS[baseName];

    const nTransforms = Math.min(Math.floor(difficulty / 3), MOTIF_TRANSFORMATIONS.length);
    const shuffled = [...MOTIF_TRANSFORMATIONS].sort(() => Math.random() - 0.5);
    const transforms = shuffled.slice(0, nTransforms);

    let intervals = [...base.intervals];
    let rhythm = [...base.rhythm];

    for (const t of transforms) {
        if (t === 'transpose') {
            const shift = [-2, -1, 1, 2][Math.floor(Math.random() * 4)];
            intervals = intervals.map(x => x + shift);
        } else if (t === 'invert') {
            intervals = intervals.map(x => -x);
        } else if (t === 'retrograde') {
            intervals.reverse();
            rhythm.reverse();
        } else if (t === 'augment') {
            rhythm = rhythm.map(r => r * 2);
        } else if (t === 'diminish') {
            rhythm = rhythm.map(r => r / 2);
        } else if (t === 'fragment') {
            const n = Math.max(2, Math.floor(intervals.length / 2));
            intervals = intervals.slice(0, n);
            rhythm = rhythm.slice(0, n);
        } else if (t === 'displace') {
            intervals = [...intervals.slice(1), intervals[0]];
        }
    }

    return {
        baseName,
        transforms,
        intervals,
        rhythm,
        desc: base.desc,
        direction: base.direction,
    };
}

const VIBE_PRESETS = {
    'All':       { scales: null, patternVibes: null, motifStyles: null },
    'Jazzy':     { scales: ['Dorian', 'Altered', 'Lydian Dominant', 'Dominant Bebop', 'Major Bebop', 'Minor Bebop', 'Jazz Minor', 'Lydian', 'Mixolydian', 'Whole Tone', 'Diminished HW'],
                   patternVibes: ['jazz', 'swing', 'bebop', 'voicing', 'modal'], motifStyles: ['jazz', 'bebop'] },
    'Bluesy':    { scales: ['Blues', 'Pentatonic Minor', 'Dominant Pentatonic', 'Mixolydian', 'Dorian'],
                   patternVibes: ['blues', 'boogie', 'soul'], motifStyles: ['blues', 'rock', 'country'] },
    'World':     { scales: ['Hungarian Minor', 'Hungarian Major', 'Byzantine', 'Persian', 'Romanian Major', 'Arabian', 'Asian', 'Javanese Pelog', 'Hirajoshi', 'In Sen', 'Iwato', 'Kumoi', 'Balinese Pelog', 'Phrygian Dominant'],
                   patternVibes: ['latin', 'afrocuban', 'drone'], motifStyles: ['all'] },
    'Classical': { scales: ['Major', 'Natural Minor', 'Harmonic Minor', 'Melodic Minor', 'Neapolitan Minor', 'Neapolitan Major'],
                   patternVibes: ['classical', 'beginner', 'romantic'], motifStyles: ['classical', 'all'] },
    'Modal':     { scales: ['Dorian', 'Lydian', 'Phrygian', 'Mixolydian', 'Whole Tone', 'Locrian'],
                   patternVibes: ['modal', 'drone'], motifStyles: ['all'] },
};

const GUITAR_OPEN = [40,45,50,55,59,64]; // E2 A2 D3 G3 B3 E4
const GUITAR_FRET_COUNT = 15;
const BLACK_KEYS = new Set([1,3,6,8,10]); // semitones that are black keys

class ImprovGenerator {
    constructor() {
        this.currentKey = 'C';
        this.currentScale = 'Major';
        this.currentPattern = 'Block Chords';
        this.instrument = 'piano';
        this.currentMotif = null;
        this.currentVibe = 'All';
        this.scaleNotes = [];
        this.patternMidi = [];
        this.currentStepIndex = 0;
        this.patternAnimId = null;
    }

    async init() {
        const container = document.getElementById('improv-content');
        if (!container) return;

        container.innerHTML = `
            <div class="instrument-toggle">
                <div class="instrument-btn selected" id="improv-btn-piano">Piano</div>
                <div class="instrument-btn" id="improv-btn-guitar">Guitar</div>
            </div>

            <div class="improv-main">
                <div class="scale-display">
                    <div class="scale-name" id="improv-display">C Major</div>
                    <div class="scale-mood" id="improv-scale-mood"></div>
                </div>

                <div id="improv-main-keyboard" class="keyboard-container"></div>
                <div id="improv-guitar-fretboard" class="fretboard-container hidden"></div>

                <div class="pattern-section">
                    <div class="pattern-header">
                        <span class="pattern-label">Pattern:</span>
                        <span class="pattern-name" id="improv-pattern-display">Block Chords</span>
                    </div>
                    <div class="pattern-desc" id="improv-pattern-desc">All chord tones simultaneously</div>
                    <div id="improv-pattern-keyboard" class="keyboard-container mini-container"></div>
                    <div id="improv-guitar-tab" class="tab-container hidden"></div>
                </div>

                <div class="motif-section" id="improv-motif-section" style="display:none">
                    <div class="motif-header">
                        <span class="motif-label">Motif:</span>
                        <span class="motif-name" id="improv-motif-name"></span>
                    </div>
                    <div class="motif-degrees" id="improv-motif-degrees"></div>
                    <div class="motif-rhythm" id="improv-motif-rhythm"></div>
                    <div class="motif-transforms" id="improv-motif-transforms"></div>
                </div>
            </div>

            <div class="vibe-filters" id="improv-vibe-filters">
                ${Object.keys(VIBE_PRESETS).map(v =>
                    `<div class="vibe-btn ${v===this.currentVibe?'active':''}" data-vibe="${v}">${v}</div>`
                ).join('')}
            </div>

            <div class="controls">
                <div class="control-row">
                    <label>Key:</label>
                    <select id="improv-key">
                        ${IMPROV_CHROMATIC.map(k => `<option value="${k}" ${k===this.currentKey?'selected':''}>${k}</option>`).join('')}
                    </select>
                </div>
                <div class="control-row">
                    <label>Scale:</label>
                    <select id="improv-scale">
                        ${Object.entries(SCALE_CATEGORIES).map(([cat, scales]) =>
                            `<optgroup label="${cat}">${scales.map(s =>
                                `<option value="${s}" ${s===this.currentScale?'selected':''}>${s}</option>`
                            ).join('')}</optgroup>`
                        ).join('')}
                    </select>
                </div>
                <div class="control-row">
                    <label>Pattern:</label>
                    <select id="improv-pattern">
                        ${this._buildPatternOptions()}
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary btn-large" id="improv-generate">Generate New</button>
                </div>
            </div>
        `;

        document.getElementById('improv-key').addEventListener('change', (e) => {
            this.currentKey = e.target.value;
            this.updateDisplay();
        });
        document.getElementById('improv-scale').addEventListener('change', (e) => {
            this.currentScale = e.target.value;
            this.updateDisplay();
        });
        document.getElementById('improv-pattern').addEventListener('change', (e) => {
            this.currentPattern = e.target.value;
            this.updateDisplay();
        });
        document.getElementById('improv-generate').addEventListener('click', () => this.generate());
        document.getElementById('improv-btn-piano').addEventListener('click', () => this.setInstrument('piano'));
        document.getElementById('improv-btn-guitar').addEventListener('click', () => this.setInstrument('guitar'));

        // Vibe filter buttons
        document.querySelectorAll('.vibe-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentVibe = btn.dataset.vibe;
                document.querySelectorAll('.vibe-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        this.updateDisplay();
    }

    setInstrument(inst) {
        this.instrument = inst;
        document.getElementById('improv-btn-piano').className = 'instrument-btn' + (inst === 'piano' ? ' selected' : '');
        document.getElementById('improv-btn-guitar').className = 'instrument-btn' + (inst === 'guitar' ? ' selected' : '');

        this._refreshPatternDropdown();

        const kb = document.getElementById('improv-main-keyboard');
        const fb = document.getElementById('improv-guitar-fretboard');
        const pkb = document.getElementById('improv-pattern-keyboard');
        const tab = document.getElementById('improv-guitar-tab');

        if (inst === 'piano') {
            if (kb) kb.classList.remove('hidden');
            if (fb) fb.classList.add('hidden');
            if (pkb) pkb.classList.remove('hidden');
            if (tab) tab.classList.add('hidden');
        } else {
            if (kb) kb.classList.add('hidden');
            if (fb) fb.classList.remove('hidden');
            if (pkb) pkb.classList.add('hidden');
            if (tab) tab.classList.remove('hidden');
        }
        this.updateDisplay();
    }

    // --- Pattern dropdown builder ---

    _getActivePatterns() {
        if (this.instrument === 'guitar') return GUITAR_PATTERNS;
        return IMPROV_PATTERNS;
    }

    _getActivePatternCategories() {
        if (this.instrument === 'guitar') return GUITAR_PATTERN_CATEGORIES;
        return PIANO_PATTERN_CATEGORIES;
    }

    _buildPatternOptions() {
        const categories = this._getActivePatternCategories();
        return Object.entries(categories).map(([cat, patterns]) =>
            `<optgroup label="${cat}">${patterns.map(p =>
                `<option value="${p}" ${p===this.currentPattern?'selected':''}>${p}</option>`
            ).join('')}</optgroup>`
        ).join('');
    }

    _refreshPatternDropdown() {
        const sel = document.getElementById('improv-pattern');
        if (!sel) return;
        sel.innerHTML = this._buildPatternOptions();
        // Ensure current pattern is valid for the active instrument
        const patterns = this._getActivePatterns();
        if (!patterns[this.currentPattern]) {
            this.currentPattern = Object.keys(patterns)[0];
            sel.value = this.currentPattern;
        }
    }

    // --- Music theory helpers ---

    getRootMidi(key, octave) {
        return IMPROV_CHROMATIC.indexOf(key) + (octave + 1) * 12;
    }

    isBlack(midi) {
        return BLACK_KEYS.has(midi % 12);
    }

    getScaleNotes() {
        const rootIdx = IMPROV_CHROMATIC.indexOf(this.currentKey);
        const intervals = IMPROV_SCALES[this.currentScale] || [0,2,4,5,7,9,11];
        const notes = [];
        // Two octaves starting from C3 (midi 48) up to C5 (midi 72)
        for (let oct = 3; oct <= 5; oct++) {
            for (const interval of intervals) {
                const midi = rootIdx + interval + (oct + 1) * 12;
                if (midi >= 48 && midi <= 84) notes.push(midi);
            }
        }
        return [...new Set(notes)].sort((a, b) => a - b);
    }

    getPatternMidi() {
        const patterns = this._getActivePatterns();
        const pat = patterns[this.currentPattern];
        if (!pat) return [];
        const scaleNotes = this.scaleNotes;
        if (!scaleNotes.length) return [];

        // Guitar patterns use a different rendering path
        if (this.instrument === 'guitar' && pat.type) return [];

        return pat.seq.map(step => {
            if (step === 0) return 0; // rest
            if (Array.isArray(step)) {
                return step.map(deg => scaleNotes[Math.min(deg - 1, scaleNotes.length - 1)] || scaleNotes[0]);
            }
            return scaleNotes[Math.min(step - 1, scaleNotes.length - 1)] || scaleNotes[0];
        });
    }

    // --- Piano keyboard rendering ---

    renderMainKeyboard() {
        const container = document.getElementById('improv-main-keyboard');
        if (!container) return;

        const rootPc = IMPROV_CHROMATIC.indexOf(this.currentKey);
        const startMidi = 48; // C3
        const endMidi = 77;   // ~2.5 octaves

        let html = '<div class="keyboard">';
        for (let midi = startMidi; midi <= endMidi; midi++) {
            const pc = midi % 12;
            const isBlk = this.isBlack(midi);
            const isInScale = this.scaleNotes.includes(midi);
            const isRoot = pc === rootPc;

            let cls = 'key ' + (isBlk ? 'black' : 'white');
            if (isRoot && isInScale) cls += ' root';
            else if (isInScale) cls += ' highlighted';

            html += `<div class="${cls}" data-midi="${midi}">`;
            if (isInScale) {
                html += `<span class="note-dot ${isRoot ? 'root-dot' : ''}"></span>`;
            }
            html += '</div>';
        }
        html += '</div>';
        container.innerHTML = html;
    }

    renderPatternKeyboard() {
        const container = document.getElementById('improv-pattern-keyboard');
        if (!container) return;

        const allNotes = [];
        this.patternMidi.forEach(step => {
            if (step === 0) return; // skip rests
            if (Array.isArray(step)) allNotes.push(...step);
            else allNotes.push(step);
        });
        if (!allNotes.length) { container.innerHTML = ''; return; }

        const minNote = Math.min(...allNotes) - 2;
        const maxNote = Math.max(...allNotes) + 2;
        const rootPc = IMPROV_CHROMATIC.indexOf(this.currentKey);

        const currentStep = this.patternMidi[this.currentStepIndex];
        const isRest = currentStep === 0;
        const activeNotes = isRest ? [] : (Array.isArray(currentStep) ? currentStep : (currentStep != null ? [currentStep] : []));

        let html = '<div class="keyboard mini">';
        for (let midi = minNote; midi <= maxNote; midi++) {
            const isBlk = this.isBlack(midi);
            const isActive = activeNotes.includes(midi);
            const isInPattern = allNotes.includes(midi) && !isActive;
            const isRoot = midi % 12 === rootPc;

            let cls = 'key ' + (isBlk ? 'black' : 'white');
            if (isRest) cls += ' rest-step';
            else if (isActive) cls += ' active';
            else if (isRoot && allNotes.includes(midi)) cls += ' root';
            else if (isInPattern) cls += ' in-pattern';

            html += `<div class="${cls}"></div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    // --- Guitar fretboard rendering ---

    getGuitarScalePositions() {
        const rootPc = IMPROV_CHROMATIC.indexOf(this.currentKey);
        const intervals = IMPROV_SCALES[this.currentScale] || [0,2,4,5,7,9,11];
        const scaleSet = new Set(intervals.map(i => (rootPc + i) % 12));

        const positions = [];
        for (let s = 0; s < 6; s++) {
            const stringPositions = [];
            for (let f = 0; f <= GUITAR_FRET_COUNT; f++) {
                const midi = GUITAR_OPEN[s] + f;
                const pc = midi % 12;
                if (scaleSet.has(pc)) {
                    stringPositions.push({ fret: f, midi, isRoot: pc === rootPc });
                }
            }
            positions.push(stringPositions);
        }
        return positions;
    }

    renderGuitarFretboard() {
        const container = document.getElementById('improv-guitar-fretboard');
        if (!container) return;

        const positions = this.getGuitarScalePositions();
        const stringNames = ['e','B','G','D','A','E'];
        const inlayFrets = [3,5,7,9,12,15];

        let html = '<div class="fretboard">';
        for (let s = 0; s < 6; s++) {
            const strIdx = 5 - s; // reverse order: high e first
            html += '<div class="guitar-string">';
            html += `<div class="string-label">${stringNames[s]}</div>`;
            html += '<div class="frets-container"><div class="string-line"></div>';

            for (let f = 0; f <= GUITAR_FRET_COUNT; f++) {
                const pos = positions[strIdx].find(p => p.fret === f);
                html += `<div class="fret">`;
                if (pos) {
                    html += `<div class="fret-dot visible ${pos.isRoot ? 'root' : ''}">${f}</div>`;
                }
                html += '</div>';
            }
            html += '</div></div>';
        }

        // Fret markers
        html += '<div class="fret-markers"><div class="fret-marker"></div>';
        for (let f = 1; f <= GUITAR_FRET_COUNT; f++) {
            const isInlay = inlayFrets.includes(f);
            html += `<div class="fret-marker ${isInlay ? 'inlay' : ''}">${isInlay ? (f === 12 ? '::' : '\u2022') : ''}</div>`;
        }
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;
    }

    renderGuitarTab() {
        const container = document.getElementById('improv-guitar-tab');
        if (!container) return;

        const positions = this.getGuitarScalePositions();
        const stringNames = ['e','B','G','D','A','E'];
        const seq = this.patternMidi;
        if (!seq.length) { container.innerHTML = ''; return; }

        let html = '<div class="tab-display">';
        for (let s = 0; s < 6; s++) {
            const strIdx = 5 - s;
            html += '<div class="tab-line">';
            html += `<div class="tab-string-label">${stringNames[s]}</div>`;
            html += '<div class="tab-content"><div class="tab-note">|</div>';

            for (let i = 0; i < seq.length; i++) {
                const step = seq[i];
                const isActive = i === this.currentStepIndex;

                if (step === 0) {
                    // Rest step
                    html += `<div class="tab-note ${isActive ? 'active-tab' : ''} rest-tab">.</div>`;
                    continue;
                }

                const notes = Array.isArray(step) ? step : [step];

                // Find if any note in this step can be played on this string
                let fretNum = null;
                for (const note of notes) {
                    const pos = positions[strIdx].find(p => p.midi === note);
                    if (pos) { fretNum = pos.fret; break; }
                }

                if (fretNum !== null) {
                    const isRoot = positions[strIdx].find(p => p.fret === fretNum)?.isRoot;
                    html += `<div class="tab-note ${isActive ? 'active-tab' : ''} ${isRoot ? 'root-tab' : ''}">${fretNum}</div>`;
                } else {
                    html += `<div class="tab-note ${isActive ? 'active-tab' : ''}">-</div>`;
                }
            }

            html += '<div class="tab-note">|</div></div></div>';
        }
        html += '</div>';
        container.innerHTML = html;
    }

    // --- Guitar pattern rendering ---

    renderGuitarPattern() {
        const container = document.getElementById('improv-guitar-tab');
        if (!container) return;

        const pat = GUITAR_PATTERNS[this.currentPattern];
        if (!pat) { container.innerHTML = ''; return; }

        const positions = this.getGuitarScalePositions();
        const rootPc = IMPROV_CHROMATIC.indexOf(this.currentKey);
        const rootMidi = rootPc; // pitch class

        // Build a flat list of all fretted notes for this scale
        const allFretNotes = [];
        for (let s = 0; s < 6; s++) {
            for (const pos of positions[s]) {
                allFretNotes.push({ string: s, fret: pos.fret, midi: pos.midi, isRoot: pos.isRoot });
            }
        }

        let sequence = [];

        if (pat.type === 'position') {
            // Box pattern: collect notes within a fret range
            const rootFrets = allFretNotes.filter(n => n.isRoot && n.string >= 4);
            const anchor = rootFrets.length ? rootFrets[0].fret : 0;
            const boxStart = Math.max(0, anchor - 1);
            const boxEnd = anchor + 4;
            sequence = allFretNotes
                .filter(n => n.fret >= boxStart && n.fret <= boxEnd)
                .sort((a, b) => a.string - b.string || a.fret - b.fret);
            if (pat.direction === 'up-down') {
                sequence = [...sequence, ...sequence.slice().reverse().slice(1)];
            }
        } else if (pat.type === 'nps') {
            // 3 notes per string
            for (let s = 0; s < 6; s++) {
                const stringNotes = positions[s].sort((a, b) => a.fret - b.fret);
                sequence.push(...stringNotes.slice(0, pat.notes_per_string));
            }
        } else if (pat.type === 'skip') {
            // String skip: play notes on every other string
            const strings = pat.direction === 'down' ? [5,3,1,4,2,0] : [0,2,4,1,3,5];
            for (const s of strings) {
                const stringNotes = positions[s].sort((a, b) => a.fret - b.fret);
                if (stringNotes.length) sequence.push(stringNotes[0]);
            }
        } else if (pat.type === 'single') {
            // Single string: all notes on one string
            const s = Math.min(pat.string, 5);
            sequence = positions[s].sort((a, b) => a.fret - b.fret);
        } else if (pat.type === 'caged') {
            // Use first CAGED shape found near root
            const rootFrets = allFretNotes.filter(n => n.isRoot);
            const anchor = rootFrets.length ? rootFrets[0].fret : 0;
            sequence = allFretNotes
                .filter(n => n.fret >= anchor && n.fret <= anchor + 5)
                .sort((a, b) => a.string - b.string || a.fret - b.fret);
            if (pat.direction === 'up-down') {
                sequence = [...sequence, ...sequence.slice().reverse().slice(1)];
            }
        } else if (pat.type === 'harmonic') {
            // Double stops / 6ths: pairs of notes on adjacent strings
            for (let s = 0; s < 5; s++) {
                const lower = positions[s].sort((a, b) => a.fret - b.fret);
                const upper = positions[s + 1].sort((a, b) => a.fret - b.fret);
                if (lower.length && upper.length) {
                    sequence.push({ pair: [lower[0], upper[0]], string: s });
                }
            }
        } else {
            // Melodic patterns (enclosure, target, pedal, motif): show scale notes sequentially
            sequence = allFretNotes.sort((a, b) => a.string - b.string || a.fret - b.fret);
        }

        // Render as description + note indicators
        const stringNames = ['e','B','G','D','A','E'];
        let html = `<div class="guitar-pattern-info">`;
        html += `<div class="guitar-pattern-type">${pat.type.toUpperCase()}</div>`;
        html += `<div class="guitar-pattern-desc">${pat.desc}</div>`;
        html += `</div>`;

        // Show a simplified tab of the sequence
        if (sequence.length) {
            html += '<div class="tab-display">';
            const maxSteps = Math.min(sequence.length, 16);
            for (let s = 0; s < 6; s++) {
                const strIdx = 5 - s;
                html += '<div class="tab-line">';
                html += `<div class="tab-string-label">${stringNames[s]}</div>`;
                html += '<div class="tab-content"><div class="tab-note">|</div>';
                for (let i = 0; i < maxSteps; i++) {
                    const step = sequence[i];
                    if (step && step.pair) {
                        // Harmonic: check both notes
                        const match = step.pair.find(n => n && (5 - n.string) === s);
                        html += `<div class="tab-note">${match ? match.fret : '-'}</div>`;
                    } else if (step && (5 - step.string) === s) {
                        html += `<div class="tab-note ${step.isRoot ? 'root-tab' : ''}">${step.fret}</div>`;
                    } else {
                        html += '<div class="tab-note">-</div>';
                    }
                }
                html += '<div class="tab-note">|</div></div></div>';
            }
            html += '</div>';
        }

        container.innerHTML = html;
    }

    // --- Pattern animation ---

    startPatternAnimation() {
        this.stopPatternAnimation();
        this.currentStepIndex = 0;
        if (this.patternMidi.length <= 1 && this.instrument === 'piano') return;
        if (this.instrument === 'guitar' && GUITAR_PATTERNS[this.currentPattern]?.type) return; // no animation for guitar patterns

        this.patternAnimId = setInterval(() => {
            this.currentStepIndex = (this.currentStepIndex + 1) % this.patternMidi.length;
            if (this.instrument === 'piano') {
                this.renderPatternKeyboard();
            } else {
                this.renderGuitarTab();
            }
        }, 400);
    }

    stopPatternAnimation() {
        if (this.patternAnimId) {
            clearInterval(this.patternAnimId);
            this.patternAnimId = null;
        }
    }

    // --- Main update & generate ---

    // --- Motif rendering ---

    renderMotifPanel() {
        const section = document.getElementById('improv-motif-section');
        if (!section) return;

        if (!this.currentMotif) {
            section.style.display = 'none';
            return;
        }

        section.style.display = '';
        const motif = this.currentMotif;

        // Name and description
        const nameEl = document.getElementById('improv-motif-name');
        if (nameEl) nameEl.textContent = motif.baseName;

        // Scale degree notation
        const degreesEl = document.getElementById('improv-motif-degrees');
        if (degreesEl) {
            const degreeNames = motif.intervals.map(i => {
                if (i <= 0) return `${i}`;
                return `${i}`;
            });
            degreesEl.innerHTML = degreeNames.map(d =>
                `<span class="motif-degree">${d}</span>`
            ).join(' <span class="motif-dash">-</span> ');
        }

        // Rhythm dots
        const rhythmEl = document.getElementById('improv-motif-rhythm');
        if (rhythmEl) {
            rhythmEl.innerHTML = motif.rhythm.map(r => {
                if (r >= 1.0) return '<span class="motif-rhythm-dot filled">\u25CF</span>';
                if (r >= 0.5) return '<span class="motif-rhythm-dot half">\u25D2</span>';
                return '<span class="motif-rhythm-dot small">\u25CB</span>';
            }).join(' ');
        }

        // Transformation history
        const transEl = document.getElementById('improv-motif-transforms');
        if (transEl) {
            if (motif.transforms.length) {
                transEl.textContent = motif.transforms.map(t =>
                    t.charAt(0).toUpperCase() + t.slice(1)
                ).join(' + ') + ` of "${motif.baseName}"`;
            } else {
                transEl.textContent = motif.desc;
            }
        }
    }

    renderMotifHighlight() {
        if (!this.currentMotif) return;
        // Motif notes are highlighted via scale degree mapping
        // The motif intervals map to scale note indices
        const motifMidi = new Set();
        const scaleNotes = this.scaleNotes;
        for (const deg of this.currentMotif.intervals) {
            const idx = Math.max(0, Math.min(deg - 1, scaleNotes.length - 1));
            if (scaleNotes[idx]) motifMidi.add(scaleNotes[idx]);
        }

        // Add motif-highlight class to matching keys
        const keys = document.querySelectorAll('#improv-main-keyboard .key, #improv-guitar-fretboard .fret-dot');
        keys.forEach(el => {
            const midi = parseInt(el.dataset?.midi);
            if (motifMidi.has(midi)) {
                el.classList.add('motif-highlight');
            }
        });
    }

    // --- Main update & generate ---

    updateDisplay() {
        this.scaleNotes = this.getScaleNotes();
        this.patternMidi = this.getPatternMidi();
        this.currentStepIndex = 0;

        // Scale display with metadata
        const meta = SCALE_METADATA[this.currentScale];
        document.getElementById('improv-display').textContent = `${this.currentKey} ${this.currentScale}`;

        const moodEl = document.getElementById('improv-scale-mood');
        if (moodEl && meta) {
            let html = '';
            if (meta.category) html += `<span class="scale-category-badge">${meta.category}</span> `;
            html += `<span>${meta.mood}</span>`;
            if (meta.chords && meta.chords.length) {
                html += `<span class="scale-chords"> | ${meta.chords.join(', ')}</span>`;
            }
            moodEl.innerHTML = html;
        } else if (moodEl) {
            moodEl.textContent = '';
        }

        document.getElementById('improv-pattern-display').textContent = this.currentPattern;

        const patterns = this._getActivePatterns();
        const pat = patterns[this.currentPattern];
        const descEl = document.getElementById('improv-pattern-desc');
        if (descEl && pat) descEl.textContent = pat.desc;

        if (this.instrument === 'piano') {
            this.renderMainKeyboard();
            this.renderPatternKeyboard();
        } else {
            this.renderGuitarFretboard();
            if (pat && pat.type) {
                this.renderGuitarPattern();
            } else {
                this.renderGuitarTab();
            }
        }

        this.renderMotifPanel();
        this.renderMotifHighlight();
        this.startPatternAnimation();
    }

    _pickRandom(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    generate() {
        const keys = IMPROV_CHROMATIC;
        const vibe = VIBE_PRESETS[this.currentVibe];

        // Filter scales by vibe
        let scalePool = vibe.scales || Object.keys(IMPROV_SCALES);
        scalePool = scalePool.filter(s => IMPROV_SCALES[s]); // ensure they exist

        // Filter patterns by vibe
        const patterns = this._getActivePatterns();
        let patternPool = Object.keys(patterns);
        if (vibe.patternVibes && this.instrument === 'piano') {
            const filtered = patternPool.filter(p => {
                const pat = IMPROV_PATTERNS[p];
                return pat && pat.vibe && pat.vibe.some(v => vibe.patternVibes.includes(v) || v === 'all');
            });
            if (filtered.length) patternPool = filtered;
        }

        this.currentKey = this._pickRandom(keys);
        this.currentScale = this._pickRandom(scalePool);
        this.currentPattern = this._pickRandom(patternPool);

        // Generate a new motif
        this.currentMotif = generateMotif(5);

        document.getElementById('improv-key').value = this.currentKey;
        document.getElementById('improv-scale').value = this.currentScale;
        document.getElementById('improv-pattern').value = this.currentPattern;

        this.updateDisplay();

        // Track progress
        try {
            const progress = storageManager.load('mode_progress').improv;
            if (!progress.scales_practiced.includes(this.currentScale)) {
                progress.scales_practiced.push(this.currentScale);
            }
            if (!progress.patterns_practiced.includes(this.currentPattern)) {
                progress.patterns_practiced.push(this.currentPattern);
            }
            if (this.currentMotif && !progress.motifs_practiced) {
                progress.motifs_practiced = [];
            }
            if (this.currentMotif && !progress.motifs_practiced.includes(this.currentMotif.baseName)) {
                progress.motifs_practiced.push(this.currentMotif.baseName);
            }
            storageManager.updateModeProgress('improv', progress);
        } catch(e) { /* ignore storage errors */ }
    }
}

window.improv = new ImprovGenerator();
