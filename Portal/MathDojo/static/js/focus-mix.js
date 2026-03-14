/**
 * FocusMix - Interleaved weakness-targeting drill across all problem types.
 * Pulls focus tags from the prediction engine across arithmetic, financial,
 * and poker categories, fetches proportional batches, and shuffles them.
 * Shares #screen-drill-game with CustomDrill and FinancialDrill.
 */
class FocusMix {
    constructor() {
        // Game state
        this.isActive = false;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.currentStreak = 0;
        this.bestStreak = 0;
        this.startTime = null;
        this.elapsedInterval = null;
        this.fetching = false;

        // Shared drill screen DOM elements
        this.drillBackBtn = document.getElementById('drill-back-btn');
        this.correctDisplay = document.getElementById('drill-correct-display');
        this.wrongDisplay = document.getElementById('drill-wrong-display');
        this.streakDisplay = document.getElementById('drill-streak-display');
        this.timerDisplay = document.getElementById('drill-timer-display');
        this.equationDisplay = document.getElementById('drill-equation-display');
        this.feedbackDisplay = document.getElementById('drill-feedback-display');
        this.drillStartButton = document.getElementById('start-drill-level');

        // Explanation panel (reuse financial explanation panel)
        this.explanationPanel = document.getElementById('financial-explanation');
        this.explanationAnswer = document.getElementById('financial-explanation-answer');
        this.explanationSteps = document.getElementById('financial-explanation-steps');
        this.nextBtn = document.getElementById('financial-next-btn');

        // Input handler (shared input element)
        this.inputHandler = new InputHandler('drill-answer-input', (answer) => this.handleAnswer(answer));

        // Menu button
        this.menuBtn = document.getElementById('focus-mix-btn');
        if (this.menuBtn) {
            this.menuBtn.addEventListener('click', () => this.openDrillScreen());
        }

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.endDrill();
            }
        });
    }

    /**
     * Open the shared drill game screen
     */
    openDrillScreen() {
        this._ownsGameScreen = true;
        screenManager.showScreen('screen-drill-game');

        // Financial equations can be long — enable auto-shrink
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

        // Override start button
        this.drillStartButton._focusMixHandler = () => this.startDrill();
        this.drillStartButton.addEventListener('click', this.drillStartButton._focusMixHandler);

        // Override back button
        this.drillBackBtn._focusMixHandler = () => {
            if (this.isActive) {
                this.endDrill();
            } else {
                this.cleanupGameScreen();
                screenManager.showScreen('screen-menu');
            }
        };
        this.drillBackBtn.addEventListener('click', this.drillBackBtn._focusMixHandler);

        // Override NEXT button for explanations
        this.nextBtn._focusMixHandler = () => {
            this.hideExplanation();
            this.loadNextProblem();
            this.inputHandler.focus();
        };
        this.nextBtn.addEventListener('click', this.nextBtn._focusMixHandler);
    }

    /**
     * Clean up shared game screen when leaving
     */
    cleanupGameScreen() {
        this._ownsGameScreen = false;
        if (this.equationDisplay) {
            this.equationDisplay.classList.remove('equation-financial');
        }
        if (this.drillStartButton && this.drillStartButton._focusMixHandler) {
            this.drillStartButton.removeEventListener('click', this.drillStartButton._focusMixHandler);
            delete this.drillStartButton._focusMixHandler;
        }
        if (this.drillBackBtn && this.drillBackBtn._focusMixHandler) {
            this.drillBackBtn.removeEventListener('click', this.drillBackBtn._focusMixHandler);
            delete this.drillBackBtn._focusMixHandler;
        }
        if (this.nextBtn && this.nextBtn._focusMixHandler) {
            this.nextBtn.removeEventListener('click', this.nextBtn._focusMixHandler);
            delete this.nextBtn._focusMixHandler;
        }
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

        profileManager.startSession('focus_mix');

        if (this.drillStartButton) this.drillStartButton.style.display = 'none';

        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Get focus tags across ALL modes
        gameManager.problemQueue = [];
        const focusTags = await profileManager.getFocusTags('all');
        await gameManager.loadMixedDrill(60, focusTags);

        this.loadNextProblem();
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

        // Update mental math hint (auto-hides for financial/poker problems)
        MentalGuides.update(problem.tags || [], 'drill');

        // Auto-submit when typed value matches the correct answer
        const tolerance = gameManager.currentProblem?.tolerance || 0;
        this.inputHandler.setAutoCheck((val) =>
            tolerance > 0
                ? Math.abs(val - gameManager.currentProblem.answer) <= tolerance
                : val === gameManager.currentProblem.answer
        );

        // Pre-fetch if running low
        if (gameManager.problemQueue.length < 5 && !this.fetching) {
            this.fetching = true;
            profileManager.invalidateCache();
            profileManager.getFocusTags('all').then(tags => {
                gameManager.loadMixedDrill(60, tags).then(() => {
                    this.fetching = false;
                });
            });
        }
    }

    /**
     * Emergency refetch when queue empty
     */
    async refetchAndContinue() {
        this.fetching = true;
        const focusTags = await profileManager.getFocusTags('all');
        await gameManager.loadMixedDrill(60, focusTags);
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
        const tolerance = gameManager.currentProblem?.tolerance || 0;
        const prefix = tolerance > 0 ? '\u2248' : '';

        profileManager.recordResult(tags, result.correct, result.timeElapsed * 1000);

        if (result.correct) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) {
                this.bestStreak = this.currentStreak;
            }
            if (tolerance > 0) {
                const pctOff = correctAnswer !== 0
                    ? Math.abs((userAnswer - correctAnswer) / correctAnswer * 100) : 0;
                const pctOffStr = pctOff === 0 ? 'exact' : `${pctOff.toFixed(1)}% off`;
                this.showFeedback(`\u2713 ${prefix}${correctAnswer} (${pctOffStr})`, 'var(--neon-green)');
            } else {
                this.showFeedback('\u2713', 'var(--neon-green)');
            }
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            if (tolerance > 0) {
                const pctOff = correctAnswer !== 0
                    ? Math.abs((userAnswer - correctAnswer) / correctAnswer * 100) : 0;
                const pctOffStr = pctOff === 0 ? 'exact' : `${pctOff.toFixed(1)}% off`;
                this.showFeedback(`\u2717 ${prefix}${correctAnswer} (${pctOffStr})`, 'var(--alert-red)');
            } else {
                this.showFeedback(`\u2717 ${correctAnswer}`, 'var(--alert-red)');
            }
        }

        this.updateStats();

        // Show explanation for wrong answers that have one
        if (!result.correct && explanation) {
            this.inputHandler.clear();
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
let focusMix;
document.addEventListener('DOMContentLoaded', () => {
    focusMix = new FocusMix();
});
