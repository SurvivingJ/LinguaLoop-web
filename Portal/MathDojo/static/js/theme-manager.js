/**
 * ThemeManager - Handles theme switching, persistence, and canvas color coordination
 */
class ThemeManager {
    constructor() {
        this.themes = {
            'neon-arcade': {
                name: 'NEON ARCADE',
                metaColor: '#0d0d0d',
                colors: {
                    primary: '#39ff14',
                    secondary: '#00d9ff',
                    background: '#000',
                    danger: '#ff0055',
                    text: '#39ff14',
                    star: '#fff'
                }
            },
            'sunset-racer': {
                name: 'SUNSET RACER',
                metaColor: '#1a0033',
                colors: {
                    primary: '#ff6ec7',
                    secondary: '#ffd900',
                    background: '#1a0033',
                    danger: '#ff2a6d',
                    text: '#ff6ec7',
                    star: '#ffd900'
                }
            },
            'deep-space': {
                name: 'DEEP SPACE',
                metaColor: '#000814',
                colors: {
                    primary: '#00d9ff',
                    secondary: '#4ea8ff',
                    background: '#000814',
                    danger: '#ff4d6d',
                    text: '#00d9ff',
                    star: '#4dd0e1'
                }
            },
            'pixel-farm': {
                name: 'PIXEL FARM',
                metaColor: '#faf3e0',
                colors: {
                    primary: '#6b8e23',
                    secondary: '#2b6cb0',
                    background: '#f5e6d3',
                    danger: '#c44536',
                    text: '#3d2817',
                    star: '#d2691e'
                }
            },
            'dungeon-crawler': {
                name: 'DUNGEON CRAWLER',
                metaColor: '#1c1410',
                colors: {
                    primary: '#d4af37',
                    secondary: '#6c5ce7',
                    background: '#1c1410',
                    danger: '#8b0000',
                    text: '#d4af37',
                    star: '#cd7f32'
                }
            },
            'bauhaus': {
                name: 'BAUHAUS',
                metaColor: '#ffffff',
                colors: {
                    primary: '#000000',
                    secondary: '#0057b8',
                    background: '#ffffff',
                    danger: '#e10600',
                    text: '#000000',
                    star: '#cccccc'
                }
            },
            'fantasy': {
                name: 'FANTASY',
                metaColor: '#f6f0dc',
                colors: {
                    primary: '#2ecc71',
                    secondary: '#3a86ff',
                    background: '#f4e7d7',
                    danger: '#c0392b',
                    text: '#2c3e50',
                    star: '#9b59b6'
                }
            },
            'gothic': {
                name: 'GOTHIC',
                metaColor: '#07060a',
                colors: {
                    primary: '#dc143c',
                    secondary: '#2ec4b6',
                    background: '#0a0a0a',
                    danger: '#ff0000',
                    text: '#e7e3da',
                    star: '#8b0000'
                }
            }
        };

        this.currentTheme = 'neon-arcade';
    }

    /**
     * Initialize after DOM is ready
     */
    init() {
        this.loadTheme();
        this.setupSelector();
    }

    /**
     * Load saved theme from storage
     */
    loadTheme() {
        const settings = storageManager.load('settings');
        const saved = settings.theme || 'neon-arcade';
        this.applyTheme(saved);
    }

    /**
     * Apply a theme by ID
     */
    applyTheme(themeId) {
        if (!this.themes[themeId]) {
            themeId = 'neon-arcade';
        }

        this.currentTheme = themeId;
        document.documentElement.setAttribute('data-theme', themeId);

        // Update mobile browser chrome color
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute('content', this.themes[themeId].metaColor);
        }

        // Persist
        const settings = storageManager.load('settings');
        settings.theme = themeId;
        storageManager.save('settings', settings);

        // Update selector if it exists
        const selector = document.getElementById('theme-selector');
        if (selector) {
            selector.value = themeId;
        }
    }

    /**
     * Get canvas colors for the current theme (used by space-defense.js)
     */
    getCanvasColors() {
        return this.themes[this.currentTheme].colors;
    }

    /**
     * Populate and bind the theme selector dropdown
     */
    setupSelector() {
        const selector = document.getElementById('theme-selector');
        if (!selector) return;

        // Populate options
        Object.keys(this.themes).forEach(key => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = this.themes[key].name;
            selector.appendChild(option);
        });

        // Set current
        selector.value = this.currentTheme;

        // Listen for changes
        selector.addEventListener('change', (e) => {
            this.applyTheme(e.target.value);
        });
    }
}

// Global instance
const themeManager = new ThemeManager();
