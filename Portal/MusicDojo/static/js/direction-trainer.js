/**
 * Direction Trainer Mode - Simplified
 * Practice hand coordination with similar/contrary/oblique motion
 */

class DirectionTrainer {
    constructor() {
        this.isRunning = false;
        this.tempo = 80;
        this.motionType = 'similar';
    }

    async init() {
        const container = document.getElementById('direction-trainer-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="dir-tempo" min="40" max="160" value="80" step="5">
                    <span id="dir-tempo-display">80</span> BPM
                </div>
                <div class="control-row">
                    <label>Motion Type:</label>
                    <select id="dir-motion">
                        <option value="similar">Similar</option>
                        <option value="contrary">Contrary</option>
                        <option value="oblique">Oblique</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="dir-start">Start Practice</button>
                </div>
            </div>

            <div class="display-area">
                <div class="instruction-text" id="dir-instruction">
                    Click Start to begin practicing hand coordination
                </div>
                <div class="mt-lg">
                    <button class="btn btn-danger hidden" id="dir-stop">Stop</button>
                </div>
            </div>
        `;

        const tempoSlider = document.getElementById('dir-tempo');
        const tempoDisplay = document.getElementById('dir-tempo-display');
        tempoSlider.addEventListener('input', (e) => {
            tempoDisplay.textContent = e.target.value;
            this.tempo = parseInt(e.target.value);
        });

        document.getElementById('dir-motion').addEventListener('change', (e) => {
            this.motionType = e.target.value;
        });

        document.getElementById('dir-start').addEventListener('click', () => this.start());
        document.getElementById('dir-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        document.getElementById('dir-instruction').textContent = `Practice ${this.motionType} motion at ${this.tempo} BPM`;
        document.getElementById('dir-start').classList.add('hidden');
        document.getElementById('dir-stop').classList.remove('hidden');

        // Start metronome clicks
        this.startMetronome();
    }

    startMetronome() {
        const interval = (60 / this.tempo) * 1000;
        this.intervalId = setInterval(() => {
            if (!this.isRunning) {
                clearInterval(this.intervalId);
                return;
            }
            audioManager.playClick(800, 0.05);
        }, interval);
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
        }

        document.getElementById('dir-start').classList.remove('hidden');
        document.getElementById('dir-stop').classList.add('hidden');
        document.getElementById('dir-instruction').textContent = 'Click Start to begin practicing hand coordination';
    }
}

const direction_trainer = new DirectionTrainer();
