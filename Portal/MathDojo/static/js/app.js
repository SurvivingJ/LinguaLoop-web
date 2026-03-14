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
        this.autoSubmitToggle = document.getElementById('auto-submit-toggle');
        this.fontToggle = document.getElementById('font-toggle');
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

        // Auto-submit toggle
        if (this.autoSubmitToggle) {
            this.autoSubmitToggle.addEventListener('click', () => {
                const settings = storageManager.load('settings');
                settings.auto_submit = !settings.auto_submit;
                storageManager.save('settings', settings);
                InputHandler.autoSubmitEnabled = settings.auto_submit;
                this.autoSubmitToggle.textContent = settings.auto_submit ? 'ON' : 'OFF';
                this.autoSubmitToggle.classList.toggle('active', settings.auto_submit);
            });
        }

        // Font toggle
        if (this.fontToggle) {
            this.fontToggle.addEventListener('click', () => {
                const settings = storageManager.load('settings');
                const newMode = settings.font_mode === 'retro' ? 'clean' : 'retro';
                settings.font_mode = newMode;
                storageManager.save('settings', settings);
                document.documentElement.setAttribute('data-font', newMode);
                this.fontToggle.textContent = newMode === 'retro' ? 'RETRO' : 'CLEAN';
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

        // Auto-submit (default true for backwards compat)
        const autoSubmit = settings.auto_submit !== undefined ? settings.auto_submit : true;
        InputHandler.autoSubmitEnabled = autoSubmit;
        if (this.autoSubmitToggle) {
            this.autoSubmitToggle.textContent = autoSubmit ? 'ON' : 'OFF';
            this.autoSubmitToggle.classList.toggle('active', autoSubmit);
        }

        // Font mode
        const fontMode = settings.font_mode || 'retro';
        document.documentElement.setAttribute('data-font', fontMode);
        if (this.fontToggle) {
            this.fontToggle.textContent = fontMode === 'retro' ? 'RETRO' : 'CLEAN';
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

    // Profile selection handlers
    const profileJames = document.getElementById('profile-james');
    const profileGuest = document.getElementById('profile-guest');
    const statsBtn = document.getElementById('stats-menu-btn');
    const focusMixBtn = document.getElementById('focus-mix-btn');
    const menuFooter = document.getElementById('menu-footer');

    function selectProfile(name) {
        profileManager.selectProfile(name);
        screenManager.showScreen('screen-menu');

        if (profileManager.isTracking()) {
            if (statsBtn) statsBtn.style.display = '';
            if (focusMixBtn) focusMixBtn.style.display = '';
            if (menuFooter) menuFooter.textContent = `PLAYER: ${name.toUpperCase()}`;
        } else {
            if (statsBtn) statsBtn.style.display = 'none';
            if (focusMixBtn) focusMixBtn.style.display = 'none';
            if (menuFooter) menuFooter.textContent = 'GUEST MODE — NO STATS';
        }
    }

    if (profileJames) {
        profileJames.addEventListener('click', () => selectProfile('james'));
    }
    if (profileGuest) {
        profileGuest.addEventListener('click', () => selectProfile('guest'));
    }

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
