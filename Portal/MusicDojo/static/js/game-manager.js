/**
 * GameManager - Handles API communication and exercise management
 */
class GameManager {
    constructor() {
        this.apiBase = ''; // Same-origin requests
        this.cache = {
            exercises: [],
            currentIndex: 0
        };
    }

    /**
     * Fetch a single exercise from API
     */
    async fetchExercise(mode, elo) {
        try {
            const response = await fetch(`${this.apiBase}/api/exercise?mode=${mode}&elo=${elo}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const exercise = await response.json();
            return exercise;
        } catch (error) {
            console.error('Error fetching exercise:', error);
            // Return fallback local exercise
            return this.generateLocalExercise(mode, this.eloToDifficulty(elo));
        }
    }

    /**
     * Fetch a batch of exercises from API
     */
    async fetchBatch(mode, count, elo, options = {}) {
        try {
            const response = await fetch(`${this.apiBase}/api/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode,
                    count,
                    elo,
                    options
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.exercises;
        } catch (error) {
            console.error('Error fetching batch:', error);
            // Return fallback local exercises
            const exercises = [];
            const difficulty = this.eloToDifficulty(elo);
            for (let i = 0; i < count; i++) {
                exercises.push(this.generateLocalExercise(mode, difficulty));
            }
            return exercises;
        }
    }

    /**
     * Get next exercise (with pre-fetching)
     */
    async getNextExercise(mode, elo) {
        // If cache is empty or low, fetch more
        if (this.cache.currentIndex >= this.cache.exercises.length - 2) {
            const newExercises = await this.fetchBatch(mode, 10, elo);
            this.cache.exercises = this.cache.exercises.concat(newExercises);
        }

        // Return next exercise from cache
        if (this.cache.currentIndex < this.cache.exercises.length) {
            const exercise = this.cache.exercises[this.cache.currentIndex];
            this.cache.currentIndex++;
            return exercise;
        }

        // Fallback: fetch single exercise
        return await this.fetchExercise(mode, elo);
    }

    /**
     * Reset exercise cache
     */
    resetCache() {
        this.cache = {
            exercises: [],
            currentIndex: 0
        };
    }

    /**
     * Get scale information from API
     */
    async getScaleInfo(key, scaleType) {
        try {
            const response = await fetch(`${this.apiBase}/api/scale-info?key=${key}&scale_type=${scaleType}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const info = await response.json();
            return info;
        } catch (error) {
            console.error('Error fetching scale info:', error);
            return null;
        }
    }

    /**
     * Record exercise completion
     */
    recordCompletion(mode, success, timeMs, stats = {}) {
        const elo = storageManager.load('user_elo');
        const difficulty = this.eloToDifficulty(elo);

        // Calculate Elo change
        const eloChange = this.calculateEloChange(timeMs, difficulty, success);

        // Update Elo
        const newElo = storageManager.updateElo(eloChange);

        // Update mode progress
        const progress = storageManager.load('mode_progress')[mode] || {};
        const sessions = (progress.sessions || 0) + 1;

        const updates = {
            sessions,
            ...stats
        };

        storageManager.updateModeProgress(mode, updates);

        return { eloChange, newElo };
    }

    /**
     * Calculate Elo change based on performance
     */
    calculateEloChange(timeMs, difficulty, success) {
        if (!success) {
            return -10; // Wrong answer
        }

        // Base gain on difficulty
        const baseGain = 5 + difficulty;

        // Time bonus (faster = more points)
        const targetTime = 5000; // 5 seconds target
        let timeFactor = 1.0;

        if (timeMs < targetTime) {
            timeFactor = 1.5; // Fast answer bonus
        } else if (timeMs > targetTime * 2) {
            timeFactor = 0.8; // Slow answer penalty
        }

        return Math.round(baseGain * timeFactor);
    }

    /**
     * Convert Elo to difficulty (1-10)
     */
    eloToDifficulty(elo) {
        if (elo < 800) return Math.max(1, Math.floor(1 + (elo - 600) / 100));
        if (elo < 1000) return 3 + Math.floor((elo - 800) / 100);
        if (elo < 1200) return 5 + Math.floor((elo - 1000) / 100);
        if (elo < 1400) return 7 + Math.floor((elo - 1200) / 100);
        return Math.min(10, 9 + Math.floor((elo - 1400) / 100));
    }

    /**
     * Generate a local exercise (fallback if API fails)
     */
    generateLocalExercise(mode, difficulty) {
        // Simple fallback exercises
        const id = 'local_' + Math.random().toString(36).substr(2, 9);

        switch (mode) {
            case 'direction':
                return {
                    id,
                    mode: 'direction',
                    difficulty,
                    tempo: 60 + difficulty * 10,
                    motion_type: 'similar',
                    note_range: 8
                };

            case 'ear_training':
                const intervals = ['Perfect 5th', 'Major 3rd', 'Perfect 4th'];
                return {
                    id,
                    mode: 'ear_training',
                    exercise_type: 'interval',
                    difficulty,
                    interval_name: intervals[Math.floor(Math.random() * intervals.length)],
                    choices: intervals,
                };

            case 'rhythm_dictation':
                return {
                    id,
                    mode: 'rhythm_dictation',
                    difficulty,
                    tempo: 100,
                    pattern: [1.0, 1.0, 1.0, 1.0],
                    choices: [[1.0, 1.0, 1.0, 1.0]],
                };

            case 'sight_reading':
                return {
                    id,
                    mode: 'sight_reading',
                    difficulty,
                    instrument: 'piano',
                    time_signature: [4, 4],
                    key_signature: 'C',
                    scale_name: 'C Major',
                    tempo: 80,
                    staves: 1,
                    measures: [{
                        clef: 'treble',
                        notes: [
                            { keys: ['c/4'], duration: 'w', midi: [60], is_rest: false, dots: 0, accidentals: [] }
                        ]
                    }],
                    bass_measures: []
                };

            default:
                return {
                    id,
                    mode,
                    difficulty,
                    tempo: 100
                };
        }
    }
}

// Create singleton instance
const gameManager = new GameManager();
