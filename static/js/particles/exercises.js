// static/js/particles/exercises.js
// Turns bank items and pattern packs into exercises, and judges answers.
// Pure functions: the page (js/pages/particle-drill.js) owns the DOM.
import { answerMatches } from './kana.js';
import { expand, parse, stripReading } from './markup.js';

export function shuffle(list, rng = Math.random) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const pick = (list, rng) => list[Math.floor(rng() * list.length)];

/** One concrete item from a pattern pack (a random combination of its values). */
export function fromPack(pack, rng = Math.random) {
  const jp = {};
  const en = {};
  const key = [];
  for (const name of Object.keys(pack.vars)) {
    const i = Math.floor(rng() * pack.vars[name].length);
    key.push(i);
    [jp[name], en[name]] = pack.vars[name][i];
  }
  return {
    id: `pack:${pack.id}:${key.join('.')}`,
    jp: expand(pack.tpl, jp),
    en: sentenceCase(expand(pack.en, en)),
    f: pack.f,
    d: pack.d,
    why: pack.why,
    lv: pack.lv,
    generated: true,
  };
}

const sentenceCase = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);

/** How many different sentences a pack can produce. */
export function packSize(pack) {
  return Object.values(pack.vars).reduce((n, values) => n * values.length, 1);
}

/**
 * An endless supply of items for one skill: the authored bank in shuffled
 * order with previously missed items first, mixed with sentences generated
 * from the pattern packs. When the bank runs out it is reshuffled, so a
 * session never ends for lack of content.
 */
export class Deck {
  constructor({ items = [], packs = [], missed = [], rng = Math.random, packShare = 0.3 } = {}) {
    this.rng = rng;
    this.items = items;
    this.packs = packs;
    this.packShare = items.length ? (packs.length ? packShare : 0) : 1;
    this.first = missed.map((id) => items.find((it) => it.id === id)).filter(Boolean);
    this.queue = [];
    this.recent = [];
  }

  get size() {
    return this.items.length + this.packs.length;
  }

  refill() {
    const firstIds = new Set(this.first.map((it) => it.id));
    this.queue = [
      ...this.first,
      ...shuffle(
        this.items.filter((it) => !firstIds.has(it.id)),
        this.rng
      ),
    ];
    this.first = [];
  }

  next() {
    if (!this.size) return null;
    for (let tries = 0; tries < 8; tries++) {
      let item;
      if (this.packs.length && this.rng() < this.packShare) {
        item = fromPack(pick(this.packs, this.rng), this.rng);
      } else {
        if (!this.queue.length) this.refill();
        item = this.queue.shift();
      }
      if (item && !this.recent.includes(item.id)) {
        this.recent.push(item.id);
        if (this.recent.length > 12) this.recent.shift();
        return item;
      }
    }
    return this.items.length
      ? pick(this.items, this.rng)
      : fromPack(pick(this.packs, this.rng), this.rng);
  }
}

/** Slot count and parsed form of an item (cached on the item). */
export function parsed(item) {
  if (!item._p) {
    Object.defineProperty(item, '_p', { value: parse(item.jp), enumerable: false });
    item.slotCount = item._p.slots.length;
  }
  return item._p;
}

const accepted = (slot) => [slot.a, ...slot.alt];
const uniq = (list) => list.filter((x, i) => list.indexOf(x) === i);

/**
 * Build an exercise of `mode` from an item.
 *   meet / choose / speed  options[] for the focus slot
 *   type                   the focus slot is typed
 *   fill                   every slot is blank; bank[] holds the chips
 *   fix                    one slot shows a wrong particle (shown[]); the
 *                          learner taps it, then picks from options[]
 */
export function build(item, mode, rng = Math.random) {
  const p = parsed(item);
  const focus = Math.min(Math.max(item.f || 0, 0), p.slots.length - 1);
  const slot = p.slots[focus];
  // Answers and options are compared as displayed text; `ruby` maps each one
  // to its marked-up form (に対[たい]して) so it can be drawn with furigana.
  const ruby = {};
  p.slots.forEach((sl) => sl.raw.forEach((raw) => (ruby[stripReading(raw)] = raw)));
  const wrongs = (item.d || []).map((d) => {
    ruby[stripReading(d)] = d;
    return stripReading(d);
  });
  const ex = {
    item,
    mode,
    parsed: p,
    focus,
    answer: slot.a,
    accepted: accepted(slot),
    typed: uniq([...accepted(slot), ...slot.kana]),
    ruby,
  };
  if (item.ask === 'reading') {
    // The kanji word is shown (cue) and its reading is the answer.
    ex.cue = slot.a;
    ex.accepted = uniq(slot.kana);
    ex.answer = ex.accepted[0];
    ex.typed = ex.accepted;
    ex.bare = true; // options are plain readings; `ruby` is for the feedback line
    slot.kana.forEach((k, i) => (ruby[k] = slot.raw[i]));
  } else if (item.ask === 'kanji') {
    // The reading is shown (cue) and the written form is chosen, without furigana.
    ex.cue = slot.kana[0];
    ex.bare = true;
  }
  if (mode === 'meet' || mode === 'choose' || mode === 'speed') {
    const wrong = shuffle(wrongs, rng).slice(0, mode === 'meet' ? 2 : 3);
    ex.options = shuffle([ex.answer, ...wrong], rng);
  } else if (mode === 'fill') {
    const chips = p.slots.map((sl) => sl.a);
    const extra = shuffle(
      wrongs.filter((d) => !chips.includes(d)),
      rng
    ).slice(0, 2);
    ex.bank = shuffle([...chips, ...extra], rng);
  } else if (mode === 'fix') {
    const wrong = pick(wrongs, rng);
    ex.wrong = wrong;
    ex.shown = p.slots.map((sl, i) => (i === focus ? wrong : sl.a));
    ex.options = shuffle([slot.a, ...wrongs.filter((d) => d !== wrong).slice(0, 2)], rng);
  }
  return ex;
}

/** A chosen option (meet / choose / speed, and the second step of fix). */
export const gradeChoice = (ex, option) => ex.accepted.includes(option);

/** A typed answer for the focus slot. */
export const gradeTyped = (ex, typed) => answerMatches(ex.typed, typed);

/** Fill: one result per slot; the exercise is right when all are. */
export function gradeFill(ex, answers) {
  const perSlot = ex.parsed.slots.map((s, i) => accepted(s).includes(answers[i]));
  return { perSlot, correct: perSlot.every(Boolean) };
}

/** Fix, first step: did the learner tap the slot that is wrong? */
export const gradeFixTap = (ex, slotIndex) => slotIndex === ex.focus;
