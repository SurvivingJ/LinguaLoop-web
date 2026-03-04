/**
 * PokerDrill - Poker math training with 5 modes
 * Dedicated game screen with card rendering, equity slider, and range grid.
 */
class PokerDrill {
    constructor() {
        // Config state
        this.categories = new Set(['pot_odds']);
        this.difficulty = 'normal';
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
        this.currentProblem = null;

        // Coach and intervention tracking
        this.problemStartTime = 0;
        this.coach = new SessionCoach();
        this.intervention = new InterventionMode('poker-intervention-progress');

        this.coach.onIntervention = (tag, score) => {
            if (!this.intervention.isActive) {
                this.intervention.activate(tag);
            }
        };

        this.intervention.onMasteryDismissed = () => {
            this.loadNextProblem();
        };

        // Range painter state
        this._painting = false;
        this._paintMode = true; // true = select, false = deselect
        this.selectedRange = new Set();

        // Config DOM
        this.catToggles = document.querySelectorAll('.poker-toggle');
        this.difficultySlider = document.getElementById('poker-difficulty');
        this.difficultyLabel = document.getElementById('poker-difficulty-label');
        this.startConfigBtn = document.getElementById('start-poker-drill');

        // Game DOM
        this.backBtn = document.getElementById('poker-back-btn');
        this.correctDisplay = document.getElementById('poker-correct-display');
        this.wrongDisplay = document.getElementById('poker-wrong-display');
        this.streakDisplay = document.getElementById('poker-streak-display');
        this.timerDisplay = document.getElementById('poker-timer-display');
        this.equationDisplay = document.getElementById('poker-equation-display');
        this.feedbackDisplay = document.getElementById('poker-feedback-display');
        this.startGameBtn = document.getElementById('start-poker-game');

        // Sub-areas
        this.cardArea = document.getElementById('poker-card-area');
        this.numericArea = document.getElementById('poker-numeric-area');
        this.equitySliderArea = document.getElementById('poker-equity-slider-area');
        this.rangeGridArea = document.getElementById('poker-range-grid-area');

        // Equity slider
        this.equitySlider = document.getElementById('poker-equity-slider');
        this.equityValue = document.getElementById('poker-equity-value');
        this.equitySubmit = document.getElementById('poker-equity-submit');

        // Range grid
        this.rangeGrid = document.getElementById('poker-range-grid');
        this.rangeSubmit = document.getElementById('poker-range-submit');

        // Explanation panel
        this.explanationPanel = document.getElementById('poker-explanation');
        this.explanationAnswer = document.getElementById('poker-explanation-answer');
        this.explanationSteps = document.getElementById('poker-explanation-steps');
        this.nextBtn = document.getElementById('poker-next-btn');

        // Input handler for numeric modes
        this.inputHandler = new InputHandler('poker-answer-input', (answer) => this.handleNumericAnswer(answer));

        this.setupConfigListeners();
        this.setupGameListeners();
        this.buildRangeGrid();
    }

    // ── Config Screen ──────────────────────────────────

    setupConfigListeners() {
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

        if (this.difficultySlider) {
            this.difficultySlider.addEventListener('input', () => {
                const idx = parseInt(this.difficultySlider.value);
                this.difficulty = this.difficultyValues[idx];
                if (this.difficultyLabel) {
                    this.difficultyLabel.textContent = this.difficultyLabels[idx];
                }
            });
        }

        if (this.startConfigBtn) {
            this.startConfigBtn.addEventListener('click', () => this.openGameScreen());
        }
    }

    // ── Game Screen ────────────────────────────────────

    setupGameListeners() {
        if (this.backBtn) {
            this.backBtn.addEventListener('click', () => {
                if (this.isActive) {
                    this.endDrill();
                } else {
                    screenManager.showScreen('screen-poker-drill');
                }
            });
        }

        if (this.startGameBtn) {
            this.startGameBtn.addEventListener('click', () => this.startDrill());
        }

        // Equity slider
        if (this.equitySlider) {
            this.equitySlider.addEventListener('input', () => {
                if (this.equityValue) {
                    this.equityValue.textContent = this.equitySlider.value + '%';
                }
            });
        }

        if (this.equitySubmit) {
            this.equitySubmit.addEventListener('click', () => this.handleEquityAnswer());
        }

        // Range submit
        if (this.rangeSubmit) {
            this.rangeSubmit.addEventListener('click', () => this.handleRangeAnswer());
        }

        // Next button (explanation panel)
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                this.hideExplanation();
                this.loadNextProblem();
            });
        }

        // Escape to end
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.endDrill();
            }
        });
    }

    openGameScreen() {
        screenManager.showScreen('screen-poker-game');
        this.resetDisplays();
        if (this.startGameBtn) this.startGameBtn.style.display = 'block';
    }

    resetDisplays() {
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
        if (this.correctDisplay) this.correctDisplay.textContent = '0';
        if (this.wrongDisplay) this.wrongDisplay.textContent = '0';
        if (this.streakDisplay) this.streakDisplay.textContent = '0';
        if (this.timerDisplay) this.timerDisplay.textContent = '0:00';
        if (this.feedbackDisplay) this.feedbackDisplay.textContent = '';
        this.hideAllAreas();
        this.hideExplanation();
    }

    hideAllAreas() {
        if (this.cardArea) this.cardArea.style.display = 'none';
        if (this.numericArea) this.numericArea.style.display = 'none';
        if (this.equitySliderArea) this.equitySliderArea.style.display = 'none';
        if (this.rangeGridArea) this.rangeGridArea.style.display = 'none';
    }

    getOptions() {
        return {
            categories: Array.from(this.categories),
            difficulty: this.difficulty
        };
    }

    // ── Drill Lifecycle ────────────────────────────────

    async startDrill() {
        this.isActive = true;
        window.gameActive = true;
        this.correctAnswers = 0;
        this.wrongAnswers = 0;
        this.currentStreak = 0;
        this.bestStreak = 0;
        this.startTime = Date.now();
        this.coach.reset();
        this.intervention.deactivate();

        if (this.startGameBtn) this.startGameBtn.style.display = 'none';

        gameManager.problemQueue = [];
        await gameManager.loadPokerDrill(50, this.getOptions());

        this.loadNextProblem();
        this.startElapsedTimer();
    }

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

    loadNextProblem() {
        this.hideExplanation();

        const problem = gameManager.getFromQueue();

        if (!problem) {
            if (this.equationDisplay) this.equationDisplay.textContent = 'LOADING...';
            this.refetchAndContinue();
            return;
        }

        this.currentProblem = problem;
        this.showProblemForMode(problem);

        // Pre-fetch if running low
        if (gameManager.problemQueue.length < 5 && !this.fetching) {
            this.fetching = true;
            const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
            gameManager.loadPokerDrill(50, this.getOptions(), focusTags).then(() => {
                this.fetching = false;
            });
        }
    }

    async refetchAndContinue() {
        this.fetching = true;
        const focusTags = this.intervention.getFocusTags() || this.coach.getFocusTags();
        await gameManager.loadPokerDrill(50, this.getOptions(), focusTags);
        this.fetching = false;
        if (this.isActive) {
            this.loadNextProblem();
        }
    }

    // ── Mode Routing ───────────────────────────────────

    showProblemForMode(problem) {
        this.problemStartTime = Date.now();
        this.hideAllAreas();
        if (this.feedbackDisplay) this.feedbackDisplay.textContent = '';

        const mode = problem.poker_mode;
        const extra = problem.extra_data || {};

        if (this.equationDisplay) {
            this.equationDisplay.textContent = problem.equation;
        }

        switch (mode) {
            case 'pot_odds':
            case 'auto_profit':
                this.showNumericMode();
                break;

            case 'combinatorics':
                this.renderCards(extra.hero, extra.board);
                this.showNumericMode();
                break;

            case 'equity':
                this.renderCardsWithVillain(extra.hero, extra.villain, extra.board);
                this.showEquityMode();
                break;

            case 'range':
                this.showRangeMode();
                break;

            default:
                this.showNumericMode();
        }
    }

    showNumericMode() {
        if (this.numericArea) this.numericArea.style.display = 'block';
        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Auto-submit when typed value matches the correct answer
        const tolerance = this.currentProblem?.tolerance || 0;
        const answer = this.currentProblem?.answer;
        this.inputHandler.setAutoCheck((val) =>
            tolerance > 0
                ? Math.abs(val - answer) <= tolerance
                : val === answer
        );
    }

    showEquityMode() {
        if (this.equitySliderArea) this.equitySliderArea.style.display = 'block';
        if (this.equitySlider) {
            this.equitySlider.value = 50;
        }
        if (this.equityValue) {
            this.equityValue.textContent = '50%';
        }
    }

    showRangeMode() {
        if (this.rangeGridArea) this.rangeGridArea.style.display = 'block';
        this.clearRangeSelection();
    }

    // ── Explanation Panel ──────────────────────────────

    showExplanation(answerText, explanation) {
        if (!this.explanationPanel) return;

        // Disable inputs while explanation is showing
        this.inputHandler.disable();
        if (this.numericArea) this.numericArea.style.display = 'none';
        if (this.equitySubmit) this.equitySubmit.disabled = true;
        if (this.rangeSubmit) this.rangeSubmit.disabled = true;
        this._painting = false;

        if (this.explanationAnswer) {
            this.explanationAnswer.textContent = answerText;
        }
        if (this.explanationSteps) {
            this.explanationSteps.textContent = explanation || '';
        }
        this.explanationPanel.style.display = 'block';
    }

    hideExplanation() {
        if (this.explanationPanel) {
            this.explanationPanel.style.display = 'none';
        }
        if (this.equitySubmit) this.equitySubmit.disabled = false;
        if (this.rangeSubmit) this.rangeSubmit.disabled = false;
    }

    // ── Card Rendering ─────────────────────────────────

    createCardEl(cardStr) {
        const rank = cardStr[0];
        const suit = cardStr[1];
        const displayRank = rank === 'T' ? '10' : rank;
        const suitSymbols = { s: '\u2660', h: '\u2665', d: '\u2666', c: '\u2663' };

        const el = document.createElement('div');
        el.className = `poker-card suit-${suit}`;

        const rankSpan = document.createElement('span');
        rankSpan.className = 'card-rank';
        rankSpan.textContent = displayRank;

        const suitSpan = document.createElement('span');
        suitSpan.className = 'card-suit';
        suitSpan.textContent = suitSymbols[suit] || suit;

        el.appendChild(rankSpan);
        el.appendChild(suitSpan);
        return el;
    }

    renderCards(hero, board) {
        if (!this.cardArea) return;
        this.cardArea.innerHTML = '';
        this.cardArea.style.display = 'flex';

        // Hero section
        const heroSection = this._buildHandSection('HERO', hero);
        this.cardArea.appendChild(heroSection);

        // Board section
        if (board && board.length > 0) {
            const boardSection = this._buildHandSection('BOARD', board);
            this.cardArea.appendChild(boardSection);
        }
    }

    renderCardsWithVillain(hero, villain, board) {
        if (!this.cardArea) return;
        this.cardArea.innerHTML = '';
        this.cardArea.style.display = 'flex';

        const heroSection = this._buildHandSection('HERO', hero);
        this.cardArea.appendChild(heroSection);

        const vs = document.createElement('div');
        vs.className = 'poker-vs';
        vs.textContent = 'VS';
        this.cardArea.appendChild(vs);

        const villainSection = this._buildHandSection('VILLAIN', villain);
        this.cardArea.appendChild(villainSection);

        if (board && board.length > 0) {
            const boardSection = this._buildHandSection('BOARD', board);
            this.cardArea.appendChild(boardSection);
        }
    }

    _buildHandSection(label, cards) {
        const section = document.createElement('div');
        section.className = 'poker-hand-section';

        const labelEl = document.createElement('div');
        labelEl.className = 'poker-hand-label';
        labelEl.textContent = label;
        section.appendChild(labelEl);

        const cardsRow = document.createElement('div');
        cardsRow.className = 'poker-hand-cards';
        cards.forEach(c => cardsRow.appendChild(this.createCardEl(c)));
        section.appendChild(cardsRow);

        return section;
    }

    // ── Range Grid ─────────────────────────────────────

    buildRangeGrid() {
        if (!this.rangeGrid) return;

        const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

        for (let r = 0; r < 13; r++) {
            for (let c = 0; c < 13; c++) {
                const cell = document.createElement('div');
                cell.className = 'range-cell';

                let label;
                if (r === c) {
                    label = ranks[r] + ranks[c]; // Pairs on diagonal
                } else if (r < c) {
                    label = ranks[r] + ranks[c] + 's'; // Suited above diagonal
                } else {
                    label = ranks[c] + ranks[r] + 'o'; // Offsuit below diagonal
                }

                cell.textContent = label;
                cell.dataset.hand = label;

                // Mouse events for drag-to-paint
                cell.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    this._painting = true;
                    this._paintMode = !cell.classList.contains('selected');
                    this.toggleCell(cell);
                });

                cell.addEventListener('mouseenter', () => {
                    if (this._painting) {
                        this.toggleCell(cell);
                    }
                });

                // Touch events
                cell.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    this._painting = true;
                    this._paintMode = !cell.classList.contains('selected');
                    this.toggleCell(cell);
                }, { passive: false });

                this.rangeGrid.appendChild(cell);
            }
        }

        // Stop painting on mouse/touch up
        document.addEventListener('mouseup', () => { this._painting = false; });
        document.addEventListener('touchend', () => { this._painting = false; });

        // Touch move for drag painting on mobile
        if (this.rangeGrid) {
            this.rangeGrid.addEventListener('touchmove', (e) => {
                if (!this._painting) return;
                e.preventDefault();
                const touch = e.touches[0];
                const el = document.elementFromPoint(touch.clientX, touch.clientY);
                if (el && el.classList.contains('range-cell')) {
                    this.toggleCell(el);
                }
            }, { passive: false });
        }
    }

    toggleCell(cell) {
        if (this._paintMode) {
            cell.classList.add('selected');
            this.selectedRange.add(cell.dataset.hand);
        } else {
            cell.classList.remove('selected');
            this.selectedRange.delete(cell.dataset.hand);
        }
    }

    clearRangeSelection() {
        this.selectedRange.clear();
        if (this.rangeGrid) {
            this.rangeGrid.querySelectorAll('.range-cell').forEach(cell => {
                cell.classList.remove('selected', 'correct-cell', 'wrong-cell');
            });
        }
    }

    // ── Answer Handlers ────────────────────────────────

    handleNumericAnswer(userAnswer) {
        if (!this.isActive || !this.currentProblem) return;

        const result = gameManager.checkAnswer(userAnswer);
        if (!result) return;

        const tags = this.currentProblem?.tags || [];
        const timeMs = result.timeElapsed * 1000;
        this.coach.record(tags, result.correct, timeMs);

        const correctAnswer = result.correctAnswer;
        const tolerance = this.currentProblem.tolerance || 0;
        const prefix = tolerance > 0 ? '\u2248' : '';
        const extra = this.currentProblem.extra_data || {};

        if (result.correct) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) this.bestStreak = this.currentStreak;
            this.showFeedback(`\u2713 ${prefix}${correctAnswer}`, 'var(--neon-green)');
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, result.correct, timeMs);
                if (check.mastered) return;  // mastery modal showing — don't advance
            }

            this.inputHandler.clear();
            this.loadNextProblem();
            this.inputHandler.focus();
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, result.correct, timeMs);
                if (check.mastered) return;
            }

            this.inputHandler.clear();
            this.showExplanation(
                `\u2717 Answer: ${prefix}${correctAnswer}`,
                extra.explanation
            );
        }
    }

    handleEquityAnswer() {
        if (!this.isActive || !this.currentProblem) return;

        const userVal = parseInt(this.equitySlider.value);
        const answer = this.currentProblem.answer;
        const tolerance = this.currentProblem.tolerance || 5;
        const isCorrect = Math.abs(userVal - answer) <= tolerance;
        const extra = this.currentProblem.extra_data || {};

        const tags = this.currentProblem?.tags || [];
        const timeMs = Date.now() - this.problemStartTime;
        this.coach.record(tags, isCorrect, timeMs);

        if (isCorrect) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) this.bestStreak = this.currentStreak;
            this.showFeedback(`\u2713 ${answer}% (${extra.outs || '?'} outs)`, 'var(--neon-green)');
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, isCorrect, timeMs);
                if (check.mastered) return;
            }

            this.loadNextProblem();
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, isCorrect, timeMs);
                if (check.mastered) return;
            }

            this.showExplanation(
                `\u2717 Answer: ${answer}% (you guessed ${userVal}%)`,
                extra.explanation
            );
        }
    }

    handleRangeAnswer() {
        if (!this.isActive || !this.currentProblem) return;

        const correctSet = new Set(this.currentProblem.extra_data.correct_range || []);
        const userSet = this.selectedRange;

        // IoU scoring
        const intersection = new Set([...userSet].filter(h => correctSet.has(h)));
        const union = new Set([...userSet, ...correctSet]);
        const iou = union.size > 0 ? intersection.size / union.size : 0;
        const isCorrect = iou >= 0.7;

        const tags = this.currentProblem?.tags || [];
        const timeMs = Date.now() - this.problemStartTime;
        this.coach.record(tags, isCorrect, timeMs);

        // Highlight correct/wrong cells
        if (this.rangeGrid) {
            this.rangeGrid.querySelectorAll('.range-cell').forEach(cell => {
                const hand = cell.dataset.hand;
                const inCorrect = correctSet.has(hand);
                const inUser = userSet.has(hand);

                cell.classList.remove('selected');
                if (inCorrect && inUser) {
                    cell.classList.add('correct-cell');
                } else if (inCorrect && !inUser) {
                    cell.classList.add('correct-cell');
                } else if (!inCorrect && inUser) {
                    cell.classList.add('wrong-cell');
                }
            });
        }

        if (isCorrect) {
            this.correctAnswers++;
            this.currentStreak++;
            if (this.currentStreak > this.bestStreak) this.bestStreak = this.currentStreak;
            this.showFeedback(`\u2713 ${Math.round(iou * 100)}% match`, 'var(--neon-green)');
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, isCorrect, timeMs);
                if (check.mastered) return;  // skip auto-advance setTimeout
            }

            // Brief delay to see the highlighted grid, then auto-advance
            setTimeout(() => {
                if (this.isActive) this.loadNextProblem();
            }, 1500);
        } else {
            this.wrongAnswers++;
            this.currentStreak = 0;
            this.updateStats();

            if (this.intervention.isActive) {
                const check = this.intervention.afterAnswer(tags, isCorrect, timeMs);
                if (check.mastered) return;
            }

            // Show explanation with NEXT button — grid stays highlighted
            this.showExplanation(
                `\u2717 ${Math.round(iou * 100)}% match (need 70%)`,
                'Green = correct range. Red = your wrong picks.\nStudy the highlighted grid, then press NEXT.'
            );
        }
    }

    // ── UI Helpers ─────────────────────────────────────

    updateStats() {
        if (this.correctDisplay) this.correctDisplay.textContent = this.correctAnswers;
        if (this.wrongDisplay) this.wrongDisplay.textContent = this.wrongAnswers;
        if (this.streakDisplay) this.streakDisplay.textContent = this.currentStreak;
    }

    showFeedback(message, color) {
        if (this.feedbackDisplay) {
            this.feedbackDisplay.textContent = message;
            this.feedbackDisplay.style.color = color;
            setTimeout(() => {
                if (this.feedbackDisplay) this.feedbackDisplay.textContent = '';
            }, 1500);
        }
    }

    endDrill() {
        this.isActive = false;
        window.gameActive = false;
        this.intervention.deactivate();

        if (this.elapsedInterval) {
            clearInterval(this.elapsedInterval);
            this.elapsedInterval = null;
        }

        this.inputHandler.disable();
        this.hideExplanation();

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

        screenManager.showScreen('screen-results');

        // Reset game screen for next time
        if (this.startGameBtn) this.startGameBtn.style.display = 'block';
        if (this.equationDisplay) this.equationDisplay.textContent = 'PRESS START';
        this.hideAllAreas();
    }
}

// Initialize when DOM is ready
let pokerDrill;
document.addEventListener('DOMContentLoaded', () => {
    pokerDrill = new PokerDrill();
});
