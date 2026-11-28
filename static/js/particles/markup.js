// static/js/particles/markup.js
// The particle-drill sentence markup (twin of services/particle_drill/markup.py):
//   私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に/へ|ni-time}起[お]きます。
// 漢字[かな] is furigana, {answer/alt|skill} is a particle slot, <name> is a
// pattern-pack variable. A slot answer is kana, or kanji with furigana for the
// compound particles: {に対[たい]して|nitaishite}.

const KANJI = '\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff々〆ヶ';
const TOKEN_RE = new RegExp(
  '\\{([^{}|]*)(?:\\|([^{}]*))?\\}' + `|([${KANJI}]+)\\[([^\\[\\]]*)\\]` + '|<([a-z][a-z0-9_]*)>',
  'g'
);

const RUBY_RE = new RegExp(`([${KANJI}]+)\\[([^\\[\\]]*)\\]`, 'g');

/** に対[たい]して -> に対して (as displayed). */
export const stripReading = (marked) => String(marked || '').replace(RUBY_RE, '$1');

/** に対[たい]して -> にたいして (as typed in kana). */
export const readingOf = (marked) => String(marked || '').replace(RUBY_RE, '$2');

/**
 * Split marked-up text into segments.
 * Returns { segs, slots }. A segment is {t}, {t, r} (ruby), {slot: index} or
 * {v: name}; a slot is {a, alt: [], skill, raw: [], kana: []} where a / alt are
 * the displayed answers, raw the marked-up ones and kana their readings.
 */
export function parse(jp) {
  const segs = [];
  const slots = [];
  const text = String(jp || '');
  let pos = 0;
  TOKEN_RE.lastIndex = 0;
  let m;
  while ((m = TOKEN_RE.exec(text))) {
    if (m.index > pos) segs.push({ t: text.slice(pos, m.index) });
    pos = m.index + m[0].length;
    if (m[3] !== undefined) {
      segs.push({ t: m[3], r: m[4] });
    } else if (m[5] !== undefined) {
      segs.push({ v: m[5] });
    } else {
      const answers = (m[1] || '')
        .split('/')
        .map((a) => a.trim())
        .filter(Boolean);
      segs.push({ slot: slots.length });
      const shown = answers.map(stripReading);
      slots.push({
        a: shown[0] || '',
        alt: shown.slice(1),
        skill: (m[2] || '').trim(),
        raw: answers,
        kana: answers.map(readingOf),
      });
    }
  }
  if (pos < text.length) segs.push({ t: text.slice(pos) });
  return { segs, slots };
}

/** The sentence as plain text; `fill(slot, index)` supplies each slot's text. */
export function plain(jp, fill) {
  const { segs, slots } = parse(jp);
  return segs
    .map((s) => {
      if (s.slot !== undefined) return fill ? fill(slots[s.slot], s.slot) : slots[s.slot].a;
      if (s.v !== undefined) return `<${s.v}>`;
      return s.t;
    })
    .join('');
}

/** Substitute <name> variables. */
export function expand(tpl, values) {
  return String(tpl).replace(/<([a-z][a-z0-9_]*)>/g, (m, k) => (k in values ? values[k] : m));
}

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);

/**
 * HTML for a parsed sentence. `slotHtml(slot, index)` renders each slot;
 * text segments become <ruby> when they carry a reading.
 */
export function toHtml(parsed, slotHtml) {
  return parsed.segs
    .map((s) => {
      if (s.slot !== undefined) return slotHtml(parsed.slots[s.slot], s.slot);
      if (s.v !== undefined) return '';
      if (s.r) return `<ruby>${esc(s.t)}<rt>${esc(s.r)}</rt></ruby>`;
      return esc(s.t);
    })
    .join('');
}
