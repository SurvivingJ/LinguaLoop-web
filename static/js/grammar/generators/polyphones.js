/**
 * polyphones generator (多音字): a word is shown and the reading of one of its
 * characters is chosen. The word table is authored and reviewed
 * (data/grammar_drills/zh/words/polyphones.json) and built into
 * polyphones-data.js by scripts/grammar_drills_swarm.py build-words.
 *
 * Options are pinyin syllables: the right reading and the character's other
 * real readings. `zh` is the word followed by its pronunciation, as in the
 * tone-sandhi generators.
 */
import { pick, shuffle } from './util.js';
import { POLYPHONES } from './polyphones-data.js';

/** Words by level (1-3), so easy words come up as often as hard ones. */
const BY_LEVEL = [1, 2, 3].map((lvl) => POLYPHONES.filter((row) => row[6] === lvl));
const LEVELS = BY_LEVEL.filter((rows) => rows.length);

export function makePolyphone(rng) {
  const [word, py, at, wrong, en, why] = pick(rng, pick(rng, LEVELS));
  const syllables = py.split(' ');
  const right = syllables[at];
  const opts = shuffle(rng, [right, ...wrong]);
  const pre = syllables.slice(0, at).join(' ');
  const post = syllables.slice(at + 1).join(' ');
  return {
    id: 'gen:polyphone',
    type: 'cloze',
    q: `${word} → ${pre ? `${pre} ` : ''}___${post ? ` ${post}` : ''}`,
    opts,
    a: opts.indexOf(right),
    zh: `${word} → ${py}`,
    py,
    en,
    why,
    cue: `How is ${word[at]} read in this word?`,
  };
}

export const generators = [
  { key: 'polyphone', label: '多音字: which reading?', make: makePolyphone },
];
