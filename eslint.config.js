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
      'no-var': 'error',
      'prefer-const': 'error',
      // debugLog() wraps console; allow intentional warn/error, flag stray log/debug/info.
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      eqeqeq: ['warn', 'smart'],
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    },
  },
];
