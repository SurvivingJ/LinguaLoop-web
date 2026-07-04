/* Dual Translation — diff-centric result UI (TASK-608).
 *
 * One page, two phases:
 *   1. Reproduce (feed-up): show the L1 reference + the rubric the learner will
 *      be graded against + an optional, client-only pre-reveal self-rating.
 *   2. Result (feed-back / feed-forward): the diff is the centrepiece (aligned
 *      reference-vs-reproduction, token-level from the cascade's diff opcodes),
 *      per-dimension bands, and the eager per-error explanation with a
 *      "drill this" hook (disabled until TASK-613 cards exist).
 *
 * Contract shapes it consumes:
 *   GET /next  -> { submission_id, l1_text, age_tier, rubric_descriptors }
 *   POST /submit -> { scores{dim:1-4}, overall_band, diff[{op,correct,user}],
 *                     errors[{category,subtype,source,severity,learner_form,
 *                             corrected_form,explanation,confidence,is_mistake}],
 *                     grader_trace }
 */
(function () {
  'use strict';

  // Dimension order for the score panel. Naturalness is deliberately last —
  // it is low-stakes (ADR-018) and hidden outright at age tiers 1-2, matching
  // routes/dual_translation.py::_rubric_descriptors_for.
  const DIMENSIONS = ['accuracy', 'understandability', 'fidelity', 'range', 'naturalness'];
  const NATURALNESS_HIDDEN_TIERS = [1, 2];

  // TASK-617 seam. Default keeps the eager, direct+metalinguistic feedback the
  // rest of the feature was designed around; 'flag_only' hides the correction
  // behind a reveal. The A/B assignment/logging is TASK-617, not built here.
  let CORRECTION_STYLE = 'direct_metalinguistic';

  const state = {
    submissionId: null,
    ageTier: null,
    selfRating: null,
    submitting: false,
    naturalnessShown: false,
    lastContract: null,
  };

  const el = {};

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  // Like tr(), but returns `fallback` when the key is missing (LinguaI18n.t
  // echoes the key back on a miss). Used for the enum-derived labels so a
  // not-yet-translated key never renders as a raw "dual_translation.x" string.
  function label(key, fallback) {
    const v = tr(key);
    return v == null || v === key ? fallback : v;
  }

  function escapeHtml(s) {
    if (window.LinguaUtils && window.LinguaUtils.escapeHtml) {
      return window.LinguaUtils.escapeHtml(String(s == null ? '' : s));
    }
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Subtypes are an open-ended per-pair taxonomy axis (18+ values); rather than
  // ship 18×4 i18n rows we humanize the canonical slug ("subject_verb_agreement"
  // -> "Subject verb agreement"). Full localisation rides with TASK-616.
  function humanize(slug) {
    if (!slug) return '';
    return String(slug)
      .replace(/_/g, ' ')
      .replace(/^\w/, (c) => c.toUpperCase());
  }

  // ------------------------------------------------------------------ init
  async function init() {
    cacheEls();
    try {
      if (window.LinguaI18n && window.LinguaI18n.init) {
        await window.LinguaI18n.init();
      }
    } catch (e) {
      /* i18n is best-effort; fall back to embedded defaults */
    }

    const wrap = document.querySelector('.dt-wrap');
    if (wrap && wrap.dataset.correctionStyle) {
      CORRECTION_STYLE = wrap.dataset.correctionStyle;
    }

    bindSelfRate();
    el.submit.addEventListener('click', onSubmit);
    el.tryAnother.addEventListener('click', loadNext);
    el.naturalnessToggle.addEventListener('click', function () {
      state.naturalnessShown = true;
      renderDims(state.lastContract.scores || {});
      el.naturalnessToggleWrap.style.display = 'none';
    });

    await loadNext();
  }

  function cacheEls() {
    [
      'dtLoading',
      'dtError',
      'dtReproduce',
      'dtReference',
      'dtRubricList',
      'dtSelfRateCard',
      'dtSelfRate',
      'dtReproduction',
      'dtSubmit',
      'dtResult',
      'dtOverallBand',
      'dtSelfRateRecall',
      'dtDiff',
      'dtDims',
      'dtNaturalnessToggleWrap',
      'dtNaturalnessToggle',
      'dtErrors',
      'dtTryAnother',
    ].forEach(function (id) {
      // strip the 'dt' prefix + lowercase first char for a tidy key
      const key = id.charAt(2).toLowerCase() + id.slice(3);
      el[key] = document.getElementById(id);
    });
  }

  function showPhase(phase) {
    el.loading.style.display = phase === 'loading' ? 'block' : 'none';
    el.error.style.display = phase === 'error' ? 'block' : 'none';
    el.reproduce.style.display = phase === 'reproduce' ? 'block' : 'none';
    el.result.style.display = phase === 'result' ? 'block' : 'none';
  }

  // -------------------------------------------------------------- GET /next
  async function loadNext() {
    showPhase('loading');
    resetReproduceUI();
    let resp;
    try {
      resp = await window.authFetch('/api/dual-translation/next');
    } catch (e) {
      return showError(tr('dual_translation.error_load'));
    }
    if (resp.status === 404) {
      return showError(tr('dual_translation.error_none'));
    }
    if (!resp.ok) {
      return showError(tr('dual_translation.error_load') + ' (' + resp.status + ')');
    }
    const data = await resp.json();

    // TASK-617: the server assigns the correction-style A/B arm per user and
    // returns it here; it overrides the static `.dt-wrap` dataset default (which
    // stays as a safe fallback when the field is absent, e.g. an older backend).
    if (data.correction_style) {
      CORRECTION_STYLE = data.correction_style;
    }

    state.submissionId = data.submission_id;
    state.ageTier = data.age_tier;
    state.selfRating = null;
    state.naturalnessShown = false;

    el.reference.textContent = data.l1_text || '';
    renderRubric(data.rubric_descriptors || {});
    showPhase('reproduce');
    el.reproduction.focus();
  }

  function resetReproduceUI() {
    if (el.reproduction) el.reproduction.value = '';
    if (el.submit) {
      el.submit.disabled = false;
      el.submit.textContent = tr('dual_translation.submit');
    }
    if (el.selfRate) {
      el.selfRate.querySelectorAll('button').forEach((b) => b.classList.remove('selected'));
    }
  }

  // rubric_descriptors: { dim: { "1": "...", ..., "4": "..." } } — server has
  // already stripped naturalness at tiers 1-2. Show each dim with its top-band
  // ("4") descriptor as the thing to aim for; degrade quietly if absent.
  function renderRubric(descriptors) {
    const dims = DIMENSIONS.filter((d) => descriptors[d]);
    if (!dims.length) {
      el.rubricList.innerHTML =
        '<div class="dt-rubric-row">' +
        escapeHtml(tr('dual_translation.rubric_generic')) +
        '</div>';
      return;
    }
    el.rubricList.innerHTML = dims
      .map(function (dim) {
        const bands = descriptors[dim] || {};
        const target = bands['4'] || bands['3'] || Object.values(bands)[0] || '';
        return (
          '<div class="dt-rubric-row"><strong>' +
          escapeHtml(tr('dual_translation.dim.' + dim)) +
          '</strong>: ' +
          escapeHtml(target) +
          '</div>'
        );
      })
      .join('');
  }

  function bindSelfRate() {
    el.selfRate.addEventListener('click', function (e) {
      const btn = e.target.closest('button[data-rating]');
      if (!btn) return;
      state.selfRating = parseInt(btn.dataset.rating, 10);
      el.selfRate.querySelectorAll('button').forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');
      // Client-only this pass (no schema change); keyed by submission so a
      // reload before submit keeps the prediction.
      try {
        if (state.submissionId != null) {
          localStorage.setItem('dt_selfrating_' + state.submissionId, String(state.selfRating));
        }
      } catch (_) {
        /* private mode / quota — non-fatal */
      }
    });
  }

  // ------------------------------------------------------------ POST /submit
  async function onSubmit() {
    if (state.submitting) return; // double-submit latch
    const reproduction = (el.reproduction.value || '').trim();
    if (!reproduction) {
      window.showToast(tr('dual_translation.empty_reproduction'), 'info');
      el.reproduction.focus();
      return;
    }

    state.submitting = true;
    el.submit.disabled = true;
    el.submit.textContent = tr('dual_translation.submitting');

    let resp;
    try {
      resp = await window.authFetch('/api/dual-translation/' + state.submissionId + '/submit', {
        method: 'POST',
        body: JSON.stringify({
          reproduction: reproduction,
          idempotency_key:
            window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
        }),
      });
    } catch (e) {
      return failSubmit();
    }
    if (!resp || !resp.ok) {
      return failSubmit(resp && resp.status);
    }
    const contract = await resp.json();
    state.lastContract = contract;
    state.submitting = false;
    renderResult(contract);
  }

  function failSubmit(status) {
    state.submitting = false;
    el.submit.disabled = false;
    el.submit.textContent = tr('dual_translation.submit');
    window.showToast(
      tr('dual_translation.error_submit') + (status ? ' (' + status + ')' : ''),
      'error'
    );
  }

  // ----------------------------------------------------------- render result
  function renderResult(contract) {
    el.overallBand.textContent = contract.overall_band != null ? contract.overall_band : '–';

    if (state.selfRating != null) {
      el.selfRateRecall.textContent = tr('dual_translation.self_rating_recall', {
        rating: state.selfRating,
      });
      el.selfRateRecall.style.display = 'block';
    } else {
      el.selfRateRecall.style.display = 'none';
    }

    renderDiff(contract.diff || []);
    renderDims(contract.scores || {});
    renderErrors(contract.errors || []);

    showPhase('result');
    window.scrollTo(0, 0);
  }

  // The diff is the visual focus: one flex "cell" per opcode, reference (gold
  // L2) on top and the learner's deviation below so the tracks stay aligned
  // token-for-token even in CJK where there are no word spaces.
  function renderDiff(diff) {
    const html = diff
      .map(function (d) {
        const op = d.op;
        const ref = escapeHtml(d.correct);
        const usr = escapeHtml(d.user);
        if (op === 'equal') {
          return '<span class="dt-cell eq"><span class="dt-top">' + ref + '</span></span>';
        }
        if (op === 'replace') {
          return (
            '<span class="dt-cell rep"><span class="dt-top">' +
            ref +
            '</span><span class="dt-bot">' +
            usr +
            '</span></span>'
          );
        }
        if (op === 'delete') {
          // gold token the learner omitted
          return (
            '<span class="dt-cell del"><span class="dt-top">' +
            ref +
            '</span><span class="dt-bot">&#8709;</span></span>'
          );
        }
        if (op === 'insert') {
          // extra token the learner added
          return (
            '<span class="dt-cell ins"><span class="dt-top">&middot;</span>' +
            '<span class="dt-bot">' +
            usr +
            '</span></span>'
          );
        }
        return '';
      })
      .join('');
    el.diff.innerHTML =
      html ||
      '<span class="text-slate-500">' + escapeHtml(tr('dual_translation.diff_empty')) + '</span>';
  }

  function renderDims(scores) {
    const hideNaturalness = NATURALNESS_HIDDEN_TIERS.indexOf(state.ageTier) !== -1;
    el.dims.innerHTML = '';

    DIMENSIONS.forEach(function (dim) {
      if (dim === 'naturalness') {
        // Tiers 1-2: hidden outright. Tiers 3+: low-stakes/optional,
        // revealed only on the learner-override toggle.
        if (hideNaturalness) return;
        if (!state.naturalnessShown) return;
      }
      if (!(dim in scores)) return;
      const band = scores[dim];
      const card = document.createElement('div');
      card.className = 'dt-dim b' + band + (dim === 'naturalness' ? ' optional' : '');
      let html =
        '<div class="dt-dim-name">' +
        escapeHtml(tr('dual_translation.dim.' + dim)) +
        '</div>' +
        '<div class="dt-dim-band">' +
        escapeHtml(band) +
        '</div>';
      if (dim === 'naturalness') {
        html +=
          '<div class="dt-dim-tag">' +
          escapeHtml(tr('dual_translation.naturalness_optional')) +
          '</div>';
      }
      card.innerHTML = html;
      el.dims.appendChild(card);
    });

    // Toggle affordance only for tiers 3+ that haven't revealed it yet.
    const showToggle = !hideNaturalness && !state.naturalnessShown && 'naturalness' in scores;
    el.naturalnessToggleWrap.style.display = showToggle ? 'block' : 'none';
  }

  function renderErrors(errors) {
    if (!errors.length) {
      el.errors.innerHTML =
        '<div class="dt-hint" style="font-size:0.95rem;">' +
        escapeHtml(tr('dual_translation.no_errors')) +
        '</div>';
      return;
    }
    el.errors.innerHTML = '';
    errors.forEach(function (err, idx) {
      el.errors.appendChild(buildErrorCard(err, idx));
    });
  }

  function buildErrorCard(err, idx) {
    const card = document.createElement('div');
    card.className = 'dt-error' + (err.severity === 'global' ? ' sev-global' : '');

    const chips =
      '<div class="dt-chips">' +
      chip(label('dual_translation.category.' + err.category, humanize(err.category))) +
      chip(humanize(err.subtype)) +
      chip(label('dual_translation.severity.' + err.severity, humanize(err.severity))) +
      (err.source
        ? chip(label('dual_translation.source.' + err.source, humanize(err.source)))
        : '') +
      '</div>';

    const forms =
      '<div class="dt-error-forms">' +
      '<span class="dt-learner">' +
      escapeHtml(err.learner_form) +
      '</span>' +
      '<span class="dt-arrow">' +
      escapeHtml(tr('dual_translation.corrected_to')) +
      '</span>' +
      '<span class="dt-corrected">' +
      escapeHtml(err.corrected_form) +
      '</span>' +
      '</div>';
    const expl = '<div class="dt-error-expl">' + escapeHtml(err.explanation) + '</div>';

    const drill =
      '<button class="dt-drill-btn" disabled title="' +
      escapeHtml(tr('dual_translation.drill_soon')) +
      '" ' +
      'data-subtype="' +
      escapeHtml(err.subtype) +
      '">' +
      escapeHtml(tr('dual_translation.drill_this')) +
      '</button>';

    if (CORRECTION_STYLE === 'flag_only') {
      // Flag-only: name the slip + location, reveal the correction on demand.
      card.innerHTML =
        chips +
        '<button class="dt-reveal-btn" data-reveal="' +
        idx +
        '">' +
        escapeHtml(tr('dual_translation.reveal_correction')) +
        '</button>' +
        '<div data-revealable="' +
        idx +
        '" style="display:none; margin-top:10px;">' +
        forms +
        expl +
        drill +
        '</div>';
      const btn = card.querySelector('[data-reveal]');
      btn.addEventListener('click', function () {
        card.querySelector('[data-revealable]').style.display = 'block';
        btn.style.display = 'none';
      });
    } else {
      // Direct + metalinguistic (default): everything eager.
      card.innerHTML = chips + forms + expl + drill;
    }
    return card;
  }

  function chip(text) {
    return '<span class="dt-chip">' + escapeHtml(text) + '</span>';
  }

  function showError(message) {
    el.error.textContent = message;
    showPhase('error');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
