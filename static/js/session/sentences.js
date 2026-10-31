// static/js/session/sentences.js
// Sentence spans for the test preview / prestudy Produce stage (TASK-911, ADR-037).
//
// The server owns sentence boundaries (`test_sentences`, served by
// GET /api/tests/<slug>/sentences); the preview, the passage cloze and the
// Produce window must all agree on them. This module fetches those rows and
// renders a transcript as per-sentence blocks, each with an optional L1
// reference line that is hidden by default (a toggle reveals it) and NEVER
// rendered in `produce` mode — the learner has to reproduce from the L1 side
// without seeing the gold.
//
// A test with no rows yet (404, empty list, network error) falls back to the
// client split on 。！？!? with a console.warn — never a blank preview.

const TERMINATORS = '。！？!?';
const CLIENT_SPLIT_RE = new RegExp(
  '[^' + TERMINATORS + ']+[' + TERMINATORS + ']+|[^' + TERMINATORS + ']+$',
  'g'
);

export const SENTENCE_CLASS = 'll-sentence';
export const SENTENCE_TEXT_CLASS = 'll-sentence-text';
export const SENTENCE_REF_CLASS = 'll-sentence-ref';

/**
 * Split `text` on CJK/Latin terminators, keeping terminators attached and
 * recording character spans into the ORIGINAL string (so spans line up with
 * `transcript.slice`). Leading/trailing whitespace is trimmed off each span.
 */
export function clientSplitSentences(text) {
  const src = String(text == null ? '' : text);
  const out = [];
  CLIENT_SPLIT_RE.lastIndex = 0;
  let m;
  while ((m = CLIENT_SPLIT_RE.exec(src)) !== null) {
    let s = m.index;
    let e = m.index + m[0].length;
    while (s < e && /\s/.test(src[s])) s++;
    while (e > s && /\s/.test(src[e - 1])) e--;
    if (s >= e) continue;
    out.push({
      idx: out.length,
      l2_text: src.slice(s, e),
      char_start: s,
      char_end: e,
      token_start: null,
      token_end: null,
      reference: null,
    });
  }
  return out;
}

/**
 * Normalise the endpoint payload ({sentences:[...]}, possibly wrapped in
 * {data:{...}}) into rows. Returns null when there are no rows. `transcript`
 * fills `l2_text` from char spans when the server withheld it (produce mode)
 * and the client legitimately holds the transcript (reading test).
 */
export function normalizeServerSentences(payload, transcript) {
  const body = payload && payload.data ? payload.data : payload;
  const rows = body && Array.isArray(body.sentences) ? body.sentences : null;
  if (!rows || !rows.length) return null;
  const src = transcript == null ? null : String(transcript);
  return rows
    .map((r, i) => {
      const cs = Number.isInteger(r.char_start) ? r.char_start : null;
      const ce = Number.isInteger(r.char_end) ? r.char_end : null;
      let text = typeof r.l2_text === 'string' ? r.l2_text : null;
      if (text == null && src != null && cs != null && ce != null) text = src.slice(cs, ce);
      return {
        idx: Number.isInteger(r.idx) ? r.idx : i,
        l2_text: text,
        char_start: cs,
        char_end: ce,
        token_start: Number.isInteger(r.token_start) ? r.token_start : null,
        token_end: Number.isInteger(r.token_end) ? r.token_end : null,
        reference: r.reference && r.reference.l1_text ? r.reference : null,
      };
    })
    .sort((a, b) => a.idx - b.idx);
}

/**
 * GET /api/tests/<slug>/sentences. Resolves to the normalised rows, or null
 * (with a console.warn) when the endpoint 404s, errors or returns no rows.
 * `mode: 'produce'` is passed through so the server applies its withholding
 * rule; `l1` is optional (server defaults to the learner's native language).
 */
export async function fetchTestSentences(slug, opts) {
  const o = opts || {};
  const fetchImpl = o.fetchImpl || window.authFetch || window.fetch;
  const params = [];
  if (o.l1) params.push('l1=' + encodeURIComponent(o.l1));
  if (o.mode) params.push('mode=' + encodeURIComponent(o.mode));
  const url =
    `/api/tests/${encodeURIComponent(slug)}/sentences` +
    (params.length ? '?' + params.join('&') : '');
  let res;
  try {
    res = await fetchImpl(url);
  } catch (e) {
    console.warn('sentences: fetch failed, falling back to client split', e);
    return null;
  }
  if (!res || !res.ok) {
    console.warn(
      `sentences: endpoint returned ${res ? res.status : 'no response'}; falling back to client split`
    );
    return null;
  }
  let payload;
  try {
    payload = await res.json();
  } catch (e) {
    console.warn('sentences: invalid JSON; falling back to client split', e);
    return null;
  }
  const rows = normalizeServerSentences(payload, o.transcript);
  if (!rows) {
    console.warn('sentences: no sentence rows for this test; falling back to client split');
    return null;
  }
  return rows;
}

/**
 * Server rows when present, else the client split of `transcript`.
 * Returns {sentences, source: 'server'|'client'}.
 */
export function resolveSentences(transcript, serverRows) {
  if (serverRows && serverRows.length) return { sentences: serverRows, source: 'server' };
  if (!serverRows) {
    // fetchTestSentences already warned when it returned null; this covers
    // callers that never had an endpoint to ask.
    console.warn('sentences: using client split on 。！？!?');
  }
  return { sentences: clientSplitSentences(transcript), source: 'client' };
}

/** True when any sentence carries an L1 reference and the mode allows showing it. */
export function hasVisibleReferences(sentences, mode) {
  if (mode === 'produce') return false;
  return (sentences || []).some((s) => s && s.reference && s.reference.l1_text);
}

/** True when every sentence has a server token span (so token-map rendering is possible). */
export function hasTokenSpans(sentences) {
  return (
    Array.isArray(sentences) &&
    sentences.length > 0 &&
    sentences.every((s) => Number.isInteger(s.token_start) && Number.isInteger(s.token_end))
  );
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Render `sentences` into `containerEl` as per-sentence blocks.
 *
 * opts:
 *   mode        — 'produce' suppresses every reference line.
 *   renderText  — (l2_text) => HTML string for the sentence body (default: escaped text).
 *   tokenMap    — tests.vocab_token_map ([[surface, senseId], ...]); when given and
 *                 every sentence has a token span, bodies are built from the
 *                 map with `.word-clickable` spans (the post-submit view).
 *   showReferences — initial visibility of the reference lines (default false).
 */
export function renderSentenceBlocks(containerEl, sentences, opts) {
  const o = opts || {};
  const produce = o.mode === 'produce';
  const useTokens = Array.isArray(o.tokenMap) && o.tokenMap.length && hasTokenSpans(sentences);
  containerEl.innerHTML = '';
  (sentences || []).forEach((s) => {
    const block = document.createElement('div');
    block.className = SENTENCE_CLASS;
    block.dataset.sentenceIdx = String(s.idx);

    const body = document.createElement('span');
    body.className = SENTENCE_TEXT_CLASS;
    if (useTokens) {
      o.tokenMap.slice(s.token_start, s.token_end).forEach(([text, senseId]) => {
        if (senseId) {
          const span = document.createElement('span');
          span.className = 'word-clickable';
          span.textContent = text;
          span.dataset.senseId = String(senseId);
          span.setAttribute('role', 'button');
          span.setAttribute('tabindex', '0');
          body.appendChild(span);
        } else {
          body.appendChild(document.createTextNode(text));
        }
      });
    } else {
      const text = s.l2_text == null ? '' : s.l2_text;
      body.innerHTML = typeof o.renderText === 'function' ? o.renderText(text) : escapeHtml(text);
    }
    block.appendChild(body);

    if (!produce && s.reference && s.reference.l1_text) {
      const ref = document.createElement('div');
      ref.className = SENTENCE_REF_CLASS;
      ref.textContent = s.reference.l1_text;
      ref.hidden = !o.showReferences;
      block.appendChild(ref);
    }
    containerEl.appendChild(block);
  });
}

/** Show/hide every reference line under `containerEl`. Returns the new visibility. */
export function setReferencesVisible(containerEl, visible) {
  containerEl.querySelectorAll('.' + SENTENCE_REF_CLASS).forEach((el) => {
    el.hidden = !visible;
  });
  return !!visible;
}
