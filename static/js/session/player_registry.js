// static/js/session/player_registry.js
// Maps a queue item to the player module that renders it. Players expose
// mount(container, ctx) -> { destroy() } and call ctx.onComplete(result) when
// the user finishes, or ctx.onSkip() to advance without marking complete.

import { escapeHtml, applyI18n } from './dom.js';

// Players are loaded on demand (dynamic import), not all up front: the page
// used to fetch every player (~256 KB over a 4-level import chain) before it
// could even ask for today's session. `preloadPlayers(queue)` warms the ones a
// queue needs as soon as the queue is known.
const LOADERS = {
  reading_listening: () => import('./players/reading_listening.js'),
  dictation: () => import('./players/dictation.js'),
  pinyin: () => import('./players/pinyin.js'),
  pitch_accent: () => import('./players/pitch_accent.js'),
  classifier_drill: () => import('./players/classifier_drill.js'),
  practice: () => import('./players/practice.js'),
  flashcards: () => import('./players/flashcards.js'),
  dual_translation: () => import('./players/dual_translation.js'),
  speed_round: () => import('./players/speed_round.js'),
  prestudy: () => import('./players/prestudy.js'),
};

const _modules = {}; // name -> Promise<module>
function loadModule(name) {
  if (!_modules[name]) {
    _modules[name] = LOADERS[name]().catch((err) => {
      delete _modules[name]; // let a later mount retry
      throw err;
    });
  }
  return _modules[name];
}

// A synchronous mount(container, ctx) -> { destroy() } whose real player is
// imported first. destroy() before the import lands cancels the mount.
function lazyPlayer(name) {
  return function mount(container, ctx) {
    let handle = null;
    let destroyed = false;
    container.innerHTML =
      '<div class="text-center py-5" data-player-loading>' +
      '<div class="spinner-border text-primary" role="status"></div></div>';
    loadModule(name)
      .then((mod) => {
        if (destroyed) return;
        container.innerHTML = '';
        handle = mod.mount(container, ctx);
        // The controller translates the stage right after mount(); the real
        // markup arrives later, so translate it here as well.
        applyI18n(container);
      })
      .catch((err) => {
        if (destroyed) return;
        console.error('[session] player failed to load:', name, err);
        placeholderPlayer({
          title: 'Could not load this exercise',
          message: 'Check your connection, then reload the page or skip it for now.',
          href: null,
        })(container, ctx);
      });
    return {
      destroy() {
        destroyed = true;
        if (handle && typeof handle.destroy === 'function') handle.destroy();
      },
    };
  };
}

const mountReadingListening = lazyPlayer('reading_listening');
const mountDictation = lazyPlayer('dictation');
const mountPinyin = lazyPlayer('pinyin');
const mountPitchAccent = lazyPlayer('pitch_accent');
const mountClassifierDrill = lazyPlayer('classifier_drill');
const mountPractice = lazyPlayer('practice');
const mountFlashcards = lazyPlayer('flashcards');
const mountDualTranslation = lazyPlayer('dual_translation');
const mountSpeedRound = lazyPlayer('speed_round');
const mountPrestudy = lazyPlayer('prestudy');

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
  // Test prestudy block before a hard new test or a retry slot
  // (wiki/features/test-prestudy.md). Opens the prestudy page, which completes
  // the block and returns to the session.
  prestudy: mountPrestudy,
};

const STANDALONE_URL = {
  dictation: (slug) => `/test/${slug}/dictation`,
  pinyin: (slug) => `/test/${slug}/pinyin`,
  pitch_accent: (slug) => `/test/${slug}/pitch-accent`,
};

// test_type / kind -> module name, for preloading.
const TEST_MODULES = {
  reading: 'reading_listening',
  listening: 'reading_listening',
  dictation: 'dictation',
  pinyin: 'pinyin',
  pitch_accent: 'pitch_accent',
  classifier_drill: 'classifier_drill',
};
const KIND_MODULES = {
  practice: 'practice',
  flashcards: 'flashcards',
  dual_translation: 'dual_translation',
  speed_round: 'speed_round',
  prestudy: 'prestudy',
};

const moduleNameFor = (item) =>
  (item && (KIND_MODULES[item.kind] || TEST_MODULES[item.test_type])) || null;

// Start importing the players a queue will need, without blocking anything.
export function preloadPlayers(items) {
  const names = new Set();
  (items || []).forEach((item) => {
    const name = moduleNameFor(item);
    if (name) names.add(name);
  });
  names.forEach((name) => loadModule(name).catch(() => {}));
}

// Ask an upcoming item's player to start loading its data. A player opts in by
// exporting `prefetch(item, ctx)`, with ctx = { languageId, current } where
// `current` is the item in progress (null before the session starts); it
// returns a promise the player's mount() later takes from `item.prefetch`, or
// nothing when loading early would be wrong (e.g. the payload depends on
// answers still being given). Called at most once per item. Resolves to the
// player module (or null), never rejects.
export function prefetchItem(item, ctx) {
  const name = moduleNameFor(item);
  if (!name || item.is_completed) return Promise.resolve(null);
  return loadModule(name)
    .then((mod) => {
      if (typeof mod.prefetch === 'function' && !item._prefetched && !item.prefetch) {
        item._prefetched = true;
        try {
          const pending = mod.prefetch(item, ctx || {});
          if (pending) item.prefetch = pending;
        } catch (err) {
          console.warn('[session] prefetch failed:', name, err);
        }
      }
      return mod;
    })
    .catch(() => null);
}

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
