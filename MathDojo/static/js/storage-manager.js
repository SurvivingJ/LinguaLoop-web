/**
 * StorageManager - Handles all localStorage operations
 */
class StorageManager {
    constructor() {
        this.STORAGE_KEY = 'retromind_data';
        this.initializeStorage();
    }

    /**
     * Get default storage structure
     */
    getDefaults() {
        return {
            user_elo: 1000,
            daily_streak: {
                last_played: this.getTodayDate(),
                count: 0
            },
            high_scores: {
                time_trial: 0,
                space_defense: 0
            },
            daily_progress: {
                current_level: 1,
                levels_today: 0,
                last_advance_date: '',
                completed_levels: []
            },
            settings: {
                sound: true,
                difficulty_offset: 0,
                theme: 'neon-arcade'
            }
        };
    }

    /**
     * Initialize storage with defaults if empty
     */
    initializeStorage() {
        const existing = this.loadAll();
        if (!existing) {
            this.saveAll(this.getDefaults());
        }
    }

    /**
     * Load all data from localStorage
     */
    loadAll() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Error loading from localStorage:', e);
            return null;
        }
    }

    /**
     * Save all data to localStorage
     */
    saveAll(data) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
            return true;
        } catch (e) {
            console.error('Error saving to localStorage:', e);
            return false;
        }
    }

    /**
     * Load specific value by key
     */
    load(key) {
        const data = this.loadAll() || this.getDefaults();
        return data[key];
    }

    /**
     * Save specific value by key
     */
    save(key, value) {
        const data = this.loadAll() || this.getDefaults();
        data[key] = value;
        return this.saveAll(data);
    }

    /**
     * Update Elo rating
     */
    updateElo(change) {
        const currentElo = this.load('user_elo');
        const newElo = Math.max(800, currentElo + change); // Minimum 800
        this.save('user_elo', newElo);
        return newElo;
    }

    /**
     * Update high score for a mode
     */
    updateHighScore(mode, score) {
        const highScores = this.load('high_scores');
        const isNewHighScore = score > highScores[mode];

        if (isNewHighScore) {
            highScores[mode] = score;
            this.save('high_scores', highScores);
        }

        return isNewHighScore;
    }

    /**
     * Update daily streak
     */
    updateStreak() {
        const streak = this.load('daily_streak');
        const today = this.getTodayDate();
        const lastPlayed = streak.last_played;

        // Check if played today already
        if (lastPlayed === today) {
            return streak.count;
        }

        // Check if streak continues (yesterday)
        const yesterday = this.getYesterdayDate();
        if (lastPlayed === yesterday) {
            streak.count += 1;
        } else {
            // Streak broken, reset
            streak.count = 1;
        }

        streak.last_played = today;
        this.save('daily_streak', streak);
        return streak.count;
    }

    /**
     * Reset all progress
     */
    resetAll() {
        this.saveAll(this.getDefaults());
    }

    /**
     * Get today's date as YYYY-MM-DD
     */
    getTodayDate() {
        return new Date().toISOString().split('T')[0];
    }

    /**
     * Get yesterday's date as YYYY-MM-DD
     */
    getYesterdayDate() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        return yesterday.toISOString().split('T')[0];
    }

    /**
     * Check if daily limit reached
     */
    canAdvanceLevel() {
        const progress = this.load('daily_progress');
        const today = this.getTodayDate();

        // Reset daily counter if new day
        if (progress.last_advance_date !== today) {
            progress.levels_today = 0;
            progress.last_advance_date = today;
            this.save('daily_progress', progress);
        }

        return progress.levels_today < 3;
    }

    /**
     * Increment daily level counter
     */
    incrementDailyLevels() {
        const progress = this.load('daily_progress');
        progress.levels_today += 1;
        this.save('daily_progress', progress);
    }

    /**
     * Mark level as completed
     */
    completeLevel(level) {
        const progress = this.load('daily_progress');

        if (!progress.completed_levels.includes(level)) {
            progress.completed_levels.push(level);
        }

        // Unlock next level
        if (level >= progress.current_level) {
            progress.current_level = level + 1;
        }

        this.save('daily_progress', progress);
    }
}

// Create global instance
const storageManager = new StorageManager();
