// static/js/session/players/classifier_drill.js
// Measure-Word (classifier) drill player for the daily-session runner.
//
// Ported from templates/classifier_drill.html. In the session, ONE 20-item
// batch == one queue item: when the batch finishes the player submits to
// /api/classifier-drill/submit (which records the attempt + ELO and, via the
// route's Study-Plan progress hook, increments weekly_plan_states.completed_counts
// for 'classifier_drill'), then shows a single Continue button that calls
// ctx.onComplete — the controller then marks the daily-load slot complete via
// /api/tests/daily-load/complete. NO redirect; no infinite "Next round" loop.
//
// Player contract: mount(container, ctx) -> { destroy() }.
//   ctx = { item, languageId, onComplete(result), onSkip() }.
// Self-contained: inline <style>, all DOM scoped to `container`, and every
// document-level listener / timer is tracked and torn down in destroy().

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof LinguaI18n.t === 'function'
    ? LinguaI18n.t(key, params) || fallback || key
    : fallback || key;

const BATCH_SIZE = 20;

function localEsc(s) {
  if (window.LinguaUtils && LinguaUtils.escapeHtml)
    return LinguaUtils.escapeHtml(String(s == null ? '' : s));
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function mount(container, ctx) {
  const languageId = (ctx && ctx.languageId) || 1;
  const escapeHtml = localEsc;

  const state = {
    mode: localStorage.getItem('cd_mode') || 'auto',
    items: [],
    cursor: 0,
    correct: 0,
    errors: [],
    startTime: 0,
    currentOptions: [],
    isLocked: false,
    currentItem: null,
    itemResults: [],
    effectiveLevel: 1,
    finished: false,
    completed: false, // ctx.onComplete already called (guard against double-fire)
  };

  // ---- teardown bookkeeping -------------------------------------------------
  const timers = new Set();
  const docListeners = [];
  function later(fn, ms) {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
    return id;
  }
  function onDoc(type, fn) {
    document.addEventListener(type, fn);
    docListeners.push([type, fn]);
  }

  container.innerHTML = MARKUP;
  const q = (id) => container.querySelector('#' + id);

  const el = {
    loading: q('cdLoading'),
    controls: q('cdControls'),
    stage: q('cdStage'),
    promptWrap: q('cdPromptWrap'),
    promptBlank: q('cdPromptBlank'),
    noun: q('cdNoun'),
    pronunciation: q('cdPronunciation'),
    gloss: q('cdGloss'),
    reversePrompt: q('cdReversePrompt'),
    options: q('cdOptions'),
    typedForm: q('cdTypedForm'),
    typedInput: q('cdTypedInput'),
    progressLabel: q('cdProgressLabel'),
    progressTotal: q('cdProgressTotal'),
    progressFill: q('cdProgressFill'),
    levelBadge: q('cdLevelBadge'),
    feedback: q('cdFeedback'),
    fbCanonical: q('cdFeedbackCanonical'),
    fbGroup: q('cdFeedbackGroup'),
    fbExamples: q('cdFeedbackExamples'),
    fbContinue: q('cdFeedbackContinue'),
    results: q('cdResults'),
    resultsGrade: q('cdResultsGrade'),
    resultsPct: q('cdResultsPct'),
    resultsCorrect: q('cdResultsCorrect'),
    resultsTotal: q('cdResultsTotal'),
    resultsTime: q('cdResultsTime'),
    resultsElo: q('cdResultsElo'),
    resultsContinue: q('cdResultsContinue'),
    modeToggle: q('cdModeToggle'),
  };

  init();

  return {
    destroy() {
      timers.forEach(clearTimeout);
      timers.clear();
      docListeners.forEach(([t, f]) => document.removeEventListener(t, f));
      docListeners.length = 0;
    },
  };

  // ==========================================================================
  async function init() {
    try {
      applyModeToToggle();
      bindModeToggle();
      bindFeedback();
      bindResults();
      bindTypedForm();
      bindKeyboard();
      await loadBatch();
    } catch (err) {
      console.error('Classifier drill init error:', err);
      el.loading.textContent =
        T('classifier_drill.error_init', null, 'Could not start the drill.') +
        ' ' +
        (err.message || '');
      el.loading.style.display = 'block';
    }
  }

  function applyModeToToggle() {
    const buttons = el.modeToggle.querySelectorAll('button');
    buttons.forEach((b) => b.classList.toggle('active', b.dataset.mode === state.mode));
  }

  function bindModeToggle() {
    el.modeToggle.addEventListener('click', function (e) {
      const btn = e.target.closest('button[data-mode]');
      if (!btn) return;
      state.mode = btn.dataset.mode;
      localStorage.setItem('cd_mode', state.mode);
      applyModeToToggle();
      if (state.currentItem && !state.isLocked) {
        resetPromptStyles();
        state.effectiveLevel = effectiveLevelForItem(state.currentItem);
        updateLevelBadge();
        renderInput();
      }
    });
  }

  function bindFeedback() {
    el.fbContinue.addEventListener('click', closeFeedback);
  }

  function bindResults() {
    el.resultsContinue.addEventListener('click', complete);
  }

  function bindKeyboard() {
    onDoc('keydown', function (e) {
      if (el.feedback.classList.contains('show')) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          closeFeedback();
        }
        return;
      }
      if (state.isLocked || !state.currentItem) return;
      if (state.effectiveLevel !== 2) {
        const idx = parseInt(e.key, 10);
        if (idx >= 1 && idx <= state.currentOptions.length) {
          e.preventDefault();
          handleChoiceClick(idx - 1);
        }
      }
    });
  }

  function bindTypedForm() {
    el.typedForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (state.isLocked || !state.currentItem) return;
      const raw = (el.typedInput.value || '').trim();
      if (!raw) return;
      const correctHanzi = state.currentItem.correct_classifier_hanzi || [];
      const isCorrect = correctHanzi.indexOf(raw) !== -1;
      state.isLocked = true;
      recordAnswer(isCorrect, raw);
      if (isCorrect) {
        el.typedInput.classList.add('correct');
        later(advance, 400);
      } else {
        el.typedInput.classList.add('wrong');
        later(function () {
          openFeedback(raw);
        }, 250);
      }
    });
  }

  function effectiveLevelForItem(item) {
    if (state.mode === 'mc') return 1;
    if (state.mode === 'type') return 2;
    const lvl = parseInt(item.level || 1, 10);
    return Math.max(1, Math.min(4, lvl));
  }

  function updateLevelBadge() {
    if (state.mode === 'auto') {
      const tag =
        state.effectiveLevel === 1
          ? '· MC'
          : state.effectiveLevel === 2
            ? '· Type'
            : state.effectiveLevel === 3
              ? '· Reverse'
              : '· Cloze';
      el.levelBadge.textContent = tag;
      el.levelBadge.style.display = 'inline';
    } else {
      el.levelBadge.style.display = 'none';
    }
  }

  async function loadBatch() {
    el.loading.style.display = 'block';
    el.stage.style.display = 'none';
    el.results.style.display = 'none';
    el.controls.style.display = 'none';

    const url = '/api/classifier-drill/session?language_id=' + languageId + '&count=' + BATCH_SIZE;
    let resp;
    try {
      resp = await window.authFetch(url);
    } catch (e) {
      console.error('Classifier drill load failed:', e);
      return showEmptyState(T('classifier_drill.error_load', null, 'Couldn’t load the drill.'));
    }
    if (!resp.ok) {
      return showEmptyState(
        T('classifier_drill.error_load', null, 'Couldn’t load the drill.') +
          ' (' +
          resp.status +
          ')'
      );
    }
    const data = await resp.json();
    const items = (data && ((data.data && data.data.items) || data.items)) || [];
    if (!items.length) {
      return showEmptyState(
        T('classifier_drill.error_empty', null, 'No drill items right now — you can move on.')
      );
    }

    state.items = items;
    state.cursor = 0;
    state.correct = 0;
    state.errors = [];
    state.itemResults = [];
    state.startTime = Date.now();
    state.isLocked = false;

    el.progressTotal.textContent = items.length;
    el.loading.style.display = 'none';
    el.controls.style.display = 'flex';
    el.stage.style.display = 'block';
    renderCurrent();
  }

  // No items / load failure: let the session advance via Continue.
  function showEmptyState(msg) {
    el.controls.style.display = 'none';
    el.stage.style.display = 'none';
    el.loading.style.display = 'none';
    el.results.style.display = 'block';
    el.resultsGrade.textContent = '👍';
    el.resultsPct.parentElement.style.display = 'none';
    el.results.querySelector('.cd-results-stats').style.display = 'none';
    const note = el.results.querySelector('#cdResultsNote');
    if (note) note.textContent = msg;
    el.resultsContinue.textContent = T('session.next_item', null, 'Next');
  }

  function renderCurrent() {
    if (state.cursor >= state.items.length) {
      return finishBatch();
    }
    if (document.activeElement && typeof document.activeElement.blur === 'function') {
      document.activeElement.blur();
    }
    state.currentItem = state.items[state.cursor];
    state.isLocked = false;
    state.effectiveLevel = effectiveLevelForItem(state.currentItem);

    el.progressLabel.textContent = String(state.cursor + 1);
    el.progressFill.style.width = (100 * state.cursor) / state.items.length + '%';
    updateLevelBadge();
    renderInput();
  }

  function renderInput() {
    const lvl = state.effectiveLevel;
    if (lvl === 4 && state.currentItem.cloze_blanked) {
      renderClozeStage();
      return;
    }
    if (lvl === 3) {
      renderReverseStage();
      return;
    }
    renderForwardStage();
    if (lvl === 2) {
      el.typedForm.style.display = 'block';
      el.options.style.display = 'none';
      el.typedInput.value = '';
      el.typedInput.classList.remove('wrong', 'correct');
      requestAnimationFrame(() => el.typedInput.focus());
    } else {
      el.typedForm.style.display = 'none';
      el.options.style.display = 'grid';
      renderMcOptions();
    }
  }

  function renderClozeStage() {
    const item = state.currentItem;
    const blanked = item.cloze_blanked || '';
    el.promptWrap.style.display = 'block';
    el.promptBlank.textContent = '';
    el.noun.textContent = '';
    el.pronunciation.textContent = '';
    el.gloss.textContent = '';
    el.reversePrompt.style.display = 'block';
    el.reversePrompt.innerHTML =
      '<div style="font-size:0.95rem; color:var(--text-muted); margin-bottom:8px;">' +
      T('classifier_drill.cloze_prompt', null, 'Fill in the measure word') +
      '</div>' +
      '<div style="font-size:1.6rem; font-weight:600; line-height:1.5; color:var(--text-primary);">' +
      escapeHtml(blanked).replace(
        /___/g,
        '<span style="color:var(--info); border-bottom:3px solid var(--info); padding:0 8px;">&nbsp;___&nbsp;</span>'
      ) +
      '</div>';
    el.typedForm.style.display = 'none';
    el.options.style.display = 'grid';
    renderMcOptions();
  }

  function renderForwardStage() {
    const item = state.currentItem;
    el.promptWrap.style.display = 'block';
    el.reversePrompt.style.display = 'none';
    el.promptBlank.textContent = '_';
    el.noun.textContent = item.noun_lemma || '';
    el.pronunciation.textContent = item.noun_pronunciation || '';
    el.gloss.textContent = item.noun_gloss || '';
  }

  function renderReverseStage() {
    const item = state.currentItem;
    const canonical = (item.correct_classifier_hanzi || [])[0] || '';
    el.promptWrap.style.display = 'block';
    el.promptBlank.textContent = canonical;
    el.promptBlank.style.color = 'var(--info)';
    el.promptBlank.style.borderBottom = 'none';
    el.noun.textContent = '?';
    el.pronunciation.textContent = '';
    el.gloss.textContent = '';
    el.reversePrompt.style.display = 'block';
    el.reversePrompt.textContent =
      T('classifier_drill.reverse_prompt', null, 'Which noun fits?') + ' ' + canonical;

    const pool = [
      {
        id: 'noun:' + (item.noun_lemma || ''),
        hanzi: item.noun_lemma || '',
        pinyin: '',
        is_correct: true,
      },
    ];
    const distractors = item.reverse_noun_options || [];
    distractors.forEach(function (n) {
      pool.push({ id: 'noun:' + n, hanzi: n, pinyin: '', is_correct: false });
    });
    state.currentOptions = shuffle(pool);

    el.typedForm.style.display = 'none';
    el.options.style.display = 'grid';
    el.options.innerHTML = '';
    state.currentOptions.forEach(function (opt, idx) {
      const btn = document.createElement('button');
      btn.className = 'cd-option';
      btn.type = 'button';
      btn.dataset.idx = idx;
      btn.innerHTML =
        '<span class="cd-option-key">' +
        (idx + 1) +
        '</span>' +
        '<span>' +
        escapeHtml(opt.hanzi) +
        '</span>';
      btn.addEventListener('click', function () {
        handleChoiceClick(idx);
      });
      el.options.appendChild(btn);
    });
  }

  function resetPromptStyles() {
    el.promptBlank.style.color = '';
    el.promptBlank.style.borderBottom = '';
  }

  function renderMcOptions() {
    const item = state.currentItem;
    const correctHanzi = (item.correct_classifier_hanzi || [])[0];
    const correctId = (item.correct_classifier_ids || [])[0];
    const distractorIds = item.distractor_ids || [];
    const distractorHanzi = item.distractor_hanzi || [];
    const distractorPinyin = item.distractor_pinyin || [];

    const pool = [{ id: correctId, hanzi: correctHanzi, pinyin: '', is_correct: true }];
    for (let i = 0; i < distractorIds.length; i++) {
      pool.push({
        id: distractorIds[i],
        hanzi: distractorHanzi[i] || '',
        pinyin: distractorPinyin[i] || '',
        is_correct: false,
      });
    }
    state.currentOptions = shuffle(pool);

    el.options.innerHTML = '';
    state.currentOptions.forEach(function (opt, idx) {
      const btn = document.createElement('button');
      btn.className = 'cd-option';
      btn.type = 'button';
      btn.dataset.idx = idx;
      btn.innerHTML =
        '<span class="cd-option-key">' +
        (idx + 1) +
        '</span>' +
        '<span>' +
        escapeHtml(opt.hanzi) +
        '</span>' +
        (opt.pinyin ? '<span class="cd-option-pinyin">' + escapeHtml(opt.pinyin) + '</span>' : '');
      btn.addEventListener('click', function () {
        handleChoiceClick(idx);
      });
      el.options.appendChild(btn);
    });
  }

  function handleChoiceClick(idx) {
    if (state.isLocked) return;
    state.isLocked = true;
    const opt = state.currentOptions[idx];

    let isCorrect;
    if (state.effectiveLevel === 3) {
      isCorrect = !!opt.is_correct;
    } else {
      const correctIds = state.currentItem.correct_classifier_ids || [];
      isCorrect = correctIds.indexOf(opt.id) !== -1;
    }
    recordAnswer(isCorrect, opt.hanzi);

    const buttons = el.options.querySelectorAll('.cd-option');
    buttons.forEach(function (b) {
      b.disabled = true;
    });

    const clickedBtn = buttons[idx];
    if (clickedBtn && typeof clickedBtn.blur === 'function') clickedBtn.blur();

    if (isCorrect) {
      clickedBtn.classList.add('correct');
      later(advance, 400);
    } else {
      clickedBtn.classList.add('wrong');
      state.currentOptions.forEach(function (o, i) {
        if (o.is_correct) buttons[i].classList.add('correct');
      });
      later(function () {
        openFeedback(opt.hanzi);
      }, 280);
    }
  }

  function recordAnswer(isCorrect, picked) {
    const cid = state.currentItem.classifier_id_primary;
    if (typeof cid === 'number') {
      state.itemResults.push({
        classifier_id: cid,
        is_correct: !!isCorrect,
        level: state.effectiveLevel,
      });
    }
    if (isCorrect) {
      state.correct += 1;
    } else {
      state.errors.push({
        lemma: state.currentItem.noun_lemma,
        picked: picked,
        correct: state.currentItem.correct_classifier_hanzi,
        ts: Date.now(),
      });
    }
  }

  function openFeedback(picked) {
    const item = state.currentItem;
    const canonical = (item.correct_classifier_hanzi || [])[0] || '';
    const altList = (item.correct_classifier_hanzi || []).slice(1);
    const altSuffix = altList.length
      ? ' <span style="font-size:1.5rem; color: var(--text-muted);">(' +
        T('classifier_drill.also', null, 'also') +
        ': ' +
        altList.join(' / ') +
        ')</span>'
      : '';
    el.fbCanonical.innerHTML =
      '一 <span class="hl">' +
      escapeHtml(canonical) +
      '</span> ' +
      escapeHtml(item.noun_lemma || '') +
      altSuffix;
    el.fbGroup.textContent = item.semantic_label || '';
    el.fbExamples.textContent =
      T('classifier_drill.your_answer', null, 'Your answer') + ': ' + picked;
    el.feedback.classList.add('show');
    el.fbContinue.focus();
  }

  function closeFeedback() {
    el.feedback.classList.remove('show');
    advance();
  }

  function advance() {
    resetPromptStyles();
    state.cursor += 1;
    renderCurrent();
  }

  async function finishBatch() {
    if (state.finished) return;
    state.finished = true;

    const total = state.items.length;
    const correct = state.correct;
    const pct = total ? Math.round((correct / total) * 100) : 0;
    const time = Math.round((Date.now() - state.startTime) / 1000);

    el.stage.style.display = 'none';
    el.controls.style.display = 'none';
    el.progressFill.style.width = '100%';
    el.progressLabel.textContent = String(total);

    el.resultsPct.textContent = pct;
    el.resultsCorrect.textContent = correct;
    el.resultsTotal.textContent = total;
    el.resultsTime.textContent = time;
    el.resultsGrade.textContent = pct >= 95 ? '🏆' : pct >= 80 ? '🎯' : pct >= 60 ? '👍' : '💪';
    el.results.style.display = 'block';

    // Submit (best-effort): records attempt + ELO + weekly progress hook.
    try {
      const resp = await window.authFetch('/api/classifier-drill/submit', {
        method: 'POST',
        body: JSON.stringify({
          language_id: languageId,
          correct_items: correct,
          total_items: total,
          time_taken: time,
          item_results: state.itemResults,
        }),
      });
      if (resp.ok) {
        const payload = await resp.json();
        const result = (payload && (payload.data || payload)) || {};
        const elo = result.user_elo_change || {};
        if (typeof elo.change === 'number' && elo.change !== 0) {
          const sign = elo.change > 0 ? '+' : '';
          el.resultsElo.textContent = T(
            'classifier_drill.results_elo',
            { value: sign + elo.change },
            'ELO ' + sign + elo.change
          );
          el.resultsElo.style.display = 'inline-block';
        } else if (typeof elo.change === 'number') {
          el.resultsElo.textContent = T(
            'classifier_drill.results_elo_unchanged',
            null,
            'ELO unchanged'
          );
          el.resultsElo.style.display = 'inline-block';
        }
      }
    } catch (e) {
      console.error('Classifier drill submit failed:', e);
    }
  }

  // Mark the session item complete and let the controller advance. Guarded so a
  // double tap / Enter can't fire onComplete twice.
  function complete() {
    if (state.completed) return;
    state.completed = true;
    const total = state.items.length;
    ctx.onComplete({ correct: state.correct, total: total, mode: 'classifier_drill' });
  }
}

// ==========================================================================
// MARKUP — self-contained. Mirrors templates/classifier_drill.html styling but
// drops the page-level sticky header (the session shell already has a sticky
// progress bar); the drill's own progress sits in a non-sticky control row.
// ==========================================================================
const MARKUP = `
<style>
    .cd-controls { max-width: 640px; margin: 8px auto 0; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
    .cd-controls-progress { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; color: var(--text-muted); }
    .cd-progress-track { width: 120px; height: 6px; background: var(--border-default); border-radius: 3px; overflow: hidden; }
    .cd-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary) 0%, var(--info) 100%); transition: width 0.3s ease; width: 0; }
    .cd-stage { max-width: 640px; margin: 0 auto; padding: 32px 20px; }
    .cd-prompt { text-align: center; font-size: 3.5rem; font-weight: 700; letter-spacing: 0.1em; color: var(--text-primary); margin-bottom: 12px; line-height: 1.1; }
    .cd-blank { display: inline-block; min-width: 1.2em; border-bottom: 4px solid var(--info); color: transparent; }
    .cd-pronunciation { text-align: center; font-size: 1.5rem; color: var(--text-muted); margin-bottom: 4px; }
    .cd-gloss { text-align: center; font-size: 1.05rem; color: var(--text-secondary); margin-bottom: 36px; }
    .cd-options { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 28px; }
    .cd-option { font-size: 2.25rem; font-weight: 600; padding: 18px 8px; border: 2px solid var(--border-default); border-radius: 12px; background: var(--bg-surface); cursor: pointer; transition: transform 0.1s, border-color 0.1s, background 0.15s; position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; }
    @media (hover: hover) and (pointer: fine) { .cd-option:hover:not(:disabled) { border-color: var(--primary); transform: translateY(-1px); } }
    .cd-option:focus { outline: none; }
    .cd-option:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
    .cd-option:disabled { cursor: default; opacity: 0.65; }
    .cd-option.correct  { background: #ecfdf5; border-color: #10b981; }
    .cd-option.wrong    { background: #fef2f2; border-color: #ef4444; }
    .cd-option .cd-option-key { position: absolute; top: 6px; left: 8px; font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
    .cd-option .cd-option-pinyin { font-size: 0.95rem; color: var(--text-muted); font-weight: 400; }
    .cd-typed-input { display: block; width: 100%; font-size: 2.5rem; font-weight: 600; text-align: center; padding: 14px 8px; border: 2px solid var(--border-default); border-radius: 12px; background: var(--bg-surface); outline: none; transition: border-color 0.1s; }
    .cd-typed-input:focus { border-color: var(--primary); }
    .cd-typed-input.wrong { border-color: #ef4444; background: #fef2f2; }
    .cd-typed-input.correct { border-color: #10b981; background: #ecfdf5; }
    .cd-feedback { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.65); display: none; align-items: center; justify-content: center; z-index: 1050; padding: 20px; }
    .cd-feedback.show { display: flex; }
    .cd-feedback-card { background: var(--bg-surface); border-radius: 16px; padding: 28px; max-width: 480px; width: 100%; box-shadow: var(--shadow-lg); }
    .cd-feedback-canonical { font-size: 3rem; text-align: center; font-weight: 700; margin: 8px 0 4px; }
    .cd-feedback-canonical .hl { color: var(--info); }
    .cd-feedback-group { text-align: center; font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 18px; }
    .cd-feedback-examples { background: var(--bg-page); border-radius: 10px; padding: 12px 16px; font-size: 1rem; margin-bottom: 18px; }
    .cd-feedback-cta { width: 100%; background: var(--primary); color: white; font-weight: 600; padding: 14px; border-radius: 10px; border: 0; cursor: pointer; font-size: 1rem; }
    .cd-results { max-width: 480px; margin: 40px auto; padding: 36px 28px; background: var(--bg-surface); border-radius: 16px; box-shadow: var(--shadow-md); text-align: center; }
    .cd-results-grade { font-size: 4rem; margin: 8px 0; }
    .cd-results-pct { font-size: 2.5rem; font-weight: 700; color: var(--primary); }
    .cd-results-stats { display: flex; justify-content: center; gap: 36px; margin: 20px 0 24px; font-size: 0.95rem; color: var(--text-secondary); }
    .cd-results-elo-badge { display: inline-block; padding: 6px 14px; border-radius: 999px; background: var(--bg-page); font-weight: 600; margin-bottom: 18px; }
    .cd-mode-toggle { display: inline-flex; background: var(--bg-page); border-radius: 999px; padding: 4px; }
    .cd-mode-toggle button { background: transparent; border: 0; padding: 6px 14px; border-radius: 999px; font-size: 0.85rem; font-weight: 500; color: var(--text-muted); cursor: pointer; }
    .cd-mode-toggle button.active { background: var(--bg-surface); color: var(--text-primary); box-shadow: var(--shadow-sm); }
    @media (max-width: 640px) {
        .cd-stage { padding: 20px 14px; }
        .cd-prompt { font-size: 2.5rem; letter-spacing: 0.05em; }
        .cd-pronunciation { font-size: 1.2rem; }
        .cd-gloss { font-size: 0.95rem; margin-bottom: 24px; }
        .cd-options { gap: 10px; margin-top: 20px; }
        .cd-option { font-size: 1.85rem; padding: 16px 6px; min-height: 76px; }
        .cd-typed-input { font-size: 2rem; padding: 12px 6px; }
        .cd-feedback-card { padding: 22px 18px; }
        .cd-feedback-canonical { font-size: 2.1rem; }
        .cd-mode-toggle button { padding: 5px 10px; font-size: 0.8rem; }
        #cdReversePrompt { font-size: 1rem !important; }
    }
</style>

<div id="cdLoading" class="text-center py-5 text-muted" data-i18n="classifier_drill.loading" style="display:none;">Loading…</div>

<div id="cdControls" class="cd-controls" style="display:none;">
    <div class="cd-mode-toggle" id="cdModeToggle" title="Auto adapts each item to your per-classifier mastery">
        <button type="button" data-mode="auto" class="active" data-i18n="classifier_drill.mode_auto">Auto</button>
        <button type="button" data-mode="mc"   data-i18n="classifier_drill.mode_mc">Choose</button>
        <button type="button" data-mode="type" data-i18n="classifier_drill.mode_type">Type</button>
    </div>
    <div class="cd-controls-progress">
        <span id="cdLevelBadge" style="display:none;"></span>
        <span><span id="cdProgressLabel">0</span> / <span id="cdProgressTotal">0</span></span>
        <div class="cd-progress-track"><div class="cd-progress-fill" id="cdProgressFill"></div></div>
    </div>
</div>

<div id="cdStage" class="cd-stage" style="display:none;">
    <div class="cd-prompt" id="cdPromptWrap">
        <span>一</span>
        <span class="cd-blank" id="cdPromptBlank">_</span>
        <span id="cdNoun"></span>
    </div>
    <div class="cd-pronunciation" id="cdPronunciation"></div>
    <div class="cd-gloss" id="cdGloss"></div>
    <div class="cd-gloss" id="cdReversePrompt" style="display:none; font-size:1.1rem; color:var(--text-secondary);"></div>

    <div class="cd-options" id="cdOptions" style="display:none;"></div>

    <form id="cdTypedForm" style="display:none;" autocomplete="off">
        <input id="cdTypedInput" type="text" class="cd-typed-input" maxlength="2"
               inputmode="text" autocapitalize="off"
               data-i18n-placeholder="classifier_drill.typed_placeholder"
               placeholder="量词" />
    </form>
</div>

<div id="cdFeedback" class="cd-feedback" role="dialog" aria-modal="true">
    <div class="cd-feedback-card">
        <div class="cd-feedback-canonical" id="cdFeedbackCanonical"></div>
        <div class="cd-feedback-group" id="cdFeedbackGroup"></div>
        <div class="cd-feedback-examples" id="cdFeedbackExamples"></div>
        <button class="cd-feedback-cta" id="cdFeedbackContinue" data-i18n="classifier_drill.feedback_continue">Continue</button>
    </div>
</div>

<div id="cdResults" class="cd-results" style="display:none;">
    <div class="cd-results-grade" id="cdResultsGrade">🎯</div>
    <div class="cd-results-pct"><span id="cdResultsPct">0</span>%</div>
    <div class="cd-results-stats">
        <div><strong id="cdResultsCorrect">0</strong> / <span id="cdResultsTotal">0</span> <span data-i18n="classifier_drill.results_classifiers">classifiers</span></div>
        <div><strong id="cdResultsTime">0</strong>s</div>
    </div>
    <div id="cdResultsNote" class="text-muted" style="display:block; margin-bottom:12px;"></div>
    <div class="cd-results-elo-badge" id="cdResultsElo" style="display:none;"></div>
    <button class="cd-feedback-cta" id="cdResultsContinue" data-i18n="session.next_item">Next</button>
</div>
`;
