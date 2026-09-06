/* Word List — upload words to the vocabulary-ladder watchlist and track
 * their status (ladder generation + matched-test sweeps).
 *
 * Backend contract (routes/word_list_import.py):
 *   POST /api/word-list/submit  { words: string[], language: 'en'|'zh'|'ja' }
 *     -> 202 { status: 'success', upload_batch_id }. Fields are flat at the
 *     top level (utils.responses.api_success spreads `data`, never nests it
 *     under a `data` key) -- processing continues in a background thread
 *     and is NOT reflected in this response.
 *   GET  /api/word-list/watchlist
 *     -> 200 { status: 'success', watchlist: [{ id, sense_id, lemma,
 *              language_id, upload_batch_id, created_at,
 *              ladder_exercises_generated, last_matched_test_id,
 *              last_matched_at, active }, ...] }
 *     `lemma` is the actual word text (e.g. "拖延"), resolved server-side via
 *     sense_id -> dim_word_senses.vocab_id -> dim_vocabulary.lemma; it may be
 *     null if that join can't resolve (deleted sense, orphaned row), in
 *     which case the "Word" column falls back to "Sense #<id>".
 *     Every active/matched row for the authenticated user, in no guaranteed
 *     order, and NOT filterable by batch server-side -- "this upload's
 *     rows" is therefore a client-side filter on upload_batch_id.
 *
 * Known contract gaps (worked around here, NOT fixed by changing
 * word_list_import.py -- see the Step 8 task notes / final report):
 *   - last_matched_test_id has no slug attached. Resolved here via the
 *     existing public GET /api/tests/test/<identifier> lookup (accepts a
 *     UUID and returns { test_data: { slug, ... } }), cached per test_id,
 *     purely so a matched row can link somewhere real without adding
 *     anything to word_list_import.py's response.
 *   - A resubmitted word that already has a watchlist row from an earlier
 *     upload gets NO new row under the new upload_batch_id (the backend
 *     silently skips the insert -- see upload_handler.py's
 *     WATCHLIST_STATUS_ALREADY_WATCHED path). That means "rows for this
 *     batch" can permanently undercount "words submitted in this batch" --
 *     see the settle heuristic in evaluateBatchProgress() below.
 *
 * Polling strategy: the watchlist is a long-lived, ever-growing list (the
 * recurring sweep cron keeps updating last_matched_test_id long after any
 * given upload finishes), not a one-shot job result -- so polling never
 * fully *stops* while this page stays open. Instead it changes cadence:
 *   - FAST_POLL_MS while a just-submitted batch is still "settling" (its
 *     row count is still growing between polls) -- surfaces ladder
 *     generation finishing word-by-word in near-real-time.
 *   - SLOW_POLL_MS once the batch stops growing for one full fast cycle, OR
 *     once FAST_POLL_MAX_MS elapses as a safety net -- a word can
 *     legitimately never produce a new row at all (see the
 *     already-watched case above), so an exact "N of N done" condition
 *     would hang forever in that case. The slow interval keeps the whole
 *     table (including older batches' newly-arriving matches) gently
 *     fresh without hammering the server on an indefinitely-open tab.
 *   - Paused entirely while the tab is hidden (visibilitychange), and
 *     refreshed immediately on becoming visible again.
 */
(function () {
  'use strict';

  const FAST_POLL_MS = 5000;
  const SLOW_POLL_MS = 60000;
  const FAST_POLL_MAX_MS = 5 * 60 * 1000; // 5 min safety net

  const el = {};
  let pollTimer = null;
  let currentIntervalMs = null;
  let activeBatch = null; // { id, lastRowCount, startedAt }
  const testLinkCache = new Map(); // test_id -> slug string, or null if unresolved

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  function escapeHtml(s) {
    if (window.LinguaUtils && window.LinguaUtils.escapeHtml) {
      return window.LinguaUtils.escapeHtml(String(s == null ? '' : s));
    }
    return String(s == null ? '' : s);
  }

  async function init() {
    cacheEls();
    try {
      if (window.LinguaI18n && window.LinguaI18n.init) await window.LinguaI18n.init();
    } catch (e) {
      /* i18n is best-effort; fall back to embedded defaults */
    }
    try {
      if (window.LinguaMetadata && window.LinguaMetadata.load) await window.LinguaMetadata.load();
    } catch (e) {
      /* language metadata is best-effort; language column falls back to '?' */
    }

    wireLanguagePicker();
    wireForm();
    await loadWatchlist();
    schedulePoll(SLOW_POLL_MS);

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        clearPoll();
      } else {
        loadWatchlist();
        schedulePoll(currentIntervalMs || SLOW_POLL_MS);
      }
    });
  }

  function cacheEls() {
    [
      'wlWords',
      'wlLangOptions',
      'wlForm',
      'wlSubmitBtn',
      'wlStatus',
      'wlLoading',
      'wlError',
      'wlEmpty',
      'wlTable',
      'wlTableBody',
    ].forEach(function (id) {
      el[id] = document.getElementById(id);
    });
  }

  function selectedLanguage() {
    const chip = el.wlLangOptions.querySelector('.wl-lang-chip.selected');
    return chip ? chip.dataset.lang : null;
  }

  function wireLanguagePicker() {
    const chips = el.wlLangOptions.querySelectorAll('.wl-lang-chip');
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(function (c) {
          c.classList.remove('selected');
        });
        chip.classList.add('selected');
      });
    });

    // Default the picker to the site-wide study language (same source as
    // base.html::applyLanguageGating) so a returning user doesn't have to
    // re-pick a language they've already chosen elsewhere in the app.
    const storedId = parseInt(localStorage.getItem('selectedLanguageId'), 10);
    const cache = window.LinguaMetadata && window.LinguaMetadata._cache;
    if (storedId && cache) {
      const lang = (cache.languages || []).find(function (l) {
        return l.id === storedId;
      });
      if (lang && lang.language_code) {
        const match = el.wlLangOptions.querySelector(
          '.wl-lang-chip[data-lang="' + lang.language_code + '"]'
        );
        if (match) match.classList.add('selected');
      }
    }
  }

  function setStatus(message, kind) {
    el.wlStatus.textContent = message || '';
    el.wlStatus.className = 'wl-status' + (kind ? ' ' + kind : '');
  }

  function wireForm() {
    el.wlForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      const raw = el.wlWords.value || '';
      const words = raw
        .split('\n')
        .map(function (w) {
          return w.trim();
        })
        .filter(function (w) {
          return w.length > 0;
        });

      if (!words.length) {
        setStatus(tr('word_list.error_empty'), 'error');
        return;
      }

      const language = selectedLanguage();
      if (!language) {
        setStatus(tr('word_list.error_no_language'), 'error');
        return;
      }

      el.wlSubmitBtn.disabled = true;
      el.wlSubmitBtn.textContent = tr('word_list.submitting');
      setStatus('', null);

      try {
        const resp = await window.authFetch('/api/word-list/submit', {
          method: 'POST',
          body: JSON.stringify({ words: words, language: language }),
        });
        const data = await resp.json().catch(function () {
          return {};
        });

        if (!resp.ok) {
          setStatus((data && data.error) || tr('word_list.error_generic'), 'error');
          return;
        }

        // Hand-off successful -- clear the textarea and let the watchlist
        // table (via polling) reveal progress; there is nothing more this
        // response can tell us (see module docstring).
        el.wlWords.value = '';
        setStatus(tr('word_list.processing'), 'processing');

        activeBatch = { id: data.upload_batch_id, lastRowCount: 0, startedAt: Date.now() };
        await loadWatchlist();
        schedulePoll(FAST_POLL_MS);
      } catch (err) {
        console.error('word-list submit failed:', err);
        setStatus(tr('word_list.error_generic'), 'error');
      } finally {
        el.wlSubmitBtn.disabled = false;
        el.wlSubmitBtn.textContent = tr('word_list.submit');
      }
    });
  }

  function schedulePoll(intervalMs) {
    clearPoll();
    currentIntervalMs = intervalMs;
    pollTimer = setInterval(loadWatchlist, intervalMs);
  }

  function clearPoll() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function loadWatchlist() {
    let resp;
    try {
      resp = await window.authFetch('/api/word-list/watchlist');
    } catch (e) {
      showError(tr('word_list.error_load'));
      return;
    }
    if (!resp || !resp.ok) {
      showError(tr('word_list.error_load') + (resp ? ' (' + resp.status + ')' : ''));
      return;
    }
    const data = await resp.json().catch(function () {
      return {};
    });
    const rows = data.watchlist || [];

    el.wlLoading.style.display = 'none';
    el.wlError.style.display = 'none';
    evaluateBatchProgress(rows);
    render(rows);
    await resolveMatchLinks(rows);
  }

  // Decides whether the just-submitted batch is still "settling" (see the
  // module docstring's Polling strategy section for the full reasoning).
  function evaluateBatchProgress(rows) {
    if (!activeBatch) return;

    const batchRowCount = rows.filter(function (r) {
      return r.upload_batch_id === activeBatch.id;
    }).length;
    const stillGrowing = batchRowCount > activeBatch.lastRowCount;
    activeBatch.lastRowCount = batchRowCount;

    const elapsed = Date.now() - activeBatch.startedAt;
    const settled = (!stillGrowing && batchRowCount > 0) || elapsed >= FAST_POLL_MAX_MS;

    if (settled) {
      setStatus('', null);
      activeBatch = null;
      if (currentIntervalMs !== SLOW_POLL_MS) schedulePoll(SLOW_POLL_MS);
    } else if (currentIntervalMs !== FAST_POLL_MS) {
      schedulePoll(FAST_POLL_MS);
    }
  }

  function showError(message) {
    el.wlLoading.style.display = 'none';
    el.wlError.textContent = message;
    el.wlError.style.display = 'block';
  }

  function codeForLanguageId(languageId) {
    const cache = window.LinguaMetadata && window.LinguaMetadata._cache;
    if (!cache) return '';
    const lang = (cache.languages || []).find(function (l) {
      return l.id === languageId;
    });
    return lang ? lang.language_code : '';
  }

  function languageDisplay(languageId) {
    const flag =
      window.LinguaUtils && window.LinguaUtils.getLanguageFlag
        ? window.LinguaUtils.getLanguageFlag(codeForLanguageId(languageId))
        : '';
    const name =
      window.LinguaMetadata && window.LinguaMetadata.getNativeNameById
        ? window.LinguaMetadata.getNativeNameById(languageId)
        : '';
    return (flag ? escapeHtml(flag) + ' ' : '') + escapeHtml(name || '?');
  }

  function render(rows) {
    if (!rows.length) {
      el.wlEmpty.style.display = 'block';
      el.wlTable.style.display = 'none';
      return;
    }
    el.wlEmpty.style.display = 'none';
    el.wlTable.style.display = '';

    // Server order is unspecified -- sort newest-first for a stable,
    // sensible default display.
    const sorted = rows.slice().sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    });

    el.wlTableBody.innerHTML = sorted.map(buildRow).join('');
  }

  function buildRow(row) {
    const isNew = Boolean(activeBatch) && row.upload_batch_id === activeBatch.id;
    const ladderBadge = row.ladder_exercises_generated
      ? '<span class="wl-badge ready">' + escapeHtml(tr('word_list.ladder_ready')) + '</span>'
      : '<span class="wl-badge pending">' + escapeHtml(tr('word_list.ladder_pending')) + '</span>';

    let matchCell;
    if (row.active === false) {
      matchCell =
        '<span class="wl-badge inactive">' + escapeHtml(tr('word_list.inactive')) + '</span>';
    } else if (row.last_matched_test_id) {
      const slug = testLinkCache.get(row.last_matched_test_id);
      matchCell =
        '<span class="wl-badge matched">' +
        escapeHtml(tr('word_list.match_found')) +
        '</span>' +
        (slug
          ? ' <a href="/test/' +
            encodeURIComponent(slug) +
            '">' +
            escapeHtml(tr('word_list.view_test')) +
            '</a>'
          : '');
    } else {
      matchCell =
        '<span class="wl-badge watching">' + escapeHtml(tr('word_list.watching')) + '</span>';
    }

    const uploaded =
      window.LinguaUtils && window.LinguaUtils.formatDate
        ? window.LinguaUtils.formatDate(row.created_at)
        : escapeHtml(row.created_at || '');

    const wordLabel = row.lemma
      ? escapeHtml(row.lemma)
      : escapeHtml(tr('word_list.sense_label')) + ' #' + escapeHtml(row.sense_id);

    return (
      '<tr class="' +
      (isNew ? 'wl-row-new' : '') +
      '">' +
      '<td>' +
      wordLabel +
      '</td>' +
      '<td>' +
      languageDisplay(row.language_id) +
      '</td>' +
      '<td>' +
      ladderBadge +
      '</td>' +
      '<td>' +
      matchCell +
      '</td>' +
      '<td>' +
      uploaded +
      '</td>' +
      '</tr>'
    );
  }

  // Resolves last_matched_test_id -> slug via the existing, public
  // GET /api/tests/test/<identifier> lookup (accepts a UUID and returns
  // { test_data: { slug, ... } }) so matched rows link somewhere real,
  // without adding anything to word_list_import.py's response contract.
  // Cached per test_id (a match's slug never changes); re-renders once any
  // new id resolves.
  async function resolveMatchLinks(rows) {
    const idsToResolve = Array.from(
      new Set(
        rows
          .map(function (r) {
            return r.last_matched_test_id;
          })
          .filter(function (id) {
            return id && !testLinkCache.has(id);
          })
      )
    );
    if (!idsToResolve.length) return;

    await Promise.all(
      idsToResolve.map(async function (testId) {
        try {
          const resp = await window.authFetch('/api/tests/test/' + encodeURIComponent(testId));
          if (resp.ok) {
            const data = await resp.json();
            const slug = data && data.test_data && data.test_data.slug;
            testLinkCache.set(testId, slug || null);
          } else {
            testLinkCache.set(testId, null);
          }
        } catch (e) {
          testLinkCache.set(testId, null);
        }
      })
    );

    render(rows);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
