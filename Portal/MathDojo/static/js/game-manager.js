/**
 * GameManager - Core game state and API communication
 */
class GameManager {
    constructor() {
        this.apiBase = '';  // Empty string for same-origin requests
        this.currentProblem = null;
        this.nextProblem = null;
        this.problemStartTime = null;
        this.problemQueue = [];
    }

    /**
     * Fetch a single problem from API
     */
    async fetchProblem(elo) {
        try {
            const response = await fetch(`${this.apiBase}/api/problem?elo=${elo}`);
            if (!response.ok) throw new Error('API request failed');
            return await response.json();
        } catch (error) {
            console.error('Error fetching problem:', error);
            return this.generateFallbackProblem();
        }
    }

    /**
     * Fetch a batch of problems
     * @param {number} count - Number of problems
     * @param {number|object} valueOrOptions - Elo rating, difficulty score, or options object
     * @param {boolean} isDifficulty - If true, send as difficulty; otherwise as elo (ignored if options object)
     */
    async fetchBatch(count, valueOrOptions, isDifficulty = false) {
        try {
            let body;
            if (typeof valueOrOptions === 'object' && valueOrOptions !== null) {
                body = { count, options: valueOrOptions };
            } else if (isDifficulty) {
                body = { count, difficulty: valueOrOptions };
            } else {
                body = { count, elo: valueOrOptions };
            }

            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            });

            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            return data.problems;
        } catch (error) {
            console.error('Error fetching batch:', error);
            const problems = [];
            for (let i = 0; i < count; i++) {
                problems.push(this.generateFallbackProblem());
            }
            return problems;
        }
    }

    /**
     * Generate a simple fallback problem when API is unavailable
     */
    generateFallbackProblem() {
        const a = Math.floor(Math.random() * 10) + 1;
        const b = Math.floor(Math.random() * 10) + 1;
        const ops = ['+', '-', '×'];
        const op = ops[Math.floor(Math.random() * ops.length)];

        let answer;
        let equation;

        if (op === '+') {
            answer = a + b;
            equation = `${a} + ${b}`;
        } else if (op === '-') {
            const max = Math.max(a, b);
            const min = Math.min(a, b);
            answer = max - min;
            equation = `${max} - ${min}`;
        } else {
            answer = a * b;
            equation = `${a} × ${b}`;
        }

        return {
            id: Math.random().toString(36).substring(7),
            equation,
            answer,
            difficulty_rating: 10
        };
    }

    /**
     * Get next problem (with pre-fetching)
     */
    async getNextProblem(elo) {
        // Use pre-fetched problem if available
        if (this.nextProblem) {
            this.currentProblem = this.nextProblem;
            this.nextProblem = null;
        } else {
            this.currentProblem = await this.fetchProblem(elo);
        }

        // Pre-fetch next problem in background
        this.nextProblem = await this.fetchProblem(elo);

        this.problemStartTime = Date.now();
        return this.currentProblem;
    }

    /**
     * Check if answer is correct and calculate Elo change
     */
    checkAnswer(userAnswer) {
        if (!this.currentProblem) return null;

        const tolerance = this.currentProblem.tolerance || 0;
        const isCorrect = tolerance > 0
            ? Math.abs(userAnswer - this.currentProblem.answer) <= tolerance
            : userAnswer === this.currentProblem.answer;
        const timeElapsed = (Date.now() - this.problemStartTime) / 1000; // seconds

        let eloChange = 0;

        if (isCorrect) {
            if (timeElapsed < 2) {
                eloChange = 10;
            } else if (timeElapsed < 5) {
                eloChange = 5;
            } else {
                eloChange = 2;
            }
        } else {
            eloChange = -15;
        }

        return {
            correct: isCorrect,
            timeElapsed,
            eloChange,
            correctAnswer: this.currentProblem.answer
        };
    }

    /**
     * Calculate Elo change for Time Trial (faster progression)
     */
    checkAnswerTimeTrial(userAnswer, correctAnswersStreak) {
        if (!this.currentProblem) return null;

        const isCorrect = userAnswer === this.currentProblem.answer;
        const timeElapsed = (Date.now() - this.problemStartTime) / 1000;

        let eloChange = 0;

        if (isCorrect) {
            // Faster progression in time trial
            if (timeElapsed < 2) {
                eloChange = 15;
            } else if (timeElapsed < 5) {
                eloChange = 8;
            } else {
                eloChange = 3;
            }

            // Bonus for streaks
            if (correctAnswersStreak > 0 && correctAnswersStreak % 5 === 0) {
                eloChange += 5;
            }
        } else {
            eloChange = -10; // Less penalty in time trial
        }

        return {
            correct: isCorrect,
            timeElapsed,
            eloChange,
            correctAnswer: this.currentProblem.answer
        };
    }

    /**
     * Load problems into queue from batch (uses direct difficulty, not elo)
     */
    async loadProblemQueue(count, difficulty) {
        this.problemQueue = await this.fetchBatch(count, difficulty, true);
        return this.problemQueue.length;
    }

    /**
     * Load custom drill problems into queue
     * @param {number} count - Number of problems
     * @param {object} options - { operations, mix, min_digits, max_digits }
     * @param {string[]|null} focusTags - Optional weakness tags from SessionCoach
     */
    async loadCustomDrill(count, options, focusTags = null) {
        const problems = await this._fetchBatchCustom(count, options, focusTags);
        this.problemQueue = this.problemQueue.concat(problems);
        return this.problemQueue.length;
    }

    /**
     * Fetch custom drill batch with optional focus_tags for adaptive targeting.
     */
    async _fetchBatchCustom(count, options, focusTags = null) {
        try {
            const body = { count, options };
            if (focusTags && focusTags.length > 0) {
                body.focus_tags = focusTags;
            }
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            return data.problems;
        } catch (error) {
            console.error('Error fetching custom batch:', error);
            return Array.from({length: count}, () => this.generateFallbackProblem());
        }
    }

    /**
     * Load financial drill problems into queue
     * @param {number} count - Number of problems
     * @param {object} financialOptions - { categories, difficulty }
     */
    async loadFinancialDrill(count, financialOptions, focusTags = null) {
        try {
            const body = { count, financial_options: financialOptions };
            if (focusTags && focusTags.length > 0) {
                body.focus_tags = focusTags;
            }
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            this.problemQueue = this.problemQueue.concat(data.problems);
            return this.problemQueue.length;
        } catch (error) {
            console.error('Error fetching financial batch:', error);
            return this.problemQueue.length;
        }
    }

    /**
     * Load poker drill problems into queue
     * @param {number} count - Number of problems
     * @param {object} pokerOptions - { categories, difficulty }
     */
    async loadPokerDrill(count, pokerOptions, focusTags = null) {
        try {
            const body = { count, poker_options: pokerOptions };
            if (focusTags && focusTags.length > 0) {
                body.focus_tags = focusTags;
            }
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            this.problemQueue = this.problemQueue.concat(data.problems);
            return this.problemQueue.length;
        } catch (error) {
            console.error('Error fetching poker batch:', error);
            return this.problemQueue.length;
        }
    }

    /**
     * Fetch financial batch (returns array, does not append to queue)
     */
    async _fetchFinancialBatch(count, financialOptions, focusTags = null) {
        try {
            const body = { count, financial_options: financialOptions };
            if (focusTags && focusTags.length > 0) body.focus_tags = focusTags;
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            return data.problems;
        } catch (error) {
            console.error('Error fetching financial batch:', error);
            return [];
        }
    }

    /**
     * Fetch poker batch (returns array, does not append to queue)
     */
    async _fetchPokerBatch(count, pokerOptions, focusTags = null) {
        try {
            const body = { count, poker_options: pokerOptions };
            if (focusTags && focusTags.length > 0) body.focus_tags = focusTags;
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            return data.problems;
        } catch (error) {
            console.error('Error fetching poker batch:', error);
            return [];
        }
    }

    /**
     * Load a mixed batch from all problem types, proportioned by focus tags.
     * Fetches arithmetic, financial, and poker problems in parallel, then shuffles.
     */
    async loadMixedDrill(count, focusTags = null) {
        const FINANCIAL_PREFIXES = ['compound_interest', 'simple_interest', 'rule_of_72',
            'margin', 'return', 'liquidity', 'valuation', 'ggm',
            'perpetuity', 'npv', 'cagr', 'bonds', 'breakeven',
            'dcf', 'terminal', 'gordon', 'duration'];
        const POKER_PREFIXES = ['pot_odds', 'auto_profit', 'combos', 'equity', 'range'];

        let arithTags = [], finTags = [], pokerTags = [];
        if (focusTags && focusTags.length > 0) {
            for (const tag of focusTags) {
                if (FINANCIAL_PREFIXES.some(p => tag.startsWith(p) || tag === p)) {
                    finTags.push(tag);
                } else if (POKER_PREFIXES.some(p => tag.startsWith(p) || tag === p)) {
                    pokerTags.push(tag);
                } else {
                    arithTags.push(tag);
                }
            }
        }

        const total = arithTags.length + finTags.length + pokerTags.length;
        let arithCount, finCount, pokerCount;

        if (total > 0) {
            // Proportional split with minimum 5 per active category
            arithCount = arithTags.length > 0 ? Math.max(5, Math.round(count * arithTags.length / total)) : 0;
            finCount = finTags.length > 0 ? Math.max(5, Math.round(count * finTags.length / total)) : 0;
            pokerCount = pokerTags.length > 0 ? Math.max(5, Math.round(count * pokerTags.length / total)) : 0;
        } else {
            // No focus tags — equal split across all three
            arithCount = Math.round(count / 3);
            finCount = Math.round(count / 3);
            pokerCount = count - arithCount - finCount;
        }

        // Fetch from all generators in parallel
        const promises = [];
        if (arithCount > 0) {
            promises.push(this._fetchBatchCustom(arithCount, {
                operations: ['addition', 'subtraction', 'multiplication', 'division'],
                mix: false, min_digits: 1, max_digits: 3
            }, arithTags.length > 0 ? arithTags : null));
        }
        if (finCount > 0) {
            promises.push(this._fetchFinancialBatch(finCount, {
                categories: ['rules', 'interest', 'ratios', 'valuation', 'ggm', 'dcf', 'bonds', 'breakeven'],
                difficulty: 'normal'
            }, finTags.length > 0 ? finTags : null));
        }
        if (pokerCount > 0) {
            // Only numeric-answer poker categories (equity/range need special UI)
            promises.push(this._fetchPokerBatch(pokerCount, {
                categories: ['pot_odds', 'auto_profit', 'combinatorics'],
                difficulty: 'normal'
            }, pokerTags.length > 0 ? pokerTags : null));
        }

        const results = await Promise.all(promises);
        let allProblems = results.flat();

        // Fisher-Yates shuffle
        for (let i = allProblems.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [allProblems[i], allProblems[j]] = [allProblems[j], allProblems[i]];
        }

        this.problemQueue = this.problemQueue.concat(allProblems);
        return this.problemQueue.length;
    }

    /**
     * Get problem from queue
     */
    getFromQueue() {
        if (this.problemQueue.length === 0) return null;

        this.currentProblem = this.problemQueue.shift();
        this.problemStartTime = Date.now();
        return this.currentProblem;
    }
}

// Create global instance
const gameManager = new GameManager();
