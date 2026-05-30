/**
 * Vitest setup: load browser-global scripts into the jsdom context.
 *
 * utils.js and exercise-renderers.js are plain <script> files that assign to
 * window.LinguaUtils / window.ExRenderers.  Running them via eval() in this
 * setup file populates those globals before each test file runs.
 *
 * eval() is intentional here — these are non-module browser scripts and this
 * is the production-safe way to exercise them in a jsdom environment without
 * modifying the production files themselves (beyond the one-line
 * `window.ExRenderers = ExRenderers` already added for this purpose).
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..', '..');

function loadBrowserScript(relPath) {
  const code = readFileSync(join(root, relPath), 'utf8');
  // eslint-disable-next-line no-eval
  eval(code);
}

// Order matters: exercise-renderers.js delegates to window.LinguaUtils.escapeHtml
loadBrowserScript('static/js/utils.js');
loadBrowserScript('static/js/exercise-renderers.js');
