import js from '@eslint/js';
import globals from 'globals';

// Flat config (ESLint 9). Scope: static/js only — the inline <script> blocks in
// Jinja templates are NOT linted here because they contain `{{ }}`/`{% %}` syntax
// that is not valid JavaScript. Those are migrated to shared modules in Phase 3.
export default [
  {
    ignores: ['node_modules/**', 'venv/**', 'Portal/**'],
  },
  js.configs.recommended,
  {
    files: ['static/js/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
      globals: {
        ...globals.browser,
        // Cross-file globals defined by sibling static/js modules and CDN libs.
        LINGUADOJO: 'readonly',
        LinguaUtils: 'writable',
        LinguaMetadata: 'writable',
        authFetch: 'readonly',
        bootstrap: 'readonly',
      },
    },
    rules: {
      // Best-effort cleanup (audio.pause, storage, etc.) deliberately swallows errors.
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-var': 'error',
      'prefer-const': 'error',
      // debugLog() wraps console; allow intentional warn/error, flag stray log/debug/info.
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      eqeqeq: ['warn', 'smart'],
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    },
  },
  {
    // ES modules (import/export) — everything else in static/js is a classic script.
    files: ['static/js/session/**/*.js'],
    // LinguaI18n is declared by dt-error-card.js / exercise-renderers.js; the session modules read it as a global.
    languageOptions: { sourceType: 'module', globals: { LinguaI18n: 'readonly' } },
  },
  {
    // Tooling and tests run under Node / vitest (jsdom), not the browser-script environment.
    files: ['playwright.config.js', 'tests/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.node, ...globals.browser, ...globals.vitest },
    },
  },
];
