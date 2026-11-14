(function () {
  'use strict';

  // dim_languages ids. `es` is a UI locale only — it has no dim_languages row,
  // so a Spanish-speaking learner reads English definitions rather than none.
  const LOCALE_TO_LANGUAGE_ID = { zh: 1, en: 2, ja: 3 };

  const el = {
    header: document.getElementById('calHeader'),
    loading: document.getElementById('calLoading'),
    stage: document.getElementById('calStage'),
    prompt: document.getElementById('calPrompt'),
    reading: document.getElementById('calReading'),
    options: document.getElementById('calOptions'),
    instruction: document.querySelector('.cal-instruction'),
    answered: document.getElementById('calAnswered'),
    accuracy: document.getElementById('calAccuracy'),
    results: document.getElementById('calResults'),
    resultLevel: document.getElementById('calResultLevel'),
    resultSub: document.getElementById('calResultSub'),
    resultNote: document.getElementById('calResultNote'),
    curve: document.getElementById('calCurve'),
    rating: document.getElementById('calRating'),
    empty: document.getElementById('calEmpty'),
    skipBtn: document.getElementById('calSkipBtn'),
    nextBtn: document.getElementById('calNextBtn'),
    nextHint: document.getElementById('calNextHint'),
    finishBtn: document.getElementById('calFinishBtn'),
    restartBtn: document.getElementById('calRestartBtn'),
    modeToggle: document.getElementById('calModeToggle'),
  };

  // TASK-771. Items are fetched ahead and rendered from a queue, so answering
  // one is never followed by waiting for the next. Sizes, not tuning knobs:
  //   FIRST_BATCH small, because it is the only fetch the learner waits on;
  //   LOW_WATER > 0, so a top-up starts while there are still items to answer;
  //   BATCH comfortably larger than anyone answers during one round trip.
  const FIRST_BATCH = 3;
  const BATCH = 12;
  const LOW_WATER = 6;
  //: How long a CORRECT answer stays on screen before moving on. A wrong one
  //: has no timer at all — see `advance`.
  const CORRECT_PAUSE_MS = 450;

  const state = {
    sessionId: null,
    item: null,
    queue: [],
    topping: false,
    topPromise: null,
    exhausted: false,
    // True between revealing the answer and moving on. The gate that stops a
    // stray keypress from consuming two items.
    awaitingAdvance: false,
    advanceTimer: null,
    locked: false,
    shownAt: 0,
    ability: null,
    mode: 'definition',
  };

  // Readings are only stored for Chinese and Japanese, so the toggle is
  // disabled rather than hidden for English — a control that vanishes reads
  // like a bug, one that is visibly unavailable reads like a limitation.
  function pronunciationAvailable() {
    return wordLanguageId() === 1 || wordLanguageId() === 3;
  }

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  const BADGE_SVG = {
    spin: '<svg viewBox="0 0 24 24"><circle class="spin" cx="12" cy="12" r="9" fill="none" stroke="var(--brand-primary, #4f46e5)" stroke-width="3" stroke-linecap="round" stroke-dasharray="40 60"/></svg>',
    tick: '<svg viewBox="0 0 24 24"><path class="draw" d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="var(--success, #16a34a)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    cross:
      '<svg viewBox="0 0 24 24"><path class="draw" d="M6 6l12 12" fill="none" stroke="var(--danger, #dc2626)" stroke-width="3" stroke-linecap="round"/><path class="draw second" d="M18 6L6 18" fill="none" stroke="var(--danger, #dc2626)" stroke-width="3" stroke-linecap="round"/></svg>',
  };

  function setBadge(btn, svg) {
    const badge = btn.querySelector('.cal-badge');
    if (badge) badge.innerHTML = svg;
  }

  function wordLanguageId() {
    const id = parseInt(localStorage.getItem('selectedLanguageId'), 10);
    return id === 1 || id === 2 || id === 3 ? id : 3;
  }

  function definitionLanguageId() {
    const locale =
      (window.LinguaI18n && window.LinguaI18n.currentLocale) ||
      document.documentElement.lang ||
      'en';
    return LOCALE_TO_LANGUAGE_ID[String(locale).slice(0, 2)] || 2;
  }

  function show(node) {
    [el.loading, el.stage, el.results, el.empty].forEach((n) => {
      n.style.display = 'none';
    });
    if (node) node.style.display = '';
  }

  async function api(path, opts) {
    const resp = await window.authFetch(path, opts);
    const data = await resp.json();
    if (!resp.ok || (data && data.status === 'error')) {
      throw new Error((data && data.error) || 'request failed');
    }
    return data;
  }

  async function startSession() {
    show(el.loading);
    el.loading.textContent = tr('calibration.loading');
    el.header.style.display = 'none';
    clearAdvance();
    hideAdvanceButton();
    // Everything buffered belongs to the session being replaced.
    state.queue = [];
    state.topping = false;
    state.topPromise = null;
    state.exhausted = false;
    state.item = null;
    try {
      const data = await api('/api/calibration/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          word_language_id: wordLanguageId(),
          definition_language_id: definitionLanguageId(),
          mode: state.mode,
        }),
      });
      state.sessionId = data.session_id;
      state.ability = null;
      updateStats({ answered: 0, correct: 0 });
      // Ask for a few, not a full batch: this is the one fetch the learner
      // actually waits on. The rest arrive while they answer these.
      await topUp(FIRST_BATCH);
      showNext();
    } catch (err) {
      el.loading.textContent = tr('calibration.error_start');
      show(el.loading);
    }
  }

  // Fetch more items into the queue. Safe to call at any time: it collapses
  // into the in-flight request rather than starting a second one.
  function topUp(count) {
    if (state.exhausted || !state.sessionId) return Promise.resolve();
    if (state.topping) return state.topPromise || Promise.resolve();

    state.topping = true;
    const sid = state.sessionId;
    state.topPromise = api(
      '/api/calibration/next?session_id=' + encodeURIComponent(sid) + '&count=' + count
    )
      .then(function (data) {
        // A restart or mode switch may have replaced the session while
        // this was in flight. Those items belong to a run we left.
        if (sid !== state.sessionId) return;
        const items = (data && data.items) || [];
        state.queue.push.apply(state.queue, items);
        // `exhausted` means the dictionary is finished. A batch that
        // merely built nothing is also the end of the road for us, but
        // only once the queue has drained.
        if (data && (data.exhausted || items.length === 0)) {
          state.exhausted = true;
        }
      })
      .catch(function () {
        /* handled by whoever is waiting for an item */
      })
      .then(function () {
        if (sid === state.sessionId) state.topping = false;
      });
    return state.topPromise;
  }

  function showNext() {
    clearAdvance();
    hideAdvanceButton();
    state.awaitingAdvance = false;
    state.locked = false;
    state.item = null;

    // Start the refill BEFORE rendering, so it overlaps the time the learner
    // spends reading this item rather than the time after it.
    if (state.queue.length <= LOW_WATER) topUp(BATCH);

    const item = state.queue.shift();
    if (!item) {
      waitForItem();
      return;
    }
    state.item = item;
    renderItem(item);
  }

  // The queue ran dry. Either the run is over, or a fetch is still in flight —
  // the only case where the learner sees a spinner at all.
  async function waitForItem() {
    if (state.exhausted) {
      show(el.empty);
      el.header.style.display = 'none';
      return;
    }
    el.loading.textContent = tr('calibration.loading');
    show(el.loading);
    await topUp(BATCH);
    if (state.queue.length) {
      showNext();
      return;
    }
    if (state.exhausted) {
      show(el.empty);
      el.header.style.display = 'none';
      return;
    }
    el.loading.textContent = tr('calibration.error_item');
    show(el.loading);
  }

  function renderItem(item) {
    el.prompt.textContent = item.lemma || '';
    el.reading.textContent = item.pronunciation || '';
    el.reading.style.display = item.pronunciation ? '' : 'none';

    const isPron = item.mode === 'pronunciation';
    el.options.classList.toggle('pron', isPron);
    el.instruction.textContent = tr(
      isPron ? 'calibration.instruction_pronunciation' : 'calibration.instruction'
    );

    el.options.innerHTML = '';
    (item.options || []).forEach(function (opt) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cal-option';
      btn.dataset.position = String(opt.position);
      btn.innerHTML =
        escapeHtml(opt.definition) + '<span class="cal-badge" aria-hidden="true"></span>';
      btn.addEventListener('click', function () {
        answer(opt.position);
      });
      el.options.appendChild(btn);
    });

    el.header.style.display = '';
    show(el.stage);
    state.shownAt = Date.now();
  }

  function updateStats(ability) {
    const answered = (ability && ability.answered) || 0;
    const correct = (ability && ability.correct) || 0;
    el.answered.textContent = String(answered);
    el.accuracy.textContent = answered ? Math.round((correct / answered) * 100) + '%' : '—';
  }

  function clearAdvance() {
    if (state.advanceTimer) {
      clearTimeout(state.advanceTimer);
      state.advanceTimer = null;
    }
  }

  function showAdvanceButton() {
    // "I don't know" is meaningless once the answer is on screen.
    el.skipBtn.hidden = true;
    el.nextBtn.hidden = false;
    el.nextHint.hidden = false;
  }

  function hideAdvanceButton() {
    el.nextBtn.hidden = true;
    el.nextHint.hidden = true;
    el.skipBtn.hidden = false;
  }

  // The single way forward from a revealed answer, whether it came from the
  // timer, the button or a key. Guarded by `awaitingAdvance` so two of those
  // firing together cannot consume two items.
  function advance() {
    if (!state.awaitingAdvance) return;
    state.awaitingAdvance = false;
    clearAdvance();
    showNext();
  }

  async function answer(position) {
    if (state.locked || !state.item) return;
    state.locked = true;

    const buttons = Array.prototype.slice.call(el.options.querySelectorAll('.cal-option'));
    buttons.forEach((b) => {
      b.disabled = true;
    });

    // Acknowledge the click before the network call, not after it.
    const picked = buttons.find((b) => parseInt(b.dataset.position, 10) === position);
    el.options.classList.add('answered');
    if (picked) {
      picked.classList.add('picked');
      setBadge(picked, BADGE_SVG.spin);
    }

    let data;
    try {
      data = await api('/api/calibration/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: state.sessionId,
          response_id: state.item.response_id,
          position: position,
          latency_ms: Math.max(0, Date.now() - state.shownAt),
        }),
      });
    } catch (err) {
      el.options.classList.remove('answered');
      if (picked) {
        picked.classList.remove('picked');
        setBadge(picked, '');
      }
      buttons.forEach((b) => {
        b.disabled = false;
      });
      state.locked = false;
      return;
    }

    // Always reveal the key, including on a skip: being shown the answer is
    // the only thing the learner gets back from an item they could not do.
    buttons.forEach(function (b) {
      const pos = parseInt(b.dataset.position, 10);
      if (pos === data.correct_position) b.classList.add('correct');
      else if (pos === position && !data.is_correct) b.classList.add('wrong');
    });
    if (picked) {
      picked.classList.remove('picked');
      setBadge(picked, data.is_correct ? BADGE_SVG.tick : BADGE_SVG.cross);
    }
    // On a wrong answer or a skip, draw the tick on the key as well.
    if (!data.is_correct) {
      const key = buttons.find((b) => parseInt(b.dataset.position, 10) === data.correct_position);
      if (key) setBadge(key, BADGE_SVG.tick);
    }

    state.ability = data;
    updateStats(data);

    state.awaitingAdvance = true;
    if (data.is_correct) {
      // Right answer: nothing to study, so it moves on by itself. A key
      // press still skips the pause.
      state.advanceTimer = setTimeout(advance, CORRECT_PAUSE_MS);
    } else {
      // Wrong, or skipped. This is the one moment in the run where there
      // is something to read — which option was right, and how close the
      // one they picked was to it. A timer would decide for them how long
      // that takes, so the learner moves on when they are ready.
      showAdvanceButton();
    }
  }

  function bandLabel(band) {
    return (
      {
        1: '< 3.0',
        2: '3.0–3.5',
        3: '3.5–4.0',
        4: '4.0–4.5',
        5: '4.5–5.0',
        6: '5.0–5.5',
        7: '5.5+',
      }[band] || String(band)
    );
  }

  function renderResults(ability) {
    const a = ability || {};
    const z85 = a.ability_zipf_85;

    if (z85 != null) {
      // Show the uncertainty, not just the point estimate. At 60 answers
      // the standard error is still ~0.27 Zipf, and a bare two-decimal
      // number reads far more precise than the measurement actually is.
      const sd = a.ability_zipf_85_sd;
      el.resultLevel.textContent =
        Number(z85).toFixed(2) + (sd != null ? ' ± ' + Number(sd).toFixed(2) : '');
      el.resultSub.textContent = tr('calibration.result_zipf_sub');
    } else {
      el.resultLevel.textContent = a.answered
        ? Math.round(((a.correct || 0) / a.answered) * 100) + '%'
        : '—';
      el.resultSub.textContent = tr('calibration.result_not_enough');
    }

    // The curve is the evidence. Showing it beside the headline number is the
    // point: a single figure derived from four answers should not look like a
    // single figure derived from eighty.
    el.curve.innerHTML = '';
    (a.bands || []).forEach(function (b) {
      const row = document.createElement('div');
      row.className = 'cal-band';
      const pct = Math.round((b.known_share || 0) * 100);
      const thin = (b.n || 0) < 3 ? ' thin' : '';
      row.innerHTML =
        '<span class="cal-band-label">' +
        escapeHtml(bandLabel(b.band)) +
        '</span>' +
        '<span class="cal-band-track"><span class="cal-band-fill' +
        thin +
        '" style="width:' +
        pct +
        '%"></span></span>' +
        '<span class="cal-band-n">' +
        pct +
        '% · n=' +
        (b.n || 0) +
        '</span>';
      el.curve.appendChild(row);
    });

    const notes = [tr('calibration.note_curve')];
    if (a.confidence === 'none' || a.confidence === 'low') {
      notes.push(tr('calibration.note_low_confidence'));
    }
    el.resultNote.textContent = notes.join(' ');
    renderRating(a.rating_decisions);

    el.header.style.display = 'none';
    show(el.results);
  }

  // A translated string, or `fallback` when the key is missing (tr returns the
  // key itself in that case).
  function trOr(key, fallback, params) {
    const text = tr(key, params);
    return text === key ? fallback : text;
  }

  // TASK-752: show what this result did to test difficulty — including a
  // refusal and its reason, so a skipped write is visible rather than silent.
  // The server owns every rule; this only renders its decisions.
  function renderRating(decisions) {
    el.rating.innerHTML = '';
    if (!Array.isArray(decisions) || !decisions.length) {
      el.rating.hidden = true;
      return;
    }
    const title = document.createElement('div');
    title.className = 'cal-rating-title';
    title.textContent = tr('calibration.rating_title');
    el.rating.appendChild(title);
    decisions.forEach(function (d) {
      const type = trOr('calibration.rating_type_' + d.test_type, d.test_type);
      let text;
      if (d.source === 'calibration_seed') {
        text = tr('calibration.rating_set', { type: type, to: d.elo_after });
      } else if (d.source === 'calibration_correct') {
        text = tr('calibration.rating_changed', {
          type: type,
          from: d.elo_before,
          to: d.elo_after,
        });
      } else {
        text = tr('calibration.rating_unchanged', {
          type: type,
          reason: trOr('calibration.rating_reason_' + d.reason, d.reason),
        });
      }
      const row = document.createElement('div');
      row.className = 'cal-rating-row';
      row.textContent = text;
      el.rating.appendChild(row);
    });
    el.rating.hidden = false;
  }

  async function finish() {
    // Whatever is still queued was served but never answered. /end discards
    // those server-side (calibration_discard_unanswered), so dropping them
    // here just keeps the two sides agreeing.
    clearAdvance();
    state.awaitingAdvance = false;
    state.queue = [];
    try {
      const data = await api('/api/calibration/end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: state.sessionId }),
      });
      renderResults(data.ability);
    } catch (err) {
      renderResults(state.ability);
    }
  }

  el.modeToggle.addEventListener('click', function (e) {
    const btn = e.target.closest('button[data-mode]');
    if (!btn || btn.disabled) return;
    const mode = btn.dataset.mode;
    if (mode === state.mode) return;
    state.mode = mode;
    syncModeToggle();
    // A mode switch is a different measurement, so it starts a new session
    // rather than mixing two kinds of item into one ability curve.
    startSession();
  });

  function syncModeToggle() {
    const pronBtn = el.modeToggle.querySelector('button[data-mode="pronunciation"]');
    if (pronBtn) {
      pronBtn.disabled = !pronunciationAvailable();
      pronBtn.title = pronBtn.disabled ? tr('calibration.mode_pronunciation_unavailable') : '';
    }
    if (!pronunciationAvailable() && state.mode === 'pronunciation') {
      state.mode = 'definition';
    }
    el.modeToggle.querySelectorAll('button[data-mode]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.mode === state.mode);
    });
  }

  el.skipBtn.addEventListener('click', function () {
    answer(null);
  });
  el.nextBtn.addEventListener('click', advance);
  el.finishBtn.addEventListener('click', finish);
  el.restartBtn.addEventListener('click', startSession);

  // Number keys 1-4 pick an option; Enter / Space move on from a revealed
  // answer. Together they are the fastest way through a long run, and they are
  // why the button is never focused: a focused button would turn one Space
  // into both a native click and this handler.
  document.addEventListener('keydown', function (e) {
    if (el.stage.style.display === 'none') return;

    if (state.awaitingAdvance) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowRight') {
        e.preventDefault();
        advance();
      }
      return;
    }
    if (state.locked) return;

    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= 4) {
      const btn = el.options.querySelectorAll('.cal-option')[n - 1];
      if (btn) btn.click();
    }
  });

  function boot() {
    syncModeToggle();
    startSession();
  }
  // Exactly once, whether this runs before DOMContentLoaded (deferred or
  // parser-inserted) or after it.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
