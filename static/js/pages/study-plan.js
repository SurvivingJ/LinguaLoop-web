(function () {
  'use strict';

  const FLAGS = { cn: '🇨🇳', en: '🇺🇸', jp: '🇯🇵' };
  const flagFor = (code) => FLAGS[code?.toLowerCase()] || '🌐';

  // i18n helpers — fall through to the data-i18n default text if the i18n
  // bundle isn't loaded yet (e.g., during early init or in tests).
  const T = (key, params) => {
    if (window.LinguaI18n && typeof window.LinguaI18n.t === 'function') {
      return window.LinguaI18n.t(key, params);
    }
    return key; // dev fallback — visible enough to spot a missing key
  };

  const SPS = window.StudyPlanSettings;

  const state = {
    languages: [], // [{id, code, name}] for languages the user has plans for OR has tested in
    plansByLang: {}, // lang_id → { plan, current_week }
    templatesByLang: {}, // lang_id → [templates]
    selectedLangId: null,
    studyPlanEnabled: false,
  };

  // The plan and templates need a language id, which only the ELO response
  // gives. So that they need not wait for it, they are requested alongside it
  // for the language this page opened on last time (else the study language)
  // and used if the guess turns out right.
  const FIRST_LANG_KEY = 'linguadojo-study-plan-lang';
  const prefetched = {}; // lang_id → Promise<[planRes, tmplRes]>

  function fetchPlanAndTemplates(langId) {
    return Promise.all([
      window.authFetch(`/api/study-plan?language_id=${langId}`),
      window.authFetch(`/api/study-plan/templates?language_id=${langId}`),
    ]);
  }

  function prefetchLikelyLanguage() {
    let hint = NaN;
    try {
      hint = parseInt(
        localStorage.getItem(FIRST_LANG_KEY) || localStorage.getItem('selectedLanguageId'),
        10
      );
    } catch (_e) {
      /* storage blocked */
    }
    if (!hint) return;
    prefetched[hint] = fetchPlanAndTemplates(hint);
    prefetched[hint].catch(() => {});
  }

  // Responses can be read once, so a prefetch is consumed by its first use.
  function takePlanAndTemplates(langId) {
    const pending = prefetched[langId];
    delete prefetched[langId];
    return pending || fetchPlanAndTemplates(langId);
  }

  document.addEventListener('DOMContentLoaded', init);

  async function init() {
    try {
      prefetchLikelyLanguage();
      await loadActiveLanguages();
      if (state.languages.length === 0) {
        showError(T('study_plan.error.no_languages'));
        return;
      }
      const firstId = state.languages[0].id;
      Object.keys(prefetched).forEach((id) => {
        if (String(id) !== String(firstId)) delete prefetched[id];
      });
      try {
        localStorage.setItem(FIRST_LANG_KEY, String(firstId));
      } catch (_e) {
        /* storage blocked */
      }
      renderLanguageCards();
      // Auto-select the first language
      await selectLanguage(state.languages[0].id);
    } catch (err) {
      console.error(err);
      showError(err.message || 'Failed to load.');
    }
  }

  async function loadActiveLanguages() {
    // Pull active languages from the cached profile-style endpoint
    const res = await window.authFetch('/api/users/elo');
    if (!res.ok) throw new Error('Failed to fetch languages');
    const data = await res.json();
    const ratings = data.ratings || {};
    state.languages = Object.entries(ratings).map(([code, info]) => ({
      id: info.language_id,
      code,
      name: info.native_name || info.language_name || code,
    }));
    // Fallback: if the user has no test history at all, surface the three canonical languages.
    if (state.languages.length === 0) {
      state.languages = [
        { id: 1, code: 'zh', name: 'Chinese' },
        { id: 2, code: 'en', name: 'English' },
        { id: 3, code: 'ja', name: 'Japanese' },
      ];
    }
  }

  function renderLanguageCards() {
    const container = document.getElementById('languageList');
    container.innerHTML = state.languages
      .map(
        (lang) => `
            <div class="col-md-4">
                <div class="card language-card h-100 p-3" data-lang-id="${lang.id}">
                    <div class="d-flex align-items-center">
                        <span class="fs-1 me-3">${flagFor(lang.code)}</span>
                        <div>
                            <h6 class="mb-1">${lang.name}</h6>
                            <small class="text-muted lang-summary" data-lang-id="${lang.id}">—</small>
                        </div>
                    </div>
                </div>
            </div>
        `
      )
      .join('');
    container.querySelectorAll('.language-card').forEach((card) => {
      card.addEventListener('click', () => selectLanguage(parseInt(card.dataset.langId)));
    });
  }

  async function selectLanguage(langId) {
    state.selectedLangId = langId;
    document.querySelectorAll('.language-card').forEach((c) => {
      c.classList.toggle('active', parseInt(c.dataset.langId) === langId);
    });

    document.getElementById('loadingState').classList.add('d-none');
    document.getElementById('planContent').classList.remove('d-none');
    document.getElementById('saveBanner').classList.add('d-none');

    const [planRes, tmplRes] = await takePlanAndTemplates(langId);

    if (tmplRes.ok) {
      const td = await tmplRes.json();
      state.templatesByLang[langId] = td.templates || td.data?.templates || [];
    } else {
      state.templatesByLang[langId] = [];
    }

    if (planRes.status === 404) {
      // No plan yet — show template picker
      state.plansByLang[langId] = null;
      showNoPlanState(langId);
    } else if (planRes.ok) {
      const pd = await planRes.json();
      const planPayload = pd.data || pd; // unwrap if api_success() shape
      state.plansByLang[langId] = planPayload;
      state.studyPlanEnabled = !!planPayload.study_plan_enabled;
      showPlanEditor(langId);
    } else {
      const t = await planRes.text();
      throw new Error(`Plan load failed (${planRes.status}): ${t}`);
    }

    updateTotalTally();
    toggleFlagBanner();
  }

  function showNoPlanState(langId) {
    document.getElementById('noPlanState').classList.remove('d-none');
    document.getElementById('planEditor').classList.add('d-none');
    const picker = document.getElementById('templatePicker');
    const templates = state.templatesByLang[langId] || [];
    const defaultSuffix = T('study_plan.template.default_suffix');
    picker.innerHTML = templates
      .map((t) => {
        const label = T('study_plan.template.daily_minutes_label', { minutes: t.daily_minutes });
        return `
            <button class="btn btn-outline-primary template-pick-btn" data-template-id="${t.template_id}">
                ${label}${t.is_default ? ' ' + defaultSuffix : ''}
            </button>`;
      })
      .join('');
    picker.querySelectorAll('.template-pick-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const tmplId = parseInt(btn.dataset.templateId);
        await applyTemplate(langId, tmplId);
      });
    });
  }

  async function applyTemplate(langId, templateId) {
    const res = await window.authFetch('/api/study-plan', {
      method: 'PUT',
      body: JSON.stringify({ language_id: langId, template_id: templateId }),
    });
    if (!res.ok) {
      const t = await res.text();
      showSaveBanner(false, T('study_plan.template.failed', { error: t }));
      return;
    }
    await selectLanguage(langId); // reload
    showSaveBanner(true, T('study_plan.template.created'));
  }

  function showPlanEditor(langId) {
    document.getElementById('noPlanState').classList.add('d-none');
    document.getElementById('planEditor').classList.remove('d-none');

    const { plan, current_week } = state.plansByLang[langId];

    // Daily minutes
    const dm = plan.daily_minutes;
    document.getElementById('dailyMinutesRange').value = dm;
    document.getElementById('dailyMinutesNumber').value = dm;

    // Weekday shape — render values; renormalization happens on save
    const ws = Array.isArray(plan.weekday_shape) ? plan.weekday_shape : [1, 1, 1, 1, 1, 1, 1];
    for (let i = 0; i < 7; i++) {
      document.getElementById('ws' + i).value = Number(ws[i] ?? 1).toFixed(2);
    }
    updateWeekdaySum();

    // Skill overrides — derive skill list from current_week.target_counts, fall back to template
    const overrides = plan.skill_weight_overrides || {};
    const skillCodes = current_week
      ? Object.keys(current_week.target_counts || {})
      : skillsForLanguage(langId);
    renderSkillOverrides(skillCodes, overrides);

    // Template select
    renderTemplateSelect(langId, plan.template_id);

    // Daily session card (scope, modules, new words)
    renderDailySession(langId);

    // Week summary
    renderWeekSummary(current_week, state.plansByLang[langId]);
  }

  // ---------------------------------------------------------------------
  // Daily session card (session-modules + session-budget-settings, Option A)
  // ---------------------------------------------------------------------

  const DS = 'study_plan.daily_session.';
  const $ = (id) => document.getElementById(id);

  function currentPayload() {
    return state.plansByLang[state.selectedLangId];
  }

  // "6 reviews" / "1 review" (no plural support in the i18n bundle, so the
  // count phrase has its own _one key and is interpolated into the message).
  function countPhrase(kind, n) {
    const key = 'session.tail.' + kind + '_count' + (Number(n) === 1 ? '_one' : '');
    return T(key, { n });
  }

  function renderDailySession(langId) {
    const payload = state.plansByLang[langId];
    if (!payload || !payload.plan) return;
    const plan = payload.plan;
    const available = payload.available_modules || [];
    const included = SPS.includedSet(available, plan.excluded_modules || []);

    // Scope radios
    const scope = plan.budget_scope === 'tests_only' ? 'tests_only' : 'tests_and_review';
    document.querySelectorAll('input[name=budgetScope]').forEach((r) => {
      r.checked = r.value === scope;
    });

    // Test prestudy trigger
    const pm = ['auto', 'ask', 'off'].includes(plan.prestudy_mode) ? plan.prestudy_mode : 'auto';
    if ($('prestudyModeSelect')) $('prestudyModeSelect').value = pm;

    // New words
    const npd = SPS.clampNewWords(plan.new_words_per_day, 0);
    $('newWordsInput').value = npd;
    $('newWordsInput').dataset.last = npd;
    $('newWordsMsg').classList.add('d-none');

    // Module toggles (one form-switch per available module; checked = included)
    const box = $('moduleToggles');
    box.textContent = '';
    available.forEach((code) => {
      const wrap = document.createElement('div');
      wrap.className = 'form-check form-switch';
      wrap.dataset.module = code;
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.className = 'form-check-input module-toggle';
      input.id = 'moduleToggle_' + code;
      input.dataset.module = code;
      input.setAttribute('role', 'switch');
      input.checked = included.has(code);
      input.addEventListener('change', updateDailySession);
      const label = document.createElement('label');
      label.className = 'form-check-label';
      label.htmlFor = input.id;
      label.textContent = T('study_plan.modules.' + code);
      wrap.append(input, label);
      box.appendChild(wrap);
    });

    updateDailySession();
  }

  function readDailySessionForm() {
    const toggles = Array.from(document.querySelectorAll('input.module-toggle'));
    const included = new Set(toggles.filter((t) => t.checked).map((t) => t.dataset.module));
    const excluded = toggles.filter((t) => !t.checked).map((t) => t.dataset.module);
    const scopeEl = document.querySelector('input[name=budgetScope]:checked');
    return {
      toggles,
      included,
      excluded,
      scope: scopeEl ? scopeEl.value : 'tests_and_review',
      npd: SPS.clampNewWords($('newWordsInput').value, 0),
    };
  }

  // Recompute every derived element from the (unsaved) form + the saved GET payload.
  function updateDailySession() {
    const payload = currentPayload();
    if (!payload || !payload.plan) return;
    const form = readDailySessionForm();
    const available = payload.available_modules || [];
    const dailyEl = $('dailyMinutesNumber');
    const daily = parseInt(dailyEl.value, 10) || payload.plan.daily_minutes;
    const mpnw = Number(payload.minutes_per_new_word) || 0;
    const practiceIncluded = form.included.has('practice');

    // Scope: "tests only" is meaningless with no test/surface module on.
    const testsOnlyOff = SPS.testsOnlyDisabled(form.included);
    $('scopeTestsOnly').disabled = testsOnlyOff;
    if (testsOnlyOff && form.scope === 'tests_only') {
      $('scopeTestsAndReview').checked = true;
      form.scope = 'tests_and_review';
    }

    // Module locks (last toggle on; last test module under tests_only)
    const ms = SPS.moduleState(available, form.included, form.npd, form.scope);
    let anyLock = false;
    form.toggles.forEach((t) => {
      const reason = ms.locks[t.dataset.module];
      t.disabled = !!reason;
      const wrap = t.closest('.form-check');
      wrap.classList.toggle('locked', !!reason);
      if (reason) {
        anyLock = true;
        wrap.title = T(
          reason === 'last_test' ? 'study_plan.modules.last_test' : 'study_plan.modules.last_one'
        );
      } else {
        wrap.removeAttribute('title');
      }
    });
    $('moduleLockHint').classList.toggle('d-none', !anyLock);
    $('moduleShortHint').classList.toggle('d-none', !ms.flashcardsOnly);

    const card = SPS.computeCard({
      daily,
      scope: form.scope,
      practiceIncluded,
      newWordsPerDay: form.npd,
      shape: payload.plan.weekday_shape,
      minutesPerNewWord: mpnw,
      typicalDay: payload.typical_day,
      governor: payload.governor,
      forecast: payload.forecast,
    });

    // Stepper limits and static help
    $('newWordsDec').disabled = form.npd <= 0;
    $('newWordsInc').disabled = form.npd >= SPS.NEW_WORDS_MAX;
    $('newWordsHelp').textContent = T(DS + 'new_words.help', { minutes: Number(mpnw.toFixed(1)) });

    // Advisory only: Save is never blocked by this.
    $('newWordsNoReviewWarning').classList.toggle('d-none', !card.noReviewWarning);

    // "~F fit in your session, ~R after (optional)" after the governor
    $('newWordsEstimate').textContent =
      card.estimate === 'off'
        ? T(DS + 'new_words.estimate_off')
        : card.estimate === 'paused'
          ? T(DS + 'new_words.estimate_paused')
          : T(DS + 'new_words.estimate', { fit: card.fit, after: card.after });

    const hint = SPS.hintDescriptor(card, daily);
    $('newWordsHint').textContent =
      card.npd > 0 ? T(DS + 'new_words.' + hint.key, hint.params) : '';

    $('reviewForecast').textContent =
      card.npd > 0 ? T(DS + 'forecast', { minutes: card.forecastMin }) : '';

    renderGovernorNote(payload.governor, form.npd);

    const summary = SPS.typicalDaySummary(card, daily, practiceIncluded);
    let text = '';
    if (summary) {
      text = T(DS + summary.key, summary.params);
      if (summary.tail) text += ' ' + T(DS + summary.tail.key, summary.tail.params);
    }
    $('typicalDaySummary').textContent = text;
    $('typicalDaySummary').classList.toggle('d-none', !summary);
  }

  function renderGovernorNote(governor, npd) {
    const note = $('governorNote');
    const key = SPS.governorMessageKey(governor);
    if (!key || npd <= 0) {
      note.classList.add('d-none');
      note.textContent = '';
      return;
    }
    note.textContent = T(DS + 'governor.' + key, {
      reviews: countPhrase('reviews', governor.overdue_items || 0),
    });
    note.classList.remove('d-none');
  }

  function skillsForLanguage(langId) {
    const tpls = state.templatesByLang[langId] || [];
    if (tpls.length === 0) return ['reading', 'listening', 'dictation'];
    return Object.keys(tpls[0].weekly_test_counts || {});
  }

  function renderSkillOverrides(skillCodes, overrides) {
    const container = document.getElementById('skillOverrides');
    container.innerHTML = skillCodes
      .map((code) => {
        const v = overrides[code] != null ? overrides[code] : 1.0;
        return `
                <div class="skill-override-row">
                    <label>${code.replace(/_/g, ' ')}</label>
                    <input type="range" class="form-range skill-override-input"
                        data-skill="${code}" min="0.5" max="2.0" step="0.05" value="${v}">
                    <span class="value" data-skill-value="${code}">${Number(v).toFixed(2)}</span>
                </div>
            `;
      })
      .join('');
    container.querySelectorAll('.skill-override-input').forEach((input) => {
      input.addEventListener('input', () => {
        document.querySelector(`[data-skill-value="${input.dataset.skill}"]`).textContent = Number(
          input.value
        ).toFixed(2);
      });
    });
  }

  function renderTemplateSelect(langId, currentTemplateId) {
    const select = document.getElementById('templateSelect');
    const templates = state.templatesByLang[langId] || [];
    const placeholder = T('study_plan.template.select_placeholder');
    const defaultSuffix = T('study_plan.template.default_suffix');
    select.innerHTML = [`<option value="">${placeholder}</option>`]
      .concat(
        templates.map((t) => {
          const label = T('study_plan.template.daily_minutes_label', { minutes: t.daily_minutes });
          return `<option value="${t.template_id}" ${t.template_id === currentTemplateId ? 'selected' : ''}>
                    ${label}${t.is_default ? ' ' + defaultSuffix : ''}
                </option>`;
        })
      )
      .join('');
  }

  function renderWeekSummary(weekState, payload) {
    const startLabel = document.getElementById('weekStartLabel');
    const statsEl = document.getElementById('weekStats');
    const tableEl = document.getElementById('weekTargetsTable');

    if (!weekState) {
      startLabel.textContent = T('study_plan.no_week_yet');
      statsEl.innerHTML = '';
      tableEl.innerHTML = '';
      window.WeeklyStudy.render(
        document.getElementById('weeklyStudied'),
        payload ? payload.weekly_study : null,
        T
      );
      renderShortfallNote(null);
      return;
    }

    startLabel.textContent = T('study_plan.week_starting', { date: weekState.week_start_date });
    statsEl.innerHTML = `
            <div class="stat-tile"><h4>${weekState.total_weekly_minutes}</h4><small>${T('study_plan.stat.total_min')}</small></div>
            <div class="stat-tile"><h4>${weekState.practice_target_minutes}</h4><small>${T('study_plan.stat.practice_target')}</small></div>
            <div class="stat-tile"><h4>${(weekState.maintenance_share * 100).toFixed(0)}%</h4><small>${T('study_plan.stat.maint_share')}</small></div>
            <div class="stat-tile"><h4>${(weekState.acquisition_share * 100).toFixed(0)}%</h4><small>${T('study_plan.stat.acq_share')}</small></div>
            ${newWordsTile(weekState)}
        `;
    window.WeeklyStudy.render(
      document.getElementById('weeklyStudied'),
      payload ? payload.weekly_study : null,
      T
    );
    renderShortfallNote(payload);

    const targets = weekState.target_counts || {};
    const completed = weekState.completed_counts || {};
    const rows = Object.keys(targets)
      .map((skill) => {
        const done = completed[skill] || 0;
        const total = targets[skill] || 0;
        const pct = total > 0 ? Math.round((100 * done) / total) : 0;
        return `
                <tr>
                    <td>${skill.replace(/_/g, ' ')}</td>
                    <td>${done} / ${total}</td>
                    <td style="width: 40%;">
                        <div class="progress" style="height: .6rem;">
                            <div class="progress-bar" role="progressbar" style="width: ${pct}%"></div>
                        </div>
                    </td>
                    <td>${pct}%</td>
                </tr>
            `;
      })
      .join('');
    tableEl.innerHTML = `
            <table class="table table-sm mb-0">
                <thead><tr><th>${T('study_plan.targets.skill_col')}</th><th>${T('study_plan.targets.done_col')}</th><th></th><th>%</th></tr></thead>
                <tbody>${rows || `<tr><td colspan="4" class="text-center text-muted">${T('study_plan.targets.empty')}</td></tr>`}</tbody>
            </table>
        `;
  }

  // "New words x / y" tile (+ minutes done in optional rounds). Counts and
  // minutes are numbers from our own API; nothing here is user text.
  function newWordsTile(weekState) {
    if (weekState.new_words_target === undefined || weekState.new_words_target === null) return '';
    const done = Number(weekState.new_words_completed) || 0;
    const target = Number(weekState.new_words_target) || 0;
    const tail = Number(weekState.tail_completed_min) || 0;
    const sub =
      tail > 0
        ? `<br><small>${T('study_plan.stats.optional_rounds', { minutes: tail })}</small>`
        : '';
    return `<div class="stat-tile" id="newWordsTile"><h4>${done} / ${target}</h4><small>${T('study_plan.stats.new_words')}</small>${sub}</div>`;
  }

  function renderShortfallNote(payload) {
    let note = document.getElementById('shortfallNote');
    if (!note) {
      note = document.createElement('p');
      note.id = 'shortfallNote';
      note.className = 'form-text text-warning mt-2 mb-0 d-none';
      note.setAttribute('role', 'status');
      document.getElementById('weekStats').after(note);
    }
    const n = payload ? Number(payload.today_new_words_shortfall) : 0;
    note.textContent = n > 0 ? T(DS + 'shortfall', { n }) : '';
    note.classList.toggle('d-none', !(n > 0));
  }

  function updateWeekdaySum() {
    let sum = 0;
    for (let i = 0; i < 7; i++) sum += Number(document.getElementById('ws' + i).value || 0);
    document.getElementById('weekdaySumLabel').textContent = T('study_plan.weekday_sum', {
      sum: sum.toFixed(2),
    });
  }

  function updateTotalTally() {
    // Sum daily_minutes across all loaded plans
    let total = 0;
    Object.values(state.plansByLang).forEach((payload) => {
      if (payload && payload.plan) total += Number(payload.plan.daily_minutes || 0);
    });
    const tally = document.getElementById('totalTally');
    tally.textContent = T('study_plan.total_tally', { minutes: total });
    tally.classList.toggle('warn', total > 90);
  }

  function toggleFlagBanner() {
    document
      .getElementById('flagDisabledBanner')
      .classList.toggle('d-none', state.studyPlanEnabled);
  }

  function showSaveBanner(ok, msg) {
    const el = document.getElementById('saveBanner');
    el.className = 'alert ' + (ok ? 'alert-success' : 'alert-danger');
    el.textContent = msg;
    el.classList.remove('d-none');
  }

  function showError(msg) {
    document.getElementById('loadingState').classList.add('d-none');
    const e = document.getElementById('errorState');
    e.textContent = msg;
    e.classList.remove('d-none');
  }

  // --- Wire up live UI elements that don't depend on a specific plan -----

  document.getElementById('dailyMinutesRange').addEventListener('input', (e) => {
    document.getElementById('dailyMinutesNumber').value = e.target.value;
    updateDailySession();
  });
  document.getElementById('dailyMinutesNumber').addEventListener('input', (e) => {
    const v = Math.max(10, Math.min(180, parseInt(e.target.value || '30')));
    document.getElementById('dailyMinutesRange').value = v;
    updateDailySession();
  });

  // --- Daily session card ----------------------------------------------
  document.querySelectorAll('input[name=budgetScope]').forEach((r) => {
    r.addEventListener('change', updateDailySession);
  });

  // Set the new-words value (clamped 0..50). Going to 0 is refused when no
  // module is on, because new words > 0 is what keeps the plan non-empty.
  function setNewWords(raw) {
    const msg = $('newWordsMsg');
    const v = SPS.clampNewWords(raw, null);
    const input = $('newWordsInput');
    if (v === null) {
      input.value = SPS.clampNewWords(readDailySessionForm().npd, 0);
      return;
    }
    if (v === 0 && readDailySessionForm().included.size === 0) {
      msg.textContent = T(DS + 'new_words.needs_module');
      msg.classList.remove('d-none');
      input.value = SPS.clampNewWords(input.dataset.last, 1) || 1;
      updateDailySession();
      return;
    }
    msg.classList.add('d-none');
    input.value = v;
    input.dataset.last = v;
    updateDailySession();
  }
  // Live preview while typing (the value is clamped on read); the field itself
  // is only normalised on change/blur so typing is never fought.
  $('newWordsInput').addEventListener('input', updateDailySession);
  $('newWordsInput').addEventListener('change', (e) => setNewWords(e.target.value));
  $('newWordsInput').addEventListener('blur', (e) => setNewWords(e.target.value));
  $('newWordsDec').addEventListener('click', () => setNewWords(readDailySessionForm().npd - 1));
  $('newWordsInc').addEventListener('click', () => setNewWords(readDailySessionForm().npd + 1));

  // Dynamic text is built with T(); rebuild when the UI language changes.
  document.addEventListener('languageChanged', () => {
    const payload = currentPayload();
    if (!payload) return;
    renderDailySession(state.selectedLangId);
    renderWeekSummary(payload.current_week, payload);
  });
  for (let i = 0; i < 7; i++) {
    document.getElementById('ws' + i).addEventListener('input', updateWeekdaySum);
  }

  document.getElementById('saveBtn').addEventListener('click', async () => {
    const langId = state.selectedLangId;
    if (!langId) return;

    const dailyMinutes = parseInt(document.getElementById('dailyMinutesNumber').value);
    const weekdayShape = [];
    for (let i = 0; i < 7; i++)
      weekdayShape.push(Number(document.getElementById('ws' + i).value || 0));
    const overrides = {};
    document.querySelectorAll('.skill-override-input').forEach((inp) => {
      const v = Number(inp.value);
      if (Math.abs(v - 1.0) > 0.005) overrides[inp.dataset.skill] = v;
    });
    const templateId = parseInt(document.getElementById('templateSelect').value) || null;
    const session = readDailySessionForm();

    const body = {
      language_id: langId,
      daily_minutes: dailyMinutes,
      weekday_shape: weekdayShape,
      skill_weight_overrides: overrides,
      excluded_modules: session.excluded,
      budget_scope: session.scope,
      new_words_per_day: session.npd,
    };
    if ($('prestudyModeSelect')) body.prestudy_mode = $('prestudyModeSelect').value;
    if (templateId) body.template_id = templateId;

    try {
      const res = await window.authFetch('/api/study-plan', {
        method: 'PUT',
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const t = await res.text();
        showSaveBanner(false, T('study_plan.save_failed', { error: `${res.status} ${t}` }));
        return;
      }
      let saved = {};
      try {
        saved = await res.json();
      } catch (_) {
        /* non-JSON success body */
      }
      await selectLanguage(langId); // reload to get normalized weekday_shape from server
      showSaveBanner(
        true,
        T(saved.session_rebuilt ? 'study_plan.modules.session_rebuilt' : 'study_plan.save_success')
      );
    } catch (e) {
      showSaveBanner(false, T('study_plan.save_failed', { error: e.message }));
    }
  });

  document.getElementById('recomputeBtn').addEventListener('click', async () => {
    const langId = state.selectedLangId;
    if (!langId) return;
    if (!state.studyPlanEnabled) {
      showSaveBanner(false, T('study_plan.recompute_disabled'));
      return;
    }
    try {
      const res = await window.authFetch('/api/study-plan/recompute', {
        method: 'POST',
        body: JSON.stringify({ language_id: langId }),
      });
      if (!res.ok) {
        const t = await res.text();
        showSaveBanner(false, T('study_plan.save_failed', { error: `${res.status} ${t}` }));
        return;
      }
      await selectLanguage(langId);
      showSaveBanner(true, T('study_plan.recompute_success'));
    } catch (e) {
      showSaveBanner(false, T('study_plan.save_failed', { error: e.message }));
    }
  });
})();
