/**
 * Main App - Initialization and global functionality
 */

/**
 * Simple AudioManager for sound effects
 */
class AudioManager {
    constructor() {
        this.sounds = {};
        this.enabled = true;
        this.loadSettings();
    }

    /**
     * Load sound settings from storage
     */
    loadSettings() {
        const settings = storageManager.load('settings');
        this.enabled = settings.sound;
    }

    /**
     * Preload sound file
     */
    preload(name, url) {
        try {
            this.sounds[name] = new Audio(url);
            this.sounds[name].preload = 'auto';
        } catch (e) {
            console.warn(`Failed to load sound: ${name}`, e);
        }
    }

    /**
     * Play sound effect
     */
    play(name) {
        if (!this.enabled) return;

        const sound = this.sounds[name];
        if (sound) {
            try {
                sound.currentTime = 0;
                sound.play().catch(e => {
                    console.warn(`Failed to play sound: ${name}`, e);
                });
            } catch (e) {
                console.warn(`Error playing sound: ${name}`, e);
            }
        }
    }

    /**
     * Toggle sound on/off
     */
    toggle() {
        this.enabled = !this.enabled;

        const settings = storageManager.load('settings');
        settings.sound = this.enabled;
        storageManager.save('settings', settings);

        return this.enabled;
    }

    /**
     * Set enabled state
     */
    setEnabled(enabled) {
        this.enabled = enabled;

        const settings = storageManager.load('settings');
        settings.sound = enabled;
        storageManager.save('settings', settings);
    }
}

/**
 * Settings screen functionality
 */
class Settings {
    constructor() {
        this.soundToggle = document.getElementById('sound-toggle');
        this.difficultyOffset = document.getElementById('difficulty-offset');
        this.difficultyOffsetValue = document.getElementById('difficulty-offset-value');
        this.resetButton = document.getElementById('reset-progress');

        this.setupEventListeners();
        this.loadSettings();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Sound toggle
        if (this.soundToggle) {
            this.soundToggle.addEventListener('click', () => {
                const enabled = window.audioManager.toggle();
                this.soundToggle.textContent = enabled ? 'ON' : 'OFF';
            });
        }

        // Difficulty offset
        if (this.difficultyOffset) {
            this.difficultyOffset.addEventListener('input', (e) => {
                const value = parseInt(e.target.value, 10);
                if (this.difficultyOffsetValue) {
                    this.difficultyOffsetValue.textContent = value;
                }

                const settings = storageManager.load('settings');
                settings.difficulty_offset = value;
                storageManager.save('settings', settings);
            });
        }

        // Reset progress
        if (this.resetButton) {
            this.resetButton.addEventListener('click', () => {
                if (confirm('Are you sure you want to reset ALL progress? This cannot be undone.')) {
                    storageManager.resetAll();
                    alert('Progress reset! Refreshing page...');
                    location.reload();
                }
            });
        }
    }

    /**
     * Load and display current settings
     */
    loadSettings() {
        const settings = storageManager.load('settings');

        if (this.soundToggle) {
            this.soundToggle.textContent = settings.sound ? 'ON' : 'OFF';
        }

        if (this.difficultyOffset) {
            this.difficultyOffset.value = settings.difficulty_offset;
        }

        if (this.difficultyOffsetValue) {
            this.difficultyOffsetValue.textContent = settings.difficulty_offset;
        }
    }
}

/**
 * Initialize application
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize audio manager
    window.audioManager = new AudioManager();

    // Preload sounds (using data URIs for silent placeholders)
    // In production, replace these with actual 8-bit sound files
    const silentAudio = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

    window.audioManager.preload('correct', silentAudio);
    window.audioManager.preload('wrong', silentAudio);
    window.audioManager.preload('laser', silentAudio);
    window.audioManager.preload('explosion', silentAudio);

    // Initialize theme manager
    themeManager.init();

    // Initialize settings
    window.settings = new Settings();

    // Update menu stats on load
    screenManager.updateMenuStats();

    console.log('RetroMind Math initialized!');
});

/**
 * Prevent accidental navigation away during active games
 */
window.addEventListener('beforeunload', (e) => {
    if (window.gameActive) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});
