/*
 * Test prestudy page (/test/<slug>/prestudy).
 *
 * Spec: wiki/features/test-prestudy.md. Ported from the reviewed demo
 * (wiki/demos/test-prestudy-demo.html), wired to:
 *   GET  /api/tests/<slug>/prestudy           study payload (no question text or answers)
 *   POST /api/tests/<slug>/prestudy/evidence  word-test evidence, once, at the end
 *
 * Flow: Preview (passage, key words, popover) -> Word prime (typed reading ->
 * meaning -> typed reading -> reverse meaning -> passage cloze -> two ladder
 * exercises, interleaved, about five exposures per word) -> readiness check
 * (five typed readings; one extra round if under 80%) -> Ready -> the test.
 *
 * "Take the test" leaves sessionStorage['prestudy:<slug>'] so test.html sends
 * prestudied: true on the first submit; the RPC then applies the 0.5x ELO
 * factor on a first attempt. "Skip" never sets the marker.
 */
(function () {
  'use strict';

  // ---------- constants ----------
  const ZH = 1, EN = 2, JA = 3;
  const LANGCODE = { 1: 'zh', 2: 'en', 3: 'ja' };
  const SENT_END = /[。！？!?]$/;
  const SLIP = 0.05, GUESS = 0.25, TRANSIT = 0.05;          // word-test BKT (knowledge_service)
  const PRIOR_K = 1.5, PRIOR_B = Math.log(0.85 / 0.15);     // zipf prior (recommended_tests_ranked)
  const MARKER_PREFIX = 'prestudy:';

  const STAGES = [
    { k: 'read_typed',  label: 'prestudy.stage_reading',  ask: 'prestudy.ask_read' },
    { k: 'def_mc',      label: 'prestudy.stage_meaning',  ask: 'prestudy.ask_def' },
    { k: 'read_typed2', label: 'prestudy.stage_reading',  ask: 'prestudy.ask_read_again' },
    { k: 'rev_mc',      label: 'prestudy.stage_meaning',  ask: 'prestudy.ask_rev' },
    { k: 'cloze_mc',    label: 'prestudy.stage_use',      ask: 'prestudy.ask_cloze' },
    { k: 'ex_use',      label: 'prestudy.stage_practice', ask: 'prestudy.ask_exercise' },
    { k: 'ex_judge',    label: 'prestudy.stage_practice', ask: 'prestudy.ask_exercise' },
  ];

  let D = null;              // payload from the API
  const S = {
    slug: null, testType: 'reading',
    test: null, glossLang: null, ability: 5.0, hl: true, aids: 'unknown',
    know: {}, snapshot: 0, shown: new Set(),
    quiz: null, prime: null, ready: null, phase: 'prime',
    answers: [], exAnswers: [], evidencePosted: false, exUsed: new Set(), step: 1,
    // 'prime' before the attempt; 'followup' after it (words behind wrong answers)
    mode: 'prime', trigger: 'opt_in', planOverride: null, block: null, returnTo: null,
    droppedToday: 0, sessionId: null, timer: null, followSenses: [],
  };
  const FOLLOWUP_STAGES = ['read_typed', 'def_mc', 'cloze_mc'];
  const FOLLOWUP_MAX_WORDS = 5;
  const LIGHT_STAGES = ['read_typed', 'def_mc'];   // the one-minute warm-up for 5-25% unknown

  const $ = (id) => document.getElementById(id);
  const T = (key, params) => (window.LinguaI18n ? window.LinguaI18n.t(key, params) : key);

  // ---------- knowledge model ----------
  function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }
  function priorP(sense) { if (!sense || sense.freq == null) return 0.3; return sigmoid(PRIOR_K * (sense.freq - S.ability) + PRIOR_B); }
  function basePKnown(sid) { const k = D.knowledge[sid]; return k ? k.p : priorP(D.senses[sid]); }
  function pNow(sid) { return S.know[sid] != null ? S.know[sid] : basePKnown(sid); }
  function status(p) { return p < 0.2 ? 'unknown' : p < 0.5 ? 'encountered' : p < 0.75 ? 'learning' : p < 0.9 ? 'probably_known' : 'known'; }
  function bktUpdateIdk(p) { const post = (p * SLIP) / (p * SLIP + (1 - p)); return post + (1 - post) * TRANSIT; }
  function bktUpdate(p, correct) {
    const post = correct ? (p * (1 - SLIP)) / (p * (1 - SLIP) + (1 - p) * GUESS) : (p * SLIP) / (p * SLIP + (1 - p) * (1 - GUESS));
    return post + (1 - post) * TRANSIT;
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function shuffle(arr) { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  function gloss(sid) {
    const s = D.senses[sid]; if (!s) return {};
    return s.glosses[String(S.glossLang)] || s.glosses[String(S.test.language_id)] || Object.values(s.glosses)[0] || {};
  }
  function tokenMap() { return S.test.vocab_token_map || []; }

  // ---------- analysis ----------
  function analyse() {
    const t = S.test, occ = {};
    for (const [, sid] of tokenMap()) { if (sid) occ[sid] = (occ[sid] || 0) + 1; }
    const qSenses = new Set(); for (const q of D.questions) (q.sense_ids || []).forEach((s) => qSenses.add(String(s)));
    const senses = (t.vocab_sense_ids || []).map(String).filter((s) => D.senses[s]);
    const rows = senses.map((sid) => { const p = pNow(sid); return { sid, p, st: status(p), occ: occ[sid] || 0, inQ: qSenses.has(sid), freq: D.senses[sid].freq }; });
    const unknown = rows.filter((r) => r.p < 0.5).length;
    const share = senses.length ? unknown / senses.length : 0;
    // key words: question-linked, then most frequent in the passage, then rarer words first
    const ranked = rows.filter((r) => r.p < 0.5).sort((a, b) => (b.inQ - a.inQ) || (b.occ - a.occ) || ((a.freq == null ? 9 : a.freq) - (b.freq == null ? 9 : b.freq)));
    return { rows, unknown, share, ranked, n: senses.length };
  }
  function trigger(share) {
    if (share > 0.25) return { mode: 'full', cls: 'bad', label: T('prestudy.mode_full') };
    if (share >= 0.05) return { mode: 'light', cls: 'ok', label: T('prestudy.mode_light') };
    return { mode: 'none', cls: 'ok', label: T('prestudy.mode_none') };
  }
  function exercisesFor(sid) { return (D.exercises && D.exercises[String(sid)]) || []; }
  function estMinutes(a) {
    if (currentPlanMode() === 'light') return 1;
    const k = Math.min(8, a.unknown);
    const ex = a.ranked.slice(0, k).filter((r) => exercisesFor(r.sid).length).length;
    return Math.min(10, Math.max(2, Math.round((60 + k * 5 * 8 + ex * 2 * 20 + 5 * 8) / 60)));
  }
  function sentences() {
    const out = []; let cur = [];
    tokenMap().forEach((tok, i) => { cur.push(i); if (SENT_END.test(tok[0])) { out.push(cur); cur = []; } });
    if (cur.length) out.push(cur);
    return out;
  }
  function passageSentenceFor(sid, blank) {
    const tm = tokenMap();
    for (const idxs of sentences()) {
      if (idxs.some((i) => String(tm[i][1]) === sid)) {
        return idxs.map((i) => { const [surf, s] = tm[i]; return String(s) === sid ? (blank ? '<span class="ps-blank">＿＿＿</span>' : `<mark>${esc(surf)}</mark>`) : esc(surf); }).join('');
      }
    }
    return '';
  }

  // ---------- reading aids (furigana / pinyin) ----------
  const PY_VOWELS = { a: 'āáǎàa', e: 'ēéěèe', i: 'īíǐìi', o: 'ōóǒòo', u: 'ūúǔùu', v: 'ǖǘǚǜü' };
  function toneMark(syl, tone) {
    syl = String(syl).toLowerCase().replace('u:', 'v'); const t = (tone >= 1 && tone <= 4) ? tone - 1 : 4;
    const put = (ch) => syl.replace(ch, PY_VOWELS[ch][t]);
    if (syl.includes('a')) return put('a'); if (syl.includes('e')) return put('e'); if (syl.includes('ou')) return put('o');
    for (let i = syl.length - 1; i >= 0; i--) { if (PY_VOWELS[syl[i]]) return syl.slice(0, i) + PY_VOWELS[syl[i]][t] + syl.slice(i + 1); }
    return syl;
  }
  function charAids() {
    const t = S.test, n = (t.transcript || '').length, out = new Array(n).fill(null);
    if (t.language_id === JA && t.furigana_payload && Array.isArray(t.furigana_payload.transcript)) {
      let pos = 0, gid = 0;
      for (const tok of t.furigana_payload.transcript) {
        const text = tok.base || tok.text || '';
        if (tok.kind === 'ruby') {
          const segs = (tok.segments && tok.segments.length ? tok.segments : [{ base: tok.base, rt: tok.rt }]);
          let p = pos;
          for (const sg of segs) { const b = sg.base || ''; if (sg.rt) { gid++; for (let k = 0; k < b.length; k++) out[p + k] = { gid, rt: sg.rt, start: p, end: p + b.length }; } p += b.length; }
        }
        pos += text.length;
      }
    } else if (t.language_id === ZH && Array.isArray(t.pinyin_payload)) {
      t.pinyin_payload.forEach((c, i) => { if (i < n && c && !c.is_punctuation && c.pinyin_text) out[i] = { gid: i + 1, rt: toneMark(c.pinyin_text, c.context_tone != null ? c.context_tone : c.base_tone), start: i, end: i + 1 }; });
    }
    return out;
  }
  function tokenWithAids(surf, start, aids) {
    let html = '', i = 0;
    while (i < surf.length) {
      const a = aids[start + i];
      if (a && a.start === start + i && a.end <= start + surf.length) { html += `<ruby>${esc(surf.slice(i, i + (a.end - a.start)))}<rt>${esc(a.rt)}</rt></ruby>`; i += a.end - a.start; }
      else { html += esc(surf[i]); i++; }
    }
    return html;
  }

  // ---------- reading graders ----------
  function readingParts(s) {
    if (!s || !s.reading) return null;
    const m = /^(.*?)\s*\((.*)\)\s*$/.exec(s.reading);           // zh: "mù tou (mu4 tou5)"
    return { shown: (m ? m[1] : s.reading).trim(), numbered: m ? m[2].trim() : null };
  }
  const KANA = { 'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o', 'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko', 'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so', 'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to', 'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no', 'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho', 'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo', 'や': 'ya', 'ゆ': 'yu', 'よ': 'yo', 'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro', 'わ': 'wa', 'を': 'o', 'ん': 'n', 'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go', 'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo', 'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do', 'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo', 'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po', 'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o', 'ゔ': 'vu' };
  const KANA_Y = { 'ゃ': 'ya', 'ゅ': 'yu', 'ょ': 'yo' };
  function kataToHira(s) { return s.replace(/[\u30a1-\u30f6]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60)); }
  function kanaToRomaji(k) {
    k = kataToHira(k); let out = '';
    for (let i = 0; i < k.length; i++) {
      const c = k[i], n = k[i + 1];
      if (c === 'っ') { out += n && KANA[n] ? KANA[n][0] : ''; continue; }
      if (c === 'ー') { out += out.slice(-1); continue; }
      if (KANA[c] && n && KANA_Y[n]) { const base = KANA[c]; out += (base.length === 3 ? base.slice(0, 2) : base[0]) + (base === 'shi' || base === 'chi' || base === 'ji' ? KANA_Y[n].slice(1) : KANA_Y[n]); i++; continue; }
      out += KANA[c] || c;
    }
    return out;
  }
  function normRomaji(r) {
    r = String(r).toLowerCase().normalize('NFC').replace(/ā/g, 'aa').replace(/ī/g, 'ii').replace(/ū/g, 'uu').replace(/ē/g, 'ee').replace(/ō/g, 'oo').replace(/ô/g, 'oo').replace(/û/g, 'uu');
    r = r.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[\s'’-]/g, '');
    r = r.replace(/sy([auo])/g, 'sh$1').replace(/ty([auo])/g, 'ch$1').replace(/(?:zy|jy)([auo])/g, 'j$1').replace(/cy([auo])/g, 'ch$1');
    r = r.replace(/si/g, 'shi').replace(/ti/g, 'chi').replace(/tu/g, 'tsu').replace(/(?<![sc])hu/g, 'fu').replace(/zi/g, 'ji').replace(/dzu|du/g, 'zu').replace(/nn([aiueo])/g, 'n$1').replace(/^wo$/, 'o');
    return r.replace(/ou/g, 'oo');
  }
  function gradeJa(input, kana) {
    const u = String(input).trim(); if (!u) return { ok: false };
    if (/[\u3040-\u30ff]/.test(u)) return { ok: kataToHira(u).replace(/\s/g, '') === kataToHira(kana).replace(/\s/g, ''), mode: 'kana' };
    return { ok: normRomaji(u) === normRomaji(kanaToRomaji(kana)), mode: 'romaji' };
  }
  const TONE_MARKS = { 'ā': ['a', 1], 'á': ['a', 2], 'ǎ': ['a', 3], 'à': ['a', 4], 'ē': ['e', 1], 'é': ['e', 2], 'ě': ['e', 3], 'è': ['e', 4], 'ī': ['i', 1], 'í': ['i', 2], 'ǐ': ['i', 3], 'ì': ['i', 4], 'ō': ['o', 1], 'ó': ['o', 2], 'ǒ': ['o', 3], 'ò': ['o', 4], 'ū': ['u', 1], 'ú': ['u', 2], 'ǔ': ['u', 3], 'ù': ['u', 4], 'ǖ': ['v', 1], 'ǘ': ['v', 2], 'ǚ': ['v', 3], 'ǜ': ['v', 4], 'ü': ['v', 0] };
  function pinyinSyllables(numbered) {
    return numbered.toLowerCase().split(/\s+/).filter(Boolean).map((x) => {
      const m = /^([a-zü:]+)([0-5])?$/.exec(x.replace('ü', 'v').replace('u:', 'v'));
      return m ? { seg: m[1], tone: m[2] ? (+m[2] === 0 ? 5 : +m[2]) : null } : { seg: x, tone: null };
    });
  }
  function parsePinyinInput(u) {
    let s = String(u).toLowerCase().trim().replace(/u:/g, 'v');
    let hasMarks = false;
    s = s.replace(/[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]/g, (c) => { const [v, t] = TONE_MARKS[c]; if (t) hasMarks = true; return v + (t ? '<' + t + '>' : ''); });
    const parts = s.split(/[\s'’-]+/).filter(Boolean);
    const segs = [], ts = [];
    for (const p of parts) {
      let seg = p.replace(/<\d>/g, ''), tone = null;
      const m = /<(\d)>/.exec(p); if (m) tone = +m[1];
      const n = /([0-5])$/.exec(seg); if (n) { tone = +n[1]; seg = seg.slice(0, -1); }
      if (tone === 0) tone = 5;
      if (hasMarks && tone == null && /[a-z]/.test(seg)) tone = 5;
      segs.push(seg); ts.push(tone);
    }
    const haveTones = ts.length && ts.every((t) => t != null);
    return { segs, tones: haveTones ? ts : null };
  }
  function gradeZh(segs, tones, numbered) {
    const ref = pinyinSyllables(numbered);
    const segOk = segs.join('') === ref.map((r) => r.seg).join('');
    const toneOk = tones != null && tones.length === ref.length && tones.every((t, i) => t === ref[i].tone);
    return { segOk, toneOk, ok: segOk && toneOk, ref };
  }
  function gradeReading(input, rp) {
    if (S.test.language_id === ZH) { const pi = parsePinyinInput(input); return gradeZh(pi.segs, pi.tones, rp.numbered).ok; }
    return gradeJa(input, rp.shown).ok;
  }
  function hasTypedReading(sid) {
    const rp = readingParts(D.senses[sid]);
    if (!rp) return false;
    if (S.test.language_id === ZH) return !!rp.numbered;
    return S.test.language_id === JA;
  }

  // ---------- preview ----------
  function drawPreview() {
    const t = S.test, a = analyse(), tr = trigger(S.snapshot);
    $('psTitle').textContent = t.title || '';
    $('psChips').innerHTML =
      `<span class="ps-chip ${tr.cls}">${esc(tr.label)}</span>` +
      `<span class="ps-chip">${esc(T('prestudy.unknown_share', { pct: Math.round(S.snapshot * 100) }))}</span>` +
      `<span class="ps-chip">${esc(T('prestudy.minutes', { n: estMinutes(a) }))}</span>`;
    const au = $('psAudio');
    if (t.audio_url) { au.src = t.audio_url; au.hidden = false; au.onerror = () => { $('psAudioNote').hidden = false; }; }
    else au.hidden = true;

    const P = $('psPassage'); P.innerHTML = ''; P.lang = LANGCODE[t.language_id] || '';
    const rowBy = Object.fromEntries(a.rows.map((r) => [r.sid, r]));
    const aids = charAids(); const offs = []; { let o = 0; tokenMap().forEach(([surf]) => { offs.push(o); o += surf.length; }); }
    const quizzed = new Set(S.quiz ? S.quiz.words : []);
    sentences().forEach((idxs) => {
      const sp = document.createElement('span'); sp.className = 'ps-sent';
      idxs.forEach((i) => {
        const [surf, rawSid] = tokenMap()[i]; const sid = rawSid ? String(rawSid) : null;
        const e = document.createElement('span'); e.className = 'ps-tok';
        const r0 = sid ? rowBy[sid] : null;
        const showAid = S.aids === 'all' || (S.aids === 'unknown' && r0 && r0.p < 0.5);
        if (showAid) e.innerHTML = tokenWithAids(surf, offs[i], aids); else e.textContent = surf;
        if (sid && D.senses[sid]) {
          e.classList.add('linked'); if (r0) e.classList.add(r0.st); if (quizzed.has(sid)) e.classList.add('quizzed');
          e.dataset.sid = sid; e.tabIndex = 0; e.setAttribute('role', 'button');
          e.onclick = (ev) => { ev.stopPropagation(); showPop(e, sid); };
          e.onkeydown = (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); ev.stopPropagation(); showPop(e, sid); } };
        }
        sp.appendChild(e);
      });
      P.appendChild(sp);
    });
    P.classList.toggle('hl', S.hl);
    $('psStats').textContent = T('prestudy.passage_stats', { n: a.n, unknown: a.unknown, inq: a.rows.filter((r) => r.inQ && r.p < 0.5).length });

    const W = $('psWordlist'); W.innerHTML = '';
    const K = tr.mode === 'light' ? Math.min(3, a.ranked.length) : Math.min(12, a.ranked.length);
    $('psKwCount').textContent = T('prestudy.key_words_count', { shown: K, total: a.ranked.length });
    a.ranked.slice(0, K).forEach((r) => {
      const s = D.senses[r.sid], g = gloss(r.sid), nEx = exercisesFor(r.sid).length;
      const el = document.createElement('button'); el.type = 'button'; el.className = 'ps-word';
      el.innerHTML = `<div class="ps-word-main"><span class="ps-dot ${r.st}"></span><span class="ps-lem">${esc(s.lemma)}</span><span class="ps-rd">${esc((readingParts(s) || {}).shown || '')}</span>
          <div class="ps-g">${esc(g.def || T('prestudy.no_gloss'))}</div></div>
        <div class="ps-tags">${r.inQ ? `<span class="ps-chip primary">${esc(T('prestudy.in_question'))}</span>` : ''}<span class="ps-chip">${esc(T('prestudy.occurrences', { n: r.occ }))}</span>${nEx ? `<span class="ps-chip ok">${esc(T('prestudy.exercises_count', { count: nEx }))}</span>` : ''}</div>`;
      el.onclick = (ev) => {
        ev.stopPropagation();
        const tok = P.querySelector(`.ps-tok[data-sid="${r.sid}"]`);
        if (tok) { tok.scrollIntoView({ behavior: 'smooth', block: 'center' }); showPop(tok, r.sid); }
      };
      W.appendChild(el);
    });
    if (!a.ranked.length) W.innerHTML = `<div class="ps-note">${esc(T('prestudy.no_key_words'))}</div>`;
  }

  // ---------- popover ----------
  function showPop(anchor, sid) {
    const POP = $('psPop'), s = D.senses[sid], g = gloss(sid), p = pNow(sid);
    S.shown.add(sid);
    const r = analyse().rows.find((x) => x.sid === sid) || {};
    const rp = readingParts(s);
    POP.innerHTML = `<div><span class="ps-pop-w">${esc(s.lemma)}</span><span class="ps-pop-r">${esc(rp ? rp.shown : '')}${s.pos ? ' · ' + esc(s.pos) : ''}</span></div>
      <div class="ps-pop-d">${esc(g.def || T('prestudy.no_gloss'))}</div>
      ${g.ex ? `<div class="ps-pop-ex">${esc(g.ex)}</div>` : ''}
      <div class="ps-pop-meta"><span class="ps-chip ${p < 0.2 ? 'bad' : p < 0.5 ? 'warn' : p < 0.75 ? 'primary' : 'ok'}">${esc(T('prestudy.status_' + status(p)))}</span><span class="ps-chip">${esc(T('prestudy.pop_in_passage', { n: r.occ || 0 }))}</span>${r.inQ ? `<span class="ps-chip primary">${esc(T('prestudy.in_question'))}</span>` : ''}</div>
      <button type="button" class="btn btn-sm btn-outline-secondary ps-pop-close" id="psPopClose">${esc(T('prestudy.pop_close'))}</button>`;
    $('psPopClose').onclick = (ev) => { ev.stopPropagation(); hidePop(); };
    POP.hidden = false; $('psScrim').hidden = false;
    const rc = anchor.getBoundingClientRect();
    POP.style.top = (rc.bottom + window.scrollY + 6) + 'px'; POP.style.left = '0px';
    const w = POP.offsetWidth;
    POP.style.left = Math.max(8, Math.min(rc.left + window.scrollX, document.documentElement.clientWidth - w - 8)) + 'px';
  }
  function hidePop() { const POP = $('psPop'); if (POP) POP.hidden = true; const sc = $('psScrim'); if (sc) sc.hidden = true; }

  // ---------- exercises ----------
  function pickExercise(sid, group) {
    const pool = exercisesFor(sid).filter((e) => e.group === group && !S.exUsed.has(e.id));
    if (!pool.length) return null;
    const e = pool[Math.floor(Math.random() * pool.length)]; S.exUsed.add(e.id); return e;
  }
  function exItem(stage, sid, group) {
    const e = pickExercise(sid, group) || pickExercise(sid, group === 'use' ? 'judge' : 'use');
    return e ? { stage, sid, kind: 'ex', ex: e } : null;
  }
  function exerciseUsable(e) {
    const c = e.c || {};
    switch (e.type) {
      case 'cloze_completion': case 'particle_selection': case 'morphology_slot':
        return Array.isArray(c.options) && c.options.length > 1 && c.correct_answer != null && c.sentence_with_blank;
      case 'definition_match': return Array.isArray(c.options) && c.options.length > 1 && c.correct_definition != null;
      case 'synonym_antonym_match': return Array.isArray(c.options) && c.options.length > 1 && c.correct_answer != null;
      case 'tl_nl_translation': return Array.isArray(c.options) && c.options.length > 1 && c.correct_nl != null;
      case 'semantic_discrimination': return Array.isArray(c.sentences) && c.sentences.some((x) => x && x.is_correct === true);
      case 'spot_incorrect_sentence': return Array.isArray(c.sentences) && c.sentences.some((x) => x && x.is_correct === false);
      case 'cloze_typed': return c.sentence_with_blank && c.answer && (c.answer.accepted || []).length;
      case 'jumbled_sentence': return Array.isArray(c.chunks) && Array.isArray(c.correct_ordering) && c.chunks.length === c.correct_ordering.length;
      default: return false;
    }
  }
  function blankify(text) { return esc(text).replace(/_{2,}|＿{2,}/, '<span class="ps-blank">＿＿＿</span>'); }
  function drawExercise(it, head) {
    const B = $('psQBody'), e = it.ex, c = e.c, t = e.type;
    const sub = `<div class="ps-row ps-sub"><span class="ps-chip warn">${esc(T('prestudy.ex_' + t))}</span></div>`;
    const mc = (promptHtml, opts, correct, extra) => {
      it.correctText = correct;
      B.innerHTML = `${head}${sub}<div class="ps-ctx">${promptHtml}</div><div class="ps-opts">${opts.map((o, i) => `<button type="button" class="ps-opt ps-cjk" data-i="${i}">${esc(o)}</button>`).join('')}</div><div id="psReveal"></div>`;
      B.querySelectorAll('.ps-opt').forEach((b) => { b.onclick = () => { const v = opts[parseInt(b.dataset.i, 10)]; answer(v === correct, v, extra()); }; });
    };
    if (t === 'cloze_completion' || t === 'particle_selection' || t === 'morphology_slot') {
      mc(blankify(c.sentence_with_blank), shuffle(c.options), c.correct_answer, () => ({ detail: c.explanation || '', shown: c.original_sentence }));
    } else if (t === 'definition_match') {
      mc(`<b>${esc(c.word)}</b>${c.pronunciation ? ' <span class="ps-note">' + esc(c.pronunciation) + '</span>' : ''}`, shuffle(c.options), c.correct_definition, () => ({}));
    } else if (t === 'synonym_antonym_match') {
      mc(`<b>${esc(c.word)}</b> <span class="ps-note">→ ${esc(c.relation || '')}</span>`, shuffle(c.options), c.correct_answer, () => ({}));
    } else if (t === 'tl_nl_translation') {
      mc(esc(c.tl_sentence), shuffle(c.options), c.correct_nl, () => ({}));
    } else if (t === 'semantic_discrimination' || t === 'spot_incorrect_sentence') {
      const wantCorrect = t === 'semantic_discrimination';
      const sents = shuffle(c.sentences.filter(Boolean)); const target = sents.find((x) => x.is_correct === wantCorrect);
      it.correctText = target.text;
      B.innerHTML = `${head}${sub}<div class="ps-opts">${sents.map((x, i) => `<button type="button" class="ps-opt ps-cjk" data-i="${i}">${esc(x.text)}</button>`).join('')}</div><div id="psReveal"></div>`;
      B.querySelectorAll('.ps-opt').forEach((b) => { b.onclick = () => { const x = sents[parseInt(b.dataset.i, 10)]; answer(x === target, x.text, { detail: wantCorrect ? (c.explanation || '') : (target.error_description || '') }); }; });
    } else if (t === 'cloze_typed') {
      const ph = T('prestudy.typed_placeholder_' + (LANGCODE[S.test.language_id] || 'en'));
      B.innerHTML = `${head}${sub}<div class="ps-ctx">${blankify(c.sentence_with_blank)}</div>
        <form id="psTypedForm" class="ps-row ps-form"><input id="psTyped" class="form-control ps-input ps-cjk" type="text" autocomplete="off" spellcheck="false" lang="${LANGCODE[S.test.language_id] || ''}" placeholder="${esc(ph)}"><button class="btn btn-primary" type="submit">${esc(T('prestudy.check'))}</button></form><div id="psReveal"></div>`;
      const norm = (x) => String(x).normalize('NFKC').trim().replace(/[。！？、，．,.!?]+$/, '').toLowerCase();
      $('psTypedForm').onsubmit = (ev) => {
        ev.preventDefault(); const v = $('psTyped').value; if (!v.trim()) return;
        answer((c.answer.accepted || []).map(norm).includes(norm(v)), v, { shown: c.original_sentence });
      };
      $('psTyped').focus();
    } else if (t === 'jumbled_sentence') {
      const order = c.correct_ordering, chunks = c.chunks, idx = shuffle(chunks.map((_, i) => i)), picked = [];
      const joiner = S.test.language_id === EN ? ' ' : '';
      const render = () => {
        B.innerHTML = `${head}${sub}<div class="ps-ctx ps-built">${picked.map((i) => `<span class="ps-chunk on">${esc(chunks[i])}</span>`).join('') || `<span class="ps-note">${esc(T('prestudy.tap_pieces'))}</span>`}</div>
          <div class="ps-chunks">${idx.filter((i) => !picked.includes(i)).map((i) => `<button type="button" class="ps-chunk" data-i="${i}">${esc(chunks[i])}</button>`).join('')}</div>
          <div class="ps-row ps-gap"><button type="button" class="btn btn-sm btn-outline-secondary" id="psUndo" ${picked.length ? '' : 'disabled'}>${esc(T('prestudy.undo'))}</button><button type="button" class="btn btn-primary" id="psCheckJ" ${picked.length === chunks.length ? '' : 'disabled'}>${esc(T('prestudy.check'))}</button></div><div id="psReveal"></div>`;
        B.querySelectorAll('.ps-chunks .ps-chunk').forEach((b) => { b.onclick = () => { picked.push(parseInt(b.dataset.i, 10)); render(); }; });
        $('psUndo').onclick = () => { picked.pop(); render(); };
        $('psCheckJ').onclick = () => { answer(picked.every((v, k) => v === order[k]), picked.map((i) => chunks[i]).join(joiner), { shown: c.original_sentence }); };
        ensureIdk();
      };
      render();
    }
  }

  // ---------- word prime ----------
  function wordPool(a) { return a.rows.map((r) => r.sid).filter((x) => gloss(x).def); }
  function pickDistractors(pool, sid, n, keyFn, prefer) {
    const seen = new Set([keyFn(sid)]); const out = [];
    const ordered = shuffle(pool.filter((x) => x !== sid && prefer(x))).concat(shuffle(pool.filter((x) => x !== sid && !prefer(x))));
    for (const x of ordered) { const v = keyFn(x); if (!v || seen.has(v)) continue; seen.add(v); out.push(x); if (out.length >= n) break; }
    return out;
  }
  function buildItem(stage, sid, a) {
    const s = D.senses[sid], pool = wordPool(a), rp = readingParts(s), samePos = (x) => D.senses[x].pos === s.pos;
    const def = gloss(sid).def;
    if (stage === 'read_typed' || stage === 'read_typed2') {
      if (!hasTypedReading(sid)) return null;
      return { stage, sid, kind: 'typed', prompt: s.lemma, correct: rp.shown, numbered: rp.numbered };
    }
    if (stage === 'def_mc') {
      if (!def) return null;
      const dis = pickDistractors(pool, sid, 3, (x) => gloss(x).def, samePos).map((x) => gloss(x).def);
      if (!dis.length) return null;
      return { stage, sid, kind: 'mc', prompt: s.lemma, sub: rp ? rp.shown : '', opts: shuffle([def, ...dis]), correct: def };
    }
    if (stage === 'rev_mc') {
      if (!def) return null;
      const dis = pickDistractors(pool, sid, 3, (x) => D.senses[x].lemma, samePos).map((x) => D.senses[x].lemma);
      if (!dis.length) return null;
      return { stage, sid, kind: 'mc', prompt: def, opts: shuffle([s.lemma, ...dis]), correct: s.lemma, cjkOpts: true, glossPrompt: true };
    }
    if (stage === 'cloze_mc') {
      const sent = passageSentenceFor(sid, true); if (!sent) return null;
      const dis = pickDistractors(pool, sid, 3, (x) => D.senses[x].lemma, samePos).map((x) => D.senses[x].lemma);
      if (!dis.length) return null;
      return { stage, sid, kind: 'mc', prompt: sent, opts: shuffle([s.lemma, ...dis]), correct: s.lemma, cjkOpts: true, cloze: true };
    }
    if (stage === 'ex_use') return exItem(stage, sid, 'use');
    if (stage === 'ex_judge') return exItem(stage, sid, 'judge');
    return null;
  }
  function newPerWord(sid) { return { exposures: 0, correct: 0, wrong: 0, idk: 0, boosters: 0, pBefore: pNow(sid), stages: {} }; }
  function buildQuiz() {
    const a = analyse(), planMode = currentPlanMode();
    let words;
    if (S.mode === 'followup') {
      // the unknown senses behind the questions answered wrong, in question order
      words = S.followSenses.filter((sid) => D.senses[sid] && pNow(sid) < 0.5).slice(0, FOLLOWUP_MAX_WORDS);
    } else {
      const n = planMode === 'light' ? Math.min(3, a.ranked.length) : Math.min(8, a.ranked.length);
      words = a.ranked.slice(0, n).map((r) => r.sid);
    }
    S.exUsed = new Set();
    const queue = [];
    const allowed = S.mode === 'followup' ? FOLLOWUP_STAGES : (planMode === 'light' ? LIGHT_STAGES : null);
    STAGES.filter((st) => !allowed || allowed.includes(st.k)).forEach((st) => {
      const round = shuffle(words.map((sid) => buildItem(st.k, sid, a)).filter(Boolean));
      if (queue.length && round.length > 1 && round[0].sid === queue[queue.length - 1].sid) round.push(round.shift());
      queue.push(...round);
    });
    const perWord = {}; words.forEach((sid) => { perWord[sid] = newPerWord(sid); });
    S.quiz = { words, queue, i: 0, mode: planMode, perWord };
    $('psQuizMode').textContent = T('prestudy.prime_header', { words: words.length, items: queue.length });
    drawQuiz();
  }
  function currentPlanMode() {
    return ['full', 'light', 'none'].includes(S.planOverride) ? S.planOverride : trigger(S.snapshot).mode;
  }
  function ensureIdk() {
    const rv = $('psReveal'); if (!rv || $('psIdk')) return;
    const q = S.quiz, it = q && q.queue[q.i]; if (!it || it.answered != null) return;
    const row = document.createElement('div'); row.className = 'ps-idkrow';
    row.innerHTML = `<button type="button" class="btn btn-outline-secondary" id="psIdk">${esc(T('prestudy.idk'))}</button><span class="ps-note">${esc(T('prestudy.idk_note'))}</span>`;
    rv.parentNode.insertBefore(row, rv);
    $('psIdk').onclick = () => answer(false, null, { idk: true });
  }
  function drawProgress(items, cur) {
    $('psQProg').innerHTML = items.map((it, i) => `<i class="${it.answered == null ? (i === cur ? 'cur' : '') : (it.ok ? 'c' : (it.idk ? 'k' : 'w'))}"></i>`).join('');
  }
  function drawQuiz() {
    const q = S.quiz, B = $('psQBody');
    drawProgress(q.queue, q.i);
    if (!q.queue.length) { B.innerHTML = `<div class="ps-note">${esc(T('prestudy.no_prime_needed'))}</div>`; updateActionBar(); return; }
    if (q.i >= q.queue.length) {
      const first = q.queue.filter((it) => !it.retry);
      const rd = first.filter((it) => it.stage.startsWith('read')), mn = first.filter((it) => !it.stage.startsWith('read'));
      B.innerHTML = `<div class="ps-statrow">
          <div class="ps-stat">${first.filter((i) => i.ok).length} / ${first.length}<small>${esc(T('prestudy.done_first_try'))}</small></div>
          ${rd.length ? `<div class="ps-stat">${rd.filter((i) => i.ok).length} / ${rd.length}<small>${esc(T('prestudy.done_reading'))}</small></div>` : ''}
          <div class="ps-stat">${mn.filter((i) => i.ok).length} / ${mn.length}<small>${esc(T('prestudy.done_meaning'))}</small></div>
          <div class="ps-stat">${q.queue.filter((it) => it.idk).length}<small>${esc(T('prestudy.done_idk'))}</small></div></div>
        <div class="ps-callout">${esc(S.mode === 'followup' ? T('prestudy.next_produce') : (readinessWords().length && currentPlanMode() !== 'light' ? T(S.phase === 'boost' ? 'prestudy.next_readiness2' : 'prestudy.next_readiness') : T('prestudy.next_ready')))}</div>`;
      updateActionBar();
      return;
    }
    const it = q.queue[q.i], s = D.senses[it.sid], st = STAGES.find((x) => x.k === it.stage), w = q.perWord[it.sid];
    const chipCls = it.stage.startsWith('read') ? 'info' : it.stage === 'cloze_mc' ? 'warn' : it.kind === 'ex' ? 'ok' : 'primary';
    const head = `<div class="ps-row ps-between ps-qhead"><span class="ps-note">${esc(T('prestudy.item_of', { i: q.i + 1, n: q.queue.length }))} · <span class="ps-chip ${chipCls}">${esc(T(st.label))}${it.retry ? ' · ' + esc(T('prestudy.again')) : ''}</span> ${esc(T(st.ask))}</span><span class="ps-note">${esc(T('prestudy.exposure', { n: w.exposures + 1 }))}</span></div>`;
    if (it.kind === 'ex') { drawExercise(it, head); ensureIdk(); updateActionBar(); return; }
    if (it.kind === 'typed') { drawTyped(it, head); updateActionBar(); return; }
    B.innerHTML = `${head}<div class="${it.cloze ? 'ps-ctx' : 'ps-qword'}${it.glossPrompt ? ' ps-gloss-prompt' : ''}">${it.cloze ? it.prompt : esc(it.prompt)}</div>${it.sub ? `<div class="ps-qread">${esc(it.sub)}${s.pos ? ' · ' + esc(s.pos) : ''}</div>` : ''}
      <div class="ps-opts">${it.opts.map((o, i) => `<button type="button" class="ps-opt${it.cjkOpts ? ' ps-cjk ps-big' : ''}" data-i="${i}">${esc(o)}</button>`).join('')}</div><div id="psReveal"></div>`;
    B.querySelectorAll('.ps-opt').forEach((b) => { b.onclick = () => { const v = it.opts[parseInt(b.dataset.i, 10)]; answer(v === it.correct, v); }; });
    ensureIdk();
    updateActionBar();
  }
  function drawTyped(it, head) {
    const B = $('psQBody'), zh = S.test.language_id === ZH;
    B.innerHTML = `${head}<div class="ps-qword">${esc(it.prompt)}</div><div class="ps-qread">${esc(T(zh ? 'prestudy.hint_zh' : 'prestudy.hint_ja'))}</div>
      <form id="psTypedForm" class="ps-row ps-form"><input id="psTyped" class="form-control ps-input" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" lang="${zh ? 'zh-Latn' : 'ja'}" placeholder="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}"><button class="btn btn-primary" type="submit">${esc(T('prestudy.check'))}</button></form><div id="psTones"></div><div id="psReveal"></div>`;
    const f = $('psTypedForm');
    f.onsubmit = (e) => {
      e.preventDefault(); const v = $('psTyped').value; if (!v.trim()) return;
      if (!zh) { const g = gradeJa(v, it.correct); answer(g.ok, v, { detail: g.ok && g.mode === 'romaji' ? T('prestudy.romaji_ok') : '' }); return; }
      const pi = parsePinyinInput(v); const g = gradeZh(pi.segs, pi.tones, it.numbered);
      if (pi.tones != null || !g.segOk) { answer(g.ok, v, { detail: g.segOk ? (g.toneOk ? '' : T('prestudy.tones_wrong')) : T('prestudy.syllables_wrong') }); return; }
      // toneless and syllables right: pick the tone of each syllable
      $('psTyped').disabled = true; f.querySelector('button').disabled = true;
      const Tn = $('psTones'); const picked = new Array(g.ref.length).fill(null);
      Tn.innerHTML = `<div class="ps-note ps-gap">${esc(T('prestudy.tones_now'))}</div><div class="ps-tonegrid">${g.ref.map((r, i) => `<div class="ps-tonesyl"><div class="ps-syl">${esc(pi.segs[i] || r.seg)}</div><div class="ps-tonebtns">${[1, 2, 3, 4, 5].map((tn) => `<button type="button" class="ps-tone" data-i="${i}" data-t="${tn}" aria-label="${esc(T('prestudy.tone_label', { n: tn }))}">${tn === 5 ? '·' : tn}</button>`).join('')}</div></div>`).join('')}</div>`;
      Tn.querySelectorAll('.ps-tone').forEach((btn) => {
        btn.onclick = () => {
          const i = +btn.dataset.i; picked[i] = +btn.dataset.t;
          Tn.querySelectorAll(`.ps-tone[data-i="${i}"]`).forEach((x) => x.classList.toggle('picked', x === btn));
          if (picked.every((tn) => tn != null)) {
            const g2 = gradeZh(pi.segs, picked, it.numbered);
            Tn.querySelectorAll('.ps-tone').forEach((x) => { const ii = +x.dataset.i, tt = +x.dataset.t; x.disabled = true; if (tt === g2.ref[ii].tone) x.classList.add('correct'); else if (tt === picked[ii]) x.classList.add('wrong'); });
            answer(g2.ok, v + ' ' + picked.join(''), { detail: g2.ok ? '' : T('prestudy.tones_wrong') });
          }
        };
      });
    };
    $('psTyped').focus(); ensureIdk();
  }
  function recordAnswer(sid, correct, idk, stage) {
    S.answers.push({ sense_id: Number(sid), correct: !!correct, idk: !!idk, stage: stage || (S.mode === 'followup' ? 'followup' : 'prime') });
  }
  function answer(ok, given, extra) {
    extra = extra || {};
    const q = S.quiz, it = q.queue[q.i]; if (!it || it.answered != null) return;
    if (!q.perWord[it.sid]) q.perWord[it.sid] = newPerWord(it.sid);
    const idk = !!extra.idk; it.answered = idk ? '' : given; it.ok = ok; it.idk = idk;
    const w = q.perWord[it.sid]; w.exposures++; if (ok) w.correct++; else w.wrong++; if (idk) w.idk++; if (!it.retry) w.stages[it.stage] = ok;
    const p0 = pNow(it.sid); S.know[it.sid] = idk ? bktUpdateIdk(p0) : bktUpdate(p0, ok);
    // ladder exercises are exercise evidence (exercise_attempts, source prestudy),
    // everything else is word-test evidence
    if (it.kind === 'ex') S.exAnswers.push({ exercise_id: it.ex.id, correct: !!ok, idk, given: given == null ? '' : String(given).slice(0, 200) });
    else recordAnswer(it.sid, ok, idk);
    const willRetry = !ok && (it.retries || 0) < (idk ? 3 : 2);
    if (willRetry) {
      const again = Object.assign({}, it, { answered: null, ok: null, idk: false, retry: true, retries: (it.retries || 0) + 1 });
      q.queue.splice(Math.min(q.queue.length, q.i + (idk ? 2 : 3) + Math.floor(Math.random() * 3)), 0, again);
    }
    // an honest miss adds one booster exposure of this word, in a different cheap stage, at the end
    let booster = null;
    if (idk && w.boosters < 2) {
      const a = analyse(); const alt = it.stage === 'def_mc' ? 'read_typed' : 'def_mc';
      booster = buildItem(alt, it.sid, a) || buildItem('rev_mc', it.sid, a);
      if (booster) { booster.retry = true; booster.booster = true; q.queue.push(booster); w.boosters++; }
    }
    const B = $('psQBody');
    B.querySelectorAll('#psIdk').forEach((b) => { b.disabled = true; });
    const corr = it.kind === 'ex' ? it.correctText : it.correct;
    B.querySelectorAll('.ps-opt').forEach((b) => { const v = it.kind === 'ex' ? b.textContent : it.opts[parseInt(b.dataset.i, 10)]; if (v === corr) b.classList.add('correct'); else if (v === given) b.classList.add('wrong'); b.disabled = true; });
    B.querySelectorAll('.ps-chunks .ps-chunk, #psUndo, #psCheckJ, #psTypedForm button, .ps-tone').forEach((b) => { b.disabled = true; });
    const typed = $('psTyped'); if (typed) { typed.disabled = true; typed.classList.add(ok ? 'is-valid' : (idk ? 'ps-idk-input' : 'is-invalid')); }

    const g = gloss(it.sid), s = D.senses[it.sid], rp = readingParts(s), isRead = it.stage.startsWith('read');
    const readingTxt = rp ? ' · ' + esc(rp.shown) + (rp.numbered ? ' (' + esc(rp.numbered) + ')' : '') + (S.test.language_id === JA ? ' · ' + esc(kanaToRomaji(rp.shown)) : '') : '';
    const lines = [];
    if (idk && isRead && g.def) lines.push(esc(T('prestudy.meaning_label', { def: g.def })));
    if (isRead) lines.push(esc(T('prestudy.meaning_next')));
    if (g.ex && !isRead) lines.push(esc(T('prestudy.example', { ex: g.ex })));
    let ctx = '';
    if (it.kind === 'ex') { if (extra.shown) ctx = `<div class="ps-note ps-gap">${esc(T('prestudy.full_sentence'))}</div><div class="ps-ctx">${esc(extra.shown)}</div>`; }
    else if (!it.cloze) { const ps = passageSentenceFor(it.sid); if (ps) ctx = `<div class="ps-note ps-gap">${esc(T('prestudy.in_passage'))}</div><div class="ps-ctx">${ps}</div>`; }
    const follow = willRetry ? T('prestudy.reasked') : (ok ? '' : T('prestudy.moving_on'));
    $('psReveal').innerHTML = `<div class="ps-reveal ${ok ? 'ok' : (idk ? 'idk' : 'bad')}"><b>${esc(T(ok ? 'prestudy.correct' : (idk ? 'prestudy.idk_reveal' : 'prestudy.wrong')))}</b> <b class="ps-cjk">${esc(s.lemma)}</b>${readingTxt}${isRead || !g.def ? '' : ' — ' + esc(g.def)}
      ${lines.map((l) => `<div class="ps-note">${l}</div>`).join('')}${ctx}
      ${extra.detail ? `<div class="ps-note">${esc(extra.detail)}</div>` : ''}
      ${follow || booster ? `<div class="ps-note">${esc(follow)}${booster ? ' ' + esc(T('prestudy.booster_added')) : ''}</div>` : ''}
      <div class="ps-reveal-foot"><button type="button" class="btn btn-primary" id="psNext">${esc(T(q.i + 1 < q.queue.length ? 'prestudy.next' : 'prestudy.finish'))}</button></div></div>`;
    $('psNext').onclick = () => { q.i++; drawQuiz(); };
    $('psNext').focus();
  }

  // ---------- readiness check ----------
  function readinessWords() {
    const q = S.prime || S.quiz; if (!q) return [];
    const score = (sid) => { const w = q.perWord[sid]; return (w.idk || 0) * 10 + (w.wrong || 0) - pNow(sid); };
    return q.words.filter(hasTypedReading).sort((a, b) => score(b) - score(a)).slice(0, 5);
  }
  function startReadiness(round) {
    S.ready = { round, words: readinessWords(), i: 0, answers: [], results: null };
    S.phase = 'ready'; drawReadiness();
  }
  function drawReadiness() {
    const R = S.ready, B = $('psQBody'), zh = S.test.language_id === ZH;
    $('psQuizMode').textContent = T('prestudy.readiness_title', { n: R.round });
    $('psQProg').innerHTML = R.words.map((_, i) => `<i class="${i < R.i ? 'c' : (i === R.i ? 'cur' : '')}"></i>`).join('');
    if (!R.words.length) { R.results = { score: 0, n: 0, pass: true, failed: [] }; B.innerHTML = `<div class="ps-note">${esc(T('prestudy.no_readiness_words'))}</div>`; updateActionBar(); return; }
    if (R.i >= R.words.length) {
      if (!R.results) {
        const rows = R.words.map((sid, i) => ({ sid, u: R.answers[i], rp: readingParts(D.senses[sid]), ok: !!R.answers[i] && gradeReading(R.answers[i], readingParts(D.senses[sid])) }));
        const score = rows.filter((r) => r.ok).length, n = rows.length, need = Math.ceil(n * 0.8);
        R.results = { score, n, need, pass: score >= need, failed: rows.filter((r) => !r.ok).map((r) => r.sid), rows };
        const q = S.prime || S.quiz;
        rows.forEach((r) => {
          const w = q.perWord[r.sid]; if (w) { w.readiness = w.readiness || []; w.readiness.push(r.ok); }
          S.know[r.sid] = r.u ? bktUpdate(pNow(r.sid), r.ok) : bktUpdateIdk(pNow(r.sid));
          recordAnswer(r.sid, r.ok, !r.u, 'readiness');
        });
      }
      const res = R.results;
      const msg = res.pass ? T('prestudy.ready_unlocked') : (R.round === 1 ? T('prestudy.extra_round_note') : T('prestudy.proceed_anyway'));
      B.innerHTML = `<div class="ps-statrow"><div class="ps-stat">${res.score} / ${res.n}<small>${esc(T('prestudy.readiness_score', { round: R.round, need: res.need }))}</small></div>
          <div class="ps-stat"><span class="ps-chip ${res.pass ? 'ok' : 'warn'} ps-chip-lg">${esc(T(res.pass ? 'prestudy.ready' : 'prestudy.not_yet'))}</span><small>${esc(msg)}</small></div></div>
        <div class="table-responsive"><table class="table table-sm ps-table"><thead><tr><th>${esc(T('prestudy.col_word'))}</th><th>${esc(T('prestudy.col_typed'))}</th><th>${esc(T('prestudy.col_reading'))}</th><th></th></tr></thead><tbody>
          ${res.rows.map((r) => `<tr><td><b class="ps-cjk">${esc(D.senses[r.sid].lemma)}</b></td><td><code>${esc(r.u || '—')}</code></td><td>${esc(r.rp.shown)}${r.rp.numbered ? ' <span class="ps-note">(' + esc(r.rp.numbered) + ')</span>' : ''}</td><td>${r.ok ? '<span class="ps-chip ok">✓</span>' : '<span class="ps-chip bad">✗</span>'}</td></tr>`).join('')}
        </tbody></table></div>`;
      updateActionBar();
      return;
    }
    const sid = R.words[R.i], s = D.senses[sid];
    B.innerHTML = `<div class="ps-row ps-between ps-qhead"><span class="ps-note">${esc(T('prestudy.check_of', { i: R.i + 1, n: R.words.length }))} · <span class="ps-chip info">${esc(T('prestudy.stage_reading'))}</span> ${esc(T('prestudy.ask_read'))}</span><span class="ps-note">${esc(T('prestudy.no_feedback'))}</span></div>
      <div class="ps-qword">${esc(s.lemma)}</div><div class="ps-qread">${esc(T(zh ? 'prestudy.ready_hint_zh' : 'prestudy.ready_hint_ja'))}</div>
      <form id="psReadyForm" class="ps-row ps-form"><input id="psReadyIn" class="form-control ps-input" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" lang="${zh ? 'zh-Latn' : 'ja'}" placeholder="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}"><button class="btn btn-primary" type="submit">${esc(T('prestudy.next'))}</button></form>
      <div class="ps-idkrow"><button type="button" class="btn btn-outline-secondary" id="psReadyIdk">${esc(T('prestudy.idk'))}</button></div>`;
    $('psReadyForm').onsubmit = (e) => { e.preventDefault(); R.answers.push($('psReadyIn').value.trim()); R.i++; drawReadiness(); };
    $('psReadyIdk').onclick = () => { R.answers.push(''); R.i++; drawReadiness(); };
    $('psReadyIn').focus();
    updateActionBar();
  }
  function startBoost() {
    const a = analyse(), failed = S.ready.results.failed, items = [];
    shuffle(failed).forEach((sid) => { const r = buildItem('read_typed', sid, a); if (r) items.push(r); });
    shuffle(failed).forEach((sid) => { const d = buildItem('def_mc', sid, a); if (d) items.push(d); });
    S.prime = S.prime || S.quiz;
    S.quiz = Object.assign({}, S.prime, { queue: items, i: 0 });
    S.phase = 'boost';
    $('psQuizMode').textContent = T('prestudy.extra_round_header', { n: failed.length });
    drawQuiz();
  }

  // ---------- ready ----------
  // The measurement record for prestudy_sessions (wiki/features/test-prestudy.md, Measurement).
  function metrics() {
    const q = S.prime || S.quiz || { queue: [], words: [], perWord: {} };
    const answered = q.queue.filter((it) => it.answered != null);
    const first = answered.filter((it) => !it.retry);
    const R = S.ready && S.ready.results;
    const a = analyse();
    const nextDay = q.words.filter((sid) => {
      const w = q.perWord[sid] || {};
      return (w.idk || 0) >= 2 || (w.readiness || []).some((x) => !x);
    });
    return {
      words_shown: Array.from(S.shown).map(Number),
      words_quizzed: q.words.map(Number),
      exposures: answered.length,
      first_try_correct: first.filter((it) => it.ok).length,
      first_try_total: first.length,
      idk_count: answered.filter((it) => it.idk).length,
      boosters: q.queue.filter((it) => it.booster).length,
      ladder_exercises: answered.filter((it) => it.kind === 'ex').length,
      readiness_score: R ? R.score : null,
      readiness_n: R ? R.n : null,
      readiness_rounds: S.ready ? S.ready.round : 0,
      ready: R ? !!R.pass : null,
      next_day_review_senses: nextDay.map(Number),
      minutes_est: estMinutes(a),
      active_seconds: S.timer ? Math.round(S.timer.stop() / 1000) : 0,
      tests_dropped_today: S.droppedToday,
    };
  }
  async function postEvidence() {
    if (S.evidencePosted) return true;
    if (!S.answers.length && !S.exAnswers.length && !S.sessionId) return true;
    S.evidencePosted = true;
    try {
      const res = await window.authFetch(`/api/tests/${encodeURIComponent(S.slug)}/prestudy/evidence`, {
        method: 'POST',
        body: JSON.stringify({
          session_id: S.sessionId, mode: S.mode,
          answers: S.answers.slice(0, 400), exercise_answers: S.exAnswers.slice(0, 40),
          metrics: metrics(),
        }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return true;
    } catch (e) {
      console.warn('[prestudy] evidence not saved:', e);
      S.evidencePosted = false;
      return false;
    }
  }
  function drawReady() {
    const q = S.prime || S.quiz || { queue: [], words: [] };
    const first = q.queue.filter((it) => !it.retry && it.answered != null);
    const R = S.ready && S.ready.results;
    $('psReadyStats').innerHTML = `<div class="ps-stat">${q.words.length}<small>${esc(T('prestudy.summary_words'))}</small></div>
      <div class="ps-stat">${first.filter((it) => it.ok).length} / ${first.length}<small>${esc(T('prestudy.summary_first_try'))}</small></div>
      ${R && R.n ? `<div class="ps-stat">${R.score} / ${R.n}<small>${esc(T('prestudy.summary_readiness'))}</small></div>` : ''}`;
    const st = $('psSaveState');
    $('psReadyTitle').textContent = T(S.mode === 'followup' ? 'prestudy.followup_done_title' : 'prestudy.ready_title');
    $('psEloNote').hidden = S.mode === 'followup';
    $('psTakeTest').hidden = S.mode === 'followup';
    $('psProduceBox').hidden = S.mode !== 'followup';
    $('psBackToSession').hidden = !(S.mode === 'followup' && S.returnTo === 'session');
    if (!S.answers.length && !S.exAnswers.length) {
      st.textContent = '';
      postEvidence();
      return;
    }
    st.textContent = T('prestudy.saving');
    postEvidence().then((ok) => { st.textContent = T(ok ? 'prestudy.saved' : 'prestudy.save_failed'); });
  }
  function testUrl() {
    return `/test/${encodeURIComponent(S.slug)}?type=${encodeURIComponent(S.testType)}`;
  }
  // Mark the session's prestudy block done (opened from the daily session).
  async function completeBlock() {
    if (!S.block) return;
    try {
      await window.authFetch('/api/study-session/complete-block', {
        method: 'POST', body: JSON.stringify({ block_id: S.block, language_id: S.test.language_id }),
      });
    } catch (e) { console.warn('[prestudy] block not completed:', e); }
  }
  async function takeTest(prestudied) {
    if (prestudied) {
      await postEvidence();
      try { sessionStorage.setItem(MARKER_PREFIX + S.slug, JSON.stringify({ at: Date.now(), test_id: S.test.id })); } catch { /* storage blocked: the attempt counts at full weight */ }
    }
    await completeBlock();
    // from the daily session: go back, where the session resumes on this test
    window.location.href = S.returnTo === 'session' ? '/session' : testUrl();
  }

  // ---------- Produce (after the follow-up) ----------
  async function startProduce() {
    const btn = $('psProduce'), msg = $('psProduceMsg');
    btn.disabled = true; msg.textContent = T('prestudy.produce_loading');
    await postEvidence();
    const fallback = analyse().ranked.slice(0, 8).map((r) => Number(r.sid));
    try {
      const res = await window.authFetch(`/api/tests/${encodeURIComponent(S.slug)}/prestudy/produce`, {
        method: 'POST', body: JSON.stringify({ fallback_sense_ids: fallback }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.submission_id) {
        msg.textContent = T(data.error_code === 'NO_WINDOW' ? 'prestudy.produce_none' : 'prestudy.produce_failed');
        btn.disabled = false;
        return;
      }
      sessionStorage.setItem('dt_produce_session', JSON.stringify(data));
      window.location.href = '/dual-translation';
    } catch (e) {
      console.warn('[prestudy] Produce failed:', e);
      msg.textContent = T('prestudy.produce_failed');
      btn.disabled = false;
    }
  }
  async function backToSession() {
    await postEvidence();
    // today's translation slot in the session will use this test's window
    if (S.mode === 'followup' && window.LinguaPrestudyLinks) window.LinguaPrestudyLinks.setProduceRequest(S.slug, S.test.id);
    window.location.href = '/session';
  }

  // ---------- navigation ----------
  function updateActionBar() {
    const back = $('psBack'), next = $('psNextStep'), note = $('psBarNote');
    back.hidden = S.step === 1 || (S.mode === 'followup' && S.step === 2);
    if (S.step === 1) {
      next.textContent = T('prestudy.start_prime'); note.textContent = T('prestudy.elo_note');
    } else if (S.step === 2) {
      note.textContent = '';
      if (S.phase === 'ready' && S.ready && S.ready.results && !S.ready.results.pass && S.ready.round < 2) next.textContent = T('prestudy.extra_round');
      else next.textContent = T('prestudy.continue');
    }
    $('psActionBar').hidden = S.step === 3;
  }
  function go(n) {
    S.step = n;
    document.querySelectorAll('.ps-step').forEach((s) => s.classList.toggle('active', s.dataset.step === String(n)));
    $('psS1').hidden = n !== 1; $('psS2').hidden = n !== 2; $('psS3').hidden = n !== 3;
    hidePop();
    if (n === 1) drawPreview();
    if (n === 2) { if (!S.quiz) buildQuiz(); else if (S.phase === 'ready') drawReadiness(); else drawQuiz(); }
    if (n === 3) drawReady();
    updateActionBar();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function notice(text) { const n = $('psNotice'); n.textContent = text; n.hidden = false; setTimeout(() => { n.hidden = true; }, 4000); }
  function onNext() {
    if (S.step === 1) { go(2); return; }
    if (S.step !== 2) return;
    const q = S.quiz;
    if (S.phase === 'ready') {
      if (!S.ready.results) { notice(T('prestudy.finish_round_first')); return; }
      if (S.ready.results.pass || S.ready.round >= 2) { S.phase = 'done'; go(3); return; }
      startBoost(); updateActionBar(); return;
    }
    if (q && q.i < q.queue.length) { notice(T('prestudy.finish_round_first')); return; }
    if (S.phase === 'prime') {
      S.prime = S.quiz;
      if (S.mode === 'followup' || currentPlanMode() === 'light' || !readinessWords().length) { S.phase = 'done'; go(3); return; }
      startReadiness(1); return;
    }
    if (S.phase === 'boost') { S.quiz = S.prime; startReadiness(2); return; }
    go(3);
  }
  function onBack() { if (S.step > 1) go(S.step - 1); }

  // ---------- boot ----------
  // Open the prestudy_sessions row; unknown share is the snapshot at open.
  async function startSession() {
    try {
      const res = await window.authFetch(`/api/tests/${encodeURIComponent(S.slug)}/prestudy/session`, {
        method: 'POST',
        body: JSON.stringify({
          test_type: S.testType, trigger: S.trigger, plan_mode: S.mode === 'followup' ? null : currentPlanMode(), mode: S.mode,
          unknown_share: Math.round(S.snapshot * 1000) / 1000, session_block_id: S.block,
        }),
      });
      if (res.ok) S.sessionId = (await res.json()).session_id || null;
    } catch (e) { console.warn('[prestudy] session not recorded:', e); }
  }
  function showError(msg) { $('psLoading').hidden = true; $('psError').hidden = false; $('psErrorMsg').textContent = msg; }
  async function init() {
    if (window.LinguaI18n && window.LinguaI18n.init) { try { await window.LinguaI18n.init(); } catch { /* English fallback */ } }
    const parts = window.location.pathname.split('/').filter(Boolean);   // ['test', slug, 'prestudy']
    S.slug = decodeURIComponent(parts[1] || '');
    const params = new URLSearchParams(window.location.search);
    S.testType = params.get('type') === 'listening' ? 'listening' : 'reading';
    S.mode = params.get('mode') === 'followup' ? 'followup' : 'prime';
    S.trigger = ['auto', 'retry', 'opt_in'].includes(params.get('trigger')) ? params.get('trigger') : 'opt_in';
    S.planOverride = params.get('plan');
    S.block = /^prestudy_[0-9a-f-]{36}$/.test(params.get('block') || '') ? params.get('block') : null;
    S.returnTo = params.get('return') === 'session' ? 'session' : null;
    S.droppedToday = Math.max(0, Math.min(3, parseInt(params.get('dropped') || '0', 10) || 0));
    $('psSkip').href = testUrl();
    $('psSkip').onclick = (e) => { e.preventDefault(); takeTest(S.answers.length > 0); };
    $('psBackToPreview').href = `/test/${encodeURIComponent(S.slug)}/preview?type=${encodeURIComponent(S.testType)}`;
    $('psErrorSkip').href = testUrl();
    try {
      const res = await window.authFetch(`/api/tests/${encodeURIComponent(S.slug)}/prestudy${S.mode === 'followup' ? '?mode=followup' : ''}`);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      D = await res.json();
      S.followSenses = (D.followup_sense_ids || []).map(String);
    } catch (e) {
      console.error('[prestudy] load failed:', e);
      showError(T('prestudy.error_load'));
      return;
    }
    S.test = D.test;
    S.test.language_id = Number(S.test.language_id);
    S.glossLang = D.gloss_language_id;
    S.ability = D.ability_zipf != null ? Number(D.ability_zipf) : 5.0;
    if (!Array.isArray(S.test.vocab_token_map) || !S.test.vocab_token_map.length) {
      // no word map: build a single-token passage so the page still shows the text
      S.test.vocab_token_map = [[S.test.transcript || '', null]];
    }
    // exercises the renderers cannot draw are dropped up front
    Object.keys(D.exercises || {}).forEach((sid) => { D.exercises[sid] = D.exercises[sid].filter(exerciseUsable); });
    S.snapshot = analyse().share;
    if (window.ActiveTimer && window.ActiveTimer.create) { S.timer = window.ActiveTimer.create(); S.timer.start(); }
    startSession();

    $('psAids').onchange = (e) => { S.aids = e.target.value; drawPreview(); };
    $('psAidsWrap').hidden = !(S.test.language_id === ZH || S.test.language_id === JA);
    $('psHl').onchange = (e) => { S.hl = e.target.checked; $('psPassage').classList.toggle('hl', S.hl); };
    $('psNextStep').onclick = onNext;
    $('psBack').onclick = onBack;
    $('psTakeTest').onclick = () => takeTest(true);
    $('psProduce').onclick = startProduce;
    $('psBackToSession').onclick = backToSession;
    $('psScrim').onclick = hidePop;
    document.addEventListener('click', (e) => { const POP = $('psPop'); if (POP && !POP.contains(e.target)) hidePop(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hidePop(); });
    document.querySelectorAll('.ps-step').forEach((s) => {
      const h = () => {
        const n = parseInt(s.dataset.step, 10);
        if (n === 3 && S.step !== 3 && !(S.phase === 'done')) { S.phase = 'done'; }
        go(n);
      };
      s.onclick = h;
      s.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); h(); } };
    });

    $('psLoading').hidden = true; $('psMain').hidden = false;
    if (S.mode === 'followup') {
      // after the attempt: no preview, a short prime, then Produce
      const s1 = document.querySelector('.ps-step[data-step="1"]'); if (s1) s1.hidden = true;
      const s2 = document.querySelector('.ps-step[data-step="2"]'); if (s2) s2.textContent = T('prestudy.step_followup');
      const s3 = document.querySelector('.ps-step[data-step="3"]'); if (s3) s3.textContent = T('prestudy.step_produce');
      go(2);
    } else {
      go(1);
    }
  }

  // exposed for unit-style checks in the browser console and tests
  window.LinguaPrestudy = { gradeJa, gradeZh, parsePinyinInput, kanaToRomaji, normRomaji, readingParts, bktUpdate, bktUpdateIdk };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
