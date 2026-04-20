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

    function escHtml(s) {
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
        return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    function i18n(key, v) {
        if (typeof LinguaI18n !== 'undefined') return LinguaI18n.t(key, v);
        const map = {
            'exercises.next': 'Next', 'exercises.check': 'Check',
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

    function mcq(badge, cefr, instr, prompt, opts, correct, expl, wordHTML) {
        const shuffled = shuffleArr(opts);
        let h = (wordHTML || '') +
            `<div class="exercise-type-badge"><i class="fas fa-pen-to-square"></i> ${badge}${cefr ? `<span class="exercise-cefr-badge">${cefr}</span>` : ''}</div>` +
            `<div class="exercise-instruction">${instr}</div>` +
            `<div class="exercise-prompt">${prompt}</div>` +
            `<div class="exercise-options" id="optionsList">`;
        shuffled.forEach((o, i) => {
            const v = typeof o === 'object' ? o.text : o;
            h += `<div class="exercise-option" data-value="${escHtml(v)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(v)}</span></div>`;
        });
        h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;

        document.getElementById('optionsList').addEventListener('click', e => {
            if (_isAnswered()) return;
            const opt = e.target.closest('.exercise-option');
            if (!opt) return;
            _setAnswered(true);
            const sel = opt.dataset.value;
            const ok = sel === correct;
            document.querySelectorAll('#optionsList .exercise-option').forEach(o => {
                o.classList.add('disabled');
                if (o.dataset.value === correct) o.classList.add('correct');
            });
            if (!ok) opt.classList.add('incorrect');
            _showFeedback(ok, expl);
            _submitAttempt(ok, { selected: sel });
        });
        bindNext();
    }

    // ── Type renderers ──

    function renderCloze(ex, c, w) {
        let p = escHtml(c.sentence_with_blank).replace('___', '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>');
        if (c.word_definition) p += `<div style="font-size:14px;color:var(--text-secondary);margin-top:10px;font-style:italic;">${escHtml(c.word_definition)}</div>`;
        mcq(fmtType('cloze_completion'), ex.cefr_level, i18n('exercises.instruction.fill_blank'), p, c.options, c.correct_answer, c.explanation, w);
    }

    function renderTlNl(ex, c, w) {
        mcq(fmtType('tl_nl_translation'), ex.cefr_level, i18n('exercises.instruction.choose_translation'), escHtml(c.tl_sentence), c.options, c.correct_nl, '', w);
    }

    function renderSemDiscrim(ex, c, w) {
        const cor = c.sentences.find(s => s.is_correct);
        mcq(fmtType('semantic_discrimination'), ex.cefr_level, i18n('exercises.instruction.which_sentence', { word: c.target_word || 'the word' }), '', c.sentences.map(s => s.text), cor ? cor.text : '', c.explanation, w);
    }

    function renderOddOneOut(ex, c, w) {
        const odd = c.items[c.odd_index];
        let h = (w || '') + `<div class="exercise-type-badge"><i class="fas fa-question-circle"></i> ${fmtType('odd_one_out')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">${i18n('exercises.instruction.odd_one_out')}</div>` +
            (c.shared_property ? `<div class="exercise-prompt" style="font-size:15px;color:var(--text-secondary)">${i18n('exercises.hint', { hint: escHtml(c.shared_property) })}</div>` : '') +
            `<div class="exercise-options" id="optionsList">`;
        shuffleArr(c.items).forEach((it, i) => { h += `<div class="exercise-option" data-value="${escHtml(it)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(it)}</span></div>`; });
        h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;
        document.getElementById('optionsList').addEventListener('click', e => {
            if (_isAnswered()) return; const o = e.target.closest('.exercise-option'); if (!o) return; _setAnswered(true);
            const sel = o.dataset.value, ok = sel === odd;
            document.querySelectorAll('#optionsList .exercise-option').forEach(x => { x.classList.add('disabled'); if (x.dataset.value === odd) x.classList.add('correct'); });
            if (!ok) o.classList.add('incorrect'); _showFeedback(ok, c.explanation); _submitAttempt(ok, { selected: sel });
        });
        bindNext();
    }

    function renderNlTl(ex, c, w) {
        let h = (w || '') + `<div class="exercise-type-badge"><i class="fas fa-language"></i> ${fmtType('nl_tl_translation')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">${i18n('exercises.instruction.translate_to_tl')}</div>` +
            `<div class="exercise-prompt">${escHtml(c.nl_sentence)}</div>` +
            `<textarea class="exercise-input-area" id="translationInput" placeholder="${i18n('exercises.type_placeholder')}"></textarea>` +
            `<button class="btn btn-primary exercise-check-btn" id="checkBtn"><i class="fas fa-check me-2"></i>${i18n('exercises.check')}</button>` +
            `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;
        document.getElementById('checkBtn').addEventListener('click', function () {
            if (_isAnswered()) return; _setAnswered(true);
            const inp = document.getElementById('translationInput').value.trim();
            const pri = (c.primary_tl || '').trim();
            const vars = (c.acceptable_variants || []).map(v => v.trim().toLowerCase());
            const ok = inp.toLowerCase() === pri.toLowerCase() || vars.includes(inp.toLowerCase());
            let expl = ''; if (c.grading_notes) expl += c.grading_notes; if (!ok) expl += '\nExpected: ' + pri;
            if (c.acceptable_variants && c.acceptable_variants.length) expl += '\nAlso accepted: ' + c.acceptable_variants.join(', ');
            this.style.display = 'none'; document.getElementById('translationInput').readOnly = true;
            _showFeedback(ok, expl); _submitAttempt(ok, { typed: inp });
        });
        bindNext();
    }

    function renderColloGap(ex, c, w) {
        let p = escHtml(c.sentence).replace('___', '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>');
        mcq(fmtType('collocation_gap_fill'), ex.cefr_level, i18n('exercises.instruction.collocation_gap_fill'), p, c.options, c.correct, '', w);
    }

    function renderColloRepair(ex, c, w) {
        let words = c.words;
        if (!words) {
            const tokens = c.sentence_with_error.split(/\s+/);
            words = tokens.map(t => {
                const clean = t.replace(/[.,;:!?"'\-()[\]]/g, '').toLowerCase();
                return { text: t, is_error: clean === (c.error_word || '').toLowerCase() };
            });
        }

        let h = (w || '') +
            `<div class="exercise-type-badge"><i class="fas fa-wrench"></i> ${fmtType('collocation_repair')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">${i18n('exercises.instruction.collocation_repair')}</div>` +
            `<div class="sip-parts" id="crWords">`;
        words.forEach((wd, i) => {
            h += `<span class="sip-part" data-idx="${i}">${escHtml(wd.text)}</span>`;
        });
        h += `</div>` +
            `<div id="crPhase2" style="display:none;margin-top:16px;">` +
            `<div class="exercise-instruction" style="font-size:14px;">${i18n('exercises.instruction.collocation_repair_phase2')}</div>` +
            `<input type="text" class="exercise-input-area" id="crInput" style="width:100%;padding:10px;font-size:16px;" autocomplete="off">` +
            `<button class="btn btn-primary exercise-check-btn" id="crCheckBtn" style="margin-top:8px;"><i class="fas fa-check me-2"></i>${i18n('exercises.check')}</button>` +
            `</div>` +
            `<div id="crCorrection" class="sip-correction" style="display:none;"></div>` +
            `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;

        document.getElementById('crWords').addEventListener('click', e => {
            if (_isAnswered()) return;
            const part = e.target.closest('.sip-part');
            if (!part) return;
            const idx = parseInt(part.dataset.idx);
            const selected = words[idx];
            const ok = !!selected.is_error;

            document.querySelectorAll('#crWords .sip-part').forEach(el => {
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
                    _submitAttempt(phase2ok, { selected_word: selected.text, typed_correction: typed, phase1_correct: true, phase2_correct: phase2ok });
                };
                document.getElementById('crCheckBtn').addEventListener('click', checkTyped);
                inp.addEventListener('keydown', e => { if (e.key === 'Enter') checkTyped(); });
            } else {
                _setAnswered(true);
                const corr = document.getElementById('crCorrection');
                corr.innerHTML = '<i class="fas fa-check me-1"></i>' + escHtml(c.error_word) + ' \u2192 ' + escHtml(c.correct_word);
                corr.style.display = '';
                _showFeedback(false, c.explanation);
                _submitAttempt(false, { selected_word: selected.text, phase1_correct: false });
            }
        });
        bindNext();
    }

    function renderOddCollo(ex, c, w) {
        const odd = c.collocations[c.odd_index];
        let h = (w || '') + `<div class="exercise-type-badge"><i class="fas fa-question-circle"></i> ${fmtType('odd_collocation_out')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">${i18n('exercises.instruction.odd_collocation_out', { word: escHtml(c.head_word) })}</div>` +
            `<div class="exercise-options" id="optionsList">`;
        shuffleArr(c.collocations).forEach((it, i) => { h += `<div class="exercise-option" data-value="${escHtml(it)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(it)}</span></div>`; });
        h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;
        document.getElementById('optionsList').addEventListener('click', e => {
            if (_isAnswered()) return; const o = e.target.closest('.exercise-option'); if (!o) return; _setAnswered(true);
            const sel = o.dataset.value, ok = sel === odd;
            document.querySelectorAll('#optionsList .exercise-option').forEach(x => { x.classList.add('disabled'); if (x.dataset.value === odd) x.classList.add('correct'); });
            if (!ok) o.classList.add('incorrect'); _showFeedback(ok, c.explanation); _submitAttempt(ok, { selected: sel });
        });
        bindNext();
    }

    function renderSpotPart(ex, c, w) {
        const errorPart = c.parts.find(p => p.is_error);
        let h = (w || '') +
            `<div class="exercise-type-badge"><i class="fas fa-search"></i> ${fmtType('spot_incorrect_part')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">Tap the part of the sentence that contains an error:</div>` +
            `<div class="sip-parts" id="sipParts">`;
        c.parts.forEach((p, i) => {
            h += `<span class="sip-part" data-idx="${i}">${escHtml(p.text)}</span>`;
        });
        h += `</div><div id="sipCorrection" class="sip-correction" style="display:none;"></div>` +
            `<div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;

        document.getElementById('sipParts').addEventListener('click', e => {
            if (_isAnswered()) return;
            const part = e.target.closest('.sip-part');
            if (!part) return;
            _setAnswered(true);
            const idx = parseInt(part.dataset.idx);
            const selected = c.parts[idx];
            const ok = !!selected.is_error;

            document.querySelectorAll('.sip-part').forEach(el => {
                el.classList.add('disabled');
                const pi = parseInt(el.dataset.idx);
                if (c.parts[pi].is_error) el.classList.add('correct');
            });
            if (!ok) part.classList.add('incorrect');

            if (errorPart && errorPart.correct_form) {
                const corr = document.getElementById('sipCorrection');
                corr.innerHTML = '<i class="fas fa-check me-1"></i>Correct form: ' + escHtml(errorPart.correct_form);
                corr.style.display = '';
            }

            const expl = errorPart ? errorPart.explanation : '';
            _showFeedback(ok, expl);
            _submitAttempt(ok, { selected_index: idx, selected_text: selected.text });
        });
        bindNext();
    }

    function renderSpotSentence(ex, c, w) {
        const incorrect = c.sentences.find(s => !s.is_correct);
        const opts = c.sentences.map(s => s.text);
        let h = (w || '') +
            `<div class="exercise-type-badge"><i class="fas fa-search"></i> ${fmtType('spot_incorrect_sentence')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-instruction">Which sentence contains an error?</div>` +
            `<div class="exercise-options" id="optionsList">`;
        opts.forEach((t, i) => {
            h += `<div class="exercise-option" data-value="${escHtml(t)}"><span class="option-letter">${String.fromCharCode(65 + i)}</span><span class="option-text">${escHtml(t)}</span></div>`;
        });
        h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
        _card.innerHTML = h;

        const correctVal = incorrect ? incorrect.text : '';
        document.getElementById('optionsList').addEventListener('click', e => {
            if (_isAnswered()) return;
            const opt = e.target.closest('.exercise-option');
            if (!opt) return;
            _setAnswered(true);
            const sel = opt.dataset.value;
            const ok = sel === correctVal;

            document.querySelectorAll('#optionsList .exercise-option').forEach(o => {
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
            let h = (w || '') +
                `<div class="exercise-type-badge"><i class="fas fa-shuffle"></i> ${fmtType('jumbled_sentence')}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
                `<div class="exercise-instruction">Arrange the words in the correct order:</div>` +
                `<div class="js-answer" id="jsAnswer">`;
            placed.forEach((ci, i) => {
                h += `<span class="js-chunk" draggable="true" data-placed="${i}" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
            });
            if (placed.length === 0) h += `<span style="color:var(--text-secondary);font-size:14px;padding:8px;">Tap or drag words below to build the sentence</span>`;
            h += `</div><div class="js-bank" id="jsBank">`;
            const bankIndices = initialBankOrder.filter(i => !placed.includes(i));
            bankIndices.forEach(ci => {
                h += `<span class="js-chunk" draggable="true" data-chunk="${ci}">${escHtml(chunks[ci])}</span>`;
            });
            h += `</div><div class="exercise-feedback" id="exerciseFeedback"></div>${nextBtnHTML()}`;
            _card.innerHTML = h;

            const answerDiv = document.getElementById('jsAnswer');
            const bankDiv = document.getElementById('jsBank');

            bankDiv.addEventListener('click', e => {
                if (_isAnswered()) return;
                const ch = e.target.closest('.js-chunk');
                if (!ch) return;
                placed.push(parseInt(ch.dataset.chunk));
                if (placed.length === chunks.length) checkJumbled();
                else render();
            });
            answerDiv.addEventListener('click', e => {
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

            _card.querySelectorAll('.js-chunk').forEach(el => {
                el.addEventListener('dragstart', e => {
                    if (_isAnswered()) { e.preventDefault(); return; }
                    dragChunkIdx = parseInt(el.dataset.chunk);
                    el.classList.add('dragging');
                    e.dataTransfer.effectAllowed = 'move';
                });
                el.addEventListener('dragend', () => { el.classList.remove('dragging'); removeIndicator(); });
            });

            [answerDiv, bankDiv].forEach(zone => {
                zone.addEventListener('dragover', e => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                    zone.classList.add('drag-over');
                    showIndicator(zone, e.clientX);
                });
                zone.addEventListener('dragleave', e => {
                    if (!zone.contains(e.relatedTarget)) {
                        zone.classList.remove('drag-over');
                        removeIndicator();
                    }
                });
                zone.addEventListener('drop', e => {
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
            document.querySelectorAll('.js-chunk').forEach(el => { el.classList.add('disabled'); el.removeAttribute('draggable'); });
            let expl = '';
            if (!ok) expl = 'Correct order: ' + correctOrder.map(i => chunks[i]).join(' ');
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
        let h = (w || '') + `<div class="exercise-type-badge"><i class="fas fa-layer-group"></i> ${fmtType(ex.exercise_type)}</div>` +
            `<div class="exercise-prompt">${escHtml(front)}</div>` +
            (pron ? `<div style="text-align:center;color:var(--text-secondary);font-size:16px;margin-bottom:16px;">${escHtml(pron)}</div>` : '') +
            `<div id="fcBack" style="display:none;text-align:center;margin-bottom:20px;">` +
            `<div style="font-size:18px;color:var(--text-primary);font-weight:500;margin-bottom:8px;">${escHtml(back)}</div>` +
            (example ? `<div style="font-size:14px;color:var(--text-secondary);font-style:italic;">${escHtml(example)}</div>` : '') +
            `</div><button class="btn btn-outline-primary w-100 mb-2" id="revealBtn"><i class="fas fa-eye me-2"></i>Reveal</button>` +
            `<div id="fcRate" style="display:none;"><p class="text-center text-muted mb-2">How well did you know this?</p>` +
            `<div class="d-flex gap-2"><button class="btn btn-danger flex-fill fc-rate" data-ok="0">Didn't know</button><button class="btn btn-success flex-fill fc-rate" data-ok="1">Knew it</button></div></div>` +
            `${nextBtnHTML()}`;
        _card.innerHTML = h;
        document.getElementById('revealBtn').addEventListener('click', function () {
            document.getElementById('fcBack').style.display = 'block'; document.getElementById('fcRate').style.display = 'block'; this.style.display = 'none';
        });
        document.querySelectorAll('.fc-rate').forEach(b => b.addEventListener('click', function () {
            if (_isAnswered()) return; _setAnswered(true); const ok = this.dataset.ok === '1';
            document.getElementById('fcRate').style.display = 'none'; _showFeedback(ok, ''); _submitAttempt(ok, { self_rated: true });
        }));
        bindNext();
    }

    function renderGeneric(ex, c, w) {
        _card.innerHTML = (w || '') + `<div class="exercise-type-badge"><i class="fas fa-question"></i> ${fmtType(ex.exercise_type)}${ex.cefr_level ? `<span class="exercise-cefr-badge">${ex.cefr_level}</span>` : ''}</div>` +
            `<div class="exercise-prompt" style="font-size:14px;text-align:left;white-space:pre-wrap;">${escHtml(JSON.stringify(c, null, 2))}</div>` +
            `<button class="btn btn-primary exercise-next-btn show" id="nextBtn">${i18n('exercises.next')} <i class="fas fa-arrow-right ms-1"></i></button>`;
        bindNext();
    }

    // ── New ladder renderers ──

    function renderPhonetic(ex, c, w) {
        const prompt = `<div class="phonetic-display">` +
            (c.ipa ? `<div class="ipa">${escHtml(c.ipa)}</div>` : '') +
            (c.pronunciation ? `<div class="pron">${escHtml(c.pronunciation)}</div>` : '') +
            (c.syllable_count ? `<div style="font-size:13px;color:var(--text-muted);margin-top:4px">${c.syllable_count} syllables</div>` : '') +
            `</div>`;
        mcq('Phonetic Recognition', null, 'Which word matches this pronunciation?', prompt, c.options || [], c.correct_answer || '', c.explanation || '', w);
    }

    function renderDefinitionMatch(ex, c, w) {
        const prompt = `<div style="text-align:center;font-size:28px;font-weight:700;color:var(--primary);margin-bottom:8px">${escHtml(c.word || ex.lemma)}</div>` +
            (c.pronunciation ? `<div style="text-align:center;color:var(--text-secondary);margin-bottom:16px">${escHtml(c.pronunciation)}</div>` : '');
        mcq('Definition Match', null, 'Choose the correct definition:', prompt, c.options || [], c.correct_definition || '', '', w);
    }

    function renderMorphologySlot(ex, c, w) {
        let prompt = escHtml(c.sentence_with_blank || '').replace('___', '<span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>');
        if (c.base_form || c.form_label) {
            prompt += `<div style="font-size:14px;color:var(--text-secondary);margin-top:10px">Base form: <strong>${escHtml(c.base_form)}</strong>`;
            if (c.form_label) prompt += ` &mdash; fill in the <em>${escHtml(c.form_label)}</em>`;
            prompt += '</div>';
        }
        mcq('Morphology Slot', null, 'Choose the correct form:', prompt, c.options || [], c.correct_answer || '', c.explanation || '', w);
    }

    // ── Dispatcher ──

    function dispatch(type, ex, c, w) {
        const map = {
            'cloze_completion': renderCloze,
            'tl_nl_translation': renderTlNl,
            'semantic_discrimination': renderSemDiscrim,
            'odd_one_out': renderOddOneOut,
            'nl_tl_translation': renderNlTl,
            'collocation_gap_fill': renderColloGap,
            'collocation_repair': renderColloRepair,
            'odd_collocation_out': renderOddCollo,
            'text_flashcard': renderFlashcard,
            'listening_flashcard': renderFlashcard,
            'spot_incorrect_part': renderSpotPart,
            'spot_incorrect_sentence': renderSpotSentence,
            'jumbled_sentence': renderJumbled,
            'phonetic_recognition': renderPhonetic,
            'definition_match': renderDefinitionMatch,
            'morphology_slot': renderMorphologySlot,
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
