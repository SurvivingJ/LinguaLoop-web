import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, it, expect } from 'vitest';

// Pins that every test/drill submit body carries both timing keys (TASK-894).
// Server rejects one-sided windows, so both must be present everywhere.
const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const FILES = [
  'static/js/session/players/reading_listening.js',
  'static/js/session/players/dictation.js',
  'static/js/session/players/pinyin.js',
  'static/js/session/players/pitch_accent.js',
  'static/js/session/players/classifier_drill.js',
  'templates/test.html',
  'templates/test_dictation.html',
  'templates/test_pinyin.html',
  'templates/test_pitch_accent.html',
  'templates/classifier_drill.html',
  'templates/counter_drill.html',
];

describe('test/drill submit payloads include started_at and finished_at', () => {
  for (const f of FILES) {
    it(f, () => {
      const src = readFileSync(join(root, f), 'utf8');
      expect(src).toMatch(/started_at\s*:/);
      expect(src).toMatch(/finished_at\s*:/);
    });
  }
});
