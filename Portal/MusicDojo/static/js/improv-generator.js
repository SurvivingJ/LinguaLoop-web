/**
 * Improv Generator Mode - Simplified
 */

class ImprovGenerator {
    constructor() {
        this.currentKey = 'C';
        this.currentScale = 'Major';
        this.currentPattern = 'Block Chords';
    }

    async init() {
        const container = document.getElementById('improv-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Key:</label>
                    <select id="improv-key">
                        <option value="C">C</option>
                        <option value="D">D</option>
                        <option value="E">E</option>
                        <option value="F">F</option>
                        <option value="G">G</option>
                        <option value="A">A</option>
                        <option value="B">B</option>
                    </select>
                </div>
                <div class="control-row">
                    <label>Scale:</label>
                    <select id="improv-scale">
                        <option value="Major">Major</option>
                        <option value="Natural Minor">Natural Minor</option>
                        <option value="Dorian">Dorian</option>
                        <option value="Pentatonic Major">Pentatonic Major</option>
                        <option value="Pentatonic Minor">Pentatonic Minor</option>
                        <option value="Blues">Blues</option>
                    </select>
                </div>
                <div class="control-row">
                    <label>Pattern:</label>
                    <select id="improv-pattern">
                        <option value="Block Chords">Block Chords</option>
                        <option value="Alberti Bass">Alberti Bass</option>
                        <option value="Walking Bass">Walking Bass</option>
                        <option value="Arpeggio Up">Arpeggio Up</option>
                        <option value="Arpeggio Down">Arpeggio Down</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="improv-generate">Generate New</button>
                </div>
            </div>

            <div class="display-area">
                <div class="scale-display">
                    <div class="scale-name" id="improv-display">C Major</div>
                    <div class="pattern-name mt-md" id="improv-pattern-display">Block Chords</div>
                </div>
                <div class="mt-lg">
                    <p class="text-secondary">Practice this scale and pattern combination</p>
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

        this.updateDisplay();
    }

    generate() {
        // Randomly select key, scale, and pattern
        const keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
        const scales = ['Major', 'Natural Minor', 'Dorian', 'Pentatonic Major', 'Pentatonic Minor', 'Blues'];
        const patterns = ['Block Chords', 'Alberti Bass', 'Walking Bass', 'Arpeggio Up', 'Arpeggio Down'];

        this.currentKey = keys[Math.floor(Math.random() * keys.length)];
        this.currentScale = scales[Math.floor(Math.random() * scales.length)];
        this.currentPattern = patterns[Math.floor(Math.random() * patterns.length)];

        document.getElementById('improv-key').value = this.currentKey;
        document.getElementById('improv-scale').value = this.currentScale;
        document.getElementById('improv-pattern').value = this.currentPattern;

        this.updateDisplay();

        // Track in progress
        const progress = storageManager.load('mode_progress').improv;
        if (!progress.scales_practiced.includes(this.currentScale)) {
            progress.scales_practiced.push(this.currentScale);
        }
        if (!progress.patterns_practiced.includes(this.currentPattern)) {
            progress.patterns_practiced.push(this.currentPattern);
        }
        storageManager.updateModeProgress('improv', progress);
    }

    updateDisplay() {
        document.getElementById('improv-display').textContent = `${this.currentKey} ${this.currentScale}`;
        document.getElementById('improv-pattern-display').textContent = this.currentPattern;
    }
}

const improv = new ImprovGenerator();
