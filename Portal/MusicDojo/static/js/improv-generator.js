/**
 * Improv Generator Mode
 * Piano keyboard with scale highlighting, guitar fretboard, tab display, pattern animation
 */

const IMPROV_CHROMATIC = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
const IMPROV_SCALES = {
    'Major':            [0,2,4,5,7,9,11],
    'Natural Minor':    [0,2,3,5,7,8,10],
    'Dorian':           [0,2,3,5,7,9,10],
    'Pentatonic Major': [0,2,4,7,9],
    'Pentatonic Minor': [0,3,5,7,10],
    'Blues':             [0,3,5,6,7,10]
};
const IMPROV_PATTERNS = {
    'Block Chords':  { seq: [[1,3,5]], desc: 'All chord tones simultaneously' },
    'Alberti Bass':  { seq: [1,5,3,5], desc: 'Root-fifth-third-fifth pattern' },
    'Walking Bass':  { seq: [1,2,3,5], desc: 'Stepwise ascending movement' },
    'Arpeggio Up':   { seq: [1,3,5,8], desc: 'Rising broken chord' },
    'Arpeggio Down': { seq: [8,5,3,1], desc: 'Falling broken chord' }
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
                        ${Object.keys(IMPROV_SCALES).map(s => `<option value="${s}" ${s===this.currentScale?'selected':''}>${s}</option>`).join('')}
                    </select>
                </div>
                <div class="control-row">
                    <label>Pattern:</label>
                    <select id="improv-pattern">
                        ${Object.keys(IMPROV_PATTERNS).map(p => `<option value="${p}" ${p===this.currentPattern?'selected':''}>${p}</option>`).join('')}
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

        this.updateDisplay();
    }

    setInstrument(inst) {
        this.instrument = inst;
        document.getElementById('improv-btn-piano').className = 'instrument-btn' + (inst === 'piano' ? ' selected' : '');
        document.getElementById('improv-btn-guitar').className = 'instrument-btn' + (inst === 'guitar' ? ' selected' : '');

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
        const pat = IMPROV_PATTERNS[this.currentPattern];
        if (!pat) return [];
        const scaleNotes = this.scaleNotes;
        if (!scaleNotes.length) return [];

        return pat.seq.map(step => {
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
            if (Array.isArray(step)) allNotes.push(...step);
            else allNotes.push(step);
        });
        if (!allNotes.length) { container.innerHTML = ''; return; }

        const minNote = Math.min(...allNotes) - 2;
        const maxNote = Math.max(...allNotes) + 2;
        const rootPc = IMPROV_CHROMATIC.indexOf(this.currentKey);

        const currentStep = this.patternMidi[this.currentStepIndex];
        const activeNotes = Array.isArray(currentStep) ? currentStep : (currentStep != null ? [currentStep] : []);

        let html = '<div class="keyboard mini">';
        for (let midi = minNote; midi <= maxNote; midi++) {
            const isBlk = this.isBlack(midi);
            const isActive = activeNotes.includes(midi);
            const isInPattern = allNotes.includes(midi) && !isActive;
            const isRoot = midi % 12 === rootPc;

            let cls = 'key ' + (isBlk ? 'black' : 'white');
            if (isActive) cls += ' active';
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
                const notes = Array.isArray(step) ? step : [step];
                const isActive = i === this.currentStepIndex;

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

    // --- Pattern animation ---

    startPatternAnimation() {
        this.stopPatternAnimation();
        this.currentStepIndex = 0;
        if (this.patternMidi.length <= 1) return;

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

    updateDisplay() {
        this.scaleNotes = this.getScaleNotes();
        this.patternMidi = this.getPatternMidi();
        this.currentStepIndex = 0;

        document.getElementById('improv-display').textContent = `${this.currentKey} ${this.currentScale}`;
        document.getElementById('improv-pattern-display').textContent = this.currentPattern;

        const desc = IMPROV_PATTERNS[this.currentPattern];
        const descEl = document.getElementById('improv-pattern-desc');
        if (descEl && desc) descEl.textContent = desc.desc;

        if (this.instrument === 'piano') {
            this.renderMainKeyboard();
            this.renderPatternKeyboard();
        } else {
            this.renderGuitarFretboard();
            this.renderGuitarTab();
        }

        this.startPatternAnimation();
    }

    generate() {
        const keys = IMPROV_CHROMATIC;
        const scales = Object.keys(IMPROV_SCALES);
        const patterns = Object.keys(IMPROV_PATTERNS);

        this.currentKey = keys[Math.floor(Math.random() * keys.length)];
        this.currentScale = scales[Math.floor(Math.random() * scales.length)];
        this.currentPattern = patterns[Math.floor(Math.random() * patterns.length)];

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
            storageManager.updateModeProgress('improv', progress);
        } catch(e) { /* ignore storage errors */ }
    }
}

window.improv = new ImprovGenerator();
