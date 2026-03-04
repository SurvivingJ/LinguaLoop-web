/**
 * Rhythm Dictation Mode
 * Listen to rhythm patterns and identify them
 */

class RhythmDictation {
    constructor() {
        this.currentExercise = null;
        this.currentElo = 1000;
        this.session = {
            correct: 0,
            total: 0,
            startTime: null
        };
        this.isPlaying = false;
    }

    /**
     * Initialize the rhythm dictation mode
     */
    async init() {
        const container = document.getElementById('rhythm-dictation-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="rhythm-tempo" min="60" max="140" value="100">
                    <span id="rhythm-tempo-display">100</span> BPM
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="rhythm-start">Start Session</button>
                </div>
            </div>

            <div id="rhythm-exercise-area" class="display-area hidden">
                <div class="instruction-text">
                    Listen to the rhythm pattern and select the matching one below.
                </div>

                <div class="mt-lg">
                    <button class="btn btn-success" id="rhythm-play-button">🔊 Play Rhythm</button>
                </div>

                <div class="choices-grid mt-lg" id="rhythm-choices">
                    <!-- Rhythm pattern choices will be populated here -->
                </div>

                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="rhythm-session-correct">0</div>
                        <div class="stat-label">Correct</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="rhythm-session-total">0</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="rhythm-session-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                </div>

                <div class="mt-lg">
                    <button class="btn btn-secondary" id="rhythm-next">Next Pattern</button>
                    <button class="btn btn-danger" id="rhythm-stop">End Session</button>
                </div>
            </div>

            <div id="rhythm-results" class="display-area hidden">
                <h3>Session Complete!</h3>
                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="rhythm-results-correct">0</div>
                        <div class="stat-label">Correct</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="rhythm-results-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="rhythm-results-elo">+0</div>
                        <div class="stat-label">Elo Change</div>
                    </div>
                </div>
                <div class="mt-lg">
                    <button class="btn btn-primary" id="rhythm-restart">New Session</button>
                </div>
            </div>
        `;

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const tempoSlider = document.getElementById('rhythm-tempo');
        const tempoDisplay = document.getElementById('rhythm-tempo-display');
        const startBtn = document.getElementById('rhythm-start');
        const playBtn = document.getElementById('rhythm-play-button');
        const nextBtn = document.getElementById('rhythm-next');
        const stopBtn = document.getElementById('rhythm-stop');
        const restartBtn = document.getElementById('rhythm-restart');

        if (tempoSlider && tempoDisplay) {
            tempoSlider.addEventListener('input', (e) => {
                tempoDisplay.textContent = e.target.value;
            });
        }

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startSession());
        }

        if (playBtn) {
            playBtn.addEventListener('click', () => this.playCurrentPattern());
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.loadNextExercise());
        }

        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.endSession());
        }

        if (restartBtn) {
            restartBtn.addEventListener('click', () => this.init());
        }
    }

    /**
     * Start a new training session
     */
    async startSession() {
        window.gameActive = true;
        audioManager.initialize();

        this.currentElo = storageManager.load('user_elo');
        this.session = {
            correct: 0,
            total: 0,
            startTime: Date.now()
        };

        // Hide controls, show exercise area
        document.querySelector('#rhythm-dictation-content .controls').classList.add('hidden');
        document.getElementById('rhythm-exercise-area').classList.remove('hidden');

        await this.loadNextExercise();
    }

    /**
     * Load next exercise
     */
    async loadNextExercise() {
        try {
            this.currentExercise = await gameManager.fetchExercise('rhythm_dictation', this.currentElo);

            // Populate choices
            this.populateChoices(this.currentExercise.choices);

            // Auto-play the pattern
            setTimeout(() => this.playCurrentPattern(), 300);

        } catch (error) {
            console.error('Error loading exercise:', error);
        }
    }

    /**
     * Populate rhythm pattern choices
     */
    populateChoices(choices) {
        const choicesContainer = document.getElementById('rhythm-choices');
        choicesContainer.innerHTML = '';

        choices.forEach((pattern, index) => {
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.innerHTML = this.renderPatternNotation(pattern);
            btn.addEventListener('click', () => {
                this.handleAnswer(index, btn);
            });

            // Add play button for each choice
            const playIcon = document.createElement('span');
            playIcon.textContent = ' 🔊';
            playIcon.style.fontSize = '0.8em';
            playIcon.style.opacity = '0.6';
            playIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                this.playPattern(pattern, this.currentExercise.tempo);
            });
            btn.appendChild(playIcon);

            choicesContainer.appendChild(btn);
        });
    }

    /**
     * Render rhythm pattern as text notation
     */
    renderPatternNotation(pattern) {
        const noteSymbols = {
            0.25: '♬', // Sixteenth
            0.333: '♪3', // Triplet eighth
            0.5: '♪', // Eighth
            1.0: '♩', // Quarter
            1.5: '♩.', // Dotted quarter
            2.0: '𝅗𝅥', // Half
        };

        return pattern.map(noteValue => {
            return noteSymbols[noteValue] || '♩';
        }).join(' ');
    }

    /**
     * Play the current rhythm pattern
     */
    playCurrentPattern() {
        if (!this.currentExercise || this.isPlaying) return;
        this.playPattern(this.currentExercise.pattern, this.currentExercise.tempo);
    }

    /**
     * Play a specific rhythm pattern
     */
    playPattern(pattern, tempo) {
        if (this.isPlaying) return;

        this.isPlaying = true;
        audioManager.playRhythm(pattern, tempo);

        // Calculate total pattern duration
        const totalBeats = pattern.reduce((sum, val) => sum + val, 0);
        const durationMs = (totalBeats / tempo) * 60000;

        setTimeout(() => {
            this.isPlaying = false;
        }, durationMs + 500);
    }

    /**
     * Handle answer selection
     */
    async handleAnswer(selectedIndex, button) {
        // Disable all choice buttons
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = true;
        });

        const correct = selectedIndex === this.currentExercise.correct_answer;

        // Visual feedback
        if (correct) {
            button.classList.add('correct');
            audioManager.playChirp();
        } else {
            button.classList.add('incorrect');
            // Highlight the correct answer
            const choiceBtns = document.querySelectorAll('.choice-btn');
            if (choiceBtns[this.currentExercise.correct_answer]) {
                choiceBtns[this.currentExercise.correct_answer].classList.add('correct');
            }
        }

        // Update session stats
        this.session.total++;
        if (correct) {
            this.session.correct++;
        }

        this.updateSessionStats();

        // Record completion
        const timeMs = Date.now() - this.session.startTime;
        gameManager.recordCompletion('rhythm_dictation', correct, timeMs);

        // Update mode progress
        const progress = storageManager.load('mode_progress').rhythm_dictation;
        progress.total = (progress.total || 0) + 1;
        progress.correct = (progress.correct || 0) + (correct ? 1 : 0);
        storageManager.updateModeProgress('rhythm_dictation', progress);

        // Wait before allowing next
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Re-enable buttons
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('correct', 'incorrect');
        });
    }

    /**
     * Update session statistics display
     */
    updateSessionStats() {
        document.getElementById('rhythm-session-correct').textContent = this.session.correct;
        document.getElementById('rhythm-session-total').textContent = this.session.total;

        const accuracy = this.session.total > 0
            ? ((this.session.correct / this.session.total) * 100).toFixed(1)
            : 0;
        document.getElementById('rhythm-session-accuracy').textContent = accuracy + '%';
    }

    /**
     * End the training session
     */
    endSession() {
        window.gameActive = false;

        // Calculate session stats
        const accuracy = this.session.total > 0
            ? ((this.session.correct / this.session.total) * 100).toFixed(1)
            : 0;

        const duration = Math.floor((Date.now() - this.session.startTime) / 1000);

        // Update progress
        const progress = storageManager.load('mode_progress').rhythm_dictation;
        progress.sessions = (progress.sessions || 0) + 1;
        progress.total_time = (progress.total_time || 0) + duration;
        storageManager.updateModeProgress('rhythm_dictation', progress);

        // Log practice session
        storageManager.logPracticeSession('rhythm_dictation', duration, {
            correct: this.session.correct,
            total: this.session.total,
            accuracy: parseFloat(accuracy)
        });

        // Calculate Elo change
        const avgCorrect = this.session.correct / Math.max(1, this.session.total);
        const eloChange = Math.round((avgCorrect - 0.5) * 20);

        storageManager.updateElo(eloChange);

        // Show results
        document.getElementById('rhythm-exercise-area').classList.add('hidden');
        document.getElementById('rhythm-results').classList.remove('hidden');

        document.getElementById('rhythm-results-correct').textContent = this.session.correct + ' / ' + this.session.total;
        document.getElementById('rhythm-results-accuracy').textContent = accuracy + '%';
        document.getElementById('rhythm-results-elo').textContent = (eloChange >= 0 ? '+' : '') + eloChange;

        // Update streak
        storageManager.updateStreak();
    }
}

// Create instance
window.rhythm_dictation = new RhythmDictation();
