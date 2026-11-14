(function () {
  'use strict';

  // Local wrapper that returns parsed JSON; delegates auth/refresh/device-restore
  // to base.html's window.authFetch.
  function authFetch(url) {
    return window.authFetch(url).then((r) => r.json());
  }

  const esc = escapeHtml;

  const LADDER_NAMES = {
    1: 'Phonetic/Orthographic',
    2: 'Definition Match',
    3: 'Cloze Completion',
    4: 'Morphology Slot',
    5: 'Collocation Gap',
    6: 'Semantic Discrimination',
    7: 'Spot Incorrect',
    8: 'Collocation Repair',
    9: 'Jumbled Sentence',
  };

  window.loadPreview = async function () {
    const senseId = document.getElementById('senseIdInput').value;
    const langId = document.getElementById('langSelect').value;
    if (!senseId) return;

    const container = document.getElementById('previewContent');
    container.innerHTML =
      '<p style="text-align:center;padding:40px;color:var(--text-secondary)">Loading...</p>';

    try {
      const data = await authFetch(
        `/api/admin/vocab/word/${senseId}/preview?language_id=${langId}`
      );
      if (data.status !== 'success') {
        container.innerHTML = `<p style="color:var(--danger)">Error: ${esc(data.error || 'Unknown error')}</p>`;
        return;
      }
      renderPreview(data, container);
    } catch (e) {
      container.innerHTML = `<p style="color:var(--danger)">Fetch error: ${esc(e.message)}</p>`;
    }
  };

  function renderPreview(data, container) {
    const w = data.word || {};
    const exercises = data.exercises || [];
    const assets = data.assets || {};

    let h = `<div class="word-card">
            <div class="word-title">${esc(w.lemma)}</div>
            <div class="word-meta">
                <span class="meta-badge">POS: ${esc(w.pos)}</span>
                <span class="meta-badge">Class: ${esc(w.semantic_class)}</span>
                <span class="meta-badge">Tier: ${esc(w.complexity_tier)}</span>
                ${w.ipa ? `<span class="meta-badge">IPA: ${esc(w.ipa)}</span>` : ''}
            </div>
            <p style="margin-top:12px;color:var(--text-secondary)">${esc(w.definition)}</p>
            <div style="margin-top:12px;display:flex;gap:8px;">`;

    ['prompt1_core', 'prompt2_exercises', 'prompt3_transforms'].forEach((at) => {
      const a = assets[at];
      if (a && a.is_valid)
        h += `<span class="asset-status valid"><i class="fas fa-check-circle"></i> ${at.replace('prompt', 'P').replace('_', ' ')}</span>`;
      else if (a)
        h += `<span class="asset-status invalid"><i class="fas fa-exclamation-circle"></i> ${at.replace('prompt', 'P').replace('_', ' ')}</span>`;
      else
        h += `<span class="asset-status missing"><i class="fas fa-minus-circle"></i> ${at.replace('prompt', 'P').replace('_', ' ')}</span>`;
    });
    h += '</div></div>';

    // Active levels
    const activeLevels = w.active_levels || [1, 2, 3, 4, 5, 6, 7, 8, 9];
    h += `<p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px">Active levels: ${activeLevels.join(', ')}</p>`;

    // Exercises by level
    const byLevel = {};
    exercises.forEach((ex) => {
      byLevel[ex.ladder_level] = ex;
    });

    activeLevels.forEach((lv) => {
      const ex = byLevel[lv];
      h += `<div class="level-section">
                <div class="level-header">
                    <div class="level-num">${lv}</div>
                    <div class="level-name">${LADDER_NAMES[lv] || 'Level ' + lv}</div>
                    ${ex ? '<span class="asset-status valid" style="margin-left:auto"><i class="fas fa-check"></i> Generated</span>' : '<span class="asset-status missing" style="margin-left:auto"><i class="fas fa-minus"></i> Missing</span>'}
                </div>`;

      if (ex) {
        h += `<div class="exercise-preview">${renderExercisePreview(ex, lv)}</div>`;
        h += `<div class="json-toggle" onclick="this.nextElementSibling.classList.toggle('show')">Toggle JSON</div>`;
        h += `<div class="json-block"><pre>${esc(JSON.stringify(ex.content, null, 2))}</pre></div>`;
      }

      h += '</div>';
    });

    // Raw assets toggle
    h += '<h2 style="margin-top:24px;font-size:16px;font-weight:600">Raw Assets</h2>';
    Object.entries(assets).forEach(([type, asset]) => {
      h += `<div class="level-section">
                <div class="json-toggle" style="margin-bottom:8px" onclick="this.nextElementSibling.classList.toggle('show')">${esc(type)} (${asset.model_used}) — click to expand</div>
                <div class="json-block"><pre>${esc(JSON.stringify(asset.content, null, 2))}</pre></div>
            </div>`;
    });

    container.innerHTML = h;
  }

  function renderExercisePreview(ex, level) {
    const c = ex.content || {};
    let h = `<div style="font-size:13px;color:var(--text-muted);margin-bottom:8px">${esc(ex.exercise_type)}</div>`;

    if (c.options && Array.isArray(c.options)) {
      // MCQ preview
      if (c.sentence_with_blank)
        h += `<p style="font-size:15px;margin-bottom:12px">${esc(c.sentence_with_blank)}</p>`;
      if (c.sentence) h += `<p style="font-size:15px;margin-bottom:12px">${esc(c.sentence)}</p>`;
      c.options.forEach((o) => {
        const text = typeof o === 'object' ? o.text || o : o;
        const isCorrect =
          text ===
          (c.correct_answer || c.correct || c.correct_definition || c.correct_collocate || '');
        h += `<div class="preview-option ${isCorrect ? 'correct' : 'distractor'}">${isCorrect ? '<i class="fas fa-check me-2" style="color:var(--success)"></i>' : ''} ${esc(text)}</div>`;
      });
      if (c.explanation)
        h += `<div style="margin-top:8px;font-size:13px;color:var(--text-secondary)"><em>${esc(c.explanation)}</em></div>`;
    } else if (c.sentences && Array.isArray(c.sentences)) {
      // Sentence-based preview (L6, L7)
      c.sentences.forEach((s) => {
        const isCorrect = level === 7 ? !s.is_correct : s.is_correct;
        h += `<div class="preview-option ${isCorrect ? 'correct' : 'distractor'}">${esc(s.text)}</div>`;
      });
    } else if (c.sentence_with_error) {
      h += `<p style="font-size:15px">${esc(c.sentence_with_error)}</p>`;
      h += `<div style="margin-top:8px;font-size:14px">Error: <strong style="color:var(--danger)">${esc(c.error_word)}</strong> &rarr; <strong style="color:var(--success)">${esc(c.correct_word)}</strong></div>`;
    } else if (c.original_sentence) {
      h += `<p style="font-size:15px">${esc(c.original_sentence)}</p>`;
      if (c.chunks)
        h += `<p style="font-size:13px;color:var(--text-secondary)">Chunks: ${c.chunks.join(' | ')}</p>`;
    } else {
      h += `<p style="font-size:13px;color:var(--text-muted)">Preview not available for this type</p>`;
    }

    return h;
  }
})();
