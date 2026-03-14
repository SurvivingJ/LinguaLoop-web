/**
 * FinancialDrill - Configurable infinite financial math drill
 * Shares #screen-drill-game with CustomDrill
 */
class FinancialDrill {
    constructor() {
        // Config state
        this.categories = new Set(['rules']);
        this.difficulty = 'normal'; // easy, normal, hard
        this.difficultyLabels = ['EASY', 'NORMAL', 'HARD'];
        this.difficultyValues = ['easy', 'normal', 'hard'];

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
        this.catToggles = document.querySelectorAll('.fin-toggle');
        this.difficultySlider = document.getElementById('fin-difficulty');
        this.difficultyLabel = document.getElementById('fin-difficulty-label');
        this.startButton = document.getElementById('start-financial-drill');

        // Game DOM elements (shared with CustomDrill)
        this.drillBackBtn = document.getElementById('drill-back-btn');
        this.correctDisplay = document.getElementById('drill-correct-display');
        this.wrongDisplay = document.getElementById('drill-wrong-display');
        this.streakDisplay = document.getElementById('drill-streak-display');
        this.timerDisplay = document.getElementById('drill-timer-display');
        this.equationDisplay = document.getElementById('drill-equation-display');
        this.feedbackDisplay = document.getElementById('drill-feedback-display');
        this.drillStartButton = document.getElementById('start-drill-level');

        // Explanation panel DOM elements
        this.explanationPanel = document.getElementById('financial-explanation');
        this.explanationAnswer = document.getElementById('financial-explanation-answer');
        this.explanationSteps = document.getElementById('financial-explanation-steps');
        this.nextBtn = document.getElementById('financial-next-btn');

        // Input handler (shared with CustomDrill via same input element)
        this.inputHandler = new InputHandler('drill-answer-input', (answer) => this.handleAnswer(answer));

        this.setupConfigListeners();
        this.setupGameListeners();
    }

    /**
     * Setup config screen listeners
     */
    setupConfigListeners() {
        // Category toggle buttons
        this.catToggles.forEach(btn => {
            btn.addEventListener('click', () => {
                const cat = btn.dataset.cat;
                if (btn.classList.contains('active')) {
                    if (this.categories.size > 1) {
                        btn.classList.remove('active');
                        this.categories.delete(cat);
                    }
                } else {
                    btn.classList.add('active');
                    this.categories.add(cat);
                }
            });
        });

        // Difficulty slider
        if (this.difficultySlider) {
            this.difficultySlider.addEventListener('input', () => {
                const idx = parseInt(this.difficultySlider.value);
                this.difficulty = this.difficultyValues[idx];
                if (this.difficultyLabel) {
                    this.difficultyLabel.textContent = this.difficultyLabels[idx];
                }
            });
        }

        // Start button
        if (this.startButton) {
            this.startButton.addEventListener('click', () => this.openDrillScreen());
        }
    }

    /**
     * Setup game screen listeners
     */
    setupGameListeners() {
        // The drill-back-btn and start-drill-level are shared with CustomDrill.
        // We use a flag (this.isActive) to determine which drill is running.
        // The back button and escape already have listeners from CustomDrill,
        // but we add our own escape handler for financial drill.
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.endDrill();
            }
        });

        // NEXT button after wrong-answer explanation
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                if (!this.isActive) return;
                this.hideExplanation();
                this.loadNextProblem();
                this.inputHandler.focus();
            });
        }
    }

    /**
     * Navigate to shared drill game screen
     */
    openDrillScreen() {
        // Mark that financial drill owns the game screen
        this._ownsGameScreen = true;

        screenManager.showScreen('screen-drill-game');

        // Add financial equation class for auto-shrink text
        if (this.equationDisplay) {
            this.equationDisplay.classList.add('equation-financial');
        }

        // Reset displays
        this.hideExplanation();
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
        if (this.correctDisplay) this.correctDisplay.textContent = '0';
        if (this.wrongDisplay) this.wrongDisplay.textContent = '0';
        if (this.streakDisplay) this.streakDisplay.textContent = '0';
        if (this.timerDisplay) this.timerDisplay.textContent = '0:00';
        if (this.drillStartButton) this.drillStartButton.style.display = 'block';

        // Override the start button for financial drill
        this.drillStartButton._financialHandler = () => this.startDrill();
        this.drillStartButton.addEventListener('click', this.drillStartButton._financialHandler);

        // Override back button for financial drill
        this.drillBackBtn._financialHandler = () => {
            if (this.isActive) {
                this.endDrill();
            } else {
                this.cleanupGameScreen();
                screenManager.showScreen('screen-financial-drill');
            }
        };
        this.drillBackBtn.addEventListener('click', this.drillBackBtn._financialHandler);
    }

    /**
     * Clean up shared game screen when leaving
     */
    cleanupGameScreen() {
        this._ownsGameScreen = false;
        if (this.equationDisplay) {
            this.equationDisplay.classList.remove('equation-financial');
        }
        // Remove financial-specific event listeners
        if (this.drillStartButton && this.drillStartButton._financialHandler) {
            this.drillStartButton.removeEventListener('click', this.drillStartButton._financialHandler);
            delete this.drillStartButton._financialHandler;
        }
        if (this.drillBackBtn && this.drillBackBtn._financialHandler) {
            this.drillBackBtn.removeEventListener('click', this.drillBackBtn._financialHandler);
            delete this.drillBackBtn._financialHandler;
        }
    }

    /**
     * Get options for API
     */
    getOptions() {
        return {
            categories: Array.from(this.categories),
            difficulty: this.difficulty
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
        this.startTime = Date.now();
        this.coach.reset();
        this.intervention.deactivate();

        // Start profile session
        profileManager.startSession('financial_drill');

        // Hide start button
        if (this.drillStartButton) this.drillStartButton.style.display = 'none';

        // Enable input
        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Clear queue and load initial batch with profile focus tags
        gameManager.problemQueue = [];
        const profileFocus = await profileManager.getFocusTags('financial');
        await gameManager.loadFinancialDrill(50, this.getOptions(), profileFocus);

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
            if (this.equationDisplay) this.equationDisplay.textContent = 'LOADING...';
            this.refetchAndContinue();
            return;
        }

        if (this.equationDisplay) {
            this.equationDisplay.textContent = problem.equation;
        }

        // Update mental math hint (auto-hides for financial problems)
        MentalGuides.update(problem.tags || [], 'drill');

        // Auto-submit when typed value matches the correct answer
        const tolerance = gameManager.currentProblem?.tolerance || 0;
        this.inputHandler.setAutoCheck((val) =>
            tolerance > 0
                ? Math.abs(val - gameManager.currentProblem.answer) <= tolerance
                : val === gameManager.currentProblem.answer
        );

        // Pre-fetch more if queue running low
        if (gameManager.problemQueue.length < 5 && !this.fetching) {
            this.fetching = true;
            const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
            gameManager.loadFinancialDrill(50, this.getOptions(), focusTags).then(() => {
                this.fetching = false;
            });
        }
    }

    /**
     * Emergency refetch when queue empty
     */
    async refetchAndContinue() {
        this.fetching = true;
        const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
        await gameManager.loadFinancialDrill(50, this.getOptions(), focusTags);
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
        const tags = gameManager.currentProblem?.tags || [];
        const explanation = gameManager.currentProblem?.explanation || '';

        const correctAnswer = result.correctAnswer;
        const pctOff = correctAnswer !== 0
            ? Math.abs((userAnswer - correctAnswer) / correctAnswer * 100)
            : Math.abs(userAnswer - correctAnswer);
        const pctOffStr = pctOff === 0 ? 'exact' : `${pctOff.toFixed(1)}% off`;
        const tolerance = gameManager.currentProblem?.tolerance || 0;
        const prefix = tolerance > 0 ? '\u2248' : '';

        // Record with coach and profile manager
        this.coach.record(tags, result.correct, result.timeElapsed * 1000);
        profileManager.recordResult(tags, result.correct, result.timeElapsed * 1000);

        if (result.correct) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) {
                this.bestStreak = this.currentStreak;
            }
            this.showFeedback(`\u2713 ${prefix}${correctAnswer} (${pctOffStr})`, 'var(--neon-green)');
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            this.showFeedback(`\u2717 ${prefix}${correctAnswer} (${pctOffStr})`, 'var(--alert-red)');
        }
        this.updateStats();

        // Check intervention mastery (must happen before showExplanation)
        if (this.intervention.isActive) {
            const check = this.intervention.afterAnswer(tags, result.correct, result.timeElapsed * 1000);
            if (check.mastered) {
                // Mastery modal takes priority — skip explanation panel
                return;
            }
        }

        if (!result.correct) {
            this.inputHandler.clear();
            // Show explanation panel — user must click NEXT to continue
            this.showExplanation(`${prefix}${correctAnswer}`, explanation);
            return;
        }

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
                if (this.feedbackDisplay) this.feedbackDisplay.textContent = '';
            }, 1500);
        }
    }

    /**
     * Show explanation panel after wrong answer
     */
    showExplanation(answerText, explanation) {
        if (this.explanationPanel) {
            if (this.explanationAnswer) this.explanationAnswer.textContent = `Answer: ${answerText}`;
            if (this.explanationSteps) this.explanationSteps.textContent = explanation;
            this.explanationPanel.style.display = 'block';
        }
        this.inputHandler.disable();
    }

    /**
     * Hide explanation panel
     */
    hideExplanation() {
        if (this.explanationPanel) {
            this.explanationPanel.style.display = 'none';
        }
        this.inputHandler.enable();
    }

    /**
     * End the drill and show results
     */
    endDrill() {
        this.isActive = false;
        window.gameActive = false;
        this.intervention.deactivate();
        this.hideExplanation();
        profileManager.endSession();

        if (this.elapsedInterval) {
            clearInterval(this.elapsedInterval);
            this.elapsedInterval = null;
        }

        this.inputHandler.disable();

        const totalProblems = this.correctAnswers + this.wrongAnswers;
        const accuracy = totalProblems > 0
            ? Math.round((this.correctAnswers / totalProblems) * 100) : 0;
        const elapsedSeconds = (Date.now() - this.startTime) / 1000;
        const problemsPerMin = elapsedSeconds > 0
            ? (totalProblems / (elapsedSeconds / 60)).toFixed(1) : 0;

        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = Math.floor(elapsedSeconds % 60);
        const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        document.getElementById('result-score').textContent = this.correctAnswers;
        document.getElementById('result-accuracy').textContent = `${accuracy}%`;
        document.getElementById('result-rate').textContent = problemsPerMin;
        document.getElementById('result-elo').textContent = timeString;

        const eloLabel = document.getElementById('result-elo')?.closest('.result-item')?.querySelector('.result-label');
        if (eloLabel) eloLabel.textContent = 'TIME';

        const banner = document.getElementById('high-score-banner');
        if (banner) banner.style.display = 'none';

        this.cleanupGameScreen();
        screenManager.showScreen('screen-results');

        if (this.drillStartButton) this.drillStartButton.style.display = 'block';
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
    }
}

// Initialize when DOM is ready
let financialDrill;
document.addEventListener('DOMContentLoaded', () => {
    financialDrill = new FinancialDrill();
});
