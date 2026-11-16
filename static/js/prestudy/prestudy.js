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
  const ZH = 1,
    EN = 2,
    JA = 3;
  const LANGCODE = { 1: 'zh', 2: 'en', 3: 'ja' };
  const SENT_END = /[。！？!?]$/;
  const SLIP = 0.05,
    GUESS = 0.25,
    TRANSIT = 0.05; // word-test BKT (knowledge_service)
  const PRIOR_K = 1.5,
    PRIOR_B = Math.log(0.85 / 0.15); // zipf prior (recommended_tests_ranked)
  const MARKER_PREFIX = 'prestudy:';

  const STAGES = [
    { k: 'read_typed', label: 'prestudy.stage_reading', ask: 'prestudy.ask_read' },
    { k: 'def_mc', label: 'prestudy.stage_meaning', ask: 'prestudy.ask_def' },
    { k: 'read_typed2', label: 'prestudy.stage_reading', ask: 'prestudy.ask_read_again' },
    { k: 'rev_mc', label: 'prestudy.stage_meaning', ask: 'prestudy.ask_rev' },
    { k: 'cloze_mc', label: 'prestudy.stage_use', ask: 'prestudy.ask_cloze' },
    { k: 'ex_use', label: 'prestudy.stage_practice', ask: 'prestudy.ask_exercise' },
    { k: 'ex_judge', label: 'prestudy.stage_practice', ask: 'prestudy.ask_exercise' },
  ];

  let D = null; // payload from the API
  const S = {
    slug: null,
    testType: 'reading',
    test: null,
    glossLang: null,
    ability: 5.0,
    hl: true,
    aids: 'unknown',
    know: {},
    snapshot: 0,
    shown: new Set(),
    quiz: null,
    prime: null,
    ready: null,
    phase: 'prime',
    answers: [],
    exAnswers: [],
    evidencePosted: false,
    exUsed: new Set(),
    step: 1,
    // 'prime' before the attempt; 'followup' after it (words behind wrong answers)
    mode: 'prime',
    trigger: 'opt_in',
    planOverride: null,
    block: null,
    returnTo: null,
    droppedToday: 0,
    sessionId: null,
    timer: null,
    followSenses: [],
    canProduce: true, // payload produce_available (false: the follow-up ends without Produce)
    added: new Set(), // senses the learner marked "I don't know this" in the preview
  };
  const FOLLOWUP_STAGES = ['read_typed', 'def_mc', 'cloze_mc'];
  const FOLLOWUP_MAX_WORDS = 5;
  const LIGHT_STAGES = ['read_typed', 'def_mc']; // the short warm-up for 5-25% unknown
  // The prime drills every unknown, encountered and learning word (below
  // probably_known), plus any word the learner adds from the passage.
  const DRILL_MAX_P = 0.75;
  const MAX_EST_MINUTES = 30;

  const $ = (id) => document.getElementById(id);
  const T = (key, params) => (window.LinguaI18n ? window.LinguaI18n.t(key, params) : key);
  // For keys added by the 2026-11 redesign (static/i18n/_redesign/prestudy.json):
  // the English fallback shows until they are merged into the locale files.
  const Tf = (key, params, fallback) => {
    const v = T(key, params);
    return v && v !== key ? v : fallback;
  };
  // Status colour of a word (passage highlight, list dot, popover tag).
  const STATUS_TAG = {
    unknown: 'bad',
    encountered: 'warn',
    learning: 'brand',
    probably_known: 'ok',
    known: 'ok',
  };
  const reducedMotion = () =>
    !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  // The one region that scrolls on a task screen (FOUNDATION.md): reset it, never the window.
  function stageTop() {
    const st = $('psStage');
    if (st) st.scrollTop = 0;
  }
  function revealInStage(el) {
    if (el && el.scrollIntoView)
      el.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' });
  }

  // ---------- knowledge model ----------
  function sigmoid(x) {
    return 1 / (1 + Math.exp(-x));
  }
  function priorP(sense) {
    if (!sense || sense.freq == null) return 0.3;
    return sigmoid(PRIOR_K * (sense.freq - S.ability) + PRIOR_B);
  }
  function basePKnown(sid) {
    const k = D.knowledge[sid];
    return k ? k.p : priorP(D.senses[sid]);
  }
  function pNow(sid) {
    return S.know[sid] != null ? S.know[sid] : basePKnown(sid);
  }
  function status(p) {
    return p < 0.2
      ? 'unknown'
      : p < 0.5
        ? 'encountered'
        : p < 0.75
          ? 'learning'
          : p < 0.9
            ? 'probably_known'
            : 'known';
  }
  function bktUpdateIdk(p) {
    const post = (p * SLIP) / (p * SLIP + (1 - p));
    return post + (1 - post) * TRANSIT;
  }
  function bktUpdate(p, correct) {
    const post = correct
      ? (p * (1 - SLIP)) / (p * (1 - SLIP) + (1 - p) * GUESS)
      : (p * SLIP) / (p * SLIP + (1 - p) * (1 - GUESS));
    return post + (1 - post) * TRANSIT;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
    );
  }
  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  function gloss(sid) {
    const s = D.senses[sid];
    if (!s) return {};
    return (
      s.glosses[String(S.glossLang)] ||
      s.glosses[String(S.test.language_id)] ||
      Object.values(s.glosses)[0] ||
      {}
    );
  }
  function tokenMap() {
    return S.test.vocab_token_map || [];
  }

  // ---------- analysis ----------
  function analyse() {
    const t = S.test,
      occ = {};
    for (const [, sid] of tokenMap()) {
      if (sid) occ[sid] = (occ[sid] || 0) + 1;
    }
    const qSenses = new Set();
    for (const q of D.questions) (q.sense_ids || []).forEach((s) => qSenses.add(String(s)));
    const senses = (t.vocab_sense_ids || []).map(String).filter((s) => D.senses[s]);
    const rows = senses.map((sid) => {
      const p = pNow(sid);
      return {
        sid,
        p,
        st: status(p),
        occ: occ[sid] || 0,
        inQ: qSenses.has(sid),
        freq: D.senses[sid].freq,
      };
    });
    const unknown = rows.filter((r) => r.p < 0.5).length;
    const share = senses.length ? unknown / senses.length : 0;
    // key words: question-linked, then most frequent in the passage, then rarer words first
    // drill list: every word below probably_known, plus the ones the learner added;
    // ranked question-linked first, then most frequent in the passage, then rarer words
    rows.forEach((r) => {
      r.added = S.added.has(r.sid);
    });
    const ranked = rows
      .filter((r) => r.added || r.p < DRILL_MAX_P)
      .sort(
        (a, b) =>
          b.inQ - a.inQ ||
          b.occ - a.occ ||
          (a.freq == null ? 9 : a.freq) - (b.freq == null ? 9 : b.freq)
      );
    return { rows, unknown, share, ranked, n: senses.length };
  }
  function trigger(share) {
    if (share > 0.25) return { mode: 'full', cls: 'bad', label: T('prestudy.mode_full') };
    if (share >= 0.05) return { mode: 'light', cls: 'ok', label: T('prestudy.mode_light') };
    return { mode: 'none', cls: 'ok', label: T('prestudy.mode_none') };
  }
  function exercisesFor(sid) {
    return (D.exercises && D.exercises[String(sid)]) || [];
  }
  function estMinutes(a) {
    const k = a.ranked.length;
    if (currentPlanMode() === 'light') return Math.max(1, Math.round((k * 2 * 8) / 60));
    const ex = a.ranked.filter((r) => exercisesFor(r.sid).length).length;
    return Math.min(
      MAX_EST_MINUTES,
      Math.max(2, Math.round((60 + k * 5 * 8 + ex * 2 * 20 + 5 * 8) / 60))
    );
  }
  function sentences() {
    const out = [];
    let cur = [];
    tokenMap().forEach((tok, i) => {
      cur.push(i);
      if (SENT_END.test(tok[0])) {
        out.push(cur);
        cur = [];
      }
    });
    if (cur.length) out.push(cur);
    return out;
  }
  function passageSentenceFor(sid, blank) {
    const tm = tokenMap();
    for (const idxs of sentences()) {
      if (idxs.some((i) => String(tm[i][1]) === sid)) {
        return idxs
          .map((i) => {
            const [surf, s] = tm[i];
            return String(s) === sid
              ? blank
                ? '<span class="ps-blank ld-blank">　</span>'
                : `<mark>${esc(surf)}</mark>`
              : esc(surf);
          })
          .join('');
      }
    }
    return '';
  }

  // ---------- reading aids (furigana / pinyin) ----------
  const PY_VOWELS = { a: 'āáǎàa', e: 'ēéěèe', i: 'īíǐìi', o: 'ōóǒòo', u: 'ūúǔùu', v: 'ǖǘǚǜü' };
  function toneMark(syl, tone) {
    syl = String(syl).toLowerCase().replace('u:', 'v');
    const t = tone >= 1 && tone <= 4 ? tone - 1 : 4;
    const put = (ch) => syl.replace(ch, PY_VOWELS[ch][t]);
    if (syl.includes('a')) return put('a');
    if (syl.includes('e')) return put('e');
    if (syl.includes('ou')) return put('o');
    for (let i = syl.length - 1; i >= 0; i--) {
      if (PY_VOWELS[syl[i]]) return syl.slice(0, i) + PY_VOWELS[syl[i]][t] + syl.slice(i + 1);
    }
    return syl;
  }
  function charAids() {
    const t = S.test,
      n = (t.transcript || '').length,
      out = new Array(n).fill(null);
    if (
      t.language_id === JA &&
      t.furigana_payload &&
      Array.isArray(t.furigana_payload.transcript)
    ) {
      // The payload's tokens are not a lossless copy of the transcript: the
      // tokenizer drops whitespace (e.g. the "\n\n" between paragraphs), so a
      // running character count drifts and readings land on the wrong kanji.
      // Re-anchor each token on the transcript text before placing its aids.
      const src = t.transcript || '';
      let pos = 0,
        gid = 0;
      for (const tok of t.furigana_payload.transcript) {
        const text = tok.base || tok.text || '';
        if (!text) continue;
        if (!src.startsWith(text, pos)) {
          let p = pos;
          while (p < n && /\s/.test(src[p])) p++;
          if (!src.startsWith(text, p)) {
            const found = src.indexOf(text, pos);
            if (found < 0 || found - pos > 8) break; // lost alignment: show no aids rather than wrong ones
            p = found;
          }
          pos = p;
        }
        if (tok.kind === 'ruby') {
          const segs =
            tok.segments && tok.segments.length ? tok.segments : [{ base: tok.base, rt: tok.rt }];
          let p = pos;
          for (const sg of segs) {
            const b = sg.base || '';
            if (sg.rt) {
              gid++;
              for (let k = 0; k < b.length; k++)
                out[p + k] = { gid, rt: sg.rt, start: p, end: p + b.length };
            }
            p += b.length;
          }
        }
        pos += text.length;
      }
    } else if (t.language_id === ZH && Array.isArray(t.pinyin_payload)) {
      t.pinyin_payload.forEach((c, i) => {
        if (i < n && c && !c.is_punctuation && c.pinyin_text)
          out[i] = {
            gid: i + 1,
            rt: toneMark(c.pinyin_text, c.context_tone != null ? c.context_tone : c.base_tone),
            start: i,
            end: i + 1,
          };
      });
    }
    return out;
  }
  function tokenWithAids(surf, start, aids) {
    let html = '',
      i = 0;
    while (i < surf.length) {
      const a = aids[start + i];
      if (a && a.start === start + i && a.end <= start + surf.length) {
        html += `<ruby>${esc(surf.slice(i, i + (a.end - a.start)))}<rt>${esc(a.rt)}</rt></ruby>`;
        i += a.end - a.start;
      } else {
        html += esc(surf[i]);
        i++;
      }
    }
    return html;
  }

  // ---------- reading graders ----------
  function readingParts(s) {
    if (!s || !s.reading) return null;
    const m = /^(.*?)\s*\((.*)\)\s*$/.exec(s.reading); // zh: "mù tou (mu4 tou5)"
    return {
      shown: (m ? m[1] : s.reading).trim(),
      numbered: m ? m[2].trim() : null,
      hanzi: s.lemma || null,
    };
  }
  const KANA = {
    あ: 'a',
    い: 'i',
    う: 'u',
    え: 'e',
    お: 'o',
    か: 'ka',
    き: 'ki',
    く: 'ku',
    け: 'ke',
    こ: 'ko',
    さ: 'sa',
    し: 'shi',
    す: 'su',
    せ: 'se',
    そ: 'so',
    た: 'ta',
    ち: 'chi',
    つ: 'tsu',
    て: 'te',
    と: 'to',
    な: 'na',
    に: 'ni',
    ぬ: 'nu',
    ね: 'ne',
    の: 'no',
    は: 'ha',
    ひ: 'hi',
    ふ: 'fu',
    へ: 'he',
    ほ: 'ho',
    ま: 'ma',
    み: 'mi',
    む: 'mu',
    め: 'me',
    も: 'mo',
    や: 'ya',
    ゆ: 'yu',
    よ: 'yo',
    ら: 'ra',
    り: 'ri',
    る: 'ru',
    れ: 're',
    ろ: 'ro',
    わ: 'wa',
    を: 'o',
    ん: 'n',
    が: 'ga',
    ぎ: 'gi',
    ぐ: 'gu',
    げ: 'ge',
    ご: 'go',
    ざ: 'za',
    じ: 'ji',
    ず: 'zu',
    ぜ: 'ze',
    ぞ: 'zo',
    だ: 'da',
    ぢ: 'ji',
    づ: 'zu',
    で: 'de',
    ど: 'do',
    ば: 'ba',
    び: 'bi',
    ぶ: 'bu',
    べ: 'be',
    ぼ: 'bo',
    ぱ: 'pa',
    ぴ: 'pi',
    ぷ: 'pu',
    ぺ: 'pe',
    ぽ: 'po',
    ぁ: 'a',
    ぃ: 'i',
    ぅ: 'u',
    ぇ: 'e',
    ぉ: 'o',
    ゔ: 'vu',
  };
  const KANA_Y = { ゃ: 'ya', ゅ: 'yu', ょ: 'yo' };
  function kataToHira(s) {
    return s.replace(/[\u30a1-\u30f6]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
  }
  function kanaToRomaji(k) {
    k = kataToHira(k);
    let out = '';
    for (let i = 0; i < k.length; i++) {
      const c = k[i],
        n = k[i + 1];
      if (c === 'っ') {
        out += n && KANA[n] ? KANA[n][0] : '';
        continue;
      }
      if (c === 'ー') {
        out += out.slice(-1);
        continue;
      }
      if (KANA[c] && n && KANA_Y[n]) {
        const base = KANA[c];
        out +=
          (base.length === 3 ? base.slice(0, 2) : base[0]) +
          (base === 'shi' || base === 'chi' || base === 'ji' ? KANA_Y[n].slice(1) : KANA_Y[n]);
        i++;
        continue;
      }
      out += KANA[c] || c;
    }
    return out;
  }
  function normRomaji(r) {
    r = String(r)
      .toLowerCase()
      .normalize('NFC')
      .replace(/ā/g, 'aa')
      .replace(/ī/g, 'ii')
      .replace(/ū/g, 'uu')
      .replace(/ē/g, 'ee')
      .replace(/ō/g, 'oo')
      .replace(/ô/g, 'oo')
      .replace(/û/g, 'uu');
    r = r
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[\s'’-]/g, '');
    r = r
      .replace(/sy([auo])/g, 'sh$1')
      .replace(/ty([auo])/g, 'ch$1')
      .replace(/(?:zy|jy)([auo])/g, 'j$1')
      .replace(/cy([auo])/g, 'ch$1');
    r = r
      .replace(/si/g, 'shi')
      .replace(/ti/g, 'chi')
      .replace(/tu/g, 'tsu')
      .replace(/(?<![sc])hu/g, 'fu')
      .replace(/zi/g, 'ji')
      .replace(/dzu|du/g, 'zu')
      .replace(/nn([aiueo])/g, 'n$1')
      .replace(/^wo$/, 'o');
    return r.replace(/ou/g, 'oo');
  }
  function gradeJa(input, kana) {
    const u = String(input).trim();
    if (!u) return { ok: false };
    if (/[\u3040-\u30ff]/.test(u))
      return {
        ok: kataToHira(u).replace(/\s/g, '') === kataToHira(kana).replace(/\s/g, ''),
        mode: 'kana',
      };
    return { ok: normRomaji(u) === normRomaji(kanaToRomaji(kana)), mode: 'romaji' };
  }
  const TONE_MARKS = {
    ā: ['a', 1],
    á: ['a', 2],
    ǎ: ['a', 3],
    à: ['a', 4],
    ē: ['e', 1],
    é: ['e', 2],
    ě: ['e', 3],
    è: ['e', 4],
    ī: ['i', 1],
    í: ['i', 2],
    ǐ: ['i', 3],
    ì: ['i', 4],
    ō: ['o', 1],
    ó: ['o', 2],
    ǒ: ['o', 3],
    ò: ['o', 4],
    ū: ['u', 1],
    ú: ['u', 2],
    ǔ: ['u', 3],
    ù: ['u', 4],
    ǖ: ['v', 1],
    ǘ: ['v', 2],
    ǚ: ['v', 3],
    ǜ: ['v', 4],
    ü: ['v', 0],
  };
  function pinyinSyllables(numbered) {
    return numbered
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .map((x) => {
        const m = /^([a-zü:]+)([0-5])?$/.exec(x.replace('ü', 'v').replace('u:', 'v'));
        return m
          ? { seg: m[1], tone: m[2] ? (+m[2] === 0 ? 5 : +m[2]) : null }
          : { seg: x, tone: null };
      });
  }
  function parsePinyinInput(u) {
    let s = String(u).toLowerCase().trim().replace(/u:/g, 'v');
    let hasMarks = false;
    s = s.replace(/[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]/g, (c) => {
      const [v, t] = TONE_MARKS[c];
      if (t) hasMarks = true;
      return v + (t ? '<' + t + '>' : '');
    });
    const parts = s.split(/[\s'’-]+/).filter(Boolean);
    const segs = [],
      ts = [];
    for (const p of parts) {
      let seg = p.replace(/<\d>/g, ''),
        tone = null;
      const m = /<(\d)>/.exec(p);
      if (m) tone = +m[1];
      const n = /([0-5])$/.exec(seg);
      if (n) {
        tone = +n[1];
        seg = seg.slice(0, -1);
      }
      if (tone === 0) tone = 5;
      if (hasMarks && tone == null && /[a-z]/.test(seg)) tone = 5;
      segs.push(seg);
      ts.push(tone);
    }
    const haveTones = ts.length && ts.every((t) => t != null);
    return { segs, tones: haveTones ? ts : null };
  }
  // Stored readings carry dictionary (citation) tones. Speech changes some of
  // them by context (tone sandhi), so a learner typing either form passes.
  // Mirrors services/pinyin_service._apply_sandhi_to_chunk.
  const YI_KEEPS_TONE_AFTER = new Set([
    '第',
    '统',
    '唯',
    '初',
    '十',
    '万',
    '之',
    '其',
    '归',
    '划',
    '专',
    '同',
    '单',
  ]);
  function sandhiTones(tones, chars) {
    const out = tones.slice();
    const ch = chars && chars.length === tones.length ? chars : null;
    for (let i = 0; i < tones.length; i++) {
      const next = i + 1 < tones.length ? tones[i + 1] : null;
      const c = ch ? ch[i] : null,
        prevC = ch && i > 0 ? ch[i - 1] : null,
        nextC = ch && next != null ? ch[i + 1] : null;
      if (c === '一' || c === '不') {
        if (next == null) continue;
        if (prevC && prevC === nextC)
          out[i] = 5; // 看一看, 好不好
        else if (c === '一' && YI_KEEPS_TONE_AFTER.has(prevC))
          continue; // 统一, 第一
        else if (next === 4) out[i] = 2;
        else if (c === '一' && next !== 5) out[i] = 4;
      } else if (tones[i] === 3 && next === 3) {
        out[i] = 2;
      }
    }
    return out;
  }
  // Any syllable after the first may be said neutral or with its full tone.
  function toneAccepted(t, i, citation, spoken) {
    return t === citation[i] || t === spoken[i] || (i > 0 && (t === 5 || citation[i] === 5));
  }
  function gradeZh(segs, tones, numbered, hanzi) {
    const ref = pinyinSyllables(numbered);
    const citation = ref.map((r) => r.tone);
    const spoken = sandhiTones(
      citation,
      hanzi ? Array.from(String(hanzi).replace(/[^\u4e00-\u9fff]/g, '')) : null
    );
    const segOk = segs.join('') === ref.map((r) => r.seg).join('');
    const toneOk =
      tones != null &&
      tones.length === ref.length &&
      tones.every((t, i) => toneAccepted(t, i, citation, spoken));
    return { segOk, toneOk, ok: segOk && toneOk, ref };
  }
  function gradeReading(input, rp) {
    if (S.test.language_id === ZH) {
      const pi = parsePinyinInput(input);
      return gradeZh(pi.segs, pi.tones, rp.numbered, rp.hanzi).ok;
    }
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
    const t = S.test,
      a = analyse(),
      tr = trigger(S.snapshot);
    $('psTitle').textContent = t.title || '';
    $('psTitle').lang = LANGCODE[t.language_id] || '';
    $('psChips').innerHTML =
      `<span class="ld-tag ld-tag--${tr.cls} ps-chip ${tr.cls}">${esc(tr.label)}</span>` +
      `<span class="ld-tag ps-chip">${esc(T('prestudy.unknown_share', { pct: Math.round(S.snapshot * 100) }))}</span>` +
      `<span class="ld-tag ps-chip">${esc(T('prestudy.minutes', { n: estMinutes(a) }))}</span>`;
    setupAudio(t.audio_url);

    const P = $('psPassage');
    P.innerHTML = '';
    P.lang = LANGCODE[t.language_id] || '';
    const rowBy = Object.fromEntries(a.rows.map((r) => [r.sid, r]));
    const aids = charAids();
    const offs = [];
    {
      let o = 0;
      tokenMap().forEach(([surf]) => {
        offs.push(o);
        o += surf.length;
      });
    }
    const quizzed = new Set(S.quiz ? S.quiz.words : []);
    sentences().forEach((idxs) => {
      const sp = document.createElement('span');
      sp.className = 'ps-sent';
      idxs.forEach((i) => {
        const [surf, rawSid] = tokenMap()[i];
        const sid = rawSid ? String(rawSid) : null;
        const e = document.createElement('span');
        e.className = 'ps-tok';
        const r0 = sid ? rowBy[sid] : null;
        const showAid = S.aids === 'all' || (S.aids === 'unknown' && r0 && r0.p < 0.5);
        if (showAid) e.innerHTML = tokenWithAids(surf, offs[i], aids);
        else e.textContent = surf;
        if (sid && D.senses[sid]) {
          e.classList.add('linked');
          if (r0) e.classList.add(r0.st);
          if (quizzed.has(sid)) e.classList.add('quizzed');
          e.dataset.sid = sid;
          e.tabIndex = 0;
          e.setAttribute('role', 'button');
          e.onclick = (ev) => {
            ev.stopPropagation();
            showPop(e, sid);
          };
          e.onkeydown = (ev) => {
            if (ev.key === 'Enter' || ev.key === ' ') {
              ev.preventDefault();
              ev.stopPropagation();
              showPop(e, sid);
            }
          };
        }
        sp.appendChild(e);
      });
      P.appendChild(sp);
    });
    P.classList.toggle('hl', S.hl);
    P.classList.toggle('aids', S.aids !== 'off');
    $('psStats').textContent = T('prestudy.passage_stats', {
      n: a.n,
      unknown: a.unknown,
      inq: a.rows.filter((r) => r.inQ && r.p < 0.5).length,
    });
    P.querySelectorAll('.ps-tok[data-sid]').forEach((e) => {
      e.classList.toggle('added', S.added.has(e.dataset.sid));
    });

    const W = $('psWordlist');
    W.innerHTML = '';
    $('psKwCount').textContent = T('prestudy.drill_words_count', { n: a.ranked.length });
    $('psKwN').textContent = String(a.ranked.length);
    const lang = LANGCODE[t.language_id] || '';
    a.ranked.forEach((r) => {
      const s = D.senses[r.sid],
        g = gloss(r.sid),
        nEx = exercisesFor(r.sid).length;
      const rd = (readingParts(s) || {}).shown || '';
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'ld-trow ps-word';
      el.dataset.sid = r.sid;
      el.innerHTML = `<span class="ps-dot ${r.st}" aria-hidden="true"></span>
        <span class="ld-trow__mid ps-word-main"><span><span class="ps-lem ld-tl" lang="${lang}">${esc(s.lemma)}</span>${rd ? ` <span class="ps-rd">${esc(rd)}</span>` : ''}</span>
          <small class="ps-g">${esc(g.def || T('prestudy.no_gloss'))}</small></span>
        <span class="ps-tags">${r.added ? `<span class="ld-tag ld-tag--warn">${esc(T('prestudy.added_chip'))}</span>` : ''}${r.inQ ? `<span class="ld-tag ld-tag--brand">${esc(T('prestudy.in_question'))}</span>` : ''}${nEx ? `<span class="ld-tag ld-tag--ok">${esc(T('prestudy.exercises_count', { count: nEx }))}</span>` : ''}<span class="ps-occ ld-num">${esc(T('prestudy.occurrences', { n: r.occ }))}</span></span>`;
      el.onclick = (ev) => {
        ev.stopPropagation();
        const tok = P.querySelector(`.ps-tok[data-sid="${r.sid}"]`);
        // the passage sits in the other tab: anchor the word sheet on this row
        if (tok && tok.offsetParent) {
          revealInStage(tok);
          showPop(tok, r.sid, el);
        } else showPop(el, r.sid, el);
      };
      W.appendChild(el);
    });
    if (!a.ranked.length)
      W.innerHTML = `<div class="ld-note">${esc(T('prestudy.no_key_words'))}</div>`;
  }
  function setTab(tab) {
    S.tab = tab === 'words' ? 'words' : 'passage';
    document.querySelectorAll('#psTabs .ps-tab').forEach((b) => {
      const on = b.dataset.tab === S.tab;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
    $('psPanePassage').hidden = S.tab !== 'passage';
    $('psPaneWords').hidden = S.tab !== 'words';
    hidePop();
  }
  function setAids(v) {
    S.aids = ['unknown', 'all', 'off'].includes(v) ? v : 'unknown';
    document.querySelectorAll('#psAids button').forEach((b) => {
      const on = b.dataset.v === S.aids;
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
  }

  // ---------- audio (custom controls over the hidden <audio>) ----------
  function fmtTime(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0');
  }
  function setupAudio(url) {
    const wrap = $('psAudioWrap'),
      au = $('psAudio');
    if (!wrap || !au) return;
    if (!url) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    if (au.dataset.src === url) return;
    au.dataset.src = url;
    au.src = url;
    const play = $('psPlay'),
      seek = $('psSeek'),
      time = $('psTime'),
      wave = $('psWave');
    if (wave && !wave.childElementCount) {
      for (let i = 0; i < 32; i++) {
        const bar = document.createElement('i');
        bar.style.setProperty(
          '--h',
          String(28 + Math.round(Math.abs(Math.sin(i * 1.7) + Math.sin(i * 0.6)) * 34))
        );
        wave.appendChild(bar);
      }
    }
    const paint = () => {
      const d = au.duration,
        frac = d && isFinite(d) ? au.currentTime / d : 0;
      if (seek && document.activeElement !== seek) seek.value = String(Math.round(frac * 1000));
      if (wave)
        Array.from(wave.children).forEach((b, i) =>
          b.classList.toggle('on', (i + 0.5) / wave.children.length <= frac)
        );
      if (time)
        time.textContent = fmtTime(au.currentTime) + (d && isFinite(d) ? ' / ' + fmtTime(d) : '');
    };
    const state = () => {
      const on = !au.paused && !au.ended;
      play.setAttribute('aria-pressed', on ? 'true' : 'false');
      play.setAttribute(
        'aria-label',
        on
          ? Tf('prestudy.audio_pause', null, 'Pause audio')
          : Tf('prestudy.audio_play', null, 'Play audio')
      );
      play.innerHTML = `<i class="bi ${on ? 'bi-pause-fill' : 'bi-play-fill'}" aria-hidden="true"></i>`;
      wrap.classList.toggle('is-playing', on);
    };
    au.onerror = () => {
      $('psAudioNote').hidden = false;
      wrap.classList.add('is-broken');
      play.disabled = true;
    };
    au.ontimeupdate = paint;
    au.onloadedmetadata = paint;
    au.onplay = state;
    au.onpause = state;
    au.onended = state;
    play.onclick = () => {
      if (au.paused) {
        const pr = au.play();
        if (pr && pr.catch)
          pr.catch(() => {
            $('psAudioNote').hidden = false;
          });
      } else au.pause();
    };
    if (seek)
      seek.oninput = () => {
        const d = au.duration;
        if (d && isFinite(d)) au.currentTime = (Number(seek.value) / 1000) * d;
        paint();
      };
    state();
    paint();
  }

  // ---------- popover ----------
  // Phones get the word as a bottom sheet over a scrim; wide screens an anchored popover.
  const sheetMode = () => !!(window.matchMedia && window.matchMedia('(width < 768px)').matches);
  let popReturn = null;
  function showPop(anchor, sid, returnTo) {
    const POP = $('psPop'),
      s = D.senses[sid],
      g = gloss(sid),
      p = pNow(sid);
    S.shown.add(sid);
    const r = analyse().rows.find((x) => x.sid === sid) || {};
    const rp = readingParts(s),
      lang = LANGCODE[S.test.language_id] || '';
    POP.innerHTML = `<div class="ps-pop-handle" aria-hidden="true"></div>
      <div class="ps-pop-head"><span class="ps-pop-w ld-tl" id="psPopWord" lang="${lang}">${esc(s.lemma)}</span><span class="ps-pop-r">${esc(rp ? rp.shown : '')}${s.pos ? ' · ' + esc(s.pos) : ''}</span></div>
      <div class="ps-pop-d">${esc(g.def || T('prestudy.no_gloss'))}</div>
      ${g.ex ? `<div class="ps-pop-ex ld-tl" lang="${lang}">${esc(g.ex)}</div>` : ''}
      <div class="ps-pop-meta ld-wrap"><span class="ld-tag ld-tag--${STATUS_TAG[status(p)]}">${esc(T('prestudy.status_' + status(p)))}</span><span class="ld-tag">${esc(T('prestudy.pop_in_passage', { n: r.occ || 0 }))}</span>${r.inQ ? `<span class="ld-tag ld-tag--brand">${esc(T('prestudy.in_question'))}</span>` : ''}${p < DRILL_MAX_P && !S.added.has(sid) && S.mode !== 'followup' ? `<span class="ld-tag">${esc(T('prestudy.pop_in_drill'))}</span>` : ''}</div>
      <div class="ld-row ps-pop-actions">${popAddButton(sid, p)}<button type="button" class="ld-btn ld-btn--sm ld-btn--ghost ps-pop-close" id="psPopClose">${esc(T('prestudy.pop_close'))}</button></div>`;
    $('psPopClose').onclick = (ev) => {
      ev.stopPropagation();
      hidePop(true);
    };
    const addBtn = $('psPopAdd');
    if (addBtn)
      addBtn.onclick = (ev) => {
        ev.stopPropagation();
        toggleAdded(sid);
        hidePop(true);
      };
    const sheet = sheetMode();
    popReturn = returnTo || anchor;
    POP.classList.toggle('ps-pop--sheet', sheet);
    POP.setAttribute('aria-modal', sheet ? 'true' : 'false');
    POP.hidden = false;
    $('psScrim').hidden = false;
    $('psScrim').classList.toggle('is-dim', sheet);
    if (sheet) {
      POP.style.top = '';
      POP.style.left = '';
    } else {
      // position: fixed, so viewport coordinates (the page itself never scrolls)
      const rc = anchor.getBoundingClientRect();
      POP.style.left = '0px';
      POP.style.top = '0px';
      const w = POP.offsetWidth,
        h = POP.offsetHeight,
        vw = document.documentElement.clientWidth,
        vh = window.innerHeight;
      const below = rc.bottom + 6,
        top = below + h > vh - 8 && rc.top - h - 6 > 8 ? rc.top - h - 6 : below;
      POP.style.top = Math.max(8, top) + 'px';
      POP.style.left = Math.max(8, Math.min(rc.left, vw - w - 8)) + 'px';
    }
    const first = POP.querySelector('#psPopAdd') || $('psPopClose');
    if (first) first.focus({ preventScroll: true });
  }
  // Words below probably_known are always drilled; any other linked word can be
  // added by the learner ("I don't know this") and removed again.
  function popAddButton(sid, p) {
    if (S.mode === 'followup') return '';
    if (p < DRILL_MAX_P && !S.added.has(sid)) return '';
    const on = S.added.has(sid);
    return `<button type="button" class="ld-btn ld-btn--sm ld-grow ${on ? 'ld-btn--ghost' : ''}" id="psPopAdd">${esc(T(on ? 'prestudy.pop_remove' : 'prestudy.pop_add'))}</button>`;
  }
  function toggleAdded(sid) {
    if (S.added.has(sid)) S.added.delete(sid);
    else S.added.add(sid);
    syncQuizWithAdded(sid);
    drawPreview();
  }
  // A word added or removed after the prime was built: rebuild it if nothing has
  // been answered yet, otherwise append the new word's items to the end.
  function syncQuizWithAdded(sid) {
    const q = S.quiz;
    if (!q || S.mode === 'followup' || S.phase !== 'prime') return;
    if (!q.queue.some((it) => it.answered != null)) {
      S.quiz = null;
      return;
    }
    if (!S.added.has(sid) || q.words.includes(sid)) return;
    const a = analyse(),
      allowed = currentPlanMode() === 'light' ? LIGHT_STAGES : null;
    STAGES.filter((st) => !allowed || allowed.includes(st.k)).forEach((st) => {
      const it = buildItem(st.k, sid, a);
      if (it) q.queue.push(it);
    });
    q.words.push(sid);
    q.perWord[sid] = newPerWord(sid);
    $('psQuizMode').textContent = T('prestudy.prime_header', {
      words: q.words.length,
      items: q.queue.length,
    });
  }
  function hidePop(restoreFocus) {
    const POP = $('psPop'),
      open = POP && !POP.hidden;
    if (POP) POP.hidden = true;
    const sc = $('psScrim');
    if (sc) sc.hidden = true;
    // give focus back to what opened the word (when it is still on screen)
    // (adding or removing a word redraws the passage and list: find the new copy)
    let back = popReturn;
    popReturn = null;
    if (back && !back.isConnected && back.dataset && back.dataset.sid) {
      const where = back.classList.contains('ps-word')
        ? '#psWordlist .ps-word'
        : '#psPassage .ps-tok';
      back = document.querySelector(`${where}[data-sid="${back.dataset.sid}"]`);
    }
    if (restoreFocus === true && open && back && back.isConnected && back.offsetParent)
      back.focus({ preventScroll: true });
  }

  // ---------- exercises ----------
  function pickExercise(sid, group) {
    const pool = exercisesFor(sid).filter((e) => e.group === group && !S.exUsed.has(e.id));
    if (!pool.length) return null;
    const e = pool[Math.floor(Math.random() * pool.length)];
    S.exUsed.add(e.id);
    return e;
  }
  function exItem(stage, sid, group) {
    const e = pickExercise(sid, group) || pickExercise(sid, group === 'use' ? 'judge' : 'use');
    return e ? { stage, sid, kind: 'ex', ex: e } : null;
  }
  function exerciseUsable(e) {
    const c = e.c || {};
    switch (e.type) {
      case 'cloze_completion':
      case 'particle_selection':
      case 'morphology_slot':
        return (
          Array.isArray(c.options) &&
          c.options.length > 1 &&
          c.correct_answer != null &&
          c.sentence_with_blank
        );
      case 'definition_match':
        return Array.isArray(c.options) && c.options.length > 1 && c.correct_definition != null;
      case 'synonym_antonym_match':
        return Array.isArray(c.options) && c.options.length > 1 && c.correct_answer != null;
      case 'tl_nl_translation':
        return Array.isArray(c.options) && c.options.length > 1 && c.correct_nl != null;
      case 'semantic_discrimination':
        return Array.isArray(c.sentences) && c.sentences.some((x) => x && x.is_correct === true);
      case 'spot_incorrect_sentence':
        return Array.isArray(c.sentences) && c.sentences.some((x) => x && x.is_correct === false);
      case 'cloze_typed':
        return c.sentence_with_blank && c.answer && (c.answer.accepted || []).length;
      case 'jumbled_sentence':
        return (
          Array.isArray(c.chunks) &&
          Array.isArray(c.correct_ordering) &&
          c.chunks.length === c.correct_ordering.length
        );
      default:
        return false;
    }
  }
  function blankify(text) {
    return esc(text).replace(/_{2,}|＿{2,}/, '<span class="ps-blank ld-blank">　</span>');
  }
  function drawExercise(it, head) {
    const B = $('psQBody'),
      e = it.ex,
      c = e.c,
      t = e.type,
      lang = LANGCODE[S.test.language_id] || '';
    // the exercise's own instruction stands in for the generic "Exercise" ask
    const sub = `<p class="ld-eyebrow ps-ask ps-sub">${esc(T('prestudy.ex_' + t))}</p>`;
    // nlOpts: the options are in the learner's language (definitions, translations)
    const mc = (promptHtml, opts, correct, extra, nlOpts) => {
      it.correctText = correct;
      B.innerHTML = `${head}${sub}<div class="ps-ctx ld-tl" lang="${lang}">${promptHtml}</div><div class="ld-opts ps-opts">${opts.map((o, i) => optButton(o, i, !nlOpts)).join('')}</div><div id="psReveal" class="ps-revealwrap"></div>`;
      B.querySelectorAll('.ps-opt').forEach((b) => {
        b.onclick = () => {
          const v = opts[parseInt(b.dataset.i, 10)];
          answer(v === correct, v, extra());
        };
      });
    };
    if (t === 'cloze_completion' || t === 'particle_selection' || t === 'morphology_slot') {
      mc(blankify(c.sentence_with_blank), shuffle(c.options), c.correct_answer, () => ({
        detail: c.explanation || '',
        shown: c.original_sentence,
      }));
    } else if (t === 'definition_match') {
      mc(
        `<b>${esc(c.word)}</b>${c.pronunciation ? ' <span class="ps-note">' + esc(c.pronunciation) + '</span>' : ''}`,
        shuffle(c.options),
        c.correct_definition,
        () => ({}),
        true
      );
    } else if (t === 'synonym_antonym_match') {
      mc(
        `<b>${esc(c.word)}</b> <span class="ps-note">→ ${esc(c.relation || '')}</span>`,
        shuffle(c.options),
        c.correct_answer,
        () => ({})
      );
    } else if (t === 'tl_nl_translation') {
      mc(esc(c.tl_sentence), shuffle(c.options), c.correct_nl, () => ({}), true);
    } else if (t === 'semantic_discrimination' || t === 'spot_incorrect_sentence') {
      const wantCorrect = t === 'semantic_discrimination';
      const sents = shuffle(c.sentences.filter(Boolean));
      const target = sents.find((x) => x.is_correct === wantCorrect);
      it.correctText = target.text;
      B.innerHTML = `${head}${sub}<div class="ld-opts ps-opts">${sents.map((x, i) => optButton(x.text, i, true)).join('')}</div><div id="psReveal" class="ps-revealwrap"></div>`;
      B.querySelectorAll('.ps-opt').forEach((b) => {
        b.onclick = () => {
          const x = sents[parseInt(b.dataset.i, 10)];
          answer(x === target, x.text, {
            detail: wantCorrect ? c.explanation || '' : target.error_description || '',
          });
        };
      });
    } else if (t === 'cloze_typed') {
      const ph = T('prestudy.typed_placeholder_' + (LANGCODE[S.test.language_id] || 'en'));
      B.innerHTML = `${head}${sub}<div class="ps-ctx ld-tl" lang="${lang}">${blankify(c.sentence_with_blank)}</div>
        <form id="psTypedForm" class="ps-form"><input id="psTyped" class="form-control ps-input ps-cjk" type="text" autocomplete="off" spellcheck="false" lang="${lang}" placeholder="${esc(ph)}" aria-label="${esc(T('prestudy.ex_cloze_typed'))}"></form><div id="psReveal" class="ps-revealwrap"></div>`;
      const norm = (x) =>
        String(x)
          .normalize('NFKC')
          .trim()
          .replace(/[。！？、，．,.!?]+$/, '')
          .toLowerCase();
      // the Check button sits in the dock and submits this form (form="psTypedForm")
      S.check = { form: 'psTypedForm' };
      $('psTypedForm').onsubmit = (ev) => {
        ev.preventDefault();
        const v = $('psTyped').value;
        if (!v.trim()) return;
        answer((c.answer.accepted || []).map(norm).includes(norm(v)), v, {
          shown: c.original_sentence,
        });
      };
      $('psTyped').focus({ preventScroll: true });
    } else if (t === 'jumbled_sentence') {
      const order = c.correct_ordering,
        chunks = c.chunks,
        idx = shuffle(chunks.map((_, i) => i)),
        picked = [];
      const joiner = S.test.language_id === EN ? ' ' : '';
      const check = () => {
        if (picked.length !== chunks.length) return;
        answer(
          picked.every((v, k) => v === order[k]),
          picked.map((i) => chunks[i]).join(joiner),
          { shown: c.original_sentence }
        );
      };
      const render = () => {
        B.innerHTML = `${head}${sub}<div class="ps-ctx ps-built ld-tl" lang="${lang}">${picked.map((i) => `<span class="ps-chunk on">${esc(chunks[i])}</span>`).join('') || `<span class="ps-note">${esc(T('prestudy.tap_pieces'))}</span>`}</div>
          <div class="ps-chunks ld-tl" lang="${lang}">${idx
            .filter((i) => !picked.includes(i))
            .map(
              (i) =>
                `<button type="button" class="ps-chunk" data-i="${i}">${esc(chunks[i])}</button>`
            )
            .join('')}</div>
          <div class="ps-jrow"><button type="button" class="ld-btn ld-btn--sm ld-btn--ghost" id="psUndo" ${picked.length ? '' : 'disabled'}>${esc(T('prestudy.undo'))}</button></div><div id="psReveal" class="ps-revealwrap"></div>`;
        B.querySelectorAll('.ps-chunks .ps-chunk').forEach((b) => {
          b.onclick = () => {
            picked.push(parseInt(b.dataset.i, 10));
            render();
          };
        });
        $('psUndo').onclick = () => {
          picked.pop();
          render();
        };
        // Check lives in the dock; it unlocks once every piece is placed
        S.check = { onclick: check, disabled: picked.length !== chunks.length };
        updateActionBar();
      };
      render();
    }
  }
  // One answer option in the shared .ld-opt look; the text sits in its own span
  // so the A-D key never leaks into the value read back on a click.
  function optButton(text, i, tl, langCode) {
    const lang = tl ? LANGCODE[S.test.language_id] || '' : langCode || '';
    return `<button type="button" class="ld-opt ps-opt${tl ? ' ps-cjk' : ''}" data-i="${i}"><span class="ld-opt__key" aria-hidden="true">${'ABCDEFGH'[i] || i + 1}</span><span class="ps-opt-t${tl ? ' ld-tl' : ''}"${lang ? ` lang="${lang}"` : ''}>${esc(text)}</span></button>`;
  }

  // ---------- word prime ----------
  function wordPool(a) {
    return a.rows.map((r) => r.sid).filter((x) => gloss(x).def);
  }
  function pickDistractors(pool, sid, n, keyFn, prefer) {
    const seen = new Set([keyFn(sid)]);
    const out = [];
    const ordered = shuffle(pool.filter((x) => x !== sid && prefer(x))).concat(
      shuffle(pool.filter((x) => x !== sid && !prefer(x)))
    );
    for (const x of ordered) {
      const v = keyFn(x);
      if (!v || seen.has(v)) continue;
      seen.add(v);
      out.push(x);
      if (out.length >= n) break;
    }
    return out;
  }
  // ---------- meaning items: one gloss language per item ----------
  // "Choose the meaning" and "choose the word" draw every option from one gloss
  // language: the learner's when the target word has a gloss in it, otherwise
  // the study language's own definitions (every linked sense has one; 49% of
  // test-linked Chinese senses had no English gloss on 2026-11-16). Skipping the
  // item instead would drop the meaning round for exactly those words. A
  // distractor never carries a plausible meaning of the target: not another
  // sense of the same word, not the same or an overlapping gloss, and not a
  // word the target's gloss names (or whose gloss names the target). Items with
  // fewer than two such distractors are skipped.
  const MIN_MEANING_DISTRACTORS = 2;
  function normGloss(t) {
    return String(t == null ? '' : t)
      .normalize('NFKC')
      .toLowerCase()
      .replace(/[\s\p{P}\p{S}～]+/gu, '');
  }
  function glossParts(t) {
    return String(t == null ? '' : t)
      .split(/[;；,，、/／|。.()（）:：]+/)
      .map(normGloss)
      .filter(Boolean);
  }
  function glossIn(senses, sid, lang) {
    const s = senses[sid],
      g = s && s.glosses && s.glosses[String(lang)];
    return (g && g.def) || '';
  }
  // Could the candidate's gloss (in `lang`) also be a right answer for the target?
  // Conservative: a rejected candidate only shrinks the pool.
  function plausibleMeaning(senses, target, cand, lang) {
    const t = senses[target],
      c = senses[cand];
    if (!t || !c) return true;
    // the same word, or one word inside the other (坐 / 坐在, 时 / 时间)
    if (t.lemma && c.lemma && (t.lemma.includes(c.lemma) || c.lemma.includes(t.lemma))) return true;
    const td = glossIn(senses, target, lang),
      cd = glossIn(senses, cand, lang);
    if (!normGloss(td) || !normGloss(cd)) return true;
    // the same gloss, or a shared / contained part ("to sit" in "to sit on; ...")
    const tp = [normGloss(td), ...glossParts(td)],
      cp = [normGloss(cd), ...glossParts(cd)];
    const overlap = (a, b) => {
      if (a === b) return true;
      const short = a.length < b.length ? a : b;
      return short.length >= 4 && (a.includes(b) || b.includes(a));
    };
    if (tp.some((a) => cp.some((b) => overlap(a, b)))) return true;
    // a gloss that names the other word (格外: "…；特别，分外。" names 特别)
    const mentions = (def, lemma) => !!lemma && lemma.length >= 2 && String(def).includes(lemma);
    return mentions(td, c.lemma) || mentions(cd, t.lemma);
  }
  /**
   * Options for one meaning item, all in one gloss language.
   *   o.senses   {sid: {lemma, glosses: {lang: {def}}}}
   *   o.langs    gloss languages to try, in order (learner's, then study language)
   *   o.mask     (def, lemma) => text shown (headword hidden)
   *   o.prefer   sid => bool (same part of speech first)
   *   o.n, o.min distractors wanted / needed (default 3 / 2)
   *   o.shuffle  array => shuffled copy
   * Returns {lang, target: text, distractors: [{sid, text}]} or null.
   */
  function meaningOptions(sid, pool, o) {
    const senses = o.senses,
      n = o.n || 3,
      min = o.min || MIN_MEANING_DISTRACTORS,
      mix = o.shuffle || ((a) => a.slice()),
      mask = o.mask || ((d) => d),
      prefer = o.prefer || (() => true);
    const langs = (o.langs || []).filter((l, i, a) => l != null && a.indexOf(l) === i);
    for (const lang of langs) {
      const def = glossIn(senses, sid, lang);
      // the target has no gloss here: try the next language (the learner's
      // language comes first, so it is used whenever the target has one)
      if (!def) continue;
      const target = mask(def, senses[sid].lemma);
      const seen = new Set([normGloss(target)]);
      const cands = pool.filter(
        (x) => x !== sid && glossIn(senses, x, lang) && !plausibleMeaning(senses, sid, x, lang)
      );
      const ordered = mix(cands.filter((x) => prefer(x))).concat(
        mix(cands.filter((x) => !prefer(x)))
      );
      const distractors = [];
      const lemmas = new Set([senses[sid].lemma]);
      for (const x of ordered) {
        const text = mask(glossIn(senses, x, lang), senses[x].lemma);
        const key = normGloss(text);
        if (!key || seen.has(key) || lemmas.has(senses[x].lemma)) continue;
        seen.add(key);
        lemmas.add(senses[x].lemma);
        distractors.push({ sid: x, text });
        if (distractors.length >= n) break;
      }
      if (distractors.length >= min) return { lang, target, distractors };
      // the target has a gloss in this language but too few distractors share
      // it: a study-language set is still consistent, so try that next
    }
    return null;
  }

  // Shared helpers from static/js/session/lexicon.js (exposed by test_prestudy.html);
  // identity / raw-tag fallbacks keep the page working if the module is late.
  function lex() {
    return window.LinguaLexicon || {};
  }
  function posClassOf(x) {
    const f = lex().posClass;
    return f ? f(D.senses[x].pos) : String(D.senses[x].pos || '');
  }
  // Definitions are shown with their own headword hidden ("宗教改革是…" -> "～是…"),
  // so the options and the reverse prompt do not contain the answer.
  function meaningFor(sid, pool, samePos) {
    const f = lex().maskHeadword;
    return meaningOptions(sid, pool, {
      senses: D.senses,
      langs: [String(S.glossLang), String(S.test.language_id)],
      mask: (d, lemma) => (f ? f(d, lemma) : d),
      prefer: samePos,
      shuffle,
    });
  }
  // lang="" for a gloss in the study language, so CJK definitions get their font
  function glossLangCode(lang) {
    return Number(lang) === S.test.language_id ? LANGCODE[S.test.language_id] || '' : '';
  }
  function buildItem(stage, sid, a) {
    const s = D.senses[sid],
      pool = wordPool(a),
      rp = readingParts(s),
      cls = posClassOf(sid),
      samePos = (x) => posClassOf(x) === cls;
    if (stage === 'read_typed' || stage === 'read_typed2') {
      if (!hasTypedReading(sid)) return null;
      return {
        stage,
        sid,
        kind: 'typed',
        prompt: s.lemma,
        correct: rp.shown,
        numbered: rp.numbered,
      };
    }
    if (stage === 'def_mc') {
      const m = meaningFor(sid, pool, samePos);
      if (!m) return null;
      return {
        stage,
        sid,
        kind: 'mc',
        prompt: s.lemma,
        sub: rp ? rp.shown : '',
        opts: shuffle([m.target, ...m.distractors.map((d) => d.text)]),
        correct: m.target,
        optLang: glossLangCode(m.lang),
      };
    }
    if (stage === 'rev_mc') {
      // the prompt is the target's gloss: a word whose gloss would fit it as
      // well is not a distractor (same rule as def_mc, in the prompt's language)
      const m = meaningFor(sid, pool, samePos);
      if (!m) return null;
      return {
        stage,
        sid,
        kind: 'mc',
        prompt: m.target,
        promptLang: glossLangCode(m.lang),
        opts: shuffle([s.lemma, ...m.distractors.map((d) => D.senses[d.sid].lemma)]),
        correct: s.lemma,
        cjkOpts: true,
        glossPrompt: true,
      };
    }
    if (stage === 'cloze_mc') {
      const sent = passageSentenceFor(sid, true);
      if (!sent) return null;
      const dis = pickDistractors(pool, sid, 3, (x) => D.senses[x].lemma, samePos).map(
        (x) => D.senses[x].lemma
      );
      if (!dis.length) return null;
      return {
        stage,
        sid,
        kind: 'mc',
        prompt: sent,
        opts: shuffle([s.lemma, ...dis]),
        correct: s.lemma,
        cjkOpts: true,
        cloze: true,
      };
    }
    if (stage === 'ex_use') return exItem(stage, sid, 'use');
    if (stage === 'ex_judge') return exItem(stage, sid, 'judge');
    return null;
  }
  function newPerWord(sid) {
    return {
      exposures: 0,
      correct: 0,
      wrong: 0,
      idk: 0,
      boosters: 0,
      pBefore: pNow(sid),
      stages: {},
    };
  }
  function buildQuiz() {
    const a = analyse(),
      planMode = currentPlanMode();
    let words;
    if (S.mode === 'followup') {
      // the unknown senses behind the questions answered wrong, in question order
      words = S.followSenses
        .filter((sid) => D.senses[sid] && pNow(sid) < 0.5)
        .slice(0, FOLLOWUP_MAX_WORDS);
    } else {
      // every unknown and learning word, plus the words the learner added
      words = a.ranked.map((r) => r.sid);
    }
    S.exUsed = new Set();
    const queue = [];
    const allowed =
      S.mode === 'followup' ? FOLLOWUP_STAGES : planMode === 'light' ? LIGHT_STAGES : null;
    STAGES.filter((st) => !allowed || allowed.includes(st.k)).forEach((st) => {
      const round = shuffle(words.map((sid) => buildItem(st.k, sid, a)).filter(Boolean));
      if (queue.length && round.length > 1 && round[0].sid === queue[queue.length - 1].sid)
        round.push(round.shift());
      queue.push(...round);
    });
    const perWord = {};
    words.forEach((sid) => {
      perWord[sid] = newPerWord(sid);
    });
    S.quiz = { words, queue, i: 0, mode: planMode, perWord };
    drawQuiz();
  }
  function currentPlanMode() {
    return ['full', 'light', 'none'].includes(S.planOverride)
      ? S.planOverride
      : trigger(S.snapshot).mode;
  }
  // Step 2 head: the round's title and its tag (an empty tag is hidden).
  function s2Head(title, tag) {
    const h = $('psS2Title'),
      m = $('psQuizMode');
    if (h && title) h.textContent = title;
    if (m) {
      m.textContent = tag || '';
      m.hidden = !tag;
    }
  }
  function primeTitle() {
    return T(S.mode === 'followup' ? 'prestudy.step_followup' : 'prestudy.step_prime');
  }
  function drawProgress(items, cur) {
    $('psQProg').innerHTML = items
      .map(
        (it, i) =>
          `<i class="${it.answered == null ? (i === cur ? 'cur' : '') : it.ok ? 'c' : it.idk ? 'k' : 'w'}"></i>`
      )
      .join('');
    // the strip is capped at three rows; keep the current pip's row in view
    const box = $('psQProg'),
      pip = box.children[cur];
    if (pip) {
      const top = pip.getBoundingClientRect().top - box.getBoundingClientRect().top;
      box.scrollTop = Math.max(0, box.scrollTop + top - 8);
    }
  }
  function stat(n, label) {
    return `<div class="ld-stat ps-stat"><div class="ld-stat__n">${n}</div><small>${esc(label)}</small></div>`;
  }
  function drawQuiz() {
    const q = S.quiz,
      B = $('psQBody');
    S.check = null;
    // the extra round keeps the head startBoost gave it
    if (S.phase !== 'boost')
      s2Head(
        primeTitle(),
        T('prestudy.prime_header', { words: q.words.length, items: q.queue.length })
      );
    drawProgress(q.queue, q.i);
    stageTop();
    if (!q.queue.length) {
      B.innerHTML = `<div class="ld-note">${esc(T(S.mode === 'followup' ? 'prestudy.followup_none' : 'prestudy.no_prime_needed'))}</div>`;
      updateActionBar();
      return;
    }
    if (q.i >= q.queue.length) {
      const first = q.queue.filter((it) => !it.retry);
      const rd = first.filter((it) => it.stage.startsWith('read')),
        mn = first.filter((it) => !it.stage.startsWith('read'));
      B.innerHTML = `<div class="ld-stats ld-stats--two ps-statrow">
          ${stat(`${first.filter((i) => i.ok).length} / ${first.length}`, T('prestudy.done_first_try'))}
          ${rd.length ? stat(`${rd.filter((i) => i.ok).length} / ${rd.length}`, T('prestudy.done_reading')) : ''}
          ${stat(`${mn.filter((i) => i.ok).length} / ${mn.length}`, T('prestudy.done_meaning'))}
          ${stat(q.queue.filter((it) => it.idk).length, T('prestudy.done_idk'))}</div>
        <div class="ld-note ps-callout">${esc(S.mode === 'followup' ? T(S.canProduce ? 'prestudy.next_produce' : 'prestudy.next_finish') : readinessWords().length && currentPlanMode() !== 'light' ? T(S.phase === 'boost' ? 'prestudy.next_readiness2' : 'prestudy.next_readiness') : T('prestudy.next_ready'))}</div>`;
      updateActionBar();
      return;
    }
    const it = q.queue[q.i],
      s = D.senses[it.sid],
      st = STAGES.find((x) => x.k === it.stage),
      w = q.perWord[it.sid];
    const lang = LANGCODE[S.test.language_id] || '';
    const tagCls = it.stage.startsWith('read')
      ? 'info'
      : it.stage === 'cloze_mc'
        ? 'warn'
        : it.kind === 'ex'
          ? 'ok'
          : 'brand';
    const head = `<div class="ld-between ps-qhead"><span class="ps-note ld-num">${esc(T('prestudy.item_of', { i: q.i + 1, n: q.queue.length }))}${it.retry ? ' · ' + esc(T('prestudy.again')) : ''} · ${esc(T('prestudy.exposure', { n: w.exposures + 1 }))}</span><span class="ld-tag ld-tag--${tagCls}">${esc(T(st.label))}</span></div>
      ${it.kind === 'ex' ? '' : `<p class="ld-eyebrow ps-ask">${esc(T(st.ask))}</p>`}`;
    if (it.kind === 'ex') {
      drawExercise(it, head);
      updateActionBar();
      return;
    }
    if (it.kind === 'typed') {
      drawTyped(it, head);
      updateActionBar();
      return;
    }
    const prompt = it.cloze
      ? `<div class="ps-ctx ld-prompt ld-tl" lang="${lang}">${it.prompt}</div>`
      : it.glossPrompt
        ? `<div class="ps-qword ps-gloss-prompt ld-h1"${it.promptLang ? ` lang="${it.promptLang}"` : ''}>${esc(it.prompt)}</div>`
        : `<div class="ps-qword ld-prompt ld-prompt--big" lang="${lang}">${esc(it.prompt)}</div>`;
    B.innerHTML = `${head}${prompt}${it.sub ? `<div class="ps-qread">${esc(it.sub)}${s.pos ? ' · ' + esc(s.pos) : ''}</div>` : ''}
      <div class="ld-opts ps-opts${it.cjkOpts ? ' ps-opts--tl' : ''}">${it.opts.map((o, i) => optButton(o, i, !!it.cjkOpts, it.optLang)).join('')}</div><div id="psReveal" class="ps-revealwrap"></div>`;
    B.querySelectorAll('.ps-opt').forEach((b) => {
      b.onclick = () => {
        const v = it.opts[parseInt(b.dataset.i, 10)];
        answer(v === it.correct, v);
      };
    });
    updateActionBar();
  }
  function drawTyped(it, head) {
    const B = $('psQBody'),
      zh = S.test.language_id === ZH,
      lang = LANGCODE[S.test.language_id] || '';
    B.innerHTML = `${head}<div class="ps-qword ld-prompt ld-prompt--big" lang="${lang}">${esc(it.prompt)}</div><p class="ps-qread ld-hint">${esc(T(zh ? 'prestudy.hint_zh' : 'prestudy.hint_ja'))}</p>
      <form id="psTypedForm" class="ps-form"><input id="psTyped" class="form-control ps-input" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" lang="${zh ? 'zh-Latn' : 'ja'}" placeholder="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}" aria-label="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}"></form><div id="psTones"></div><div id="psReveal" class="ps-revealwrap"></div>`;
    const f = $('psTypedForm');
    // the Check button sits in the dock and submits this form (form="psTypedForm")
    S.check = { form: 'psTypedForm' };
    f.onsubmit = (e) => {
      e.preventDefault();
      const v = $('psTyped').value;
      if (!v.trim()) return;
      if (!zh) {
        const g = gradeJa(v, it.correct);
        answer(g.ok, v, { detail: g.ok && g.mode === 'romaji' ? T('prestudy.romaji_ok') : '' });
        return;
      }
      const pi = parsePinyinInput(v);
      const g = gradeZh(pi.segs, pi.tones, it.numbered, it.prompt);
      if (pi.tones != null || !g.segOk) {
        answer(g.ok, v, {
          detail: g.segOk
            ? g.toneOk
              ? ''
              : T('prestudy.tones_wrong')
            : T('prestudy.syllables_wrong'),
        });
        return;
      }
      // toneless and syllables right: pick the tone of each syllable
      $('psTyped').disabled = true;
      S.check.disabled = true;
      updateActionBar();
      const Tn = $('psTones');
      const picked = new Array(g.ref.length).fill(null);
      Tn.innerHTML = `<p class="ld-note ps-tonenote">${esc(T('prestudy.tones_now'))}</p><div class="ps-tonegrid">${g.ref.map((r, i) => `<div class="ps-tonesyl" role="group" aria-label="${esc(pi.segs[i] || r.seg)}"><div class="ps-syl">${esc(pi.segs[i] || r.seg)}</div><div class="ps-tonebtns">${[1, 2, 3, 4, 5].map((tn) => `<button type="button" class="ps-tone" data-i="${i}" data-t="${tn}" aria-pressed="false" aria-label="${esc(T('prestudy.tone_label', { n: tn }))}">${tn === 5 ? '·' : tn}</button>`).join('')}</div></div>`).join('')}</div>`;
      Tn.querySelectorAll('.ps-tone').forEach((btn) => {
        btn.onclick = () => {
          const i = +btn.dataset.i;
          picked[i] = +btn.dataset.t;
          Tn.querySelectorAll(`.ps-tone[data-i="${i}"]`).forEach((x) => {
            x.classList.toggle('picked', x === btn);
            x.setAttribute('aria-pressed', x === btn ? 'true' : 'false');
          });
          if (picked.every((tn) => tn != null)) {
            const g2 = gradeZh(pi.segs, picked, it.numbered, it.prompt);
            Tn.querySelectorAll('.ps-tone').forEach((x) => {
              const ii = +x.dataset.i,
                tt = +x.dataset.t;
              x.disabled = true;
              if (tt === g2.ref[ii].tone) x.classList.add('correct');
              else if (tt === picked[ii]) x.classList.add('wrong');
            });
            answer(g2.ok, v + ' ' + picked.join(''), {
              detail: g2.ok ? '' : T('prestudy.tones_wrong'),
            });
          }
        };
      });
      const firstTone = Tn.querySelector('.ps-tone');
      if (firstTone) {
        firstTone.focus({ preventScroll: true });
        revealInStage(Tn);
      }
    };
    $('psTyped').focus({ preventScroll: true });
  }
  function recordAnswer(sid, correct, idk, stage) {
    S.answers.push({
      sense_id: Number(sid),
      correct: !!correct,
      idk: !!idk,
      stage: stage || (S.mode === 'followup' ? 'followup' : 'prime'),
    });
  }
  function answer(ok, given, extra) {
    extra = extra || {};
    const q = S.quiz,
      it = q.queue[q.i];
    if (!it || it.answered != null) return;
    if (!q.perWord[it.sid]) q.perWord[it.sid] = newPerWord(it.sid);
    const idk = !!extra.idk;
    it.answered = idk ? '' : given;
    it.ok = ok;
    it.idk = idk;
    const w = q.perWord[it.sid];
    w.exposures++;
    if (ok) w.correct++;
    else w.wrong++;
    if (idk) w.idk++;
    if (!it.retry) w.stages[it.stage] = ok;
    const p0 = pNow(it.sid);
    S.know[it.sid] = idk ? bktUpdateIdk(p0) : bktUpdate(p0, ok);
    // ladder exercises are exercise evidence (exercise_attempts, source prestudy),
    // everything else is word-test evidence
    if (it.kind === 'ex')
      S.exAnswers.push({
        exercise_id: it.ex.id,
        correct: !!ok,
        idk,
        given: given == null ? '' : String(given).slice(0, 200),
      });
    else recordAnswer(it.sid, ok, idk);
    const willRetry = !ok && (it.retries || 0) < (idk ? 3 : 2);
    if (willRetry) {
      const again = Object.assign({}, it, {
        answered: null,
        ok: null,
        idk: false,
        retry: true,
        retries: (it.retries || 0) + 1,
      });
      q.queue.splice(
        Math.min(q.queue.length, q.i + (idk ? 2 : 3) + Math.floor(Math.random() * 3)),
        0,
        again
      );
    }
    // an honest miss adds one booster exposure of this word, in a different cheap stage, at the end
    let booster = null;
    if (idk && w.boosters < 2) {
      const a = analyse();
      const alt = it.stage === 'def_mc' ? 'read_typed' : 'def_mc';
      booster = buildItem(alt, it.sid, a) || buildItem('rev_mc', it.sid, a);
      if (booster) {
        booster.retry = true;
        booster.booster = true;
        q.queue.push(booster);
        w.boosters++;
      }
    }
    const B = $('psQBody');
    const corr = it.kind === 'ex' ? it.correctText : it.correct;
    B.querySelectorAll('.ps-opt').forEach((b) => {
      const v =
        it.kind === 'ex'
          ? (b.querySelector('.ps-opt-t') || b).textContent
          : it.opts[parseInt(b.dataset.i, 10)];
      if (v === corr) b.classList.add('correct', 'is-correct');
      else if (v === given) b.classList.add('wrong', 'is-wrong');
      b.disabled = true;
    });
    B.querySelectorAll('.ps-chunks .ps-chunk, #psUndo, .ps-tone').forEach((b) => {
      b.disabled = true;
    });
    const typed = $('psTyped');
    if (typed) {
      typed.disabled = true;
      typed.classList.add(ok ? 'is-valid' : idk ? 'ps-idk-input' : 'is-invalid');
    }

    const g = gloss(it.sid),
      s = D.senses[it.sid],
      rp = readingParts(s),
      isRead = it.stage.startsWith('read');
    const lang = LANGCODE[S.test.language_id] || '';
    const readingTxt = rp
      ? ' · ' +
        esc(rp.shown) +
        (rp.numbered ? ' (' + esc(rp.numbered) + ')' : '') +
        (S.test.language_id === JA ? ' · ' + esc(kanaToRomaji(rp.shown)) : '')
      : '';
    const lines = [];
    if (idk && isRead && g.def) lines.push(esc(T('prestudy.meaning_label', { def: g.def })));
    if (isRead) lines.push(esc(T('prestudy.meaning_next')));
    if (g.ex && !isRead) lines.push(esc(T('prestudy.example', { ex: g.ex })));
    let ctx = '';
    if (it.kind === 'ex') {
      if (extra.shown)
        ctx = `<span class="ps-note">${esc(T('prestudy.full_sentence'))}</span><span class="ps-ctx ld-tl" lang="${lang}">${esc(extra.shown)}</span>`;
    } else if (!it.cloze) {
      const ps = passageSentenceFor(it.sid);
      if (ps)
        ctx = `<span class="ps-note">${esc(T('prestudy.in_passage'))}</span><span class="ps-ctx ld-tl" lang="${lang}">${ps}</span>`;
    }
    const follow = willRetry ? T('prestudy.reasked') : ok ? '' : T('prestudy.moving_on');
    const kind = ok ? 'ok' : idk ? 'idk' : 'bad';
    $('psReveal').innerHTML =
      `<div class="ld-feedback ld-feedback--${kind} ps-reveal ${kind}" role="status"><b>${esc(T(ok ? 'prestudy.correct' : idk ? 'prestudy.idk_reveal' : 'prestudy.wrong'))}</b>
      <span><b class="ps-cjk ld-tl" lang="${lang}">${esc(s.lemma)}</b>${readingTxt}${isRead || !g.def ? '' : ' — ' + esc(g.def)}</span>
      ${lines.map((l) => `<span class="ps-note">${l}</span>`).join('')}${ctx}
      ${extra.detail ? `<span class="ps-note">${esc(extra.detail)}</span>` : ''}
      ${follow || booster ? `<span class="ps-note">${esc(follow)}${booster ? ' ' + esc(T('prestudy.booster_added')) : ''}</span>` : ''}</div>`;
    // the dock's Next button moves on to the next item
    updateActionBar();
    revealInStage($('psReveal'));
    $('psNextStep').focus({ preventScroll: true });
  }

  // ---------- readiness check ----------
  function readinessWords() {
    const q = S.prime || S.quiz;
    if (!q) return [];
    const score = (sid) => {
      const w = q.perWord[sid];
      return (w.idk || 0) * 10 + (w.wrong || 0) - pNow(sid);
    };
    return q.words
      .filter(hasTypedReading)
      .sort((a, b) => score(b) - score(a))
      .slice(0, 5);
  }
  function startReadiness(round) {
    S.ready = { round, words: readinessWords(), i: 0, answers: [], results: null };
    S.phase = 'ready';
    drawReadiness();
  }
  function drawReadiness() {
    const R = S.ready,
      B = $('psQBody'),
      zh = S.test.language_id === ZH,
      lang = LANGCODE[S.test.language_id] || '';
    // the mockup's head: "Readiness check · round N"; the item row carries "No feedback yet"
    s2Head(T('prestudy.readiness_title', { n: R.round }), '');
    S.check = null;
    stageTop();
    $('psQProg').innerHTML = R.words
      .map((_, i) => `<i class="${i < R.i ? 'c' : i === R.i ? 'cur' : ''}"></i>`)
      .join('');
    if (!R.words.length) {
      R.results = { score: 0, n: 0, pass: true, failed: [] };
      B.innerHTML = `<div class="ld-note">${esc(T('prestudy.no_readiness_words'))}</div>`;
      updateActionBar();
      return;
    }
    if (R.i >= R.words.length) {
      if (!R.results) {
        const rows = R.words.map((sid, i) => ({
          sid,
          u: R.answers[i],
          rp: readingParts(D.senses[sid]),
          ok: !!R.answers[i] && gradeReading(R.answers[i], readingParts(D.senses[sid])),
        }));
        const score = rows.filter((r) => r.ok).length,
          n = rows.length,
          need = Math.ceil(n * 0.8);
        R.results = {
          score,
          n,
          need,
          pass: score >= need,
          failed: rows.filter((r) => !r.ok).map((r) => r.sid),
          rows,
        };
        const q = S.prime || S.quiz;
        rows.forEach((r) => {
          const w = q.perWord[r.sid];
          if (w) {
            w.readiness = w.readiness || [];
            w.readiness.push(r.ok);
          }
          S.know[r.sid] = r.u ? bktUpdate(pNow(r.sid), r.ok) : bktUpdateIdk(pNow(r.sid));
          recordAnswer(r.sid, r.ok, !r.u, 'readiness');
        });
      }
      const res = R.results;
      const msg = res.pass
        ? T('prestudy.ready_unlocked')
        : R.round === 1
          ? T('prestudy.extra_round_note')
          : T('prestudy.proceed_anyway');
      B.innerHTML = `<div class="ld-stats ld-stats--two ps-statrow">${stat(`${res.score} / ${res.n}`, T('prestudy.readiness_score', { round: R.round, need: res.need }))}
          <div class="ld-stat ps-stat"><span class="ld-tag ld-tag--${res.pass ? 'ok' : 'warn'} ps-chip-lg">${esc(T(res.pass ? 'prestudy.ready' : 'prestudy.not_yet'))}</span><small>${esc(msg)}</small></div></div>
        <div class="ps-tablewrap"><table class="ps-table"><thead><tr><th scope="col">${esc(T('prestudy.col_word'))}</th><th scope="col">${esc(T('prestudy.col_typed'))}</th><th scope="col">${esc(T('prestudy.col_reading'))}</th><th scope="col"><span class="visually-hidden">${esc(T('prestudy.check'))}</span></th></tr></thead><tbody>
          ${res.rows.map((r) => `<tr><td><b class="ps-cjk ld-tl" lang="${lang}">${esc(D.senses[r.sid].lemma)}</b></td><td><code>${esc(r.u || '—')}</code></td><td>${esc(r.rp.shown)}${r.rp.numbered ? ' <span class="ps-note">(' + esc(r.rp.numbered) + ')</span>' : ''}</td><td>${r.ok ? `<span class="ld-tag ld-tag--ok" aria-label="${esc(T('prestudy.correct'))}">✓</span>` : `<span class="ld-tag ld-tag--bad" aria-label="${esc(T('prestudy.wrong'))}">✗</span>`}</td></tr>`).join('')}
        </tbody></table></div>`;
      updateActionBar();
      return;
    }
    const sid = R.words[R.i],
      s = D.senses[sid];
    B.innerHTML = `<div class="ld-between ps-qhead"><span class="ps-note ld-num">${esc(T('prestudy.check_of', { i: R.i + 1, n: R.words.length }))}</span><span class="ld-tag ld-tag--info">${esc(T('prestudy.no_feedback'))}</span></div>
      <p class="ld-eyebrow ps-ask">${esc(T('prestudy.stage_reading'))} · ${esc(T('prestudy.ask_read'))}</p>
      <div class="ps-qword ld-prompt ld-prompt--big" lang="${lang}">${esc(s.lemma)}</div><p class="ps-qread ld-hint">${esc(T(zh ? 'prestudy.ready_hint_zh' : 'prestudy.ready_hint_ja'))}</p>
      <form id="psReadyForm" class="ps-form"><input id="psReadyIn" class="form-control ps-input" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" lang="${zh ? 'zh-Latn' : 'ja'}" placeholder="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}" aria-label="${esc(T(zh ? 'prestudy.placeholder_pinyin' : 'prestudy.placeholder_kana'))}"></form>`;
    $('psReadyForm').onsubmit = (e) => {
      e.preventDefault();
      R.answers.push($('psReadyIn').value.trim());
      R.i++;
      drawReadiness();
    };
    // "I don't know" sits in the dock (updateActionBar wires it to this)
    S.readyIdk = () => {
      R.answers.push('');
      R.i++;
      drawReadiness();
    };
    $('psReadyIn').focus({ preventScroll: true });
    updateActionBar();
  }
  function startBoost() {
    const a = analyse(),
      failed = S.ready.results.failed,
      items = [];
    shuffle(failed).forEach((sid) => {
      const r = buildItem('read_typed', sid, a);
      if (r) items.push(r);
    });
    shuffle(failed).forEach((sid) => {
      const d = buildItem('def_mc', sid, a);
      if (d) items.push(d);
    });
    S.prime = S.prime || S.quiz;
    S.quiz = Object.assign({}, S.prime, { queue: items, i: 0 });
    S.phase = 'boost';
    s2Head(
      T('prestudy.extra_round_header', { n: failed.length }),
      T('prestudy.prime_header', { words: failed.length, items: items.length })
    );
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
      met_sense_ids: S.mode === 'prime' ? metSenses(q) : [],
    };
  }
  // New-word drill (ADR-040): a word whose prime met intro session 1's target
  // (every reading/meaning/use stage it was given eventually answered right,
  // at least three of them) starts the drill at session 2.
  const INTRO_S1 = ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc'];
  function metSenses(q) {
    // The drill's own counting rule (window.IntroDrillCount, from
    // static/js/session/players/intro_drill.js): 5 counted right answers,
    // spaced and in different formats, as in intro session 1.
    const C = window.IntroDrillCount;
    if (C && C.countWord) {
      const answered = q.queue.filter((it) => it.answered != null);
      const K = q.words.length;
      return q.words
        .filter((sid) => {
          const atts = [];
          answered.forEach((it, pos) => {
            if (String(it.sid) === String(sid))
              atts.push({ pos, format: it.stage, correct: !!it.ok, idk: !!it.idk });
          });
          const formats = [...new Set(atts.map((x) => x.format))];
          return atts.length > 0 && C.countWord(1, atts, K, formats).passed;
        })
        .map(Number);
    }
    return q.words
      .filter((sid) => {
        const items = q.queue.filter(
          (it) => String(it.sid) === String(sid) && INTRO_S1.includes(it.stage)
        );
        const stages = new Set(items.map((it) => it.stage));
        if (stages.size < 3) return false;
        return [...stages].every((st) => items.some((it) => it.stage === st && it.ok && !it.idk));
      })
      .map(Number);
  }
  async function postEvidence() {
    if (S.evidencePosted) return true;
    if (!S.answers.length && !S.exAnswers.length && !S.sessionId) return true;
    S.evidencePosted = true;
    try {
      const res = await window.authFetch(
        `/api/tests/${encodeURIComponent(S.slug)}/prestudy/evidence`,
        {
          method: 'POST',
          body: JSON.stringify({
            session_id: S.sessionId,
            mode: S.mode,
            answers: S.answers.slice(0, 400),
            exercise_answers: S.exAnswers.slice(0, 40),
            metrics: metrics(),
          }),
        }
      );
      if (!res.ok) throw new Error('HTTP ' + res.status);
      try {
        const j = await res.json();
        S.intro = ((j && j.data) || j || {}).intro || null;
      } catch {
        S.intro = null;
      }
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
    $('psReadyStats').innerHTML =
      stat(q.words.length, T('prestudy.summary_words')) +
      stat(
        `${first.filter((it) => it.ok).length} / ${first.length}`,
        T('prestudy.summary_first_try')
      ) +
      (R && R.n ? stat(`${R.score} / ${R.n}`, T('prestudy.summary_readiness')) : '');
    $('psReadyStats').classList.toggle('ld-stats--two', !(R && R.n));
    const st = $('psSaveState');
    $('psReadyTitle').textContent = T(
      S.mode === 'followup' ? 'prestudy.followup_done_title' : 'prestudy.ready_title'
    );
    $('psEloNote').hidden = S.mode === 'followup';
    $('psProduceBox').hidden = !(S.mode === 'followup' && S.canProduce);
    // the step's buttons (Take the test / Produce / Back to session) are in the dock
    updateActionBar();
    if (!S.answers.length && !S.exAnswers.length) {
      st.textContent = '';
      postEvidence();
      return;
    }
    st.textContent = T('prestudy.saving');
    postEvidence().then((ok) => {
      st.textContent = T(ok ? 'prestudy.saved' : 'prestudy.save_failed');
      drawOverflow();
    });
  }
  // More drilled words than today's new-word room: queue the rest (default) or add them all now.
  function drawOverflow() {
    const o = S.intro && S.intro.overflow;
    const old = $('psOverflow');
    if (old) old.remove();
    if (!o || !o.over) return;
    const box = document.createElement('div');
    box.id = 'psOverflow';
    box.className = 'ld-note ld-note--warn ld-col ps-overflow';
    box.innerHTML = `<b>${esc(T('prestudy.overflow_title', { total: o.fits + o.over, fits: o.fits }))}</b>
      <span>${esc(T('prestudy.overflow_body', { over: o.over, min: o.extra_minutes_per_day }))}</span>
      <div class="ld-row ps-overflow-actions"><button type="button" class="ld-btn ld-btn--sm ld-btn--ghost ld-grow" id="psOverflowQueue">${esc(T('prestudy.overflow_queue'))}</button>
      <button type="button" class="ld-btn ld-btn--sm ld-grow" id="psOverflowAdd">${esc(T('prestudy.overflow_add', { over: o.over }))}</button></div>`;
    $('psSaveState').after(box);
    $('psOverflowQueue').onclick = () => {
      box.className = 'ld-note ps-overflow';
      box.innerHTML = `<span>${esc(T('prestudy.overflow_queued', { over: o.over }))}</span>`;
    };
    $('psOverflowAdd').onclick = async () => {
      $('psOverflowAdd').disabled = true;
      try {
        const res = await window.authFetch(
          `/api/tests/${encodeURIComponent(S.slug)}/prestudy/admit-overflow`,
          {
            method: 'POST',
            body: JSON.stringify({ sense_ids: o.sense_ids }),
          }
        );
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const j = await res.json();
        const n = (((j && j.data) || j || {}).started || []).length;
        box.className = 'ld-note ld-note--ok ps-overflow';
        box.innerHTML = `<span>${esc(T('prestudy.overflow_added', { n }))}</span>`;
      } catch (e) {
        console.warn('[prestudy] overflow not added:', e);
        $('psOverflowAdd').disabled = false;
      }
    };
  }
  function testUrl() {
    return `/test/${encodeURIComponent(S.slug)}?type=${encodeURIComponent(S.testType)}`;
  }
  // Mark the session's prestudy block done (opened from the daily session).
  async function completeBlock() {
    if (!S.block) return;
    try {
      await window.authFetch('/api/study-session/complete-block', {
        method: 'POST',
        body: JSON.stringify({ block_id: S.block, language_id: S.test.language_id }),
      });
    } catch (e) {
      console.warn('[prestudy] block not completed:', e);
    }
  }
  let leaving = false;
  async function takeTest(prestudied) {
    // one tap only: saving takes a moment and a second tap would post twice
    if (leaving) return;
    leaving = true;
    if (prestudied) {
      await postEvidence();
      try {
        sessionStorage.setItem(
          MARKER_PREFIX + S.slug,
          JSON.stringify({ at: Date.now(), test_id: S.test.id })
        );
      } catch {
        /* storage blocked: the attempt counts at full weight */
      }
      // the result screen offers Produce from this, without asking again
      if (window.LinguaPrestudyLinks && window.LinguaPrestudyLinks.setProduceAvailable)
        window.LinguaPrestudyLinks.setProduceAvailable(S.slug, S.canProduce);
    }
    await completeBlock();
    // from the daily session: go back, where the session resumes on this test
    window.location.href = S.returnTo === 'session' ? '/session' : testUrl();
  }

  // ---------- Produce (after the follow-up) ----------
  async function startProduce() {
    const btn = $('psProduce'),
      msg = $('psProduceMsg');
    btn.disabled = true;
    msg.textContent = T('prestudy.produce_loading');
    await postEvidence();
    const fallback = analyse()
      .ranked.slice(0, 8)
      .map((r) => Number(r.sid));
    try {
      const res = await window.authFetch(
        `/api/tests/${encodeURIComponent(S.slug)}/prestudy/produce`,
        {
          method: 'POST',
          body: JSON.stringify({ fallback_sense_ids: fallback }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.submission_id) {
        msg.textContent = T(
          data.error_code === 'NO_WINDOW' ? 'prestudy.produce_none' : 'prestudy.produce_failed'
        );
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
    if (S.mode === 'followup' && S.canProduce && window.LinguaPrestudyLinks)
      window.LinguaPrestudyLinks.setProduceRequest(S.slug, S.test.id);
    window.location.href = '/session';
  }

  // ---------- navigation ----------
  // The dock holds every action of the current screen (FOUNDATION.md, task mode):
  //   step 1           Start the word prime · Skip and take the test
  //   item, unanswered I don't know · Check (typed items and sentence order)
  //   item, answered   Next / Finish
  //   readiness item   I don't know · Next
  //   round summaries  Continue / Extra round on missed words
  //   step 3           Take the test, or Produce + Back to today's session
  function updateActionBar() {
    const next = $('psNextStep'),
      note = $('psBarNote'),
      idk = $('psIdk'),
      chk = $('psCheck');
    if (!next) return;
    let showNext = true,
      showIdk = false,
      showCheck = false,
      hint = '';
    next.disabled = false;
    if (S.step === 1) {
      next.textContent = T('prestudy.start_prime');
      hint = T('prestudy.elo_note');
    } else if (S.step === 2) {
      const q = S.quiz,
        it = q && q.queue[q.i],
        R = S.ready;
      if (S.phase !== 'ready' && it) {
        // mid-round: Next is live once this item is answered; before that the
        // dock offers "I don't know" (and Check where the item needs one)
        next.textContent = T(q.i + 1 < q.queue.length ? 'prestudy.next' : 'prestudy.finish');
        if (it.answered == null) {
          showNext = false;
          showIdk = true;
          showCheck = !!S.check;
          hint = T('prestudy.idk_note');
          idk.onclick = () => answer(false, null, { idk: true });
        }
      } else if (S.phase === 'ready' && R && !R.results && R.i < R.words.length) {
        next.textContent = T('prestudy.next');
        showIdk = !!S.readyIdk;
        idk.onclick = S.readyIdk || null;
      } else if (
        S.phase === 'ready' &&
        S.ready &&
        S.ready.results &&
        !S.ready.results.pass &&
        S.ready.round < 2
      )
        next.textContent = T('prestudy.extra_round');
      else next.textContent = T('prestudy.continue');
    } else {
      showNext = false;
    }
    if (showCheck) {
      const c = S.check;
      chk.textContent = T('prestudy.check');
      if (c.form) {
        chk.type = 'submit';
        chk.setAttribute('form', c.form);
        chk.onclick = null;
      } else {
        chk.type = 'button';
        chk.removeAttribute('form');
        chk.onclick = c.onclick || null;
      }
      chk.disabled = !!c.disabled;
    }
    next.hidden = !showNext;
    idk.hidden = !showIdk;
    chk.hidden = !showCheck;
    idk.classList.toggle('ld-btn--block', showIdk && !showCheck && !showNext);
    // step 3 buttons
    const s3 = S.step === 3,
      follow = S.mode === 'followup';
    $('psTakeTest').hidden = !s3 || follow;
    $('psProduce').hidden = !s3 || !follow || !S.canProduce;
    $('psBackToSession').hidden = !(s3 && follow && S.returnTo === 'session');
    // without Produce it is the step's only action, so it takes the primary style
    $('psBackToSession').classList.toggle('ld-btn--ghost', S.canProduce);
    // no Produce and not from the session: a plain way back to the test
    $('psDone').hidden = !(s3 && follow && !S.canProduce && S.returnTo !== 'session');
    $('psSkip').hidden = S.step !== 1;
    note.textContent = hint;
    // the rating note is a desktop extra; phones keep the dock to the buttons
    note.classList.toggle('ps-dockhint--wide', S.step === 1);
  }
  function go(n) {
    S.step = n;
    document.querySelectorAll('.ps-step').forEach((s) => {
      const on = s.dataset.step === String(n);
      s.classList.toggle('active', on);
      s.classList.toggle('is-on', on);
      s.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    $('psS1').hidden = n !== 1;
    $('psS2').hidden = n !== 2;
    $('psS3').hidden = n !== 3;
    hidePop();
    if (n === 1) drawPreview();
    if (n === 2) {
      if (!S.quiz) buildQuiz();
      else if (S.phase === 'ready') drawReadiness();
      else drawQuiz();
    }
    if (n === 3) drawReady();
    updateActionBar();
    stageTop();
  }
  function notice(text) {
    if (typeof window.showToast === 'function') {
      window.showToast(text, 'info');
      return;
    }
    const n = $('psNotice');
    n.textContent = text;
    n.hidden = false;
    setTimeout(() => {
      n.hidden = true;
    }, 4000);
  }
  function onNext() {
    if (S.step === 1) {
      go(2);
      return;
    }
    if (S.step !== 2) return;
    const q = S.quiz;
    if (S.phase === 'ready') {
      const R = S.ready,
        f = $('psReadyForm');
      if (!R.results && f) {
        f.requestSubmit();
        return;
      }
      if (!R.results) {
        notice(T('prestudy.finish_round_first'));
        return;
      }
      if (S.ready.results.pass || S.ready.round >= 2) {
        S.phase = 'done';
        go(3);
        return;
      }
      startBoost();
      updateActionBar();
      return;
    }
    if (q && q.i < q.queue.length) {
      if (q.queue[q.i].answered == null) return;
      q.i++;
      drawQuiz();
      return;
    }
    if (S.phase === 'prime') {
      S.prime = S.quiz;
      if (S.mode === 'followup' || currentPlanMode() === 'light' || !readinessWords().length) {
        S.phase = 'done';
        go(3);
        return;
      }
      startReadiness(1);
      return;
    }
    if (S.phase === 'boost') {
      S.quiz = S.prime;
      startReadiness(2);
      return;
    }
    go(3);
  }

  // ---------- boot ----------
  // Open the prestudy_sessions row; unknown share is the snapshot at open.
  async function startSession() {
    try {
      const res = await window.authFetch(
        `/api/tests/${encodeURIComponent(S.slug)}/prestudy/session`,
        {
          method: 'POST',
          body: JSON.stringify({
            test_type: S.testType,
            trigger: S.trigger,
            plan_mode: S.mode === 'followup' ? null : currentPlanMode(),
            mode: S.mode,
            unknown_share: Math.round(S.snapshot * 1000) / 1000,
            session_block_id: S.block,
          }),
        }
      );
      if (res.ok) S.sessionId = (await res.json()).session_id || null;
    } catch (e) {
      console.warn('[prestudy] session not recorded:', e);
    }
  }
  // Task header (base.html, task mode) through window.LinguaShell; text only.
  function setHeader(o) {
    if (window.LinguaShell && window.LinguaShell.setTaskHeader) {
      window.LinguaShell.setTaskHeader(o);
      return;
    }
    if (o.title != null && $('ldTaskTitle')) $('ldTaskTitle').textContent = o.title;
    if (o.subtitle != null && $('ldTaskSubtitle')) $('ldTaskSubtitle').textContent = o.subtitle;
    if (o.backHref && $('ldBack')) $('ldBack').setAttribute('href', o.backHref);
  }
  // Strings added by the redesign: [data-ps-t] text, [data-ps-aria] labels (English fallback).
  function applyLocalText() {
    document.querySelectorAll('[data-ps-t]').forEach((el) => {
      el.textContent = Tf(el.dataset.psT, null, el.textContent);
    });
    document.querySelectorAll('[data-ps-aria]').forEach((el) => {
      el.setAttribute(
        'aria-label',
        Tf(el.dataset.psAria, null, el.getAttribute('aria-label') || '')
      );
    });
  }
  // Arrow keys move between the options of a tab list / radio group (roving tabindex).
  function radioKeys(e, sel, pick) {
    const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    if (!(e.key in keys)) return;
    const items = Array.from(document.querySelectorAll(sel)).filter((b) => !b.hidden);
    const i = items.indexOf(document.activeElement);
    if (i < 0) return;
    e.preventDefault();
    const b = items[(i + keys[e.key] + items.length) % items.length];
    pick(b);
    b.focus();
  }
  function showError(msg) {
    $('psLoading').hidden = true;
    $('psError').hidden = false;
    $('psErrorMsg').textContent = msg;
  }
  async function init() {
    // Also loaded on the session page for its reading graders (window.LinguaPrestudy).
    if (!$('psSkip')) return;
    // Translations and the prestudy data load in parallel; rendering waits for both.
    const i18nReady =
      window.LinguaI18n && window.LinguaI18n.init
        ? Promise.resolve(window.LinguaI18n.init()).catch(() => {
            /* English fallback */
          })
        : Promise.resolve();
    const parts = window.location.pathname.split('/').filter(Boolean); // ['test', slug, 'prestudy']
    S.slug = decodeURIComponent(parts[1] || '');
    const params = new URLSearchParams(window.location.search);
    S.testType = params.get('type') === 'listening' ? 'listening' : 'reading';
    S.mode = params.get('mode') === 'followup' ? 'followup' : 'prime';
    S.trigger = ['auto', 'retry', 'opt_in'].includes(params.get('trigger'))
      ? params.get('trigger')
      : 'opt_in';
    S.planOverride = params.get('plan');
    S.block = /^prestudy_[0-9a-f-]{36}$/.test(params.get('block') || '')
      ? params.get('block')
      : null;
    S.returnTo = params.get('return') === 'session' ? 'session' : null;
    S.droppedToday = Math.max(0, Math.min(3, parseInt(params.get('dropped') || '0', 10) || 0));
    $('psSkip').href = testUrl();
    $('psSkip').onclick = (e) => {
      e.preventDefault();
      takeTest(S.answers.length > 0);
    };
    // the Back pill: today's session when opened from it, else this test's preview
    const backHref =
      S.returnTo === 'session'
        ? '/session'
        : `/test/${encodeURIComponent(S.slug)}/preview?type=${encodeURIComponent(S.testType)}`;
    setHeader({ backHref });
    $('psErrorSkip').href = testUrl();
    $('psDone').href =
      `/test/${encodeURIComponent(S.slug)}/preview?type=${encodeURIComponent(S.testType)}`;
    const dataP = window
      .authFetch(
        `/api/tests/${encodeURIComponent(S.slug)}/prestudy${S.mode === 'followup' ? '?mode=followup' : ''}`
      )
      .then((res) => {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      });
    dataP.catch(() => {
      /* handled below */
    });
    await i18nReady;
    const typeLabel = T(
      S.testType === 'listening' ? 'test_preview.listening' : 'test_preview.reading'
    );
    const pageLabel = T(S.mode === 'followup' ? 'prestudy.step_followup' : 'prestudy.page_title');
    setHeader({ title: pageLabel, subtitle: `${pageLabel} · ${typeLabel}` });
    applyLocalText();
    try {
      D = await dataP;
      S.followSenses = (D.followup_sense_ids || []).map(String);
    } catch (e) {
      console.error('[prestudy] load failed:', e);
      showError(T('prestudy.error_load'));
      return;
    }
    S.test = D.test;
    S.test.language_id = Number(S.test.language_id);
    setHeader({ title: S.test.title || '' });
    const titleEl = $('ldTaskTitle');
    if (titleEl) titleEl.lang = LANGCODE[S.test.language_id] || '';
    S.glossLang = D.gloss_language_id;
    S.ability = D.ability_zipf != null ? Number(D.ability_zipf) : 5.0;
    if (!Array.isArray(S.test.vocab_token_map) || !S.test.vocab_token_map.length) {
      // no word map: build a single-token passage so the page still shows the text
      S.test.vocab_token_map = [[S.test.transcript || '', null]];
    }
    // exercises the renderers cannot draw are dropped up front
    Object.keys(D.exercises || {}).forEach((sid) => {
      D.exercises[sid] = D.exercises[sid].filter(exerciseUsable);
    });
    // The server's share (services/prestudy.share_plan) is the one the daily
    // session's card shows; the page's own count is only a fallback.
    S.snapshot =
      D.plan && D.plan.unknown_share != null ? Number(D.plan.unknown_share) : analyse().share;
    // Produce only where POST .../prestudy/produce can find a window (false only
    // when the server says so; an older payload without the flag keeps it on).
    S.canProduce = D.produce_available !== false;
    if (window.ActiveTimer && window.ActiveTimer.create) {
      S.timer = window.ActiveTimer.create();
      S.timer.start();
    }
    startSession();

    $('psAids')
      .querySelectorAll('button')
      .forEach((b) => {
        b.onclick = () => {
          setAids(b.dataset.v);
          drawPreview();
        };
      });
    $('psAids').onkeydown = (e) =>
      radioKeys(e, '#psAids button', (b) => {
        setAids(b.dataset.v);
        drawPreview();
      });
    setAids(S.aids);
    $('psAidsWrap').hidden = !(S.test.language_id === ZH || S.test.language_id === JA);
    $('psHl').onchange = (e) => {
      S.hl = e.target.checked;
      $('psPassage').classList.toggle('hl', S.hl);
    };
    document.querySelectorAll('#psTabs .ps-tab').forEach((b) => {
      b.onclick = (e) => {
        e.stopPropagation();
        setTab(b.dataset.tab);
      };
    });
    $('psTabs').onkeydown = (e) => radioKeys(e, '#psTabs .ps-tab', (b) => setTab(b.dataset.tab));
    setTab('passage');
    $('psNextStep').onclick = onNext;
    $('psTakeTest').onclick = () => takeTest(true);
    $('psProduce').onclick = startProduce;
    $('psBackToSession').onclick = backToSession;
    $('psDone').onclick = async (e) => {
      e.preventDefault();
      await postEvidence();
      window.location.href = $('psDone').getAttribute('href');
    };
    $('psScrim').onclick = () => hidePop(true);
    document.addEventListener('click', (e) => {
      const POP = $('psPop');
      if (POP && !POP.hidden && !POP.contains(e.target)) hidePop();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hidePop(true);
    });
    document.querySelectorAll('.ps-step').forEach((s) => {
      const h = () => {
        const n = parseInt(s.dataset.step, 10);
        if (n === 3 && S.step !== 3 && !(S.phase === 'done')) {
          S.phase = 'done';
        }
        go(n);
      };
      s.onclick = h;
      s.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          h();
        }
      };
    });

    $('psLoading').hidden = true;
    $('psMain').hidden = false;
    $('psActionBar').hidden = false;
    if (S.mode === 'followup') {
      // after the attempt: no preview, a short prime, then Produce
      const s1 = document.querySelector('.ps-step[data-step="1"]');
      if (s1) s1.hidden = true;
      const s2 = document.querySelector('.ps-step[data-step="2"]');
      if (s2) s2.textContent = T('prestudy.step_followup');
      if ($('psS2Title')) $('psS2Title').textContent = T('prestudy.step_followup');
      const s3 = document.querySelector('.ps-step[data-step="3"]');
      if (s3) s3.textContent = S.canProduce ? T('prestudy.step_produce') : T('prestudy.step_done');
      go(2);
    } else {
      go(1);
    }
  }

  // exposed for unit-style checks in the browser console and tests
  window.LinguaPrestudy = {
    gradeJa,
    gradeZh,
    sandhiTones,
    parsePinyinInput,
    kanaToRomaji,
    normRomaji,
    readingParts,
    bktUpdate,
    bktUpdateIdk,
    meaningOptions,
    plausibleMeaning,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
