import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
let AT;

beforeAll(() => {
  // eslint-disable-next-line no-eval
  eval(readFileSync(join(here, '..', '..', 'static/js/active-timer.js'), 'utf8'));
  AT = window.ActiveTimer;
});

function setVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true });
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('ActiveTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-14T10:00:00Z'));
    setVisibility('visible');
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts continuous activity', () => {
    const t = AT.create();
    t.start();
    for (let i = 0; i < 4; i++) {
      vi.advanceTimersByTime(10000);
      document.dispatchEvent(new Event('pointermove'));
    }
    expect(t.stop()).toBe(40000);
  });

  it('drops idle time beyond 45 s', () => {
    const t = AT.create();
    t.start();
    vi.advanceTimersByTime(10 * 60 * 1000);
    expect(t.stop()).toBe(AT.IDLE_MS);
  });

  it('excludes time while the tab is hidden', () => {
    const t = AT.create();
    t.start();
    vi.advanceTimersByTime(5000);
    setVisibility('hidden');
    vi.advanceTimersByTime(30000);
    setVisibility('visible');
    vi.advanceTimersByTime(7000);
    expect(t.stop()).toBe(12000);
  });

  it('stop without start returns 0 and reset discards time', () => {
    const t = AT.create();
    expect(t.stop()).toBe(0);
    t.start();
    vi.advanceTimersByTime(3000);
    t.reset();
    expect(t.isRunning()).toBe(false);
    expect(t.stop()).toBe(0);
  });

  it('returns an integer and restarts from zero', () => {
    const t = AT.create();
    t.start();
    vi.advanceTimersByTime(1500);
    expect(Number.isInteger(t.stop())).toBe(true);
    t.start();
    vi.advanceTimersByTime(2000);
    expect(t.stop()).toBe(2000);
  });

  it('shared start/stop API works', () => {
    AT.start();
    vi.advanceTimersByTime(1000);
    expect(AT.stop()).toBe(1000);
  });
});

describe('ActiveTimer.newEventId', () => {
  const uuidRe = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

  it('returns a uuid4', () => {
    expect(AT.newEventId()).toMatch(uuidRe);
  });

  it('falls back to a uuid4 generator without crypto.randomUUID', () => {
    const orig = window.crypto.randomUUID;
    Object.defineProperty(window.crypto, 'randomUUID', { value: undefined, configurable: true });
    try {
      const a = AT.newEventId();
      expect(a).toMatch(uuidRe);
      expect(AT.newEventId()).not.toBe(a);
    } finally {
      Object.defineProperty(window.crypto, 'randomUUID', { value: orig, configurable: true });
    }
  });
});
