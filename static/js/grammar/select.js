// static/js/grammar/select.js
// Grammar drills: which items a round holds, the answer bank of the recall
// stage, and which topic to recommend. No DOM; randomness comes in as `rng`.

import { blankCount, rightOption } from './check.js';
import { isInstant, levelCap, stageDef } from './ladder.js';
import { itemKey } from './store.js';

export const ROUND_SIZE = 20;
/** Share of a round kept for items missed before, when there are any. */
export const MISSED_SHARE = 0.3;
export const BANK_SIZE = 8;

/** Answers that must pass before a box's items are due again (box 1-5). */
const BOX_GAP = [0, 15, 40, 100, 250, 600];

function shuffled(list, rng) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Selection class of an item, lower first: 0 never seen, 1 missed last time,
 * 2 seen and due again (Leitner gap passed), 3 seen and not due. Items above
 * the level cap rank after every item within it.
 */
export function itemClass(item, slug, topic, cap) {
  const rec = topic.items[itemKey(slug, item.id)];
  let cls;
  if (!rec) cls = 0;
  else if (rec[0] === 0) cls = 1;
  else cls = topic.seq - rec[1] >= BOX_GAP[Math.min(rec[0], BOX_GAP.length - 1)] ? 2 : 3;
  return (item.lvl || 1) > cap ? cls + 4 : cls;
}

/**
 * Up to `n` of `cands` ([{ item, cls, seen }]): lowest class first; inside a
 * class the sub-points take turns, each giving its least recently seen item.
 */
function take(cands, n, rng) {
  const out = [];
  const classes = [...new Set(cands.map((c) => c.cls))].sort((a, b) => a - b);
  for (const cls of classes) {
    if (out.length >= n) break;
    const bySub = new Map();
    shuffled(
      cands.filter((c) => c.cls === cls),
      rng
    )
      .sort((a, b) => a.seen - b.seen)
      .forEach((c) => {
        const sub = c.item.sub || '';
        if (!bySub.has(sub)) bySub.set(sub, []);
        bySub.get(sub).push(c);
      });
    const queues = shuffled([...bySub.values()], rng);
    while (out.length < n && queues.some((q) => q.length)) {
      for (const q of queues) {
        if (out.length >= n) break;
        if (q.length) out.push(q.shift());
      }
    }
  }
  return out;
}

/**
 * The items of one round for a topic at a stage.
 *   items  the topic's items          topic  the store's view of the topic
 *   stage  1-4                        size   round length
 * Order of preference: items missed before (up to MISSED_SHARE of the round),
 * then never-seen items, then seen items that are due, then the least recently
 * seen; sub-points balanced; only the stage's types; item levels up to
 * ladder.levelCap (higher levels only when nothing else is left). A stage with
 * `focus` types fills `focusShare` of the round from them when it can.
 */
export function pickRound({ items, slug, topic, stage, size = ROUND_SIZE, rng = Math.random }) {
  const def = stageDef(stage);
  const cap = levelCap(topic);
  const cands = (items || [])
    .filter((it) => def.types.includes(it.type))
    .map((item) => {
      const rec = topic.items[itemKey(slug, item.id)];
      return { item, cls: itemClass(item, slug, topic, cap), seen: rec ? rec[1] : 0 };
    });
  const picked = new Set();
  const add = (list) => list.forEach((c) => picked.add(c));
  const left = () => cands.filter((c) => !picked.has(c));

  add(
    take(
      cands.filter((c) => c.cls === 1),
      Math.ceil(size * MISSED_SHARE),
      rng
    )
  );
  if (def.focus) {
    const isFocus = (c) => def.focus.includes(c.item.type);
    const want = Math.round(size * def.focusShare) - [...picked].filter(isFocus).length;
    if (want > 0) add(take(left().filter(isFocus), Math.min(want, size - picked.size), rng));
  }
  add(take(left(), size - picked.size, rng));
  return shuffled([...picked], rng).map((c) => c.item);
}

/**
 * The chips a recall-stage cloze is answered from: distinct right answers used
 * across the topic's cloze items (same number of blanks), most frequent first,
 * always with this item's answer and with those of its own distractors that
 * are answers elsewhere; at most `cap`, in a fixed (code point) order so a
 * form keeps its place from item to item. Falls back to the item's own
 * options when the topic has fewer than two distinct answers.
 */
export function answerBank(items, item, cap = BANK_SIZE) {
  const right = rightOption(item);
  const blanks = blankCount(right);
  const freq = new Map();
  (items || []).forEach((it) => {
    if (it.type !== 'cloze' || !it.opts) return;
    const ans = rightOption(it);
    if (blankCount(ans) !== blanks) return;
    freq.set(ans, (freq.get(ans) || 0) + 1);
  });
  if (!freq.has(right)) freq.set(right, 1);
  if (freq.size < 2) return (item.opts || []).slice();
  const byFreq = [...freq.keys()].sort((a, b) => freq.get(b) - freq.get(a) || (a < b ? -1 : 1));
  const own = (item.opts || []).filter((o) => o !== right && freq.has(o));
  const bank = [...new Set([right, ...own, ...byFreq])].slice(0, cap);
  return bank.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

/**
 * The topic to continue with: the most recently practised one that is not yet
 * instant, else the first topic (manifest order) with items that is not
 * instant, else the first topic. `topics` are manifest topics; `store` gives
 * practised() and topic(slug).
 */
export function recommendTopic(topics, store) {
  const bySlug = new Map((topics || []).map((t) => [t.slug, t]));
  const open = (slug) => bySlug.has(slug) && !isInstant(store.topic(slug));
  const recent = store.practised().find(open);
  if (recent) return bySlug.get(recent);
  return (topics || []).find((t) => t.count > 0 && open(t.slug)) || (topics || [])[0] || null;
}

/**
 * Topics for a mixed review round: practised topics that have items, most
 * recent first, at most `max`.
 */
export function mixedTopics(topics, store, max = 5) {
  const bySlug = new Map((topics || []).map((t) => [t.slug, t]));
  return store
    .practised()
    .map((slug) => bySlug.get(slug))
    .filter((t) => t && t.count > 0 && store.topic(t.slug).seq > 0)
    .slice(0, max);
}

/**
 * A mixed round: `size` items spread evenly over `parts`
 * ([{ slug, items, topic }]), each drawn as that topic's own round at its
 * current stage. Returns [{ slug, item }] shuffled.
 */
export function pickMixed(parts, size = ROUND_SIZE, rng = Math.random) {
  const out = [];
  const live = (parts || []).filter((p) => p.items && p.items.length);
  live.forEach((p, k) => {
    const share = Math.ceil((size - out.length) / (live.length - k));
    pickRound({
      items: p.items,
      slug: p.slug,
      topic: p.topic,
      stage: p.topic.stage,
      size: share,
      rng,
    }).forEach((item) => out.push({ slug: p.slug, item }));
  });
  return shuffled(out, rng).slice(0, size);
}
