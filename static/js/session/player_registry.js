// static/js/session/player_registry.js
// Maps a queue item to the player module that renders it. Players expose
// mount(container, ctx) -> { destroy() } and call ctx.onComplete(result) when
// the user finishes, or ctx.onSkip() to advance without marking complete.

import { mount as mountReadingListening } from './players/reading_listening.js';
import { mount as mountDictation } from './players/dictation.js';
import { mount as mountPinyin } from './players/pinyin.js';
import { mount as mountPitchAccent } from './players/pitch_accent.js';
import { mount as mountClassifierDrill } from './players/classifier_drill.js';
import { mount as mountPractice } from './players/practice.js';
import { mount as mountFlashcards } from './players/flashcards.js';
import { mount as mountDualTranslation } from './players/dual_translation.js';
import { mount as mountSpeedRound } from './players/speed_round.js';

// test_type -> mount fn. Phase 2/3 add dictation / pinyin / pitch_accent /
// classifier_drill / practice. Anything still unmapped falls through to a
// placeholder that links to the existing standalone page.
const TEST_PLAYERS = {
  reading: mountReadingListening,
  listening: mountReadingListening,
  dictation: mountDictation,
  pinyin: mountPinyin,
  pitch_accent: mountPitchAccent,
  classifier_drill: mountClassifierDrill,
};

// Non-test queue kinds (TASK-714 / ADR-021). flashcards and dual_translation
// are plannable SURFACES, not test types — no `tests` row, no ELO — so they
// dispatch on item.kind rather than item.test_type. Widening this union is
// what let the planner budget them without pretending they are tests.
//
// listening_lab and mystery are deliberately absent: ADR-021 puts them outside
// the planner, so the resolver never emits them and nothing here should invite
// a future contributor to add them.
const KIND_PLAYERS = {
  practice: mountPractice,
  flashcards: mountFlashcards,
  dual_translation: mountDualTranslation,
  // TASK-533. A kind, not a test_type and not a ladder level: its capability
  // row carries ladder_level = NULL precisely so it stays out of the drill
  // rotation and is reachable only when something schedules it explicitly.
  speed_round: mountSpeedRound,
};

const STANDALONE_URL = {
  dictation: (slug) => `/test/${slug}/dictation`,
  pinyin: (slug) => `/test/${slug}/pinyin`,
  pitch_accent: (slug) => `/test/${slug}/pitch-accent`,
};

export function getPlayer(item) {
  const byKind = KIND_PLAYERS[item.kind];
  if (byKind) {
    return { mount: byKind };
  }

  const mount = TEST_PLAYERS[item.test_type];
  if (mount) return { mount };

  const href = STANDALONE_URL[item.test_type] ? STANDALONE_URL[item.test_type](item.slug) : null;
  return {
    mount: placeholderPlayer({
      title: capitalize(item.test_type || 'Exercise'),
      message: 'This exercise type isn’t available inside the session yet.',
      href,
    }),
  };
}

// A minimal player used for not-yet-ported item types: shows a card with an
// optional link to the standalone page and a "Skip for now" button.
function placeholderPlayer({ title, message, href }) {
  return function mount(container, ctx) {
    container.innerHTML = `
            <div class="session-card"><div class="card"><div class="card-body p-4 text-center">
                <h2 class="h5 mb-2">${escapeHtml(title)}</h2>
                <p class="text-muted">${escapeHtml(message)}</p>
                ${href ? `<a class="btn btn-outline-primary me-2" href="${href}">Open page</a>` : ''}
                <button class="btn btn-secondary" type="button" data-session-skip>Skip for now</button>
            </div></div></div>`;
    const skip = container.querySelector('[data-session-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
    return {
      destroy() {
        /* nothing to clean up */
      },
    };
  };
}

function capitalize(s) {
  s = String(s || '');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}
