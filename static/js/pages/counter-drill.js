// /counter-drill: the Japanese counter drill as a page. The drill engine is the
// one behind the measure-word drill (session/players/classifier_drill.js); this
// file is the counter's config: endpoints, i18n keys, markup and how a counter
// item is shown and judged.
import { escapeHtml, shuffle } from '../session/dom.js';
import { mountDrillPage } from '../session/players/classifier_drill.js';

// Every counter the dictionary marks correct, not just the primary. 兎
// genuinely takes both 匹 and 羽; marking either wrong teaches a falsehood,
// which is why the API returns an array here.
const acceptedAnswers = (item) => (item.correct_counter_text || []).filter(Boolean);

function resetPrompt({ el }) {
  el.promptBlank.textContent = '_';
  el.promptBlank.classList.remove('correct', 'wrong');
}

// Feedback follows every answer, right or wrong.
function recordAnswer(d, isCorrect, picked) {
  if (isCorrect) d.state.correct += 1;
  d.openFeedback(isCorrect, picked);
}

function renderOptions(d) {
  const { state, el } = d;
  const item = state.currentItem;
  const correct = (item.correct_counter_text || [])[0] || '';
  const correctReading = (item.correct_counter_reading || [])[0] || '';

  const opts = [{ text: correct, reading: correctReading, correct: true }];
  (item.distractor_text || []).forEach((text, i) => {
    opts.push({
      text: text,
      reading: (item.distractor_reading || [])[i] || '',
      correct: false,
    });
  });
  state.currentOptions = shuffle(opts);

  el.options.innerHTML = state.currentOptions
    .map(
      (o, i) =>
        `<button type="button" class="ct-option" data-idx="${i}">` +
        `<div class="ct-option-text">${escapeHtml(o.text)}</div>` +
        `<div class="ct-option-reading">${escapeHtml(o.reading)}</div>` +
        `</button>`
    )
    .join('');

  el.options.querySelectorAll('button[data-idx]').forEach((btn) => {
    btn.addEventListener('click', () => d.choose(parseInt(btn.dataset.idx, 10)));
  });
}

export const COUNTER = {
  kind: 'counter',
  testType: 'counter_drill',
  label: 'Counter',
  apiBase: '/api/counter-drill',
  languageId: 3, // Japanese: the route rejects anything else.
  i18n: 'counter_drill',
  prefix: 'ct',
  // Two modes only. The classifier drill also has 'auto', which routes each
  // item by the learner's per-classifier mastery level; counters have no
  // equivalent mastery table.
  modeKey: 'ct_mode',
  defaultMode: 'mc',
  ignoreSameMode: true,
  display: { loading: '', bar: '', stage: '', results: '' },
  exitUrl: '/tests',
  lenientLoad: true,
  submitHeaders: { 'Content-Type': 'application/json' },

  // IME-safe typed input. A Japanese learner types romaji into a composition
  // buffer and presses Enter to CHOOSE a candidate, so submitting on that
  // Enter would submit the half-built romaji. compositionstart/end tracks the
  // buffer, and keyCode 229 covers the IMEs that never fire compositionstart
  // at all. Both guards are needed.
  bindTyped(d) {
    const { state, el } = d;
    let composing = false;

    function submitTyped() {
      if (state.isLocked) return;
      const raw = (el.typedInput.value || '').trim();
      if (!raw) return;
      state.isLocked = true;
      el.typedInput.disabled = true;

      const isCorrect = acceptedAnswers(state.currentItem).includes(raw);
      el.promptBlank.textContent = raw;
      el.promptBlank.classList.add(isCorrect ? 'correct' : 'wrong');

      recordAnswer(d, isCorrect, raw);
    }

    el.typedInput.addEventListener('compositionstart', () => {
      composing = true;
    });
    el.typedInput.addEventListener('compositionend', () => {
      composing = false;
    });
    el.typedInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !composing && e.keyCode !== 229) {
        e.preventDefault();
        submitTyped();
      }
    });
    el.typedForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!composing) submitTyped();
    });
  },

  digitKeys: (state) => state.mode === 'mc' && !state.isLocked,

  onModeChange(d) {
    resetPrompt(d);
    d.renderInput();
  },

  renderCurrent(d) {
    const { state, el } = d;
    const item = state.items[state.cursor];
    state.currentItem = item;
    state.isLocked = false;
    resetPrompt(d);

    el.noun.textContent = item.noun_lemma || '';
    el.numeral.textContent = '一';
    el.reading.textContent = item.noun_pronunciation || '';
    el.gloss.textContent = item.noun_gloss || '';
    el.progressLabel.textContent = String(state.cursor);
    el.progressFill.style.width = ((state.cursor / state.items.length) * 100).toFixed(1) + '%';

    d.renderInput();
  },

  renderInput(d) {
    const { state, el } = d;
    if (state.mode === 'type') {
      el.options.style.display = 'none';
      el.typedForm.style.display = '';
      el.typedInput.value = '';
      el.typedInput.disabled = false;
      el.typedInput.focus();
    } else {
      el.typedForm.style.display = 'none';
      el.options.style.display = '';
      renderOptions(d);
    }
  },

  onChoice(d, idx) {
    const { state, el } = d;
    const picked = state.currentOptions[idx];
    const isCorrect = !!picked && acceptedAnswers(state.currentItem).includes(picked.text);

    el.options.querySelectorAll('button[data-idx]').forEach((btn, i) => {
      btn.disabled = true;
      if (state.currentOptions[i].correct) btn.classList.add('correct');
      else if (i === idx && !isCorrect) btn.classList.add('wrong');
    });

    recordAnswer(d, isCorrect, picked ? picked.text : '');
  },

  fillFeedback({ state, el, t }, isCorrect) {
    const item = state.currentItem;
    const canonical = (item.correct_counter_text || [])[0] || '';
    const reading = (item.correct_counter_reading || [])[0] || '';
    const alts = (item.correct_counter_text || []).slice(1).filter(Boolean);

    el.fbCanonical.textContent =
      (isCorrect ? '✓ ' : '✕ ') + (item.noun_lemma || '') + 'を一' + canonical;
    el.fbReading.textContent = reading;
    el.fbGroup.textContent = item.semantic_label || '';

    // The euphonic numeral readings are the actual difficulty of Japanese
    // counters: a learner who has memorised 本 without them still cannot say
    // "three pens". Shown on every item, right or wrong.
    const numerals = item.numeral_readings || {};
    const keys = Object.keys(numerals).sort((a, b) => Number(a) - Number(b));
    el.fbNumerals.innerHTML = keys.length
      ? escapeHtml(t('feedback_numerals')) +
        '<br>' +
        keys
          .map((k) => `<b>${escapeHtml(k)}${escapeHtml(canonical)}</b> ${escapeHtml(numerals[k])}`)
          .join('　')
      : '';

    el.fbAlts.textContent = alts.length ? t('feedback_also') + ' ' + alts.join('、') : '';
  },

  onFinish({ el }) {
    el.header.style.display = 'none';
  },

  grade: (pct) => (pct >= 90 ? '🏆' : pct >= 70 ? '🎯' : '📚'),

  submitBody: (d, score, timing) => ({
    ...score,
    started_at: timing.started_at,
    finished_at: timing.finished_at,
    idempotency_key:
      window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : undefined,
  }),

  async onSubmitted({ el }, resp) {
    const payload = await resp.json();
    const result = (payload && (payload.data || payload)) || {};
    const change = result.user_elo_change && result.user_elo_change.change;
    if (typeof change === 'number' && change !== 0) {
      el.resultsElo.textContent = (change > 0 ? '▲ +' : '▼ ') + change + ' ELO';
      el.resultsElo.style.display = '';
    }
  },

  // The round is over and the learner has their score; a failed submission
  // costs ELO, not the session. Surfaced, not swallowed.
  onSubmitError({ el, t }, err) {
    console.error('Counter drill submit failed:', err);
    el.resultsElo.textContent = t('submit_failed');
    el.resultsElo.style.display = '';
  },

  pageMarkup: `
<div id="ctHeader" class="ct-header py-3 px-3 px-md-4 flex items-center justify-between gap-2" style="display:none;">
    <div class="ct-header-left">
        <a href="/tests" class="text-slate-500 hover:text-slate-700" aria-label="Home" style="font-size: 1.1rem; line-height: 1;">&larr;</a>
        <h1 class="text-base font-semibold" data-i18n="counter_drill.title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Counters</h1>
    </div>
    <div class="ct-header-right">
        <div class="text-sm text-slate-500" style="white-space: nowrap;"><span id="ctProgressLabel">0</span> / <span id="ctProgressTotal">0</span></div>
    </div>
    <div class="ct-header-controls">
        <div class="ct-mode-toggle" id="ctModeToggle">
            <button type="button" data-mode="mc" class="active" data-i18n="counter_drill.mode_mc">Choose</button>
            <button type="button" data-mode="type" data-i18n="counter_drill.mode_type">Type</button>
        </div>
    </div>
    <div class="ct-progress-bar"><div class="ct-progress-fill" id="ctProgressFill"></div></div>
</div>

<div id="ctLoading" class="text-center py-20 text-slate-500" data-i18n="counter_drill.loading">Loading…</div>

<div id="ctEmpty" class="ct-empty" style="display:none;">
    <p data-i18n="counter_drill.empty">No counter items are available yet.</p>
</div>

<div id="ctStage" class="ct-stage" style="display:none;">
    <div class="ct-prompt" id="ctPromptWrap">
        <span id="ctNoun"></span>
        <span>を</span>
        <span id="ctNumeral">一</span>
        <span class="ct-blank" id="ctPromptBlank">_</span>
    </div>
    <div class="ct-reading" id="ctReading"></div>
    <div class="ct-gloss" id="ctGloss"></div>

    <div class="ct-options" id="ctOptions" style="display:none;"></div>

    <form id="ctTypedForm" style="display:none;" autocomplete="off">
        <input id="ctTypedInput" type="text" class="ct-typed-input" maxlength="3"
               inputmode="text" autocapitalize="off" autocorrect="off" spellcheck="false"
               data-i18n-placeholder="counter_drill.typed_placeholder"
               placeholder="助数詞" />
        <div class="ct-typed-hint" data-i18n="counter_drill.typed_hint">Press Enter to check</div>
    </form>
</div>

<div id="ctFeedback" class="ct-feedback" role="dialog" aria-modal="true">
    <div class="ct-feedback-card">
        <div class="ct-feedback-canonical" id="ctFeedbackCanonical"></div>
        <div class="ct-feedback-reading" id="ctFeedbackReading"></div>
        <div class="ct-feedback-group" id="ctFeedbackGroup"></div>
        <div class="ct-feedback-numerals" id="ctFeedbackNumerals"></div>
        <div class="ct-feedback-alts" id="ctFeedbackAlts"></div>
        <button class="ct-feedback-cta" id="ctFeedbackContinue" data-i18n="counter_drill.feedback_continue">Continue</button>
    </div>
</div>

<div id="ctResults" class="ct-results" style="display:none;">
    <div class="ct-results-grade" id="ctResultsGrade">🎯</div>
    <div class="ct-results-pct"><span id="ctResultsPct">0</span>%</div>
    <div class="ct-results-stats">
        <div><strong id="ctResultsCorrect">0</strong> / <span id="ctResultsTotal">0</span> <span data-i18n="counter_drill.results_counters">counters</span></div>
        <div><strong id="ctResultsTime">0</strong>s</div>
    </div>
    <div class="ct-results-elo-badge" id="ctResultsElo" style="display:none;"></div>
    <div class="ct-results-actions">
        <button class="ct-feedback-cta" id="ctResultsNext" data-i18n="counter_drill.results_next">Next round</button>
        <button class="ct-feedback-cta" id="ctResultsExit" style="background: var(--bg-page); color: var(--text-primary);" data-i18n="counter_drill.results_exit">Done</button>
    </div>
</div>
`,
};

const root = document.getElementById('drillRoot');
if (root && root.dataset.drill === 'counter') {
  const start = () => mountDrillPage(root, COUNTER);
  if (document.readyState === 'complete') start();
  else document.addEventListener('DOMContentLoaded', start);
}
