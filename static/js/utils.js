/**
 * LinguaDojo Shared Utilities
 * Common functions used across templates - import to avoid duplication.
 */

// =============================================================================
// CONSTANTS
// =============================================================================

const LINGUADOJO = window.LINGUADOJO || {};

// ELO difficulty ranges
const ELO_RANGES = {
    BEGINNER: { min: 0, max: 1199, label: 'Beginner', class: 'badge-beginner' },
    ELEMENTARY: { min: 1200, max: 1399, label: 'Elementary', class: 'badge-elementary' },
    INTERMEDIATE: { min: 1400, max: 1599, label: 'Intermediate', class: 'badge-intermediate' },
    ADVANCED: { min: 1600, max: 1799, label: 'Advanced', class: 'badge-advanced' },
    EXPERT: { min: 1800, max: 9999, label: 'Expert', class: 'badge-expert' }
};

// Language flag mapping
const LANGUAGE_FLAGS = {
    'en': '🇺🇸', 'english': '🇺🇸', 'English': '🇺🇸',
    'zh': '🇨🇳', 'cn': '🇨🇳', 'chinese': '🇨🇳', 'Chinese': '🇨🇳',
    'ja': '🇯🇵', 'jp': '🇯🇵', 'japanese': '🇯🇵', 'Japanese': '🇯🇵',
    'ko': '🇰🇷', 'korean': '🇰🇷', 'Korean': '🇰🇷',
    'fr': '🇫🇷', 'french': '🇫🇷', 'French': '🇫🇷'
};

// Debug mode - set to false in production
const DEBUG = false;

// =============================================================================
// SECURITY
// =============================================================================

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Raw text to escape
 * @returns {string} HTML-safe text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// DIFFICULTY / ELO HELPERS
// =============================================================================

/**
 * Get difficulty label from ELO rating
 * @param {number} elo - ELO rating
 * @returns {string} Difficulty label
 */
function getDifficultyLabel(elo) {
    if (elo < 1200) return 'Beginner';
    if (elo < 1400) return 'Elementary';
    if (elo < 1600) return 'Intermediate';
    if (elo < 1800) return 'Advanced';
    return 'Expert';
}

/**
 * Get full difficulty info from ELO rating
 * @param {number} elo - ELO rating
 * @returns {Object} {label, class, color}
 */
function getDifficultyInfo(elo) {
    const level = getDifficultyLabel(elo);
    return {
        label: level,
        class: `badge-${level.toLowerCase()}`,
        color: getDifficultyColor(level)
    };
}

/**
 * Get color for difficulty level
 * @param {string} level - Difficulty level name
 * @returns {string} CSS color
 */
function getDifficultyColor(level) {
    const colors = {
        'Beginner': '#22c55e',
        'Elementary': '#84cc16',
        'Intermediate': '#eab308',
        'Advanced': '#f97316',
        'Expert': '#ef4444'
    };
    return colors[level] || '#6b7280';
}

// =============================================================================
// LANGUAGE HELPERS
// =============================================================================

/**
 * Get flag emoji for language
 * @param {string} langCode - Language code or name
 * @returns {string} Flag emoji or default globe
 */
function getLanguageFlag(langCode) {
    return LANGUAGE_FLAGS[langCode] || '🌐';
}

// =============================================================================
// DOM HELPERS
// =============================================================================

/**
 * Show an element by removing d-none class
 * @param {HTMLElement|string} el - Element or selector
 */
function show(el) {
    const element = typeof el === 'string' ? document.querySelector(el) : el;
    element?.classList.remove('d-none');
}

/**
 * Hide an element by adding d-none class
 * @param {HTMLElement|string} el - Element or selector
 */
function hide(el) {
    const element = typeof el === 'string' ? document.querySelector(el) : el;
    element?.classList.add('d-none');
}

/**
 * Toggle element visibility
 * @param {HTMLElement|string} el - Element or selector
 * @param {boolean} visible - Whether to show (true) or hide (false)
 */
function toggle(el, visible) {
    visible ? show(el) : hide(el);
}

// =============================================================================
// API HELPERS
// =============================================================================

/**
 * Get auth headers for API requests
 * @returns {Object} Headers object with Authorization
 */
function getAuthHeaders() {
    const token = localStorage.getItem('jwt_token') || LINGUADOJO.jwt_token;
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

/**
 * Make authenticated API request
 * @param {string} url - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(url, options = {}) {
    const config = {
        headers: getAuthHeaders(),
        ...options
    };

    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.message || 'Request failed');
    }

    return data;
}

/**
 * API GET request
 * @param {string} url - API endpoint
 * @returns {Promise<Object>} Response data
 */
function apiGet(url) {
    return apiRequest(url, { method: 'GET' });
}

/**
 * API POST request
 * @param {string} url - API endpoint
 * @param {Object} body - Request body
 * @returns {Promise<Object>} Response data
 */
function apiPost(url, body) {
    return apiRequest(url, { method: 'POST', body });
}

// =============================================================================
// STORAGE HELPERS
// =============================================================================

/**
 * Get item from localStorage with JSON parsing
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default if not found
 * @returns {*} Parsed value or default
 */
function getStorageItem(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        return defaultValue;
    }
}

/**
 * Set item in localStorage with JSON stringification
 * @param {string} key - Storage key
 * @param {*} value - Value to store
 */
function setStorageItem(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

// =============================================================================
// LOGGING (conditional)
// =============================================================================

/**
 * Debug log - only outputs if DEBUG is true
 * @param  {...any} args - Arguments to log
 */
function debugLog(...args) {
    if (DEBUG) {
        console.log(...args);
    }
}

// =============================================================================
// DATE/TIME HELPERS
// =============================================================================

/**
 * Format seconds to MM:SS
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDate(date) {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// =============================================================================
// EXPORTS (for module usage)
// =============================================================================

// Make utilities globally available
window.LinguaUtils = {
    // Constants
    ELO_RANGES,
    LANGUAGE_FLAGS,
    DEBUG,

    // Security
    escapeHtml,

    // Difficulty
    getDifficultyLabel,
    getDifficultyInfo,
    getDifficultyColor,

    // Language
    getLanguageFlag,

    // DOM
    show,
    hide,
    toggle,

    // API
    getAuthHeaders,
    apiRequest,
    apiGet,
    apiPost,

    // Storage
    getStorageItem,
    setStorageItem,

    // Logging
    debugLog,

    // Date/Time
    formatTime,
    formatDate
};
