/**
 * ProfileManager - Handles profile selection, result buffering, and focus tag fetching.
 * For Guest mode, all recording/fetching is no-ops.
 */
class ProfileManager {
    constructor() {
        this.activeProfile = null; // 'james' or 'guest'
        this.resultBuffer = [];
        this.sessionStart = null;
        this.sessionMode = null;
        this.sessionCorrect = 0;
        this.sessionAttempted = 0;
        this.cachedFocusTags = null;
        this.cachedFocusMode = null;
    }

    /**
     * Set the active profile.
     */
    selectProfile(name) {
        this.activeProfile = name.toLowerCase();
        window.activeProfile = this.activeProfile;
    }

    isTracking() {
        return this.activeProfile && this.activeProfile !== 'guest';
    }

    /**
     * Start a new session (call when entering a game mode).
     */
    startSession(mode) {
        this.sessionStart = Date.now();
        this.sessionMode = mode;
        this.sessionCorrect = 0;
        this.sessionAttempted = 0;
        this.resultBuffer = [];
    }

    /**
     * Record a single problem result. Buffered until flush.
     */
    recordResult(tags, correct, timeMs) {
        if (!this.isTracking()) return;

        this.resultBuffer.push({
            tags: tags || [],
            correct: correct,
            time_ms: Math.round(timeMs)
        });
        this.sessionAttempted++;
        if (correct) this.sessionCorrect++;

        // Auto-flush every 20 problems for long drills
        if (this.resultBuffer.length >= 20) {
            this.flushResults();
        }
    }

    /**
     * Flush buffered results to the server (without ending session).
     */
    async flushResults() {
        if (!this.isTracking() || this.resultBuffer.length === 0) return;

        const results = [...this.resultBuffer];
        this.resultBuffer = [];

        try {
            await fetch(`/api/profile/${this.activeProfile}/record`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results })
            });
        } catch (e) {
            console.error('Failed to flush results:', e);
            // Re-add to buffer on failure
            this.resultBuffer = results.concat(this.resultBuffer);
        }
    }

    /**
     * End session: flush remaining results + session summary.
     */
    async endSession() {
        if (!this.isTracking()) return;

        const durationS = Math.round((Date.now() - this.sessionStart) / 1000);
        const session = {
            mode: this.sessionMode,
            duration_s: durationS,
            problems_attempted: this.sessionAttempted,
            correct: this.sessionCorrect
        };

        const results = [...this.resultBuffer];
        this.resultBuffer = [];

        try {
            await fetch(`/api/profile/${this.activeProfile}/record`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results, session })
            });
        } catch (e) {
            console.error('Failed to end session:', e);
        }

        this.cachedFocusTags = null;
        this.cachedFocusMode = null;
    }

    /**
     * Get focus tags from prediction engine.
     * Caches per mode within a session.
     */
    async getFocusTags(mode) {
        if (!this.isTracking()) return null;

        // Use cache if same mode
        if (this.cachedFocusTags && this.cachedFocusMode === mode) {
            return this.cachedFocusTags;
        }

        try {
            const modeParam = mode ? `?mode=${mode}` : '';
            const response = await fetch(`/api/profile/${this.activeProfile}/focus-tags${modeParam}`);
            if (!response.ok) return null;
            const data = await response.json();
            this.cachedFocusTags = data.focus_tags;
            this.cachedFocusMode = mode;
            return data.focus_tags;
        } catch (e) {
            console.error('Failed to get focus tags:', e);
            return null;
        }
    }

    /**
     * Invalidate cached focus tags (call after significant practice).
     */
    invalidateCache() {
        this.cachedFocusTags = null;
        this.cachedFocusMode = null;
    }
}

// Global instance
const profileManager = new ProfileManager();
