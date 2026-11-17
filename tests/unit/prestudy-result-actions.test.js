/**
 * Result-screen prestudy actions (static/js/prestudy/prestudy-links.js
 * renderResultActions): Produce is offered only when it can succeed.
 * E2E finding 2026-11-16: "Translate a passage from this test" was offered on
 * tests with no usable reference window, and Produce then answered 422 NO_WINDOW.
 */

import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';

let L;
beforeAll(async () => {
  await import('../../static/js/prestudy/prestudy-links.js');
  L = window.LinguaPrestudyLinks;
});

beforeEach(() => {
  sessionStorage.clear();
  document.body.innerHTML = '<div id="c"></div>';
  delete window.authFetch;
});

const box = () => document.getElementById('c');
const links = () => Array.from(box().querySelectorAll('a')).map((a) => a.textContent);
const PRODUCE = 'Translate a passage from this test (about 5 min)';
const FOLLOWUP = 'Review the words you missed (about 2 min)';

describe('renderResultActions', () => {
  it('offers the follow-up whenever answers were wrong', () => {
    L.renderResultActions(box(), { slug: 's', type: 'reading', wrong: 2, produceAvailable: false });
    expect(links()).toEqual([FOLLOWUP]);
  });

  it('offers Produce after a clean prestudied attempt only when it is available', () => {
    L.renderResultActions(box(), {
      slug: 's',
      type: 'reading',
      wrong: 0,
      prestudied: true,
      produceAvailable: true,
    });
    expect(links()).toEqual([PRODUCE]);
    document.body.innerHTML = '<div id="c"></div>';
    const el = L.renderResultActions(box(), {
      slug: 's',
      type: 'reading',
      wrong: 0,
      prestudied: true,
      produceAvailable: false,
    });
    expect(links()).toEqual([]);
    // the half-weight note still shows
    expect(el.textContent).toContain('half weight');
  });

  it('uses the answer the prestudy page left, without a request', () => {
    window.authFetch = vi.fn();
    L.setProduceAvailable('s', false);
    L.renderResultActions(box(), { slug: 's', type: 'reading', wrong: 0, prestudied: true });
    expect(links()).toEqual([]);
    expect(window.authFetch).not.toHaveBeenCalled();
    L.setProduceAvailable('s', true);
    document.body.innerHTML = '<div id="c"></div>';
    L.renderResultActions(box(), { slug: 's', type: 'reading', wrong: 0, prestudied: true });
    expect(links()).toEqual([PRODUCE]);
  });

  it('the hint survives the prestudied marker being cleared on submit', () => {
    L.setProduceAvailable('s', true);
    L.clearMarker('s');
    expect(L.knownProduceAvailable('s')).toBe(true);
    expect(L.knownProduceAvailable('other')).toBeNull();
  });

  it('asks the server once when nothing is known', async () => {
    window.authFetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ status: 'success', produce_available: true }),
    }));
    const el = L.renderResultActions(box(), {
      slug: 'a b',
      type: 'listening',
      wrong: 0,
      prestudied: true,
    });
    expect(links()).toEqual([]);
    await el.ready;
    expect(window.authFetch).toHaveBeenCalledWith('/api/tests/a%20b/prestudy/produce-available');
    expect(links()).toEqual([PRODUCE]);
  });

  it('shows nothing when the server says no or fails', async () => {
    window.authFetch = vi.fn(async () => ({ ok: false, json: async () => ({}) }));
    const el = L.renderResultActions(box(), {
      slug: 's',
      type: 'reading',
      wrong: 0,
      prestudied: true,
    });
    await el.ready;
    expect(links()).toEqual([]);
  });
});
