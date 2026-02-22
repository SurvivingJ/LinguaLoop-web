/**
 * Ghost Metronome Mode - Simplified
 */

class GhostMetronome {
    constructor() {
        this.isRunning = false;
        this.tempo = 100;
        this.activeBars = 4;
        this.ghostBars = 2;
        this.currentPhase = 'active';
        this.currentBeat = 0;
    }

    async init() {
        const container = document.getElementById('ghost-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="ghost-tempo" min="60" max="160" value="100">
                    <span id="ghost-tempo-display">100</span> BPM
                </div>
                <div class="control-row">
                    <label>Active Bars:</label>
                    <input type="number" id="ghost-active" min="1" max="8" value="4">
                </div>
                <div class="control-row">
                    <label>Ghost Bars:</label>
                    <input type="number" id="ghost-ghost" min="1" max="8" value="2">
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="ghost-start">Start</button>
                    <button class="btn btn-danger hidden" id="ghost-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <div class="phase-display">
                    <h3 id="ghost-phase-display">Active Phase</h3>
                    <p id="ghost-bar-display">Bar 1 of 4</p>
                </div>
                <div class="mt-lg">
                    <p class="text-secondary">Metronome will alternate between active and silent (ghost) phases</p>
                </div>
            </div>
        `;

        document.getElementById('ghost-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('ghost-tempo-display').textContent = this.tempo;
        });

        document.getElementById('ghost-active').addEventListener('input', (e) => {
            this.activeBars = parseInt(e.target.value);
        });

        document.getElementById('ghost-ghost').addEventListener('input', (e) => {
            this.ghostBars = parseInt(e.target.value);
        });

        document.getElementById('ghost-start').addEventListener('click', () => this.start());
        document.getElementById('ghost-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        this.currentPhase = 'active';
        this.currentBeat = 0;
        this.currentBar = 1;

        document.getElementById('ghost-start').classList.add('hidden');
        document.getElementById('ghost-stop').classList.remove('hidden');

        this.startMetronome();
    }

    startMetronome() {
        const beatDuration = (60 / this.tempo) * 1000;
        let beatInBar = 0;

        this.intervalId = setInterval(() => {
            if (!this.isRunning) return;

            beatInBar++;
            if (beatInBar > 4) {
                beatInBar = 1;
                this.currentBar++;

                // Check if we need to switch phases
                if (this.currentPhase === 'active' && this.currentBar > this.activeBars) {
                    this.currentPhase = 'ghost';
                    this.currentBar = 1;
                } else if (this.currentPhase === 'ghost' && this.currentBar > this.ghostBars) {
                    this.currentPhase = 'active';
                    this.currentBar = 1;
                }

                this.updateDisplay();
            }

            // Only play sound during active phase
            if (this.currentPhase === 'active') {
                const isAccent = beatInBar === 1;
                audioManager.playClick(isAccent ? 1000 : 800, 0.05, isAccent);
            }

        }, beatDuration);
    }

    updateDisplay() {
        const phaseText = this.currentPhase === 'active' ? 'Active Phase' : 'Ghost Phase (Silent)';
        const maxBars = this.currentPhase === 'active' ? this.activeBars : this.ghostBars;

        document.getElementById('ghost-phase-display').textContent = phaseText;
        document.getElementById('ghost-bar-display').textContent = `Bar ${this.currentBar} of ${maxBars}`;
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.intervalId) clearInterval(this.intervalId);

        document.getElementById('ghost-start').classList.remove('hidden');
        document.getElementById('ghost-stop').classList.add('hidden');
    }
}

const ghost = new GhostMetronome();
