/**
 * LinguaDojo Theme Manager
 * Handles theme switching, persistence via localStorage, and smooth transitions.
 */
(function() {
    'use strict';

    const THEMES = {
        'default':  { name: 'Default',  icon: 'fa-sun' },
        'midnight': { name: 'Midnight', icon: 'fa-moon' },
        'sakura':   { name: 'Sakura',   icon: 'fa-fan' },
        'forest':   { name: 'Forest',   icon: 'fa-leaf' }
    };

    const STORAGE_KEY = 'linguadojo-theme';
    let currentTheme = 'default';

    function loadTheme() {
        const saved = localStorage.getItem(STORAGE_KEY) || 'default';
        applyTheme(saved, false);
    }

    function applyTheme(themeId, animate) {
        if (!THEMES[themeId]) themeId = 'default';
        currentTheme = themeId;

        if (themeId === 'default') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', themeId);
        }

        // Update meta theme-color
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            const primary = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
            meta.setAttribute('content', primary);
        }

        localStorage.setItem(STORAGE_KEY, themeId);
        updateSwitcherUI();
    }

    function setupSwitcher() {
        const dropdown = document.getElementById('themeSwitcherMenu');
        if (!dropdown) return;

        dropdown.innerHTML = '';

        Object.entries(THEMES).forEach(function([id, theme]) {
            const li = document.createElement('li');
            const btn = document.createElement('button');
            btn.className = 'dropdown-item d-flex align-items-center gap-2';
            btn.type = 'button';
            btn.dataset.theme = id;
            btn.innerHTML = '<i class="fas ' + theme.icon + '"></i> ' + theme.name;
            btn.addEventListener('click', function() {
                applyTheme(id, true);
            });
            li.appendChild(btn);
            dropdown.appendChild(li);
        });

        updateSwitcherUI();
    }

    function updateSwitcherUI() {
        var items = document.querySelectorAll('#themeSwitcherMenu .dropdown-item');
        items.forEach(function(item) {
            if (item.dataset.theme === currentTheme) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Update the trigger button icon
        var triggerIcon = document.querySelector('#themeSwitcherBtn i');
        if (triggerIcon && THEMES[currentTheme]) {
            triggerIcon.className = 'fas ' + THEMES[currentTheme].icon;
        }
    }

    // Apply theme immediately (before DOMContentLoaded) to prevent flash
    loadTheme();

    document.addEventListener('DOMContentLoaded', function() {
        setupSwitcher();
    });

    // Expose for external use if needed
    window.LinguaTheme = {
        apply: applyTheme,
        current: function() { return currentTheme; }
    };
})();
