/**
 * static/js/session/players/flashcards.js — the next card shows as soon as a
 * rating is given; review POSTs are queued (in order, retried) and all sent
 * before the block completes.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/flashcards.js';

const flush = () => new Promise((r) => setTimeout(r, 0));

const CARDS = [
  { card_id: 'c1', lemma: '木', definition: 'tree' },
  { card_id: 'c2', lemma: '水', definition: 'water' },
];

let reviewImpl;
let reviews;
let dueCalls;

beforeEach(() => {
  reviews = [];
  dueCalls = 0;
  reviewImpl = async () => ({ ok: true });
  window.authFetch = vi.fn(async (url, opts) => {
    if (url.startsWith('/api/flashcards/due')) {
      dueCalls++;
      return { ok: true, json: async () => ({ data: { cards: CARDS } }) };
    }
    reviews.push(JSON.parse(opts.body));
    return reviewImpl(url, opts);
  });
  window.showToast = vi.fn();
});

afterEach(() => {
  delete window.authFetch;
  delete window.showToast;
  document.body.innerHTML = '';
  vi.useRealTimers();
  vi.restoreAllMocks();
});

async function setup(item = { kind: 'flashcards', cards: 15 }) {
  const c = document.createElement('div');
  document.body.appendChild(c);
  const ctx = { item, languageId: 2, onComplete: vi.fn(), onSkip: vi.fn() };
  mount(c, ctx);
  await flush();
  await flush();
  const rate = (value) => {
    c.querySelector('[data-fc-reveal]').click();
    c.querySelector(`[data-fc-rating="${value}"]`).click();
  };
  return { c, ctx, rate };
}

describe('flashcards player', () => {
  it('shows the next card before the review POST returns', async () => {
    let release;
    reviewImpl = () => new Promise((r) => (release = () => r({ ok: true })));
    const { c, ctx, rate } = await setup();
    expect(c.querySelector('h2').textContent).toBe('木');
    rate(3);
    // Synchronously on the next card, with the POST still pending.
    expect(c.querySelector('h2').textContent).toBe('水');
    await flush();
    expect(reviews).toEqual([{ card_id: 'c1', rating: 3 }]);
    expect(ctx.onComplete).not.toHaveBeenCalled();
    release();
    await flush();
  });

  it('flushes every review, in order, before completing the block', async () => {
    const releases = [];
    reviewImpl = () => new Promise((r) => releases.push(() => r({ ok: true })));
    const { ctx, rate } = await setup();
    rate(3);
    rate(1);
    await flush();
    // Last card rated, but the block is not complete until the saves land.
    expect(ctx.onComplete).not.toHaveBeenCalled();
    expect(reviews).toHaveLength(1);
    releases[0]();
    await flush();
    expect(reviews.map((r) => r.card_id)).toEqual(['c1', 'c2']);
    expect(ctx.onComplete).not.toHaveBeenCalled();
    releases[1]();
    await flush();
    expect(ctx.onComplete).toHaveBeenCalledWith({ reviewed: 2 });
  });

  it('retries a failed review and still completes, reporting the loss', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const { ctx, rate } = await setup();
    vi.useFakeTimers();
    let attempts = 0;
    reviewImpl = async (url, opts) => {
      const body = JSON.parse(opts.body);
      if (body.card_id === 'c1') {
        attempts++;
        return { ok: false, status: 500 };
      }
      return { ok: true };
    };
    rate(3);
    rate(4);
    await vi.advanceTimersByTimeAsync(5000);
    expect(attempts).toBe(3);
    expect(window.showToast).toHaveBeenCalledTimes(1);
    expect(ctx.onComplete).toHaveBeenCalledWith({ reviewed: 1 });
  });

  it('uses a prefetched due list instead of loading again', async () => {
    const item = {
      kind: 'flashcards',
      cards: 1,
      prefetch: Promise.resolve({ ok: true, data: { data: { cards: CARDS } } }),
    };
    const { c } = await setup(item);
    expect(dueCalls).toBe(0);
    expect('prefetch' in item).toBe(false);
    expect(c.querySelector('p').textContent).toContain('1 of 1');
  });

  it('an empty deck completes the block', async () => {
    window.authFetch = vi.fn(async () => ({ ok: true, json: async () => ({ data: { cards: [] } }) }));
    const { ctx } = await setup();
    expect(ctx.onComplete).toHaveBeenCalledWith({ reviewed: 0 });
  });
});
