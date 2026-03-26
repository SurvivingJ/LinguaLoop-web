/**
 * PianoVisualizer - HTML/CSS piano keyboard with press animations
 * Renders a 3-octave keyboard (C3-B5) and highlights keys in sync with playback.
 */
class PianoVisualizer {
    constructor() {
        this.container = null;
        this.keys = {}; // keyed by MIDI number
        this.START_MIDI = 48; // C3
        this.END_MIDI = 84;   // C6
    }

    /**
     * Check if a MIDI note is a black key.
     */
    isBlackKey(midi) {
        const note = midi % 12;
        return [1, 3, 6, 8, 10].includes(note);
    }

    /**
     * Get note name from MIDI number.
     */
    midiToNoteName(midi) {
        const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const octave = Math.floor(midi / 12) - 1;
        return `${names[midi % 12]}${octave}`;
    }

    /**
     * Render the piano keyboard into a container element.
     * @param {HTMLElement|string} container - DOM element or ID
     */
    render(container) {
        if (typeof container === 'string') {
            container = document.getElementById(container);
        }
        if (!container) return;
        this.container = container;

        let html = '<div class="piano-container"><div class="piano-keyboard">';

        for (let midi = this.START_MIDI; midi <= this.END_MIDI; midi++) {
            const isBlack = this.isBlackKey(midi);
            const noteName = this.midiToNoteName(midi);
            const keyClass = isBlack ? 'black' : 'white';

            html += `<div class="piano-key ${keyClass}" data-midi="${midi}">`;
            html += `<span class="piano-key-label">${noteName}</span>`;
            html += '</div>';
        }

        html += '</div></div>';
        container.innerHTML = html;

        // Cache key references
        this.keys = {};
        container.querySelectorAll('.piano-key').forEach(key => {
            this.keys[key.dataset.midi] = key;
        });
    }

    /**
     * Highlight a single key (for playback animation).
     * @param {number} midi - MIDI note number
     */
    highlightKey(midi) {
        const key = this.keys[midi];
        if (key) {
            key.classList.add('pressed');
        }
    }

    /**
     * Clear all active highlights.
     */
    clearHighlight() {
        if (!this.container) return;
        this.container.querySelectorAll('.pressed').forEach(key => {
            key.classList.remove('pressed');
        });
    }

    /**
     * Show entire pattern statically (all notes highlighted).
     * @param {Array} midiSequence - Array of MIDI numbers
     */
    showPattern(midiSequence) {
        this.clearAll();
        midiSequence.forEach(midi => {
            const key = this.keys[midi];
            if (key) {
                key.classList.add('glow-static');
            }
        });
    }

    /**
     * Clear all highlights.
     */
    clearAll() {
        if (!this.container) return;
        this.container.querySelectorAll('.pressed, .glow-static').forEach(key => {
            key.classList.remove('pressed', 'glow-static');
        });
    }
}

// Export singleton
window.pianoVisualizer = new PianoVisualizer();
