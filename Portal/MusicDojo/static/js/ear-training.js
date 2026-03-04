/**
 * Ear Training Mode
 * Interval, chord, and progression recognition
 */

class EarTraining {
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
     * Initialize the ear training mode
     */
    async init() {
        const container = document.getElementById('ear-training-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Exercise Type:</label>
                    <select id="ear-exercise-type">
                        <option value="interval">Intervals</option>
                        <option value="chord">Chords</option>
                        <option value="progression">Progressions</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="ear-start">Start Session</button>
                </div>
            </div>

            <div id="ear-exercise-area" class="display-area hidden">
                <div class="instruction-text" id="ear-instruction">
                    Loading...
                </div>

                <div class="mt-lg">
                    <button class="btn btn-success" id="ear-play-button">🔊 Play Sound</button>
                </div>

                <div class="choices-grid" id="ear-choices">
                    <!-- Choices will be populated here -->
                </div>

                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="ear-session-correct">0</div>
                        <div class="stat-label">Correct</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="ear-session-total">0</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="ear-session-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                </div>

                <div class="mt-lg">
                    <button class="btn btn-secondary" id="ear-next">Next Exercise</button>
                    <button class="btn btn-danger" id="ear-stop">End Session</button>
                </div>
            </div>

            <div id="ear-results" class="display-area hidden">
                <h3>Session Complete!</h3>
                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="ear-results-correct">0</div>
                        <div class="stat-label">Correct</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="ear-results-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="ear-results-elo">+0</div>
                        <div class="stat-label">Elo Change</div>
                    </div>
                </div>
                <div class="mt-lg">
                    <button class="btn btn-primary" id="ear-restart">New Session</button>
                </div>
            </div>
        `;

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const startBtn = document.getElementById('ear-start');
        const playBtn = document.getElementById('ear-play-button');
        const nextBtn = document.getElementById('ear-next');
        const stopBtn = document.getElementById('ear-stop');
        const restartBtn = document.getElementById('ear-restart');

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startSession());
        }

        if (playBtn) {
            playBtn.addEventListener('click', () => this.playCurrentExercise());
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
        document.querySelector('#ear-training-content .controls').classList.add('hidden');
        document.getElementById('ear-exercise-area').classList.remove('hidden');

        await this.loadNextExercise();
    }

    /**
     * Load next exercise
     */
    async loadNextExercise() {
        const exerciseType = document.getElementById('ear-exercise-type').value;

        try {
            this.currentExercise = await gameManager.fetchExercise('ear_training', this.currentElo);

            // Update instruction
            const instruction = document.getElementById('ear-instruction');
            if (this.currentExercise.exercise_type === 'interval') {
                instruction.textContent = `Identify the interval (${this.currentExercise.direction})`;
            } else if (this.currentExercise.exercise_type === 'chord') {
                instruction.textContent = 'Identify the chord quality';
            } else {
                instruction.textContent = 'Identify the chord progression';
            }

            // Populate choices
            this.populateChoices(this.currentExercise.choices);

            // Auto-play the exercise
            setTimeout(() => this.playCurrentExercise(), 300);

        } catch (error) {
            console.error('Error loading exercise:', error);
            document.getElementById('ear-instruction').textContent = 'Error loading exercise. Please try again.';
        }
    }

    /**
     * Populate answer choices
     */
    populateChoices(choices) {
        const choicesContainer = document.getElementById('ear-choices');
        choicesContainer.innerHTML = '';

        choices.forEach((choice, index) => {
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.textContent = choice;
            btn.addEventListener('click', () => this.handleAnswer(choice, btn));
            choicesContainer.appendChild(btn);
        });
    }

    /**
     * Play the current exercise sound
     */
    playCurrentExercise() {
        if (!this.currentExercise || this.isPlaying) return;

        this.isPlaying = true;
        const ex = this.currentExercise;

        if (ex.exercise_type === 'interval') {
            // Play interval
            if (ex.play_style === 'harmonic') {
                // Play both notes together
                audioManager.playChord([ex.root_midi, ex.top_midi], 1.0);
            } else {
                // Play notes sequentially
                const notes = ex.direction === 'ascending'
                    ? [ex.root_midi, ex.top_midi]
                    : [ex.top_midi, ex.root_midi];
                audioManager.playMelody(notes, 0.5, 0.1);
            }
        } else if (ex.exercise_type === 'chord') {
            // Play chord
            audioManager.playChord(ex.chord_midis, 1.5);
        } else if (ex.exercise_type === 'progression') {
            // Play progression (simplified - just play root notes)
            const rootMidi = ex.root_midi;
            const pattern = ex.progression.map(numeral => {
                // Simple mapping of Roman numerals to scale degrees
                const degree = this.romanToScaleDegree(numeral);
                return rootMidi + degree;
            });
            audioManager.playMelody(pattern, 0.8, 0.2);
        }

        // Reset playing flag after sound finishes
        setTimeout(() => {
            this.isPlaying = false;
        }, 3000);
    }

    /**
     * Convert Roman numeral to scale degree (simplified)
     */
    romanToScaleDegree(numeral) {
        const map = {
            'I': 0, 'i': 0,
            'II': 2, 'ii': 2,
            'III': 4, 'iii': 4,
            'IV': 5, 'iv': 5,
            'V': 7, 'v': 7,
            'VI': 9, 'vi': 9,
            'VII': 11, 'vii': 11
        };
        return map[numeral] || 0;
    }

    /**
     * Handle answer selection
     */
    async handleAnswer(selectedAnswer, button) {
        // Disable all choice buttons
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = true;
        });

        const correct = selectedAnswer === this.currentExercise.correct_answer;

        // Visual feedback
        if (correct) {
            button.classList.add('correct');
            audioManager.playChirp();
        } else {
            button.classList.add('incorrect');
            // Highlight the correct answer
            document.querySelectorAll('.choice-btn').forEach(btn => {
                if (btn.textContent === this.currentExercise.correct_answer) {
                    btn.classList.add('correct');
                }
            });
        }

        // Update session stats
        this.session.total++;
        if (correct) {
            this.session.correct++;
        }

        this.updateSessionStats();

        // Record completion
        const timeMs = Date.now() - this.session.startTime;
        gameManager.recordCompletion('ear_training', correct, timeMs);

        // Update mode progress
        const progress = storageManager.load('mode_progress').ear_training;
        progress.total = (progress.total || 0) + 1;
        progress.correct = (progress.correct || 0) + (correct ? 1 : 0);
        storageManager.updateModeProgress('ear_training', progress);

        // Wait before allowing next
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Re-enable next button
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('correct', 'incorrect');
        });
    }

    /**
     * Update session statistics display
     */
    updateSessionStats() {
        document.getElementById('ear-session-correct').textContent = this.session.correct;
        document.getElementById('ear-session-total').textContent = this.session.total;

        const accuracy = this.session.total > 0
            ? ((this.session.correct / this.session.total) * 100).toFixed(1)
            : 0;
        document.getElementById('ear-session-accuracy').textContent = accuracy + '%';
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
        const progress = storageManager.load('mode_progress').ear_training;
        progress.sessions = (progress.sessions || 0) + 1;
        progress.total_time = (progress.total_time || 0) + duration;
        storageManager.updateModeProgress('ear_training', progress);

        // Log practice session
        storageManager.logPracticeSession('ear_training', duration, {
            correct: this.session.correct,
            total: this.session.total,
            accuracy: parseFloat(accuracy)
        });

        // Calculate Elo change
        const avgCorrect = this.session.correct / Math.max(1, this.session.total);
        const eloChange = Math.round((avgCorrect - 0.5) * 20); // -10 to +10 based on accuracy

        const newElo = storageManager.updateElo(eloChange);

        // Show results
        document.getElementById('ear-exercise-area').classList.add('hidden');
        document.getElementById('ear-results').classList.remove('hidden');

        document.getElementById('ear-results-correct').textContent = this.session.correct + ' / ' + this.session.total;
        document.getElementById('ear-results-accuracy').textContent = accuracy + '%';
        document.getElementById('ear-results-elo').textContent = (eloChange >= 0 ? '+' : '') + eloChange;

        // Update streak
        storageManager.updateStreak();
    }
}

// Create instance
window.ear_training = new EarTraining();
