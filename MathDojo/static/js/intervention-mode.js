/**
 * InterventionMode - Focused practice when a severe weakness is detected.
 * Activates via SessionCoach callback, tracks mastery progress, exits when
 * dual validation passes (short-term + long-term accuracy thresholds).
 */
class InterventionMode {
    constructor(progressContainerId = 'intervention-progress') {
        this.isActive = false;
        this.targetTag = null;
        this.history = [];  // [{correct, timeMs}] — only target-tag problems

        // Exit thresholds
        this.minAttempts = 10;
        this.longTermTarget = 0.70;
        this.shortTermTarget = 0.80;
        this.recentWindow = 10;

        // Callback set by CustomDrill — called when mastery modal is dismissed
        this.onMasteryDismissed = null;

        // DOM refs
        this.progressContainer = document.getElementById(progressContainerId);
    }

    // Tag label map for UI display
    static TAG_LABELS = {
        // Arithmetic tags
        'carry:once': 'SINGLE CARRY', 'carry:multi': 'MULTI CARRY',
        'carry:none': 'NO CARRY',
        'trap:7x8': '7 x 8 TRAP', 'trap:6x7': '6 x 7 TRAP',
        'trap:8x9': '8 x 9 TRAP', 'trap:6x9': '6 x 9 TRAP',
        'bridge:tens': 'TENS BRIDGE', 'bridge:hundreds': 'HUNDREDS BRIDGE',
        'near:round': 'NEAR ROUND', 'borrow:across-zero': 'BORROW ACROSS ZERO',
        'table:easy': 'EASY TABLES', 'table:mid': 'MID TABLES (6-9)', 'table:hard': 'HARD TABLES',
        'div:large': 'LARGE DIVISION',
        'op:add': 'ADDITION', 'op:sub': 'SUBTRACTION',
        'op:mul': 'MULTIPLICATION', 'op:div': 'DIVISION',
        'scale:1x1': '1-DIGIT', 'scale:1x2': '1x2 DIGIT', 'scale:2x1': '2x1 DIGIT',
        'scale:2x2': '2-DIGIT x 2-DIGIT', 'scale:2x3': '2x3 DIGIT',
        'scale:3x2': '3x2 DIGIT', 'scale:3x3': '3-DIGIT x 3-DIGIT',
        'scale:big': 'BIG NUMBERS',
        // Financial category tags
        'rules': 'RULES OF THUMB', 'interest': 'INTEREST',
        'ratios': 'RATIOS', 'valuation': 'VALUATION',
        'ggm': 'GORDON GROWTH', 'dcf': 'DCF',
        'bonds': 'BONDS', 'breakeven': 'BREAK-EVEN',
        // Financial type tags
        'rule_of_72': 'RULE OF 72', 'rule_of_114': 'RULE OF 114',
        'rule_of_144': 'RULE OF 144',
        'simple_interest': 'SIMPLE INTEREST', 'compound_interest': 'COMPOUND INTEREST',
        'margin': 'MARGINS', 'return_ratio': 'ROE / ROA',
        'liquidity_ratio': 'LIQUIDITY RATIOS',
        'earnings_yield': 'EARNINGS YIELD', 'peg_ratio': 'PEG RATIO',
        'rule_of_20': 'RULE OF 20', 'ev_ebitda': 'EV / EBITDA',
        'gordon_growth': 'GGM FAIR PRICE', 'perpetuity': 'PERPETUITY',
        'terminal_value': 'TERMINAL VALUE', 'pv_single': 'PRESENT VALUE',
        'cagr': 'CAGR',
        'duration_impact': 'DURATION IMPACT', 'bond_yield': 'BOND YIELD',
        // Poker category tags
        'pot_odds': 'POT ODDS', 'auto_profit': 'AUTO PROFIT',
        'combinatorics': 'COMBINATORICS', 'equity': 'EQUITY',
        'range': 'RANGE PAINTER',
        // Poker equity scenario type tags
        'flush_draw': 'FLUSH DRAW', 'open_ended_straight_draw': 'OPEN-ENDED STRAIGHT',
        'gutshot': 'GUTSHOT', 'overcards': 'OVERCARDS',
        'combo_draw': 'COMBO DRAW', 'two_pair_draw': 'TWO PAIR DRAW',
    };

    /**
     * Get human-readable label for a tag.
     */
    getTagLabel(tag) {
        return InterventionMode.TAG_LABELS[tag] || tag.toUpperCase().replace(':', ': ');
    }

    /**
     * Activate intervention for a specific tag.
     */
    activate(tag) {
        this.isActive = true;
        this.targetTag = tag;
        this.history = [];

        console.log(`[Intervention] ACTIVATED for tag: ${tag}`);
        this.showProgressBar();

        // Wire coach-modal OK button for mastery dismissal
        const okBtn = document.getElementById('coach-ok');
        if (okBtn) {
            okBtn.onclick = () => {
                document.getElementById('coach-modal').style.display = 'none';
                if (this.onMasteryDismissed) this.onMasteryDismissed();
            };
        }
    }

    /**
     * Deactivate intervention (user ended drill or mastery achieved).
     */
    deactivate() {
        if (this.isActive) {
            console.log(`[Intervention] DEACTIVATED — returning to normal mode`);
        }
        this.isActive = false;
        this.targetTag = null;
        this.history = [];
        this.hideProgressBar();
    }

    /**
     * Called after every answered problem.
     * Only records if the problem's tags include the target tag.
     * @returns {{mastered: boolean}}
     */
    afterAnswer(tags, correct, timeMs) {
        if (!this.isActive || !tags || !tags.includes(this.targetTag)) {
            return { mastered: false };
        }

        this.history.push({ correct, timeMs });
        this.updateProgressBar();

        // Check mastery
        const check = this.checkMastery();

        // Log progress
        const attempts = this.history.length;
        const overall = attempts > 0 ? Math.round((this.history.filter(h => h.correct).length / attempts) * 100) : 0;
        const recentSlice = this.history.slice(-this.recentWindow);
        const recentAcc = recentSlice.length > 0 ? Math.round((recentSlice.filter(h => h.correct).length / recentSlice.length) * 100) : 0;
        console.log(`[Intervention] Progress: ${attempts}/${this.minAttempts} attempts | Overall: ${overall}% | Recent: ${recentSlice.length >= this.recentWindow ? recentAcc + '%' : '--'}`);

        if (check.achieved) {
            this.completeMastery(check.stats);
            return { mastered: true };
        }

        console.log(`[Intervention] ${check.reason}`);
        return { mastered: false };
    }

    /**
     * Check if all 3 mastery criteria are met.
     */
    checkMastery() {
        const attempts = this.history.length;
        const correct = this.history.filter(h => h.correct).length;
        const accuracy = attempts > 0 ? correct / attempts : 0;

        // Criterion 1: Minimum attempts
        if (attempts < this.minAttempts) {
            return {
                achieved: false,
                reason: `Need ${this.minAttempts - attempts} more attempts`
            };
        }

        // Criterion 2: Long-term accuracy
        if (accuracy < this.longTermTarget) {
            return {
                achieved: false,
                reason: `Overall accuracy ${Math.round(accuracy * 100)}% < ${Math.round(this.longTermTarget * 100)}% target`
            };
        }

        // Criterion 3: Short-term accuracy (last N target-tag problems)
        const recentSlice = this.history.slice(-this.recentWindow);
        const recentCorrect = recentSlice.filter(h => h.correct).length;
        const recentAccuracy = recentSlice.length > 0 ? recentCorrect / recentSlice.length : 0;

        if (recentAccuracy < this.shortTermTarget) {
            return {
                achieved: false,
                reason: `Recent accuracy ${Math.round(recentAccuracy * 100)}% < ${Math.round(this.shortTermTarget * 100)}% target`
            };
        }

        return {
            achieved: true,
            reason: 'Mastery confirmed',
            stats: {
                longTermAccuracy: accuracy,
                shortTermAccuracy: recentAccuracy,
                totalAttempts: attempts
            }
        };
    }

    /**
     * Get focus tags for batch requests.
     * When active, overrides SessionCoach with single-tag targeting.
     * @returns {string[]|null} — null means "use SessionCoach instead"
     */
    getFocusTags() {
        if (this.isActive && this.targetTag) {
            return [this.targetTag];
        }
        return null;
    }

    /**
     * Show the progress bar in #intervention-progress.
     */
    showProgressBar() {
        if (!this.progressContainer) return;

        const label = this.getTagLabel(this.targetTag);
        this.progressContainer.innerHTML = `
            <div class="intervention-bar">
                <div class="intervention-header">
                    <span class="intervention-label">WEAKNESS: ${label}</span>
                </div>
                <div class="intervention-metrics">
                    <span>Practice: <b id="iv-attempts">0</b>/${this.minAttempts}</span>
                    <span>Overall: <b id="iv-long">--</b>/${Math.round(this.longTermTarget * 100)}%</span>
                    <span>Recent: <b id="iv-short">--</b>/${Math.round(this.shortTermTarget * 100)}%</span>
                </div>
                <div class="intervention-fill-track">
                    <div class="intervention-fill" id="iv-fill" style="width:0%"></div>
                </div>
            </div>
        `;
        this.progressContainer.style.display = 'block';
    }

    /**
     * Update progress bar metrics and fill.
     */
    updateProgressBar() {
        const attempts = this.history.length;
        const correct = this.history.filter(h => h.correct).length;
        const accuracy = attempts > 0 ? correct / attempts : 0;

        const recentSlice = this.history.slice(-this.recentWindow);
        const recentCorrect = recentSlice.filter(h => h.correct).length;
        const recentAccuracy = recentSlice.length > 0 ? recentCorrect / recentSlice.length : 0;

        const elAttempts = document.getElementById('iv-attempts');
        const elLong = document.getElementById('iv-long');
        const elShort = document.getElementById('iv-short');
        const elFill = document.getElementById('iv-fill');

        if (elAttempts) elAttempts.textContent = attempts;
        if (elLong) elLong.textContent = Math.round(accuracy * 100) + '%';
        if (elShort) elShort.textContent = attempts >= this.recentWindow
            ? Math.round(recentAccuracy * 100) + '%' : '--';

        // Weighted progress: 25% attempts, 35% long-term, 40% short-term
        const pAttempts = Math.min(1, attempts / this.minAttempts);
        const pLong = Math.min(1, accuracy / this.longTermTarget);
        const pShort = attempts >= this.recentWindow
            ? Math.min(1, recentAccuracy / this.shortTermTarget) : 0;
        const overall = (pAttempts * 0.25 + pLong * 0.35 + pShort * 0.40) * 100;

        if (elFill) elFill.style.width = Math.round(overall) + '%';
    }

    /**
     * Hide progress bar.
     */
    hideProgressBar() {
        if (!this.progressContainer) return;
        this.progressContainer.style.display = 'none';
        this.progressContainer.innerHTML = '';
    }

    /**
     * Complete mastery — log, show modal, deactivate.
     */
    completeMastery(stats) {
        console.log(`[Intervention] MASTERY ACHIEVED: ${this.targetTag}`);
        console.log(`[Intervention]   Long-term: ${Math.round(stats.longTermAccuracy * 100)}% (target ${Math.round(this.longTermTarget * 100)}%)`);
        console.log(`[Intervention]   Short-term: ${Math.round(stats.shortTermAccuracy * 100)}% (target ${Math.round(this.shortTermTarget * 100)}%)`);
        console.log(`[Intervention]   Total problems: ${stats.totalAttempts}`);

        this.hideProgressBar();
        this.showMasteryModal(stats);
        this.isActive = false;
    }

    /**
     * Show mastery summary in #coach-modal.
     */
    showMasteryModal(stats) {
        const label = this.getTagLabel(this.targetTag);
        const longPct = Math.round(stats.longTermAccuracy * 100);
        const shortPct = Math.round(stats.shortTermAccuracy * 100);

        const titleEl = document.querySelector('#coach-modal .modal-title');
        if (titleEl) titleEl.textContent = 'SKILL MASTERED';

        const msg = `
            <div style="font-size:1rem; color:var(--neon-green); margin-bottom:20px;">
                ${label}
            </div>
            <div style="font-size:0.85rem; line-height:2;">
                Recent: ${shortPct}% (target ${Math.round(this.shortTermTarget * 100)}%)<br>
                Overall: ${longPct}% (target ${Math.round(this.longTermTarget * 100)}%)<br>
                Problems: ${stats.totalAttempts}
            </div>
        `;

        document.getElementById('coach-message').innerHTML = msg;
        document.getElementById('coach-modal').style.display = 'flex';
    }
}
