/**
 * FretboardVisualizer - CSS Grid guitar neck with glow animations
 * Renders a 6-string × 25-fret grid and highlights notes in sync with playback.
 */
class FretboardVisualizer {
    constructor() {
        this.container = null;
        this.cells = {}; // keyed by "string_fret"
        this.STRING_NAMES = ['E2', 'A2', 'D3', 'G3', 'B3', 'E4'];
        this.DOT_FRETS = [3, 5, 7, 9, 12, 15, 17, 19, 21, 24];
        this.DOUBLE_DOT_FRETS = [12, 24];
    }

    /**
     * Render the fretboard into a container element.
     * @param {HTMLElement|string} container - DOM element or ID
     */
    render(container) {
        if (typeof container === 'string') {
            container = document.getElementById(container);
        }
        if (!container) return;
        this.container = container;

        let html = '<div class="fretboard-container">';
        html += '<div class="fretboard-grid">';

        // Render 6 strings (high E at top = index 5, low E at bottom = index 0)
        for (let s = 5; s >= 0; s--) {
            // String label
            html += `<div class="fretboard-string-label">${this.STRING_NAMES[s]}</div>`;

            // 25 frets (0 = open/nut through 24)
            for (let f = 0; f <= 24; f++) {
                const classes = ['fretboard-cell'];
                if (f === 0) classes.push('nut');
                if (this.DOT_FRETS.includes(f) && s === 2) classes.push('dot');
                if (this.DOUBLE_DOT_FRETS.includes(f) && (s === 1 || s === 3)) classes.push('dot');

                html += `<div class="${classes.join(' ')}" data-string="${s}" data-fret="${f}"></div>`;
            }
        }

        html += '</div>';

        // Fret numbers
        html += '<div class="fretboard-fret-numbers">';
        html += '<div class="fretboard-fret-number"></div>'; // Empty for label column
        for (let f = 0; f <= 24; f++) {
            html += `<div class="fretboard-fret-number">${f > 0 ? f : ''}</div>`;
        }
        html += '</div>';
        html += '</div>';

        container.innerHTML = html;

        // Cache cell references
        this.cells = {};
        container.querySelectorAll('.fretboard-cell').forEach(cell => {
            const key = `${cell.dataset.string}_${cell.dataset.fret}`;
            this.cells[key] = cell;
        });
    }

    /**
     * Highlight a single note (for playback animation).
     * @param {number} string - String index (0=low E, 5=high E)
     * @param {number} fret - Fret number
     * @param {string} label - Optional label to show in the cell
     */
    highlightNote(string, fret, label = '') {
        const key = `${string}_${fret}`;
        const cell = this.cells[key];
        if (cell) {
            cell.classList.add('glow');
            if (label) cell.textContent = label;
        }
    }

    /**
     * Clear all active highlights.
     */
    clearHighlight() {
        if (!this.container) return;
        this.container.querySelectorAll('.glow').forEach(cell => {
            cell.classList.remove('glow');
            cell.textContent = '';
        });
    }

    /**
     * Show entire pattern statically (all notes at once with sequence numbers).
     * @param {Array} fingering - Array of {string, fret, note_name} objects
     */
    showPattern(fingering) {
        this.clearAll();
        fingering.forEach((note, i) => {
            const key = `${note.string}_${note.fret}`;
            const cell = this.cells[key];
            if (cell) {
                cell.classList.add('glow-static');
                cell.textContent = i + 1;
            }
        });
    }

    /**
     * Clear all highlights (both glow and glow-static).
     */
    clearAll() {
        if (!this.container) return;
        this.container.querySelectorAll('.glow, .glow-static').forEach(cell => {
            cell.classList.remove('glow', 'glow-static');
            cell.textContent = '';
        });
    }
}

// Export singleton
window.fretboardVisualizer = new FretboardVisualizer();
