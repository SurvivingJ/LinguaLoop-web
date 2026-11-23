/* Vocabulary placement (/placement) — wiki/features/vocab-placement.tech.md §8, §15, §16.

   A short adaptive test: each word's meaning first (the word only, no
   reading), then, for zh/ja and only after a right meaning, its reading in the
   same word. Every word ends in ONE combined reveal. The server owns every
   decision (grading, what comes next, when to stop, the result); this page only
   renders what /api/calibration/placement/* sends, and no payload carries a key
   before the word is complete (§18).

   Flow: GET /latest (an unseen abandoned result is shown first) → intro →
   POST /start → item → POST /answer → (the same word's next question, no
   feedback) … → reveal → Next / auto-advance → … → result. "Stop here and see
   your result" (once the server says can_stop) and "End now" call POST /end. */
(function () {
  'use strict';

  const API = '/api/calibration/placement';
  // dim_languages ids. `es` is a UI locale only: a Spanish-speaking learner
  // reads English definitions, as in the vocabulary check (calibration.js).
  const LANG_CODE = { 1: 'zh', 2: 'en', 3: 'ja' };
  const CODE_TO_ID = { zh: 1, en: 2, ja: 3 };
  //: A fully right word stays on screen this long, then moves on (as the check).
  const CORRECT_PAUSE_MS = 450;
  //: The band strip draws one dot per 5% of the check's word pool.
  const BAND_DOTS = 20;

  // ------------------------------------------------------------------
  // Pure helpers (also on window.LinguaPlacement for the unit tests)
  // ------------------------------------------------------------------

  function isSkipped(part) {
    if (part.skipped === true) return true;
    if (part.skipped === false) return false;
    return part.chosen_text === null || part.chosen_text === undefined;
  }

  // Auto-advance only when every question of the word, probes included, was
  // right: anything else leaves something to read.
  function allCorrect(parts) {
    return (
      Array.isArray(parts) &&
      parts.length > 0 &&
      parts.every(function (p) {
        return p.is_correct === true;
      })
    );
  }

  // The word's group in "Your answers (guesses included)" (§4). Probes never
  // move a word between groups, and a word with no scored meaning answer (a
  // recheck probe) is not one of this test's words.
  function wordGroup(parts) {
    const scored = (parts || []).filter(function (p) {
      return !p.probe_kind;
    });
    const meaning = scored.find(function (p) {
      return p.kind === 'meaning';
    });
    if (!meaning) return null;
    if (meaning.is_correct !== true) return 'not_yet';
    const reading = scored.find(function (p) {
      return p.kind === 'reading';
    });
    if (!reading || reading.is_correct === true) return 'both';
    if (reading.tone_only_miss === true) return 'tones_not_yet';
    return 'meaning_only';
  }

  // One state per dot of the band strip: 'in' (wholly below lo), 'range'
  // (overlaps lo–hi) or 'out' (wholly above hi).
  function bandDots(lo, hi, n, count) {
    const dots = [];
    const k = count || BAND_DOTS;
    for (let i = 0; i < k; i++) {
      const start = (i * n) / k;
      const end = ((i + 1) * n) / k;
      if (end <= lo) dots.push('in');
      else if (start < hi) dots.push('range');
      else dots.push('out');
    }
    return dots;
  }

  window.LinguaPlacement = {
    allCorrect: allCorrect,
    wordGroup: wordGroup,
    bandDots: bandDots,
    CORRECT_PAUSE_MS: CORRECT_PAUSE_MS,
  };

  // ------------------------------------------------------------------
  // Page
  // ------------------------------------------------------------------

  const $ = function (id) {
    return document.getElementById(id);
  };
  const el = {
    strip: $('plcStrip'),
    minutes: $('plcMinutes'),
    bar: $('plcBar'),
    stopBtn: $('plcStopBtn'),
    endBtn: $('plcEndBtn'),
    loading: $('plcLoading'),
    intro: $('plcIntro'),
    introTime: $('plcIntroTime'),
    confirm: $('plcConfirm'),
    confirmText: $('plcConfirmText'),
    keepGoing: $('plcKeepGoing'),
    item: $('plcItem'),
    probeBadge: $('plcProbeBadge'),
    prompt: $('plcPrompt'),
    instruction: $('plcInstruction'),
    options: $('plcOptions'),
    reveal: $('plcReveal'),
    result: $('plcResult'),
    message: $('plcMessage'),
    dock: $('plcDock'),
    introActions: $('plcIntroActions'),
    itemActions: $('plcItemActions'),
    revealActions: $('plcRevealActions'),
    resultActions: $('plcResultActions'),
    retryActions: $('plcRetryActions'),
    startBtn: $('plcStartBtn'),
    idkBtn: $('plcIdkBtn'),
    nextBtn: $('plcNextBtn'),
    newBtn: $('plcNewBtn'),
    retryBtn: $('plcRetryBtn'),
    langName: $('plcLangName'),
  };

  const state = {
    view: 'loading',
    lang: 3,
    defLang: 2,
    sessionId: null,
    item: null,
    // The answered parts of the word in progress, held until its reveal (§15).
    pendingWord: null,
    progress: null,
    canStop: false,
    needed: null,
    result: null,
    // The /answer response whose next item or result follows the reveal.
    after: null,
    // True between a reveal and moving on: the one-advance guard (TASK-775).
    awaitingAdvance: false,
    advanceTimer: null,
    // True while an answer is in flight.
    locked: false,
    starting: false,
    ending: false,
    shownAt: 0,
    retry: null,
    messageKey: null,
    resultOpts: null,
  };

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  function uiLocale() {
    const i18n = window.LinguaI18n;
    const cur = i18n && typeof i18n.currentLanguage === 'function' ? i18n.currentLanguage() : '';
    return String(cur || document.documentElement.lang || 'en').slice(0, 2);
  }

  function fmt(n) {
    try {
      return new Intl.NumberFormat(uiLocale()).format(n);
    } catch {
      return String(n);
    }
  }

  // Keep "500–1,100" on one line: word joiners around a dash between digits.
  function keepRanges(text) {
    return String(text).replace(/(\d)–(\d)/g, '$1⁠–⁠$2');
  }

  function fmtRange(r) {
    return keepRanges(fmt(r.lo) + '–' + fmt(r.hi));
  }

  function fmtDate(iso) {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    try {
      return d.toLocaleDateString(uiLocale(), { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return d.toISOString().slice(0, 10);
    }
  }

  function now() {
    return window.performance && performance.now ? performance.now() : Date.now();
  }

  function storedLanguageId() {
    try {
      return parseInt(localStorage.getItem('selectedLanguageId'), 10);
    } catch {
      return NaN;
    }
  }

  // ?lang= (an id or a code, from the entry points, TASK-1085), else the study
  // language, else Japanese as the check does.
  function wordLanguageId() {
    const q = new URLSearchParams(window.location.search).get('lang');
    if (q) {
      const byCode = CODE_TO_ID[String(q).toLowerCase()];
      if (byCode) return byCode;
      const n = parseInt(q, 10);
      if (LANG_CODE[n]) return n;
    }
    const id = storedLanguageId();
    return LANG_CODE[id] ? id : 3;
  }

  // D as the check's start: the UI locale's language, English for es.
  function definitionLanguageId() {
    return CODE_TO_ID[uiLocale()] || 2;
  }

  function langCode(id) {
    return LANG_CODE[id] || 'en';
  }

  function isCjk() {
    return state.lang === 1 || state.lang === 3;
  }

  function idkAllowed(item) {
    if (!item) return false;
    if (item.probe_kind === 'forced_guess') return false;
    return item.idk_allowed !== false;
  }

  function toast(key) {
    if (window.showToast) window.showToast(tr(key));
  }

  function node(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  // ---- network ----------------------------------------------------

  async function call(method, path, body) {
    const opts = { method: method };
    if (body !== undefined) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(body);
    }
    let resp;
    try {
      resp = await window.authFetch(API + path, opts);
    } catch {
      return { ok: false, network: true, status: 0, data: null };
    }
    let data = null;
    try {
      data = await resp.json();
    } catch {
      data = null;
    }
    const ok = !!resp.ok && !(data && data.status === 'error');
    return { ok: ok, network: false, status: resp.status, data: data };
  }

  function getResult(sessionId) {
    return call('GET', '/result?session_id=' + encodeURIComponent(sessionId));
  }

  // ---- word log (the group lists of the result) --------------------

  function logKey(sessionId) {
    return 'placement.words.' + sessionId;
  }

  function readLog(sessionId) {
    if (!sessionId) return null;
    try {
      const raw = sessionStorage.getItem(logKey(sessionId));
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function appendLog(sessionId, entry) {
    if (!sessionId) return;
    const log = readLog(sessionId) || [];
    log.push(entry);
    try {
      sessionStorage.setItem(logKey(sessionId), JSON.stringify(log));
    } catch {}
  }

  // Server lists win (word_lists: {group: [lemma | {lemma, reading, meaning}]}),
  // then this tab's own log of the session's reveals.
  function groupLists(serverLists, sessionId) {
    const lists = {};
    if (serverLists && typeof serverLists === 'object') {
      Object.keys(serverLists).forEach(function (g) {
        lists[g] = (serverLists[g] || []).map(function (w) {
          return typeof w === 'string' ? { lemma: w } : w;
        });
      });
      return lists;
    }
    const log = readLog(sessionId);
    if (!log) return null;
    log.forEach(function (w) {
      (lists[w.group] = lists[w.group] || []).push(w);
    });
    return lists;
  }

  // ---- screens -----------------------------------------------------

  const VIEWS = ['loading', 'intro', 'item', 'reveal', 'result', 'message'];
  const DOCKS = ['introActions', 'itemActions', 'revealActions', 'resultActions', 'retryActions'];

  function show(view, dock) {
    state.view = view;
    VIEWS.forEach(function (v) {
      el[v].hidden = v !== view;
    });
    DOCKS.forEach(function (d) {
      el[d].hidden = d !== dock;
    });
    el.dock.hidden = !dock;
    const testing = view === 'item' || view === 'reveal';
    el.strip.hidden = !testing;
    if (!testing) el.confirm.hidden = true;
    const scroller = el[view].closest ? el[view].closest('.ld-stage') : null;
    if (scroller) scroller.scrollTop = 0;
  }

  function showLoading() {
    el.loading.textContent = tr('placement.loading');
    show('loading', null);
  }

  function showMessage(key, opts) {
    const o = opts || {};
    el.message.textContent = tr(key);
    el.message.dataset.state = o.state || key;
    state.messageKey = key;
    state.retry = o.retry || null;
    show('message', state.retry ? 'retryActions' : null);
  }

  function showUnavailable() {
    showMessage('placement.unavailable', { state: 'unavailable' });
  }

  function showIntro() {
    clearAdvance();
    state.sessionId = null;
    state.item = null;
    state.pendingWord = null;
    state.result = null;
    el.introTime.textContent = tr(isCjk() ? 'placement.intro_time_cjk' : 'placement.intro_time_en');
    show('intro', 'introActions');
  }

  function updateProgress() {
    const p = state.progress;
    if (p && p.minutes_left !== null && p.minutes_left !== undefined) {
      const n = Math.max(1, Math.round(Number(p.minutes_left) || 0));
      el.minutes.textContent = tr('placement.minutes_left', { count: n });
    } else {
      el.minutes.textContent = '';
    }
    const cap = p && p.cap ? p.cap : 0;
    const pct = cap ? Math.min(100, Math.round(((p.scored || 0) / cap) * 100)) : 0;
    el.bar.style.width = pct + '%';
    el.stopBtn.hidden = !state.canStop;
    el.endBtn.hidden = !!state.canStop;
  }

  function clearAdvance() {
    if (state.advanceTimer) {
      clearTimeout(state.advanceTimer);
      state.advanceTimer = null;
    }
  }

  function setHeader() {
    if (el.langName) {
      const key = 'lang_select.name_' + langCode(state.lang);
      el.langName.setAttribute('data-i18n', key);
      el.langName.textContent = tr(key);
    }
    if (window.LinguaShell && window.LinguaShell.setTaskHeader) {
      window.LinguaShell.setTaskHeader({ glyph: { 1: '词', 2: 'Aa', 3: '語' }[state.lang] });
    }
  }

  // ---- start -------------------------------------------------------

  function adoptSession(data) {
    if (data.session_id !== state.sessionId) state.pendingWord = null;
    state.sessionId = data.session_id;
    state.progress = data.progress || null;
    state.canStop = !!data.can_stop;
    state.needed = data.needed !== undefined ? data.needed : null;
  }

  async function start() {
    if (state.starting) return;
    state.starting = true;
    showLoading();
    const r = await call('POST', '/start', {
      word_language_id: state.lang,
      definition_language_id: state.defLang,
    });
    state.starting = false;
    if (r.status === 404) return showUnavailable();
    if (r.status === 429) return showMessage('placement.rate_limited', { state: 'rate_limited' });
    if (!r.ok || !r.data || !r.data.session_id) {
      return showMessage('placement.error_start', { state: 'error', retry: start });
    }
    adoptSession(r.data);
    if (r.data.resumed && window.showToast) window.showToast(tr('placement.resumed'), 'info');
    if (r.data.item) return renderItem(r.data.item);
    if (r.data.result) return showResult(r.data.result, resultOpts(r.data));
    return showMessage('placement.error_start', { state: 'error', retry: start });
  }

  // After a lost answer response: the session may have finished, or moved on.
  // A finished session has a result; an open one is resumed by /start, which
  // re-sends its pending item.
  async function resync() {
    showLoading();
    if (state.sessionId) {
      const r = await getResult(state.sessionId);
      if (r.ok && r.data && r.data.result) return showResult(r.data.result, resultOpts(r.data));
    }
    return start();
  }

  // ---- item --------------------------------------------------------

  function instructionKey(item) {
    if (item.probe_kind === 'forced_guess') return 'placement.best_guess';
    if (item.probe_kind === 'sound_pair') return 'placement.sound_pair_prompt';
    if (item.kind === 'reading') {
      return state.lang === 1 ? 'placement.choose_pinyin' : 'placement.choose_reading_ja';
    }
    return 'placement.choose_meaning';
  }

  function isReadingPart(p) {
    return p.kind === 'reading' || p.probe_kind === 'sound_pair';
  }

  function renderItem(item) {
    clearAdvance();
    state.awaitingAdvance = false;
    state.locked = false;
    state.item = item;
    state.after = null;
    if (!state.pendingWord || state.pendingWord.vocab_id !== item.vocab_id) {
      state.pendingWord = { vocab_id: item.vocab_id, lemma: item.lemma, parts: [] };
    }

    const wordLang = langCode(state.lang);
    // The word only: a meaning item never shows a reading (§2 rule 2).
    el.prompt.textContent = item.lemma || '';
    el.prompt.lang = wordLang;
    el.probeBadge.hidden = !item.probe_kind;
    el.instruction.textContent = tr(instructionKey(item));

    const reading = isReadingPart(item);
    const options = item.options || [];
    el.options.className = 'cal-options' + (reading ? ' pron' : '');
    el.options.dataset.count = String(options.length);
    el.options.innerHTML = '';
    options.forEach(function (text, i) {
      const btn = node('button', 'cal-option');
      btn.type = 'button';
      btn.dataset.position = String(i);
      const key = node('span', 'cal-key', String(i + 1));
      key.setAttribute('aria-hidden', 'true');
      const label = node('span', 'cal-option-text', text);
      // Readings in the study language's face, definitions in D's.
      label.lang = reading ? wordLang : langCode(state.defLang);
      const badge = node('span', 'cal-badge');
      badge.setAttribute('aria-hidden', 'true');
      btn.append(key, label, badge);
      btn.addEventListener('click', function () {
        answer(i);
      });
      el.options.appendChild(btn);
    });

    el.idkBtn.hidden = !idkAllowed(item);
    el.idkBtn.disabled = false;
    el.idkBtn.classList.remove('picked');
    show('item', 'itemActions');
    updateProgress();
    state.shownAt = now();
  }

  const SPIN =
    '<svg viewBox="0 0 24 24"><circle class="spin" cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="40 60"/></svg>';

  function optionButtons() {
    return Array.prototype.slice.call(el.options.querySelectorAll('.cal-option'));
  }

  // Acknowledge the tap before the network call, not after it.
  function lockItem(position) {
    const buttons = optionButtons();
    buttons.forEach(function (b) {
      b.disabled = true;
    });
    el.idkBtn.disabled = true;
    el.options.classList.add('answered');
    if (position === null) {
      el.idkBtn.classList.add('picked');
    } else if (buttons[position]) {
      buttons[position].classList.add('picked');
      buttons[position].querySelector('.cal-badge').innerHTML = SPIN;
    }
  }

  function unlockItem() {
    el.options.classList.remove('answered');
    optionButtons().forEach(function (b) {
      b.disabled = false;
      b.classList.remove('picked');
      b.querySelector('.cal-badge').innerHTML = '';
    });
    el.idkBtn.disabled = false;
    el.idkBtn.classList.remove('picked');
    state.locked = false;
  }

  async function answer(position) {
    if (state.locked || state.awaitingAdvance || state.view !== 'item' || !state.item) return;
    const item = state.item;
    if (position === null && !idkAllowed(item)) return;
    const n = (item.options || []).length;
    if (position !== null && (position < 0 || position >= n)) return;

    state.locked = true;
    el.confirm.hidden = true;
    const latency = Math.max(0, Math.round(now() - state.shownAt));
    lockItem(position);

    const body = {
      session_id: state.sessionId,
      response_id: item.response_id,
      position: position,
      latency_ms: latency,
    };
    let r = await call('POST', '/answer', body);
    // A network (or server) error is retried once with the same answer: the
    // RPC rejects a second grading of one item, so this is safe.
    if (!r.ok && (r.network || r.status >= 500)) r = await call('POST', '/answer', body);
    if (state.item !== item || state.view !== 'item') return; // ended meanwhile
    if (!r.ok || !r.data) return answerFailed(r);
    handleAnswer(r.data, item, position);
  }

  function answerFailed(r) {
    unlockItem();
    if (r.network || !r.status || r.status >= 500 || r.status === 429) {
      return toast('placement.error_answer');
    }
    // Another 4xx: the item was already graded (a lost response) or the
    // session closed. Ask the server where things stand.
    return resync();
  }

  function handleAnswer(data, item, position) {
    const word =
      state.pendingWord ||
      (state.pendingWord = { vocab_id: item.vocab_id, lemma: item.lemma, parts: [] });
    word.parts.push({
      kind: item.kind,
      probe_kind: item.probe_kind || null,
      chosen_text: position === null ? null : item.options[position],
      is_correct: data.answer ? data.answer.is_correct : undefined,
    });
    if (data.progress) state.progress = data.progress;
    state.canStop = !!data.can_stop;
    if (data.needed !== undefined) state.needed = data.needed;

    if (data.reveal) {
      state.after = data;
      return showReveal(data.reveal);
    }
    // No reveal: the same word goes on (its reading, or a probe). No feedback
    // between the questions of a word (§3).
    if (data.next_item && !data.done) return renderItem(data.next_item);
    if (data.done) return finishWith(data);
    return resync();
  }

  // ---- reveal ------------------------------------------------------

  function partLabelKey(part) {
    if (isReadingPart(part)) {
      return state.lang === 1 ? 'placement.reveal_pinyin' : 'placement.reveal_reading';
    }
    return 'placement.reveal_meaning';
  }

  function revealPart(p, wordLang) {
    const status = p.is_correct === true ? 'right' : isSkipped(p) ? 'skipped' : 'wrong';
    const li = node('li', 'plc-part plc-part--' + status);
    li.dataset.kind = p.kind || '';
    if (p.probe_kind) li.dataset.probe = p.probe_kind;
    const mark = node('span', 'plc-part__mark', { right: '✓', wrong: '✗', skipped: '–' }[status]);
    const body = node('div', 'plc-part__body');
    body.appendChild(node('span', 'plc-part__label', tr(partLabelKey(p))));
    if (p.probe_kind) {
      body.appendChild(node('span', 'ld-tag plc-probe-badge', tr('placement.probe_badge')));
    }
    if (status === 'wrong') {
      const chose = node('div', 'plc-part__chose');
      chose.appendChild(node('span', 'plc-part__chose-label', tr('placement.you_chose') + ' '));
      const t = node('span', 'plc-part__chosen', p.chosen_text || '');
      t.lang = isReadingPart(p) ? wordLang : langCode(state.defLang);
      chose.appendChild(t);
      body.appendChild(chose);
      if (p.tone_only_miss === true) {
        body.appendChild(node('div', 'plc-part__tones', tr('placement.tone_only_miss')));
      }
    } else if (status === 'skipped') {
      body.appendChild(node('div', 'plc-part__chose', tr('placement.idk')));
    }
    li.append(mark, body);
    return li;
  }

  function showReveal(reveal) {
    const held = (state.pendingWord && state.pendingWord.parts) || [];
    const source = reveal.parts && reveal.parts.length ? reveal.parts : held;
    const parts = source.map(function (p, i) {
      const own = held[i] || {};
      return Object.assign({}, p, {
        chosen_text: p.chosen_text !== undefined ? p.chosen_text : own.chosen_text,
      });
    });
    const lemma = reveal.lemma || (state.pendingWord && state.pendingWord.lemma) || '';
    const group = wordGroup(parts);
    if (group) {
      appendLog(state.sessionId, {
        lemma: lemma,
        reading: reveal.reading || null,
        meaning: reveal.meaning || null,
        group: group,
      });
    }

    const wordLang = langCode(state.lang);
    const card = el.reveal;
    card.innerHTML = '';
    const head = node('div', 'plc-reveal__head');
    const w = node('div', 'plc-reveal__word', lemma);
    w.lang = wordLang;
    head.appendChild(w);
    if (reveal.reading) {
      const rd = node('div', 'plc-reveal__reading', reveal.reading);
      rd.lang = wordLang;
      head.appendChild(rd);
    }
    if (reveal.meaning) {
      const m = node('div', 'plc-reveal__meaning', reveal.meaning);
      m.lang = langCode(state.defLang);
      head.appendChild(m);
    }
    card.appendChild(head);
    const list = node('ul', 'plc-reveal__parts');
    parts.forEach(function (p) {
      list.appendChild(revealPart(p, wordLang));
    });
    card.appendChild(list);

    state.awaitingAdvance = true;
    state.locked = false;
    if (allCorrect(parts)) {
      // Nothing to read: it moves on by itself. A key press skips the pause.
      el.idkBtn.disabled = true;
      show('reveal', 'itemActions');
      state.advanceTimer = setTimeout(advance, CORRECT_PAUSE_MS);
    } else {
      show('reveal', 'revealActions');
    }
    updateProgress();
  }

  // The single way forward from a reveal: the timer, the button or a key.
  function advance() {
    if (!state.awaitingAdvance) return;
    state.awaitingAdvance = false;
    clearAdvance();
    state.pendingWord = null;
    const after = state.after;
    state.after = null;
    if (after && after.done) return finishWith(after);
    if (after && after.next_item) return renderItem(after.next_item);
    return resync();
  }

  async function finishWith(data) {
    if (data && data.result) return showResult(data.result, resultOpts(data));
    showLoading();
    const r = await getResult(state.sessionId);
    if (r.ok && r.data && r.data.result) return showResult(r.data.result, resultOpts(r.data));
    return showMessage('placement.error_answer', { state: 'error', retry: resync });
  }

  // ---- ending early ------------------------------------------------

  async function endNow() {
    if (state.ending || state.locked || !state.sessionId) return;
    state.ending = true;
    const r = await call('POST', '/end', { session_id: state.sessionId });
    state.ending = false;
    if (r.ok && r.data && r.data.result) return showResult(r.data.result, resultOpts(r.data));
    if (r.ok && r.data && r.data.not_enough) {
      state.canStop = false;
      if (r.data.needed !== undefined) state.needed = r.data.needed;
      updateProgress();
      return showConfirm();
    }
    if (!state.canStop) return showConfirm();
    return toast('placement.error_answer');
  }

  function showConfirm() {
    const k = state.needed === null || state.needed === undefined ? '' : fmt(state.needed);
    el.confirmText.textContent = tr('placement.not_enough', { k: k });
    el.confirm.hidden = false;
  }

  // ---- result (§8 blocks, in order) --------------------------------

  // What a response carrying a result may add beside it (outside the frozen
  // JSON): the group word lists and the learner's remaining new-word budget.
  function resultOpts(data, extra) {
    const d = data || {};
    return Object.assign(
      {
        sessionId: state.sessionId,
        wordLists: d.word_lists || null,
        budget: typeof d.new_word_budget_left === 'number' ? d.new_word_budget_left : undefined,
      },
      extra || {}
    );
  }

  function block(cls, title) {
    const s = node('section', 'plc-block ld-card ' + cls);
    if (title) s.appendChild(node('h2', 'ld-eyebrow plc-block__title', title));
    return s;
  }

  function actionLink(key, href, suffix) {
    const a = node('a', 'ld-btn ld-btn--sm ld-btn--ghost plc-action', tr(key) + (suffix || ''));
    a.href = href;
    return a;
  }

  // "(up to {k} today)" when the group is larger than today's new-word budget.
  function upToToday(count, budget) {
    if (typeof budget !== 'number' || count <= budget) return '';
    return ' ' + tr('placement.up_to_today', { k: fmt(Math.max(0, budget)) });
  }

  function wordList(own) {
    const wl = node('ul', 'plc-group__words');
    own.forEach(function (w) {
      const wi = node('li', 'plc-word');
      const lem = node('span', 'plc-word__lemma', w.lemma);
      lem.lang = langCode(state.lang);
      wi.appendChild(lem);
      if (w.reading) {
        const rd = node('span', 'plc-word__reading', w.reading);
        rd.lang = langCode(state.lang);
        wi.appendChild(rd);
      }
      if (w.meaning) {
        const mn = node('span', 'plc-word__meaning', w.meaning);
        mn.lang = langCode(state.defLang);
        wi.appendChild(mn);
      }
      wl.appendChild(wi);
    });
    return wl;
  }

  // Block 1: this test's own words, guesses included. A group with words opens
  // in place to list them (when this tab saw them, or the server sent them)
  // with its action.
  function groupBlock(result, lists, cjk, zh, budget) {
    const words = result.words || {};
    const s = block('plc-groups', tr('placement.answers_heading'));
    s.appendChild(
      node('p', 'plc-groups__of', tr('placement.answers_of', { n: fmt(words.asked || 0) }))
    );
    let groups = ['both', 'not_yet'];
    if (cjk) groups = ['both', 'meaning_only', 'not_yet'];
    if (cjk && zh) groups = ['both', 'tones_not_yet', 'meaning_only', 'not_yet'];
    const ul = node('ul', 'plc-groups__list');
    groups.forEach(function (g) {
      const count = words[g] || 0;
      const li = node('li', 'plc-group');
      li.dataset.group = g;
      const panel = node('div', 'plc-group__body');
      panel.hidden = true;
      if (count) {
        const own = lists && lists[g];
        if (own && own.length) panel.appendChild(wordList(own));
        if (cjk && (g === 'tones_not_yet' || g === 'meaning_only')) {
          panel.appendChild(
            actionLink('placement.practise_readings', '/session', upToToday(count, budget))
          );
        } else if (g === 'not_yet') {
          panel.appendChild(
            actionLink('placement.learn_these', '/session', upToToday(count, budget))
          );
        }
      }
      const tappable = panel.childNodes.length > 0;
      const head = node(tappable ? 'button' : 'div', 'plc-group__head');
      head.appendChild(node('b', 'plc-group__count', fmt(count)));
      const labelKey =
        g === 'both' && !cjk ? 'placement.group_recognised_en' : 'placement.group_' + g;
      head.appendChild(node('span', 'plc-group__label', tr(labelKey)));
      li.appendChild(head);
      if (tappable) {
        head.type = 'button';
        head.setAttribute('aria-expanded', 'false');
        const chev = node('span', 'plc-group__chev', '›');
        chev.setAttribute('aria-hidden', 'true');
        head.appendChild(chev);
        li.appendChild(panel);
        head.addEventListener('click', function () {
          panel.hidden = !panel.hidden;
          head.setAttribute('aria-expanded', String(!panel.hidden));
          li.classList.toggle('is-open', !panel.hidden);
        });
      }
      ul.appendChild(li);
    });
    s.appendChild(ul);
    return s;
  }

  function bandSvg(range, n) {
    const NS = 'http://www.w3.org/2000/svg';
    const step = 14;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'plc-band');
    svg.setAttribute('viewBox', '0 0 ' + BAND_DOTS * step + ' 14');
    svg.setAttribute('role', 'img');
    svg.setAttribute(
      'aria-label',
      tr('placement.band_aria', { lo: fmt(range.lo), hi: fmt(range.hi), N: fmt(n) })
    );
    bandDots(range.lo, range.hi, n, BAND_DOTS).forEach(function (st, i) {
      const c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', String(i * step + step / 2));
      c.setAttribute('cy', '7');
      c.setAttribute('r', '5');
      c.setAttribute('class', 'plc-dot plc-dot--' + st);
      svg.appendChild(c);
    });
    return svg;
  }

  const LABEL_KEYS = {
    good: 'placement.label_good',
    medium: 'placement.label_medium',
    rough: 'placement.label_rough',
    low: 'placement.label_rough',
  };

  // The headline range: meaning-and-reading for zh/ja, meaning for en.
  function headline(r, cjk) {
    if (!r) return null;
    return cjk ? r.mr || r.m || null : r.m || null;
  }

  // Block 2: the range, its label and the band strip.
  function rangeBlock(result, cjk) {
    const t = result.this || {};
    const head = headline(t, cjk);
    if (!head) return null;
    const n = result.frame_n || 0;
    const s = block('plc-range', null);
    const fewer = head.lo <= 0 || head.label === 'fewer' || head.label === 'fewer_than';
    let text;
    if (fewer) {
      text = tr('placement.result_fewer', { hi: fmt(head.hi), N: fmt(n) });
    } else {
      let key = 'placement.result_m_en';
      if (cjk) key = t.mr ? 'placement.result_mr' : 'placement.result_m';
      text = tr(key, {
        N: fmt(n),
        language: tr('lang_select.name_' + langCode(state.lang)),
        lo: fmt(head.lo),
        hi: fmt(head.hi),
      });
    }
    s.appendChild(node('p', 'plc-range__text', keepRanges(text)));
    const labelKey = LABEL_KEYS[head.label] || (fewer ? 'placement.label_rough' : null);
    if (labelKey) s.appendChild(node('span', 'ld-tag plc-range__label', tr(labelKey)));
    if (n > 0) s.appendChild(bandSvg(head, n));
    return s;
  }

  // Block 3: the gaps, each only when the server kept it (lo above threshold).
  function gapBlock(result, cjk, zh) {
    if (!cjk) return null;
    const t = result.this || {};
    const lines = [];
    if (zh && t.tone_gap) {
      lines.push([
        'plc-gap--tones',
        tr('placement.result_tone_gap', { lo: fmt(t.tone_gap.lo), hi: fmt(t.tone_gap.hi) }),
      ]);
    }
    if (t.gap) {
      lines.push([
        'plc-gap--reading',
        tr('placement.result_gap', { lo: fmt(t.gap.lo), hi: fmt(t.gap.hi) }),
      ]);
    }
    if (!lines.length) return null;
    const s = block('plc-gaps', null);
    lines.forEach(function (l) {
      s.appendChild(node('p', 'plc-gap ' + l[0], keepRanges(l[1])));
    });
    return s;
  }

  const VERDICT_KEYS = {
    up: 'placement.retake_up',
    clearly_up: 'placement.retake_up',
    down: 'placement.retake_down',
    clearly_down: 'placement.retake_down',
  };

  // Block 4: only on a retake (result.previous).
  function retakeBlock(result, cjk) {
    const prev = result.previous;
    if (!prev) return null;
    const s = block('plc-retake', tr('placement.retake_title'));
    const current = headline(result.this, cjk);
    const before = headline(prev, cjk);
    if (current) {
      s.appendChild(
        node('p', 'plc-retake__this', tr('placement.retake_this', { range: fmtRange(current) }))
      );
    }
    if (before) {
      const date = fmtDate(prev.ended_at);
      s.appendChild(
        node(
          'p',
          'plc-retake__previous',
          tr('placement.retake_previous', { date: date, range: fmtRange(before) })
        )
      );
    }
    s.appendChild(
      node('p', 'plc-retake__verdict', tr(VERDICT_KEYS[prev.verdict] || 'placement.retake_same'))
    );
    // `combined` has the shape of `this`, and is null when it equals it.
    const comb = headline(result.combined, cjk);
    if (comb) {
      s.appendChild(
        node(
          'p',
          'plc-retake__combined',
          tr('placement.retake_combined', { range: fmtRange(comb) })
        )
      );
    }
    return s;
  }

  // Block 5: next steps. The two word actions only when they have words.
  function nextBlock(result, cjk, budget) {
    const words = result.words || {};
    const s = block('plc-next', tr('placement.next_title'));
    const list = node('div', 'plc-next__list');
    const readings = (words.tones_not_yet || 0) + (words.meaning_only || 0);
    if (cjk && readings > 0) {
      list.appendChild(
        actionLink('placement.practise_readings', '/session', upToToday(readings, budget))
      );
    }
    if ((words.not_yet || 0) > 0) {
      list.appendChild(
        actionLink('placement.learn_these', '/session', upToToday(words.not_yet, budget))
      );
    }
    list.appendChild(actionLink('placement.next_session', '/session'));
    list.appendChild(actionLink('placement.next_check', '/calibration'));
    s.appendChild(list);
    return s;
  }

  // Block 6: how this works (closed by default).
  function howBlock(cjk, zh) {
    const d = node('details', 'plc-block ld-card plc-how');
    d.appendChild(node('summary', 'plc-how__title', tr('placement.how_title')));
    d.appendChild(
      node('p', 'plc-how__body', tr(cjk ? 'placement.how_body_cjk' : 'placement.how_body_en'))
    );
    if (zh) d.appendChild(node('p', 'plc-how__body plc-how__tones', tr('placement.how_tones_zh')));
    return d;
  }

  function flagsBlock(result) {
    const notes = [];
    if (result.ended_early) notes.push(['plc-flag--early', 'placement.ended_early']);
    if (result.fast) notes.push(['plc-flag--fast', 'placement.fast_flag']);
    if (!notes.length) return null;
    const s = node('div', 'plc-flags');
    notes.forEach(function (f) {
      s.appendChild(node('p', 'ld-note ld-note--warn plc-flag ' + f[0], tr(f[1])));
    });
    return s;
  }

  function showResult(result, opts) {
    const o = opts || {};
    clearAdvance();
    state.awaitingAdvance = false;
    state.locked = false;
    state.item = null;
    state.result = result;
    state.resultOpts = o;
    if (LANG_CODE[result.word_language_id]) state.lang = result.word_language_id;
    if (LANG_CODE[result.definition_language_id]) state.defLang = result.definition_language_id;
    const cjk = isCjk();
    const zh = state.lang === 1;
    const lists = groupLists(o.wordLists, o.sessionId);

    const root = el.result;
    root.innerHTML = '';
    root.appendChild(node('h1', 'ld-h1 plc-result__title', tr('placement.result_title')));
    [
      groupBlock(result, lists, cjk, zh, o.budget),
      rangeBlock(result, cjk),
      gapBlock(result, cjk, zh),
      retakeBlock(result, cjk),
      nextBlock(result, cjk, o.budget),
      howBlock(cjk, zh),
      flagsBlock(result),
    ].forEach(function (b) {
      if (b) root.appendChild(b);
    });

    el.newBtn.hidden = !o.unseen;
    show('result', 'resultActions');
  }

  // ---- events ------------------------------------------------------

  el.startBtn.addEventListener('click', start);
  el.idkBtn.addEventListener('click', function () {
    answer(null);
  });
  el.nextBtn.addEventListener('click', advance);
  el.stopBtn.addEventListener('click', endNow);
  el.endBtn.addEventListener('click', endNow);
  el.keepGoing.addEventListener('click', function () {
    el.confirm.hidden = true;
  });
  el.newBtn.addEventListener('click', showIntro);
  el.retryBtn.addEventListener('click', function () {
    const fn = state.retry;
    state.retry = null;
    if (fn) fn();
  });

  // 1–4 pick an option, 0 is "I don't know" (not on a forced guess), Enter /
  // Space / → move on from a reveal, Enter starts from the intro. Buttons are
  // never focused by the page, so a key does not also fire a native click.
  document.addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;

    if (state.view === 'intro') {
      if (e.key === 'Enter') {
        e.preventDefault();
        start();
      }
      return;
    }
    if (state.awaitingAdvance) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowRight') {
        e.preventDefault();
        advance();
      }
      return;
    }
    if (state.view !== 'item' || state.locked || !state.item) return;
    if (e.key === '0') {
      if (idkAllowed(state.item)) {
        e.preventDefault();
        answer(null);
      }
      return;
    }
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= (state.item.options || []).length) {
      e.preventDefault();
      answer(n - 1);
    }
  });

  // A UI-language switch re-renders what this script wrote (data-i18n text
  // follows by itself).
  document.addEventListener('languageChanged', function () {
    setHeader();
    if (state.view === 'intro') showIntro();
    else if (state.view === 'item' && state.item) {
      el.instruction.textContent = tr(instructionKey(state.item));
      updateProgress();
    } else if (state.view === 'reveal') updateProgress();
    else if (state.view === 'result' && state.result) showResult(state.result, state.resultOpts);
    else if (state.view === 'message' && state.messageKey) {
      el.message.textContent = tr(state.messageKey);
    }
  });

  // Every screen is rendered from the translations, so they come first. The
  // loading line until then is the template's own (data-i18n) text.
  function i18nReady() {
    const i18n = window.LinguaI18n;
    if (!i18n || typeof i18n.init !== 'function') return Promise.resolve();
    return Promise.resolve(i18n.init()).catch(function () {});
  }

  async function boot() {
    state.lang = wordLanguageId();
    state.defLang = definitionLanguageId();
    const ready = i18nReady();

    // A frozen result by id (a link to a past placement).
    const sid = new URLSearchParams(window.location.search).get('session_id');
    if (sid) {
      const r = (await Promise.all([getResult(sid), ready]))[0];
      setHeader();
      if (r.ok && r.data && r.data.result) {
        return showResult(r.data.result, resultOpts(r.data, { sessionId: sid }));
      }
    }

    // An abandoned placement that had enough answers has a result the learner
    // has not seen: show it first, once (/latest marks it seen).
    const latest = (
      await Promise.all([call('GET', '/latest?word_language_id=' + state.lang), ready])
    )[0];
    setHeader();
    if (latest.status === 404) return showUnavailable();
    if (latest.ok && latest.data && latest.data.result && latest.data.unseen) {
      return showResult(
        latest.data.result,
        resultOpts(latest.data, { sessionId: latest.data.session_id || null, unseen: true })
      );
    }
    return showIntro();
  }

  // Exactly once, whether this runs before DOMContentLoaded or after it.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
