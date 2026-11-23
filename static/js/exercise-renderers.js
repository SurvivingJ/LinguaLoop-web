/**
 * Shared Exercise Renderers
 *
 * Extracted from exercises.html so both the Exercises page and Vocab Dojo
 * can reuse the same rendering logic. Host pages inject callbacks via init().
 *
 * Usage:
 *   ExRenderers.init({ cardEl, isAnswered, setAnswered, showFeedback, submitAttempt, nextExercise });
 *   ExRenderers.dispatch(exerciseType, exercise, content, wordHTML);
 */
/* global LinguaI18n */
const ExRenderers = (function () {
  'use strict';

  // ── Injected by host page ──
  let _card = null;
  // Optional pinned action area (the session's .ld-dock). When a host passes
  // `dockEl`, each renderer puts its feedback, Check and Next controls there
  // and only the question in the card; without one everything goes in the
  // card, as before.
  let _dock = null;
  let _isAnswered = () => false;
  let _setAnswered = () => {};
  let _showFeedback = () => {};
  let _submitAttempt = () => {};
  let _nextExercise = () => {};

  function init({
    cardEl,
    dockEl,
    isAnswered,
    setAnswered,
    showFeedback,
    submitAttempt,
    nextExercise,
  }) {
    _card = cardEl;
    _dock = dockEl || null;
    _isAnswered = isAnswered;
    _setAnswered = setAnswered;
    _showFeedback = showFeedback;
    _submitAttempt = submitAttempt;
    _nextExercise = nextExercise;
  }

  // ── Pure utilities ──

  // Delegate to the canonical escapeHtml in utils.js when available;
  // fall back to a local implementation so this file is usable on
  // pages that don't load utils.js (e.g., the admin dashboard).
  function escHtml(s) {
    if (
      typeof window !== 'undefined' &&
      window.LinguaUtils &&
      typeof window.LinguaUtils.escapeHtml === 'function'
    ) {
      return window.LinguaUtils.escapeHtml(s);
    }
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function shuffleArr(a) {
    a = a.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function fmtType(t) {
    if (typeof LinguaI18n !== 'undefined') {
      const k = 'exercises.type.' + t;
      const v = LinguaI18n.t(k);
      if (v !== k) return v;
    }
    return t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function i18n(key, v) {
    if (typeof LinguaI18n !== 'undefined') return LinguaI18n.t(key, v);
    const map = {
      'exercises.next': 'Next',
      'exercises.check': 'Check',
      'exercises.instruction.fill_blank': 'Fill in the blank:',
      'exercises.instruction.choose_translation': 'Choose the correct translation:',
      'exercises.instruction.which_sentence': `Which sentence uses "${(v && v.word) || ''}" correctly?`,
      'exercises.instruction.odd_one_out': 'Which word does not belong?',
      'exercises.instruction.translate_to_tl': 'Translate into the target language:',
      'exercises.instruction.collocation_gap_fill': 'Fill in the missing word:',
      'exercises.instruction.collocation_repair': 'Choose the correct word:',
      'exercises.instruction.collocation_repair_phase2': 'Now type the correct word:',
      'exercises.instruction.odd_collocation_out': `Which collocation with "${(v && v.word) || ''}" does not fit?`,
      'exercises.type_placeholder': 'Type your answer...',
      'exercises.hint': `Hint: ${(v && v.hint) || ''}`,
      'exercises.instruction.hanzi_to_pinyin': 'Choose the correct pinyin:',
      'exercises.instruction.pinyin_to_hanzi': 'Choose the characters for this pinyin:',
      'exercises.instruction.kanji_to_reading': 'Choose the correct reading:',
      'exercises.instruction.reading_to_kanji': 'Choose the written form for this reading:',
      'exercises.instruction.tone_id_word': 'Which tone pattern does this word have?',
      'exercises.instruction.classifier_match': 'Choose the correct measure word:',
      'exercises.instruction.counter_match': 'Choose the correct counter:',
      'exercises.instruction.synonym': 'Which word means the same?',
      'exercises.instruction.antonym': 'Which word means the opposite?',
      'exercises.instruction.word_family': 'Choose the correct form of the word:',
      'exercises.instruction.particle_selection': 'Choose the correct particle:',
      'exercises.in_context': 'In this sentence:',
      'exercises.tone_id_answer': `Full pinyin: ${(v && v.pinyin) || ''}`,
      'exercises.measure_word_group': `Group: ${(v && v.label) || ''}`,
      'exercises.word_family_stem': `Stem: ${(v && v.stem) || ''}`,
      'exercises.word_family_pos': `Needs a ${(v && v.pos) || ''}`,
    };
    return map[key] || key;
  }

  /** i18n() with an English fallback for keys the bundle may not have yet. */
  function tr(key, fallback, v) {
    const s = i18n(key, v);
    return s && s !== key ? s : fallback;
  }

  /** Put the question in the card and the controls in the dock (or both in the card). */
  function paint(body, dock) {
    if (_dock) {
      _card.innerHTML = body;
      _dock.innerHTML = dock;
    } else {
      _card.innerHTML = body + dock;
    }
  }

  function typeBadge(icon, label, cefr) {
    return `<div class="exercise-type-badge"><i class="fas ${icon}" aria-hidden="true"></i> ${label}${cefr ? `<span class="exercise-cefr-badge">${escHtml(cefr)}</span>` : ''}</div>`;
  }

  function checkBtnHTML(id, extra) {
    return `<button type="button" class="ld-btn exercise-check-btn" id="${id}"${extra || ''}><i class="fas fa-check" aria-hidden="true"></i>${i18n('exercises.check')}</button>`;
  }

  /** "Tap an answer to check it." — shown in the dock until an answer is given. */
  function tapHintHTML() {
    return `<p class="ld-hint ex-dock-hint">${tr('exercises.tap_to_check', 'Tap an answer to check it.')}</p>`;
  }

  const FEEDBACK_HTML = '<div class="exercise-feedback" id="exerciseFeedback" role="status"></div>';

  /** The answer is in: drop the "tap an answer" hint and show the verdict. */
  function dropHint() {
    const hint = (_dock || _card).querySelector('.ex-dock-hint');
    if (hint) hint.remove();
  }

  // Explanations are written for the right answer and often open with
  // "Correct." in the study language; that reads wrong after a miss.
  const AFFIRM_RE = /^\s*(?:正解です|正解|正确|正確|correct|¡?correcto)[。．.!！]\s*/i;

  function showFeedbackNow(ok, expl) {
    dropHint();
    _showFeedback(ok, !ok && typeof expl === 'string' ? expl.replace(AFFIRM_RE, '') : expl);
  }

  /** Escape, then show authored **emphasis** as bold instead of raw asterisks. */
  function emHtml(s) {
    return escHtml(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  }

  function nextBtnHTML() {
    return `<button type="button" class="ld-btn exercise-next-btn" id="nextBtn">${i18n('exercises.next')} <i class="fas fa-arrow-right" aria-hidden="true"></i></button>`;
  }

  function bindNext() {
    document.getElementById('nextBtn').addEventListener('click', _nextExercise);
  }

  /** One answer option: a real button (keyboard and screen-reader reachable). */
  function optionHTML(value, i, inner) {
    return `<button type="button" class="exercise-option ld-opt" data-value="${escHtml(value)}"><span class="option-letter ld-opt__key" aria-hidden="true">${String.fromCharCode(65 + i)}</span>${inner}</button>`;
  }

  // ── MCQ shared builder ──

  /**
   * @param {Object} [extra] Optional per-item behaviour:
   *   - `labels`    {value: displayText} — show something other than the
   *     option's own value. `tone_id_word` needs this: its options are tone
   *     digits ("1", "4"), which are the submitted value but not readable text.
   *   - `sublabels` {value: secondLine} — a muted second line under an option
   *     (classifier/counter readings: 家 / jiā).
   *   - `accepted`  [value] — every value graded correct. Measure-word items
   *     are genuinely multi-answer (书 takes 本 *and* 册), and this path grades
   *     client-side, so equality against a single key would mark a right
   *     answer wrong.
   *   - `plain`     true when the options are native-language text.
   */
  function mcq(badge, cefr, instr, prompt, opts, correct, expl, wordHTML, extra) {
    extra = extra || {};
    const labels = extra.labels || null;
    const sublabels = extra.sublabels || null;
    // `notes` {value: text} — revealed under each option once answered.
    const notes = extra.notes || null;
    const accepted =
      Array.isArray(extra.accepted) && extra.accepted.length ? extra.accepted : [correct];
    const shuffled = shuffleArr(opts);
    // `plain`: the options are in the learner's own language (translations,
    // definitions, tone labels), so they are not set in the target-language face.
    const optCls = extra.plain ? 'option-text' : 'option-text ex-tl';
    let h =
      (wordHTML || '') +
      typeBadge('fa-pen-to-square', badge, cefr) +
      `<div class="exercise-instruction">${instr}</div>` +
      (prompt ? `<div class="exercise-prompt ex-tl">${prompt}</div>` : '') +
      `<div class="exercise-options ld-opts" id="optionsList">`;
    shuffled.forEach((o, i) => {
      const v = typeof o === 'object' ? o.text : o;
      const label = (labels && labels[v]) || v;
      const sub = sublabels && sublabels[v] ? `<small>${escHtml(sublabels[v])}</small>` : '';
      h += optionHTML(v, i, `<span class="${optCls}">${escHtml(label)}${sub}</span>`);
    });
    h += `</div>`;
    paint(h, tapHintHTML() + FEEDBACK_HTML + nextBtnHTML());

    document.getElementById('optionsList').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const opt = e.target.closest('.exercise-option');
      if (!opt) return;
      _setAnswered(true);
      const sel = opt.dataset.value;
      const ok = accepted.indexOf(sel) !== -1;
      document.querySelectorAll('#optionsList .exercise-option').forEach((o) => {
        o.classList.add('disabled');
        if (accepted.indexOf(o.dataset.value) !== -1) o.classList.add('correct');
      });
      if (!ok) opt.classList.add('incorrect');
      if (notes) {
        document.querySelectorAll('#optionsList .exercise-option').forEach((o) => {
          const n = notes[o.dataset.value];
          if (!n) return;
          const d = document.createElement('span');
          d.className = 'exercise-option-note';
          d.style.cssText =
            'display:block;font-size:13px;color:var(--text-secondary);margin-top:6px';
          d.textContent = n;
          o.querySelector('.option-text').appendChild(d);
        });
      }
      showFeedbackNow(ok, expl);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  // ── Type renderers ──

  function renderCloze(ex, c, w) {
    let p = escHtml(c.sentence_with_blank).replace(
      '___',
      '<span class="blank ld-blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    if (c.word_definition)
      p += `<div class="ex-note ex-note--def">${escHtml(c.word_definition)}</div>`;
    mcq(
      fmtType('cloze_completion'),
      ex.cefr_level,
      i18n('exercises.instruction.fill_blank'),
      p,
      c.options,
      c.correct_answer,
      c.explanation,
      w
    );
  }

  /**
   * cloze_typed (TASK-532) — the same blank as cloze_completion, no options.
   *
   * Two things make this different from every other renderer here:
   *
   * 1. **It does not decide correctness.** The accepted set is compared under
   *    normalisation rules (NFKC, t2s, case, trailing punctuation) that live in
   *    utils/answer_normalization.py. Re-implementing them in JS would give one
   *    rule two implementations, so the server's verdict is authoritative and
   *    the local guess only drives the optimistic UI.
   *
   * 2. **It must survive an IME.** For Chinese and Japanese the learner types
   *    romaji/pinyin into a composition buffer and presses Enter to CHOOSE a
   *    candidate. Submitting on that Enter would submit the half-built romaji.
   *    compositionstart/end tracks the buffer, and keydown ignores Enter while
   *    composing (plus keyCode 229, which some IMEs send instead of firing
   *    compositionstart at all).
   */
  function renderClozeTyped(ex, c, w) {
    const prompt = escHtml(c.sentence_with_blank || '').replace(
      '___',
      '<span class="blank ld-blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    const isIme = c.input_mode === 'ime';
    const instruction = i18n('exercises.instruction.type_missing_word');
    const h =
      (w || '') +
      typeBadge('fa-keyboard', fmtType('cloze_typed'), ex.cefr_level) +
      `<div class="exercise-instruction">${instruction}</div>` +
      `<div class="exercise-prompt ex-tl">${prompt}</div>` +
      `<input type="text" class="exercise-input-area ex-tl" id="ctInput" autocomplete="off" ` +
      `autocorrect="off" autocapitalize="off" spellcheck="false" ` +
      `${isIme ? 'inputmode="text" ' : ''}` +
      `aria-label="${escHtml(instruction)}" ` +
      `placeholder="${i18n('exercises.type_word_placeholder')}">` +
      `<div id="ctCorrection" class="sip-correction" style="display:none;"></div>`;
    paint(h, checkBtnHTML('ctCheckBtn') + FEEDBACK_HTML + nextBtnHTML());

    const inp = document.getElementById('ctInput');
    const btn = document.getElementById('ctCheckBtn');
    let composing = false;
    inp.addEventListener('compositionstart', () => {
      composing = true;
    });
    inp.addEventListener('compositionend', () => {
      composing = false;
    });
    inp.focus();

    const submit = () => {
      if (_isAnswered()) return;
      const typed = inp.value.trim();
      if (!typed) return;
      _setAnswered(true);
      inp.readOnly = true;
      btn.style.display = 'none';

      // Optimistic only. _submitAttempt POSTs `typed`; the server re-grades and
      // its verdict is the one that reaches the ladder.
      const accepted = (c.answer && c.answer.accepted) || [];
      const guess = accepted.some((a) => String(a).trim().toLowerCase() === typed.toLowerCase());
      if (!guess && c.target_word) {
        const corr = document.getElementById('ctCorrection');
        corr.innerHTML =
          '<i class="fas fa-check me-1" aria-hidden="true"></i>' + escHtml(c.target_word);
        corr.style.display = '';
      }
      showFeedbackNow(guess, c.explanation || '');
      _submitAttempt(guess, { typed: typed });
    };

    btn.addEventListener('click', submit);
    inp.addEventListener('keydown', (e) => {
      // keyCode 229 = "the IME is handling this key" on browsers that do not
      // fire compositionstart reliably. Both guards are needed.
      if (e.key === 'Enter' && !composing && e.keyCode !== 229) {
        e.preventDefault();
        submit();
      }
    });
    bindNext();
  }

  function renderTlNl(ex, c, w) {
    mcq(
      fmtType('tl_nl_translation'),
      ex.cefr_level,
      i18n('exercises.instruction.choose_translation'),
      escHtml(c.tl_sentence),
      c.options,
      c.correct_nl,
      '',
      w,
      { plain: true }
    );
  }

  function renderSemDiscrim(ex, c, w) {
    const cor = c.sentences.find((s) => s.is_correct);
    const notes = {};
    c.sentences.forEach((s) => {
      if (s.explanation) notes[s.text] = s.explanation;
    });
    const hasNotes = Object.keys(notes).length > 0;
    mcq(
      fmtType('semantic_discrimination'),
      ex.cefr_level,
      i18n('exercises.instruction.which_sentence', { word: escHtml(c.target_word || 'the word') }),
      '',
      c.sentences.map((s) => s.text),
      cor ? cor.text : '',
      hasNotes ? '' : dedupeExpl(c.explanation),
      w,
      hasNotes ? { notes } : undefined
    );
  }

  // Older rows joined every wrong sentence's note into one string, often the
  // same sentence repeated; show each distinct sentence once.
  function dedupeExpl(s) {
    if (!s) return '';
    const parts = String(s)
      .split(/(?<=[。．.!?！？])\s*/)
      .map((x) => x.trim())
      .filter(Boolean);
    return [...new Set(parts)].join(' ');
  }

  function renderOddOneOut(ex, c, w) {
    const odd = c.items[c.odd_index];
    let h =
      (w || '') +
      typeBadge('fa-question-circle', fmtType('odd_one_out'), ex.cefr_level) +
      `<div class="exercise-instruction">${i18n('exercises.instruction.odd_one_out')}</div>` +
      (c.shared_property
        ? `<div class="exercise-prompt exercise-prompt--note">${i18n('exercises.hint', { hint: escHtml(c.shared_property) })}</div>`
        : '') +
      `<div class="exercise-options ld-opts" id="optionsList">`;
    shuffleArr(c.items).forEach((it, i) => {
      h += optionHTML(it, i, `<span class="option-text ex-tl">${escHtml(it)}</span>`);
    });
    h += `</div>`;
    paint(h, tapHintHTML() + FEEDBACK_HTML + nextBtnHTML());
    document.getElementById('optionsList').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const o = e.target.closest('.exercise-option');
      if (!o) return;
      _setAnswered(true);
      const sel = o.dataset.value,
        ok = sel === odd;
      document.querySelectorAll('#optionsList .exercise-option').forEach((x) => {
        x.classList.add('disabled');
        if (x.dataset.value === odd) x.classList.add('correct');
      });
      if (!ok) o.classList.add('incorrect');
      showFeedbackNow(ok, c.explanation);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderNlTl(ex, c, w) {
    const instruction = i18n('exercises.instruction.translate_to_tl');
    const h =
      (w || '') +
      typeBadge('fa-language', fmtType('nl_tl_translation'), ex.cefr_level) +
      `<div class="exercise-instruction">${instruction}</div>` +
      `<div class="exercise-prompt">${escHtml(c.nl_sentence)}</div>` +
      `<textarea class="exercise-input-area ex-tl" id="translationInput" rows="3" aria-label="${escHtml(instruction)}" placeholder="${i18n('exercises.type_placeholder')}"></textarea>`;
    paint(h, checkBtnHTML('checkBtn') + FEEDBACK_HTML + nextBtnHTML());
    document.getElementById('checkBtn').addEventListener('click', function () {
      if (_isAnswered()) return;
      _setAnswered(true);
      const inp = document.getElementById('translationInput').value.trim();
      const pri = (c.primary_tl || '').trim();
      const vars = (c.acceptable_variants || []).map((v) => v.trim().toLowerCase());
      const ok = inp.toLowerCase() === pri.toLowerCase() || vars.includes(inp.toLowerCase());
      let expl = '';
      if (c.grading_notes) expl += c.grading_notes;
      if (!ok) expl += '\nExpected: ' + pri;
      if (c.acceptable_variants && c.acceptable_variants.length)
        expl += '\nAlso accepted: ' + c.acceptable_variants.join(', ');
      this.style.display = 'none';
      document.getElementById('translationInput').readOnly = true;
      showFeedbackNow(ok, expl);
      _submitAttempt(ok, { typed: inp });
    });
    bindNext();
  }

  function renderColloGap(ex, c, w) {
    const p = escHtml(c.sentence).replace(
      '___',
      '<span class="blank ld-blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    mcq(
      fmtType('collocation_gap_fill'),
      ex.cefr_level,
      i18n('exercises.instruction.collocation_gap_fill'),
      p,
      c.options,
      c.correct,
      '',
      w
    );
  }

  function renderColloRepair(ex, c, w) {
    let words = c.words;
    if (!words) {
      const tokens = c.sentence_with_error.split(/\s+/);
      words = tokens.map((t) => {
        const clean = t.replace(/[.,;:!?"'\-()[\]]/g, '').toLowerCase();
        return { text: t, is_error: clean === (c.error_word || '').toLowerCase() };
      });
    }

    const phase2 = i18n('exercises.instruction.collocation_repair_phase2');
    let h =
      (w || '') +
      typeBadge('fa-wrench', fmtType('collocation_repair'), ex.cefr_level) +
      `<div class="exercise-instruction">${i18n('exercises.instruction.collocation_repair')}</div>` +
      `<div class="sip-parts ex-tl" id="crWords">`;
    words.forEach((wd, i) => {
      h += `<button type="button" class="sip-part" data-idx="${i}">${escHtml(wd.text)}</button>`;
    });
    h +=
      `</div>` +
      `<div id="crPhase2" class="ex-phase2" style="display:none;">` +
      `<div class="exercise-instruction exercise-instruction--sub">${phase2}</div>` +
      `<input type="text" class="exercise-input-area ex-tl" id="crInput" autocomplete="off" aria-label="${escHtml(phase2)}">` +
      `</div>` +
      `<div id="crCorrection" class="sip-correction" style="display:none;"></div>`;
    // The phase-2 Check is shown together with #crPhase2.
    paint(
      h,
      tapHintHTML() +
        checkBtnHTML('crCheckBtn', ' style="display:none;"') +
        FEEDBACK_HTML +
        nextBtnHTML()
    );

    document.getElementById('crWords').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const part = e.target.closest('.sip-part');
      if (!part) return;
      const idx = parseInt(part.dataset.idx);
      const selected = words[idx];
      const ok = !!selected.is_error;

      document.querySelectorAll('#crWords .sip-part').forEach((el) => {
        el.classList.add('disabled');
        const pi = parseInt(el.dataset.idx);
        if (words[pi].is_error) el.classList.add('correct');
      });
      if (!ok) part.classList.add('incorrect');

      if (ok) {
        _setAnswered(true);
        document.getElementById('crPhase2').style.display = '';
        document.getElementById('crCheckBtn').style.display = '';
        dropHint();
        const inp = document.getElementById('crInput');
        inp.focus();

        const checkTyped = () => {
          const typed = inp.value.trim();
          if (!typed) return;
          inp.readOnly = true;
          document.getElementById('crCheckBtn').style.display = 'none';
          const phase2ok = typed.toLowerCase() === c.correct_word.toLowerCase();
          if (!phase2ok) {
            const corr = document.getElementById('crCorrection');
            corr.innerHTML =
              '<i class="fas fa-check me-1" aria-hidden="true"></i>' + escHtml(c.correct_word);
            corr.style.display = '';
          }
          showFeedbackNow(phase2ok, c.explanation);
          _submitAttempt(phase2ok, {
            selected_word: selected.text,
            typed_correction: typed,
            phase1_correct: true,
            phase2_correct: phase2ok,
          });
        };
        document.getElementById('crCheckBtn').addEventListener('click', checkTyped);
        inp.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') checkTyped();
        });
      } else {
        _setAnswered(true);
        const corr = document.getElementById('crCorrection');
        corr.innerHTML =
          '<i class="fas fa-check me-1" aria-hidden="true"></i>' +
          escHtml(c.error_word) +
          ' \u2192 ' +
          escHtml(c.correct_word);
        corr.style.display = '';
        showFeedbackNow(false, c.explanation);
        _submitAttempt(false, { selected_word: selected.text, phase1_correct: false });
      }
    });
    bindNext();
  }

  function renderOddCollo(ex, c, w) {
    const odd = c.collocations[c.odd_index];
    let h =
      (w || '') +
      typeBadge('fa-question-circle', fmtType('odd_collocation_out'), ex.cefr_level) +
      `<div class="exercise-instruction">${i18n('exercises.instruction.odd_collocation_out', { word: escHtml(c.head_word) })}</div>` +
      `<div class="exercise-options ld-opts" id="optionsList">`;
    shuffleArr(c.collocations).forEach((it, i) => {
      h += optionHTML(it, i, `<span class="option-text ex-tl">${escHtml(it)}</span>`);
    });
    h += `</div>`;
    paint(h, tapHintHTML() + FEEDBACK_HTML + nextBtnHTML());
    document.getElementById('optionsList').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const o = e.target.closest('.exercise-option');
      if (!o) return;
      _setAnswered(true);
      const sel = o.dataset.value,
        ok = sel === odd;
      document.querySelectorAll('#optionsList .exercise-option').forEach((x) => {
        x.classList.add('disabled');
        if (x.dataset.value === odd) x.classList.add('correct');
      });
      if (!ok) o.classList.add('incorrect');
      showFeedbackNow(ok, c.explanation);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderSpotPart(ex, c, w) {
    const errorPart = c.parts.find((p) => p.is_error);
    let h =
      (w || '') +
      typeBadge('fa-search', fmtType('spot_incorrect_part'), ex.cefr_level) +
      `<div class="exercise-instruction">Tap the part of the sentence that contains an error:</div>` +
      `<div class="sip-parts ex-tl" id="sipParts">`;
    c.parts.forEach((p, i) => {
      h += `<button type="button" class="sip-part" data-idx="${i}">${escHtml(p.text)}</button>`;
    });
    h += `</div><div id="sipCorrection" class="sip-correction" style="display:none;"></div>`;
    paint(h, tapHintHTML() + FEEDBACK_HTML + nextBtnHTML());

    document.getElementById('sipParts').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const part = e.target.closest('.sip-part');
      if (!part) return;
      _setAnswered(true);
      const idx = parseInt(part.dataset.idx);
      const selected = c.parts[idx];
      const ok = !!selected.is_error;

      document.querySelectorAll('.sip-part').forEach((el) => {
        el.classList.add('disabled');
        const pi = parseInt(el.dataset.idx);
        if (c.parts[pi].is_error) el.classList.add('correct');
      });
      if (!ok) part.classList.add('incorrect');

      if (errorPart && errorPart.correct_form) {
        const corr = document.getElementById('sipCorrection');
        corr.innerHTML =
          '<i class="fas fa-check me-1"></i>Correct form: ' + escHtml(errorPart.correct_form);
        corr.style.display = '';
      }

      const expl = errorPart ? errorPart.explanation : '';
      showFeedbackNow(ok, expl);
      _submitAttempt(ok, { selected_index: idx, selected_text: selected.text });
    });
    bindNext();
  }

  function renderSpotSentence(ex, c, w) {
    const incorrect = c.sentences.find((s) => !s.is_correct);
    const opts = c.sentences.map((s) => s.text);
    let h =
      (w || '') +
      typeBadge('fa-search', fmtType('spot_incorrect_sentence'), ex.cefr_level) +
      `<div class="exercise-instruction">Which sentence contains an error?</div>` +
      `<div class="exercise-options ld-opts" id="optionsList">`;
    opts.forEach((t, i) => {
      h += optionHTML(t, i, `<span class="option-text ex-tl">${escHtml(t)}</span>`);
    });
    h += `</div>`;
    paint(h, tapHintHTML() + FEEDBACK_HTML + nextBtnHTML());

    const correctVal = incorrect ? incorrect.text : '';
    document.getElementById('optionsList').addEventListener('click', (e) => {
      if (_isAnswered()) return;
      const opt = e.target.closest('.exercise-option');
      if (!opt) return;
      _setAnswered(true);
      const sel = opt.dataset.value;
      const ok = sel === correctVal;

      document.querySelectorAll('#optionsList .exercise-option').forEach((o) => {
        o.classList.add('disabled');
        if (o.dataset.value === correctVal) o.classList.add('correct');
      });
      if (!ok) opt.classList.add('incorrect');

      let expl = '';
      if (incorrect) {
        if (incorrect.error_description) expl += incorrect.error_description;
        if (incorrect.error_type) expl += (expl ? ' ' : '') + '(' + incorrect.error_type + ')';
      }
      showFeedbackNow(ok, expl);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderJumbled(ex, c, w) {
    const chunks = c.chunks;
    // Stored rows that were never chunked server-side have no `chunks`; say so
    // instead of throwing on `chunks.length`.
    if (!Array.isArray(chunks) || chunks.length === 0)
      throw new Error('jumbled_sentence content has no chunks (not prepared server-side)');
    // `chunks` is stored in answer order, so a missing ordering is the identity.
    const correctOrder = Array.isArray(c.correct_ordering)
      ? c.correct_ordering
      : chunks.map((_, i) => i);
    const placed = [];
    const initialBankOrder = shuffleArr([...Array(chunks.length).keys()]);

    function render() {
      const answered = _isAnswered();
      const complete = placed.length === chunks.length;
      let h =
        (w || '') +
        typeBadge('fa-shuffle', fmtType('jumbled_sentence'), ex.cefr_level) +
        `<div class="exercise-instruction">Arrange the words in the correct order:</div>` +
        `<div class="js-answer ex-tl" id="jsAnswer">`;
      placed.forEach((ci, i) => {
        // `js-chunk--placed` carries the removal affordance (a × via ::after).
        h += `<span class="js-chunk js-chunk--placed" draggable="true" data-placed="${i}" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
      });
      if (placed.length === 0)
        h += `<span class="js-empty">Tap or drag words below to build the sentence</span>`;
      h += `</div><div class="js-bank ex-tl" id="jsBank">`;
      const bankIndices = initialBankOrder.filter((i) => !placed.includes(i));
      bankIndices.forEach((ci) => {
        h += `<span class="js-chunk" draggable="true" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
      });
      h += `</div>`;
      // Grading is explicit: the learner arranges, reviews, then submits.
      // Auto-grading on the final placement used to lock the card at exactly
      // the moment they'd want to fix a word.
      let dock = '';
      if (!answered) dock += checkBtnHTML('jsCheckBtn', complete ? '' : ' disabled');
      dock += FEEDBACK_HTML + nextBtnHTML();
      paint(h, dock);

      const answerDiv = document.getElementById('jsAnswer');
      const bankDiv = document.getElementById('jsBank');
      const checkBtn = document.getElementById('jsCheckBtn');
      if (checkBtn) checkBtn.addEventListener('click', checkJumbled);

      // A native HTML5 drag swallows the `click` that would otherwise follow,
      // and Chrome decides a press is a drag after only a few px of travel —
      // so tapping a chunk silently did nothing often enough to read as broken.
      // Track the pointer ourselves and treat a near-stationary press as a tap,
      // keeping the plain `click` path for keyboard/AT and for environments
      // without pointer events.
      const TAP_SLOP_PX = 5;

      // Both paths can fire for one gesture. Re-rendering replaces _card's
      // children but leaves the old subtree intact and still wired to the old
      // zone listener, so the losing handler would act a second time on a stale
      // index. Marking the node makes the pair idempotent.
      function tap(ch, handler) {
        if (_isAnswered() || !ch || ch.dataset.tapped) return;
        ch.dataset.tapped = '1';
        handler(ch);
      }

      function bindTap(zone, handler) {
        let start = null;
        zone.addEventListener('pointerdown', (e) => {
          const ch = e.target.closest('.js-chunk');
          start = ch ? { ch: ch, x: e.clientX, y: e.clientY } : null;
        });
        zone.addEventListener('pointerup', (e) => {
          const s = start;
          start = null;
          if (!s) return;
          if (Math.abs(e.clientX - s.x) > TAP_SLOP_PX) return;
          if (Math.abs(e.clientY - s.y) > TAP_SLOP_PX) return;
          tap(s.ch, handler);
        });
        zone.addEventListener('pointercancel', () => {
          start = null;
        });
        zone.addEventListener('click', (e) => {
          tap(e.target.closest('.js-chunk'), handler);
        });
      }

      bindTap(bankDiv, (ch) => {
        const ci = parseInt(ch.dataset.chunk, 10);
        if (Number.isNaN(ci)) return;
        placed.push(ci);
        render();
      });
      bindTap(answerDiv, (ch) => {
        // `parseInt` guarded because splice(NaN, 1) silently drops chunk 0.
        const at = parseInt(ch.dataset.placed, 10);
        if (Number.isNaN(at)) return;
        placed.splice(at, 1);
        render();
      });

      // Drag and drop
      let dragChunkIdx = null;

      function getInsertIndex(zone, clientX) {
        const children = [...zone.querySelectorAll('.js-chunk:not(.dragging)')];
        for (let i = 0; i < children.length; i++) {
          const rect = children[i].getBoundingClientRect();
          if (clientX < rect.left + rect.width / 2) return i;
        }
        return children.length;
      }

      function removeIndicator() {
        const old = answerDiv.querySelector('.js-drop-indicator');
        if (old) old.remove();
      }

      function showIndicator(zone, clientX) {
        removeIndicator();
        if (zone !== answerDiv) return;
        const indicator = document.createElement('span');
        indicator.className = 'js-drop-indicator';
        const children = [...zone.querySelectorAll('.js-chunk:not(.dragging)')];
        const idx = getInsertIndex(zone, clientX);
        if (idx < children.length) {
          zone.insertBefore(indicator, children[idx]);
        } else {
          zone.appendChild(indicator);
        }
      }

      _card.querySelectorAll('.js-chunk').forEach((el) => {
        el.addEventListener('dragstart', (e) => {
          if (_isAnswered()) {
            e.preventDefault();
            return;
          }
          dragChunkIdx = parseInt(el.dataset.chunk);
          el.classList.add('dragging');
          e.dataTransfer.effectAllowed = 'move';
        });
        el.addEventListener('dragend', () => {
          el.classList.remove('dragging');
          removeIndicator();
        });
      });

      [answerDiv, bankDiv].forEach((zone) => {
        zone.addEventListener('dragover', (e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'move';
          zone.classList.add('drag-over');
          showIndicator(zone, e.clientX);
        });
        zone.addEventListener('dragleave', (e) => {
          if (!zone.contains(e.relatedTarget)) {
            zone.classList.remove('drag-over');
            removeIndicator();
          }
        });
        zone.addEventListener('drop', (e) => {
          e.preventDefault();
          zone.classList.remove('drag-over');
          removeIndicator();
          if (_isAnswered() || dragChunkIdx === null) return;
          const target = zone.id === 'jsAnswer' ? 'answer' : 'bank';

          const existingIdx = placed.indexOf(dragChunkIdx);
          if (existingIdx !== -1) placed.splice(existingIdx, 1);

          if (target === 'answer') {
            const insertAt = getInsertIndex(zone, e.clientX);
            placed.splice(insertAt, 0, dragChunkIdx);
          }

          dragChunkIdx = null;
          render();
        });
      });

      bindNext();
    }

    function checkJumbled() {
      if (_isAnswered()) return;
      // The Check button is disabled until every chunk is placed, but guard
      // here too: `every` on a short array returns true whenever the prefix
      // happens to be right ([0] against [0,1,2]), which would grade a
      // half-built sentence as correct.
      if (placed.length !== chunks.length) return;
      const ok =
        placed.length === correctOrder.length && placed.every((ci, i) => ci === correctOrder[i]);
      // Lock first so the final render() draws the answered state — no Check
      // button — in one pass.
      _setAnswered(true);
      render();
      const answerDiv = document.getElementById('jsAnswer');
      answerDiv.classList.add(ok ? 'correct' : 'incorrect');
      document.querySelectorAll('.js-chunk').forEach((el) => {
        el.classList.add('disabled');
        el.removeAttribute('draggable');
      });
      let expl = '';
      if (!ok) expl = 'Correct order: ' + correctOrder.map((i) => chunks[i]).join(' ');
      showFeedbackNow(ok, expl);
      _submitAttempt(ok, { user_ordering: placed });
    }

    render();
  }

  function renderFlashcard(ex, c, w) {
    const front = c.target_word || c.front_sentence || ex.lemma || '';
    const back = c.word_definition || c.back_sentence || ex.definition || '';
    const pron = c.pronunciation || ex.pronunciation || '';
    const example = c.example_sentence || '';
    const h =
      (w || '') +
      typeBadge('fa-layer-group', fmtType(ex.exercise_type)) +
      `<div class="ex-fcard">` +
      `<div class="exercise-prompt ex-tl ex-fcard__front">${emHtml(front)}</div>` +
      (pron ? `<div class="ex-fcard__pron">${escHtml(pron)}</div>` : '') +
      `<div id="fcBack" class="ex-fcard__back" style="display:none;">` +
      `<div class="ex-fcard__meaning">${emHtml(back)}</div>` +
      (example ? `<div class="ex-fcard__example ex-tl">${emHtml(example)}</div>` : '') +
      `</div></div>`;
    const dock =
      `<button type="button" class="ld-btn" id="revealBtn"><i class="fas fa-eye" aria-hidden="true"></i>${escHtml(tr('exercises.fc_reveal', 'Reveal'))}</button>` +
      `<div id="fcRate" style="display:none;"><p class="ld-hint mb-2">${escHtml(tr('exercises.fc_how_well', 'How well did you know this?'))}</p>` +
      `<div class="ld-row"><button type="button" class="ld-btn fc-rate fc-rate--no" data-ok="0">${escHtml(tr('exercises.fc_no', "Didn't know"))}</button><button type="button" class="ld-btn ld-btn--ok fc-rate" data-ok="1">${escHtml(tr('exercises.fc_yes', 'Knew it'))}</button></div></div>` +
      FEEDBACK_HTML +
      nextBtnHTML();
    paint(h, dock);
    document.getElementById('revealBtn').addEventListener('click', function () {
      document.getElementById('fcBack').style.display = 'block';
      document.getElementById('fcRate').style.display = 'block';
      this.style.display = 'none';
    });
    document.querySelectorAll('.fc-rate').forEach((b) =>
      b.addEventListener('click', function () {
        if (_isAnswered()) return;
        _setAnswered(true);
        const ok = this.dataset.ok === '1';
        document.getElementById('fcRate').style.display = 'none';
        showFeedbackNow(ok, '');
        _submitAttempt(ok, { self_rated: true });
      })
    );
    bindNext();
  }

  function renderGeneric(ex, c, w) {
    paint(
      (w || '') +
        typeBadge('fa-question', fmtType(ex.exercise_type), ex.cefr_level) +
        `<div class="exercise-prompt exercise-prompt--raw">${escHtml(JSON.stringify(c, null, 2))}</div>`,
      `<button type="button" class="ld-btn exercise-next-btn show" id="nextBtn">${i18n('exercises.next')} <i class="fas fa-arrow-right" aria-hidden="true"></i></button>`
    );
    bindNext();
  }

  // ── New ladder renderers ──

  function renderPhonetic(ex, c, w) {
    const hasAudio = !!c.audio_url;
    // When audio is present, the IPA + written pronunciation would give
    // away the answer (the learner is supposed to identify the spoken
    // word from 4 written choices). Show only the play button.
    const prompt =
      `<div class="phonetic-display">` +
      (hasAudio
        ? `<button type="button" class="audio-play-btn" id="phoneticPlayBtn" aria-label="Play audio">
                       <i class="fas fa-volume-up" aria-hidden="true"></i>
                   </button>
                   <div class="phonetic-note">Tap to replay</div>`
        : (c.ipa ? `<div class="ipa">${escHtml(c.ipa)}</div>` : '') +
          (c.pronunciation ? `<div class="pron">${escHtml(c.pronunciation)}</div>` : '') +
          (c.syllable_count
            ? `<div class="phonetic-note">${c.syllable_count} syllables</div>`
            : '')) +
      `</div>`;
    mcq(
      'Phonetic Recognition',
      null,
      hasAudio ? 'Which word did you hear?' : 'Which word matches this pronunciation?',
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );

    if (hasAudio) {
      const playAudio = () => {
        try {
          const a = new Audio(c.audio_url);
          a.play().catch((e) => console.error('Audio playback failed:', e));
        } catch (e) {
          console.error('Audio init failed:', e);
        }
      };
      const btn = document.getElementById('phoneticPlayBtn');
      if (btn) btn.addEventListener('click', playAudio);
      // Auto-play once on first render so the learner doesn't have to tap.
      playAudio();
    }
  }

  function renderDefinitionMatch(ex, c, w) {
    const prompt =
      `<div class="ex-word ex-word--brand">${escHtml(c.word || ex.lemma)}</div>` +
      (c.pronunciation ? `<div class="ex-sub">${escHtml(c.pronunciation)}</div>` : '');
    mcq(
      'Definition Match',
      null,
      'Choose the correct definition:',
      prompt,
      c.options || [],
      // v2 (flattenNl) carries `correct_answer`; v1 rows carry `correct_definition`.
      c.correct_answer || c.correct_definition || '',
      '',
      w,
      { plain: true }
    );
  }

  function renderMorphologySlot(ex, c, w) {
    let prompt = escHtml(c.sentence_with_blank || '').replace(
      '___',
      '<span class="blank ld-blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    if (c.base_form || c.form_label) {
      prompt += `<div class="ex-note">Base form: <strong>${escHtml(c.base_form)}</strong>`;
      if (c.form_label) prompt += ` &mdash; fill in the <em>${escHtml(c.form_label)}</em>`;
      prompt += '</div>';
    }
    mcq(
      'Morphology Slot',
      null,
      'Choose the correct form:',
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );
  }

  // ── Ladder script/sound, measure-word and relation renderers ──

  const BLANK_SPAN = '<span class="blank ld-blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>';

  function withBlank(text) {
    return escHtml(text || '').replace('___', BLANK_SPAN);
  }

  /** A muted note under the prompt — stem, required form, distractor group. */
  function noteHTML(parts) {
    const kept = parts.filter(Boolean);
    if (!kept.length) return '';
    return `<div class="ex-note">${kept.join(' &mdash; ')}</div>`;
  }

  /**
   * The disambiguating sentence carried by polyphone items.
   *
   * `reveal` is the direction-dependent half. Script→sound already shows the
   * word as the prompt, so the sentence can show it too, emphasised. Sound→
   * script must NOT: the key *is* the written form, and printing it in the
   * context sentence hands over the answer. There the target is blanked, and
   * when it has no literal match in the sentence (an inflected JA form) the
   * whole sentence is dropped rather than shown intact — a hard item beats a
   * free one.
   */
  function contextHTML(sentence, target, reveal, key) {
    if (!sentence) return '';
    let body;
    if (reveal) {
      body = target
        ? escHtml(sentence)
            .split(escHtml(target))
            .join(`<strong>${escHtml(target)}</strong>`)
        : escHtml(sentence);
    } else {
      if (!target || sentence.indexOf(target) === -1) return '';
      body = escHtml(sentence).split(escHtml(target)).join(BLANK_SPAN);
      // Belt and braces: today `context_target` is the key in every stored
      // row, but they are separate fields and a future row could differ.
      if (key) body = body.split(escHtml(key)).join(BLANK_SPAN);
    }
    return (
      `<div class="ex-context">` +
      `<div class="ex-context__label">${i18n('exercises.in_context')}</div>` +
      `${body}</div>`
    );
  }

  // Types whose prompt is the script and whose answer is the pronunciation.
  const SCRIPT_TO_SOUND = { hanzi_to_pinyin: true, kanji_to_reading: true };

  /**
   * hanzi_to_pinyin / pinyin_to_hanzi / kanji_to_reading / reading_to_kanji.
   *
   * One renderer for four types: the stored item is the same shape in every
   * direction (`prompt`, `options`, `correct_answer`), and only the wording of
   * the instruction differs. What is not shared is how the context sentence is
   * treated — see contextHTML.
   */
  function renderScriptSound(ex, c, w) {
    const type = ex.exercise_type;
    const prompt =
      `<div class="ex-word">${escHtml(c.prompt || c.word || '')}</div>` +
      contextHTML(c.context_sentence, c.context_target, !!SCRIPT_TO_SOUND[type], c.correct_answer);
    mcq(
      fmtType(type),
      ex.cefr_level,
      i18n('exercises.instruction.' + type),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );
  }

  /**
   * tone_id_word — pick the tone contour, not the whole pronunciation.
   *
   * The options are contour strings ("1", "24"); `option_labels` carries the
   * readable form ("rising (2) + falling (4)"). The value is what gets
   * submitted, so it stays as the option's data-value and only the display
   * text is swapped. The pinyin shown in the prompt is deliberately the
   * toneless one — the marked pinyin would print the answer.
   */
  function renderToneId(ex, c, w) {
    const prompt =
      `<div class="ex-word">${escHtml(c.word || ex.lemma || '')}</div>` +
      (c.toneless_pinyin
        ? `<div class="ex-sub ex-sub--spaced">${escHtml(c.toneless_pinyin)}</div>`
        : '');
    mcq(
      fmtType('tone_id_word'),
      ex.cefr_level,
      i18n('exercises.instruction.tone_id_word'),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.full_pinyin ? i18n('exercises.tone_id_answer', { pinyin: escHtml(c.full_pinyin) }) : '',
      w,
      { labels: c.option_labels || null, plain: !!c.option_labels }
    );
  }

  /**
   * classifier_match (zh) / counter_match (ja) — the same item in two languages.
   *
   * Both are multi-answer by nature, so `accepted_answers` drives grading;
   * `option_readings` rides along because a JA counter fuses with the numeral
   * (一本 = いっぽん) and the form alone does not say how the phrase sounds.
   */
  function renderMeasureWord(ex, c, w) {
    const type = ex.exercise_type;
    const prompt =
      `<div class="ex-word ex-word--md">${withBlank(c.stem)}</div>` +
      (c.pronunciation ? `<div class="ex-sub">${escHtml(c.pronunciation)}</div>` : '');
    mcq(
      fmtType(type),
      ex.cefr_level,
      i18n('exercises.instruction.' + type),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.semantic_label
        ? i18n('exercises.measure_word_group', { label: escHtml(c.semantic_label) })
        : '',
      w,
      {
        sublabels: c.option_readings || null,
        accepted: c.accepted_answers || null,
      }
    );
  }

  /**
   * synonym_antonym_match — the relation is the question, so it drives the
   * instruction rather than sitting in the prompt as a label.
   */
  function renderSynAnt(ex, c, w) {
    const relation = c.relation === 'antonym' ? 'antonym' : 'synonym';
    const prompt =
      `<div class="ex-word ex-word--brand">${escHtml(c.word || ex.lemma || '')}</div>` +
      (c.word_definition
        ? `<div class="ex-note ex-note--def">${escHtml(c.word_definition)}</div>`
        : '');
    mcq(
      fmtType('synonym_antonym_match'),
      ex.cefr_level,
      i18n('exercises.instruction.' + relation),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );
  }

  /**
   * word_family — fill the slot with the right derivation of a stem.
   *
   * `required_pos` is shown because the slot is defined by it: without it
   * "decide / decision / decisive" are three defensible fills of one blank.
   */
  function renderWordFamily(ex, c, w) {
    const prompt =
      `<div>${withBlank(c.sentence_with_blank)}</div>` +
      noteHTML([
        c.stem ? i18n('exercises.word_family_stem', { stem: escHtml(c.stem) }) : '',
        c.required_pos ? i18n('exercises.word_family_pos', { pos: escHtml(c.required_pos) }) : '',
      ]);
    mcq(
      fmtType('word_family'),
      ex.cefr_level,
      i18n('exercises.instruction.word_family'),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );
  }

  /**
   * particle_selection — the JA L4. `error_tags` is not rendered: it is a
   * confusion-class enum the practice engine aggregates on, not learner text.
   */
  function renderParticleSelection(ex, c, w) {
    const prompt = `<div class="ex-sentence">${withBlank(c.sentence_with_blank)}</div>`;
    mcq(
      fmtType('particle_selection'),
      ex.cefr_level,
      i18n('exercises.instruction.particle_selection'),
      prompt,
      c.options || [],
      c.correct_answer || '',
      c.explanation || '',
      w
    );
  }

  // ── Schema-v2 nl envelope (TASK-519) ──

  /**
   * Native-language-facing keys inside `content.nl.<code>` map back onto the
   * flat names the renderers below were written against.
   */
  const V2_TO_V1 = {
    correct: 'correct_nl',
    prompt: 'nl_sentence',
    definition: 'word_definition',
  };

  /**
   * Flatten a schema-v2 content envelope for the learner's native language.
   *
   * v2 stores nl-facing text under `content.nl.<code>` so one item can serve
   * several native languages. Every renderer predates that, so flattening once
   * here keeps them all unchanged. v1 content passes through untouched, and an
   * envelope missing the learner's language falls back to its only block
   * rather than rendering blank.
   */
  function flattenNl(c) {
    if (!c || typeof c !== 'object' || !(c.schema_version >= 2)) return c;
    const nl = c.nl;
    if (!nl || typeof nl !== 'object') return c;

    const want =
      (window.LinguaI18n && LinguaI18n.currentLanguage && LinguaI18n.currentLanguage()) || 'en';
    const codes = Object.keys(nl);
    let block = nl[want];
    if (!block && codes.length === 1) block = nl[codes[0]];
    if (!block || typeof block !== 'object') return c;

    const flat = {};
    Object.keys(c).forEach((k) => {
      if (k !== 'nl') flat[k] = c[k];
    });
    Object.keys(block).forEach((k) => {
      flat[V2_TO_V1[k] || k] = block[k];
    });
    flat.nl_language = nl[want] ? want : codes[0];
    return flat;
  }

  // ── Dispatcher ──

  function dispatch(type, ex, c, w) {
    c = flattenNl(c);
    const map = {
      cloze_completion: renderCloze,
      cloze_typed: renderClozeTyped,
      tl_nl_translation: renderTlNl,
      semantic_discrimination: renderSemDiscrim,
      odd_one_out: renderOddOneOut,
      nl_tl_translation: renderNlTl,
      collocation_gap_fill: renderColloGap,
      collocation_repair: renderColloRepair,
      odd_collocation_out: renderOddCollo,
      text_flashcard: renderFlashcard,
      listening_flashcard: renderFlashcard,
      spot_incorrect_part: renderSpotPart,
      spot_incorrect_sentence: renderSpotSentence,
      jumbled_sentence: renderJumbled,
      phonetic_recognition: renderPhonetic,
      definition_match: renderDefinitionMatch,
      morphology_slot: renderMorphologySlot,
      hanzi_to_pinyin: renderScriptSound,
      pinyin_to_hanzi: renderScriptSound,
      kanji_to_reading: renderScriptSound,
      reading_to_kanji: renderScriptSound,
      tone_id_word: renderToneId,
      classifier_match: renderMeasureWord,
      counter_match: renderMeasureWord,
      synonym_antonym_match: renderSynAnt,
      word_family: renderWordFamily,
      particle_selection: renderParticleSelection,
    };
    const fn = map[type] || renderGeneric;
    fn(ex, c, w);
  }

  // ── Public API ──
  return {
    init,
    dispatch,
    // Expose utilities for host pages that need them
    escHtml,
    shuffleArr,
    fmtType,
    i18n,
    mcq,
  };
})();

window.ExRenderers = ExRenderers;
