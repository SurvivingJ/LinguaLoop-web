/**
 * ThemeManager - Handles visual themes for MusicDojo
 */
class ThemeManager {
    constructor() {
        this.themes = {
            NEON_PULSE: {
                name: 'NEON PULSE',
                metaColor: '#1a1a2e',
                colors: {
                    primary: '#667eea',
                    secondary: '#764ba2',
                    accent: '#ecc94b',
                    background: '#1a1a2e',
                    surface: '#16213e',
                    surface2: '#2d3748',
                    text: '#ffffff',
                    textSecondary: '#a0aec0',
                    success: '#48bb78',
                    danger: '#e53e3e',
                    warning: '#ecc94b',
                    border: '#4a5568'
                }
            },
            JAZZ_LOUNGE: {
                name: 'JAZZ LOUNGE',
                metaColor: '#2a1810',
                colors: {
                    primary: '#d4af37',
                    secondary: '#8b4513',
                    accent: '#cd5c5c',
                    background: '#1a0f0a',
                    surface: '#2a1810',
                    surface2: '#3d2416',
                    text: '#f5deb3',
                    textSecondary: '#d4a574',
                    success: '#98c379',
                    danger: '#e06c75',
                    warning: '#e5c07b',
                    border: '#6b4423'
                }
            },
            CLASSICAL_CONCERT: {
                name: 'CLASSICAL CONCERT',
                metaColor: '#0a0a0a',
                colors: {
                    primary: '#d4af37',
                    secondary: '#c0c0c0',
                    accent: '#ffd700',
                    background: '#000000',
                    surface: '#1a1a1a',
                    surface2: '#2a2a2a',
                    text: '#ffffff',
                    textSecondary: '#c0c0c0',
                    success: '#90ee90',
                    danger: '#ff6b6b',
                    warning: '#ffd700',
                    border: '#4a4a4a'
                }
            },
            RETRO_SYNTH: {
                name: 'RETRO SYNTH',
                metaColor: '#1a0033',
                colors: {
                    primary: '#ff006e',
                    secondary: '#8338ec',
                    accent: '#00f5ff',
                    background: '#0d0221',
                    surface: '#1a0033',
                    surface2: '#2e0055',
                    text: '#ffffff',
                    textSecondary: '#ff99c8',
                    success: '#06ffa5',
                    danger: '#ff006e',
                    warning: '#ffbe0b',
                    border: '#8338ec'
                }
            },
            FOREST_ACOUSTIC: {
                name: 'FOREST ACOUSTIC',
                metaColor: '#1a2f1a',
                colors: {
                    primary: '#8fbc8f',
                    secondary: '#556b2f',
                    accent: '#d4a574',
                    background: '#0f1f0f',
                    surface: '#1a2f1a',
                    surface2: '#2d4a2d',
                    text: '#f0ead6',
                    textSecondary: '#bdb76b',
                    success: '#90ee90',
                    danger: '#cd5c5c',
                    warning: '#daa520',
                    border: '#556b2f'
                }
            },
            MIDNIGHT_KEYS: {
                name: 'MIDNIGHT KEYS',
                metaColor: '#0a1929',
                colors: {
                    primary: '#90caf9',
                    secondary: '#5c6bc0',
                    accent: '#64b5f6',
                    background: '#001e3c',
                    surface: '#0a1929',
                    surface2: '#173a5e',
                    text: '#ffffff',
                    textSecondary: '#b0bec5',
                    success: '#66bb6a',
                    danger: '#ef5350',
                    warning: '#ffa726',
                    border: '#2e4a68'
                }
            },
            SUNSET_STAGE: {
                name: 'SUNSET STAGE',
                metaColor: '#2d1b00',
                colors: {
                    primary: '#ff6b35',
                    secondary: '#f7931e',
                    accent: '#ffd23f',
                    background: '#1a0f00',
                    surface: '#2d1b00',
                    surface2: '#4a2f0a',
                    text: '#fff8e7',
                    textSecondary: '#ffd4a3',
                    success: '#aad576',
                    danger: '#e63946',
                    warning: '#ffd23f',
                    border: '#8b4500'
                }
            },
            MINIMAL_MONO: {
                name: 'MINIMAL MONO',
                metaColor: '#1a1a1a',
                colors: {
                    primary: '#ffffff',
                    secondary: '#b0b0b0',
                    accent: '#808080',
                    background: '#0a0a0a',
                    surface: '#1a1a1a',
                    surface2: '#2a2a2a',
                    text: '#ffffff',
                    textSecondary: '#b0b0b0',
                    success: '#d0d0d0',
                    danger: '#808080',
                    warning: '#a0a0a0',
                    border: '#4a4a4a'
                }
            }
        };

        this.currentTheme = 'NEON_PULSE';
        this.loadTheme();
    }

    /**
     * Load theme from storage and apply it
     */
    loadTheme() {
        const settings = storageManager.load('settings');
        this.currentTheme = settings.theme || 'NEON_PULSE';
        this.applyTheme(this.currentTheme);
    }

    /**
     * Apply a theme
     */
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) {
            console.error('Theme not found:', themeName);
            return;
        }

        this.currentTheme = themeName;

        // Apply CSS variables
        const root = document.documentElement;
        const colors = theme.colors;

        root.style.setProperty('--color-primary', colors.primary);
        root.style.setProperty('--color-secondary', colors.secondary);
        root.style.setProperty('--color-accent', colors.accent);
        root.style.setProperty('--color-background', colors.background);
        root.style.setProperty('--color-surface', colors.surface);
        root.style.setProperty('--color-surface2', colors.surface2);
        root.style.setProperty('--color-text', colors.text);
        root.style.setProperty('--color-text-secondary', colors.textSecondary);
        root.style.setProperty('--color-success', colors.success);
        root.style.setProperty('--color-danger', colors.danger);
        root.style.setProperty('--color-warning', colors.warning);
        root.style.setProperty('--color-border', colors.border);

        // Update meta theme color
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', theme.metaColor);
        }

        // Save to storage
        const settings = storageManager.load('settings');
        settings.theme = themeName;
        storageManager.save('settings', settings);

        // Dispatch event for theme change
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: themeName } }));
    }

    /**
     * Get current theme
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * Get all available themes
     */
    getAllThemes() {
        return Object.keys(this.themes).map(key => ({
            key,
            name: this.themes[key].name
        }));
    }

    /**
     * Get theme colors (for canvas rendering)
     */
    getThemeColors() {
        return this.themes[this.currentTheme].colors;
    }

    /**
     * Get canvas-optimized colors
     */
    getCanvasColors() {
        const colors = this.getThemeColors();
        return {
            background: colors.background,
            primary: colors.primary,
            secondary: colors.secondary,
            accent: colors.accent,
            success: colors.success,
            danger: colors.danger,
            warning: colors.warning,
            text: colors.textSecondary,
            border: colors.border
        };
    }
}

// Create singleton instance
const themeManager = new ThemeManager();
