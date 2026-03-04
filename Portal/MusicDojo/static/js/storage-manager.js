/**
 * StorageManager - Handles localStorage for MusicDojo
 */
class StorageManager {
    constructor() {
        this.STORAGE_KEY = 'musicdojo_data';
        this.defaultData = {
            user_elo: 1000,
            daily_streak: {
                last_played: null,
                count: 0
            },
            high_scores: {
                direction_trainer: 0,
                polyrhythm_mastery: 0,
                tempo_ramp_max: 60,
                ear_training_streak: 0,
                rhythm_dictation_accuracy: 0,
                sight_reading_streak: 0
            },
            settings: {
                sound_enabled: true,
                theme: 'NEON_PULSE',
                metronome_sound: 'sine',
                master_volume: 0.5
            },
            mode_progress: {
                direction_trainer: { sessions: 0, avg_accuracy: 0, total_time: 0 },
                split_metronome: { sessions: 0, total_time: 0 },
                polyrhythm: { sessions: 0, ratios_mastered: [], total_time: 0 },
                swing: { sessions: 0, swing_styles_practiced: [], total_time: 0 },
                tempo_ramp: { sessions: 0, max_tempo_reached: 60, total_time: 0 },
                improv: { sessions: 0, scales_practiced: [], patterns_practiced: [], total_time: 0 },
                ghost: { sessions: 0, total_time: 0 },
                ear_training: { sessions: 0, correct: 0, total: 0, total_time: 0 },
                rhythm_dictation: { sessions: 0, correct: 0, total: 0, total_time: 0 },
                metronome: { sessions: 0, total_time: 0 },
                sight_reading: {
                    sessions: 0, exercises_completed: 0, correct: 0, total: 0, total_time: 0,
                    preferences: {
                        instrument: 'piano',
                        guitar_tone: 'acoustic',
                        scales: ['random'],
                        tempo: null,
                        note_types: ['random'],
                        measures: 4
                    }
                }
            },
            achievements: [],
            practice_log: [],
            guitar_exercises: {
                practice_logs: [],  // Last 100 guitar practice sessions
                progress_snapshots: {},  // Current state per exercise (keyed by exercise_id)
                category_stats: {
                    chromatic: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    scales: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    legato: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    trills: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    alternate_picking: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    economy_sweep: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    string_skipping: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    bending_vibrato: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    chord_transitions: { sessions: 0, total_time: 0, avg_bpm: 0 },
                    palm_muting: { sessions: 0, total_time: 0, avg_bpm: 0 }
                },
                milestones: [],  // Achievement badges (IDs)
                practice_streak: {
                    last_practiced: null,
                    count: 0
                },
                session_structure_preference: {
                    warmup_duration: 5,  // minutes
                    technique_focus_duration: 20,
                    musical_application_duration: 15,
                    cooldown_duration: 5
                }
            }
        };
    }

    /**
     * Load all data from localStorage
     */
    loadAll() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (!data) {
                // First time user - initialize with defaults silently
                this.saveAll(this.defaultData);
                return JSON.parse(JSON.stringify(this.defaultData));
            }
            const parsed = JSON.parse(data);
            // Merge with defaults to handle new fields
            return this._mergeWithDefaults(parsed);
        } catch (e) {
            console.error('Error loading storage:', e);
            this.saveAll(this.defaultData);
            return JSON.parse(JSON.stringify(this.defaultData));
        }
    }

    /**
     * Merge loaded data with default data (handles new fields)
     */
    _mergeWithDefaults(loaded) {
        const merged = JSON.parse(JSON.stringify(this.defaultData));

        for (const key in loaded) {
            if (typeof loaded[key] === 'object' && !Array.isArray(loaded[key])) {
                merged[key] = { ...merged[key], ...loaded[key] };
            } else {
                merged[key] = loaded[key];
            }
        }

        return merged;
    }

    /**
     * Save all data to localStorage
     */
    saveAll(data) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error('Error saving storage:', e);
        }
    }

    /**
     * Load a specific value
     */
    load(key) {
        const data = this.loadAll();
        return data[key];
    }

    /**
     * Save a specific value
     */
    save(key, value) {
        const data = this.loadAll();
        data[key] = value;
        this.saveAll(data);
    }

    /**
     * Update user Elo rating
     */
    updateElo(change) {
        const data = this.loadAll();
        data.user_elo = Math.max(400, data.user_elo + change);
        this.saveAll(data);
        return data.user_elo;
    }

    /**
     * Update high score for a specific mode
     */
    updateHighScore(mode, score) {
        const data = this.loadAll();
        if (!data.high_scores[mode] || score > data.high_scores[mode]) {
            data.high_scores[mode] = score;
            this.saveAll(data);
            return true; // New high score
        }
        return false;
    }

    /**
     * Update daily streak
     */
    updateStreak() {
        const data = this.loadAll();
        const today = new Date().toDateString();
        const lastPlayed = data.daily_streak.last_played;

        if (lastPlayed === today) {
            // Already played today
            return data.daily_streak.count;
        }

        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toDateString();

        if (lastPlayed === yesterdayStr) {
            // Consecutive day - increment streak
            data.daily_streak.count++;
        } else if (lastPlayed) {
            // Streak broken - reset
            data.daily_streak.count = 1;
        } else {
            // First time playing
            data.daily_streak.count = 1;
        }

        data.daily_streak.last_played = today;
        this.saveAll(data);
        return data.daily_streak.count;
    }

    /**
     * Update mode progress
     */
    updateModeProgress(mode, updates) {
        const data = this.loadAll();
        if (!data.mode_progress[mode]) {
            data.mode_progress[mode] = {};
        }

        data.mode_progress[mode] = {
            ...data.mode_progress[mode],
            ...updates
        };

        this.saveAll(data);
    }

    /**
     * Add achievement
     */
    addAchievement(achievementId) {
        const data = this.loadAll();
        if (!data.achievements.includes(achievementId)) {
            data.achievements.push(achievementId);
            this.saveAll(data);
            return true; // New achievement
        }
        return false;
    }

    /**
     * Log practice session
     */
    logPracticeSession(mode, durationSeconds, stats = {}) {
        const data = this.loadAll();
        const entry = {
            mode,
            date: new Date().toISOString(),
            duration: durationSeconds,
            stats
        };

        data.practice_log.push(entry);

        // Keep only last 100 sessions
        if (data.practice_log.length > 100) {
            data.practice_log = data.practice_log.slice(-100);
        }

        this.saveAll(data);
    }

    /**
     * Get total practice time for a mode
     */
    getTotalPracticeTime(mode = null) {
        const data = this.loadAll();

        if (mode) {
            return data.mode_progress[mode]?.total_time || 0;
        }

        // Sum all modes
        let total = 0;
        for (const m in data.mode_progress) {
            total += data.mode_progress[m].total_time || 0;
        }
        return total;
    }

    /**
     * Reset all data (only called from settings screen)
     */
    resetAll() {
        if (confirm('Are you sure you want to reset ALL progress? This cannot be undone.')) {
            this.saveAll(JSON.parse(JSON.stringify(this.defaultData)));
            return true;
        }
        return false;
    }

    /**
     * Export data as JSON
     */
    exportData() {
        const data = this.loadAll();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `musicdojo_backup_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * Import data from JSON
     */
    importData(jsonString) {
        try {
            const data = JSON.parse(jsonString);
            this.saveAll(data);
            return true;
        } catch (e) {
            console.error('Error importing data:', e);
            return false;
        }
    }

    // ===== GUITAR EXERCISE METHODS =====

    /**
     * Log guitar practice session
     * @param {string} exerciseId - Exercise ID
     * @param {number} bpmAchieved - Max clean BPM achieved
     * @param {string} subdivision - Subdivision used (quarter/eighth/sixteenth/sextuplet)
     * @param {number} qualityRating - 1=easy, 2=focused, 3=hard
     * @param {string} accuracyTier - gold/silver/bronze
     * @param {number} durationSeconds - Session duration in seconds
     * @param {string} notes - Optional notes
     * @param {Object} exercise - Exercise object from API
     */
    logGuitarPractice(exerciseId, bpmAchieved, subdivision, qualityRating, accuracyTier, durationSeconds, notes = '', exercise = null) {
        const data = this.loadAll();

        // Create log entry
        const logEntry = {
            id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            exercise_id: exerciseId,
            date: new Date().toISOString(),
            bpm_achieved: bpmAchieved,
            subdivision: subdivision,
            quality_rating: qualityRating,
            accuracy_tier: accuracyTier,
            duration_seconds: durationSeconds,
            notes: notes
        };

        // Add to practice logs
        data.guitar_exercises.practice_logs.push(logEntry);

        // Keep only last 100 logs
        if (data.guitar_exercises.practice_logs.length > 100) {
            data.guitar_exercises.practice_logs = data.guitar_exercises.practice_logs.slice(-100);
        }

        // Update progress snapshot
        this._updateGuitarProgressSnapshot(data, exerciseId, bpmAchieved, subdivision, accuracyTier, exercise);

        // Update category stats
        if (exercise) {
            const category = exercise.category;
            if (data.guitar_exercises.category_stats[category]) {
                const stats = data.guitar_exercises.category_stats[category];
                stats.sessions++;
                stats.total_time += durationSeconds;

                // Update avg_bpm
                const totalBpm = stats.avg_bpm * (stats.sessions - 1) + bpmAchieved;
                stats.avg_bpm = Math.round(totalBpm / stats.sessions);
            }
        }

        // Update practice streak
        const today = new Date().toDateString();
        const lastPracticed = data.guitar_exercises.practice_streak.last_practiced;

        if (lastPracticed !== today) {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            const yesterdayStr = yesterday.toDateString();

            if (lastPracticed === yesterdayStr) {
                data.guitar_exercises.practice_streak.count++;
            } else if (lastPracticed) {
                data.guitar_exercises.practice_streak.count = 1;
            } else {
                data.guitar_exercises.practice_streak.count = 1;
            }

            data.guitar_exercises.practice_streak.last_practiced = today;
        }

        this.saveAll(data);

        // Check for milestones
        this.checkGuitarMilestones();

        return logEntry;
    }

    /**
     * Update progress snapshot for an exercise (internal method)
     */
    _updateGuitarProgressSnapshot(data, exerciseId, bpmAchieved, subdivision, accuracyTier, exercise) {
        let snapshot = data.guitar_exercises.progress_snapshots[exerciseId];

        if (!snapshot) {
            snapshot = {
                exercise_id: exerciseId,
                current_bpm_ceiling: bpmAchieved,
                current_subdivision: subdivision,
                best_bpm_all_time: bpmAchieved,
                sessions_at_current_level: 1,
                last_practiced: new Date().toISOString(),
                streak_days: 0,
                advancement_ready: false,
                last_three_sessions: []
            };
        } else {
            snapshot.current_bpm_ceiling = Math.max(snapshot.current_bpm_ceiling, bpmAchieved);
            snapshot.best_bpm_all_time = Math.max(snapshot.best_bpm_all_time, bpmAchieved);
            snapshot.last_practiced = new Date().toISOString();

            if (bpmAchieved === snapshot.current_bpm_ceiling && subdivision === snapshot.current_subdivision) {
                snapshot.sessions_at_current_level++;
            } else {
                snapshot.sessions_at_current_level = 1;
                snapshot.current_subdivision = subdivision;
            }
        }

        // Track last 3 sessions for advancement detection
        snapshot.last_three_sessions.push({
            date: new Date().toISOString(),
            bpm: bpmAchieved,
            accuracy: accuracyTier
        });

        if (snapshot.last_three_sessions.length > 3) {
            snapshot.last_three_sessions = snapshot.last_three_sessions.slice(-3);
        }

        // Check if ready to advance (last 3 sessions all Gold)
        if (snapshot.last_three_sessions.length === 3) {
            snapshot.advancement_ready = snapshot.last_three_sessions.every(s => s.accuracy === 'gold');

            if (snapshot.advancement_ready && exercise) {
                // Calculate next BPM (10% rule)
                snapshot.next_bpm = Math.ceil(snapshot.current_bpm_ceiling * 1.10);
            }
        }

        data.guitar_exercises.progress_snapshots[exerciseId] = snapshot;
    }

    /**
     * Get progress snapshot for an exercise
     */
    getGuitarProgress(exerciseId) {
        const data = this.loadAll();
        return data.guitar_exercises.progress_snapshots[exerciseId] || null;
    }

    /**
     * Get all progress snapshots
     */
    getAllGuitarProgress() {
        const data = this.loadAll();
        return data.guitar_exercises.progress_snapshots;
    }

    /**
     * Get practice logs for an exercise
     */
    getGuitarPracticeLogs(exerciseId = null) {
        const data = this.loadAll();

        if (exerciseId) {
            return data.guitar_exercises.practice_logs.filter(log => log.exercise_id === exerciseId);
        }

        return data.guitar_exercises.practice_logs;
    }

    /**
     * Get category statistics
     */
    getGuitarCategoryStats(category = null) {
        const data = this.loadAll();

        if (category) {
            return data.guitar_exercises.category_stats[category] || null;
        }

        return data.guitar_exercises.category_stats;
    }

    /**
     * Check and award guitar milestones
     */
    checkGuitarMilestones() {
        const data = this.loadAll();
        const logs = data.guitar_exercises.practice_logs;
        const snapshots = data.guitar_exercises.progress_snapshots;
        const categoryStats = data.guitar_exercises.category_stats;
        const streak = data.guitar_exercises.practice_streak.count;
        let newMilestones = [];

        // Milestone definitions
        const milestones = [
            // General milestones
            { id: 'first-session', name: 'First Steps', check: () => logs.length >= 1 },
            { id: 'week-warrior', name: 'Week Warrior', check: () => streak >= 7 },
            { id: 'month-master', name: 'Month Master', check: () => streak >= 30 },
            { id: '10-hours', name: 'Dedicated Guitarist', check: () => {
                const totalTime = Object.values(categoryStats).reduce((sum, cat) => sum + cat.total_time, 0);
                return totalTime >= 36000; // 10 hours in seconds
            }},
            { id: '50-hours', name: 'Serious Musician', check: () => {
                const totalTime = Object.values(categoryStats).reduce((sum, cat) => sum + cat.total_time, 0);
                return totalTime >= 180000; // 50 hours in seconds
            }},

            // BPM achievements
            { id: 'speed-100', name: 'Century Club', check: () => {
                return Object.values(snapshots).some(s => s.best_bpm_all_time >= 100);
            }},
            { id: 'speed-120', name: 'Speed Demon', check: () => {
                return Object.values(snapshots).some(s =>
                    s.best_bpm_all_time >= 120 && s.current_subdivision === 'sixteenth'
                );
            }},
            { id: 'speed-160', name: 'Shred Territory', check: () => {
                return Object.values(snapshots).some(s =>
                    s.best_bpm_all_time >= 160 && s.current_subdivision === 'sixteenth'
                );
            }},

            // Category coverage
            { id: 'all-categories', name: 'Well-Rounded', check: () => {
                return Object.values(categoryStats).every(cat => cat.sessions > 0);
            }},

            // Progression
            { id: 'first-advancement', name: 'Progress!', check: () => {
                return Object.values(snapshots).some(s => s.advancement_ready);
            }}
        ];

        // Check each milestone
        for (const milestone of milestones) {
            if (!data.guitar_exercises.milestones.includes(milestone.id)) {
                if (milestone.check()) {
                    data.guitar_exercises.milestones.push(milestone.id);
                    newMilestones.push(milestone);
                }
            }
        }

        if (newMilestones.length > 0) {
            this.saveAll(data);
        }

        return newMilestones;
    }

    /**
     * Get all earned milestones
     */
    getGuitarMilestones() {
        const data = this.loadAll();
        return data.guitar_exercises.milestones;
    }

    /**
     * Get total guitar practice time
     */
    getTotalGuitarPracticeTime() {
        const data = this.loadAll();
        const stats = data.guitar_exercises.category_stats;
        return Object.values(stats).reduce((sum, cat) => sum + cat.total_time, 0);
    }
}

// Create singleton instance
const storageManager = new StorageManager();
