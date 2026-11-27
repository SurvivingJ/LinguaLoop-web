/**
 * Infinite-practice generators for the Chinese grammar drills. Each
 * generator builds one drill item (shaped like the static items described in
 * data/grammar_drills/zh/SPEC.md) from curated word lists.
 *
 *   generatorsFor(slug) -> [{ key, label, make(rng) }]
 *   GENERATOR_TOPICS    -> slugs that have at least one generator
 *
 * `rng` returns a float in [0, 1) and defaults to Math.random; every random
 * choice goes through it, so a seeded rng reproduces a session.
 */
import { generators as numbersTime } from './numbers-time.js';
import { generators as erLiang } from './er-liang.js';
import { generators as toneSandhi } from './tone-sandhi.js';
import { generators as measureWords } from './measure-words.js';
import { generators as deThree } from './de-three.js';
import { generators as buMei } from './bu-mei.js';
import { generators as potential } from './potential-complement.js';
import { generators as wordOrder } from './word-order.js';
import { baGenerators, beiGenerators } from './ba-bei.js';
import { generators as comparison } from './comparison.js';
import { generators as duration } from './duration-frequency.js';
import { generators as separable } from './separable-verbs.js';

const TABLE = {
  'numbers-time': numbersTime,
  'er-liang': erLiang,
  'tone-sandhi': toneSandhi,
  'measure-words': measureWords,
  'de-three': deThree,
  'bu-mei': buMei,
  'potential-complement': potential,
  'word-order': wordOrder,
  ba: baGenerators,
  bei: beiGenerators,
  comparison,
  'duration-frequency': duration,
  'separable-verbs': separable,
};

const withDefaultRng = ({ key, label, make }) => ({
  key,
  label,
  make: (rng = Math.random) => make(rng),
});

const READY = Object.fromEntries(
  Object.entries(TABLE).map(([slug, list]) => [slug, list.map(withDefaultRng)])
);

/** Slugs of the topics that have generators. */
export const GENERATOR_TOPICS = Object.keys(READY);

/** Generators for a topic slug; an empty array when the topic has none. */
export function generatorsFor(slug) {
  return Object.prototype.hasOwnProperty.call(READY, slug) ? READY[slug].slice() : [];
}
