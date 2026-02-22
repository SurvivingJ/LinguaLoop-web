/**
 * Tempo Ramp Mode - Simplified
 */

class TempoRamp {
    constructor() {
        this.isRunning = false;
        this.currentTempo = 80;
        this.startTempo = 80;
        this.maxTempo = 160;
        this.increment = 5;
        this.intervalSeconds = 30;
        this.startTime = null;
    }

    async init() {
        const container = document.getElementById('tempo-ramp-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Start Tempo:</label>
                    <input type="number" id="ramp-start" min="40" max="200" value="80">
                    <span>BPM</span>
                </div>
                <div class="control-row">
                    <label>Max Tempo:</label>
                    <input type="number" id="ramp-max" min="40" max="240" value="160">
                    <span>BPM</span>
                </div>
                <div class="control-row">
                    <label>Increment:</label>
                    <input type="number" id="ramp-increment" min="1" max="20" value="5">
                    <span>BPM</span>
                </div>
                <div class="control-row">
                    <label>Interval:</label>
                    <input type="number" id="ramp-interval" min="10" max="60" value="30">
                    <span>seconds</span>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="ramp-start">Start</button>
                    <button class="btn btn-danger hidden" id="ramp-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <div class="tempo-display" id="ramp-current-tempo">80</div>
                <p>BPM</p>
                <div class="mt-md">
                    <small>Next increase in: <span id="ramp-countdown">--</span>s</small>
                </div>
            </div>
        `;

        document.getElementById('ramp-start-tempo').addEventListener('input', (e) => {
            this.startTempo = parseInt(e.target.value);
        });

        document.getElementById('ramp-start').addEventListener('click', () => this.start());
        document.getElementById('ramp-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        this.startTempo = parseInt(document.getElementById('ramp-start').value) || 80;
        this.maxTempo = parseInt(document.getElementById('ramp-max').value) || 160;
        this.increment = parseInt(document.getElementById('ramp-increment').value) || 5;
        this.intervalSeconds = parseInt(document.getElementById('ramp-interval').value) || 30;

        this.currentTempo = this.startTempo;
        this.startTime = Date.now();
        this.lastRampTime = this.startTime;

        document.getElementById('ramp-start').classList.add('hidden');
        document.getElementById('ramp-stop').classList.remove('hidden');

        this.updateDisplay();
        this.startMetronome();
        this.startUpdateLoop();
    }

    startMetronome() {
        this.updateMetronomeInterval();
    }

    updateMetronomeInterval() {
        if (this.metronomeInterval) {
            clearInterval(this.metronomeInterval);
        }

        const interval = (60 / this.currentTempo) * 1000;
        this.metronomeInterval = setInterval(() => {
            if (!this.isRunning) return;
            audioManager.playClick(900, 0.05, true);
        }, interval);
    }

    startUpdateLoop() {
        this.updateInterval = setInterval(() => {
            if (!this.isRunning) return;

            const now = Date.now();
            const timeSinceLastRamp = (now - this.lastRampTime) / 1000;
            const countdown = Math.max(0, this.intervalSeconds - Math.floor(timeSinceLastRamp));

            document.getElementById('ramp-countdown').textContent = countdown;

            if (timeSinceLastRamp >= this.intervalSeconds) {
                this.rampTempo();
            }
        }, 100);
    }

    rampTempo() {
        if (this.currentTempo < this.maxTempo) {
            this.currentTempo = Math.min(this.maxTempo, this.currentTempo + this.increment);
            this.lastRampTime = Date.now();
            this.updateDisplay();
            this.updateMetronomeInterval();
            audioManager.playChirp();

            // Update high score
            storageManager.updateHighScore('tempo_ramp_max', this.currentTempo);
        }
    }

    updateDisplay() {
        document.getElementById('ramp-current-tempo').textContent = this.currentTempo;
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.metronomeInterval) clearInterval(this.metronomeInterval);
        if (this.updateInterval) clearInterval(this.updateInterval);

        document.getElementById('ramp-start').classList.remove('hidden');
        document.getElementById('ramp-stop').classList.add('hidden');

        // Log session
        if (this.startTime) {
            const duration = Math.floor((Date.now() - this.startTime) / 1000);
            storageManager.logPracticeSession('tempo_ramp', duration, { max_tempo: this.currentTempo });
        }
    }
}

const tempo_ramp = new TempoRamp();
