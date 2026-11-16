/**
 * LinguaDojo Theme Manager
 *
 * Two independent, persisted choices:
 *   theme  'default' (the redesign palette) | 'stillwater' | 'midnight' |
 *          'sakura' | 'forest' | 'inkstone'      -> html[data-theme]
 *          (no attribute for 'default')
 *   mode   'system' | 'light' | 'dark'           -> html[data-mode]
 *          (no attribute for 'system'). Only the default theme has light
 *          and dark variants; a named theme is fixed light or dark.
 *
 * pages/base-head.js applies both before first paint (no flash); this file
 * keeps them in sync afterwards, renders the switchers and exposes the API
 * below. Every change dispatches `lingua:themechange` on document with
 * detail { theme, mode, scheme }.
 *
 * Public API — window.LinguaTheme:
 *   list()               -> [{ id, name, nameKey, description, descriptionKey,
 *                             scheme: 'auto'|'light'|'dark', swatches: [bg, brand, accent] }]
 *   current()            -> theme id
 *   setTheme(id)         -> apply + persist a theme ('default' to go back)
 *   apply(id)            -> alias of setTheme (kept for older callers)
 *   mode()               -> 'system' | 'light' | 'dark'
 *   setMode(mode)        -> apply + persist the light/dark preference. Choosing
 *                           light or dark while a named theme is active switches
 *                           back to the default theme (the mode only applies to it).
 *   scheme()             -> the resolved scheme now: 'light' | 'dark'
 *   toggleScheme()       -> flip light/dark (the app bar's moon/sun button)
 *   onChange(fn)         -> subscribe; returns an unsubscribe function
 *   renderThemePicker(el)  fills el with a theme list (buttons, aria-pressed)
 *   renderModePicker(el)   fills el with a System / Light / Dark segmented control
 *
 * Declarative hooks (rendered on DOMContentLoaded and kept in sync):
 *   <ul id="themeSwitcherMenu">        dropdown items (app bar)
 *   <div data-ld-theme-picker>         list of theme rows (.ld-trow)
 *   <div data-ld-mode-picker>          segmented System / Light / Dark
 *   <button data-ld-mode-toggle>       light/dark toggle (icon swaps)
 */
(function () {
  'use strict';

  const THEMES = [
    {
      id: 'default',
      name: 'Dojo (default)',
      nameKey: 'theme.name.default',
      description: 'Follows light and dark',
      descriptionKey: 'theme.desc.default',
      scheme: 'auto',
      swatches: ['#edf3f1', '#0a6b60', '#ef6a35'],
    },
    {
      id: 'stillwater',
      name: 'Still Water',
      description: 'Light',
      descriptionKey: 'theme.desc.light',
      scheme: 'light',
      swatches: ['#f6f9f8', '#0e7569', '#e8833a'],
    },
    {
      id: 'midnight',
      name: 'Midnight',
      description: 'Dark',
      descriptionKey: 'theme.desc.dark',
      scheme: 'dark',
      swatches: ['#0b1416', '#3db3a0', '#f0975a'],
    },
    {
      id: 'sakura',
      name: 'Sakura',
      description: 'Light',
      descriptionKey: 'theme.desc.light',
      scheme: 'light',
      swatches: ['#fbf3f6', '#c0407c', '#e8833a'],
    },
    {
      id: 'forest',
      name: 'Forest',
      description: 'Light',
      descriptionKey: 'theme.desc.light',
      scheme: 'light',
      swatches: ['#f4f8f4', '#2f7d46', '#b08530'],
    },
    {
      id: 'inkstone',
      name: 'Inkstone & Vermilion',
      description: 'Light',
      descriptionKey: 'theme.desc.light',
      scheme: 'light',
      swatches: ['#f5f1e8', '#b5331e', '#b8862c'],
    },
  ];
  const MODES = ['system', 'light', 'dark'];
  const MODE_KEYS = {
    system: ['theme.mode.system', 'System'],
    light: ['theme.mode.light', 'Light'],
    dark: ['theme.mode.dark', 'Dark'],
  };

  const STORAGE_KEY = 'linguadojo-theme';
  const MODE_KEY = 'linguadojo-theme-mode';
  const root = document.documentElement;
  const listeners = [];
  const darkQuery =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;

  let currentTheme = 'default';
  let currentMode = 'system';

  function byId(id) {
    for (let i = 0; i < THEMES.length; i++) if (THEMES[i].id === id) return THEMES[i];
    return null;
  }

  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function write(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage blocked: the choice lasts for this page only */
    }
  }

  function tr(key, fallback) {
    const i18n = window.LinguaI18n;
    if (!key || !i18n || typeof i18n.t !== 'function' || !i18n.isReady || !i18n.isReady()) {
      return fallback;
    }
    const text = i18n.t(key);
    return text && text !== key ? text : fallback;
  }

  function systemDark() {
    return !!(darkQuery && darkQuery.matches);
  }

  function resolvedScheme() {
    const theme = byId(currentTheme);
    if (theme && theme.scheme !== 'auto') return theme.scheme;
    if (currentMode === 'light' || currentMode === 'dark') return currentMode;
    return systemDark() ? 'dark' : 'light';
  }

  function syncDocument() {
    if (currentTheme === 'default') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', currentTheme);
    if (currentMode === 'system') root.removeAttribute('data-mode');
    else root.setAttribute('data-mode', currentMode);
    // Bootstrap's own dark styles (close icons, form-control chrome).
    root.setAttribute('data-bs-theme', resolvedScheme());

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta && typeof getComputedStyle === 'function') {
      const bg = getComputedStyle(root).getPropertyValue('--bg').trim();
      if (bg) meta.setAttribute('content', bg);
    }
  }

  function notify() {
    const detail = { theme: currentTheme, mode: currentMode, scheme: resolvedScheme() };
    updateSwitcherUI();
    for (let i = 0; i < listeners.length; i++) {
      try {
        listeners[i](detail);
      } catch (e) {
        console.error('[theme] listener failed', e);
      }
    }
    try {
      document.dispatchEvent(new CustomEvent('lingua:themechange', { detail: detail }));
    } catch {
      /* CustomEvent unsupported: listeners above still ran */
    }
  }

  function setTheme(themeId) {
    if (!byId(themeId)) themeId = 'default';
    currentTheme = themeId;
    write(STORAGE_KEY, themeId);
    syncDocument();
    notify();
  }

  function setMode(mode) {
    if (MODES.indexOf(mode) === -1) mode = 'system';
    currentMode = mode;
    write(MODE_KEY, mode);
    // The mode only exists for the default theme: picking light/dark from a
    // named theme means "the default palette, in that scheme".
    if (mode !== 'system' && currentTheme !== 'default') {
      currentTheme = 'default';
      write(STORAGE_KEY, 'default');
    }
    syncDocument();
    notify();
  }

  function toggleScheme() {
    setMode(resolvedScheme() === 'dark' ? 'light' : 'dark');
  }

  function loadTheme() {
    const savedTheme = read(STORAGE_KEY);
    const savedMode = read(MODE_KEY);
    currentTheme = byId(savedTheme) ? savedTheme : 'default';
    currentMode = MODES.indexOf(savedMode) !== -1 ? savedMode : 'system';
    syncDocument();
  }

  // ---- Rendering -----------------------------------------------------------

  function swatchesHTML(theme) {
    return (
      '<span class="ld-swatches" aria-hidden="true">' +
      theme.swatches
        .map(function (c) {
          return '<i style="background:' + c + '"></i>';
        })
        .join('') +
      '</span>'
    );
  }

  function themeLabel(theme) {
    return tr(theme.nameKey, theme.name);
  }

  function themeDescription(theme) {
    return tr(theme.descriptionKey, theme.description);
  }

  function setupSwitcher() {
    const dropdown = document.getElementById('themeSwitcherMenu');
    if (!dropdown) return;
    dropdown.innerHTML = '';
    THEMES.forEach(function (theme) {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.className = 'dropdown-item ld-theme-opt';
      btn.type = 'button';
      btn.dataset.themeId = theme.id;
      btn.innerHTML =
        swatchesHTML(theme) +
        '<span class="ld-theme-opt__text"><span></span><small></small></span>';
      btn.querySelector('.ld-theme-opt__text > span').textContent = themeLabel(theme);
      btn.querySelector('small').textContent = themeDescription(theme);
      btn.addEventListener('click', function () {
        setTheme(theme.id);
      });
      li.appendChild(btn);
      dropdown.appendChild(li);
    });
  }

  function renderThemePicker(el) {
    if (!el) return;
    el.classList.add('ld-rowlist');
    el.setAttribute('role', 'group');
    el.innerHTML = '';
    THEMES.forEach(function (theme) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ld-trow ld-theme-opt';
      btn.dataset.themeId = theme.id;
      btn.innerHTML =
        swatchesHTML(theme) +
        '<span class="ld-trow__mid"><b></b><small></small></span>' +
        '<span class="ld-tag" data-ld-theme-state></span>';
      btn.querySelector('b').textContent = themeLabel(theme);
      btn.querySelector('small').textContent = themeDescription(theme);
      btn.addEventListener('click', function () {
        setTheme(theme.id);
      });
      el.appendChild(btn);
    });
    el.dataset.ldRendered = '1';
    updateSwitcherUI();
  }

  function renderModePicker(el) {
    if (!el) return;
    el.classList.add('ld-seg');
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', tr('theme.mode_label', 'Appearance'));
    el.innerHTML = '';
    MODES.forEach(function (mode) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.mode = mode;
      btn.textContent = tr(MODE_KEYS[mode][0], MODE_KEYS[mode][1]);
      btn.addEventListener('click', function () {
        setMode(mode);
      });
      el.appendChild(btn);
    });
    el.dataset.ldRendered = '1';
    updateSwitcherUI();
  }

  function updateSwitcherUI() {
    if (!document.body) return;
    const usesMode = currentTheme === 'default';
    document.querySelectorAll('.ld-theme-opt[data-theme-id]').forEach(function (item) {
      const on = item.dataset.themeId === currentTheme;
      item.classList.toggle('active', on && item.classList.contains('dropdown-item'));
      item.setAttribute('aria-pressed', on ? 'true' : 'false');
      const state = item.querySelector('[data-ld-theme-state]');
      if (state) {
        state.textContent = on ? '✓' : '';
        state.classList.toggle('ld-tag--ok', on);
        state.hidden = !on;
      }
    });
    document.querySelectorAll('[data-ld-mode-picker] button[data-mode]').forEach(function (btn) {
      // Under a named theme the segmented control shows no choice: the
      // colour theme decides. Clicking still works (switches to default).
      btn.setAttribute(
        'aria-pressed',
        usesMode && btn.dataset.mode === currentMode ? 'true' : 'false'
      );
    });
    const dark = resolvedScheme() === 'dark';
    document.querySelectorAll('[data-ld-mode-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
      const icon = btn.querySelector('i');
      if (icon) icon.className = 'fas ' + (dark ? 'fa-sun' : 'fa-moon');
    });
  }

  function renderAll() {
    setupSwitcher();
    document.querySelectorAll('[data-ld-theme-picker]').forEach(renderThemePicker);
    document.querySelectorAll('[data-ld-mode-picker]').forEach(renderModePicker);
    updateSwitcherUI();
  }

  // Apply immediately (before DOMContentLoaded): base-head.js already set the
  // attributes; this re-derives them from storage and sets data-bs-theme.
  loadTheme();

  if (darkQuery) {
    const onSystemChange = function () {
      if (currentTheme === 'default' && currentMode === 'system') {
        syncDocument();
        notify();
      }
    };
    if (typeof darkQuery.addEventListener === 'function') {
      darkQuery.addEventListener('change', onSystemChange);
    } else if (typeof darkQuery.addListener === 'function') {
      darkQuery.addListener(onSystemChange);
    }
  }

  // Another tab changed the theme.
  window.addEventListener('storage', function (e) {
    if (e.key === STORAGE_KEY || e.key === MODE_KEY) {
      loadTheme();
      notify();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    renderAll();
    document.addEventListener('click', function (e) {
      const toggle = e.target.closest && e.target.closest('[data-ld-mode-toggle]');
      if (toggle) toggleScheme();
    });
    // Labels follow the UI language.
    document.addEventListener('languageChanged', renderAll);
    if (window.LinguaI18n && typeof window.LinguaI18n.init === 'function') {
      window.LinguaI18n.init().then(renderAll, function () {});
    }
  });

  window.LinguaTheme = {
    list: function () {
      return THEMES.map(function (t) {
        return Object.assign({}, t, { swatches: t.swatches.slice() });
      });
    },
    current: function () {
      return currentTheme;
    },
    setTheme: setTheme,
    apply: setTheme,
    mode: function () {
      return currentMode;
    },
    setMode: setMode,
    scheme: resolvedScheme,
    toggleScheme: toggleScheme,
    onChange: function (fn) {
      listeners.push(fn);
      return function () {
        const i = listeners.indexOf(fn);
        if (i !== -1) listeners.splice(i, 1);
      };
    },
    renderThemePicker: renderThemePicker,
    renderModePicker: renderModePicker,
  };
})();
