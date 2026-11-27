/* Knowledge Report, "My vocabulary" (wiki/features/knowledge-report.tech.md §3.1, §4, §10).
 *
 * GET /api/knowledge/summary (tech §6.3) renders the summary cards; GET
 * /api/knowledge/prestudy-suggestion adds next-step rule 2 when it arrives. Both start at once,
 * alongside the i18n bundle (ADR-042), and the page renders when the summary and i18n settle.
 *
 * Copy rules (§2.14): every number carries a prefix (From your answers / Estimated / Model); a
 * range uses an en dash and names the pool; the point estimate is drawn only as a tick, never
 * printed; "0 words" is never shown; no "due", "fading", praise, streaks or emoji. All text is set
 * with textContent. localStorage holds only kn.growthWindow, always inside try/catch.
 */
(function () {
  'use strict';

  const LANG_CODES = { 1: 'zh', 2: 'en', 3: 'ja' };
  const GLYPHS = { 1: '词', 2: 'Aa', 3: '語' };
  const WINDOW_KEY = 'kn.growthWindow';
  const GROUP_ORDER = ['most_common', 'common', 'mid', 'rare', 'none'];
  // Next-step rule numbers (§2.13); the prestudy suggestion is rule 2.
  const STEP_RANK = {
    'knowledge.next.check': 1,
    'knowledge.next.prestudy': 2,
    'knowledge.next.session': 3,
    'knowledge.next.review_practice': 4,
    'knowledge.next.refresh_check': 5,
    'knowledge.next.take_test': 6,
  };
  const MAX_STEPS = 3;

  const state = {
    languageId: 3,
    summary: null,
    prestudy: null,
    growthWindow: 30,
  };
  const el = {};

  // ---------------------------------------------------------------- helpers

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  // Intl locale for the UI language. English copy is British ("13 Sep", "recognised").
  const INTL_LOCALES = { en: 'en-GB', es: 'es', ja: 'ja', zh: 'zh-CN' };

  function locale() {
    const lang =
      window.LinguaI18n && window.LinguaI18n.currentLanguage
        ? window.LinguaI18n.currentLanguage()
        : 'en';
    return INTL_LOCALES[lang] || lang || 'en-GB';
  }

  function fmt(n) {
    try {
      return new Intl.NumberFormat(locale()).format(n);
    } catch {
      return String(n);
    }
  }

  // A "1 word|{count} words" string: the raw count picks the plural form, then the number is
  // shown in the locale's format (1,234).
  function trCount(key, count, params) {
    const text = tr(key, Object.assign({}, params || {}, { count: count }));
    const pretty = fmt(count);
    return pretty === String(count) ? text : text.split(String(count)).join(pretty);
  }

  function fmtSigned(n) {
    try {
      return new Intl.NumberFormat(locale(), { signDisplay: 'exceptZero' }).format(n);
    } catch {
      return (n > 0 ? '+' : '') + String(n);
    }
  }

  function parseDay(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : null;
  }

  // "13 Sep" (the year is added when it is not the report's year).
  function fmtDate(iso) {
    const d = parseDay(iso);
    if (!d) return '';
    const ref = parseDay(state.summary && state.summary.as_of) || new Date();
    const opts = { day: 'numeric', month: 'short', timeZone: 'UTC' };
    if (d.getUTCFullYear() !== ref.getUTCFullYear()) opts.year = 'numeric';
    try {
      return new Intl.DateTimeFormat(locale(), opts).format(d);
    } catch {
      return String(iso).slice(0, 10);
    }
  }

  function readLanguageId() {
    const id = parseInt(localStorage.getItem('selectedLanguageId'), 10);
    return LANG_CODES[id] ? id : 3;
  }

  function languageName() {
    const code = LANG_CODES[state.languageId];
    const name = tr('lang_select.name_' + code);
    if (name && name !== 'lang_select.name_' + code) return name;
    const lang = state.summary && state.summary.language;
    return (lang && lang.name) || code;
  }

  function node(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  // A line that leads with its claim prefix: "Model · Rated known after a direct check: 69 words".
  function prefixed(prefix, text, cls) {
    const p = node('p', 'kn-line' + (cls ? ' ' + cls : ''));
    p.appendChild(node('span', 'kn-prefix', tr('knowledge.prefix.' + prefix)));
    p.appendChild(node('span', 'kn-line__text', text));
    return p;
  }

  function show(n, on) {
    if (n) n.classList.toggle('d-none', !on);
  }

  function clear(n) {
    while (n && n.firstChild) n.removeChild(n.firstChild);
  }

  function linkButton(href, text, ghost) {
    const a = node('a', 'ld-btn' + (ghost ? ' ld-btn--ghost' : ''), text);
    a.href = href;
    return a;
  }

  function pct(x) {
    return Math.max(0, Math.min(100, x * 100));
  }

  // ---------------------------------------------------------------- loading

  function cacheEls() {
    [
      'knLoading',
      'knError',
      'knRetry',
      'knUnavailable',
      'knEmpty',
      'knEmptyTitle',
      'knEstimate',
      'knEstimateBody',
      'knGroups',
      'knGroupsBody',
      'knLists',
      'knListsBody',
      'knWordList',
      'knGrowth',
      'knGrowthSeg',
      'knGrowthBody',
      'knSkills',
      'knSkillsBody',
      'knNext',
      'knNextBody',
      'knProTeaser',
      'knProTitle',
      'knProBody',
      'knWords',
      'knSubtitle',
    ].forEach(function (id) {
      el[id.charAt(2).toLowerCase() + id.slice(3)] = document.getElementById(id);
    });
  }

  async function getJson(url) {
    try {
      const res = await window.authFetch(url);
      if (!res) return { status: 0, body: null };
      let body = null;
      try {
        body = await res.json();
      } catch {
        body = null;
      }
      return { status: res.status, body: body };
    } catch {
      return { status: 0, body: null };
    }
  }

  function initI18n() {
    try {
      if (window.LinguaI18n && window.LinguaI18n.init) {
        return Promise.resolve(window.LinguaI18n.init()).catch(function () {});
      }
    } catch {
      /* i18n is best-effort; the template keeps its English text */
    }
    return Promise.resolve();
  }

  function readGrowthWindow() {
    try {
      const v = parseInt(localStorage.getItem(WINDOW_KEY), 10);
      if (v === 30 || v === 90) state.growthWindow = v;
    } catch {
      /* storage blocked: keep 30 */
    }
  }

  function storeGrowthWindow() {
    try {
      localStorage.setItem(WINDOW_KEY, String(state.growthWindow));
    } catch {
      /* storage blocked: the choice lasts for this page view */
    }
  }

  async function load() {
    show(el.loading, true);
    show(el.error, false);
    show(el.unavailable, false);
    const q = '?language_id=' + state.languageId;
    const summaryReq = getJson('/api/knowledge/summary' + q);
    const prestudyReq = getJson('/api/knowledge/prestudy-suggestion' + q);
    const results = await Promise.all([summaryReq, initI18n()]);
    handleSummary(results[0]);
    const pre = await prestudyReq;
    if (pre.status === 200 && pre.body && pre.body.suggestion) {
      state.prestudy = pre.body.suggestion;
      if (state.summary) renderNext(state.summary);
    }
  }

  function handleSummary(res) {
    show(el.loading, false);
    if (res.status === 200 && res.body && res.body.status === 'success') {
      state.summary = res.body;
      render(res.body);
      return;
    }
    hideCards();
    if (res.status === 404 || res.status === 503) {
      show(el.unavailable, true); // E8
    } else {
      show(el.error, true); // E9
    }
  }

  function hideCards() {
    [
      el.empty,
      el.estimate,
      el.groups,
      el.lists,
      el.wordList,
      el.growth,
      el.skills,
      el.next,
      el.proTeaser,
      el.words,
    ].forEach(function (n) {
      show(n, false);
    });
  }

  // ---------------------------------------------------------------- render

  function render(s) {
    hideCards();
    if (el.subtitle) el.subtitle.textContent = languageName();
    if (s.state === 'E0') {
      // E0: one card, two actions, no zeros anywhere.
      el.emptyTitle.textContent = tr('knowledge.state.empty_title', { language: languageName() });
      show(el.empty, true);
      return;
    }
    renderEstimate(s);
    renderGroups(s);
    renderLists(s);
    renderGrowth(s);
    renderSkills(s);
    renderNext(s);
    renderPro(s);
  }

  function rangeBar(est) {
    const n = est.universe_words || 0;
    const bar = node('div', 'kn-range');
    bar.setAttribute('role', 'img');
    const lo = est.kind === 'range' ? est.lo : 0;
    bar.setAttribute(
      'aria-label',
      est.kind === 'range'
        ? tr('knowledge.estimate.headline', {
            lo: fmt(est.lo),
            hi: fmt(est.hi),
            n: fmt(n),
            language: languageName(),
          })
        : tr('knowledge.estimate.upper_only', {
            hi: fmt(est.hi),
            n: fmt(n),
            language: languageName(),
          })
    );
    if (n > 0) {
      const fill = node('span', 'kn-range__fill');
      fill.style.left = pct(lo / n) + '%';
      fill.style.width = Math.max(0.5, pct((Math.min(est.hi, n) - lo) / n)) + '%';
      bar.appendChild(fill);
      if (est.tick != null) {
        const tick = node('i', 'kn-range__tick');
        tick.style.left = pct(est.tick / n) + '%';
        bar.appendChild(tick);
      }
    }
    const ends = node('div', 'kn-range__ends ld-small ld-muted');
    ends.appendChild(node('span', null, fmt(0)));
    ends.appendChild(node('span', null, fmt(n)));
    const wrap = node('div', 'kn-range-wrap');
    wrap.appendChild(bar);
    wrap.appendChild(ends);
    return wrap;
  }

  function renderEstimate(s) {
    const body = el.estimateBody;
    clear(body);
    const est = s.estimate || {};
    if (est.shown) {
      const label = tr('knowledge.confidence.' + est.label);
      const head = node('div', 'kn-estimate__head');
      head.appendChild(node('span', 'kn-prefix', tr('knowledge.prefix.estimated')));
      head.appendChild(node('span', 'ld-tag ld-tag--info', label));
      body.appendChild(head);
      const params = {
        lo: fmt(est.lo),
        hi: fmt(est.hi),
        n: fmt(est.universe_words),
        language: languageName(),
      };
      const key =
        est.kind === 'range' ? 'knowledge.estimate.headline' : 'knowledge.estimate.upper_only';
      body.appendChild(node('p', 'kn-headline', tr(key, params)));
      body.appendChild(rangeBar(est));
      body.appendChild(
        node(
          'p',
          'ld-small ld-muted kn-basis',
          tr('knowledge.estimate.basis', {
            answers: fmt(est.answers),
            first: fmtDate(est.first_answer_at),
            last: fmtDate(est.last_answer_at),
          }) +
            ' · ' +
            label
        )
      );
    } else {
      let text;
      if (est.reason === 'out_of_date') {
        text = tr('knowledge.estimate.out_of_date', { date: fmtDate(est.last_answer_at) });
      } else if (est.reason === 'too_uncertain') {
        text = tr('knowledge.estimate.too_uncertain', { k: fmt(est.answers_needed || 0) });
      } else {
        text = tr('knowledge.estimate.need_answers', { have: fmt(est.have || 0) });
      }
      body.appendChild(node('p', 'kn-headline kn-headline--soft', text));
      const actions = node('div', 'kn-actions');
      actions.appendChild(linkButton('/placement', tr('knowledge.state.empty_placement')));
      actions.appendChild(linkButton('/calibration', tr('knowledge.state.empty_check'), true));
      body.appendChild(actions);
    }

    const rated = s.rated_known_words || 0;
    body.appendChild(
      prefixed(
        'model',
        rated > 0 ? trCount('knowledge.rated_known.line', rated) : tr('knowledge.rated_known.none')
      )
    );
    body.appendChild(node('p', 'ld-small ld-muted kn-why', tr('knowledge.rated_known.why')));
    const tracked = s.tracked_words || 0;
    body.appendChild(
      prefixed(
        'answers',
        tracked > 0 ? trCount('knowledge.tracked.line', tracked) : tr('knowledge.tracked.none')
      )
    );
    if (est.disagreement) {
      body.appendChild(node('p', 'ld-note ld-note--warn', tr('knowledge.estimate.disagreement')));
    }
    if (s.few_tracked) {
      body.appendChild(node('p', 'ld-note', tr('knowledge.state.few_words', { t: fmt(tracked) })));
    }
    if (s.stale_days != null) {
      body.appendChild(node('p', 'ld-note', tr('knowledge.state.stale', { d: fmt(s.stale_days) })));
    }
    show(el.estimate, true);
  }

  function shareBar(lo, hi, tickAt) {
    const bar = node('div', 'kn-range kn-range--thin');
    bar.setAttribute('aria-hidden', 'true');
    const fill = node('span', 'kn-range__fill');
    fill.style.left = pct(lo) + '%';
    fill.style.width = Math.max(0.5, pct(hi - lo)) + '%';
    bar.appendChild(fill);
    if (tickAt != null) {
      const tick = node('i', 'kn-range__tick');
      tick.style.left = pct(tickAt) + '%';
      bar.appendChild(tick);
    }
    return bar;
  }

  function renderGroups(s) {
    const body = el.groupsBody;
    clear(body);
    const estShown = !!(s.estimate && s.estimate.shown);
    const groups = (s.groups || []).slice().sort(function (a, b) {
      return GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group);
    });
    groups.forEach(function (g) {
      const row = node('div', 'kn-group');
      const head = node('div', 'kn-group__head');
      head.appendChild(node('b', null, tr('knowledge.group.' + g.group)));
      if (g.universe) {
        head.appendChild(
          node('small', 'ld-muted', tr('knowledge.group.universe', { n: fmt(g.universe) }))
        );
      }
      row.appendChild(head);
      if (g.shown) {
        row.appendChild(
          prefixed(
            'estimated',
            tr('knowledge.group.share', {
              lo: Math.round(g.share_lo * 100),
              hi: Math.round(g.share_hi * 100),
            })
          )
        );
        row.appendChild(shareBar(g.share_lo, g.share_hi));
      } else if (estShown && g.group !== 'none') {
        row.appendChild(
          node(
            'p',
            'ld-small ld-muted kn-line',
            tr('knowledge.group.not_enough', { n: fmt(g.answers || 0) })
          )
        );
      }
      const counts = node('p', 'kn-line kn-group__counts ld-small');
      [
        ['answers', tr('knowledge.group.tracked', { count: fmt(g.tracked || 0) })],
        ['model', tr('knowledge.group.rated_known', { count: fmt(g.rated_known || 0) })],
      ].forEach(function (pair) {
        // Each prefix stays on the same line as its number.
        const unit = node('span', 'kn-pair');
        unit.appendChild(node('span', 'kn-prefix', tr('knowledge.prefix.' + pair[0])));
        unit.appendChild(node('span', null, pair[1]));
        counts.appendChild(unit);
      });
      row.appendChild(counts);
      body.appendChild(row);
    });
    show(el.groups, groups.length > 0);
  }

  function renderLists(s) {
    // The list cards themselves come with the word-list files (TASK-1050). E4 (no file for the
    // language) hides the card; E4c (Storage unreadable) shows only this line.
    clear(el.listsBody);
    if (s.lists_unavailable) {
      el.listsBody.appendChild(node('p', 'ld-note', tr('knowledge.lists.unavailable')));
      show(el.lists, true);
    } else {
      show(el.lists, false);
    }
    show(el.wordList, false);
  }

  function renderGrowth(s) {
    const g = s.growth || {};
    const body = el.growthBody;
    clear(body);
    const entry = g['d' + state.growthWindow] || {};
    if (el.growthSeg) {
      el.growthSeg.querySelectorAll('button[data-window]').forEach(function (b) {
        b.setAttribute('aria-pressed', String(+b.dataset.window === state.growthWindow));
      });
    }

    body.appendChild(node('p', 'kn-prefix kn-prefix--block', tr('knowledge.prefix.answers')));
    const stats = node('div', 'ld-stats kn-stats');
    [
      ['practised', entry.practised],
      ['direct_checks', entry.direct_checks],
      ['met_in_texts', entry.met_in_texts],
    ].forEach(function (pair) {
      const tile = node('div', 'ld-stat');
      tile.appendChild(node('div', 'ld-stat__n', fmt(pair[1] || 0)));
      tile.appendChild(node('small', null, tr('knowledge.growth.' + pair[0])));
      stats.appendChild(tile);
    });
    body.appendChild(stats);

    if (entry.rated_known_delta != null) {
      body.appendChild(
        prefixed(
          'model',
          tr('knowledge.growth.rated_known_delta', {
            delta: fmtSigned(entry.rated_known_delta),
            date: fmtDate(entry.anchor_date),
          })
        )
      );
      body.appendChild(
        node(
          'p',
          'ld-small ld-muted kn-line',
          entry.direct_checks > 0
            ? tr('knowledge.growth.direct_checks_period', { k: fmt(entry.direct_checks) })
            : tr('knowledge.growth.no_direct_checks')
        )
      );
    } else if (entry.first_trend_on) {
      body.appendChild(
        node(
          'p',
          'ld-small ld-muted kn-line',
          tr('knowledge.growth.first_trend_on', { date: fmtDate(entry.first_trend_on) })
        )
      );
    }

    const change = entry.estimate_change;
    if (change) {
      const verdictKey = {
        no_clear_change: 'knowledge.growth.no_clear_change',
        higher: 'knowledge.growth.higher_than',
        lower: 'knowledge.growth.lower_than',
      }[change.verdict];
      if (verdictKey) {
        body.appendChild(
          prefixed('estimated', tr(verdictKey, { date: fmtDate(entry.anchor_date) }))
        );
        [
          ['then', change.then],
          ['now', change.now],
        ].forEach(function (pair) {
          const r = pair[1] || {};
          const range =
            r.kind === 'upper_only'
              ? tr('knowledge.growth.fewer_than', { hi: fmt(r.hi) })
              : fmt(r.lo) + '–' + fmt(r.hi);
          body.appendChild(
            node(
              'p',
              'ld-small ld-muted kn-line',
              tr('knowledge.growth.' + pair[0], {
                range: range,
                first: fmtDate(r.first_answer_at),
                last: fmtDate(r.last_answer_at),
              })
            )
          );
        });
      }
    }
    if (entry.pool_changed) {
      body.appendChild(
        node(
          'p',
          'ld-note',
          tr('knowledge.growth.pool_changed', {
            x: fmt(entry.pool_changed.from),
            y: fmt(entry.pool_changed.to),
            date: fmtDate(entry.anchor_date),
          })
        )
      );
    }
    if (g.idle60 > 0) {
      body.appendChild(prefixed('answers', trCount('knowledge.growth.idle60', g.idle60)));
    }
    show(el.growth, true);
  }

  function familyName(family) {
    const key = 'knowledge.skills.family.' + family;
    const name = tr(key);
    return name === key ? String(family).replace(/_/g, ' ') : name;
  }

  function familyKind(family) {
    const key = 'knowledge.skills.kind.' + family;
    const kind = tr(key);
    return kind === key ? String(family).replace(/_/g, ' ') : kind;
  }

  function renderSkills(s) {
    const skills = s.skills || {};
    const families = skills.families || [];
    const body = el.skillsBody;
    clear(body);
    if (!families.length) {
      show(el.skills, false);
      return;
    }
    body.appendChild(node('p', 'kn-prefix kn-prefix--block', tr('knowledge.prefix.answers')));
    families.forEach(function (f) {
      const row = node('div', 'kn-skill');
      const head = node('div', 'kn-group__head');
      head.appendChild(node('b', null, familyName(f.family)));
      if (f.shown) {
        const p = f.n ? f.correct / f.n : 0;
        head.appendChild(node('span', 'kn-skill__pct ld-num', Math.round(p * 100) + '%'));
        row.appendChild(head);
        row.appendChild(shareBar(f.lo, f.hi, p));
        row.appendChild(
          node(
            'p',
            'ld-small ld-muted kn-line',
            tr('knowledge.skills.tries', { n: fmt(f.n), m: fmt(f.meanings) })
          )
        );
      } else {
        row.appendChild(head);
        row.appendChild(
          node(
            'p',
            'ld-small ld-muted kn-line',
            tr('knowledge.skills.not_enough', { kind: familyKind(f.family), m: fmt(f.meanings) })
          )
        );
      }
      body.appendChild(row);
    });
    const sentence = skills.sentence;
    if (sentence) {
      const by = {};
      families.forEach(function (f) {
        by[f.family] = f;
      });
      const weak = by[sentence.weak];
      const strong = by[sentence.strong];
      if (weak && strong) {
        body.appendChild(
          node(
            'p',
            'kn-sentence',
            tr('knowledge.skills.sentence', {
              weak: familyKind(weak.family),
              weak_pct: Math.round((weak.correct / weak.n) * 100),
              weak_n: fmt(weak.n),
              weak_m: fmt(weak.meanings),
              strong: familyKind(strong.family),
              strong_pct: Math.round((strong.correct / strong.n) * 100),
              strong_n: fmt(strong.n),
              strong_m: fmt(strong.meanings),
            })
          )
        );
        body.appendChild(node('p', 'ld-small ld-muted', tr('knowledge.skills.footnote')));
      }
    }
    show(el.skills, true);
  }

  // The server's first three steps (rules 1, 3–6) plus rule 2 from /prestudy-suggestion, in rule
  // order, at most three. A stale learner (E3) keeps "Do today's session" first.
  function stepsWithPrestudy(s) {
    const steps = (s.next_steps || []).slice();
    const pre = state.prestudy;
    if (pre && pre.slug) {
      steps.push({
        key: 'knowledge.next.prestudy',
        href: '/test/' + encodeURIComponent(pre.slug) + '/prestudy',
        params: { title: pre.title || '', u: pre.unknown, n: pre.n },
      });
    }
    const stale = s.stale_days != null;
    const rank = function (st) {
      if (stale && st.key === 'knowledge.next.session') return 0;
      return STEP_RANK[st.key] || 99;
    };
    return steps
      .map(function (st, i) {
        return { st: st, i: i };
      })
      .sort(function (a, b) {
        return rank(a.st) - rank(b.st) || a.i - b.i;
      })
      .map(function (x) {
        return x.st;
      })
      .slice(0, MAX_STEPS);
  }

  function stepLabel(step) {
    const p = Object.assign({}, step.params || {});
    if (p.n != null && step.key === 'knowledge.next.check') p.n = fmt(p.n);
    if (step.key === 'knowledge.next.prestudy') {
      p.u = fmt(p.u || 0);
      p.n = fmt(p.n || 0);
    }
    return tr(step.key, p);
  }

  function renderNext(s) {
    const body = el.nextBody;
    clear(body);
    const steps = stepsWithPrestudy(s);
    steps.forEach(function (step, i) {
      const a = linkButton(step.href, stepLabel(step), i > 0);
      a.dataset.step = step.key;
      body.appendChild(a);
    });
    show(el.next, steps.length > 0);
  }

  function renderPro(s) {
    const detail = s.detail || {};
    const body = el.proBody;
    clear(body);
    if (detail.level === 1) {
      // Pro: the Word by word section arrives with TASK-1046.
      show(el.proTeaser, false);
      return;
    }
    const t = s.pro_teaser || {};
    const clauses = [];
    if (t.tracked_meanings) {
      clauses.push(trCount('knowledge.pro.teaser_words', t.tracked_meanings));
    }
    if (t.missed_recent) {
      clauses.push(tr('knowledge.pro.teaser_missed', { count: fmt(t.missed_recent) }));
    }
    if (t.missing_next_level && t.next_level) {
      clauses.push(
        tr('knowledge.pro.teaser_next_level', {
          count: fmt(t.missing_next_level),
          level: t.next_level,
        })
      );
    }
    clauses.push(tr('knowledge.pro.teaser_export'));
    body.appendChild(node('p', 'kn-pro__clauses', clauses.join(' · ')));

    if (detail.preview) {
      // Shadow mode (§3.3): a neutral note, no upsell.
      el.proTitle.textContent = tr('knowledge.pro.preview_title');
      body.appendChild(node('p', 'ld-note', tr('knowledge.pro.preview_note')));
    } else {
      el.proTitle.textContent = tr('knowledge.pro.title');
      if (window.LinguaPaywall && typeof window.LinguaPaywall.open === 'function') {
        const btn = node('button', 'ld-btn ld-btn--ghost', tr('knowledge.pro.see'));
        btn.type = 'button';
        btn.addEventListener('click', function () {
          window.LinguaPaywall.open({ reason: 'bkt_report_detail' });
        });
        body.appendChild(btn);
      } else {
        body.appendChild(node('p', 'ld-small ld-muted', tr('knowledge.pro.available_with_pro')));
      }
    }
    show(el.proTeaser, true);
  }

  // ---------------------------------------------------------------- boot

  function bind() {
    if (el.retry) el.retry.addEventListener('click', load);
    if (el.growthSeg) {
      el.growthSeg.addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-window]');
        if (!btn) return;
        const w = parseInt(btn.dataset.window, 10);
        if (w !== 30 && w !== 90) return;
        state.growthWindow = w;
        storeGrowthWindow();
        if (state.summary) renderGrowth(state.summary);
      });
    }
    document.addEventListener('languageChanged', function () {
      if (state.summary) render(state.summary);
    });
  }

  function boot() {
    cacheEls();
    state.languageId = readLanguageId();
    readGrowthWindow();
    if (window.LinguaShell && window.LinguaShell.setTaskHeader) {
      window.LinguaShell.setTaskHeader({ glyph: GLYPHS[state.languageId] });
    }
    bind();
    load();
  }

  // Exactly once, whether this runs before DOMContentLoaded (deferred) or after it.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
