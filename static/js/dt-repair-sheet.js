/**
 * DT guided self-repair: the app-style pop-up (wiki/features/dt-guided-self-repair.tech.md §8).
 *
 * After Submit the feedback opens as a full-screen sheet over the exercise (a centred 420 px card
 * on wide screens). One step per screen, three fixed zones (header with progress and close, stage,
 * action area), no scrolling. Each flagged sentence is a "fix" step: the learner's own sentence in
 * an editable field, an optional hint ladder, and a Check button that asks the server to re-check
 * the revision. The answer is only ever shown after the server hands it over (reveal).
 *
 * Exposed as a plain global (window.DTRepairSheet), like window.DTErrorCard, because the standalone
 * DT page is a classic script while the session players are ES modules.
 *
 *   DTRepairSheet.open({ mode: 'pass'|'daily', session, items, fetch, returnFocus, onDone,
 *                        l1, l2, animate, autoAdvance }) -> { close() }
 *
 * Every request and response shape is the contract in tech §4. Nothing here invents a field.
 * Every failure degrades to a usable path (retry, the answer screen, or the host's own result view).
 */
(function () {
  'use strict';

  const BASE = '/api/dual-translation/repair';
  const DEFAULT_AUTO_MS = 1600;
  const CHECK_TIMEOUT_MS = 7000;
  const CALL_TIMEOUT_MS = 10000;
  const FINISH_TIMEOUT_MS = 6000;
  const SURFACE = { pass: 'repair_pass', daily: 'daily_practice' };

  const ICON = {
    pen: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 17l1-4L14 3l3 3L7 16l-4 1z"/></svg>',
    bulb: '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 14a5.5 5.5 0 116 0v2H7v-2zM8 19h4"/></svg>',
    again:
      '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 10a6 6 0 11-2-4.5M14 2v4h-4"/></svg>',
    tick: '<svg width="44" height="44" viewBox="0 0 44 44" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 23l8 8 14-17"/></svg>',
    dash: '<svg width="44" height="44" viewBox="0 0 44 44" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round" aria-hidden="true"><path d="M12 22h20"/></svg>',
    close:
      '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 4l12 12M16 4L4 16"/></svg>',
  };

  // ------------------------------------------------------------------ helpers
  function fill(text, params) {
    return params
      ? String(text).replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m))
      : String(text);
  }

  // LinguaI18n.t echoes the key on a miss, so a miss falls back to the English text.
  function tr(key, params, fallback) {
    const i18n = typeof window !== 'undefined' ? window.LinguaI18n : null;
    if (i18n && typeof i18n.t === 'function') {
      const v = i18n.t(key, params);
      if (v && v !== key) return v;
    }
    return fill(fallback || key, params);
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
    );
  }

  // The client-side twin of the server's revision normalisation (tech §4.6).
  function norm(s) {
    return String(s == null ? '' : s)
      .normalize('NFC')
      .replace(/\r\n|\n|\t/g, ' ')
      .replace(/ {2,}/g, ' ')
      .trim();
  }

  function uuid() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      try {
        return window.crypto.randomUUID();
      } catch {
        /* insecure context: fall through */
      }
    }
    if (window.ActiveTimer && typeof window.ActiveTimer.newEventId === 'function') {
      return window.ActiveTimer.newEventId();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.floor(Math.random() * 16);
      return (c === 'x' ? r : (r & 3) | 8).toString(16);
    });
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function mq(query) {
    try {
      return !!(window.matchMedia && window.matchMedia(query).matches);
    } catch {
      return false;
    }
  }

  // Server offsets are Python code points; JS strings are UTF-16. These two helpers keep marks
  // right for characters outside the BMP.
  function cpToIdx(str, n) {
    let idx = 0;
    let seen = 0;
    while (idx < str.length && seen < n) {
      idx += str.codePointAt(idx) > 0xffff ? 2 : 1;
      seen += 1;
    }
    return idx;
  }

  function mergeRanges(ranges) {
    const sorted = (ranges || [])
      .filter((r) => Array.isArray(r) && r[1] > r[0])
      .map((r) => [r[0], r[1]])
      .sort((a, b) => a[0] - b[0]);
    const out = [];
    sorted.forEach((r) => {
      const last = out[out.length - 1];
      if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
      else out.push(r);
    });
    return out;
  }

  // Wrap each code-point range of `text` in <tag>, escaping everything.
  function markup(text, ranges, tag) {
    const chars = Array.from(String(text || ''));
    const merged = mergeRanges(ranges);
    if (!merged.length) return esc(chars.join(''));
    let html = '';
    let pos = 0;
    merged.forEach((r) => {
      const s = Math.max(pos, Math.min(r[0], chars.length));
      const e = Math.min(r[1], chars.length);
      if (e <= s) return;
      html += esc(chars.slice(pos, s).join(''));
      html += `<${tag}>${esc(chars.slice(s, e).join(''))}</${tag}>`;
      pos = e;
    });
    return html + esc(chars.slice(pos).join(''));
  }

  function uiLang() {
    const i18n = window.LinguaI18n;
    if (i18n && typeof i18n.currentLanguage === 'function') return i18n.currentLanguage() || 'en';
    return (document.documentElement && document.documentElement.lang) || 'en';
  }

  // "From your translation on {day}": a weekday within the last 6 days, else "Nov 3".
  function dayLabel(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    if (!m) return '';
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diff = Math.round((today - d) / 86400000);
    const opts = diff >= 0 && diff <= 6 ? { weekday: 'long' } : { month: 'short', day: 'numeric' };
    try {
      return new Intl.DateTimeFormat(uiLang(), opts).format(d);
    } catch {
      return String(iso);
    }
  }

  // The nearest occurrence of the "where" text to its reported offset, as a UTF-16 index (or -1).
  function locate(value, where) {
    if (!where || !where.text) return -1;
    const near = cpToIdx(value, where.start || 0);
    let best = -1;
    let from = 0;
    for (;;) {
      const k = value.indexOf(where.text, from);
      if (k < 0) break;
      if (best < 0 || Math.abs(k - near) < Math.abs(best - near)) best = k;
      from = k + 1;
    }
    return best;
  }

  // ---------------------------------------------------------------- the sheet
  let current = null; // the one open sheet

  function open(opts) {
    if (current) current.dispose();
    const inst = createSheet(opts || {});
    current = inst;
    return { close: () => inst.requestClose(), dispose: () => inst.dispose() };
  }

  function createSheet(opts) {
    const mode = opts.mode === 'daily' ? 'daily' : 'pass';
    const surface = SURFACE[mode];
    const session = mode === 'pass' ? opts.session || {} : null;
    const doFetch = opts.fetch || (typeof window !== 'undefined' && window.authFetch);
    const animate =
      opts.animate !== false &&
      !mq('(prefers-reduced-motion: reduce)') &&
      !document.documentElement.classList.contains('dtr-noanim');
    const reduced = mq('(prefers-reduced-motion: reduce)');
    const autoMs =
      opts.autoAdvance === false || reduced
        ? 0
        : session && session.auto_advance_ms != null
          ? session.auto_advance_ms
          : DEFAULT_AUTO_MS;
    const l2 = (session && session.l2) || opts.l2 || '';
    const l1 = (session && session.l1) || opts.l1 || '';

    const S = {
      mode,
      view: null,
      i: 0,
      tk: 0,
      busy: false,
      closed: false,
      finishP: null,
      summary: null,
      timer: null,
      steps: (mode === 'pass' ? session.steps || [] : opts.items || []).map(makeStep),
    };

    function makeStep(st) {
      const level = st.hint_level | 0;
      const start = st.last_text != null ? st.last_text : st.learner_sentence || '';
      return Object.assign({}, st, {
        unsure: st.step_kind === 'unsure',
        direct: st.step_kind === 'direct',
        rungs: Array.isArray(st.hint_rungs) ? st.hint_rungs : [],
        value: start,
        checkedText: start,
        where: st.where || null,
        hintLevel: level,
        maxLevel: level,
        baseHints:
          mode === 'daily'
            ? (Array.isArray(st.hint_rungs) ? st.hint_rungs : []).filter((r) => r <= level).length
            : 0,
        hintsAsked: 0,
        noMore: false,
        hint: null,
        msg: '',
        errStreak: 0,
        hintFails: 0,
        pendingCheck: null,
        pointStale: false,
        closedNow: st.state === 'closed',
        outcome: st.outcome || null,
        answer: null,
        openP: null,
        tShown: 0,
        tPrev: 0,
        tFirstEdit: 0,
        activeAcc: 0,
        eventId: null,
        timer: null,
        timerAcc: 0,
      });
    }

    // ------------------------------------------------------------- DOM shell
    const scrim = document.createElement('div');
    scrim.className = 'dtr-scrim';
    scrim.innerHTML = `
      <section class="dtr-sheet" id="dtr-sheet" role="dialog" aria-modal="true" aria-labelledby="dtr-h" data-mode="${mode}">
        <header class="dtr-hd">
          <button class="dtr-x" id="dtr-close" type="button" data-act="close" aria-label="${esc(tr('dt_repair.close', null, 'Close'))}">${ICON.close}</button>
          <div class="dtr-dots" id="dtr-dots"></div>
        </header>
        <div class="dtr-stage" id="dtr-stage"></div>
        <footer class="dtr-act" id="dtr-act"></footer>
        <div class="dtr-sr" id="dtr-live" role="status" aria-live="polite"></div>
      </section>`;
    const sheet = scrim.firstElementChild;
    const stageEl = sheet.querySelector('#dtr-stage');
    const actEl = sheet.querySelector('#dtr-act');
    const dotsEl = sheet.querySelector('#dtr-dots');
    const liveEl = sheet.querySelector('#dtr-live');
    const liveNode = document.createTextNode('');
    liveEl.appendChild(liveNode);
    let liveToggle = false;
    const $ = (sel) => sheet.querySelector(sel);

    // Whole-session timer (pass): one credit for the repair time at finish.
    const passTimer =
      mode === 'pass' && window.ActiveTimer && typeof window.ActiveTimer.create === 'function'
        ? window.ActiveTimer.create()
        : null;
    const passEventId = uuid();

    const cur = () => S.steps[S.i];

    function live(text) {
      liveToggle = !liveToggle;
      liveNode.nodeValue = String(text || '') + (liveToggle ? '' : ' ');
    }

    // -------------------------------------------------------------- network
    // Resolves {ok, status, data, network}; never rejects.
    async function api(path, body, timeoutMs) {
      const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timer = ctl ? setTimeout(() => ctl.abort(), timeoutMs || CALL_TIMEOUT_MS) : null;
      try {
        const res = await doFetch(BASE + path, {
          method: 'POST',
          body: JSON.stringify(body || {}),
          signal: ctl ? ctl.signal : undefined,
        });
        let data = await res.json().catch(() => ({}));
        if (data && data.data && typeof data.data === 'object' && !('status' in data)) {
          data = data.data;
        }
        return { ok: !!res.ok, status: res.status, data: data || {}, network: false };
      } catch {
        return { ok: false, status: 0, data: {}, network: true };
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    function sincePrev(s) {
      const now = Date.now();
      const ms = s.tPrev ? Math.max(0, Math.min(3600000, now - s.tPrev)) : 0;
      s.tPrev = now;
      return ms;
    }

    // Per-item active time (daily practice credits it on the call that closes the sitting).
    function startItemTimer(s) {
      s.eventId = uuid();
      s.timerAcc = 0;
      if (window.ActiveTimer && typeof window.ActiveTimer.create === 'function') {
        s.timer = window.ActiveTimer.create();
        s.timer.start();
      }
    }

    function activeFields(s) {
      if (mode !== 'daily' || !s.timer) return {};
      s.timerAcc += s.timer.stop();
      s.timer.start();
      return { active_ms: s.timerAcc, client_event_id: s.eventId };
    }

    function itemBody(s, extra) {
      return Object.assign({ surface, since_prev_ms: sincePrev(s) }, activeFields(s), extra || {});
    }

    // open / hint / check / reveal / dispute / skip share the "sitting must be open" wrapper.
    async function itemCall(s, action, body, timeoutMs) {
      if (s.openP) await s.openP;
      let r = await api(`/items/${s.item_id}/${action}`, body, timeoutMs);
      if (mode === 'daily' && r.status === 409 && r.data.error_code === 'NOT_OPENED') {
        s.openP = openItem(s);
        await s.openP;
        r = await api(`/items/${s.item_id}/${action}`, body, timeoutMs);
      }
      return r;
    }

    async function openItem(s) {
      const r = await api(`/items/${s.item_id}/open`, itemBodyLite(s));
      if (!r.ok) {
        // Open is bookkeeping: carry on to the fix view (tech §8.9).
        console.warn('dt-repair: open failed', r.status);
        return null;
      }
      const st = r.data && r.data.step;
      if (st && S.steps[S.i] === s && !s.hintsAsked && !s.touched) {
        if (st.hint_level != null) {
          s.hintLevel = st.hint_level | 0;
          s.maxLevel = Math.max(s.maxLevel, s.hintLevel);
          if (mode === 'daily') s.baseHints = s.rungs.filter((x) => x <= s.hintLevel).length;
        }
        if (st.where) s.where = st.where;
        if (st.last_text != null && s.value === s.learner_sentence) {
          s.value = st.last_text;
          s.checkedText = st.last_text;
        }
        if (S.view === 'fix') refreshField();
      }
      return st || null;
    }

    function itemBodyLite(s) {
      return { surface, since_prev_ms: sincePrev(s) };
    }

    // ---------------------------------------------------------------- views
    function dots() {
      const showDots =
        ['fix', 'ok', 'kept', 'reveal', 'alt', 'answer_loading'].includes(S.view) &&
        S.steps.length > 1;
      dotsEl.innerHTML = showDots
        ? S.steps
            .map((_, k) => `<i class="${k < S.i ? 'dtr-done' : k === S.i ? 'dtr-cur' : ''}"></i>`)
            .join('') +
          `<span class="dtr-sr">${esc(tr('dt_repair.progress', { i: S.i + 1, n: S.steps.length }, 'Sentence {i} of {n}'))}</span>`
        : '';
    }

    function isLast() {
      for (let k = S.i + 1; k < S.steps.length; k++) if (!S.steps[k].closedNow) return false;
      return true;
    }

    function nextLabel() {
      return isLast() ? tr('dt_repair.finish', null, 'Finish') : tr('dt_repair.next', null, 'Next');
    }

    function primaryBtn(id, label, act) {
      return `<button class="dtr-btn dtr-primary" id="${id}" type="button" data-act="${act}">${esc(label)}</button>`;
    }

    function viewHtml(view) {
      const s = cur();
      if (view === 'result') {
        const n = S.steps.length;
        const q = S.steps.every((x) => x.unsure || x.direct);
        const key = `dt_repair.result_${q ? 'look' : 'fix'}_${n === 1 ? 'one' : 'many'}`;
        const fall = {
          one: q ? 'sentence to look at' : 'sentence to fix',
          many: q ? 'sentences to look at' : 'sentences to fix',
        };
        const nClean = session && session.n_clean > 0 ? session.n_clean : 0;
        return {
          stage: `<div class="dtr-moment"><div class="dtr-big" aria-hidden="true">${n}</div><h2 id="dtr-h" tabindex="-1"><span class="dtr-sr">${n} </span>${esc(tr(key, null, fall[n === 1 ? 'one' : 'many']))}</h2>${
            nClean
              ? `<p>${esc(tr('dt_repair.result_others_fine', { n: nClean }, 'The other {n} look fine.'))}</p>`
              : ''
          }</div>`,
          act: primaryBtn('dtr-go', tr('dt_repair.start', null, 'Start'), 'go'),
        };
      }
      if (view === 'clean') {
        return {
          stage: `<div class="dtr-moment"><div class="dtr-badge dtr-pop">${ICON.tick}</div><h2 id="dtr-h" tabindex="-1">${esc(tr('dt_repair.clean_title', null, 'No issues found'))}</h2><p>${esc(tr('dt_repair.clean_body', null, 'Nothing was flagged in your translation.'))}</p></div>`,
          act: primaryBtn('dtr-done', tr('dt_repair.done', null, 'Done'), 'done'),
        };
      }
      if (view === 'fix') return fixHtml(s);
      if (view === 'ok') {
        const n = s.hintsUsedNow != null ? Math.max(0, s.hintsUsedNow - s.baseHints) : s.hintsAsked;
        const sub =
          n === 0
            ? mode === 'daily'
              ? tr('dt_repair.fixed_no_more', null, 'Without any more help')
              : tr('dt_repair.fixed_own', null, 'On your own')
            : n === 1
              ? tr('dt_repair.fixed_hints_one', null, 'With 1 hint')
              : tr('dt_repair.fixed_hints_many', { n }, 'With {n} hints');
        return {
          stage: `<div class="dtr-moment"><div class="dtr-badge dtr-pop">${ICON.tick}</div><h2 id="dtr-h" tabindex="-1">${esc(tr('dt_repair.fixed', null, 'Fixed'))}</h2><p>${esc(sub)}</p></div>`,
          act: primaryBtn('dtr-next', nextLabel(), 'next'),
        };
      }
      if (view === 'kept') {
        return {
          stage: `<div class="dtr-moment"><div class="dtr-badge dtr-n dtr-pop">${ICON.dash}</div><h2 id="dtr-h" tabindex="-1">${esc(tr('dt_repair.kept_title', null, 'Kept as written'))}</h2><p>${esc(tr('dt_repair.kept_body', null, 'We’ll leave this one alone.'))}</p></div>`,
          act: primaryBtn('dtr-next', nextLabel(), 'next'),
        };
      }
      if (view === 'reveal' || view === 'alt') return answerHtml(s);
      if (view === 'answer_loading') {
        return {
          stage: `<div class="dtr-moment"><h2 id="dtr-h" class="dtr-sr" tabindex="-1">${esc(tr('dt_repair.loading', null, 'Loading…'))}</h2><span class="dtr-spin dtr-spinner-big" aria-hidden="true"></span></div>`,
          act: '',
        };
      }
      if (view === 'answer_failed') {
        return {
          stage: `<div class="dtr-moment"><h2 id="dtr-h" tabindex="-1">${esc(tr('dt_repair.answer_failed', null, 'Couldn’t load the answer.'))}</h2></div>`,
          act:
            primaryBtn('dtr-retry', tr('dt_repair.retry', null, 'Try again'), 'retry') +
            `<div class="dtr-quiet"><button class="dtr-txt" id="dtr-skip" type="button" data-act="skip">${esc(tr('dt_repair.skip_sentence', null, 'Skip this sentence'))}</button></div>`,
        };
      }
      if (view === 'summary') {
        const c = S.summary || clientTally();
        const title =
          mode === 'daily'
            ? tr('dt_repair.summary_daily_title', null, 'Practice done')
            : tr('dt_repair.summary_title', null, 'All done');
        const third =
          mode === 'daily'
            ? tr('dt_repair.summary_later', null, 'Back in practice later')
            : tr('dt_repair.summary_saved', null, 'Saved to practice');
        return {
          stage: `<div class="dtr-moment"><h2 id="dtr-h" tabindex="-1">${esc(title)}</h2><ul class="dtr-tally"><li><span>${esc(tr('dt_repair.summary_fixed', null, 'Fixed yourself'))}</span> <b>${c.fixed_yourself}</b></li><li><span>${esc(tr('dt_repair.summary_help', null, 'Needed help'))}</span> <b>${c.needed_help}</b></li><li><span>${esc(third)}</span> <b>${c.saved_to_practice}</b></li></ul></div>`,
          act: primaryBtn('dtr-done', tr('dt_repair.done', null, 'Done'), 'done'),
        };
      }
      return { stage: '', act: '' };
    }

    function promptText(s) {
      return s.prompt_l1 || (session && session.prompt_l1_passage) || '';
    }

    function promptHtml(s) {
      // The "look at the underlined part" cue on the prompt is not in the contract (no L1 span).
      return esc(promptText(s));
    }

    function hintLabel(s) {
      if (s.hintFails >= 2 || s.noMore || !nextRung(s))
        return tr('dt_repair.show_answer', null, 'Show answer');
      return s.hintsAsked > 0
        ? tr('dt_repair.hint_another', null, 'Another hint')
        : tr('dt_repair.hint_need', null, 'Need a hint?');
    }

    function nextRung(s) {
      return s.rungs.find((r) => r > s.hintLevel);
    }

    function fixHtml(s) {
      const label = s.unsure
        ? tr('dt_repair.label_unsure', null, 'This part may need another look')
        : tr('dt_repair.label_fix', null, 'Fix your sentence');
      const eyebrow =
        s.from_date != null && s.from_date !== ''
          ? `<p class="dtr-eyebrow">${esc(tr('dt_repair.from_date', { day: dayLabel(s.from_date) }, 'From your translation on {day}'))}</p>`
          : '';
      const pText = promptText(s);
      const prompt = pText
        ? `<button class="dtr-prompt" id="dtr-prompt" type="button" data-act="prompt" ${l1 ? `lang="${esc(l1)}"` : ''} tabindex="-1"><span>${promptHtml(s)}</span></button>`
        : '';
      const fine = tr('dt_repair.mine_fine', null, 'Mine is fine');
      const check = tr('dt_repair.check', null, 'Check');
      const act = s.unsure
        ? `<div class="dtr-pair"><button class="dtr-btn dtr-plain" id="dtr-fine" type="button" data-act="fine">${esc(fine)}</button><button class="dtr-btn dtr-plain" id="dtr-check" type="button" data-act="check">${esc(check)}</button></div>`
        : `<div class="dtr-quiet"><button class="dtr-txt" id="dtr-hint" type="button" data-act="hint">${esc(hintLabel(s))}</button><button class="dtr-txt" id="dtr-fine" type="button" data-act="fine">${esc(fine)}</button></div>${primaryBtn('dtr-check', s.errStreak >= 2 ? tr('dt_repair.show_answer', null, 'Show answer') : check, 'check')}`;
      return {
        stage:
          eyebrow +
          prompt +
          `<label class="dtr-lab" id="dtr-lab" for="dtr-ta" tabindex="-1">${ICON.pen}<span>${esc(label)}</span></label>` +
          `<div class="dtr-field" id="dtr-field" ${l2 ? `lang="${esc(l2)}"` : ''}><div class="dtr-mirror" id="dtr-mirror" aria-hidden="true"></div><textarea id="dtr-ta" rows="1" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" enterkeyhint="done" aria-describedby="dtr-slot">${esc(s.value)}</textarea></div>` +
          `<div class="dtr-slot" id="dtr-slot"></div>`,
        act,
      };
    }

    function answerHtml(s) {
      const a = s.answer || {};
      const heading =
        a.heading === 'no_issue'
          ? tr('dt_repair.compare_no_issue', null, 'No issue found. Compare:')
          : a.heading === 'disputed'
            ? tr('dt_repair.compare_disputed', null, 'Noted. Compare:')
            : tr('dt_repair.compare', null, 'Compare');
      const L = a.l2 || l2;
      const mine = markup(
        a.learner_sentence != null ? a.learner_sentence : s.learner_sentence,
        a.learner_marks,
        'del'
      );
      const ans = markup(a.answer_sentence, a.answer_marks, 'b');
      const lang = L ? ` lang="${esc(L)}"` : '';
      const why = a.explanation
        ? `<p class="dtr-why" ${a.explanation_lang ? `lang="${esc(a.explanation_lang)}"` : ''}>${esc(a.explanation)}</p>`
        : '';
      return {
        stage:
          `<div class="dtr-orig" id="dtr-orig"><h2 id="dtr-h" tabindex="-1">${esc(heading)}</h2>` +
          `<div class="dtr-cmp dtr-mine" id="dtr-cmp-mine"><span class="dtr-tag">${esc(tr('dt_repair.you_wrote', null, 'You wrote'))}</span><span class="dtr-sent"${lang}>${mine}</span></div>` +
          `<div class="dtr-cmp dtr-ans" id="dtr-cmp-ans"><span class="dtr-tag">${esc(tr('dt_repair.answer', null, 'Answer'))}</span><span class="dtr-sent"${lang}>${ans}</span></div>` +
          `${why}</div>`,
        act: primaryBtn('dtr-next', nextLabel(), 'next'),
      };
    }

    // ------------------------------------------------------------ rendering
    function render(view, opt) {
      clearTimeout(S.timer);
      S.view = view;
      S.tk += 1;
      const html = viewHtml(view);
      stageEl.innerHTML = html.stage;
      actEl.innerHTML = html.act;
      sheet.dataset.view = view;
      sheet.dataset.fieldState = '';
      sheet.dataset.i = String(S.i);
      sheet.setAttribute('aria-labelledby', view === 'fix' ? 'dtr-lab' : 'dtr-h');
      stageEl.classList.remove('dtr-hinted');
      dots();
      if (animate && !(opt && opt.quiet)) {
        [stageEl, actEl].forEach((el) => {
          el.classList.remove('dtr-in');
          void el.offsetWidth;
          el.classList.add('dtr-in');
        });
      }
      if (view === 'fix') {
        const s = cur();
        s.tShown = s.tShown || Date.now();
        refreshField();
        focusField();
      } else {
        const h = stageEl.querySelector('h2');
        if (h) h.focus({ preventScroll: true });
        if (view === 'reveal' || view === 'alt') fitAnswer();
      }
      if ((view === 'ok' || view === 'kept') && autoMs > 0) {
        S.timer = setTimeout(() => next(), autoMs);
      }
      const ann =
        view === 'ok'
          ? tr('dt_repair.fixed', null, 'Fixed')
          : view === 'kept'
            ? tr('dt_repair.kept_title', null, 'Kept as written')
            : '';
      if (ann) live(ann);
    }

    function focusField() {
      const ta = $('#dtr-ta');
      if (!ta) return;
      if (mq('(pointer: fine)')) {
        ta.focus({ preventScroll: true });
        ta.setSelectionRange(ta.value.length, ta.value.length);
      } else {
        const lab = $('#dtr-lab');
        if (lab) lab.focus({ preventScroll: true });
      }
    }

    // Everything on the fix view that depends on the step's runtime state.
    function refreshField() {
      slot(false);
      const hb = $('#dtr-hint');
      if (hb) hb.textContent = hintLabel(cur());
      const cb = $('#dtr-check');
      if (cb && !S.busy)
        cb.textContent =
          cur().errStreak >= 2 && !cur().unsure
            ? tr('dt_repair.show_answer', null, 'Show answer')
            : tr('dt_repair.check', null, 'Check');
      const pr = $('#dtr-prompt');
      if (pr) {
        pr.firstElementChild.innerHTML = promptHtml(cur());
      }
      paint();
    }

    // The mirror layer under the textarea draws the "where" underline.
    function paint() {
      const s = cur();
      const ta = $('#dtr-ta');
      const m = $('#dtr-mirror');
      const f = $('#dtr-field');
      if (!s || !ta || !m || !f) return;
      const v = ta.value;
      const w = s.where;
      let html = null;
      if (w && w.point) {
        if (!s.pointStale) {
          const at = Math.min(cpToIdx(v, w.start || 0), v.length);
          html = `${esc(v.slice(0, at))}<span class="dtr-pt"></span>${esc(v.slice(at))}`;
        }
      } else if (w && w.text) {
        const k = locate(v, w);
        if (k >= 0) {
          html = `${esc(v.slice(0, k))}<mark${s.unsure ? ' class="dtr-maybe"' : ''}>${esc(w.text)}</mark>${esc(v.slice(k + w.text.length))}`;
        }
      }
      m.innerHTML = (html == null ? esc(v) : html) + '​';
      // Long sentence: step the type down until it fits; past the last step the field scrolls itself.
      f.classList.remove('dtr-f1', 'dtr-f2', 'dtr-f3');
      for (const c of ['dtr-f1', 'dtr-f2', 'dtr-f3']) {
        if (m.scrollHeight <= m.clientHeight + 1) break;
        f.classList.add(c);
      }
      m.scrollTop = ta.scrollTop;
      const pr = $('#dtr-prompt');
      if (pr) {
        const sp = pr.firstElementChild;
        const more = sp.scrollHeight > sp.clientHeight + 1;
        pr.classList.toggle('dtr-more', more);
        pr.tabIndex = more ? 0 : -1;
      }
    }

    // The single hint slot: a new hint or message replaces what was there.
    function slot(anim) {
      const s = cur();
      const el = $('#dtr-slot');
      if (!s || !el) return;
      let h = '';
      const msg = (key, fb) => `${ICON.again}<p>${esc(tr(key, null, fb))}</p>`;
      if (s.msg === 'still') {
        h =
          nextRung(s) && !s.noMore
            ? msg('dt_repair.still', 'Still not quite. Try again, or take a hint.')
            : msg('dt_repair.still_last', 'Still not quite. Try again.');
      } else if (s.msg === 'same')
        h = msg('dt_repair.same', 'That’s the same sentence. Change something first.');
      else if (s.msg === 'error')
        h = msg('dt_repair.check_failed', 'Couldn’t check just now — try again.');
      else if (s.msg === 'hint_failed')
        h = msg('dt_repair.hint_failed', 'Couldn’t load a hint — try again.');
      else if (s.hint) {
        const small = `<small>${esc(tr('dt_repair.hint_n_of', { n: s.hint.n, total: s.hint.total }, 'Hint {n} of {total}'))}</small>`;
        const body =
          s.hint.type === 'where'
            ? esc(tr('dt_repair.hint_where', null, 'Look at the underlined part.'))
            : `<span ${s.hint.lang ? `lang="${esc(s.hint.lang)}"` : ''}>${esc(s.hint.text)}</span>`;
        h = `${ICON.bulb}<p>${small}${body}</p>`;
      }
      el.innerHTML = h;
      stageEl.classList.toggle('dtr-hinted', !!h);
      if (anim && animate) {
        el.classList.remove('dtr-in');
        void el.offsetWidth;
        el.classList.add('dtr-in');
      }
    }

    function shake() {
      const f = $('#dtr-field');
      if (!f || !animate) return;
      f.classList.remove('dtr-shake');
      void f.offsetWidth;
      f.classList.add('dtr-shake');
    }

    // Answer view: type steps down, then clamp (tap to read the whole sentence).
    function fitAnswer() {
      const o = $('#dtr-orig');
      if (!o) return;
      const over = () => stageEl.scrollHeight > stageEl.clientHeight;
      for (const c of ['dtr-f1', 'dtr-f2', 'dtr-f3']) {
        if (!over()) break;
        o.classList.add(c);
      }
      for (const n of [3, 2, 1]) {
        if (!over()) break;
        o.classList.add('dtr-clamp');
        o.style.setProperty('--dtr-cl', n);
      }
      if (over()) {
        o.classList.add('dtr-tt');
        for (const n of [2, 1]) {
          if (!over()) break;
          o.style.setProperty('--dtr-cl', n);
        }
      }
      o.querySelectorAll('.dtr-cmp').forEach((b) => {
        const sp = b.querySelector('.dtr-sent');
        const more = o.classList.contains('dtr-clamp') && sp.scrollHeight > sp.clientHeight + 1;
        b.classList.toggle('dtr-more', more);
        if (more) {
          b.setAttribute('role', 'button');
          b.tabIndex = 0;
        }
      });
    }

    function showFull(html, lang, tagText) {
      const full = document.createElement('button');
      full.type = 'button';
      full.className = 'dtr-full';
      full.dataset.act = 'full-close';
      if (lang) full.lang = lang;
      full.innerHTML = `<span>${tagText ? `<span class="dtr-tag">${esc(tagText)}</span>` : ''}<span class="dtr-sent">${html}</span></span><small>${esc(tr('dt_repair.tap_close', null, 'Tap to close'))}</small>`;
      sheet.appendChild(full);
      full.focus({ preventScroll: true });
      return full;
    }

    // ---------------------------------------------------------------- flow
    function start() {
      sheet.dataset.view = '';
      if (mode === 'pass' && session.clean) return render('clean');
      if (!S.steps.length) {
        // Nothing to do: hand control straight back to the host.
        setTimeout(() => guard(requestClose), 0);
        return undefined;
      }
      if (mode === 'daily') return enter(0);
      const resumed = S.steps.some((x) => x.closedNow);
      if (resumed) {
        const k = S.steps.findIndex((x) => !x.closedNow);
        return k < 0 ? finishUp() : enter(k);
      }
      return render('result');
    }

    function enter(i) {
      S.i = i;
      const s = cur();
      S.busy = false;
      if (s.direct) {
        s.touched = true;
        return reveal('direct');
      }
      startItemTimer(s);
      s.tPrev = Date.now();
      s.openP = openItem(s);
      render('fix');
    }

    function next() {
      if (S.closed) return;
      clearTimeout(S.timer);
      let k = S.i + 1;
      while (k < S.steps.length && S.steps[k].closedNow) k += 1;
      if (k < S.steps.length) return enter(k);
      return finishUp();
    }

    // Finish the pass (or the daily set) and show the summary.
    async function finishUp() {
      render('answer_loading');
      if (mode === 'pass' && session.status === 'open') {
        const r = await finishPass(false);
        if (S.closed) return;
        S.summary = r && r.summary ? r.summary : null;
      }
      render('summary');
    }

    function finishPass(closedEarly) {
      if (mode !== 'pass' || session.status !== 'open') return Promise.resolve(null);
      if (!S.finishP) {
        const body = { closed_early: !!closedEarly };
        if (passTimer) {
          body.active_ms = passTimer.stop();
          body.client_event_id = passEventId;
        }
        S.finishP = api(`/sessions/${session.session_id}/finish`, body, FINISH_TIMEOUT_MS).then(
          (r) => (r.ok ? r.data : null)
        );
      }
      return S.finishP;
    }

    function clientTally() {
      const c = { fixed_yourself: 0, needed_help: 0, saved_to_practice: 0 };
      S.steps.forEach((s) => {
        const fixed = s.outcome === 'self_repaired' || s.outcome === 'repaired_alternative';
        if (fixed) c.fixed_yourself += 1;
        if (s.outcome === 'answer_shown') c.needed_help += 1;
        if (s.unsure) return;
        if (
          ['answer_shown', 'shown_directly', 'skipped'].includes(s.outcome) ||
          (fixed && s.maxLevel >= 2) ||
          (!s.outcome && !s.closedNow)
        ) {
          c.saved_to_practice += 1;
        }
      });
      return c;
    }

    // ------------------------------------------------------------- actions
    function applyAnswer(s, data) {
      s.closedNow = true;
      s.outcome = data.outcome || s.outcome;
      if (data.answer) s.answer = data.answer;
    }

    async function reveal(reason) {
      const s = cur();
      if (!s || S.view === 'answer_loading') return;
      S.busy = true;
      s.revealReason = reason;
      render('answer_loading');
      const tk = S.tk;
      const r = await itemCall(s, 'reveal', itemBody(s, { reason }));
      if (S.closed || S.tk !== tk) return;
      S.busy = false;
      if (r.ok && r.data && r.data.answer) {
        applyAnswer(s, r.data);
        s.maxLevel = Math.max(s.maxLevel, 4);
        render(s.answer.heading === 'no_issue' ? 'alt' : 'reveal');
      } else {
        s.retryAction = () => reveal(reason === 'direct' ? 'direct' : reason);
        render('answer_failed');
      }
    }

    async function hint() {
      const s = cur();
      if (S.busy || S.view !== 'fix') return;
      s.touched = true;
      const r = s.hintFails >= 2 || s.noMore ? null : nextRung(s);
      if (!r) return reveal(s.hintFails >= 2 ? 'grader_failed' : 'asked');
      S.busy = true;
      const hb = $('#dtr-hint');
      if (hb) hb.disabled = true;
      const tk = S.tk;
      const res = await itemCall(s, 'hint', itemBody(s, { expected_level: r }));
      if (S.closed || S.tk !== tk) return;
      S.busy = false;
      if (hb) hb.disabled = false;
      if (res.ok && res.data && res.data.hint) {
        const d = res.data;
        s.hintLevel = d.hint_level | 0;
        s.maxLevel = Math.max(s.maxLevel, s.hintLevel);
        s.hintsAsked += 1;
        s.hintFails = 0;
        s.msg = '';
        s.hint = {
          type: d.hint.type,
          text: d.hint.text,
          lang: d.hint.lang,
          n: d.hint_number,
          total: d.hint_total,
        };
        if (d.where) s.where = d.where;
        if (d.next === 'answer') s.noMore = true;
        s.pointStale = false;
        refreshField();
        slot(true);
        const ta = $('#dtr-ta');
        if (s.hint.type === 'where')
          live(tr('dt_repair.hint_where', null, 'Look at the underlined part.'));
        else live(s.hint.text);
        if (ta && mq('(pointer: fine)')) ta.focus({ preventScroll: true });
      } else if (res.status === 409 && res.data.error_code === 'NO_MORE_HINTS') {
        s.noMore = true;
        return reveal('asked');
      } else {
        s.hintFails += 1;
        s.msg = 'hint_failed';
        refreshField();
        slot(true);
        live(tr('dt_repair.hint_failed', null, 'Couldn’t load a hint — try again.'));
      }
    }

    function setChecking(on) {
      const cb = $('#dtr-check');
      const ta = $('#dtr-ta');
      if (cb) {
        cb.setAttribute('aria-busy', on ? 'true' : 'false');
        cb.disabled = false;
        cb.innerHTML = on
          ? `<span class="dtr-spin" aria-hidden="true"></span>${esc(tr('dt_repair.checking', null, 'Checking…'))}`
          : esc(
              cur().errStreak >= 2 && !cur().unsure
                ? tr('dt_repair.show_answer', null, 'Show answer')
                : tr('dt_repair.check', null, 'Check')
            );
      }
      if (ta) ta.readOnly = on;
      actEl.querySelectorAll('.dtr-txt, #dtr-fine').forEach((b) => {
        b.disabled = on;
      });
      sheet.dataset.fieldState = on ? 'checking' : '';
    }

    async function check(viaKey) {
      const s = cur();
      if (!s || S.busy || S.view !== 'fix' || s.closedNow) return;
      if (!viaKey && s.errStreak >= 2 && !s.unsure && s.showAnswerArmed)
        return reveal('grader_failed');
      const ta = $('#dtr-ta');
      const text = norm(ta ? ta.value : s.value);
      s.touched = true;
      if (!text) {
        if (ta) ta.focus({ preventScroll: true });
        return;
      }
      if (text === norm(s.checkedText)) {
        s.msg = 'same';
        slot(true);
        shake();
        live(tr('dt_repair.same', null, 'That’s the same sentence. Change something first.'));
        return;
      }
      S.busy = true;
      setChecking(true);
      live(tr('dt_repair.checking', null, 'Checking…'));
      const tk = S.tk;
      // The idempotency key is reused when the same text is re-sent after a network failure.
      if (!s.pendingCheck || s.pendingCheck.text !== text) s.pendingCheck = { text, id: uuid() };
      const body = itemBody(s, { text, client_check_id: s.pendingCheck.id });
      if (!s.firstCheckSent && s.tFirstEdit) {
        body.first_edit_ms = Math.max(0, s.tFirstEdit - s.tShown);
      }
      let r = await itemCall(s, 'check', body, CHECK_TIMEOUT_MS);
      if (S.closed || S.tk !== tk) return;
      if (r.status === 409 && r.data.error_code === 'CHECK_IN_PROGRESS') {
        await sleep(1000);
        if (S.closed || S.tk !== tk) return;
        r = await itemCall(s, 'check', body, CHECK_TIMEOUT_MS);
        if (S.closed || S.tk !== tk) return;
      }
      s.firstCheckSent = true;
      S.busy = false;
      onCheckResult(s, text, r);
    }

    function checkFailed(s) {
      s.errStreak += 1;
      s.msg = 'error';
      setChecking(false);
      if (s.errStreak >= 2 && !s.unsure) {
        s.showAnswerArmed = true;
        const cb = $('#dtr-check');
        if (cb) cb.textContent = tr('dt_repair.show_answer', null, 'Show answer');
      }
      slot(true);
      shake();
      live(tr('dt_repair.check_failed', null, 'Couldn’t check just now — try again.'));
      const ta = $('#dtr-ta');
      if (ta) ta.focus({ preventScroll: true });
    }

    function onCheckResult(s, text, r) {
      const d = r.data || {};
      if (
        r.status === 409 &&
        (d.error_code === 'ITEM_CLOSED' || d.error_code === 'SESSION_CLOSED')
      ) {
        // Closed elsewhere (another tab): ask for the answer, which is idempotent for closed items.
        s.pendingCheck = null;
        return reveal('asked');
      }
      if (!r.ok || !d.result) {
        // Network failure, timeout or non-2xx: keep the text and the idempotency key.
        return checkFailed(s);
      }
      if (d.result === 'error') {
        s.pendingCheck = null; // the server stored this result under the key; use a new one
        return checkFailed(s);
      }
      s.pendingCheck = null;
      s.errStreak = 0;
      s.showAnswerArmed = false;
      s.msg = '';
      s.checkedText = text;
      s.checksUsed = d.checks_used != null ? d.checks_used : s.checksUsed;
      if (d.hints_used != null) s.hintsUsedNow = d.hints_used;
      if (d.result === 'unchanged') {
        s.msg = 'same';
        setChecking(false);
        slot(true);
        shake();
        return;
      }
      if (d.result === 'fixed') {
        s.closedNow = true;
        s.outcome = d.outcome || 'self_repaired';
        return render('ok');
      }
      if (d.closed && d.answer) {
        // no_issue_found, auto reveal at the check cap, or the budget ran out
        applyAnswer(s, d);
        return render(
          s.answer.heading === 'no_issue' || d.result === 'no_issue_found' ? 'alt' : 'reveal'
        );
      }
      if (d.result === 'no_issue_found') {
        // no answer came with it: fetch it through reveal, which is idempotent
        return reveal('asked');
      }
      // still_flagged, not closed
      s.where = d.where || null;
      s.pointStale = false;
      s.msg = 'still';
      setChecking(false);
      refreshField();
      slot(true);
      shake();
      live(tr('dt_repair.still', null, 'Still not quite. Try again, or take a hint.'));
      const ta = $('#dtr-ta');
      if (ta) ta.focus({ preventScroll: true });
    }

    function dispute() {
      if (S.busy || S.view !== 'fix') return undefined;
      cur().touched = true;
      return runDispute();
    }

    async function runDispute() {
      const s = cur();
      S.busy = true;
      render('answer_loading');
      const tk = S.tk;
      const r = await itemCall(s, 'dispute', itemBody(s));
      if (S.closed || S.tk !== tk) return;
      S.busy = false;
      const d = r.data || {};
      if (r.ok && d.closed && !d.answer) {
        s.closedNow = true;
        s.outcome = d.outcome || 'unsure_dismissed';
        return render('kept');
      }
      if (r.ok && d.answer) {
        applyAnswer(s, d);
        if (!s.outcome) s.outcome = 'disputed';
        return render('reveal');
      }
      s.retryAction = () => runDispute();
      render('answer_failed');
    }

    async function skipItem() {
      const s = cur();
      if (!s) return;
      if (mode === 'daily') {
        // Best effort: the sitting stays due and is not counted as failed.
        await itemCall(s, 'skip', itemBody(s), 5000);
      }
      s.closedNow = true;
      s.outcome = s.outcome || 'skipped';
      next();
    }

    // -------------------------------------------------------------- closing
    async function requestClose() {
      if (S.closed) return;
      const early = S.view !== 'summary';
      const s = cur();
      S.closed = true;
      clearTimeout(S.timer);
      teardownUi();
      let summary = null;
      let completed = 0;
      try {
        if (mode === 'pass') {
          const r = await finishPass(early);
          summary = r && r.summary ? r.summary : S.summary;
        } else {
          completed = S.steps.filter((x) => x.closedNow).length;
          if (early && s && !s.closedNow && !s.direct && s.item_id != null) {
            await itemCall(s, 'skip', itemBody(s), 4000);
          }
        }
      } catch (e) {
        console.warn('dt-repair: close failed', e);
      }
      if (typeof opts.onDone === 'function') {
        opts.onDone(
          mode === 'pass'
            ? {
                summary,
                closedEarly: early && S.view !== 'clean',
                clean: !!(session && session.clean),
              }
            : { completed, closedEarly: early }
        );
      }
    }

    // Close without any callbacks (a second open(), or the host being destroyed).
    function dispose() {
      if (S.closed) return;
      S.closed = true;
      clearTimeout(S.timer);
      teardownUi();
    }

    function fatal(err) {
      console.error('dt-repair: sheet error', err);
      if (S.closed) return;
      S.closed = true;
      clearTimeout(S.timer);
      teardownUi();
      const done = () => {
        if (typeof opts.onDone === 'function') opts.onDone({ closedEarly: true, error: true });
      };
      if (mode === 'pass') finishPass(true).then(done, done);
      else done();
    }

    function teardownUi() {
      document.removeEventListener('keydown', onDocKey, true);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', vv);
        window.visualViewport.removeEventListener('scroll', vv);
      }
      window.removeEventListener('resize', vv);
      host.restore();
      scrim.classList.remove('dtr-on');
      sheet.classList.remove('dtr-on');
      const gone = () => {
        if (scrim.parentNode) scrim.parentNode.removeChild(scrim);
      };
      if (animate) setTimeout(gone, 340);
      else gone();
      const rf = opts.returnFocus;
      if (rf && typeof rf.focus === 'function' && document.contains(rf)) {
        try {
          rf.focus({ preventScroll: true });
        } catch {
          /* ignore */
        }
      }
      if (current && current.dispose === dispose) current = null;
    }

    // ----------------------------------------------- viewport and host page
    const host = {
      inerted: [],
      overflow: null,
      lock() {
        Array.from(document.body.children).forEach((el) => {
          if (el === scrim || el.inert) return;
          el.inert = true;
          this.inerted.push(el);
        });
        const de = document.documentElement;
        this.overflow = [de.style.overflow, document.body.style.overflow];
        de.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';
      },
      restore() {
        this.inerted.forEach((el) => {
          el.inert = false;
        });
        this.inerted = [];
        if (this.overflow) {
          document.documentElement.style.overflow = this.overflow[0];
          document.body.style.overflow = this.overflow[1];
          this.overflow = null;
        }
      },
    };

    // Follow the visual viewport so the action bar rides above an open keyboard.
    function vv() {
      const v = window.visualViewport;
      const h = v ? v.height : window.innerHeight;
      if (window.innerWidth < 600) {
        sheet.style.setProperty('--dtr-vvh', `${h}px`);
        sheet.style.setProperty('--dtr-vvt', `${v ? v.offsetTop : 0}px`);
      } else {
        sheet.style.removeProperty('--dtr-vvh');
        sheet.style.removeProperty('--dtr-vvt');
      }
      sheet.classList.toggle('dtr-kb', window.innerWidth < 600 && h < 560);
      sheet.classList.toggle('dtr-tight', h < 400);
      if (S.view === 'fix') paint();
      else if (S.view === 'reveal' || S.view === 'alt') {
        const o = $('#dtr-orig');
        if (o) {
          o.classList.remove('dtr-f1', 'dtr-f2', 'dtr-f3', 'dtr-clamp', 'dtr-tt');
          fitAnswer();
        }
      }
    }

    // -------------------------------------------------------------- events
    function onDocKey(e) {
      if (S.closed) return;
      if (e.key === 'Escape') {
        const full = sheet.querySelector('.dtr-full');
        e.preventDefault();
        if (full) closeFull(full);
        else guard(requestClose);
        return;
      }
      if (e.key === 'Tab') {
        const items = Array.from(
          sheet.querySelectorAll('button:not(:disabled), textarea:not([readonly]), [tabindex="0"]')
        ).filter((el) => !el.closest('[hidden]') && el.getClientRects().length);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        const a = document.activeElement;
        if (!sheet.contains(a)) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && a === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && a === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    function closeFull(full) {
      const prev = full.dataset.returnTo;
      full.remove();
      const target = prev && sheet.querySelector(prev);
      if (target) target.focus({ preventScroll: true });
    }

    function guard(fn) {
      try {
        const r = fn();
        if (r && typeof r.catch === 'function') r.catch(fatal);
      } catch (e) {
        fatal(e);
      }
    }

    sheet.addEventListener('click', (e) => {
      if (S.closed) return;
      // any pointer interaction cancels the success auto-advance
      if (S.timer) {
        clearTimeout(S.timer);
        S.timer = null;
      }
      const cmp = e.target.closest && e.target.closest('.dtr-cmp.dtr-more');
      if (cmp) {
        const sp = cmp.querySelector('.dtr-sent');
        const full = showFull(sp.innerHTML, sp.lang, cmp.querySelector('.dtr-tag').textContent);
        full.dataset.returnTo = `#${cmp.id}`;
        return;
      }
      const btn = e.target.closest && e.target.closest('[data-act]');
      if (!btn || btn.disabled) return;
      const act = btn.dataset.act;
      guard(() => {
        if (act === 'close') return requestClose();
        if (act === 'go')
          return enter(
            S.steps.findIndex((x) => !x.closedNow) < 0 ? 0 : S.steps.findIndex((x) => !x.closedNow)
          );
        if (act === 'done') return requestClose();
        if (act === 'next') return next();
        if (act === 'check') return check();
        if (act === 'hint') return hint();
        if (act === 'fine') return dispute();
        if (act === 'retry') {
          const s = cur();
          return s && s.retryAction ? s.retryAction() : undefined;
        }
        if (act === 'skip') return skipItem();
        if (act === 'full-close') return closeFull(btn);
        if (act === 'prompt') {
          const pr = $('#dtr-prompt');
          if (!pr || !pr.classList.contains('dtr-more')) return undefined;
          const full = showFull(promptHtml(cur()), l1);
          full.dataset.returnTo = '#dtr-prompt';
          return undefined;
        }
        return undefined;
      });
    });

    sheet.addEventListener('keydown', (e) => {
      if (S.timer) {
        clearTimeout(S.timer);
        S.timer = null;
      }
      const t = e.target;
      if (t && t.id === 'dtr-ta' && e.key === 'Enter') {
        // Never submit while an IME composition is active (Safari fires keydown after compositionend).
        if (e.isComposing || e.keyCode === 229 || S.composing) return;
        e.preventDefault();
        guard(() => check(true));
        return;
      }
      // role=button blocks (a clamped sentence) activate with Enter / Space
      if (
        t &&
        t.getAttribute &&
        t.getAttribute('role') === 'button' &&
        (e.key === 'Enter' || e.key === ' ')
      ) {
        e.preventDefault();
        t.click();
      }
    });

    sheet.addEventListener('compositionstart', () => {
      S.composing = true;
    });
    sheet.addEventListener('compositionend', () => {
      setTimeout(() => {
        S.composing = false;
      }, 0);
    });

    sheet.addEventListener('input', (e) => {
      const t = e.target;
      if (!t || t.id !== 'dtr-ta') return;
      const s = cur();
      s.touched = true;
      if (!s.tFirstEdit) s.tFirstEdit = Date.now();
      const clean = t.value.replace(/[\r\n]+/g, ' ');
      if (clean !== t.value) t.value = clean;
      s.value = clean;
      s.pointStale = true;
      if (s.msg) {
        s.msg = '';
        slot(false);
      }
      paint();
      if (s.unsure) {
        const cb = $('#dtr-check');
        if (cb) {
          const changed = norm(clean) !== norm(s.learner_sentence);
          cb.classList.toggle('dtr-primary', changed);
          cb.classList.toggle('dtr-plain', !changed);
        }
      }
    });

    stageEl.addEventListener(
      'scroll',
      () => {
        stageEl.scrollTop = 0; // the stage never scrolls
      },
      { passive: true }
    );
    sheet.addEventListener(
      'scroll',
      (e) => {
        if (e.target && e.target.id === 'dtr-ta') {
          const m = $('#dtr-mirror');
          if (m) m.scrollTop = e.target.scrollTop;
        }
      },
      true
    );

    // ---------------------------------------------------------------- mount
    document.body.appendChild(scrim);
    host.lock();
    document.addEventListener('keydown', onDocKey, true);
    (window.visualViewport || window).addEventListener('resize', vv);
    if (window.visualViewport) window.visualViewport.addEventListener('scroll', vv);
    window.addEventListener('resize', vv);
    vv();
    if (passTimer) passTimer.start();
    if (animate) {
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          scrim.classList.add('dtr-on');
          sheet.classList.add('dtr-on');
        })
      );
    } else {
      scrim.classList.add('dtr-on');
      sheet.classList.add('dtr-on');
    }
    try {
      start();
    } catch (e) {
      fatal(e);
    }

    return { requestClose: () => guard(requestClose), dispose, _state: S };
  }

  window.DTRepairSheet = { open, norm, dayLabel };
})();
