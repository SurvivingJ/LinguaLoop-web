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
/* eslint-disable no-unused-vars */
/* global LinguaI18n */
const ExRenderers = (function () {
  'use strict';

  // ── Injected by host page ──
  let _card = null;
  let _isAnswered = () => false;
  let _setAnswered = () => {};
  let _showFeedback = () => {};
  let _submitAttempt = () => {};
  let _nextExercise = () => {};

  function init({ cardEl, isAnswered, setAnswered, showFeedback, submitAttempt, nextExercise }) {
    _card = cardEl;
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

  function nextBtnHTML() {
    return `<button class="btn btn-primary exercise-next-btn" id="nextBtn">${i18n('exercises.next')} <i class="fas fa-arrow-right ms-1"></i></button>`;
  }

  function bindNext() {
    document.getElementById('nextBtn').addEventListener('click', _nextExercise);
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
   */
  function mcq(badge, cefr, instr, prompt, opts, correct, expl, wordHTML, extra) {
    extra = extra || {};
    const labels = extra.labels || null;
    const sublabels = extra.sublabels || null;
    const accepted =
      Array.isArray(extra.accepted) && extra.accepted.length ? extra.accepted : [correct];
    const shuffled = shuffleArr(opts);
    let h =
      (wordHTML || '') +
      `<div class="exercise-type-badge"><i class="fas fa-pen-to-square"></i> ${badge}${cefr ? `<span class="exercise-cefr-badge">${cefr}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${instr}</div>` +
      `<div class="exercise-prompt">${prompt}</div>` +
      `<div class="exercise-options" id="optionsList">`;
    shuffled.forEach((o, i) => {
      const v = typeof o === 'object' ? o.text : o;
      const label = (labels && labels[v]) || v;
      const sub =
        sublabels && sublabels[v]
          ? `<span style="display:block;font-size:13px;color:var(--text-secondary);margin-top:2px">${escHtml(sublabels[v])}</span>`
          : '';
      h += `<div class="exercise-option" data-value="${escHtml(v)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(label)}${sub}</span></div>`;
    });
    h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;

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
      _showFeedback(ok, expl);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  // ── Type renderers ──

  function renderCloze(ex, c, w) {
    let p = escHtml(c.sentence_with_blank).replace(
      '___',
      '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    if (c.word_definition)
      p += `<div style="font-size:14px;color:var(--text-secondary);margin-top:10px;font-style:italic;">${escHtml(c.word_definition)}</div>`;
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
      '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    const isIme = c.input_mode === 'ime';
    const h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-keyboard"></i> ${fmtType('cloze_typed')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${i18n('exercises.instruction.type_missing_word')}</div>` +
      `<div class="exercise-prompt">${prompt}</div>` +
      `<input type="text" class="exercise-input-area" id="ctInput" autocomplete="off" ` +
      `autocorrect="off" autocapitalize="off" spellcheck="false" ` +
      `${isIme ? 'inputmode="text" ' : ''}` +
      `style="width:100%;padding:10px;font-size:18px;" ` +
      `placeholder="${i18n('exercises.type_word_placeholder')}">` +
      `<button class="btn btn-primary exercise-check-btn" id="ctCheckBtn"><i class="fas fa-check me-2"></i>${i18n('exercises.check')}</button>` +
      `<div id="ctCorrection" class="sip-correction" style="display:none;"></div>` +
      `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;

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
        corr.innerHTML = '<i class="fas fa-check me-1"></i>' + escHtml(c.target_word);
        corr.style.display = '';
      }
      _showFeedback(guess, c.explanation || '');
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
      w
    );
  }

  function renderSemDiscrim(ex, c, w) {
    const cor = c.sentences.find((s) => s.is_correct);
    mcq(
      fmtType('semantic_discrimination'),
      ex.cefr_level,
      i18n('exercises.instruction.which_sentence', { word: c.target_word || 'the word' }),
      '',
      c.sentences.map((s) => s.text),
      cor ? cor.text : '',
      c.explanation,
      w
    );
  }

  function renderOddOneOut(ex, c, w) {
    const odd = c.items[c.odd_index];
    let h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-question-circle"></i> ${fmtType('odd_one_out')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${i18n('exercises.instruction.odd_one_out')}</div>` +
      (c.shared_property
        ? `<div class="exercise-prompt" style="font-size:15px;color:var(--text-secondary)">${i18n('exercises.hint', { hint: escHtml(c.shared_property) })}</div>`
        : '') +
      `<div class="exercise-options" id="optionsList">`;
    shuffleArr(c.items).forEach((it, i) => {
      h += `<div class="exercise-option" data-value="${escHtml(it)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(it)}</span></div>`;
    });
    h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;
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
      _showFeedback(ok, c.explanation);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderNlTl(ex, c, w) {
    const h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-language"></i> ${fmtType('nl_tl_translation')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${i18n('exercises.instruction.translate_to_tl')}</div>` +
      `<div class="exercise-prompt">${escHtml(c.nl_sentence)}</div>` +
      `<textarea class="exercise-input-area" id="translationInput" placeholder="${i18n('exercises.type_placeholder')}"></textarea>` +
      `<button class="btn btn-primary exercise-check-btn" id="checkBtn"><i class="fas fa-check me-2"></i>${i18n('exercises.check')}</button>` +
      `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;
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
      _showFeedback(ok, expl);
      _submitAttempt(ok, { typed: inp });
    });
    bindNext();
  }

  function renderColloGap(ex, c, w) {
    const p = escHtml(c.sentence).replace(
      '___',
      '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
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

    let h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-wrench"></i> ${fmtType('collocation_repair')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${i18n('exercises.instruction.collocation_repair')}</div>` +
      `<div class="sip-parts" id="crWords">`;
    words.forEach((wd, i) => {
      h += `<span class="sip-part" data-idx="${i}">${escHtml(wd.text)}</span>`;
    });
    h +=
      `</div>` +
      `<div id="crPhase2" style="display:none;margin-top:16px;">` +
      `<div class="exercise-instruction" style="font-size:14px;">${i18n('exercises.instruction.collocation_repair_phase2')}</div>` +
      `<input type="text" class="exercise-input-area" id="crInput" style="width:100%;padding:10px;font-size:16px;" autocomplete="off">` +
      `<button class="btn btn-primary exercise-check-btn" id="crCheckBtn" style="margin-top:8px;"><i class="fas fa-check me-2"></i>${i18n('exercises.check')}</button>` +
      `</div>` +
      `<div id="crCorrection" class="sip-correction" style="display:none;"></div>` +
      `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;

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
            corr.innerHTML = '<i class="fas fa-check me-1"></i>' + escHtml(c.correct_word);
            corr.style.display = '';
          }
          _showFeedback(phase2ok, c.explanation);
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
          '<i class="fas fa-check me-1"></i>' +
          escHtml(c.error_word) +
          ' \u2192 ' +
          escHtml(c.correct_word);
        corr.style.display = '';
        _showFeedback(false, c.explanation);
        _submitAttempt(false, { selected_word: selected.text, phase1_correct: false });
      }
    });
    bindNext();
  }

  function renderOddCollo(ex, c, w) {
    const odd = c.collocations[c.odd_index];
    let h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-question-circle"></i> ${fmtType('odd_collocation_out')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">${i18n('exercises.instruction.odd_collocation_out', { word: escHtml(c.head_word) })}</div>` +
      `<div class="exercise-options" id="optionsList">`;
    shuffleArr(c.collocations).forEach((it, i) => {
      h += `<div class="exercise-option" data-value="${escHtml(it)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(it)}</span></div>`;
    });
    h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;
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
      _showFeedback(ok, c.explanation);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderSpotPart(ex, c, w) {
    const errorPart = c.parts.find((p) => p.is_error);
    let h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-search"></i> ${fmtType('spot_incorrect_part')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">Tap the part of the sentence that contains an error:</div>` +
      `<div class="sip-parts" id="sipParts">`;
    c.parts.forEach((p, i) => {
      h += `<span class="sip-part" data-idx="${i}">${escHtml(p.text)}</span>`;
    });
    h +=
      `</div><div id="sipCorrection" class="sip-correction" style="display:none;"></div>` +
      `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;

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
      _showFeedback(ok, expl);
      _submitAttempt(ok, { selected_index: idx, selected_text: selected.text });
    });
    bindNext();
  }

  function renderSpotSentence(ex, c, w) {
    const incorrect = c.sentences.find((s) => !s.is_correct);
    const opts = c.sentences.map((s) => s.text);
    let h =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-search"></i> ${fmtType('spot_incorrect_sentence')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-instruction">Which sentence contains an error?</div>` +
      `<div class="exercise-options" id="optionsList">`;
    opts.forEach((t, i) => {
      h += `<div class="exercise-option" data-value="${escHtml(t)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(t)}</span></div>`;
    });
    h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
    _card.innerHTML = h;

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
      _showFeedback(ok, expl);
      _submitAttempt(ok, { selected: sel });
    });
    bindNext();
  }

  function renderJumbled(ex, c, w) {
    const correctOrder = c.correct_ordering;
    const chunks = c.chunks;
    const placed = [];
    const initialBankOrder = shuffleArr([...Array(chunks.length).keys()]);

    function render() {
      let h =
        (w || '') +
        `<div class="exercise-type-badge"><i class="fas fa-shuffle"></i> ${fmtType('jumbled_sentence')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
        `<div class="exercise-instruction">Arrange the words in the correct order:</div>` +
        `<div class="js-answer" id="jsAnswer">`;
      placed.forEach((ci, i) => {
        h += `<span class="js-chunk" draggable="true" data-placed="${i}" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
      });
      if (placed.length === 0)
        h += `<span style="color:var(--text-secondary);font-size:14px;padding:8px;">Tap or drag words below to build the sentence</span>`;
      h += `</div><div class="js-bank" id="jsBank">`;
      const bankIndices = initialBankOrder.filter((i) => !placed.includes(i));
      bankIndices.forEach((ci) => {
        h += `<span class="js-chunk" draggable="true" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
      });
      h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
      _card.innerHTML = h;

      const answerDiv = document.getElementById('jsAnswer');
      const bankDiv = document.getElementById('jsBank');

      bankDiv.addEventListener('click', (e) => {
        if (_isAnswered()) return;
        const ch = e.target.closest('.js-chunk');
        if (!ch) return;
        placed.push(parseInt(ch.dataset.chunk));
        if (placed.length === chunks.length) checkJumbled();
        else render();
      });
      answerDiv.addEventListener('click', (e) => {
        if (_isAnswered()) return;
        const ch = e.target.closest('.js-chunk');
        if (!ch || ch.dataset.placed === undefined) return;
        placed.splice(parseInt(ch.dataset.placed), 1);
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
          if (placed.length === chunks.length) checkJumbled();
          else render();
        });
      });

      bindNext();
    }

    function checkJumbled() {
      _setAnswered(true);
      const ok = placed.every((ci, i) => ci === correctOrder[i]);
      const answerDiv = document.getElementById('jsAnswer');
      answerDiv.classList.add(ok ? 'correct' : 'incorrect');
      document.querySelectorAll('.js-chunk').forEach((el) => {
        el.classList.add('disabled');
        el.removeAttribute('draggable');
      });
      let expl = '';
      if (!ok) expl = 'Correct order: ' + correctOrder.map((i) => chunks[i]).join(' ');
      _showFeedback(ok, expl);
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
      `<div class="exercise-type-badge"><i class="fas fa-layer-group"></i> ${fmtType(ex.exercise_type)}</div>` +
      `<div class="exercise-prompt">${escHtml(front)}</div>` +
      (pron
        ? `<div style="text-align:center;color:var(--text-secondary);font-size:16px;margin-bottom:16px;">${escHtml(pron)}</div>`
        : '') +
      `<div id="fcBack" style="display:none;text-align:center;margin-bottom:20px;">` +
      `<div style="font-size:18px;color:var(--text-primary);font-weight:500;margin-bottom:8px;">${escHtml(back)}</div>` +
      (example
        ? `<div style="font-size:14px;color:var(--text-secondary);font-style:italic;">${escHtml(example)}</div>`
        : '') +
      `</div><button class="btn btn-outline-primary w-100 mb-2" id="revealBtn"><i class="fas fa-eye me-2"></i>Reveal</button>` +
      `<div id="fcRate" style="display:none;"><p class="text-center text-muted mb-2">How well did you know this?</p>` +
      `<div class="d-flex gap-2"><button class="btn btn-danger flex-fill fc-rate" data-ok="0">Didn't know</button><button class="btn btn-success flex-fill fc-rate" data-ok="1">Knew it</button></div></div>` +
      `${nextBtnHTML()}`;
    _card.innerHTML = h;
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
        _showFeedback(ok, '');
        _submitAttempt(ok, { self_rated: true });
      })
    );
    bindNext();
  }

  function renderGeneric(ex, c, w) {
    _card.innerHTML =
      (w || '') +
      `<div class="exercise-type-badge"><i class="fas fa-question"></i> ${fmtType(ex.exercise_type)}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
      `<div class="exercise-prompt" style="font-size:14px;text-align:left;white-space:pre-wrap;">${escHtml(JSON.stringify(c, null, 2))}</div>` +
      `<button class="btn btn-primary exercise-next-btn show" id="nextBtn">${i18n('exercises.next')} <i class="fas fa-arrow-right ms-1"></i></button>`;
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
                       <i class="fas fa-volume-up"></i>
                   </button>
                   <div style="font-size:13px;color:var(--text-muted);margin-top:8px">Tap to replay</div>`
        : (c.ipa ? `<div class="ipa">${escHtml(c.ipa)}</div>` : '') +
          (c.pronunciation ? `<div class="pron">${escHtml(c.pronunciation)}</div>` : '') +
          (c.syllable_count
            ? `<div style="font-size:13px;color:var(--text-muted);margin-top:4px">${c.syllable_count} syllables</div>`
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
      `<div style="text-align:center;font-size:28px;font-weight:700;color:var(--primary);margin-bottom:8px">${escHtml(c.word || ex.lemma)}</div>` +
      (c.pronunciation
        ? `<div style="text-align:center;color:var(--text-secondary);margin-bottom:16px">${escHtml(c.pronunciation)}</div>`
        : '');
    mcq(
      'Definition Match',
      null,
      'Choose the correct definition:',
      prompt,
      c.options || [],
      c.correct_definition || '',
      '',
      w
    );
  }

  function renderMorphologySlot(ex, c, w) {
    let prompt = escHtml(c.sentence_with_blank || '').replace(
      '___',
      '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'
    );
    if (c.base_form || c.form_label) {
      prompt += `<div style="font-size:14px;color:var(--text-secondary);margin-top:10px">Base form: <strong>${escHtml(c.base_form)}</strong>`;
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

  const BLANK_SPAN = '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>';

  function withBlank(text) {
    return escHtml(text || '').replace('___', BLANK_SPAN);
  }

  /** A muted note under the prompt — stem, required form, distractor group. */
  function noteHTML(parts) {
    const kept = parts.filter(Boolean);
    if (!kept.length) return '';
    return `<div style="font-size:14px;color:var(--text-secondary);margin-top:10px">${kept.join(' &mdash; ')}</div>`;
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
      `<div style="font-size:15px;color:var(--text-secondary);margin-top:12px">` +
      `<div style="font-size:13px;color:var(--text-muted);margin-bottom:4px">${i18n('exercises.in_context')}</div>` +
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
      `<div style="font-size:32px;font-weight:700;color:var(--text-primary)">${escHtml(c.prompt || c.word || '')}</div>` +
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
      `<div style="font-size:34px;font-weight:700;color:var(--text-primary)">${escHtml(c.word || ex.lemma || '')}</div>` +
      (c.toneless_pinyin
        ? `<div style="font-size:18px;color:var(--text-secondary);margin-top:6px;letter-spacing:1px">${escHtml(c.toneless_pinyin)}</div>`
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
      { labels: c.option_labels || null }
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
      `<div style="font-size:28px;font-weight:700;color:var(--text-primary)">${withBlank(c.stem)}</div>` +
      (c.pronunciation
        ? `<div style="font-size:15px;color:var(--text-secondary);margin-top:6px">${escHtml(c.pronunciation)}</div>`
        : '');
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
      `<div style="font-size:28px;font-weight:700;color:var(--primary)">${escHtml(c.word || ex.lemma || '')}</div>` +
      (c.word_definition
        ? `<div style="font-size:14px;color:var(--text-secondary);margin-top:8px;font-style:italic">${escHtml(c.word_definition)}</div>`
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
    const prompt = `<div style="font-size:24px;font-weight:600;line-height:1.7">${withBlank(c.sentence_with_blank)}</div>`;
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
