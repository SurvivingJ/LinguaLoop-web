/**
 * CustomDrill - Configurable infinite drill mode
 */
class CustomDrill {
    constructor() {
        // Config state
        this.operations = new Set(['addition']);
        this.mix = false;
        this.minDigits = 1;
        this.maxDigits = 2;

        // Game state
        this.isActive = false;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.currentStreak = 0;
        this.bestStreak = 0;
        this.startTime = null;
        this.elapsedInterval = null;
        this.fetching = false;
        this.coach = new SessionCoach();
        this.intervention = new InterventionMode();

        // Wire SessionCoach intervention trigger
        this.coach.onIntervention = (tag, score) => {
            if (!this.intervention.isActive) {
                this.intervention.activate(tag);
            }
        };

        // Wire mastery dismissal — resume drill after modal OK
        this.intervention.onMasteryDismissed = () => {
            this.inputHandler.clear();
            this.loadNextProblem();
            this.inputHandler.focus();
        };

        // Config DOM elements
        this.opToggles = document.querySelectorAll('.op-toggle');
        this.mixToggle = document.getElementById('mix-toggle');
        this.minDigitsSlider = document.getElementById('min-digits');
        this.maxDigitsSlider = document.getElementById('max-digits');
        this.minDigitsValue = document.getElementById('min-digits-value');
        this.maxDigitsValue = document.getElementById('max-digits-value');
        this.startButton = document.getElementById('start-custom-drill');

        // Game DOM elements
        this.drillBackBtn = document.getElementById('drill-back-btn');
        this.correctDisplay = document.getElementById('drill-correct-display');
        this.wrongDisplay = document.getElementById('drill-wrong-display');
        this.streakDisplay = document.getElementById('drill-streak-display');
        this.timerDisplay = document.getElementById('drill-timer-display');
        this.equationDisplay = document.getElementById('drill-equation-display');
        this.feedbackDisplay = document.getElementById('drill-feedback-display');
        this.drillStartButton = document.getElementById('start-drill-level');

        // Input handler for drill game
        this.inputHandler = new InputHandler('drill-answer-input', (answer) => this.handleAnswer(answer));

        this.setupConfigListeners();
        this.setupGameListeners();
    }

    /**
     * Setup config screen listeners
     */
    setupConfigListeners() {
        // Operation toggle buttons
        this.opToggles.forEach(btn => {
            btn.addEventListener('click', () => {
                const op = btn.dataset.op;
                if (btn.classList.contains('active')) {
                    // Don't allow deselecting the last operation
                    if (this.operations.size > 1) {
                        btn.classList.remove('active');
                        this.operations.delete(op);
                    }
                } else {
                    btn.classList.add('active');
                    this.operations.add(op);
                }
                this.updateMixVisibility();
            });
        });

        // Mix toggle
        if (this.mixToggle) {
            this.mixToggle.addEventListener('click', () => {
                this.mix = !this.mix;
                this.mixToggle.textContent = this.mix ? 'ON' : 'OFF';
                this.mixToggle.classList.toggle('active', this.mix);
            });
        }

        // Digit sliders
        if (this.minDigitsSlider) {
            this.minDigitsSlider.addEventListener('input', () => {
                this.minDigits = parseInt(this.minDigitsSlider.value);
                this.minDigitsValue.textContent = this.minDigits;
                // Enforce min <= max
                if (this.minDigits > this.maxDigits) {
                    this.maxDigits = this.minDigits;
                    this.maxDigitsSlider.value = this.maxDigits;
                    this.maxDigitsValue.textContent = this.maxDigits;
                }
            });
        }

        if (this.maxDigitsSlider) {
            this.maxDigitsSlider.addEventListener('input', () => {
                this.maxDigits = parseInt(this.maxDigitsSlider.value);
                this.maxDigitsValue.textContent = this.maxDigits;
                // Enforce min <= max
                if (this.maxDigits < this.minDigits) {
                    this.minDigits = this.maxDigits;
                    this.minDigitsSlider.value = this.minDigits;
                    this.minDigitsValue.textContent = this.minDigits;
                }
            });
        }

        // Start drill button
        if (this.startButton) {
            this.startButton.addEventListener('click', () => this.openDrillScreen());
        }
    }

    /**
     * Show/hide mix toggle based on selected operations
     */
    updateMixVisibility() {
        // Mix only makes sense with 2+ operations
        const mixSection = this.mixToggle ? this.mixToggle.closest('.config-section') : null;
        if (mixSection) {
            mixSection.style.display = this.operations.size >= 2 ? 'block' : 'none';
        }
        // If only 1 op selected, force mix off
        if (this.operations.size < 2) {
            this.mix = false;
            if (this.mixToggle) {
                this.mixToggle.textContent = 'OFF';
                this.mixToggle.classList.remove('active');
            }
        }
    }

    /**
     * Setup game screen listeners
     */
    setupGameListeners() {
        // Start button on drill game screen
        if (this.drillStartButton) {
            this.drillStartButton.addEventListener('click', () => this.startDrill());
        }

        // Back button ends drill
        if (this.drillBackBtn) {
            this.drillBackBtn.addEventListener('click', () => {
                if (!this._ownsGameScreen) return;
                if (this.isActive) {
                    this.endDrill();
                } else {
                    screenManager.showScreen('screen-daily-drill');
                }
            });
        }

        // Escape key ends drill
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.endDrill();
            }
        });
    }

    /**
     * Navigate to drill game screen
     */
    openDrillScreen() {
        this._ownsGameScreen = true;
        screenManager.showScreen('screen-drill-game');

        // Reset displays
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
        if (this.correctDisplay) this.correctDisplay.textContent = '0';
        if (this.wrongDisplay) this.wrongDisplay.textContent = '0';
        if (this.streakDisplay) this.streakDisplay.textContent = '0';
        if (this.timerDisplay) this.timerDisplay.textContent = '0:00';
        if (this.drillStartButton) this.drillStartButton.style.display = 'block';
    }

    /**
     * Get current options object for API
     */
    getOptions() {
        return {
            operations: Array.from(this.operations),
            mix: this.mix,
            min_digits: this.minDigits,
            max_digits: this.maxDigits
        };
    }

    /**
     * Start the drill
     */
    async startDrill() {
        if (!this._ownsGameScreen) return;
        this.isActive = true;
        window.gameActive = true;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.currentStreak = 0;
        this.bestStreak = 0;
        this.coach.reset();
        this.intervention.deactivate();
        this.startTime = Date.now();

        // Start profile session
        profileManager.startSession('custom_drill');

        // Hide start button
        if (this.drillStartButton) this.drillStartButton.style.display = 'none';

        // Enable input
        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Clear queue and load initial batch with profile focus tags
        gameManager.problemQueue = [];
        const profileFocus = await profileManager.getFocusTags('custom');
        await gameManager.loadCustomDrill(50, this.getOptions(), profileFocus);

        // Load first problem
        this.loadNextProblem();

        // Start elapsed timer
        this.startElapsedTimer();
    }

    /**
     * Start counting elapsed time
     */
    startElapsedTimer() {
        this.elapsedInterval = setInterval(() => {
            if (this.timerDisplay) {
                const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                this.timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    /**
     * Load next problem from queue
     */
    loadNextProblem() {
        const problem = gameManager.getFromQueue();

        if (!problem) {
            // Queue empty — should not happen if pre-fetching works, but handle it
            this.equationDisplay.textContent = 'LOADING...';
            this.refetchAndContinue();
            return;
        }

        if (this.equationDisplay) {
            this.equationDisplay.textContent = problem.equation;
        }

        // Update mental math hint
        MentalGuides.update(problem.tags || [], 'drill');

        // Auto-submit when typed value matches the correct answer
        const tolerance = gameManager.currentProblem?.tolerance || 0;
        this.inputHandler.setAutoCheck((val) =>
            tolerance > 0
                ? Math.abs(val - gameManager.currentProblem.answer) <= tolerance
                : val === gameManager.currentProblem.answer
        );

        // Pre-fetch more if queue is running low
        if (gameManager.problemQueue.length < 5 && !this.fetching) {
            this.fetching = true;
            const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
            gameManager.loadCustomDrill(50, this.getOptions(), focusTags).then(() => {
                this.fetching = false;
            });
        }
    }

    /**
     * Emergency refetch when queue is empty
     */
    async refetchAndContinue() {
        this.fetching = true;
        const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
        await gameManager.loadCustomDrill(50, this.getOptions(), focusTags);
        this.fetching = false;
        if (this.isActive) {
            this.loadNextProblem();
        }
    }

    /**
     * Handle answer submission
     */
    handleAnswer(userAnswer) {
        if (!this.isActive) return;

        MentalGuides.hide('drill');
        const result = gameManager.checkAnswer(userAnswer);

        // Record with coach and profile manager before currentProblem gets overwritten
        const tags = gameManager.currentProblem?.tags || [];
        this.coach.record(tags, result.correct, result.timeElapsed * 1000);
        profileManager.recordResult(tags, result.correct, result.timeElapsed * 1000);

        if (result.correct) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) {
                this.bestStreak = this.currentStreak;
            }
            this.showFeedback('\u2713', 'var(--neon-green)');
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            this.showFeedback(`\u2717 ${result.correctAnswer}`, 'var(--alert-red)');
        }

        // Update stats display
        this.updateStats();

        // Update intervention tracking (after score is tallied)
        if (this.intervention.isActive) {
            const check = this.intervention.afterAnswer(tags, result.correct, result.timeElapsed * 1000);
            if (check.mastered) {
                // Mastery modal is showing — pause drill, don't auto-advance
                // The onMasteryDismissed callback resumes
                return;
            }
        }

        // Clear input and load next
        this.inputHandler.clear();
        this.loadNextProblem();
        this.inputHandler.focus();
    }

    /**
     * Update running stats display
     */
    updateStats() {
        if (this.correctDisplay) this.correctDisplay.textContent = this.correctAnswers;
        if (this.wrongDisplay) this.wrongDisplay.textContent = this.wrongAnswers;
        if (this.streakDisplay) this.streakDisplay.textContent = this.currentStreak;
    }

    /**
     * Show feedback message
     */
    showFeedback(message, color) {
        if (this.feedbackDisplay) {
            this.feedbackDisplay.textContent = message;
            this.feedbackDisplay.style.color = color;

            setTimeout(() => {
                if (this.feedbackDisplay) {
                    this.feedbackDisplay.textContent = '';
                }
            }, 1000);
        }
    }

    /**
     * End the drill and show results
     */
    endDrill() {
        this.isActive = false;
        this._ownsGameScreen = false;
        window.gameActive = false;
        this.intervention.deactivate();
        profileManager.endSession();

        // Stop timer
        if (this.elapsedInterval) {
            clearInterval(this.elapsedInterval);
            this.elapsedInterval = null;
        }

        // Disable input
        this.inputHandler.disable();

        // Calculate results
        const totalProblems = this.correctAnswers + this.wrongAnswers;
        const accuracy = totalProblems > 0
            ? Math.round((this.correctAnswers / totalProblems) * 100)
            : 0;
        const elapsedSeconds = (Date.now() - this.startTime) / 1000;
        const problemsPerMin = elapsedSeconds > 0
            ? (totalProblems / (elapsedSeconds / 60)).toFixed(1)
            : 0;

        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = Math.floor(elapsedSeconds % 60);
        const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        // Show results screen
        document.getElementById('result-score').textContent = this.correctAnswers;
        document.getElementById('result-accuracy').textContent = `${accuracy}%`;
        document.getElementById('result-rate').textContent = problemsPerMin;
        document.getElementById('result-elo').textContent = timeString;

        // Change the ELO label to TIME for drill results
        const eloLabel = document.getElementById('result-elo')?.closest('.result-item')?.querySelector('.result-label');
        if (eloLabel) eloLabel.textContent = 'TIME';

        // Hide high score banner
        const banner = document.getElementById('high-score-banner');
        if (banner) banner.style.display = 'none';

        screenManager.showScreen('screen-results');

        // Reset drill game screen for next use
        if (this.drillStartButton) this.drillStartButton.style.display = 'block';
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
    }
}

// Initialize when DOM is ready
let customDrill;
document.addEventListener('DOMContentLoaded', () => {
    customDrill = new CustomDrill();
    // Initialize mix visibility
    customDrill.updateMixVisibility();
});
