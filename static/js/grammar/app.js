// static/js/grammar/app.js
// Grammar drills (/grammar-drill): the screens. Hub -> topic (guide) -> drill
// round, endless stream or mixed review -> results. One task per screen: each
// screen is .ld-screen > strip + scrolling .ld-stage + pinned .ld-dock.
//
// Content is static JSON (data.js); progress is local (store.js); the rules
// are in pure modules (ladder.js, select.js, round.js, check.js, text.js).
// Styles: static/css/redesign/grammar.css (.gd).
//
// Locations (location.hash): '' hub, '#<slug>' topic, '#<slug>/drill',
// '#<slug>/endless' and '#mixed' a running session (a reload falls back to the
// topic or the hub: sessions are not restored).

import { escapeHtml, applyI18n, nowMs } from '../session/dom.js';
import { loadGenerators, loadManifest, loadTopic } from './data.js';
import {
  checkCloze,
  checkJudge,
  checkOrder,
  checkTyped,
  correctSentence,
  rightOption,
} from './check.js';
import {
  LAST_STAGE,
  STAGES,
  UNLOCK_ACC,
  WINDOW,
  isInstant,
  nextSpeedBase,
  speedLimit,
  stageDef,
  stageStats,
  topicStatus,
} from './ladder.js';
import { createRound } from './round.js';
import { mixedTopics, pickMixed, pickRound, recommendTopic, ROUND_SIZE } from './select.js';
import { createStore } from './store.js';
import { EMPTY, clozeSegments, guessPinyin, readingMap, seconds, tokenPinyin } from './text.js';
import {
  clozeHtml,
  guideHtml,
  hasPinyin,
  nothingLabel,
  optionLabel,
  sentenceHtml,
  t,
} from './render.js';

/** Right answer on the speed stage: move on by itself after this long. */
const AUTO_NEXT_MS = 800;
/** Endless mode: static items are drawn this many at a time. */
const ENDLESS_BATCH = 10;

const STAGE_NAMES = { recognise: 'Recognise', build: 'Build', recall: 'Recall', speed: 'Speed' };
const stageName = (key) => t('stage_' + key, null, STAGE_NAMES[key] || key);
const pct = (x) => Math.round(x * 100);

function shuffleWith(list, rng) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Mount the app in `root`. `opts.manifestUrl` is the versioned URL of
 * manifest.json and `opts.generatorsUrl` (default: root's data-generators)
 * that of the optional generators module; `opts.store`, `opts.rng` and
 * `opts.generators` (a slug -> list function) can be injected by tests. Returns { destroy() }.
 */
export function mountGrammar(root, opts = {}) {
  const store = opts.store || createStore();
  const rng = opts.rng || Math.random;
  const manifestUrl = opts.manifestUrl || root.dataset.manifest || '';
  const shell = () => window.LinguaShell || null;

  let manifest = null;
  let topics = new Map();
  let generatorsFor = () => [];
  let session = null; // the running round / endless stream / mixed review
  let results = null; // the finished session's summary, while its screen shows
  let alive = true;
  let drawn = ''; // which screen root holds: 'hub' | 'topic:<slug>' | 'drill' | 'results'

  // ------------------------------------------------------------------ shell
  function header(o) {
    const sh = shell();
    if (sh && sh.setTaskHeader) sh.setTaskHeader(o);
  }

  function message(text, retry) {
    drawn = 'msg';
    root.innerHTML =
      '<div class="ld-screen gd"><div class="ld-stage gd-stage"><div class="gd-msg">' +
      '<p>' +
      escapeHtml(text) +
      '</p>' +
      (retry
        ? '<button type="button" class="ld-btn ld-btn--ghost" data-act="retry">' +
          escapeHtml(t('retry', null, 'Try again')) +
          '</button>'
        : '') +
      '</div></div></div>';
  }

  // ---------------------------------------------------------------- routing
  const parseHash = () => {
    const raw = decodeURIComponent((location.hash || '').replace(/^#\/?/, ''));
    const [slug, mode] = raw.split('/');
    return { slug: slug || '', mode: mode || '' };
  };

  function go(hash, replace) {
    const url = location.pathname + location.search + (hash ? '#' + hash : '');
    try {
      if (replace) history.replaceState(history.state, '', url);
      else history.pushState({ gd: true }, '', url);
    } catch {}
    route();
  }

  /** One step up: session -> topic (or hub for mixed), topic -> hub. */
  function parentHash() {
    const { slug, mode } = parseHash();
    if (!slug) return null;
    if (slug === 'mixed' || !mode) return '';
    return slug;
  }

  function back() {
    const parent = parentHash();
    if (parent === null) return false; // hub: let the shell leave the page
    if (history.state && history.state.gd) history.back();
    else go(parent, true);
    return true;
  }

  function route() {
    if (!alive || !manifest) return;
    const { slug, mode } = parseHash();
    const inSession =
      session &&
      ((slug === 'mixed' && session.kind === 'mixed') ||
        (session.slug === slug &&
          ((mode === 'drill' && session.kind === 'round') ||
            (mode === 'endless' && session.kind === 'endless'))));
    if (inSession) {
      if (results) drawResults();
      else drawDrill();
      return;
    }
    endSession();
    if (slug === 'mixed' || !topics.has(slug)) {
      if (slug) {
        go('', true);
        return;
      }
      drawHub();
      return;
    }
    if (mode) {
      go(slug, true);
      return;
    }
    openTopic(slug);
  }

  // -------------------------------------------------------------------- hub
  function statLine(topic, view) {
    const bits = [];
    if (topic.count) bits.push(t('items_n', { count: topic.count }, '{count} items'));
    else if (generatorsFor(topic.slug).length) {
      bits.push(t('endless_only', null, 'Endless practice'));
    } else bits.push(t('guide_only', null, 'Guide only for now'));
    if (view.seq) {
      const s = stageStats(view.results[view.stage]);
      if (s.n) {
        bits.push(pct(s.acc) + '%');
        bits.push(t('seconds', { n: seconds(s.medianMs) }, '{n} s'));
      }
    } else if (view.endless.answers) {
      bits.push(pct(view.endless.correct / view.endless.answers) + '%');
    }
    return bits.join(' · ');
  }

  function statusTag(view) {
    const status = topicStatus(view);
    if (status === 'new') return '';
    if (status === 'instant') {
      return (
        '<span class="ld-tag ld-tag--ok">' + escapeHtml(t('instant', null, 'Instant')) + '</span>'
      );
    }
    if (!view.seq) return '';
    return (
      '<span class="ld-tag ld-tag--brand">' +
      escapeHtml(view.stage + ' · ' + stageName(status)) +
      '</span>'
    );
  }

  function glyphHtml(zh, cls) {
    const len = Array.from(String(zh || '')).length;
    const size = len <= 1 ? 'one' : len <= 3 ? 'few' : 'many';
    return (
      '<span class="' +
      cls +
      ' gd-glyph gd-glyph--' +
      size +
      '" lang="zh" aria-hidden="true">' +
      escapeHtml(zh || '') +
      '</span>'
    );
  }

  function settingsHtml() {
    const s = store.settings();
    const row = (name, on, label, sub) =>
      '<div class="ld-set gd-set"><span><b>' +
      escapeHtml(label) +
      '</b><small>' +
      escapeHtml(sub) +
      '</small></span><button type="button" class="ld-switch" role="switch" aria-checked="' +
      (on ? 'true' : 'false') +
      '" data-act="setting" data-name="' +
      name +
      '" aria-label="' +
      escapeHtml(label) +
      '"></button></div>';
    return (
      '<section class="ld-card ld-card--list gd-settings">' +
      row(
        'pinyin',
        s.pinyin,
        t('set_pinyin', null, 'Always show pinyin'),
        t('set_pinyin_sub', null, 'Off: pinyin appears only when you ask (P)')
      ) +
      row(
        'typing',
        s.typing,
        t('set_typing', null, 'Type answers'),
        t('set_typing_sub', null, 'At Recall and Speed, type the missing word instead')
      ) +
      '</section>'
    );
  }

  function drawHub() {
    drawn = 'hub';
    header({
      title: t('title', null, 'Grammar Drills'),
      subtitle: t('subtitle', null, 'One point at a time, until it is instant'),
      glyph: '法',
      end: '',
    });
    const list = manifest.topics || [];
    const next = recommendTopic(list, store);
    const canMix = mixedTopics(list, store).length > 0;
    const started = store.practised().length > 0;
    const parts = [];
    if (next) {
      const view = store.topic(next.slug);
      parts.push(
        '<section class="ld-hero gd-hero">' +
          '<span class="ld-hero__wm" lang="zh" aria-hidden="true">' +
          escapeHtml(next.zh || '') +
          '</span>' +
          '<p class="ld-eyebrow">' +
          escapeHtml(
            started ? t('continue_with', null, 'Up next') : t('start_with', null, 'Start here')
          ) +
          '</p>' +
          '<h2 class="ld-h1 gd-hero__title" lang="zh">' +
          escapeHtml(next.title) +
          '</h2>' +
          '<p class="ld-hero__sub">' +
          escapeHtml(statLine(next, view)) +
          '</p>' +
          '<div class="ld-row gd-hero__row">' +
          '<button type="button" class="ld-btn" data-act="continue" data-slug="' +
          escapeHtml(next.slug) +
          '">' +
          escapeHtml(started ? t('continue', null, 'Continue') : t('start', null, 'Start')) +
          '</button>' +
          '<button type="button" class="ld-btn ld-btn--ghost" data-act="mixed"' +
          (canMix ? '' : ' disabled') +
          '>' +
          escapeHtml(t('mixed', null, 'Mixed review')) +
          '</button></div>' +
          (canMix
            ? ''
            : '<p class="ld-hero__sub gd-hero__hint">' +
              escapeHtml(
                t('mixed_hint', null, 'Mixed review opens once you have practised a topic.')
              ) +
              '</p>') +
          '</section>'
      );
    }
    (manifest.categories || []).forEach((cat) => {
      const inCat = list.filter((tp) => tp.cat === cat.key);
      if (!inCat.length) return;
      parts.push(
        '<section class="gd-cat"><h2 class="ld-h2 gd-cat__title" lang="zh">' +
          escapeHtml(cat.title) +
          '</h2><div class="gd-grid">' +
          inCat
            .map((tp) => {
              const view = store.topic(tp.slug);
              return (
                '<button type="button" class="ld-card gd-topic" data-act="topic" data-slug="' +
                escapeHtml(tp.slug) +
                '">' +
                glyphHtml(tp.zh, 'gd-topic__zh') +
                '<span class="gd-topic__body"><b lang="zh">' +
                escapeHtml(tp.title) +
                '</b><small>' +
                escapeHtml(statLine(tp, view)) +
                '</small></span>' +
                statusTag(view) +
                '</button>'
              );
            })
            .join('') +
          '</div></section>'
      );
    });
    parts.splice(next ? 1 : 0, 0, settingsHtml());
    root.innerHTML =
      '<div class="ld-screen gd gd--hub"><div class="ld-stage gd-stage">' +
      parts.join('') +
      '</div></div>';
  }

  // ------------------------------------------------------------------ topic
  async function fetchTopic(slug) {
    const data = await loadTopic(manifestUrl, topics.get(slug));
    if (!data.readings) data.readings = readingMap(data.items);
    return data;
  }

  async function openTopic(slug) {
    const meta = topics.get(slug);
    drawn = 'topic:' + slug;
    header({
      title: meta.title,
      subtitle: t('title', null, 'Grammar Drills'),
      glyph: firstGlyph(meta),
      end: '',
    });
    root.innerHTML =
      '<div class="ld-screen gd"><div class="ld-stage gd-stage"><div class="gd-msg">' +
      escapeHtml(t('loading', null, 'Loading…')) +
      '</div></div></div>';
    let data;
    try {
      data = await fetchTopic(slug);
    } catch {
      if (alive && drawn === 'topic:' + slug) {
        message(t('error_topic', null, 'Could not load this topic. Check your connection.'), true);
      }
      return;
    }
    if (!alive || drawn !== 'topic:' + slug) return;
    drawTopic(slug, data);
  }

  const firstGlyph = (meta) => Array.from(String(meta.zh || '法'))[0];

  function stagePickerHtml(view) {
    return (
      '<div class="gd-stages" role="group" aria-label="' +
      escapeHtml(t('stage', null, 'Stage')) +
      '">' +
      STAGES.map((s) => {
        const locked = s.n > view.unlocked;
        const st = stageStats(view.results[s.n]);
        const sub = locked
          ? t('locked', null, 'Locked')
          : st.n
            ? pct(st.acc) + '% · ' + t('seconds', { n: seconds(st.medianMs) }, '{n} s')
            : t('stage_' + s.key + '_sub', null, STAGE_SUBS[s.key]);
        return (
          '<button type="button" class="gd-stagebtn' +
          (s.n === view.stage ? ' is-on' : '') +
          '" data-act="stage" data-n="' +
          s.n +
          '" aria-pressed="' +
          (s.n === view.stage ? 'true' : 'false') +
          '"' +
          (locked ? ' disabled' : '') +
          '><span class="gd-stagebtn__n">' +
          s.n +
          '</span><b>' +
          escapeHtml(stageName(s.key)) +
          '</b><small>' +
          escapeHtml(sub) +
          '</small></button>'
        );
      }).join('') +
      '</div>'
    );
  }

  const STAGE_SUBS = {
    recognise: 'Pick the right form',
    build: 'Build sentences',
    recall: 'Recall, then confirm',
    speed: 'Against the clock',
  };

  function unlockNoteHtml(view) {
    if (isInstant(view)) {
      return (
        '<p class="gd-note gd-note--ok">' +
        escapeHtml(t('instant_note', null, 'Instant: fast and accurate at the Speed stage.')) +
        '</p>'
      );
    }
    if (view.stage < view.unlocked) return '';
    const st = stageStats(view.results[view.stage].slice(-WINDOW));
    if (view.stage === LAST_STAGE) {
      return (
        '<p class="gd-note">' +
        escapeHtml(
          t(
            'instant_rule',
            null,
            'Instant = 90% of your last 30 Speed answers right, median under 3 s.'
          )
        ) +
        '</p>'
      );
    }
    return (
      '<p class="gd-note">' +
      escapeHtml(
        t(
          'unlock_rule',
          {
            have: st.n,
            need: WINDOW,
            pct: pct(UNLOCK_ACC),
            next: stageName(stageDef(view.stage + 1).key),
          },
          '{next} opens at {pct}% over your last {need} answers here ({have} so far).'
        )
      ) +
      '</p>'
    );
  }

  function drawTopic(slug, data) {
    const meta = topics.get(slug);
    const view = store.topic(slug);
    const gens = generatorsFor(slug);
    const hasItems = data.items.length > 0;
    header({
      title: meta.title,
      subtitle: t('title', null, 'Grammar Drills'),
      glyph: firstGlyph(meta),
      end: '',
    });
    const dock = [];
    if (hasItems) {
      dock.push(
        '<button type="button" class="ld-btn" data-act="start">' +
          escapeHtml(
            t('start_stage', { stage: stageName(stageDef(view.stage).key) }, 'Start · {stage}')
          ) +
          '</button>'
      );
    }
    if (gens.length) {
      dock.push(
        '<button type="button" class="ld-btn' +
          (hasItems ? ' ld-btn--ghost' : '') +
          '" data-act="endless">' +
          escapeHtml(t('endless', null, 'Endless')) +
          '</button>'
      );
    }
    root.innerHTML =
      '<div class="ld-screen gd gd--topic' +
      (store.settings().pinyin ? ' is-py' : '') +
      '"><div class="ld-stage gd-stage">' +
      '<div class="gd-topichead">' +
      glyphHtml(meta.zh, 'gd-topichead__zh') +
      '<div><h1 class="ld-h1" lang="zh">' +
      escapeHtml(meta.title) +
      '</h1><p class="ld-muted ld-small">' +
      escapeHtml(statLine(meta, view)) +
      '</p></div></div>' +
      (hasItems ? stagePickerHtml(view) + unlockNoteHtml(view) : '') +
      (!hasItems && !gens.length
        ? '<p class="gd-note">' +
          escapeHtml(t('no_items', null, 'Drill items for this topic are not ready yet.')) +
          '</p>'
        : '') +
      '<div class="gd-guidebar"><h2 class="ld-h2">' +
      escapeHtml(t('guide', null, 'Guide')) +
      '</h2>' +
      pinyinButtonHtml(store.settings().pinyin, true) +
      '</div>' +
      guideHtml(data.guide) +
      '</div>' +
      (dock.length
        ? '<div class="ld-dock gd-dock"><div class="ld-row">' + dock.join('') + '</div></div>'
        : '') +
      '</div>';
  }

  function pinyinButtonHtml(on, usable) {
    return (
      '<button type="button" class="ld-chip gd-pybtn" data-act="py" aria-pressed="' +
      (on ? 'true' : 'false') +
      '"' +
      (usable ? '' : ' disabled') +
      ' title="P"><span lang="zh" aria-hidden="true">拼</span> ' +
      escapeHtml(t('pinyin', null, 'Pinyin')) +
      '</button>'
    );
  }

  // --------------------------------------------------------------- sessions
  function clearTimers() {
    if (!session) return;
    clearTimeout(session.timer);
    clearTimeout(session.auto);
    session.timer = session.auto = null;
  }

  function endSession() {
    clearTimers();
    session = null;
    results = null;
  }

  async function startRound(slug) {
    let data;
    try {
      data = await fetchTopic(slug);
    } catch {
      message(t('error_topic', null, 'Could not load this topic. Check your connection.'), true);
      return;
    }
    if (!alive) return;
    const view = store.topic(slug);
    const items = pickRound({ items: data.items, slug, topic: view, stage: view.stage, rng });
    if (!items.length) return;
    endSession();
    session = {
      kind: 'round',
      slug,
      stage: view.stage,
      data: new Map([[slug, data]]),
      round: createRound(items.map((item) => ({ slug, item }))),
      speedBase: view.speedMs,
      unlocked: 0,
    };
    beginItem();
    go(slug + '/drill', parseHash().mode === 'drill');
  }

  async function startEndless(slug) {
    const gens = generatorsFor(slug);
    if (!gens.length) return;
    let data;
    try {
      data = await fetchTopic(slug);
    } catch {
      message(t('error_topic', null, 'Could not load this topic. Check your connection.'), true);
      return;
    }
    if (!alive) return;
    endSession();
    let pool = [];
    const more = () => {
      const view = store.topic(slug);
      const useStatic = data.items.length > 0 && rng() < 0.5;
      if (useStatic) {
        if (!pool.length) {
          pool = pickRound({
            items: data.items,
            slug,
            topic: view,
            stage: view.stage,
            size: ENDLESS_BATCH,
            rng,
          });
        }
        if (pool.length) return { slug, item: pool.shift() };
      }
      for (let tries = 0; tries < 5; tries++) {
        const gen = gens[Math.floor(rng() * gens.length)];
        try {
          const item = gen.make(rng);
          if (item && item.type) return { slug, item, generated: true };
        } catch {}
      }
      return pool.length ? { slug, item: pool.shift() } : null;
    };
    session = {
      kind: 'endless',
      slug,
      stage: store.topic(slug).stage,
      data: new Map([[slug, data]]),
      round: createRound([], { more }),
      unlocked: 0,
    };
    if (!session.round.current()) {
      session = null;
      return;
    }
    beginItem();
    go(slug + '/endless', parseHash().mode === 'endless');
  }

  async function startMixed() {
    const list = mixedTopics(manifest.topics || [], store);
    if (!list.length) return;
    let loaded;
    try {
      loaded = await Promise.all(list.map((tp) => fetchTopic(tp.slug)));
    } catch {
      message(t('error_topic', null, 'Could not load this topic. Check your connection.'), true);
      return;
    }
    if (!alive) return;
    const parts = list.map((tp, k) => ({
      slug: tp.slug,
      items: loaded[k].items,
      topic: store.topic(tp.slug),
    }));
    const entries = pickMixed(parts, ROUND_SIZE, rng);
    if (!entries.length) return;
    endSession();
    session = {
      kind: 'mixed',
      slug: 'mixed',
      stage: 0,
      data: new Map(list.map((tp, k) => [tp.slug, loaded[k]])),
      round: createRound(entries),
      unlocked: 0,
    };
    beginItem();
    go('mixed', parseHash().slug === 'mixed');
  }

  /** The stage whose rules draw the current item. */
  function itemStage(entry) {
    if (session.kind === 'mixed') return stageDef(store.topic(entry.slug).stage);
    return stageDef(session.stage);
  }

  /** Set up the per-item state for round.current(). */
  function beginItem() {
    clearTimers();
    const cur = session.round.current();
    if (!cur) return;
    const { item, slug } = cur.entry;
    const def = itemStage(cur.entry);
    const data = session.data.get(slug);
    const state = {
      entry: cur.entry,
      item,
      retry: cur.retry,
      def,
      py: store.settings().pinyin,
      answered: null,
      startedAt: nowMs(),
      limitMs: 0,
    };
    if (item.type === 'cloze') {
      // Generated items show their options at once.
      const recall = def.recall && !cur.entry.generated && Array.isArray(item.opts);
      // Recall, then confirm: the item's own options stay hidden until the
      // learner has thought of the answer and asks for them (or types it).
      state.options = (item.opts || []).slice();
      state.typing = recall && store.settings().typing;
      state.hidden = recall && !state.typing;
      state.revealMs = 0;
    } else if (item.type === 'order' || item.type === 'rewrite') {
      const own = tokenPinyin(item.tokens, item.py);
      const extra = (item.extra || []).map((x) => guessPinyin(x, data.readings));
      const pys = own && extra.every(Boolean) ? [...own, ...extra] : null;
      const tiles = [...(item.tokens || []), ...(item.extra || [])].map((text, k) => ({
        text,
        py: pys ? pys[k] : '',
      }));
      let order = shuffleWith(tiles, rng);
      for (
        let k = 0;
        k < 5 &&
        checkOrder(
          item,
          order.map((x) => x.text)
        );
        k++
      ) {
        order = shuffleWith(tiles, rng);
      }
      state.tiles = order;
      state.placed = []; // indexes into state.tiles, in the learner's order
    }
    if (def.timed && session.kind === 'round') {
      state.limitMs = speedLimit(session.speedBase, item);
      session.timer = setTimeout(() => submit(false, { timeout: true }), state.limitMs);
    }
    session.pausedAt = 0;
    session.cur = state;
  }

  function itemHasPinyin(state) {
    const it = state.item;
    if (it.type === 'cloze') return clozeSegments(it).some((seg) => seg.pairs && seg.pairs.length);
    if (state.answered) {
      return hasPinyin(correctSentence(it), it.py) || hasPinyin(it.s, it.s_py || it.py);
    }
    if (it.type === 'judge') return hasPinyin(it.s, it.s_py || it.py);
    if (it.type === 'rewrite' && hasPinyin(it.src, it.src_py)) return true;
    return (state.tiles || []).some((x) => x.py);
  }

  function submit(ok, detail) {
    if (!session || !session.cur || session.cur.answered) return;
    const state = session.cur;
    resumeClock();
    const timeout = !!(detail && detail.timeout);
    const totalMs = timeout ? state.limitMs : Math.round(nowMs() - state.startedAt);
    // The recall time is what counts at a recall cloze: up to "Show choices".
    const ms = !timeout && state.revealMs ? state.revealMs : totalMs;
    clearTimers();
    state.hidden = false;
    const { first } = session.round.answer(ok, ms);
    state.answered = { ok, ms, totalMs, ...(detail || {}) };
    if (first) record(state, ok, ms, totalMs);
    drawDrill();
    if (ok && state.limitMs) {
      session.auto = setTimeout(next, AUTO_NEXT_MS);
    }
  }

  function record(state, ok, ms, totalMs) {
    const { slug, item, generated } = state.entry;
    if (session.kind === 'round') {
      const { unlocked } = store.record(slug, {
        id: item.id,
        stage: session.stage,
        ok,
        ms,
        totalMs,
      });
      if (unlocked) session.unlocked = unlocked;
      if (state.limitMs) {
        session.speedBase = nextSpeedBase(session.speedBase, ok, session.round.streak());
        store.setSpeed(slug, session.speedBase);
      }
    } else if (session.kind === 'mixed') {
      store.record(slug, { id: item.id, stage: null, ok, ms });
    } else {
      store.recordEndless(slug, ok, session.round.streak());
      if (!generated) store.record(slug, { id: item.id, stage: null, ok, ms });
    }
  }

  function next() {
    if (!session || !session.round.isAnswered()) return;
    clearTimers();
    if (session.round.next()) {
      beginItem();
      drawDrill();
    } else {
      finish();
    }
  }

  function finish() {
    if (!session) return;
    clearTimers();
    results = session.round.summary();
    drawResults();
  }

  // ------------------------------------------------------------------ drill
  function stripHtml(state) {
    const sum = session.round.summary();
    let left;
    if (session.kind === 'endless') {
      left =
        '<span class="gd-live"><b>' +
        escapeHtml(t('streak_n', { n: session.round.streak() }, 'Streak {n}')) +
        '</b>' +
        (sum.answers
          ? '<span>' +
            pct(sum.accuracy) +
            '%</span><span>' +
            escapeHtml(t('seconds', { n: seconds(sum.medianMs) }, '{n} s')) +
            '</span>'
          : '') +
        '</span>';
    } else {
      const p = session.round.progress();
      left =
        '<span class="gd-count ld-num">' +
        p.done +
        ' / ' +
        p.total +
        '</span>' +
        (session.kind === 'round'
          ? '<span class="ld-tag ld-tag--info">' + escapeHtml(stageName(state.def.key)) + '</span>'
          : '') +
        (state.retry
          ? '<span class="ld-tag ld-tag--warn">' +
            escapeHtml(t('again_tag', null, 'Again')) +
            '</span>'
          : '');
    }
    const p = session.round.progress();
    const bar =
      session.kind === 'endless'
        ? ''
        : '<div class="ld-bar gd-bar"><i style="width:' +
          (p.total ? Math.round((p.done / p.total) * 100) : 0) +
          '%"></i></div>';
    // The countdown is information, not decoration: its duration is set
    // !important so the reduced-motion reset in styles.css does not empty it.
    let timer = '';
    if (state.limitMs && !state.answered) {
      const elapsed = Math.max(0, Math.round(nowMs() - state.startedAt));
      timer =
        '<div class="gd-timer" aria-hidden="true"><i style="animation-duration:' +
        state.limitMs +
        'ms !important;animation-delay:-' +
        elapsed +
        'ms"></i></div>';
    }
    return (
      '<div class="gd-strip"><div class="gd-strip__row">' +
      left +
      '<span class="gd-strip__tools">' +
      pinyinButtonHtml(state.py, itemHasPinyin(state)) +
      '<button type="button" class="ld-chip" data-act="guide">' +
      escapeHtml(t('guide', null, 'Guide')) +
      '</button>' +
      (session.kind === 'endless'
        ? '<button type="button" class="ld-chip" data-act="stop">' +
          escapeHtml(t('stop', null, 'Stop')) +
          '</button>'
        : '') +
      '</span></div>' +
      bar +
      timer +
      '</div>'
    );
  }

  const cueHtml = (item) => {
    const cue = item.cue || item.en;
    return cue ? '<p class="gd-cue">' + escapeHtml(cue) + '</p>' : '';
  };

  function optionsHtml(state) {
    const a = state.answered;
    const right = rightOption(state.item);
    return (
      '<div class="gd-opts' +
      '" lang="zh">' +
      state.options
        .map((opt, k) => {
          let cls = 'gd-opt';
          if (a && opt === right) cls += ' is-right';
          else if (a && a.choice === opt) cls += ' is-wrong';
          return (
            '<button type="button" class="' +
            cls +
            '" data-act="opt" data-i="' +
            k +
            '"' +
            (a ? ' disabled' : '') +
            '><span class="gd-key" aria-hidden="true">' +
            (k + 1) +
            '</span><span class="gd-opt__text' +
            (opt.split('|').includes(EMPTY) ? ' gd-opt__text--none' : '') +
            '">' +
            escapeHtml(optionLabel(opt)) +
            '</span></button>'
          );
        })
        .join('') +
      '</div>'
    );
  }

  function typedHtml(state) {
    const a = state.answered;
    return (
      '<form class="gd-typed" data-form="typed" autocomplete="off">' +
      '<input type="text" class="gd-typed__input' +
      (a ? (a.ok ? ' is-right' : ' is-wrong') : '') +
      '" id="gdTyped" lang="zh" inputmode="text" autocapitalize="off" autocorrect="off" spellcheck="false" maxlength="12" aria-label="' +
      escapeHtml(t('typed_label', null, 'Your answer')) +
      '" placeholder="' +
      escapeHtml(t('typed_placeholder', null, 'Type the missing word')) +
      '"' +
      (a ? ' disabled value="' + escapeHtml(a.typed || '') + '"' : '') +
      '>' +
      (state.options.includes(EMPTY)
        ? '<button type="button" class="ld-chip" data-act="typed-none"' +
          (a ? ' disabled' : '') +
          '>' +
          escapeHtml(nothingLabel()) +
          '</button>'
        : '') +
      '</form>'
    );
  }

  function tilesHtml(state) {
    const a = state.answered;
    const tile = (k, act) => {
      const x = state.tiles[k];
      return (
        '<button type="button" class="gd-tile" data-act="' +
        act +
        '" data-i="' +
        k +
        '"' +
        (a ? ' disabled' : '') +
        '><span class="gd-tile__py">' +
        escapeHtml(x.py || '') +
        '</span><span class="gd-tile__text">' +
        escapeHtml(x.text) +
        '</span></button>'
      );
    };
    const built = state.placed.length
      ? state.placed.map((k) => tile(k, 'unplace')).join('')
      : '<span class="gd-built__hint">' +
        escapeHtml(t('order_hint', null, 'Tap the tiles in order')) +
        '</span>';
    const bank = state.tiles
      .map((x, k) =>
        state.placed.includes(k)
          ? '<span class="gd-tile gd-tile--used" aria-hidden="true"><span class="gd-tile__py">' +
            escapeHtml(x.py || '') +
            '</span><span class="gd-tile__text">' +
            escapeHtml(x.text) +
            '</span></span>'
          : tile(k, 'place')
      )
      .join('');
    return (
      '<div class="gd-built' +
      (a ? (a.ok ? ' is-right' : ' is-wrong') : '') +
      '" lang="zh" aria-label="' +
      escapeHtml(t('your_sentence', null, 'Your sentence')) +
      '">' +
      built +
      '</div><div class="gd-tiles" lang="zh">' +
      bank +
      '</div>'
    );
  }

  function itemHtml(state) {
    const it = state.item;
    const a = state.answered;
    const eyebrow = (text) => '<p class="ld-eyebrow gd-kind">' + escapeHtml(text) + '</p>';
    if (it.type === 'cloze') {
      return (
        eyebrow(t('kind_cloze', null, 'Fill the blank')) +
        '<p class="gd-sentence" lang="zh">' +
        clozeHtml(it, !!a) +
        '</p>' +
        cueHtml(it) +
        (state.typing
          ? typedHtml(state)
          : state.hidden
            ? '<p class="gd-recall">' +
              escapeHtml(
                t('recall_hint', null, 'Say the missing word to yourself, then show the choices.')
              ) +
              '</p>'
            : optionsHtml(state))
      );
    }
    if (it.type === 'judge') {
      const btn = (says, key, label, k) => {
        let cls = 'gd-opt gd-opt--judge';
        if (a && !!it.ok === says) cls += ' is-right';
        else if (a && a.says === says) cls += ' is-wrong';
        return (
          '<button type="button" class="' +
          cls +
          '" data-act="judge" data-ok="' +
          (says ? '1' : '0') +
          '"' +
          (a ? ' disabled' : '') +
          '><span class="gd-key" aria-hidden="true">' +
          k +
          '</span><span class="gd-opt__text gd-opt__text--none">' +
          escapeHtml(t(key, null, label)) +
          '</span></button>'
        );
      };
      return (
        eyebrow(t('kind_judge', null, 'Is this sentence correct?')) +
        '<p class="gd-sentence' +
        (a && !it.ok ? ' is-bad' : '') +
        '" lang="zh">' +
        sentenceHtml(it.s, it.s_py || it.py) +
        '</p>' +
        cueHtml(it) +
        '<div class="gd-opts gd-opts--two">' +
        btn(true, 'correct', 'Correct', 1) +
        btn(false, 'wrong', 'Wrong', 2) +
        '</div>'
      );
    }
    // order / rewrite
    const head =
      it.type === 'rewrite'
        ? eyebrow(t('kind_rewrite', null, 'Rewrite the sentence')) +
          '<p class="gd-src" lang="zh">' +
          sentenceHtml(it.src, it.src_py) +
          '</p>' +
          '<p class="gd-task">' +
          escapeHtml(it.task || '') +
          '</p>'
        : eyebrow(t('kind_order', null, 'Build the sentence'));
    return head + cueHtml(it) + tilesHtml(state);
  }

  function feedbackHtml(state) {
    const it = state.item;
    const a = state.answered;
    const zh = correctSentence(it);
    const title = a.ok
      ? t('fb_right', null, 'Correct')
      : a.timeout
        ? t('fb_timeout', null, 'Time is up')
        : t('fb_wrong', null, 'Not quite');
    const lines = [];
    if (!a.ok && it.type === 'cloze') {
      lines.push(
        '<p class="gd-fb__answer">' +
          escapeHtml(t('answer', null, 'Answer')) +
          ': <b lang="zh">' +
          escapeHtml(optionLabel(rightOption(it))) +
          '</b></p>'
      );
    }
    if (it.type === 'judge') {
      lines.push(
        '<p class="gd-fb__answer">' +
          escapeHtml(
            it.ok
              ? t('judge_was_ok', null, 'The sentence is correct.')
              : t('judge_was_bad', null, 'The sentence is wrong. Corrected:')
          ) +
          '</p>'
      );
    }
    const showSentence = zh && it.type !== 'cloze' && !(it.type === 'judge' && it.ok);
    if (showSentence) {
      lines.push('<p class="gd-fb__zh" lang="zh">' + sentenceHtml(zh, it.py) + '</p>');
    }
    if (it.en && (!a.ok || it.cue))
      lines.push('<p class="gd-fb__en">' + escapeHtml(it.en) + '</p>');
    if (!a.ok && it.why)
      lines.push('<p class="gd-fb__why" lang="zh">' + escapeHtml(it.why) + '</p>');
    return (
      '<div class="ld-feedback ' +
      (a.ok ? 'ld-feedback--ok' : 'ld-feedback--bad') +
      ' gd-fb" role="status" aria-live="polite"><b>' +
      escapeHtml(title) +
      '</b>' +
      lines.join('') +
      '</div>'
    );
  }

  function dockHtml(state) {
    const it = state.item;
    if (state.answered) {
      return (
        feedbackHtml(state) +
        '<button type="button" class="ld-btn" data-act="next" id="gdNext">' +
        escapeHtml(t('next', null, 'Next')) +
        '</button>'
      );
    }
    if (it.type === 'order' || it.type === 'rewrite') {
      const ready = state.placed.length >= (it.tokens || []).length;
      return (
        '<button type="button" class="ld-btn" data-act="check"' +
        (ready ? '' : ' disabled') +
        '>' +
        escapeHtml(t('check', null, 'Check')) +
        '</button>'
      );
    }
    if (state.hidden) {
      return (
        '<button type="button" class="ld-btn" data-act="reveal">' +
        escapeHtml(t('show_choices', null, 'Show choices')) +
        '</button>'
      );
    }
    if (state.typing) {
      return (
        '<button type="button" class="ld-btn" data-act="check">' +
        escapeHtml(t('check', null, 'Check')) +
        '</button>'
      );
    }
    return (
      '<p class="ld-hint gd-hint">' + escapeHtml(t('tap_hint', null, 'Tap an answer.')) + '</p>'
    );
  }

  function drawDrill() {
    if (!session || !session.cur) return;
    const state = session.cur;
    const { slug } = state.entry;
    const meta = topics.get(slug);
    const keepSheet = root.querySelector('.gd-sheet');
    const typedBefore = root.querySelector('#gdTyped');
    const typedValue = typedBefore && !state.answered ? typedBefore.value : null;
    drawn = 'drill';
    header({
      title:
        session.kind === 'mixed'
          ? t('mixed', null, 'Mixed review')
          : session.kind === 'endless'
            ? t('endless', null, 'Endless')
            : meta.title,
      subtitle: session.kind === 'round' ? t('title', null, 'Grammar Drills') : meta.title,
      glyph: firstGlyph(meta),
      end: '',
    });
    root.innerHTML =
      '<div class="ld-screen gd gd--drill' +
      (state.py ? ' is-py' : '') +
      (state.answered ? ' is-answered' : '') +
      '">' +
      stripHtml(state) +
      '<div class="ld-stage gd-stage"><div class="gd-item gd-item--' +
      escapeHtml(state.item.type) +
      '">' +
      itemHtml(state) +
      '</div></div><div class="ld-dock gd-dock">' +
      dockHtml(state) +
      '</div></div>';
    if (keepSheet) root.querySelector('.gd').appendChild(keepSheet);
    const typed = root.querySelector('#gdTyped');
    if (typed && !state.answered) {
      if (typedValue != null) typed.value = typedValue;
      typed.focus();
    }
    const nextBtn = root.querySelector('#gdNext');
    if (nextBtn && !keepSheet) nextBtn.focus({ preventScroll: true });
  }

  function togglePinyin() {
    const screen = root.querySelector('.gd');
    if (!screen) return;
    let on;
    if (session && session.cur && drawn === 'drill') {
      if (!itemHasPinyin(session.cur)) return;
      on = session.cur.py = !session.cur.py;
    } else {
      on = !screen.classList.contains('is-py');
    }
    screen.classList.toggle('is-py', on);
    root.querySelectorAll('.gd-pybtn').forEach((b) => b.setAttribute('aria-pressed', String(on)));
  }

  async function openGuide() {
    if (!session || !session.cur || root.querySelector('.gd-sheet')) return;
    const slug = session.cur.entry.slug;
    const data = session.data.get(slug);
    const sheet = document.createElement('div');
    sheet.className = 'gd-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    sheet.setAttribute('aria-label', t('guide', null, 'Guide'));
    sheet.innerHTML =
      '<div class="gd-sheet__head"><h2 class="ld-h2" lang="zh">' +
      escapeHtml(topics.get(slug).title) +
      '</h2><button type="button" class="ld-btn ld-btn--sm ld-btn--ghost" data-act="guide-close">' +
      escapeHtml(t('close', null, 'Close')) +
      '</button></div><div class="gd-sheet__body">' +
      guideHtml(data && data.guide) +
      '</div>';
    root.querySelector('.gd').appendChild(sheet);
    pauseClock();
    sheet.querySelector('[data-act="guide-close"]').focus();
  }

  function closeGuide() {
    const sheet = root.querySelector('.gd-sheet');
    if (!sheet) return false;
    sheet.remove();
    resumeClock();
    return true;
  }

  /**
   * Reading the guide is not answering: the item's clock (and the speed
   * countdown) stops while the guide is open.
   */
  function pauseClock() {
    if (!session || !session.cur || session.pausedAt) return;
    session.pausedAt = nowMs();
    clearTimeout(session.timer);
    session.timer = null;
    // After a right answer on the speed stage: stay on the item until Next.
    clearTimeout(session.auto);
    session.auto = null;
    const bar = root.querySelector('.gd-timer > i');
    if (bar) bar.style.animationPlayState = 'paused';
  }

  function resumeClock() {
    if (!session || !session.pausedAt) return;
    const away = nowMs() - session.pausedAt;
    session.pausedAt = 0;
    const state = session.cur;
    if (!state || state.answered) return;
    state.startedAt += away;
    if (state.limitMs) {
      const left = state.limitMs - (nowMs() - state.startedAt);
      session.timer = setTimeout(() => submit(false, { timeout: true }), Math.max(0, left));
      if (drawn === 'drill') drawDrill(); // the bar picks up where it stopped
    }
  }

  // ---------------------------------------------------------------- results
  function drawResults() {
    if (!session || !results) return;
    drawn = 'results';
    const r = results;
    const slug = session.slug;
    const meta = topics.get(slug);
    const stat = (n, label) =>
      '<div class="ld-stat"><div class="ld-stat__n">' +
      escapeHtml(String(n)) +
      '</div><small>' +
      escapeHtml(label) +
      '</small></div>';
    const parts = [
      '<div class="gd-results__score"><div class="gd-results__pct ld-num">' +
        pct(r.accuracy) +
        '%</div><p class="ld-muted">' +
        escapeHtml(
          t(
            'results_first_try',
            { correct: r.correct, total: r.answers },
            '{correct} of {total} right first time'
          )
        ) +
        '</p></div>',
      '<div class="ld-stats">' +
        stat(
          t('seconds', { n: seconds(r.medianMs) }, '{n} s'),
          session.kind === 'round' && stageDef(session.stage).recall
            ? t('median_recall', null, 'Median recall time')
            : t('median_time', null, 'Median time')
        ) +
        stat(r.missed.length, t('missed', null, 'Missed')) +
        (session.kind === 'endless'
          ? stat(r.best, t('best_streak', null, 'Best streak'))
          : stat(r.answers, t('items', null, 'Items'))) +
        '</div>',
    ];
    if (session.kind === 'round') {
      const view = store.topic(slug);
      const st = stageStats(view.results[session.stage].slice(-WINDOW));
      const name = stageName(stageDef(session.stage).key);
      let note;
      if (isInstant(view)) {
        note = t('instant_note', null, 'Instant: fast and accurate at the Speed stage.');
      } else if (session.unlocked) {
        note = t(
          'unlocked_note',
          { stage: stageName(stageDef(session.unlocked).key) },
          '{stage} is now open.'
        );
      } else if (session.stage === LAST_STAGE) {
        note = t(
          'instant_rule',
          null,
          'Instant = 90% of your last 30 Speed answers right, median under 3 s.'
        );
      } else if (session.stage < view.unlocked) {
        note = '';
      } else {
        note = t(
          'unlock_rule',
          {
            have: st.n,
            need: WINDOW,
            pct: pct(UNLOCK_ACC),
            next: stageName(stageDef(session.stage + 1).key),
          },
          '{next} opens at {pct}% over your last {need} answers here ({have} so far).'
        );
      }
      parts.push(
        '<section class="ld-card gd-progress"><div class="gd-progress__head"><b>' +
          escapeHtml(session.stage + ' · ' + name) +
          '</b><span class="ld-num">' +
          escapeHtml(t('last_n', { n: st.n, pct: pct(st.acc) }, 'last {n} answers: {pct}%')) +
          '</span></div><div class="ld-bar gd-progress__bar"><i style="width:' +
          Math.min(100, Math.round((st.n / WINDOW) * 100)) +
          '%"></i></div>' +
          (note
            ? '<p class="gd-note' +
              (session.unlocked || isInstant(view) ? ' gd-note--ok' : '') +
              '">' +
              escapeHtml(note) +
              '</p>'
            : '') +
          (session.unlocked
            ? '<button type="button" class="ld-btn ld-btn--sm" data-act="next-stage" data-n="' +
              session.unlocked +
              '">' +
              escapeHtml(
                t(
                  'start_stage',
                  { stage: stageName(stageDef(session.unlocked).key) },
                  'Start · {stage}'
                )
              ) +
              '</button>'
            : '') +
          '</section>'
      );
    }
    // A generator can hand out the same sentence twice: list it once.
    const missedOnce = [];
    const listed = new Set();
    r.missed.forEach(({ item }) => {
      const key =
        item.id && !String(item.id).startsWith('gen:')
          ? item.id
          : correctSentence(item) + '|' + (item.q || '');
      if (listed.has(key)) return;
      listed.add(key);
      missedOnce.push(item);
    });
    if (missedOnce.length) {
      parts.push(
        '<section class="gd-missed"><h2 class="ld-h2">' +
          escapeHtml(t('missed_title', null, 'Items you missed')) +
          '</h2><ul class="gd-exs">' +
          missedOnce
            .map((item) => {
              const zh = correctSentence(item);
              return (
                '<li class="gd-ex"><span class="gd-zh" lang="zh">' +
                sentenceHtml(zh || item.q || '', item.py) +
                '</span>' +
                (item.en || item.cue
                  ? '<span class="gd-ex__en">' + escapeHtml(item.en || item.cue) + '</span>'
                  : '') +
                '</li>'
              );
            })
            .join('') +
          '</ul></section>'
      );
    }
    header({
      title:
        session.kind === 'mixed'
          ? t('mixed', null, 'Mixed review')
          : meta
            ? meta.title
            : t('title', null, 'Grammar Drills'),
      subtitle: t('results', null, 'Results'),
      end: '',
    });
    root.innerHTML =
      '<div class="ld-screen gd gd--results' +
      (store.settings().pinyin ? ' is-py' : '') +
      '"><div class="ld-stage gd-stage">' +
      parts.join('') +
      '</div><div class="ld-dock gd-dock"><div class="ld-row">' +
      '<button type="button" class="ld-btn ld-btn--ghost" data-act="hub">' +
      escapeHtml(t('back_to_topics', null, 'Back to topics')) +
      '</button><button type="button" class="ld-btn" data-act="again" id="gdAgain">' +
      escapeHtml(t('again', null, 'Again')) +
      '</button></div></div></div>';
  }

  function again() {
    if (!session) return;
    const { kind, slug } = session;
    if (kind === 'mixed') startMixed();
    else if (kind === 'endless') startEndless(slug);
    else startRound(slug);
  }

  // ----------------------------------------------------------------- events
  /** Recall cloze: show the item's options; the time so far is the recall time. */
  function reveal() {
    const state = session && session.cur;
    if (!state || state.answered || !state.hidden) return;
    state.hidden = false;
    state.revealMs = Math.max(1, Math.round(nowMs() - state.startedAt));
    drawDrill();
  }

  function chooseOption(k) {
    const state = session && session.cur;
    if (!state || state.answered || state.item.type !== 'cloze' || state.typing) return;
    if (state.hidden) return;
    const opt = state.options[k];
    if (opt == null) return;
    submit(checkCloze(state.item, opt), { choice: opt });
  }

  function judge(says) {
    const state = session && session.cur;
    if (!state || state.answered || state.item.type !== 'judge') return;
    submit(checkJudge(state.item, says), { says });
  }

  function place(k) {
    const state = session && session.cur;
    if (!state || state.answered || !state.tiles || state.placed.includes(k)) return;
    if (!state.tiles[k]) return;
    state.placed.push(k);
    drawDrill();
  }

  function unplace(k) {
    const state = session && session.cur;
    if (!state || state.answered || !state.tiles) return;
    const at = k == null ? state.placed.length - 1 : state.placed.indexOf(k);
    if (at < 0) return;
    state.placed.splice(at, 1);
    drawDrill();
  }

  function check() {
    const state = session && session.cur;
    if (!state || state.answered) return;
    const it = state.item;
    if (state.tiles) {
      if (state.placed.length < (it.tokens || []).length) return;
      submit(
        checkOrder(
          it,
          state.placed.map((k) => state.tiles[k].text)
        ),
        {}
      );
    } else if (state.typing) {
      const input = root.querySelector('#gdTyped');
      const typed = input ? input.value.trim() : '';
      if (!typed) return;
      submit(checkTyped(it, typed), { typed });
    }
  }

  function onClick(e) {
    const el = e.target.closest ? e.target.closest('[data-act]') : null;
    if (!el || !root.contains(el) || el.disabled) return;
    const act = el.dataset.act;
    const slug = el.dataset.slug;
    if (act === 'topic') go(slug);
    else if (act === 'continue') {
      // A topic already practised goes straight to its next round; a new one shows its guide first.
      if (store.topic(slug).seq > 0 && topics.get(slug).count > 0) startRound(slug);
      else go(slug);
    } else if (act === 'mixed') startMixed();
    else if (act === 'retry') boot();
    else if (act === 'setting') {
      const on = el.getAttribute('aria-checked') !== 'true';
      store.setSetting(el.dataset.name, on);
      el.setAttribute('aria-checked', String(on));
    } else if (act === 'stage') {
      const cur = parseHash().slug;
      store.setStage(cur, Number(el.dataset.n));
      openTopic(cur);
    } else if (act === 'start') startRound(parseHash().slug);
    else if (act === 'endless') startEndless(parseHash().slug);
    else if (act === 'py') togglePinyin();
    else if (act === 'guide') openGuide();
    else if (act === 'guide-close') closeGuide();
    else if (act === 'stop') finish();
    else if (act === 'opt') chooseOption(Number(el.dataset.i));
    else if (act === 'judge') judge(el.dataset.ok === '1');
    else if (act === 'place') place(Number(el.dataset.i));
    else if (act === 'unplace') unplace(Number(el.dataset.i));
    else if (act === 'check') check();
    else if (act === 'reveal') reveal();
    else if (act === 'typed-none') {
      const state = session && session.cur;
      if (state && !state.answered)
        submit(checkCloze(state.item, EMPTY), { typed: nothingLabel() });
    } else if (act === 'next') next();
    else if (act === 'again') again();
    else if (act === 'hub') {
      endSession();
      go('', true);
    } else if (act === 'next-stage') {
      store.setStage(session.slug, Number(el.dataset.n));
      startRound(session.slug);
    }
  }

  function onSubmit(e) {
    if (e.target && e.target.dataset && e.target.dataset.form === 'typed') {
      e.preventDefault();
      check();
    }
  }

  function onKey(e) {
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = e.target && e.target.tagName;
    const inField = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    if (e.key === 'Escape' && closeGuide()) {
      e.preventDefault();
      return;
    }
    if (root.querySelector('.gd-sheet')) return;
    if (!inField && (e.key === 'p' || e.key === 'P')) {
      if (drawn === 'drill' || drawn.startsWith('topic:')) {
        e.preventDefault();
        togglePinyin();
      }
      return;
    }
    if (drawn === 'results') {
      if (e.key === 'Enter' && tag !== 'BUTTON' && tag !== 'A') {
        e.preventDefault();
        again();
      }
      return;
    }
    if (drawn !== 'drill' || !session || !session.cur) return;
    const state = session.cur;
    const onControl = tag === 'BUTTON' || tag === 'A';
    if (e.key === 'Enter' || (e.key === ' ' && !inField)) {
      if (onControl || inField) return; // the control's own click / the form's submit
      e.preventDefault();
      if (state.answered) next();
      else if (state.hidden) reveal();
      else check();
      return;
    }
    if (inField || state.answered) return;
    if (e.key === 'Backspace' && state.tiles) {
      e.preventDefault();
      unplace(null);
      return;
    }
    if (!/^[1-9]$/.test(e.key)) return;
    const n = Number(e.key);
    if (state.item.type === 'cloze') {
      e.preventDefault();
      chooseOption(n - 1);
    } else if (state.item.type === 'judge') {
      if (n <= 2) {
        e.preventDefault();
        judge(n === 1);
      }
    } else if (state.tiles) {
      // The nth tile still waiting to be placed.
      const waiting = state.tiles.map((_, k) => k).filter((k) => !state.placed.includes(k));
      if (waiting[n - 1] != null) {
        e.preventDefault();
        place(waiting[n - 1]);
      }
    }
  }

  // ------------------------------------------------------------------- boot
  async function boot() {
    root.innerHTML =
      '<div class="ld-screen gd"><div class="ld-stage gd-stage"><div class="gd-msg">' +
      escapeHtml(t('loading', null, 'Loading…')) +
      '</div></div></div>';
    try {
      if (window.LinguaI18n && window.LinguaI18n.init) await window.LinguaI18n.init();
    } catch {}
    let gens;
    try {
      [manifest, gens] = await Promise.all([
        opts.manifest ? Promise.resolve(opts.manifest) : loadManifest(manifestUrl),
        opts.generators
          ? Promise.resolve(opts.generators)
          : loadGenerators(
              opts.generatorsUrl != null ? opts.generatorsUrl : root.dataset.generators
            ),
      ]);
    } catch {
      manifest = null;
      if (alive) {
        message(
          t('error_manifest', null, 'Grammar drills are not available right now. Try again later.'),
          true
        );
      }
      return;
    }
    if (!alive) return;
    generatorsFor = gens;
    topics = new Map((manifest.topics || []).map((tp) => [tp.slug, tp]));
    if (!topics.size) {
      message(t('empty', null, 'No grammar topics are available yet.'), false);
      return;
    }
    applyI18n(root);
    route();
  }

  const onPop = () => route();
  root.addEventListener('click', onClick);
  root.addEventListener('submit', onSubmit);
  document.addEventListener('keydown', onKey);
  window.addEventListener('popstate', onPop);
  const sh = shell();
  const offBack = sh && sh.onBack ? sh.onBack(() => (closeGuide() ? true : back())) : null;
  boot();

  return {
    destroy() {
      alive = false;
      endSession();
      root.removeEventListener('click', onClick);
      root.removeEventListener('submit', onSubmit);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('popstate', onPop);
      if (offBack) offBack();
      root.innerHTML = '';
    },
  };
}
