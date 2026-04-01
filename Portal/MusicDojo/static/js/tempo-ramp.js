/**
 * Tempo Ramp Mode
 * Progress bar, warning overlay, beat counter, elapsed time
 */

class TempoRamp {
    constructor() {
        this.isRunning = false;
        this.currentTempo = 80;
        this.startTempo = 80;
        this.maxTempo = 160;
        this.increment = 5;
        this.intervalSeconds = 30;
        this.sessionStartTime = null;
        // Animation state
        this.animFrameId = null;
        this.lastTimestamp = 0;
        this.elapsedTime = 0;
        this.currentBeat = -1;
        this.elapsedSinceLastRamp = 0;
        this.isWarningActive = false;
        this.warningShownAt = 0;
        this.lastRampTime = 0;
    }

    async init() {
        const container = document.getElementById('tempo-ramp-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Start Tempo:</label>
                    <input type="number" id="ramp-start-tempo" min="40" max="200" value="80">
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
                <div id="ramp-warning" class="warning-overlay" style="display:none">
                    GET READY: +5 BPM
                </div>
                <div class="tempo-display" id="ramp-current-tempo">80 BPM</div>
                <div class="ramp-progress">
                    <div class="ramp-progress-bar" id="ramp-progress-bar" style="width:0%"></div>
                </div>
                <div class="stats-row mt-md">
                    <div class="stat">
                        <div class="stat-value" id="ramp-elapsed">00:00</div>
                        <div class="stat-label">Time</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="ramp-beat">0</div>
                        <div class="stat-label">Beat</div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('ramp-start').addEventListener('click', () => this.start());
        document.getElementById('ramp-stop').addEventListener('click', () => this.stop());
    }

    triggerWarning() {
        this.isWarningActive = true;
        this.warningShownAt = performance.now();
        const warn = document.getElementById('ramp-warning');
        if (warn) {
            warn.textContent = `GET READY: +${this.increment} BPM`;
            warn.style.display = 'block';
        }
    }

    executeRamp() {
        if (this.currentTempo < this.maxTempo) {
            this.currentTempo = Math.min(this.maxTempo, this.currentTempo + this.increment);
            this.elapsedSinceLastRamp = 0;
            this.lastRampTime = this.elapsedTime;
            audioManager.playChirp();
            storageManager.updateHighScore('tempo_ramp_max', this.currentTempo);
        }
        this.isWarningActive = false;
        const warn = document.getElementById('ramp-warning');
        if (warn) warn.style.display = 'none';
    }

    updateProgressBar() {
        const bar = document.getElementById('ramp-progress-bar');
        if (bar) {
            const pct = Math.min(100, (this.elapsedSinceLastRamp / this.intervalSeconds) * 100);
            bar.style.width = pct + '%';
        }
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;
        this.elapsedTime += delta;
        this.elapsedSinceLastRamp += delta;

        // Calculate beat and play click on each new beat
        const beatDurMs = getBeatDurationMs(this.currentTempo);
        const newBeat = Math.floor((this.elapsedTime * 1000) / beatDurMs);
        if (newBeat !== this.currentBeat) {
            this.currentBeat = newBeat;
            audioManager.playClick(900, 0.05, true);
        }

        // Check for warning (2 beats before ramp)
        const beatsUntilRamp = (this.intervalSeconds - this.elapsedSinceLastRamp) / (beatDurMs / 1000);
        if (beatsUntilRamp <= 2 && beatsUntilRamp > 0 && !this.isWarningActive && this.currentTempo < this.maxTempo) {
            this.triggerWarning();
        }

        // Execute ramp
        if (this.elapsedSinceLastRamp >= this.intervalSeconds) {
            this.executeRamp();
        }

        // Hide warning after 800ms
        if (this.isWarningActive && (performance.now() - this.warningShownAt) > 800) {
            this.isWarningActive = false;
            const warn = document.getElementById('ramp-warning');
            if (warn) warn.style.display = 'none';
        }

        // Update displays
        const tempoEl = document.getElementById('ramp-current-tempo');
        if (tempoEl) tempoEl.textContent = this.currentTempo + ' BPM';
        const elEl = document.getElementById('ramp-elapsed');
        if (elEl) elEl.textContent = formatTime(this.elapsedTime);
        const beatEl = document.getElementById('ramp-beat');
        if (beatEl) beatEl.textContent = this.currentBeat;
        this.updateProgressBar();

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        this.startTempo = parseInt(document.getElementById('ramp-start-tempo').value) || 80;
        this.maxTempo = parseInt(document.getElementById('ramp-max').value) || 160;
        this.increment = parseInt(document.getElementById('ramp-increment').value) || 5;
        this.intervalSeconds = parseInt(document.getElementById('ramp-interval').value) || 30;

        this.currentTempo = this.startTempo;
        this.sessionStartTime = Date.now();
        this.elapsedTime = 0;
        this.lastTimestamp = 0;
        this.currentBeat = -1;
        this.elapsedSinceLastRamp = 0;
        this.isWarningActive = false;
        this.lastRampTime = 0;

        document.getElementById('ramp-start').classList.add('hidden');
        document.getElementById('ramp-stop').classList.remove('hidden');

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);

        document.getElementById('ramp-start').classList.remove('hidden');
        document.getElementById('ramp-stop').classList.add('hidden');

        // Log session
        if (this.sessionStartTime) {
            const duration = Math.floor((Date.now() - this.sessionStartTime) / 1000);
            storageManager.logPracticeSession('tempo_ramp', duration, { max_tempo: this.currentTempo });
        }
    }
}

window.tempo_ramp = new TempoRamp();
