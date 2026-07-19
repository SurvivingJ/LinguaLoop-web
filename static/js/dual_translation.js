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
 *                             corrected_form,explanation,confidence,is_mistake,
 *                             explanation_parts{rule,application|null}}],
 *                     highlights[{span_reproduction:[a,b],reason}],
 *                     provisional, grader_trace }
 *
 * TASK-631 (Result UI v2) surfaces the v2 signal the contract now carries:
 * positive-evidence highlights on the diff, client-derived per-dimension "because"
 * lines, three-level severity chips, the provisional banner, a feed-forward "next
 * focus" line, and Rule/Application as distinct explanation layers. `highlights`
 * and `explanation_parts` are absent on v1/cached grades and degrade gracefully.
 */
(function () {
  'use strict';

  // Dimension order for the score panel. Naturalness is deliberately last —
  // it is low-stakes (ADR-018) and hidden outright at age tiers 1-2, matching
  // routes/dual_translation.py::_rubric_descriptors_for.
  const DIMENSIONS = ['accuracy', 'understandability', 'fidelity', 'range', 'naturalness'];
  const NATURALNESS_HIDDEN_TIERS = [1, 2];

  // TASK-639/TASK-631: single source of truth for how a severity presents. The MQM
  // triad (TASK-625) now styles all three levels distinctly — `chipClass` on the
  // severity chip, `cardClass` on the error card's left border (minor was previously
  // unstyled; the three-level chips are a TASK-631 acceptance criterion).
  const SEVERITY_META = {
    minor: {
      chipClass: 'sev-minor',
      cardClass: 'sev-card-minor',
      i18nKey: 'dual_translation.severity.minor',
    },
    major: {
      chipClass: 'sev-major',
      cardClass: 'sev-card-major',
      i18nKey: 'dual_translation.severity.major',
    },
    critical: {
      chipClass: 'sev-critical',
      cardClass: 'sev-card-critical',
      i18nKey: 'dual_translation.severity.critical',
    },
  };

  // Ascending impact — used to pick the "worst" severity that drives a because-line.
  const SEVERITY_ORDER = ['minor', 'major', 'critical'];

  // Pre-triad vocabulary. dt_severity_triad.sql backfilled the live rows, but an
  // un-migrated environment (or a _cached_grade row served verbatim) can still
  // carry these, and their i18n keys are gone from the locale files.
  const LEGACY_SEVERITY = { global: 'major', local: 'minor' };

  function canonicalSeverity(severity) {
    return LEGACY_SEVERITY[severity] || severity;
  }

  function severityMeta(severity) {
    const canonical = canonicalSeverity(severity);
    return (
      SEVERITY_META[canonical] || {
        chipClass: '',
        cardClass: '',
        i18nKey: 'dual_translation.severity.' + canonical,
      }
    );
  }

  // TASK-631: client-side proxy mapping the model's per-error `category` axis
  // (grammatical/lexical/pragmatic_expressional) onto the scored *dimension* a
  // because-line describes. The authoritative subtype->dimension map lives in the
  // taxonomy `subtype_meta`, which is NOT in the /submit contract (the AC forbids
  // new API surface), so a because-line attributes errors by this correlation —
  // approximate, but the error-profile trend stays the headline (anti-gamification).
  // accuracy <- grammatical; fidelity <- lexical. understandability draws on ALL
  // errors (severity axis); range/naturalness are model-judged, not error-derived.
  const CATEGORY_DIMENSION = {
    grammatical: 'accuracy',
    lexical: 'fidelity',
    pragmatic_expressional: 'naturalness',
  };

  // Dims scored by a judgment of the whole reproduction rather than by discrete
  // error instances (mirrors scoring.JUDGE_DIMENSIONS) — their because-line is the
  // "judged from your whole translation" phrase, not an error tally.
  const JUDGED_DIMS = ['range', 'naturalness'];

  const BECAUSE_KEY = {
    minor: 'dual_translation.because_minor',
    major: 'dual_translation.because_major',
    critical: 'dual_translation.because_critical',
  };

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
    // TASK-631: the reproduction the learner just submitted, kept so highlight
    // spans (char offsets into this string) can slice out their evidence text.
    reproduction: '',
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
      'dtProvisionalNotice',
      'dtOverallBand',
      'dtSelfRateRecall',
      'dtDiff',
      'dtHighlights',
      'dtDims',
      'dtNaturalnessToggleWrap',
      'dtNaturalnessToggle',
      'dtNextFocus',
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
    state.reproduction = reproduction;
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
    // TASK-628: a provisional grade means a grading pass failed (v2). Show the
    // "grading incomplete — retry" notice; when both passes failed the contract
    // also has no scores/overall_band, so the '–' fallback below still holds.
    if (el.provisionalNotice) {
      el.provisionalNotice.style.display = contract.provisional ? 'block' : 'none';
    }

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
    renderHighlights(contract.highlights || [], state.reproduction || '');
    renderDims(contract.scores || {});
    renderNextFocus(contract.errors || []);
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

  // TASK-631: positive-evidence highlights from the v2 detector, shown under the
  // diff. Each is {span_reproduction:[a,b], reason} where the span indexes the
  // learner's reproduction (the same string submitted, kept in state.reproduction).
  // Absent/empty -> hide the strip entirely (graceful on v1/cached grades).
  function renderHighlights(highlights, reproduction) {
    if (!el.highlights) return;
    const cards = (highlights || [])
      .map(function (h) {
        if (!h || !Array.isArray(h.span_reproduction)) return '';
        const text = String(reproduction).slice(h.span_reproduction[0], h.span_reproduction[1]);
        if (!text) return '';
        const reasonLabel = label(
          'dual_translation.highlight_reason.' + h.reason,
          humanize(h.reason)
        );
        return (
          '<div class="dt-highlight">' +
          '<span class="dt-hl-text">' +
          escapeHtml(text) +
          '</span>' +
          '<span class="dt-hl-reason">' +
          escapeHtml(reasonLabel) +
          '</span>' +
          '</div>'
        );
      })
      .filter(Boolean)
      .join('');
    if (!cards) {
      el.highlights.innerHTML = '';
      el.highlights.style.display = 'none';
      return;
    }
    el.highlights.innerHTML =
      '<div class="dt-highlights-label">' +
      escapeHtml(tr('dual_translation.highlights_heading')) +
      '</div>' +
      cards;
    el.highlights.style.display = 'flex';
  }

  // TASK-631: feed-forward "next focus" — the most frequent subtype among this
  // submission's real (non-is_mistake) errors. It will link into remediation once
  // Feature 2 (drill cards) is user-facing; for now it names the focus and notes
  // that targeted practice is coming. Hidden when there are no errors to focus on.
  function renderNextFocus(errors) {
    if (!el.nextFocus) return;
    const counts = {};
    (errors || []).forEach(function (e) {
      if (!e || e.is_mistake || !e.subtype) return;
      counts[e.subtype] = (counts[e.subtype] || 0) + 1;
    });
    let top = null;
    let topN = 0;
    Object.keys(counts).forEach(function (s) {
      if (counts[s] > topN) {
        topN = counts[s];
        top = s;
      }
    });
    if (!top) {
      el.nextFocus.innerHTML = '';
      el.nextFocus.style.display = 'none';
      return;
    }
    el.nextFocus.innerHTML =
      '<div class="dt-nf-title">' +
      escapeHtml(tr('dual_translation.next_focus', { subtype: humanize(top) })) +
      '</div>' +
      '<div class="dt-nf-hint">' +
      escapeHtml(tr('dual_translation.next_focus_hint')) +
      '</div>';
    el.nextFocus.style.display = 'block';
  }

  // TASK-631: a per-dimension "because" line derived entirely client-side from the
  // errors + bands already in the contract (no new API surface). Judged dims get a
  // fixed "judged from your whole translation" phrase; error-driven dims get a terse
  // tally of the worst-severity errors attributed to them, or a clean phrase when none.
  function becauseLineFor(dim, errors) {
    if (JUDGED_DIMS.indexOf(dim) !== -1) {
      return tr('dual_translation.because_judged');
    }
    const relevant = errorsForDimension(dim, errors);
    if (!relevant.length) {
      return tr('dual_translation.because_clean');
    }
    let worstRank = 0;
    relevant.forEach(function (e) {
      const r = SEVERITY_ORDER.indexOf(canonicalSeverity(e.severity));
      if (r > worstRank) worstRank = r;
    });
    const worst = SEVERITY_ORDER[worstRank];
    const count = relevant.filter(function (e) {
      return canonicalSeverity(e.severity) === worst;
    }).length;
    return tr(BECAUSE_KEY[worst], { count: count });
  }

  // Errors a dimension's because-line should tally. is_mistake errors are acceptable
  // variations that never drove a band down, so they're excluded. understandability
  // draws on every real error (severity axis); accuracy/fidelity on the
  // CATEGORY_DIMENSION-attributed subset.
  function errorsForDimension(dim, errors) {
    return (errors || []).filter(function (e) {
      if (!e || e.is_mistake) return false;
      if (dim === 'understandability') return true;
      return CATEGORY_DIMENSION[e.category] === dim;
    });
  }

  function renderDims(scores) {
    const hideNaturalness = NATURALNESS_HIDDEN_TIERS.indexOf(state.ageTier) !== -1;
    const errors = (state.lastContract && state.lastContract.errors) || [];
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
      // TASK-631: computed "because" line — why this dim landed on this band.
      const because = becauseLineFor(dim, errors);
      if (because) {
        html += '<div class="dt-dim-because">' + escapeHtml(because) + '</div>';
      }
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
    const sev = severityMeta(err.severity);
    card.className = 'dt-error' + (sev.cardClass ? ' ' + sev.cardClass : '');

    const chips =
      '<div class="dt-chips">' +
      chip(label('dual_translation.category.' + err.category, humanize(err.category))) +
      chip(humanize(err.subtype)) +
      chip(label(sev.i18nKey, humanize(err.severity)), sev.chipClass) +
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
    const expl = buildExplanation(err);

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

  function chip(text, extraClass) {
    return (
      '<span class="dt-chip' +
      (extraClass ? ' ' + extraClass : '') +
      '">' +
      escapeHtml(text) +
      '</span>'
    );
  }

  // TASK-631: render the explanation as distinct Rule (general) and Application
  // (this-sentence) layers when the v2 contract carries explanation_parts (TASK-630),
  // falling back to the flat explanation string for v1/cached grades that lack the
  // breakdown. All model-derived text is HTML-escaped (AC).
  function buildExplanation(err) {
    const parts = err.explanation_parts;
    if (parts && typeof parts === 'object') {
      let inner = '';
      if (parts.rule) {
        inner += '<div class="dt-expl-rule">' + escapeHtml(parts.rule) + '</div>';
      }
      if (parts.application) {
        inner += '<div class="dt-expl-application">' + escapeHtml(parts.application) + '</div>';
      }
      if (inner) return '<div class="dt-error-expl">' + inner + '</div>';
    }
    return '<div class="dt-error-expl">' + escapeHtml(err.explanation || '') + '</div>';
  }

  function showError(message) {
    el.error.textContent = message;
    showPhase('error');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
