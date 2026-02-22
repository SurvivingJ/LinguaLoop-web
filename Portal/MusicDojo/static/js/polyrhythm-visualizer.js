/**
 * Polyrhythm Visualizer Mode - Simplified
 */

class PolyrhythmVisualizer {
    constructor() {
        this.isRunning = false;
        this.tempo = 90;
        this.ratioLeft = 3;
        this.ratioRight = 2;
    }

    async init() {
        const container = document.getElementById('polyrhythm-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="poly-tempo" min="40" max="160" value="90">
                    <span id="poly-tempo-display">90</span> BPM
                </div>
                <div class="control-row">
                    <label>Ratio:</label>
                    <select id="poly-ratio">
                        <option value="2:1">2:1</option>
                        <option value="3:2" selected>3:2</option>
                        <option value="4:3">4:3</option>
                        <option value="5:4">5:4</option>
                        <option value="3:1">3:1</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="poly-start">Start</button>
                    <button class="btn btn-danger hidden" id="poly-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <h3 id="poly-display">3 : 2</h3>
                <p>Listen and feel the polyrhythm pattern</p>
            </div>
        `;

        document.getElementById('poly-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('poly-tempo-display').textContent = this.tempo;
        });

        document.getElementById('poly-ratio').addEventListener('change', (e) => {
            const [left, right] = e.target.value.split(':').map(n => parseInt(n));
            this.ratioLeft = left;
            this.ratioRight = right;
            document.getElementById('poly-display').textContent = `${left} : ${right}`;
        });

        document.getElementById('poly-start').addEventListener('click', () => this.start());
        document.getElementById('poly-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        document.getElementById('poly-start').classList.add('hidden');
        document.getElementById('poly-stop').classList.remove('hidden');

        this.playPolyrhythm();
    }

    playPolyrhythm() {
        const beatDuration = 60 / this.tempo;
        const cycleDuration = Math.max(this.ratioLeft, this.ratioRight) * beatDuration;
        const leftInterval = (cycleDuration / this.ratioLeft) * 1000;
        const rightInterval = (cycleDuration / this.ratioRight) * 1000;

        this.intervalLeft = setInterval(() => {
            if (!this.isRunning) return;
            audioManager.playClick(700, 0.05);
        }, leftInterval);

        this.intervalRight = setInterval(() => {
            if (!this.isRunning) return;
            audioManager.playClick(900, 0.05);
        }, rightInterval);
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.intervalLeft) clearInterval(this.intervalLeft);
        if (this.intervalRight) clearInterval(this.intervalRight);

        document.getElementById('poly-start').classList.remove('hidden');
        document.getElementById('poly-stop').classList.add('hidden');
    }
}

const polyrhythm = new PolyrhythmVisualizer();
