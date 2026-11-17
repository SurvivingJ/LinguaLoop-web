/**
 * static/js/session/players/classifier_drill.js — measure-word drill levels
 * and mastery wiring (TASK-998).
 *
 * In Auto mode each item is drawn at the level the server stamped (1 Choose,
 * 2 Type, 3 Reverse, 4 Fill in), lowered when the item lacks the content for
 * it, and the badge names what is drawn. Every answer is sent in
 * item_results against classifier_id_primary, so the server can call
 * update_classifier_mastery; Choose / Type modes pin the level.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/classifier_drill.js';

// Microtasks only: setTimeout is faked.
const flush = async () => {
  for (let i = 0; i < 20; i++) await Promise.resolve();
};

const item = (over) => ({
  pair_id: 1,
  noun_lemma: '书',
  noun_pronunciation: 'shū',
  noun_gloss: '',
  correct_classifier_ids: [379, 440],
  correct_classifier_hanzi: ['本', '种'],
  correct_classifier_pinyin: ['běn', 'zhǒng'],
  distractor_ids: [1, 2, 3],
  distractor_hanzi: ['册', '部', '份'],
  distractor_pinyin: ['cè', 'bù', 'fèn'],
  semantic_label: 'bound',
  level: 1,
  classifier_id_primary: 379,
  reverse_noun_options: ['猫', '车', '鱼'],
  cloze_sentence: '这本书很好看。',
  cloze_blanked: '这___书很好看。',
  ...over,
});

let submits;
let batch;

function mountWith(items) {
  batch = items;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const player = mount(container, { item: {}, languageId: 1, onComplete: vi.fn() });
  return { container, player };
}

const $ = (c, sel) => c.querySelector(sel);
const badge = (c) => $(c, '#cdLevelBadge').textContent.trim();
const optionTexts = (c) =>
  [...c.querySelectorAll('#cdOptions .cd-option-text')].map((n) => n.textContent);

async function pick(c, text) {
  const idx = optionTexts(c).indexOf(text);
  expect(idx).toBeGreaterThanOrEqual(0);
  c.querySelectorAll('#cdOptions .cd-option')[idx].click();
  await vi.advanceTimersByTimeAsync(500);
}

async function type(c, text) {
  $(c, '#cdTypedInput').value = text;
  $(c, '#cdTypedForm').dispatchEvent(new Event('submit', { cancelable: true }));
  await vi.advanceTimersByTimeAsync(500);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  localStorage.clear();
  submits = [];
  window.authFetch = vi.fn(async (url, opts) => {
    if (url.startsWith('/api/classifier-drill/session')) {
      return { ok: true, json: async () => ({ data: { items: batch } }) };
    }
    submits.push(JSON.parse(opts.body));
    return { ok: true, json: async () => ({ data: { mastery_updates: [] } }) };
  });
  window.requestAnimationFrame = (fn) => fn();
});

afterEach(() => {
  delete window.authFetch;
  document.body.innerHTML = '';
  vi.useRealTimers();
});

describe('Auto mode draws each item at its level', () => {
  it('walks Choose, Type, Reverse and Fill in, and records every answer', async () => {
    const { container: c } = mountWith([
      item({ level: 1 }),
      item({ level: 2 }),
      item({ level: 3 }),
      item({ level: 4 }),
    ]);
    await vi.advanceTimersByTimeAsync(0);

    // 1 Choose: classifier options with the noun shown.
    expect(badge(c)).toBe('Choose');
    expect($(c, '#cdNoun').textContent).toBe('书');
    expect(optionTexts(c)).toContain('本');
    await pick(c, '本');

    // 2 Type: the typed form, no options.
    expect(badge(c)).toBe('Type');
    expect($(c, '#cdTypedForm').style.display).toBe('block');
    expect($(c, '#cdOptions').style.display).toBe('none');
    await type(c, '本');

    // 3 Reverse: the classifier is given, the options are nouns.
    expect(badge(c)).toBe('Reverse');
    expect($(c, '#cdReversePrompt').textContent).toBe('Which noun takes 本?');
    expect(optionTexts(c).sort()).toEqual(['书', '猫', '车', '鱼'].sort());
    await pick(c, '猫'); // wrong
    expect($(c, '#cdFeedback').classList.contains('show')).toBe(true);
    $(c, '#cdFeedbackContinue').click();
    await vi.advanceTimersByTimeAsync(0);

    // 4 Fill in: the sentence with a blank, classifier options.
    expect(badge(c)).toBe('Fill in');
    expect($(c, '#cdReversePrompt').querySelector('.cd-cloze').textContent).toContain('这');
    expect($(c, '#cdReversePrompt .cd-cloze-blank')).not.toBeNull();
    expect($(c, '#cdPromptWrap').style.display).toBe('none');
    await pick(c, '本');
    await flush();
    await vi.advanceTimersByTimeAsync(0);

    expect(submits).toHaveLength(1);
    expect(submits[0].correct_items).toBe(3);
    expect(submits[0].total_items).toBe(4);
    expect(submits[0].item_results).toEqual([
      { classifier_id: 379, is_correct: true, level: 1 },
      { classifier_id: 379, is_correct: true, level: 2 },
      { classifier_id: 379, is_correct: false, level: 3 },
      { classifier_id: 379, is_correct: true, level: 4 },
    ]);
  });

  it('falls back to a level the content supports and badges it', async () => {
    const { container: c } = mountWith([
      item({ level: 4, cloze_blanked: null }), // no sentence -> Reverse
      item({ level: 4, cloze_blanked: null, reverse_noun_options: [] }), // -> Type
      item({ level: 3, reverse_noun_options: [] }), // no wrong nouns -> Type
      item({ level: null }), // unstamped (old server) -> Choose
    ]);
    await vi.advanceTimersByTimeAsync(0);
    expect(badge(c)).toBe('Reverse');
    await pick(c, '书');
    expect(badge(c)).toBe('Type');
    await type(c, '本');
    expect(badge(c)).toBe('Type');
    await type(c, '本');
    expect(badge(c)).toBe('Choose');
    await pick(c, '本');
    await flush();
    await vi.advanceTimersByTimeAsync(0);
    expect(submits[0].item_results.map((r) => r.level)).toEqual([3, 2, 2, 1]);
  });

  it('records nothing for an item with no answer classifier', async () => {
    const { container: c } = mountWith([item({ classifier_id_primary: null })]);
    await vi.advanceTimersByTimeAsync(0);
    await pick(c, '本');
    await flush();
    await vi.advanceTimersByTimeAsync(0);
    expect(submits[0].correct_items).toBe(1);
    expect(submits[0].item_results).toEqual([]);
  });
});

describe('manual modes pin the level', () => {
  it('Choose ignores the stamped level and hides the badge', async () => {
    localStorage.setItem('cd_mode', 'mc');
    const { container: c } = mountWith([item({ level: 4 }), item({ level: 3 })]);
    await vi.advanceTimersByTimeAsync(0);
    expect($(c, '#cdLevelBadge').style.display).toBe('none');
    expect($(c, '#cdNoun').textContent).toBe('书');
    await pick(c, '本');
    await pick(c, '部'); // wrong
    $(c, '#cdFeedbackContinue').click();
    await flush();
    await vi.advanceTimersByTimeAsync(0);
    expect(submits[0].item_results).toEqual([
      { classifier_id: 379, is_correct: true, level: 1 },
      { classifier_id: 379, is_correct: false, level: 1 },
    ]);
  });
});
