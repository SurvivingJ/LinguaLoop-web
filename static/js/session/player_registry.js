// static/js/session/player_registry.js
// Maps a queue item to the player module that renders it. Players expose
// mount(container, ctx) -> { destroy() } and call ctx.onComplete(result) when
// the user finishes, or ctx.onSkip() to advance without marking complete.

import { mount as mountReadingListening } from './players/reading_listening.js';
import { mount as mountDictation } from './players/dictation.js';
import { mount as mountPinyin } from './players/pinyin.js';
import { mount as mountPitchAccent } from './players/pitch_accent.js';
import { mount as mountPractice } from './players/practice.js';

// test_type -> mount fn. Phase 2/3 add dictation / pinyin / pitch_accent /
// practice. Until then those fall through to a placeholder that links to the
// existing standalone page.
const TEST_PLAYERS = {
  reading: mountReadingListening,
  listening: mountReadingListening,
  dictation: mountDictation,
  pinyin: mountPinyin,
  pitch_accent: mountPitchAccent,
};

const STANDALONE_URL = {
  dictation: (slug) => `/test/${slug}/dictation`,
  pinyin: (slug) => `/test/${slug}/pinyin`,
  pitch_accent: (slug) => `/test/${slug}/pitch-accent`,
};

export function getPlayer(item) {
  if (item.kind === 'practice') {
    return { mount: mountPractice };
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
