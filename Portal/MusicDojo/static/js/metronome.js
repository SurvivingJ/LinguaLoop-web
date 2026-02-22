/**
 * Advanced Metronome Mode
 * Metronome with subdivisions, accent patterns, and tap tempo
 */

class AdvancedMetronome {
    constructor() {
        this.isRunning = false;
        this.tempo = 120;
        this.beatsPerMeasure = 4;
        this.subdivision = 'none'; // none, eighth, sixteenth, triplet
        this.accentPattern = []; // Array of beat indices to accent
        this.currentBeat = 0;
        this.currentSubdivision = 0;
        this.schedulerTimerId = null;
        this.nextNoteTime = 0;
        this.startTime = null;
        this.tapTimes = [];
    }

    /**
     * Initialize the metronome mode
     */
    async init() {
        const container = document.getElementById('metronome-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="metro-tempo" min="40" max="240" value="120" step="1">
                    <input type="number" id="metro-tempo-num" min="40" max="240" value="120">
                    <span>BPM</span>
                </div>

                <div class="control-row">
                    <button class="btn btn-primary" id="metro-tap-tempo">Tap Tempo</button>
                    <small class="text-secondary">Tap 4+ times to set tempo</small>
                </div>

                <div class="control-row">
                    <label>Beats per Measure:</label>
                    <select id="metro-beats">
                        <option value="2">2/4</option>
                        <option value="3">3/4</option>
                        <option value="4" selected>4/4</option>
                        <option value="5">5/4</option>
                        <option value="6">6/8</option>
                        <option value="7">7/8</option>
                    </select>
                </div>

                <div class="control-row">
                    <label>Subdivision:</label>
                    <select id="metro-subdivision">
                        <option value="none" selected>None (Quarter Notes)</option>
                        <option value="eighth">Eighth Notes</option>
                        <option value="triplet">Triplets</option>
                        <option value="sixteenth">Sixteenth Notes</option>
                    </select>
                </div>

                <div class="control-row">
                    <label>Accent Pattern:</label>
                    <select id="metro-accent-pattern">
                        <option value="downbeat">Downbeat Only</option>
                        <option value="all-beats">All Beats</option>
                        <option value="every-2">Every 2 Beats</option>
                        <option value="every-3">Every 3 Beats</option>
                        <option value="custom">Custom...</option>
                    </select>
                </div>

                <div class="control-row hidden" id="metro-custom-accent-row">
                    <label>Custom Accents (e.g., 1,3):</label>
                    <input type="text" id="metro-custom-accents" placeholder="1,3,5">
                </div>
            </div>

            <div class="display-area">
                <div class="metronome-visual">
                    <div class="tempo-display" id="metro-tempo-display">120</div>
                    <div class="beat-indicator-container">
                        <div class="beat-indicator" id="metro-beat-indicator"></div>
                        <div class="beat-number" id="metro-beat-number">-</div>
                    </div>
                    <div class="elapsed-time" id="metro-elapsed">00:00</div>
                </div>

                <div class="mt-lg">
                    <button class="btn btn-success btn-large" id="metro-start">Start</button>
                    <button class="btn btn-danger btn-large hidden" id="metro-stop">Stop</button>
                </div>
            </div>
        `;

        this.setupEventListeners();
        this.updateDisplay();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const tempoSlider = document.getElementById('metro-tempo');
        const tempoNum = document.getElementById('metro-tempo-num');
        const tapBtn = document.getElementById('metro-tap-tempo');
        const beatsSelect = document.getElementById('metro-beats');
        const subdivisionSelect = document.getElementById('metro-subdivision');
        const accentPatternSelect = document.getElementById('metro-accent-pattern');
        const customAccentsInput = document.getElementById('metro-custom-accents');
        const startBtn = document.getElementById('metro-start');
        const stopBtn = document.getElementById('metro-stop');

        if (tempoSlider) {
            tempoSlider.addEventListener('input', (e) => {
                this.tempo = parseInt(e.target.value);
                if (tempoNum) tempoNum.value = this.tempo;
                this.updateDisplay();
            });
        }

        if (tempoNum) {
            tempoNum.addEventListener('input', (e) => {
                this.tempo = parseInt(e.target.value);
                if (tempoSlider) tempoSlider.value = this.tempo;
                this.updateDisplay();
            });
        }

        if (tapBtn) {
            tapBtn.addEventListener('click', () => this.handleTapTempo());
        }

        if (beatsSelect) {
            beatsSelect.addEventListener('change', (e) => {
                this.beatsPerMeasure = parseInt(e.target.value);
                this.updateAccentPattern();
            });
        }

        if (subdivisionSelect) {
            subdivisionSelect.addEventListener('change', (e) => {
                this.subdivision = e.target.value;
            });
        }

        if (accentPatternSelect) {
            accentPatternSelect.addEventListener('change', (e) => {
                const customRow = document.getElementById('metro-custom-accent-row');
                if (e.target.value === 'custom') {
                    customRow.classList.remove('hidden');
                } else {
                    customRow.classList.add('hidden');
                }
                this.updateAccentPattern();
            });
        }

        if (customAccentsInput) {
            customAccentsInput.addEventListener('input', () => {
                if (accentPatternSelect.value === 'custom') {
                    this.updateAccentPattern();
                }
            });
        }

        if (startBtn) {
            startBtn.addEventListener('click', () => this.start());
        }

        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stop());
        }
    }

    /**
     * Handle tap tempo
     */
    handleTapTempo() {
        const now = Date.now();
        this.tapTimes.push(now);

        // Keep only last 8 taps
        if (this.tapTimes.length > 8) {
            this.tapTimes.shift();
        }

        // Need at least 2 taps to calculate tempo
        if (this.tapTimes.length >= 2) {
            const intervals = [];
            for (let i = 1; i < this.tapTimes.length; i++) {
                intervals.push(this.tapTimes[i] - this.tapTimes[i - 1]);
            }

            const avgInterval = intervals.reduce((a, b) => a + b) / intervals.length;
            const bpm = Math.round(60000 / avgInterval);

            if (bpm >= 40 && bpm <= 240) {
                this.tempo = bpm;
                document.getElementById('metro-tempo').value = bpm;
                document.getElementById('metro-tempo-num').value = bpm;
                this.updateDisplay();
            }
        }

        // Reset tap times after 2 seconds of inactivity
        clearTimeout(this.tapResetTimeout);
        this.tapResetTimeout = setTimeout(() => {
            this.tapTimes = [];
        }, 2000);

        // Visual feedback
        audioManager.playClick(1000, 0.03);
    }

    /**
     * Update accent pattern based on settings
     */
    updateAccentPattern() {
        const patternType = document.getElementById('metro-accent-pattern').value;
        this.accentPattern = [];

        switch (patternType) {
            case 'downbeat':
                this.accentPattern = [1];
                break;

            case 'all-beats':
                for (let i = 1; i <= this.beatsPerMeasure; i++) {
                    this.accentPattern.push(i);
                }
                break;

            case 'every-2':
                for (let i = 1; i <= this.beatsPerMeasure; i += 2) {
                    this.accentPattern.push(i);
                }
                break;

            case 'every-3':
                for (let i = 1; i <= this.beatsPerMeasure; i += 3) {
                    this.accentPattern.push(i);
                }
                break;

            case 'custom':
                const customInput = document.getElementById('metro-custom-accents').value;
                const beats = customInput.split(',').map(b => parseInt(b.trim())).filter(b => !isNaN(b) && b >= 1 && b <= this.beatsPerMeasure);
                this.accentPattern = beats;
                break;
        }
    }

    /**
     * Start the metronome
     */
    start() {
        if (this.isRunning) return;

        window.gameActive = true;
        audioManager.initialize();

        this.isRunning = true;
        this.currentBeat = 0;
        this.currentSubdivision = 0;
        this.startTime = Date.now();

        this.updateAccentPattern();

        // Start scheduler
        this.nextNoteTime = audioManager.getCurrentTime();
        this.startScheduler();

        // Start visual update loop
        this.updateLoop();

        // Toggle buttons
        document.getElementById('metro-start').classList.add('hidden');
        document.getElementById('metro-stop').classList.remove('hidden');
    }

    /**
     * Stop the metronome
     */
    stop() {
        if (!this.isRunning) return;

        window.gameActive = false;
        this.isRunning = false;

        if (this.schedulerTimerId) {
            clearInterval(this.schedulerTimerId);
            this.schedulerTimerId = null;
        }

        // Log practice session
        if (this.startTime) {
            const duration = Math.floor((Date.now() - this.startTime) / 1000);
            const progress = storageManager.load('mode_progress').metronome;
            progress.sessions = (progress.sessions || 0) + 1;
            progress.total_time = (progress.total_time || 0) + duration;
            storageManager.updateModeProgress('metronome', progress);

            storageManager.logPracticeSession('metronome', duration, { tempo: this.tempo });
        }

        // Toggle buttons
        document.getElementById('metro-start').classList.remove('hidden');
        document.getElementById('metro-stop').classList.add('hidden');

        // Reset display
        document.getElementById('metro-beat-number').textContent = '-';
        document.getElementById('metro-beat-indicator').classList.remove('pulse');
    }

    /**
     * Start the audio scheduler
     */
    startScheduler() {
        const scheduleAheadTime = 0.1;
        const lookahead = 25;

        const schedule = () => {
            const ctx = audioManager.context;
            if (!ctx || !this.isRunning) return;

            const beatDuration = 60.0 / this.tempo;
            const subdivisionsPerBeat = this.getSubdivisionsPerBeat();
            const subdivisionDuration = beatDuration / subdivisionsPerBeat;

            while (this.nextNoteTime < ctx.currentTime + scheduleAheadTime) {
                const isDownbeat = (this.currentBeat % this.beatsPerMeasure) === 0;
                const beatNumber = (this.currentBeat % this.beatsPerMeasure) + 1;
                const isAccent = this.accentPattern.includes(beatNumber);
                const isSubdivision = this.currentSubdivision > 0;

                let frequency;
                let volume;

                if (isSubdivision) {
                    // Subdivision click (quieter)
                    frequency = 600;
                    volume = 0.15;
                } else if (isDownbeat || isAccent) {
                    // Accented beat
                    frequency = 1000;
                    volume = 0.35;
                } else {
                    // Regular beat
                    frequency = 800;
                    volume = 0.25;
                }

                audioManager.scheduleNote(this.nextNoteTime, frequency, 0.05, isDownbeat || isAccent);

                this.nextNoteTime += subdivisionDuration;
                this.currentSubdivision++;

                if (this.currentSubdivision >= subdivisionsPerBeat) {
                    this.currentSubdivision = 0;
                    this.currentBeat++;
                }
            }
        };

        this.schedulerTimerId = setInterval(schedule, lookahead);
    }

    /**
     * Get number of subdivisions per beat
     */
    getSubdivisionsPerBeat() {
        switch (this.subdivision) {
            case 'eighth': return 2;
            case 'triplet': return 3;
            case 'sixteenth': return 4;
            default: return 1;
        }
    }

    /**
     * Visual update loop
     */
    updateLoop() {
        if (!this.isRunning) return;

        // Update elapsed time
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        document.getElementById('metro-elapsed').textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        // Update beat indicator (simplified - based on time)
        const beatDuration = 60000 / this.tempo;
        const timeSinceStart = Date.now() - this.startTime;
        const currentBeat = Math.floor(timeSinceStart / beatDuration) % this.beatsPerMeasure;

        document.getElementById('metro-beat-number').textContent = (currentBeat + 1).toString();

        // Pulse animation
        const beatIndicator = document.getElementById('metro-beat-indicator');
        const phaseInBeat = (timeSinceStart % beatDuration) / beatDuration;
        if (phaseInBeat < 0.2) {
            beatIndicator.classList.add('pulse');
        } else {
            beatIndicator.classList.remove('pulse');
        }

        requestAnimationFrame(() => this.updateLoop());
    }

    /**
     * Update display values
     */
    updateDisplay() {
        document.getElementById('metro-tempo-display').textContent = this.tempo;
    }
}

// Create instance
const metronome = new AdvancedMetronome();
