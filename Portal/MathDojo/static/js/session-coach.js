/**
 * SessionCoach - Tracks per-tag performance for the custom arithmetic drill.
 * Performs dual-layer analysis (recent 10 + full session) every 10 problems.
 * Outputs focus_tags for the next batch request.
 */
class SessionCoach {
    constructor() {
        this.history = [];
        this.focusTags = [];
        this.analysisInterval = 10;
        this.onIntervention = null;  // callback: (tag, priorityScore) => void
    }

    /**
     * Reset coach for a new drill session.
     */
    reset() {
        this.history = [];
        this.focusTags = [];
    }

    /**
     * Record a completed problem.
     * @param {string[]} tags - Tags from the problem object
     * @param {boolean} correct - Whether user answered correctly
     * @param {number} timeMs - Time to answer in milliseconds
     */
    record(tags, correct, timeMs) {
        this.history.push({ tags, correct, timeMs });

        if (this.history.length % this.analysisInterval === 0) {
            this._analyze();
        }
    }

    /**
     * Get current focus tags for next batch request.
     * @returns {string[]} Array of up to 3 tag strings (possibly empty)
     */
    getFocusTags() {
        return this.focusTags;
    }

    /**
     * Dual-layer analysis: recent window + full session.
     * Updates this.focusTags.
     */
    _analyze() {
        const recent = this.history.slice(-this.analysisInterval);
        const session = this.history;

        const recentStats = this._computeTagStats(recent);
        const sessionStats = this._computeTagStats(session);

        // Log summary
        const recentCorrect = recent.filter(r => r.correct).length;
        const recentAvgTime = recent.reduce((s, r) => s + r.timeMs, 0) / recent.length;
        const sessionCorrect = session.filter(r => r.correct).length;

        console.log(`[Coach] Analysis at problem ${this.history.length}:`);
        console.log(`[Coach]   Recent (last ${this.analysisInterval}): ${recentCorrect}/${recent.length} correct, avg ${(recentAvgTime / 1000).toFixed(1)}s`);
        console.log(`[Coach]   Session (all ${session.length}): ${sessionCorrect}/${session.length} correct`);

        // Apply decision rules (returns full sorted [[tag, score], ...])
        const ranked = this._applyRules(recentStats, sessionStats);
        this.focusTags = ranked.slice(0, 3).map(([tag]) => tag);

        if (this.focusTags.length > 0) {
            console.log(`[Coach]   Focus tags: ${JSON.stringify(this.focusTags)}`);
        } else {
            console.log(`[Coach]   No weaknesses detected - standard problems`);
        }

        // Trigger intervention if a tag hits crisis level (priority >= 4)
        if (this.onIntervention && ranked.length > 0 && ranked[0][1] >= 4) {
            this.onIntervention(ranked[0][0], ranked[0][1]);
        }
    }

    /**
     * Compute per-tag stats from an array of records.
     * @param {Array} records - Array of {tags, correct, timeMs}
     * @returns {Map<string, {attempts, errors, errorRate, avgTimeMs}>}
     */
    _computeTagStats(records) {
        const stats = new Map();

        for (const rec of records) {
            if (!rec.tags) continue;
            for (const tag of rec.tags) {
                if (!stats.has(tag)) {
                    stats.set(tag, { attempts: 0, errors: 0, totalTimeMs: 0 });
                }
                const s = stats.get(tag);
                s.attempts++;
                if (!rec.correct) s.errors++;
                s.totalTimeMs += rec.timeMs;
            }
        }

        for (const [, s] of stats) {
            s.errorRate = s.errors / s.attempts;
            s.avgTimeMs = s.totalTimeMs / s.attempts;
        }

        return stats;
    }

    /**
     * Apply decision rules to identify focus tags.
     * Returns full sorted array of [tag, priorityScore] pairs.
     *
     * R1 - Recent crisis: errorRate >= 0.5 in recent, attempts >= 2 (priority 4)
     * R2 - Persistent weakness: session errorRate >= 0.4, attempts >= 5 (priority 3)
     * R3 - Slow + error-prone: session avgTime in top 25% AND errorRate >= 0.3 (priority 2)
     * R4 - Regression: recent avgTime >= 1.5x session avgTime, session attempts >= 3 (priority 1)
     */
    _applyRules(recentStats, sessionStats) {
        const candidates = new Map();

        // R1: Recent accuracy crisis
        for (const [tag, s] of recentStats) {
            if (s.attempts >= 2 && s.errorRate >= 0.5) {
                candidates.set(tag, (candidates.get(tag) || 0) + 4);
            }
        }

        // R2: Persistent weakness
        for (const [tag, s] of sessionStats) {
            if (s.attempts >= 5 && s.errorRate >= 0.4) {
                candidates.set(tag, (candidates.get(tag) || 0) + 3);
            }
        }

        // R3: Slow + error-prone
        const allAvgTimes = [...sessionStats.values()].map(s => s.avgTimeMs);
        const p75 = this._percentile(allAvgTimes, 75);
        for (const [tag, s] of sessionStats) {
            if (s.avgTimeMs >= p75 && s.errorRate >= 0.3) {
                candidates.set(tag, (candidates.get(tag) || 0) + 2);
            }
        }

        // R4: Regression
        for (const [tag, recent] of recentStats) {
            const session = sessionStats.get(tag);
            if (session && session.attempts >= 3 && recent.avgTimeMs >= session.avgTimeMs * 1.5) {
                candidates.set(tag, (candidates.get(tag) || 0) + 1);
            }
        }

        // Sort by priority score, return full ranked list
        return [...candidates.entries()].sort((a, b) => b[1] - a[1]);
    }

    /**
     * Compute Nth percentile of an array.
     */
    _percentile(arr, n) {
        if (arr.length === 0) return 0;
        const sorted = [...arr].sort((a, b) => a - b);
        const idx = Math.ceil((n / 100) * sorted.length) - 1;
        return sorted[Math.max(0, idx)];
    }
}
