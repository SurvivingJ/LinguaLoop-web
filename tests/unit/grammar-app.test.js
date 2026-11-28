/**
 * static/js/grammar/app.js: the /grammar-drill screens in a DOM. Hub -> topic
 * (guide) -> a round where a missed item comes back -> results; pinyin on
 * demand (P); settings kept in the store; a topic with generators only offers
 * Endless.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mountGrammar } from '../../static/js/grammar/app.js';
import { createStore } from '../../static/js/grammar/store.js';
import { CLOZE, CLOZE_NONE, JUDGE_BAD, memoryStorage, seeded } from './fixtures/grammar.js';

const GUIDE = {
  topic: 'le',
  summary: 'What 了 does.',
  subs: [{ key: 'completed-quantified', label: '了 after the verb' }],
  rules: [
    {
      sub: 'completed-quantified',
      rule: 'Counted object: 了 after the verb.',
      pattern: 'S + V + 了 + number',
      examples: [
        { zh: '我买了三本书。', py: 'wǒ mǎi le sān běn shū', en: 'I bought three books.' },
      ],
    },
  ],
  contrasts: [
    {
      wrong: '我昨天没去了。',
      right: { zh: '我昨天没去。', py: 'wǒ zuó tiān méi qù', en: "I didn't go yesterday." },
      why: '没 already says it did not happen.',
    },
  ],
  cheat: ['Counted object? 了 after the verb.'],
};
const ITEMS = [CLOZE, CLOZE_NONE, { ...JUDGE_BAD, id: 'le-01-003' }];
const MANIFEST = {
  language: 'zh',
  categories: [{ key: 'aspect', title: 'Aspect and time' }],
  total: 3,
  topics: [
    {
      slug: 'le',
      title: '了: completed action',
      zh: '了',
      cat: 'aspect',
      count: 3,
      v: 'abc',
      subs: [
        { key: 'completed-quantified', label: '了 after the verb' },
        { key: 'no-le', label: 'No 了 for habits' },
      ],
    },
    { slug: 'tone-sandhi', title: 'Tone changes', zh: '变调', cat: 'aspect', count: 0, v: 'def' },
  ],
};
const GEN = {
  key: 'bu',
  label: '不',
  make: () => ({
    id: 'gen:bu',
    type: 'cloze',
    cue: 'Tone of 不',
    q: '不 + 是 → ___',
    opts: ['bú', 'bù'],
    a: 0,
  }),
};

const flush = async () => {
  for (let i = 0; i < 30; i++) await Promise.resolve();
};
const press = (key) =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));

let root;
let app;
let store;
let fetched;

async function mount(storage = memoryStorage(), extra = {}) {
  store = createStore(storage);
  app = mountGrammar(root, {
    ...extra,
    manifestUrl: '/static/data/grammar/zh/manifest.json?v=1',
    manifest: MANIFEST,
    store,
    rng: seeded(11),
    generators: (slug) => (slug === 'tone-sandhi' ? [GEN] : []),
  });
  await flush();
}

/** Answer the cloze / judge on screen; `right` false picks a wrong answer. */
function answer(right) {
  const text = root.querySelector('.gd-item').textContent;
  const item = ITEMS.find((it) => text.includes(it.en));
  if (item.type === 'judge') {
    root
      .querySelector(`[data-act="judge"][data-ok="${(right ? item.ok : !item.ok) ? 1 : 0}"]`)
      .click();
  } else {
    const want = right ? item.a : item.a === 0 ? 1 : 0;
    root.querySelectorAll('.gd-opt')[want].click();
  }
  return item;
}

beforeEach(() => {
  history.replaceState(null, '', location.pathname);
  root = document.createElement('div');
  document.body.appendChild(root);
  fetched = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url) => {
      fetched.push(String(url));
      const slug = String(url).split('/').pop().split('.')[0];
      return {
        ok: true,
        json: async () => ({ topic: slug, guide: GUIDE, items: slug === 'le' ? ITEMS : [] }),
      };
    })
  );
});

afterEach(() => {
  if (app) app.destroy();
  root.remove();
  vi.unstubAllGlobals();
});

describe('grammar drill app', () => {
  it('shows the hub with a card per topic and Mixed review closed until something is practised', async () => {
    await mount();
    expect(root.querySelectorAll('.gd-topic')).toHaveLength(2);
    expect(root.querySelector('.gd-topic[data-slug="le"]').textContent).toContain('3 items');
    expect(root.querySelector('.gd-topic[data-slug="tone-sandhi"]').textContent).toContain(
      'Endless practice'
    );
    expect(root.querySelector('[data-act="mixed"]').disabled).toBe(true);
    expect(root.querySelector('[data-act="continue"]').dataset.slug).toBe('le');
  });

  it('opens a topic with its guide, fetched from the versioned topic file', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    expect(fetched).toEqual(['/static/data/grammar/zh/le.json?v=abc']);
    expect(location.hash).toBe('#le');
    const guide = root.querySelector('.gd-guide');
    expect(guide.textContent).toContain('What 了 does.');
    expect(guide.querySelectorAll('ruby').length).toBeGreaterThan(0);
    expect(root.querySelectorAll('.gd-stagebtn:not(:disabled)')).toHaveLength(1);
    expect(root.querySelector('[data-act="start"]')).not.toBeNull();
    expect(root.querySelector('[data-act="endless"]')).toBeNull();
  });

  it('runs a round: a missed item returns until right, then results and stored progress', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
    expect(location.hash).toBe('#le/drill');
    expect(root.querySelector('.gd-count').textContent).toBe('0 / 3');

    const missed = answer(false);
    const fb = root.querySelector('.gd-fb');
    expect(fb.classList.contains('ld-feedback--bad')).toBe(true);
    expect(fb.textContent).toContain(missed.why);
    answer(true); // a second answer to the same item is ignored
    expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--bad')).toBe(true);
    root.querySelector('[data-act="next"]').click();

    const seen = [missed.id];
    let guard = 0;
    while (root.querySelector('.gd--drill') && guard++ < 10) {
      expect(root.querySelector('.gd-fb')).toBeNull();
      seen.push(answer(true).id);
      expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--ok')).toBe(true);
      press('Enter');
    }
    expect(seen).toHaveLength(4); // three items + the missed one again
    expect(seen.filter((id) => id === missed.id)).toHaveLength(2);
    expect(seen[3]).toBe(missed.id);

    const results = root.querySelector('.gd--results');
    expect(results.querySelector('.gd-results__pct').textContent).toBe('67%');
    expect(results.textContent).toContain('2 of 3 right first time');
    expect(results.querySelector('.gd-missed').textContent).toContain(missed.en);
    const view = store.topic('le');
    expect(view.results[1]).toHaveLength(3);
    expect(view.results[1].filter((r) => r < 0)).toHaveLength(1);
    expect(view.items[missed.id.slice(3)][0]).toBe(0);
  });

  it('shows "(nothing)" for ∅ and answers with number keys', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
    let guard = 0;
    while (!root.querySelector('.gd-item').textContent.includes(CLOZE_NONE.en) && guard++ < 5) {
      answer(true);
      press('Enter');
    }
    const labels = [...root.querySelectorAll('.gd-opt__text')].map((x) => x.textContent);
    expect(labels).toEqual(['了', '(nothing)']);
    expect(root.querySelector('.gd-sentence .gd-blank')).not.toBeNull();
    press('2');
    expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--ok')).toBe(true);
    expect(root.querySelector('.gd-sentence .gd-fill').textContent).toBe('(nothing)');
  });

  it('keeps pinyin hidden until P, and the answer syllable out of the question', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
    const screen = () => root.querySelector('.gd--drill');
    expect(screen().classList.contains('is-py')).toBe(false);
    press('p');
    expect(screen().classList.contains('is-py')).toBe(true);
    expect(root.querySelector('.gd-pybtn').getAttribute('aria-pressed')).toBe('true');
    let guard = 0;
    while (!root.querySelector('.gd-item').textContent.includes(CLOZE.en) && guard++ < 5) {
      answer(true);
      press('Enter');
    }
    // A new item starts with pinyin hidden again (the setting is off).
    const rts = () => [...root.querySelectorAll('.gd-sentence rt')].map((x) => x.textContent);
    expect(rts()).toEqual(['wǒ', 'zuó', 'tiān', 'mǎi', 'sān', 'běn', 'shū']);
    answer(true);
    expect(rts()).toContain('le');
  });

  it('remembers the settings and starts items with pinyin when "always" is on', async () => {
    const storage = memoryStorage();
    await mount(storage);
    const sw = root.querySelector('[data-act="setting"][data-name="pinyin"]');
    expect(sw.getAttribute('aria-checked')).toBe('false');
    sw.click();
    expect(sw.getAttribute('aria-checked')).toBe('true');
    expect(createStore(storage).settings()).toEqual({ pinyin: true, typing: false });
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
    expect(root.querySelector('.gd--drill').classList.contains('is-py')).toBe(true);
  });

  it('offers Endless for a topic with generators only and never stores generated items', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="tone-sandhi"]').click();
    await flush();
    expect(root.querySelector('[data-act="start"]')).toBeNull();
    root.querySelector('[data-act="endless"]').click();
    await flush();
    expect(location.hash).toBe('#tone-sandhi/endless');
    expect(root.querySelector('.gd-cue').textContent).toBe('Tone of 不');
    for (let k = 0; k < 4; k++) {
      root.querySelectorAll('.gd-opt')[0].click();
      root.querySelector('[data-act="next"]').click();
    }
    expect(root.querySelector('.gd-live').textContent).toContain('Streak 4');
    root.querySelector('[data-act="stop"]').click();
    expect(root.querySelector('.gd--results').textContent).toContain('4 of 4 right first time');
    const view = store.topic('tone-sandhi');
    expect(view.endless).toEqual({ answers: 4, correct: 4, best: 4 });
    expect(view.items).toEqual({});
  });

  const seedStage = (stage, extra = {}) =>
    memoryStorage({
      'ld.grammar.zh.v1': JSON.stringify({
        v: 1,
        s: {},
        t: { le: { s: stage, u: 4, r: [[], [], [], []], i: {}, q: 0, l: 0, ...extra } },
      }),
    });

  async function startRound(storage) {
    await mount(storage);
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
  }

  /** Move on until the item with this English cue is on screen. */
  function skipTo(item) {
    let guard = 0;
    while (!root.querySelector('.gd-item').textContent.includes(item.en) && guard++ < 6) {
      if (root.querySelector('[data-act="reveal"]')) press(' ');
      answer(true);
      root.querySelector('[data-act="next"]').click();
    }
  }

  describe('recall, then confirm', () => {
    beforeEach(() => {
      vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'Date'] });
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it('hides the item options until "Show choices" and times the recall apart from the total', async () => {
      await startRound(seedStage(3));
      skipTo(CLOZE);
      expect(root.querySelectorAll('.gd-opt')).toHaveLength(0);
      expect(root.querySelector('.gd-recall')).not.toBeNull();
      press('1'); // nothing to pick yet
      expect(root.querySelector('.gd-fb')).toBeNull();
      vi.advanceTimersByTime(1500);
      press(' ');
      // The item's OWN options, nothing borrowed from other items.
      expect([...root.querySelectorAll('.gd-opt__text')].map((x) => x.textContent)).toEqual(
        CLOZE.opts
      );
      vi.advanceTimersByTime(700);
      press('1');
      expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--ok')).toBe(true);
      const view = store.topic('le');
      expect(view.results[3].at(-1)).toBe(1500);
      expect(view.totals[3].at(-1)).toBe(2200);
    });

    it('lets the button reveal too, and a wrong pick after it is a miss', async () => {
      await startRound(seedStage(3));
      skipTo(CLOZE);
      vi.advanceTimersByTime(400);
      root.querySelector('[data-act="reveal"]').click();
      root.querySelectorAll('.gd-opt')[1].click();
      expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--bad')).toBe(true);
      expect(store.topic('le').results[3].at(-1)).toBe(-400);
    });

    it('types instead of revealing when "type answers" is on', async () => {
      const storage = seedStage(3);
      const data = JSON.parse(storage.data['ld.grammar.zh.v1']);
      data.s.ty = 1;
      storage.data['ld.grammar.zh.v1'] = JSON.stringify(data);
      await startRound(storage);
      skipToTyped();
      expect(root.querySelector('[data-act="reveal"]')).toBeNull();
      const input = root.querySelector('#gdTyped');
      input.value = '了';
      root.querySelector('[data-act="check"]').click();
      expect(root.querySelector('.gd-fb').classList.contains('ld-feedback--ok')).toBe(true);
    });

    function skipToTyped() {
      let guard = 0;
      while (!root.querySelector('.gd-item').textContent.includes(CLOZE.en) && guard++ < 6) {
        const item = ITEMS.find((it) => root.querySelector('.gd-item').textContent.includes(it.en));
        if (item.type === 'judge') answer(true);
        else root.querySelector('[data-act="typed-none"]').click();
        root.querySelector('[data-act="next"]').click();
      }
    }

    it('runs the speed countdown over both steps and pauses it while the guide is open', async () => {
      await startRound(seedStage(4, { sp: 8000 }));
      skipTo(CLOZE);
      expect(root.querySelector('.gd-timer')).not.toBeNull();
      vi.advanceTimersByTime(3000);
      press(' '); // reveal: the countdown keeps running
      expect(root.querySelector('.gd-timer')).not.toBeNull();
      vi.advanceTimersByTime(2000);
      root.querySelector('[data-act="guide"]').click();
      vi.advanceTimersByTime(60000); // reading the guide: no timeout
      expect(root.querySelector('.gd-fb')).toBeNull();
      press('Escape');
      expect(root.querySelector('.gd-sheet')).toBeNull();
      vi.advanceTimersByTime(2900); // 7.9 s on the clock
      expect(root.querySelector('.gd-fb')).toBeNull();
      vi.advanceTimersByTime(200); // 8.1 s: time is up
      expect(root.querySelector('.gd-fb').textContent).toContain('Time is up');
      expect(store.topic('le').results[4].at(-1)).toBe(-8000);
    });
  });

  it('opens the guide over a drill and closes it with Escape', async () => {
    await mount();
    root.querySelector('.gd-topic[data-slug="le"]').click();
    await flush();
    root.querySelector('[data-act="start"]').click();
    await flush();
    root.querySelector('[data-act="guide"]').click();
    expect(root.querySelector('.gd-sheet .gd-guide')).not.toBeNull();
    press('1'); // keys do not answer behind the guide
    expect(root.querySelector('.gd-fb')).toBeNull();
    press('Escape');
    expect(root.querySelector('.gd-sheet')).toBeNull();
  });

  describe('progress tracking (ADR-066)', () => {
    /** A sync stand-in: records what the page hands over, serves `progress`. */
    function fakeSync(progress = null) {
      const sent = [];
      return {
        sent,
        queueRound: vi.fn(async (mode, topics) => {
          sent.push({ mode, topics });
          return 1;
        }),
        pull: vi.fn(async () => progress),
        progress: () => progress,
      };
    }
    const day = (d, answers, correct, extra = {}) => ({
      topic: 'le',
      day: d,
      answers,
      correct,
      timed: correct,
      ms_sum: correct * 2500,
      stage: 1,
      instant: false,
      sub_misses: {},
      ...extra,
    });
    const HISTORY = {
      today: '2026-11-27',
      merged: 0,
      states: {},
      daily: [
        day('2026-11-10', 20, 10, { sub_misses: { 'no-le': 9 } }),
        day('2026-11-20', 20, 15, { sub_misses: { 'completed-quantified': 2, 'no-le': 3 } }),
        day('2026-11-27', 20, 18, { ms_sum: 18 * 1500, sub_misses: { 'no-le': 1 } }),
      ],
    };

    it('hands a finished round to the sync: first answers, misses by sub-point', async () => {
      const sync = fakeSync();
      await mount(memoryStorage(), { sync });
      expect(sync.pull).toHaveBeenCalledTimes(1);
      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      root.querySelector('[data-act="start"]').click();
      await flush();
      const missed = answer(false);
      root.querySelector('[data-act="next"]').click();
      let guard = 0;
      while (root.querySelector('.gd--drill') && guard++ < 10) {
        answer(true);
        press('Enter');
      }
      expect(root.querySelector('.gd--results')).not.toBeNull();
      expect(sync.sent).toHaveLength(1);
      expect(sync.sent[0].mode).toBe('round');
      const [topic] = sync.sent[0].topics;
      expect(topic).toMatchObject({ topic: 'le', answers: 3, correct: 2, timed: 2 });
      // 'no-le' is a sub-point of the topic; an item whose sub the manifest does
      // not list (the judge fixture) is counted as a miss without a sub-point.
      const known = ['completed-quantified', 'no-le'];
      expect(topic.sub_misses).toEqual(known.includes(missed.sub) ? { [missed.sub]: 1 } : {});
      // Leaving the results sends nothing more.
      root.querySelector('[data-act="hub"]').click();
      await flush();
      expect(sync.sent).toHaveLength(1);
    });

    it('sends the answers of a round left part-way, and nothing for one not started', async () => {
      const sync = fakeSync();
      await mount(memoryStorage(), { sync });
      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      root.querySelector('[data-act="start"]').click();
      await flush();
      history.back();
      await new Promise((r) => setTimeout(r, 20));
      await flush();
      expect(sync.sent).toHaveLength(0);
      root.querySelector('[data-act="start"]').click();
      await flush();
      answer(true);
      app.destroy();
      app = null;
      expect(sync.sent).toHaveLength(1);
      expect(sync.sent[0].topics[0]).toMatchObject({ topic: 'le', answers: 1, correct: 1 });
    });

    it('sends an Endless session when it is stopped', async () => {
      const sync = fakeSync();
      await mount(memoryStorage(), { sync });
      root.querySelector('.gd-topic[data-slug="tone-sandhi"]').click();
      await flush();
      root.querySelector('[data-act="endless"]').click();
      await flush();
      root.querySelectorAll('.gd-opt')[0].click();
      root.querySelector('[data-act="stop"]').click();
      expect(sync.sent).toEqual([
        {
          mode: 'endless',
          topics: [
            expect.objectContaining({
              topic: 'tone-sandhi',
              answers: 1,
              correct: 1,
              sub_misses: {},
            }),
          ],
        },
      ]);
    });

    it('draws no progress view without server history, and the screens still work', async () => {
      await mount(memoryStorage(), { sync: fakeSync(null) });
      expect(root.querySelector('.gd-trend')).toBeNull();
      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      expect(root.querySelector('.gd-trend')).toBeNull();
      expect(root.querySelector('.gd-guide')).not.toBeNull();
      app.destroy();
      history.replaceState(null, '', location.pathname);
      // A sync whose pull fails outright changes nothing either.
      const broken = fakeSync(null);
      broken.pull = vi.fn(async () => {
        throw new Error('offline');
      });
      await mount(memoryStorage(), { sync: broken });
      expect(root.querySelectorAll('.gd-topic')).toHaveLength(2);
      app.destroy();
      await mount(memoryStorage(), { sync: false });
      expect(root.querySelectorAll('.gd-topic')).toHaveLength(2);
    });

    it('shows the hub summary and the topic Progress card from the history', async () => {
      await mount(memoryStorage(), { sync: fakeSync(HISTORY) });
      const hub = root.querySelector('.gd-trend--hub');
      expect(hub).not.toBeNull();
      const stats = [...hub.querySelectorAll('.ld-stat__n')].map((x) => x.textContent);
      expect(stats).toEqual(['3', '60', '0']);
      const strip = hub.querySelector('.gd-trend__strip');
      expect(strip.getAttribute('aria-label')).toBe('Practice on 3 of the last 30 days');
      expect(strip.querySelectorAll('rect')).toHaveLength(30);
      expect(strip.querySelectorAll('.gd-trend__cell--4')).toHaveLength(3);

      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      const card = root.querySelector('.gd-trend');
      expect(card.dataset.days).toBe('3');
      const acc = card.querySelector('[data-measure="acc"]');
      expect(acc.querySelector('.gd-trend__v').textContent).toBe('90%');
      expect(acc.querySelector('.gd-trend__d').textContent).toBe('+40 pts since your first week');
      expect(acc.querySelector('svg').getAttribute('aria-label')).toBe(
        'Accuracy over 3 practised days, from 50% to 90%'
      );
      expect(acc.querySelectorAll('.gd-trend__hit title')).toHaveLength(3);
      expect(acc.querySelector('path').getAttribute('d')).toMatch(/^M6 /);
      const secs = card.querySelector('[data-measure="secs"]');
      expect(secs.querySelector('.gd-trend__v').textContent).toBe('1.5 s');
      expect(secs.querySelector('.gd-trend__d').textContent).toBe('−1.0 s since your first week');
      // Needs work: the last 14 days only (the 10th is outside), most missed first.
      const needs = [...card.querySelectorAll('.gd-trend__needs li')].map((li) => li.textContent);
      expect(needs).toEqual(['No 了 for habits4 missed', '了 after the verb2 missed']);
    });

    it('handles a topic with one recorded day and one with none', async () => {
      const one = { ...HISTORY, daily: [day('2026-11-27', 10, 0)] };
      await mount(memoryStorage(), { sync: fakeSync(one) });
      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      const card = root.querySelector('.gd-trend');
      expect(card.dataset.days).toBe('1');
      expect(card.querySelector('[data-measure="acc"] .gd-trend__v').textContent).toBe('0%');
      expect(card.querySelector('[data-measure="acc"] path')).toBeNull();
      expect(card.querySelector('[data-measure="acc"] .gd-trend__dot')).not.toBeNull();
      expect(card.querySelector('[data-measure="acc"] .gd-trend__d').textContent).toBe('');
      expect(card.querySelector('[data-measure="secs"]')).toBeNull();
      expect(card.textContent).toContain('No timed answers yet.');
      expect(card.textContent).toContain('One day recorded so far.');
      expect(card.textContent).toContain('No misses in the last 14 days.');
      app.destroy();

      history.replaceState(null, '', location.pathname);
      await mount(memoryStorage(), { sync: fakeSync({ ...HISTORY, daily: [] }) });
      expect(root.querySelector('.gd-trend--hub')).toBeNull();
      root.querySelector('.gd-topic[data-slug="le"]').click();
      await flush();
      expect(root.querySelector('.gd-trend').dataset.days).toBe('0');
      expect(root.querySelector('.gd-trend svg')).toBeNull();
    });

    it('redraws the hub when the server state unlocked a stage elsewhere', async () => {
      const storage = memoryStorage();
      const sync = fakeSync({ ...HISTORY, merged: 1 });
      sync.pull = vi.fn(async () => {
        store.mergeRemote('le', { u: 3, r: ['900', '800', '700', ''], q: 60, e: [0, 0, 0], l: 99 });
        return sync.progress();
      });
      await mount(storage, { sync });
      expect(root.querySelector('.gd-topic[data-slug="le"] .ld-tag').textContent).toContain(
        'Recall'
      );
      expect(root.querySelector('.gd-trend--hub')).not.toBeNull();
    });
  });
});
