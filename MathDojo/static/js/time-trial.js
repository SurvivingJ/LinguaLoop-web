/**
 * TimeTrial - 60-second time trial game mode
 */
class TimeTrial {
    constructor() {
        this.isActive = false;
        this.timeRemaining = 60;
        this.score = 0;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.timerInterval = null;
        this.currentElo = 1000;

        // DOM elements
        this.timerDisplay = document.getElementById('timer-display');
        this.scoreDisplay = document.getElementById('score-display');
        this.equationDisplay = document.getElementById('equation-display');
        this.feedbackDisplay = document.getElementById('feedback-display');
        this.startButton = document.getElementById('start-time-trial');
        this.gameArea = document.querySelector('#screen-time-trial .game-area');

        // Input handler
        this.inputHandler = new InputHandler('answer-input', (answer) => this.handleAnswer(answer));

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        if (this.startButton) {
            this.startButton.addEventListener('click', () => this.start());
        }
    }

    /**
     * Start the game
     */
    async start() {
        this.isActive = true;
        window.gameActive = true;
        this.timeRemaining = 60;
        this.score = 0;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.currentElo = storageManager.load('user_elo');

        // Hide start button
        if (this.startButton) this.startButton.style.display = 'none';

        // Enable input
        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Update displays
        this.updateDisplay();

        // Load first problem
        await this.loadNextProblem();

        // Start timer
        this.startTimer();
    }

    /**
     * Start countdown timer
     */
    startTimer() {
        this.timerInterval = setInterval(() => {
            this.timeRemaining--;

            if (this.timerDisplay) {
                this.timerDisplay.textContent = this.timeRemaining;

                // Flash red when time is running out
                if (this.timeRemaining <= 10) {
                    this.timerDisplay.style.color = 'var(--alert-red)';
                }
            }

            if (this.timeRemaining <= 0) {
                this.end();
            }
        }, 1000);
    }

    /**
     * Load next problem
     */
    async loadNextProblem() {
        const problem = await gameManager.getNextProblem(this.currentElo);

        if (this.equationDisplay) {
            this.equationDisplay.textContent = problem.equation;
        }
    }

    /**
     * Handle answer submission
     */
    async handleAnswer(userAnswer) {
        if (!this.isActive) return;

        const result = gameManager.checkAnswerTimeTrial(userAnswer, this.correctAnswers);

        if (result.correct) {
            this.handleCorrectAnswer(result);
        } else {
            this.handleWrongAnswer(result);
        }

        // Update Elo
        this.currentElo = storageManager.updateElo(result.eloChange);

        // Clear input and load next problem
        this.inputHandler.clear();
        await this.loadNextProblem();
        this.inputHandler.focus();
    }

    /**
     * Handle correct answer
     */
    handleCorrectAnswer(result) {
        this.correctAnswers++;
        this.score++;

        // Visual feedback
        this.showFeedback('✓ CORRECT', 'var(--neon-green)');
        this.flashScreen('flash-correct');

        // Play sound (if implemented)
        this.playSound('correct');

        this.updateDisplay();
    }

    /**
     * Handle wrong answer
     */
    handleWrongAnswer(result) {
        this.wrongAnswers++;

        // Visual feedback
        this.showFeedback(`✗ WRONG (${result.correctAnswer})`, 'var(--alert-red)');
        this.flashScreen('flash-wrong');
        this.shakeScreen();

        // Play sound (if implemented)
        this.playSound('wrong');
    }

    /**
     * Update score and timer displays
     */
    updateDisplay() {
        if (this.scoreDisplay) {
            this.scoreDisplay.textContent = this.score;
        }

        if (this.timerDisplay) {
            this.timerDisplay.textContent = this.timeRemaining;
        }
    }

    /**
     * Show feedback message
     */
    showFeedback(message, color) {
        if (this.feedbackDisplay) {
            this.feedbackDisplay.textContent = message;
            this.feedbackDisplay.style.color = color;

            // Clear after 1 second
            setTimeout(() => {
                if (this.feedbackDisplay) {
                    this.feedbackDisplay.textContent = '';
                }
            }, 1000);
        }
    }

    /**
     * Flash screen effect
     */
    flashScreen(className) {
        if (this.gameArea) {
            this.gameArea.classList.add(className);
            setTimeout(() => {
                this.gameArea.classList.remove(className);
            }, 300);
        }
    }

    /**
     * Shake screen effect
     */
    shakeScreen() {
        if (this.gameArea) {
            this.gameArea.classList.add('shake');
            setTimeout(() => {
                this.gameArea.classList.remove('shake');
            }, 300);
        }
    }

    /**
     * Play sound effect
     */
    playSound(soundName) {
        // Will be implemented with AudioManager
        if (window.audioManager) {
            window.audioManager.play(soundName);
        }
    }

    /**
     * End the game
     */
    end() {
        this.isActive = false;
        window.gameActive = false;

        // Stop timer
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }

        // Disable input
        this.inputHandler.disable();

        // Calculate stats
        const totalAnswers = this.correctAnswers + this.wrongAnswers;
        const accuracy = totalAnswers > 0 ? Math.round((this.correctAnswers / totalAnswers) * 100) : 0;
        const problemsPerMin = this.correctAnswers; // Already 60 seconds

        // Check for high score
        const isNewHighScore = storageManager.updateHighScore('time_trial', this.score);

        // Update streak
        storageManager.updateStreak();

        // Show results
        this.showResults(this.score, accuracy, problemsPerMin, this.currentElo, isNewHighScore);

        // Reset UI
        if (this.startButton) this.startButton.style.display = 'block';
        if (this.timerDisplay) {
            this.timerDisplay.textContent = '60';
            this.timerDisplay.style.color = 'var(--amber)';
        }
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
    }

    /**
     * Show results screen
     */
    showResults(score, accuracy, problemsPerMin, newElo, isNewHighScore) {
        // Update results screen
        document.getElementById('result-score').textContent = score;
        document.getElementById('result-accuracy').textContent = accuracy + '%';
        document.getElementById('result-rate').textContent = problemsPerMin;
        document.getElementById('result-elo').textContent = newElo;

        const highScoreBanner = document.getElementById('high-score-banner');
        if (highScoreBanner) {
            highScoreBanner.style.display = isNewHighScore ? 'block' : 'none';
        }

        // Switch to results screen
        screenManager.showScreen('screen-results');
    }
}

// Initialize when DOM is ready
let timeTrial;
document.addEventListener('DOMContentLoaded', () => {
    timeTrial = new TimeTrial();
});
