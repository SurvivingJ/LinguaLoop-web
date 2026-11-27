// static/js/grammar/check.js
// Grammar drills: answer checking. No DOM.

import { EMPTY, fillCloze, optionParts } from './text.js';

/** The option string that is right for a cloze item. */
export function rightOption(item) {
  return item && item.opts ? item.opts[item.a] : '';
}

/** `choice` is an option string ('了', '因为|所以', '∅'). */
export function checkCloze(item, choice) {
  return choice != null && choice === rightOption(item);
}

/**
 * Typed text as an option string: parts separated by spaces, commas, '|' or
 * '…' become 'a|b'; nothing typed is ∅.
 */
export function typedToOption(text) {
  const parts = String(text == null ? '' : text)
    .split(/[\s|,，、…]+/)
    .filter(Boolean);
  return parts.length ? parts.join('|') : EMPTY;
}

/** A typed answer is right when it is exactly the right option. */
export function checkTyped(item, text) {
  return typedToOption(text) === rightOption(item);
}

/** `built` is the list of tile texts in the learner's order. */
export function checkOrder(item, built) {
  const got = (built || []).join('');
  if (!got) return false;
  if (got === (item.tokens || []).join('')) return true;
  return (item.alts || []).some((alt) => alt.join('') === got);
}

/** `saysOk` is true when the learner called the sentence correct. */
export function checkJudge(item, saysOk) {
  return !!saysOk === !!item.ok;
}

/** The full correct sentence for any item ('' when the item carries none). */
export function correctSentence(item) {
  if (item.zh) return item.zh;
  if (item.type === 'cloze') return fillCloze(item.q, rightOption(item));
  if (item.tokens) return item.tokens.join('');
  return '';
}

/** Number of blanks an option fills. */
export function blankCount(opt) {
  return optionParts(opt).length;
}
