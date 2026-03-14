/**
 * ScreenManager - Handles screen transitions
 */
class ScreenManager {
    constructor() {
        this.currentScreen = 'screen-profile';
        this.screens = document.querySelectorAll('.screen');
        this.setupNavigation();
    }

    /**
     * Show a specific screen by ID
     */
    showScreen(screenId) {
        // Add 'screen-' prefix if not present
        if (!screenId.startsWith('screen-')) {
            screenId = 'screen-' + screenId;
        }

        // Hide all screens
        this.screens.forEach(screen => {
            screen.classList.remove('active');
        });

        // Show target screen
        const targetScreen = document.getElementById(screenId);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenId;

            // Update UI if returning to menu
            if (screenId === 'screen-menu') {
                this.updateMenuStats();
            }

            // Load stats dashboard when shown
            if (screenId === 'screen-stats' && typeof statsDashboard !== 'undefined') {
                statsDashboard.load();
            }
        }
    }

    /**
     * Setup navigation event listeners
     */
    setupNavigation() {
        // All buttons with data-screen attribute
        document.addEventListener('click', (e) => {
            const target = e.target.closest('[data-screen]');
            if (target) {
                const screenId = target.getAttribute('data-screen');
                this.showScreen(screenId);
            }
        });

        // Escape key to return to menu
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentScreen !== 'screen-menu') {
                // Don't interrupt active games
                if (!this.isGameActive()) {
                    this.showScreen('screen-menu');
                }
            }
        });
    }

    /**
     * Check if a game is currently active
     */
    isGameActive() {
        // Check if any game timers are running
        return window.gameActive || false;
    }

    /**
     * Update stats displayed on menu
     */
    updateMenuStats() {
        const elo = storageManager.load('user_elo');
        const streak = storageManager.load('daily_streak');

        const eloDisplay = document.getElementById('elo-display');
        const streakDisplay = document.getElementById('streak-display');

        if (eloDisplay) eloDisplay.textContent = elo;
        if (streakDisplay) streakDisplay.textContent = streak.count;
    }
}

// Create global instance
const screenManager = new ScreenManager();
