// static/js/session/players/pitch_accent.js
// Japanese pitch-accent trainer player for the daily-session runner. Ported
// from templates/test_pitch_accent.html (whose styles live in the global
// static/css/styles.css, so no inline CSS is needed here). Container-scoped,
// leak-free teardown (document keydown + timer tracked), error-modal buttons
// wired via listeners (no window globals), and ctx.onComplete() on finish.

const CLASS_INFO = {
  heiban: { key: 'pitch.class.heiban', arrow: '←', desc: 'pitch.class.heiban_desc' },
  atamadaka: { key: 'pitch.class.atamadaka', arrow: '↑', desc: 'pitch.class.atamadaka_desc' },
  nakadaka: { key: 'pitch.class.nakadaka', arrow: '→', desc: 'pitch.class.nakadaka_desc' },
  odaka: { key: 'pitch.class.odaka', arrow: '↓', desc: 'pitch.class.odaka_desc' },
};

const KEY_TO_CLASS = {
  ArrowLeft: 'heiban',
  ArrowUp: 'atamadaka',
  ArrowRight: 'nakadaka',
  ArrowDown: 'odaka',
};

function t(key, fallback) {
  try {
    return window.LinguaI18n && LinguaI18n.t
      ? LinguaI18n.t(key) || fallback || key
      : fallback || key;
  } catch (e) {
    return fallback || key;
  }
}

function escapeHtml(str) {
  if (str == null) return '';
  if (window.LinguaUtils && LinguaUtils.escapeHtml) return LinguaUtils.escapeHtml(String(str));
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeHtmlFuri(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderFuriganaToken(tok) {
  if (!tok || tok.kind !== 'ruby') return null;
  const segs =
    Array.isArray(tok.segments) && tok.segments.length
      ? tok.segments
      : [{ base: tok.base, rt: tok.rt }];
  let html = '<ruby>';
  for (const seg of segs)
    html += escapeHtmlFuri(seg.base) + '<rt>' + escapeHtmlFuri(seg.rt || '') + '</rt>';
  html += '</ruby>';
  return html;
}

export function mount(container, ctx) {
  const state = {
    slug: ctx.item.slug,
    testData: null,
    allTokens: [],
    playableTokens: [],
    playableIndices: [],
    currentIndex: 0,
    correctCount: 0,
    errorCount: 0,
    errors: [],
    startTime: null,
    timerInterval: null,
    isComplete: false,
    isPaused: false,
    mode: 'quick',
    contourInput: [],
    contourCursor: 0,
    furiganaPayload: null,
    furiganaBySurface: {},
    furiganaEnabled: false,
    furiganaUsedThisAttempt: false,
  };

  const cleanup = [];
  const on = (el, ev, fn, opts) => {
    el.addEventListener(ev, fn, opts);
    cleanup.push(() => el.removeEventListener(ev, fn, opts));
  };
  const q = (id) => container.querySelector('#' + id);
  const qs = (sel) => container.querySelector(sel);
  const qsa = (sel) => container.querySelectorAll(sel);

  container.innerHTML = MARKUP;
  init();

  return {
    destroy() {
      if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
      }
      cleanup.forEach((fn) => {
        try {
          fn();
        } catch (_) {}
      });
    },
  };

  function renderSurfaceHtml(surface) {
    if (state.furiganaEnabled) {
      const tok = state.furiganaBySurface[surface];
      const html = tok ? renderFuriganaToken(tok) : null;
      if (html) return html;
    }
    return escapeHtmlFuri(surface);
  }

  async function init() {
    try {
      showLoading(true);
      if (!state.slug) throw new Error('No test slug');
      try {
        const savedMode = localStorage.getItem('pa_mode');
        if (savedMode === 'quick' || savedMode === 'contour') state.mode = savedMode;
      } catch (e) {}

      await loadTestData();
      await setupFuriganaToggle();
      renderPassage();
      setupInputHandlers();
      setupModeToggle();
      renderControls();
      startTimer();

      q('paHeader').style.display = 'block';
      q('passageContainer').style.display = 'block';
      q('controlsHint').style.display = 'block';

      qsa('#modeToggle button').forEach((btn) =>
        btn.classList.toggle('active', btn.dataset.mode === state.mode)
      );
      highlightCurrent();
      showLoading(false);
    } catch (err) {
      console.error('Pitch accent init error:', err);
      showError(err.message);
      showLoading(false);
    }
  }

  async function loadTestData() {
    const resp = await window.authFetch(`/api/tests/test/${state.slug}`);
    if (!resp.ok) throw new Error(t('pitch.error.load_failed', 'Failed to load test'));
    const data = await resp.json();
    state.testData = data.test_data;
    if (!data.pitch_payload || data.pitch_payload.length === 0) {
      throw new Error(
        t('pitch.error.no_data', 'No pitch accent data is available for this test yet.')
      );
    }
    state.allTokens = data.pitch_payload;
    state.allTokens.forEach((tok, i) => {
      if (!tok.is_punctuation && tok.mora_count > 0 && tok.pattern_class !== 'unknown') {
        state.playableIndices.push(i);
        state.playableTokens.push(tok);
      }
    });
    state.furiganaPayload = data.furigana_payload || null;
    if (state.furiganaPayload && Array.isArray(state.furiganaPayload.transcript)) {
      for (const tok of state.furiganaPayload.transcript) {
        if (tok && tok.kind === 'ruby' && tok.base) state.furiganaBySurface[tok.base] = tok;
      }
    }
    if (state.playableTokens.length === 0) {
      throw new Error(t('pitch.error.no_words', 'No drillable words found in this passage.'));
    }
    q('testTitle').textContent = state.testData.title || t('pitch.title', 'Pitch Accent Trainer');
    const langName =
      window.LinguaMetadata && LinguaMetadata.getNativeName
        ? LinguaMetadata.getNativeName(state.testData.language)
        : '日本語';
    q('testLanguage').textContent = langName || '日本語';
  }

  function renderPassage() {
    const grid = q('passageGrid');
    grid.innerHTML = '';
    state.allTokens.forEach((token, idx) => {
      const el = document.createElement('span');
      el.className = 'word-token';
      el.dataset.index = idx;
      const surfaceHtml = renderSurfaceHtml(token.surface);
      if (token.is_punctuation || token.pattern_class === 'unknown') {
        el.classList.add('punctuation');
        el.innerHTML = `<span class="word-surface">${surfaceHtml}</span>`;
      } else {
        el.classList.add('upcoming');
        el.innerHTML = `<span class="word-surface">${surfaceHtml}</span><span class="word-kana-mini">&nbsp;</span><span class="contour-mini"></span>`;
      }
      grid.appendChild(el);
    });
  }

  function highlightCurrent() {
    if (state.isComplete) return;
    const prev = qs('.word-token.current');
    if (prev) prev.classList.remove('current');
    const allIdx = state.playableIndices[state.currentIndex];
    const el = qs(`.word-token[data-index="${allIdx}"]`);
    if (el) {
      el.classList.remove('upcoming');
      el.classList.add('current');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (state.mode === 'contour') {
      resetContourInput();
      renderScratchpad();
    } else {
      clearScratchpad();
    }
    updateProgress();
  }

  function markCompleted(playableIdx, token) {
    const allIdx = state.playableIndices[playableIdx];
    const el = qs(`.word-token[data-index="${allIdx}"]`);
    if (!el) return;
    el.classList.remove('current', 'upcoming');
    el.classList.add('completed', `cls-${token.pattern_class}`);
    const kanaEl = el.querySelector('.word-kana-mini');
    if (kanaEl) kanaEl.textContent = token.kana || '';
    const contourEl = el.querySelector('.contour-mini');
    if (contourEl) contourEl.innerHTML = miniContourSvg(token);
    el.classList.add('correct-flash');
    setTimeout(() => el.classList.remove('correct-flash'), 200);
  }

  function flashError(playableIdx) {
    const allIdx = state.playableIndices[playableIdx];
    const el = qs(`.word-token[data-index="${allIdx}"]`);
    if (el) {
      el.classList.add('error-flash');
      setTimeout(() => el.classList.remove('error-flash'), 300);
    }
  }

  function updateProgress() {
    const total = state.playableTokens.length;
    const pct = total > 0 ? (state.currentIndex / total) * 100 : 0;
    q('progressFill').style.width = pct + '%';
  }

  function derivedParticlePitch(token) {
    if (!token || typeof token.accent !== 'number') return null;
    return token.accent === 0 ? 'H' : 'L';
  }

  function classStrokeColor(cls) {
    switch (cls) {
      case 'heiban':
        return 'var(--accent-heiban)';
      case 'atamadaka':
        return 'var(--accent-atamadaka)';
      case 'nakadaka':
        return 'var(--accent-nakadaka)';
      case 'odaka':
        return 'var(--accent-odaka)';
      default:
        return 'var(--primary)';
    }
  }

  function miniContourSvg(token) {
    const wordCount = token.contour ? token.contour.length : 0;
    if (wordCount <= 0) return '';
    const particlePitch = token.trailing_particle_pitch || derivedParticlePitch(token);
    const totalSlots = wordCount + 1;
    const slotW = 14;
    const w = Math.max(56, totalSlots * slotW);
    const h = 28;
    const stepX = w / totalSlots;
    const yHigh = 5,
      yLow = h - 7;
    const stroke = classStrokeColor(token.pattern_class);
    const isPhantom = !token.trailing_particle;
    const pts = [];
    for (let i = 0; i < wordCount; i++)
      pts.push([stepX * i + stepX / 2, token.contour[i] === 'H' ? yHigh : yLow]);
    if (particlePitch)
      pts.push([stepX * wordCount + stepX / 2, particlePitch === 'H' ? yHigh : yLow]);
    const dividerX = stepX * wordCount;
    const path = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0] + ',' + p[1]).join(' ');
    const dots = pts
      .map((p, i) => {
        const isLast = i === pts.length - 1;
        const r = isLast && isPhantom ? 1.8 : 2.6;
        const fill = isLast && isPhantom ? 'var(--text-muted)' : stroke;
        return `<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${fill}"/>`;
      })
      .join('');
    return (
      `<svg width="${w}" height="${h}" style="display:block;">` +
      `<line x1="0" y1="${yHigh}" x2="${w}" y2="${yHigh}" stroke="var(--border-default)" stroke-width="0.5" stroke-dasharray="2 3"/>` +
      `<line x1="0" y1="${yLow}" x2="${w}" y2="${yLow}" stroke="var(--border-default)" stroke-width="0.5" stroke-dasharray="2 3"/>` +
      `<line x1="${dividerX}" y1="2" x2="${dividerX}" y2="${h - 2}" stroke="var(--border-strong)" stroke-width="0.5" stroke-dasharray="1 2"/>` +
      `<path d="${path}" stroke="${stroke}" stroke-width="1.75" fill="none" stroke-linejoin="round" stroke-linecap="round"/>` +
      dots +
      `</svg>`
    );
  }

  function handleClassInput(guessedClass) {
    if (state.isComplete || state.isPaused || state.mode !== 'quick') return;
    const token = state.playableTokens[state.currentIndex];
    if (!token) return;
    if (guessedClass === token.pattern_class) acceptToken(token);
    else rejectToken(token, { mode: 'quick', guessedClass });
  }

  function resetContourInput() {
    const token = state.playableTokens[state.currentIndex];
    if (!token) {
      state.contourInput = [];
      state.contourCursor = 0;
      return;
    }
    state.contourInput = new Array(token.mora_count).fill(null);
    state.contourCursor = 0;
  }

  function clearScratchpad() {
    const wrap = q('scratchpadContainer');
    if (wrap) wrap.innerHTML = '';
  }

  function renderScratchpad() {
    const wrap = q('scratchpadContainer');
    if (!wrap) return;
    const token = state.playableTokens[state.currentIndex];
    if (!token) {
      wrap.innerHTML = '';
      return;
    }
    const moraCount = token.mora_count;
    const hasParticle = !!token.trailing_particle;
    const cols = moraCount + (hasParticle ? 1 : 0);
    const colTemplate = `60px repeat(${cols}, 1fr)`;

    let highRow = `<div class="scratch-row" style="grid-template-columns: ${colTemplate};"><div class="scratch-row-label">HIGH</div>`;
    for (let i = 0; i < moraCount; i++) {
      const sel = state.contourInput[i] === 'H' ? 'selected row-high' : '';
      const cur = i === state.contourCursor ? 'current' : '';
      highRow += `<div class="scratch-cell ${sel} ${cur}" data-mora="${i}" data-pitch="H"><span class="scratch-dot"></span></div>`;
    }
    if (hasParticle)
      highRow += `<div class="scratch-cell" style="opacity:0.4; cursor:default;"></div>`;
    highRow += `</div>`;

    let lowRow = `<div class="scratch-row" style="grid-template-columns: ${colTemplate};"><div class="scratch-row-label">LOW</div>`;
    for (let i = 0; i < moraCount; i++) {
      const sel = state.contourInput[i] === 'L' ? 'selected row-low' : '';
      const cur = i === state.contourCursor ? 'current' : '';
      lowRow += `<div class="scratch-cell ${sel} ${cur}" data-mora="${i}" data-pitch="L"><span class="scratch-dot"></span></div>`;
    }
    if (hasParticle)
      lowRow += `<div class="scratch-cell" style="opacity:0.4; cursor:default;"></div>`;
    lowRow += `</div>`;

    let moraRow = `<div class="scratch-row scratch-mora-row" style="grid-template-columns: ${colTemplate};"><div></div>`;
    for (let i = 0; i < moraCount; i++) moraRow += `<div>${escapeHtml(token.mora[i] || '')}</div>`;
    if (hasParticle)
      moraRow += `<div class="particle">${escapeHtml(token.trailing_particle)}</div>`;
    moraRow += `</div>`;

    const ready = state.contourInput.every((v) => v !== null);
    const submitLabel = t('pitch.contour.submit', 'Submit (Enter)');
    const inst = t(
      'pitch.contour.instruction',
      'Click HIGH or LOW for each mora. Then press Enter.'
    );

    wrap.innerHTML = `
            <div class="scratchpad" id="scratchpad">
                <div class="scratch-word">${escapeHtml(token.surface)}</div>
                <div class="scratch-instruction">${inst}</div>
                <div class="scratch-wrap"><div class="scratch-track">${highRow}${lowRow}${moraRow}</div></div>
                <button class="scratch-submit" id="scratchSubmit" ${ready ? '' : 'disabled'}>${submitLabel}</button>
            </div>`;

    wrap.querySelectorAll('.scratch-cell[data-mora]').forEach((cell) => {
      cell.addEventListener('click', () =>
        setContourMora(parseInt(cell.dataset.mora, 10), cell.dataset.pitch)
      );
    });
    const sub = wrap.querySelector('#scratchSubmit');
    if (sub) sub.addEventListener('click', submitContour);
  }

  function setContourMora(moraIdx, pitch) {
    if (state.isComplete || state.isPaused || state.mode !== 'contour') return;
    state.contourInput[moraIdx] = pitch;
    state.contourCursor = Math.min(moraIdx + 1, state.contourInput.length - 1);
    renderScratchpad();
  }

  function moveContourCursor(delta) {
    if (state.mode !== 'contour') return;
    state.contourCursor = Math.max(
      0,
      Math.min(state.contourInput.length - 1, state.contourCursor + delta)
    );
    renderScratchpad();
  }

  function submitContour() {
    if (state.isComplete || state.isPaused || state.mode !== 'contour') return;
    const token = state.playableTokens[state.currentIndex];
    if (!token) return;
    if (state.contourInput.some((v) => v === null)) return;
    const { valid, derivedAccent, reason } = analyzeContour(state.contourInput);
    if (!valid) {
      rejectToken(token, { mode: 'contour', reason });
      return;
    }
    if (derivedAccent === token.accent) acceptToken(token);
    else rejectToken(token, { mode: 'contour', derivedAccent });
  }

  function analyzeContour(contour) {
    if (contour.length === 0) return { valid: false, reason: 'empty' };
    if (contour.length >= 2 && contour[0] === contour[1])
      return { valid: false, reason: 'mora1_eq_mora2' };
    let drops = 0,
      dropAt = 0,
      rises = 0;
    for (let i = 1; i < contour.length; i++) {
      if (contour[i - 1] === 'H' && contour[i] === 'L') {
        drops++;
        dropAt = i;
      }
      if (contour[i - 1] === 'L' && contour[i] === 'H') {
        if (drops > 0) rises++;
      }
    }
    if (drops > 1) return { valid: false, reason: 'multiple_drops' };
    if (rises > 0) return { valid: false, reason: 'rise_after_drop' };
    const accent = drops === 0 ? 0 : dropAt;
    return { valid: true, derivedAccent: accent };
  }

  function acceptToken(token) {
    markCompleted(state.currentIndex, token);
    state.correctCount++;
    state.currentIndex++;
    if (state.currentIndex >= state.playableTokens.length) completeGame();
    else highlightCurrent();
  }

  function rejectToken(token, info) {
    state.errorCount++;
    flashError(state.currentIndex);
    state.errors.push({
      surface: token.surface,
      kana: token.kana,
      accent: token.accent,
      pattern_class: token.pattern_class,
      mode: info.mode,
      info,
    });
    showErrorModal(token, info);
  }

  function showErrorModal(token, info) {
    state.isPaused = true;
    const wordCount = token.contour ? token.contour.length : 0;
    const particlePitch = token.trailing_particle_pitch || derivedParticlePitch(token);
    const showParticleSlot = !!particlePitch;
    const isPhantomParticle = showParticleSlot && !token.trailing_particle;
    const totalSlots = wordCount + (showParticleSlot ? 1 : 0);
    const cellW = 36;
    const svgW = Math.max(160, totalSlots * cellW);
    const svgH = 100;
    const yHigh = 18,
      yLow = svgH - 36;
    const stepX = svgW / totalSlots;
    const stroke = classStrokeColor(token.pattern_class);

    const pts = [];
    for (let i = 0; i < wordCount; i++)
      pts.push([stepX * i + stepX / 2, token.contour[i] === 'H' ? yHigh : yLow]);
    if (showParticleSlot)
      pts.push([stepX * wordCount + stepX / 2, particlePitch === 'H' ? yHigh : yLow]);
    const dividerX = stepX * wordCount;
    const pathD = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0] + ',' + p[1]).join(' ');
    const dots = pts
      .map((p, i) => {
        const isLast = i === pts.length - 1;
        const fill = isLast && isPhantomParticle ? 'var(--text-muted)' : stroke;
        const r = isLast && isPhantomParticle ? 3.2 : 4;
        return `<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${fill}"/>`;
      })
      .join('');

    let moraLabels = '';
    for (let i = 0; i < token.mora.length; i++) {
      moraLabels += `<text x="${stepX * i + stepX / 2}" y="${svgH - 6}" text-anchor="middle" font-size="14" fill="var(--text-primary)">${escapeHtml(token.mora[i] || '')}</text>`;
    }
    if (showParticleSlot) {
      const particleLabel = token.trailing_particle || '+が';
      const labelFill = isPhantomParticle ? 'var(--text-muted)' : 'var(--text-secondary)';
      const labelStyle = isPhantomParticle ? 'font-style: italic;' : '';
      moraLabels += `<text x="${stepX * wordCount + stepX / 2}" y="${svgH - 6}" text-anchor="middle" font-size="14" fill="${labelFill}" style="${labelStyle}">${escapeHtml(particleLabel)}</text>`;
    }

    const className = t(CLASS_INFO[token.pattern_class].key, token.pattern_class);
    const classDesc = t(CLASS_INFO[token.pattern_class].desc, '');

    let yourAnswerHtml = '';
    if (info.mode === 'quick' && info.guessedClass) {
      const guessName = t(CLASS_INFO[info.guessedClass].key, info.guessedClass);
      yourAnswerHtml = `
                <div class="error-classes">
                    <div class="class-label"><div class="class-name" style="color: var(--accent-${info.guessedClass})">${escapeHtml(guessName)}</div><div class="class-desc">${t('pitch.your_answer', 'Your answer')}</div></div>
                    <div style="font-size: 1.5rem; color: var(--text-muted); align-self: center;"><i class="bi bi-arrow-right"></i></div>
                    <div class="class-label"><div class="class-name" style="color: var(--accent-${token.pattern_class})">${escapeHtml(className)}</div><div class="class-desc">${t('pitch.correct', 'Correct')}</div></div>
                </div>`;
    } else if (info.mode === 'contour' && info.reason) {
      const reasonMsg =
        {
          mora1_eq_mora2: t(
            'pitch.error.mora1_eq_mora2',
            'Mora 1 and mora 2 must differ in pitch.'
          ),
          multiple_drops: t(
            'pitch.error.multiple_drops',
            'A Japanese word has at most one H→L drop.'
          ),
          rise_after_drop: t(
            'pitch.error.rise_after_drop',
            'Pitch cannot rise again after it has fallen.'
          ),
          empty: t('pitch.error.empty', 'No contour was submitted.'),
        }[info.reason] || info.reason;
      yourAnswerHtml = `<div class="accent-explanation">${escapeHtml(reasonMsg)}</div>`;
    } else if (info.mode === 'contour' && typeof info.derivedAccent === 'number') {
      yourAnswerHtml = `<div class="accent-explanation">${t('pitch.error.wrong_drop', 'Close — your contour is valid, but the drop is in the wrong place.')}</div>`;
    }

    const html = `
            <div class="error-backdrop" data-pa-dismiss></div>
            <div class="error-modal">
                <div class="error-word cls-${token.pattern_class}" style="color: var(--accent-${token.pattern_class})">${escapeHtml(token.surface)}</div>
                <div class="error-kana">${escapeHtml(token.kana || '')}</div>
                ${yourAnswerHtml}
                <div style="text-align: center; margin: 8px 0 12px;">
                    <svg width="${svgW}" height="${svgH}" style="max-width: 100%;">
                        <line x1="0" y1="${yHigh}" x2="${svgW}" y2="${yHigh}" stroke="var(--border-default)" stroke-dasharray="3 4"/>
                        <line x1="0" y1="${yLow}" x2="${svgW}" y2="${yLow}" stroke="var(--border-default)" stroke-dasharray="3 4"/>
                        <line x1="${dividerX}" y1="6" x2="${dividerX}" y2="${svgH - 22}" stroke="var(--border-strong)" stroke-width="1" stroke-dasharray="2 3"/>
                        <text x="2" y="${yHigh - 4}" font-size="10" fill="var(--text-muted)">HIGH</text>
                        <text x="2" y="${yLow + 14}" font-size="10" fill="var(--text-muted)">LOW</text>
                        <path d="${pathD}" stroke="${stroke}" stroke-width="2.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
                        ${dots}${moraLabels}
                    </svg>
                </div>
                <div class="accent-explanation">
                    <strong>${escapeHtml(className)}</strong>
                    ${
                      token.accent === 0
                        ? ` — ${t('pitch.explain.heiban', 'no drop; pitch stays high after the first mora (including any following particle).')}`
                        : ` — ${t('pitch.explain.drop_at', 'drop after mora')} ${token.accent}${token.accent === token.mora_count ? ' ' + t('pitch.explain.odaka_particle', '— the drop only becomes audible because of the following particle.') : ''}`
                    }
                    ${classDesc ? `<br><span style="color: var(--text-muted); font-size: 0.85rem;">${escapeHtml(classDesc)}</span>` : ''}
                </div>
                <button class="error-continue-btn" type="button" data-pa-dismiss>${t('pitch.continue', 'Continue')} <span style="font-size: 0.8em; opacity: 0.7;">(Enter)</span></button>
            </div>`;
    const cont = q('errorModalContainer');
    cont.innerHTML = html;
    cont
      .querySelectorAll('[data-pa-dismiss]')
      .forEach((el) => el.addEventListener('click', dismissErrorModal));
  }

  function dismissErrorModal() {
    q('errorModalContainer').innerHTML = '';
    state.isPaused = false;
    if (state.mode === 'contour') {
      resetContourInput();
      renderScratchpad();
    }
  }

  function setupInputHandlers() {
    on(document, 'keydown', (e) => {
      if (state.isComplete) return;
      if (state.isPaused) {
        if (e.key === 'Enter') {
          e.preventDefault();
          dismissErrorModal();
        }
        return;
      }
      if (state.mode === 'quick') {
        const cls = KEY_TO_CLASS[e.key];
        if (cls) {
          e.preventDefault();
          handleClassInput(cls);
          return;
        }
      } else {
        if (e.key === '1' || e.key === 'l' || e.key === 'L') {
          e.preventDefault();
          setContourMora(state.contourCursor, 'L');
          return;
        }
        if (e.key === '2' || e.key === 'h' || e.key === 'H') {
          e.preventDefault();
          setContourMora(state.contourCursor, 'H');
          return;
        }
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          moveContourCursor(-1);
          return;
        }
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          moveContourCursor(+1);
          return;
        }
        if (e.key === 'Enter') {
          e.preventDefault();
          submitContour();
          return;
        }
      }
    });
  }

  async function setupFuriganaToggle() {
    const wrap = q('furiganaToggleLabel');
    const cb = q('furiganaToggle');
    if (!wrap || !cb) return;
    if (!state.furiganaPayload) {
      wrap.classList.remove('visible');
      return;
    }
    wrap.classList.add('visible');
    try {
      const resp = await window.authFetch('/api/users/preferences', { method: 'GET' });
      if (resp && resp.ok) {
        const body = await resp.json();
        const prefs = (body && (body.data || body).exercise_preferences) || {};
        state.furiganaEnabled = !!prefs.furigana_enabled;
      }
    } catch (_) {}
    cb.checked = state.furiganaEnabled;
    if (state.furiganaEnabled) state.furiganaUsedThisAttempt = true;
    on(cb, 'change', () => {
      state.furiganaEnabled = cb.checked;
      if (cb.checked) state.furiganaUsedThisAttempt = true;
      try {
        window.authFetch('/api/users/preferences', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ furigana_enabled: cb.checked }),
        });
      } catch (_) {}
      qsa('.word-token').forEach((el) => {
        const idx = parseInt(el.dataset.index, 10);
        const token = state.allTokens[idx];
        if (!token) return;
        const surfaceEl = el.querySelector('.word-surface');
        if (surfaceEl) surfaceEl.innerHTML = renderSurfaceHtml(token.surface);
      });
    });
  }

  function setupModeToggle() {
    qsa('#modeToggle button').forEach((btn) => {
      on(btn, 'click', () => {
        if (state.isComplete) return;
        const newMode = btn.dataset.mode;
        if (newMode === state.mode) return;
        state.mode = newMode;
        try {
          localStorage.setItem('pa_mode', newMode);
        } catch (e) {}
        qsa('#modeToggle button').forEach((b) =>
          b.classList.toggle('active', b.dataset.mode === newMode)
        );
        renderControls();
        if (state.mode === 'contour') {
          resetContourInput();
          renderScratchpad();
        } else {
          clearScratchpad();
        }
      });
    });
  }

  function renderControls() {
    const grid = q('controlsGrid');
    if (state.mode === 'quick') {
      grid.innerHTML = `
                <div class="control-item"><span class="control-key">←</span><span class="class-dot" style="background: var(--accent-heiban)"></span><span>${t('pitch.class.heiban', 'Heiban')}</span></div>
                <div class="control-item"><span class="control-key">↑</span><span class="class-dot" style="background: var(--accent-atamadaka)"></span><span>${t('pitch.class.atamadaka', 'Atamadaka')}</span></div>
                <div class="control-item"><span class="control-key">→</span><span class="class-dot" style="background: var(--accent-nakadaka)"></span><span>${t('pitch.class.nakadaka', 'Nakadaka')}</span></div>
                <div class="control-item"><span class="control-key">↓</span><span class="class-dot" style="background: var(--accent-odaka)"></span><span>${t('pitch.class.odaka', 'Odaka')}</span></div>`;
    } else {
      grid.innerHTML = `
                <div class="control-item"><span class="control-key">1 / L</span><span>${t('pitch.contour.low', 'LOW for current mora')}</span></div>
                <div class="control-item"><span class="control-key">2 / H</span><span>${t('pitch.contour.high', 'HIGH for current mora')}</span></div>
                <div class="control-item"><span class="control-key">← →</span><span>${t('pitch.contour.navigate', 'Move mora')}</span></div>
                <div class="control-item"><span class="control-key">Enter</span><span>${t('pitch.contour.submit_short', 'Submit')}</span></div>`;
    }
  }

  function completeGame() {
    state.isComplete = true;
    clearInterval(state.timerInterval);
    q('controlsHint').style.display = 'none';
    clearScratchpad();
    const total = state.playableTokens.length;
    const accuracy = total > 0 ? (Math.max(0, total - state.errorCount) / total) * 100 : 0;
    const timeSec = Math.floor((Date.now() - state.startTime) / 1000);
    submitResults(timeSec);
    showResults(accuracy, timeSec);
  }

  async function submitResults(timeSec) {
    try {
      const startedAtIso = state.startTime ? new Date(state.startTime).toISOString() : null;
      const finishedAtIso = new Date().toISOString();
      const resp = await window.authFetch(`/api/tests/${state.slug}/submit-pitch-accent`, {
        method: 'POST',
        body: JSON.stringify({
          correct_units: Math.max(0, state.playableTokens.length - state.errorCount),
          total_units: state.playableTokens.length,
          time_taken: timeSec,
          errors: state.errors.slice(0, 50),
          furigana_used: state.furiganaUsedThisAttempt,
          started_at: startedAtIso,
          finished_at: finishedAtIso,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.result) updateResultsWithElo(data.result);
      }
    } catch (err) {
      console.error('Pitch accent submit error:', err);
    }
  }

  function showResults(accuracy, timeSec) {
    let grade = 'poor',
      label = t('pitch.grade.poor', 'Keep practicing');
    if (accuracy >= 95) {
      grade = 'excellent';
      label = t('pitch.grade.excellent', 'Excellent!');
    } else if (accuracy >= 80) {
      grade = 'good';
      label = t('pitch.grade.good', 'Good');
    } else if (accuracy >= 60) {
      grade = 'fair';
      label = t('pitch.grade.fair', 'Fair');
    }

    const minutes = Math.floor(timeSec / 60);
    const seconds = timeSec % 60;
    const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    const html = `
            <div class="results-overlay">
                <div class="results-card">
                    <h2 class="h3">${escapeHtml(label)}</h2>
                    <div class="results-accuracy ${grade}">${accuracy.toFixed(1)}%</div>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">${t('pitch.accuracy_label', 'Accent accuracy')}</p>
                    <div class="results-stats">
                        <div class="stat-box"><div class="stat-value">${state.correctCount}/${state.playableTokens.length}</div><div class="stat-label">${t('pitch.stat.words', 'Words')}</div></div>
                        <div class="stat-box"><div class="stat-value">${timeStr}</div><div class="stat-label">${t('pitch.stat.time', 'Time')}</div></div>
                        <div class="stat-box"><div class="stat-value">${state.errorCount}</div><div class="stat-label">${t('pitch.stat.mistakes', 'Mistakes')}</div></div>
                        <div class="stat-box"><div class="stat-value" id="eloChangeDisplay">--</div><div class="stat-label">${t('pitch.stat.elo_change', 'ELO change')}</div></div>
                    </div>
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-primary flex-fill" type="button" data-session-next>
                            <span>${t('session.next_item', 'Next')}</span><i class="bi bi-arrow-right ms-1"></i>
                        </button>
                    </div>
                </div>
            </div>`;
    q('resultsContainer').innerHTML = html;
    const nextBtn = q('resultsContainer').querySelector('[data-session-next]');
    if (nextBtn) nextBtn.onclick = () => ctx.onComplete({ accuracy });
  }

  function updateResultsWithElo(result) {
    const eloEl = q('eloChangeDisplay');
    if (eloEl && result.user_elo_change) {
      const change = result.user_elo_change.change || 0;
      const sign = change >= 0 ? '+' : '';
      eloEl.textContent = sign + change;
      eloEl.className = 'stat-value ' + (change >= 0 ? 'text-success' : 'text-danger');
    }
  }

  function startTimer() {
    state.startTime = Date.now();
    const el = q('elapsedTime');
    state.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      const m = Math.floor(elapsed / 60),
        s = elapsed % 60;
      if (el) el.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }, 1000);
  }

  function showLoading(show) {
    const el = q('loadingOverlay');
    if (el) el.style.display = show ? 'flex' : 'none';
  }

  function showError(msg) {
    const err = q('errorState');
    if (err) {
      err.style.display = 'block';
      q('errorMessage').textContent = msg;
    }
    ['paHeader', 'passageContainer', 'controlsHint'].forEach((id) => {
      const el = q(id);
      if (el) el.style.display = 'none';
    });
  }
}

// ========================================================================
// MARKUP — styles come from the global static/css/styles.css (loaded by base.html)
// ========================================================================
const MARKUP = `
<div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="loading-spinner"><div class="spinner-icon"></div><p class="mb-0 text-slate-600" data-i18n="pitch.loading">Loading pitch accent data...</p></div>
</div>

<div id="errorState" class="container py-5" style="display:none;">
    <div class="alert alert-danger">
        <h2 class="h5"><i class="fas fa-exclamation-triangle me-2"></i><span data-i18n="pitch.error.title">Error</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>
</div>

<div class="pa-header" id="paHeader" style="display:none;">
    <div class="container py-3">
        <div class="row align-items-center g-2">
            <div class="col-12 col-md-auto">
                <h1 class="mb-0 h5"><i class="bi bi-music-note-beamed text-primary me-2"></i><span id="testTitle" data-i18n="pitch.title">Pitch Accent Trainer</span></h1>
            </div>
            <div class="col-12 col-md-auto ms-md-auto d-flex align-items-center gap-2 flex-wrap">
                <div class="mode-toggle" id="modeToggle">
                    <button type="button" data-mode="quick" class="active"><i class="bi bi-lightning-charge-fill me-1"></i><span data-i18n="pitch.mode.quick">Quick</span></button>
                    <button type="button" data-mode="contour"><i class="bi bi-graph-up me-1"></i><span data-i18n="pitch.mode.contour">Contour</span></button>
                </div>
                <span class="badge bg-primary" id="testLanguage"></span>
                <label class="furigana-toggle" id="furiganaToggleLabel" title="Furigana over kanji (halves ELO change)">
                    <input type="checkbox" id="furiganaToggle"><span>ふりがな</span>
                </label>
                <span class="text-slate-500"><i class="far fa-clock me-1"></i><span id="elapsedTime">00:00</span></span>
            </div>
        </div>
    </div>
    <div class="pa-progress-bar"><div class="pa-progress-fill" id="progressFill" style="width:0%"></div></div>
</div>

<div class="passage-container" id="passageContainer" style="display:none;">
    <div class="passage-grid" id="passageGrid"></div>
    <div id="scratchpadContainer"></div>
</div>

<div class="controls-hint" id="controlsHint" style="display:none;">
    <div class="controls-grid" id="controlsGrid"></div>
</div>

<div id="errorModalContainer"></div>
<div id="resultsContainer"></div>
`;
