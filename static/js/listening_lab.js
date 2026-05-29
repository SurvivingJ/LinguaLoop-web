/**
 * Listening Lab — page controller.
 *
 * Speed-graded listening: same passage at 0.75 / 0.9 / 1.0 / 1.15. After each
 * tier, the user takes a 5-MCQ check; 4/5 unlocks the next speed. All grading
 * and question sampling is server-side — this controller only renders state
 * and posts user input.
 */
/* global LinguaI18n */
(function () {
  'use strict';

  const TIER_SPEEDS = [0.75, 0.9, 1.0, 1.15];
  const PASS_THRESHOLD = 4;

  // ---------- Page state ------------------------------------------------
  const slug = decodeURIComponent(
    (window.location.pathname.match(/\/listening-lab\/([^/?#]+)/) || [])[1] || ''
  );

  const state = {
    passage: null,
    session: null, // current session object
    currentTier: null, // smallint 0..3 while playing, 4 when done
    questions: [], // [{id, question_text, choices}]
    selected: {}, // {question_id: selected_answer}
    audioUrl: null,
    playCount: 0,
    completed: false,
  };

  // ---------- Helpers ---------------------------------------------------

  function escapeHtml(s) {
    return String(s ?? '').replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
    );
  }

  function uuid() {
    // RFC4122-ish. authFetch's environment usually has crypto.randomUUID.
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function $(sel, root = document) {
    return root.querySelector(sel);
  }
  function $$(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function renderTemplate(id, container) {
    const tpl = document.getElementById(id);
    if (!tpl) {
      console.error('Missing template:', id);
      return;
    }
    container.replaceChildren(tpl.content.cloneNode(true));
    if (window.LinguaI18n && typeof LinguaI18n.applyTranslations === 'function') {
      try {
        LinguaI18n.applyTranslations(container);
      } catch (_) {
        /* ignore */
      }
    }
  }

  // ---------- Tier stepper ---------------------------------------------

  function paintTierPills(currentTier, tiersPassed) {
    const pills = $$('#tierPills .tier-pill');
    const connectors = $$('#tierPills .tier-connector');
    const passedSet = new Set((tiersPassed || []).map((t) => parseInt(t, 10)));

    pills.forEach((pill, idx) => {
      pill.classList.remove('active', 'completed', 'locked');
      if (passedSet.has(idx)) {
        pill.classList.add('completed');
      } else if (idx === currentTier && currentTier <= 3) {
        pill.classList.add('active');
      } else {
        pill.classList.add('locked');
      }
    });

    connectors.forEach((c, idx) => {
      c.classList.remove('completed');
      // Connector between pill idx and idx+1 is "completed" once pill idx is passed.
      if (passedSet.has(idx)) c.classList.add('completed');
    });
  }

  // ---------- Boot ------------------------------------------------------

  async function boot() {
    if (!slug) {
      showFatal('Invalid URL.');
      return;
    }
    try {
      const resp = await authFetch(`/api/listening-lab/${encodeURIComponent(slug)}`);
      const data = await resp.json();

      if (data.status !== 'success' || !data.passage) {
        showFatal('Passage not found.');
        return;
      }

      state.passage = data.passage;
      $('#passageTitle').textContent = state.passage.title || 'Listening Passage';

      if (data.active_session) {
        // Resume the in-flight session via a redundant start (idempotent: the
        // RPC returns the existing row with current questions + audio URL).
        await resumeOrStart();
      } else {
        showStartCta();
      }
    } catch (err) {
      console.error('boot failed:', err);
      showFatal('Failed to load passage.');
    }
  }

  function showStartCta() {
    const card = $('#mainCard');
    renderTemplate('startCtaTemplate', card);
    $('#startBtn').addEventListener('click', resumeOrStart);
    paintTierPills(0, []);
  }

  async function resumeOrStart() {
    try {
      const resp = await authFetch(`/api/listening-lab/${encodeURIComponent(slug)}/start`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      const data = await resp.json();
      if (data.status !== 'success' || !data.success) {
        showFatal(data.error || 'Failed to start session.');
        return;
      }

      state.session = {
        id: data.session_id,
        tiers_passed: (data.tiers_passed || []).map((t) => parseInt(t, 10)),
      };
      state.currentTier = parseInt(data.tier, 10);
      state.audioUrl = data.audio_url;
      state.questions = data.questions || [];
      state.selected = {};
      state.playCount = 0;

      renderTier();
    } catch (err) {
      console.error('start failed:', err);
      showFatal('Failed to start session.');
    }
  }

  // ---------- Tier render -----------------------------------------------

  function renderTier() {
    const card = $('#mainCard');
    renderTemplate('tierPlayTemplate', card);

    paintTierPills(state.currentTier, state.session.tiers_passed);

    $('#tierNumber').textContent = state.currentTier + 1;
    $('#currentSpeed').textContent =
      (TIER_SPEEDS[state.currentTier] || 1).toFixed(2).replace(/\.?0+$/, '') + '×';

    // Audio
    const audio = $('#tierAudio');
    audio.src = state.audioUrl;
    audio.load();
    audio.addEventListener('play', onAudioPlay);

    // Questions
    renderQuestions();

    // Buttons
    $('#submitTierBtn').addEventListener('click', onSubmitTier);
    $('#abandonBtn').addEventListener('click', onAbandon);

    updateSubmitEnabled();
  }

  function onAudioPlay() {
    const audio = $('#tierAudio');
    // Count each fresh playback (not seek-then-resume within the same play).
    // The 'play' event fires on resume too; count only when at start.
    if (audio.currentTime < 0.5) {
      state.playCount += 1;
      const pc = $('#playCount');
      if (pc) pc.textContent = state.playCount === 1 ? '1 play' : `${state.playCount} plays`;
    }
  }

  function renderQuestions() {
    const container = $('#questionsContainer');
    container.innerHTML = state.questions
      .map((q, idx) => {
        const choicesRaw = q.choices;
        const choices = normalizeChoices(choicesRaw);
        const options = choices
          .map(
            (opt, optIdx) => `
                <div class="option-item" data-qid="${escapeHtml(q.id)}"
                     data-answer="${escapeHtml(opt)}" role="radio" aria-checked="false">
                    <div class="option-radio"></div>
                    <div class="option-text">${escapeHtml(opt)}</div>
                </div>
            `
          )
          .join('');
        return `
                <div class="question-block" data-qid="${escapeHtml(q.id)}">
                    <div class="question-text">${idx + 1}. ${escapeHtml(q.question_text)}</div>
                    <div class="option-list" role="radiogroup">${options}</div>
                </div>
            `;
      })
      .join('');

    // Wire selection handlers
    $$('.option-item', container).forEach((el) => {
      el.addEventListener('click', () => selectOption(el));
    });
  }

  function normalizeChoices(raw) {
    // Choices may be stored as a JSON array of strings, or as a {A,B,C,D} object.
    if (Array.isArray(raw)) return raw.map(String);
    if (raw && typeof raw === 'object') {
      // Stable key order: A,B,C,D,... else insertion order.
      const keys = Object.keys(raw);
      const ordered = keys.slice().sort();
      return ordered.map((k) => String(raw[k]));
    }
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw);
        return normalizeChoices(parsed);
      } catch (_) {
        return [String(raw)];
      }
    }
    return [];
  }

  function selectOption(el) {
    const qid = el.dataset.qid;
    const answer = el.dataset.answer;
    state.selected[qid] = answer;

    // Visual: clear other options in the same question, mark this selected
    const group = el.closest('.question-block');
    $$('.option-item', group).forEach((opt) => {
      opt.classList.remove('selected');
      opt.setAttribute('aria-checked', 'false');
    });
    el.classList.add('selected');
    el.setAttribute('aria-checked', 'true');

    updateSubmitEnabled();
  }

  function updateSubmitEnabled() {
    const allAnswered = state.questions.every((q) => state.selected[q.id]);
    $('#submitTierBtn').disabled = !allAnswered;
  }

  // ---------- Submit ----------------------------------------------------

  async function onSubmitTier() {
    const submitBtn = $('#submitTierBtn');
    submitBtn.disabled = true;
    const feedback = $('#feedback');
    feedback.className = 'll-feedback';
    feedback.style.display = 'none';

    const responses = state.questions.map((q) => ({
      question_id: q.id,
      selected_answer: state.selected[q.id] || '',
    }));

    try {
      const resp = await authFetch(
        `/api/listening-lab/session/${encodeURIComponent(state.session.id)}/tier/${state.currentTier}/submit`,
        {
          method: 'POST',
          body: JSON.stringify({
            responses,
            idempotency_key: uuid(),
          }),
        }
      );
      const data = await resp.json();

      if (data.status !== 'success' || !data.success) {
        feedback.classList.add('error');
        feedback.textContent = data.error || 'Submission failed.';
        feedback.style.display = 'block';
        submitBtn.disabled = false;
        return;
      }

      applySubmitResult(data);
    } catch (err) {
      console.error('submit failed:', err);
      feedback.classList.add('error');
      feedback.textContent = 'Network error. Try again.';
      feedback.style.display = 'block';
      submitBtn.disabled = false;
    }
  }

  function applySubmitResult(result) {
    // Mark per-question correctness on the just-submitted options
    const perQ = result.question_results || [];
    perQ.forEach((qr) => {
      const block = document.querySelector(
        `.question-block[data-qid="${CSS.escape(qr.question_id)}"]`
      );
      if (!block) return;
      const items = $$('.option-item', block);
      items.forEach((item) => {
        item.classList.add('disabled');
        if (item.dataset.answer === qr.correct_answer) {
          item.classList.add('correct');
        }
        if (item.classList.contains('selected') && !qr.is_correct) {
          item.classList.add('incorrect');
        }
      });
    });

    if (result.completed) {
      // Final tier passed — show completion modal with ELO result.
      state.completed = true;
      paintTierPills(4, [0, 1, 2, 3]);
      showCompletionModal(result);
      return;
    }

    if (result.passed) {
      // Advance to next tier.
      state.session.tiers_passed = (state.session.tiers_passed || []).concat([state.currentTier]);
      state.currentTier = result.next_tier;
      state.audioUrl = result.next_audio_url;
      state.questions = result.next_questions || [];
      state.selected = {};
      state.playCount = 0;

      const feedback = $('#feedback');
      feedback.className = 'll-feedback success';
      feedback.textContent = `${result.score}/5 — next speed unlocked: ${TIER_SPEEDS[state.currentTier].toFixed(2)}×`;
      feedback.style.display = 'block';

      // After a short pause, render the new tier UI.
      setTimeout(renderTier, 1400);
    } else {
      // Failed: same tier, fresh questions.
      const feedback = $('#feedback');
      feedback.className = 'll-feedback warn';
      feedback.textContent = `${result.score}/5 — ${PASS_THRESHOLD} needed to advance. Fresh questions coming up.`;
      feedback.style.display = 'block';

      state.questions = result.retry_questions || [];
      state.selected = {};
      // Don't reset playCount — user can keep replaying the same audio.

      setTimeout(() => {
        renderQuestions();
        $('#submitTierBtn').disabled = true;
        $('#feedback').style.display = 'none';
      }, 1800);
    }
  }

  // ---------- Completion modal -----------------------------------------

  function showCompletionModal(result) {
    const elo = result.elo_result || {};
    const score = elo.score;
    const total = elo.total_questions || 20;
    const eloChange = elo.user_elo_change;
    const eloAfter = elo.user_elo_after;

    $('#completionIcon').textContent = '🏆';
    $('#completionTitle').textContent = 'Listening Lab complete';
    $('#completionScore').textContent =
      typeof score === 'number' && total ? `Final score: ${score} / ${total}` : '';

    const deltaEl = $('#completionEloDelta');
    if (typeof eloChange === 'number') {
      const sign = eloChange >= 0 ? '+' : '';
      deltaEl.textContent = `${sign}${eloChange} ELO`;
      deltaEl.style.display = '';
      deltaEl.classList.toggle('negative', eloChange < 0);
    } else {
      deltaEl.style.display = 'none';
    }
    $('#completionMessage').textContent =
      typeof eloAfter === 'number' ? `New listening_lab rating: ${eloAfter}` : '';

    $('#completionContinueBtn').addEventListener('click', () => {
      window.location.href = '/listening-lab';
    });
    $('#completionBackBtn').addEventListener('click', () => {
      window.location.href = '/listening-lab';
    });

    const modalEl = document.getElementById('completionModal');
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: 'static',
      keyboard: false,
    });
    modal.show();
  }

  // ---------- Abandon ---------------------------------------------------

  async function onAbandon() {
    if (!state.session) return;
    const ok = window.confirm(
      'End this session? Your progress will be discarded and no ELO awarded.'
    );
    if (!ok) return;

    try {
      await authFetch(
        `/api/listening-lab/session/${encodeURIComponent(state.session.id)}/abandon`,
        { method: 'POST', body: JSON.stringify({}) }
      );
    } catch (err) {
      console.error('abandon failed:', err);
    }
    window.location.href = '/listening-lab';
  }

  // ---------- Fatal error -----------------------------------------------

  function showFatal(msg) {
    const card = $('#mainCard');
    card.innerHTML = `
            <div class="ll-section-body">
                <div class="ll-feedback error" style="display:block;">${escapeHtml(msg)}</div>
                <div class="ll-actions">
                    <a href="/listening-lab" class="btn-abandon">Back to list</a>
                </div>
            </div>
        `;
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
