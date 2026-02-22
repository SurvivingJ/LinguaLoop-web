/**
 * ScreenManager - Handles navigation between screens
 */
class ScreenManager {
    constructor() {
        this.currentScreen = 'home';
        this.screens = [
            'home',
            'direction-trainer',
            'split-metronome',
            'polyrhythm',
            'swing',
            'tempo-ramp',
            'improv',
            'ghost',
            'ear-training',
            'rhythm-dictation',
            'metronome',
            'guitar-exercises',
            'guitar-practice-session',
            'guitar-dashboard',
            'stats',
            'settings'
        ];

        this.setupEscapeKey();
    }

    /**
     * Show a specific screen
     */
    showScreen(screenId) {
        // Hide all screens
        this.screens.forEach(id => {
            const element = document.getElementById(`${id}-screen`);
            if (element) {
                element.classList.remove('active');
            }
        });

        // Show requested screen
        const targetScreen = document.getElementById(`${screenId}-screen`);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenId;

            // Update home screen stats when returning to home
            if (screenId === 'home') {
                this.updateHomeScreenStats();
            }
        } else {
            console.error(`Screen not found: ${screenId}`);
        }
    }

    /**
     * Update stats displayed on home screen
     */
    updateHomeScreenStats() {
        const data = storageManager.loadAll();

        // Update Elo display
        const eloEl = document.getElementById('home-elo');
        if (eloEl) {
            eloEl.textContent = Math.round(data.user_elo);
        }

        // Update streak display
        const streakEl = document.getElementById('home-streak');
        if (streakEl) {
            streakEl.textContent = data.daily_streak.count;
        }

        // Update total practice time
        const totalTime = storageManager.getTotalPracticeTime();
        const timeEl = document.getElementById('home-practice-time');
        if (timeEl) {
            const hours = Math.floor(totalTime / 3600);
            const minutes = Math.floor((totalTime % 3600) / 60);
            timeEl.textContent = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        }

        // Update achievement count
        const achievementsEl = document.getElementById('home-achievements');
        if (achievementsEl) {
            achievementsEl.textContent = data.achievements.length;
        }
    }

    /**
     * Update stats displayed on stats screen
     */
    updateStatsScreen() {
        const data = storageManager.loadAll();

        // Update Elo
        const eloEl = document.getElementById('stats-elo');
        if (eloEl) {
            eloEl.textContent = Math.round(data.user_elo);
        }

        // Update streak
        const streakEl = document.getElementById('stats-streak');
        if (streakEl) {
            streakEl.textContent = data.daily_streak.count;
        }

        // Update total time
        const totalTime = storageManager.getTotalPracticeTime();
        const timeEl = document.getElementById('stats-total-time');
        if (timeEl) {
            const hours = Math.floor(totalTime / 3600);
            const minutes = Math.floor((totalTime % 3600) / 60);
            timeEl.textContent = `${hours}h ${minutes}m`;
        }

        // Update mode-specific stats
        this.updateModeStats(data);

        // Update high scores
        this.updateHighScores(data);
    }

    /**
     * Update mode-specific statistics
     */
    updateModeStats(data) {
        for (const mode in data.mode_progress) {
            const progress = data.mode_progress[mode];
            const sessionEl = document.getElementById(`stats-${mode}-sessions`);
            const timeEl = document.getElementById(`stats-${mode}-time`);

            if (sessionEl) {
                sessionEl.textContent = progress.sessions || 0;
            }

            if (timeEl) {
                const minutes = Math.floor((progress.total_time || 0) / 60);
                timeEl.textContent = `${minutes}m`;
            }

            // Mode-specific additional stats
            if (mode === 'ear_training' && progress.total > 0) {
                const accuracyEl = document.getElementById('stats-ear-accuracy');
                if (accuracyEl) {
                    const accuracy = (progress.correct / progress.total * 100).toFixed(1);
                    accuracyEl.textContent = `${accuracy}%`;
                }
            }

            if (mode === 'rhythm_dictation' && progress.total > 0) {
                const accuracyEl = document.getElementById('stats-rhythm-accuracy');
                if (accuracyEl) {
                    const accuracy = (progress.correct / progress.total * 100).toFixed(1);
                    accuracyEl.textContent = `${accuracy}%`;
                }
            }
        }
    }

    /**
     * Update high scores display
     */
    updateHighScores(data) {
        for (const mode in data.high_scores) {
            const scoreEl = document.getElementById(`highscore-${mode}`);
            if (scoreEl) {
                scoreEl.textContent = data.high_scores[mode];
            }
        }
    }

    /**
     * Setup escape key to return to home
     */
    setupEscapeKey() {
        document.addEventListener('keydown', (e) => {
            // Only return to home if not in an active game/session
            if (e.key === 'Escape' && !window.gameActive) {
                this.showScreen('home');
            }
        });
    }

    /**
     * Get current screen
     */
    getCurrentScreen() {
        return this.currentScreen;
    }
}

// Create singleton instance
const screenManager = new ScreenManager();
