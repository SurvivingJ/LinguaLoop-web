/**
 * static/js/session/save_queue.js — background saves: in order, retried, and
 * never dropped when they finally fail.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { createSaveQueue } from '../../static/js/session/save_queue.js';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('save queue', () => {
  it('enqueue returns at once and resolves true when the save is acknowledged', async () => {
    const q = createSaveQueue();
    let release;
    const send = vi.fn(() => new Promise((r) => (release = r)));
    const saved = q.enqueue(send, 'a');
    expect(q.pending).toBe(1);
    await Promise.resolve();
    await Promise.resolve();
    expect(send).toHaveBeenCalledTimes(1);
    release(true);
    expect(await saved).toBe(true);
    expect(q.pending).toBe(0);
    expect(await q.settle()).toBe(true);
  });

  it('sends one save at a time, in the order queued', async () => {
    const q = createSaveQueue();
    const log = [];
    const job = (name) => async () => {
      log.push(`start ${name}`);
      await new Promise((r) => setTimeout(r, 5));
      log.push(`end ${name}`);
      return true;
    };
    q.enqueue(job('a'));
    q.enqueue(job('b'));
    q.enqueue(job('c'));
    await q.settle();
    expect(log).toEqual(['start a', 'end a', 'start b', 'end b', 'start c', 'end c']);
  });

  it('retries a save that is rejected or throws, with backoff', async () => {
    vi.useFakeTimers();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const q = createSaveQueue({ delays: [1000, 3000] });
    const send = vi
      .fn()
      .mockResolvedValueOnce(false)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(true);
    const saved = q.enqueue(send);
    await vi.advanceTimersByTimeAsync(0);
    expect(send).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(999);
    expect(send).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(send).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(3000);
    expect(send).toHaveBeenCalledTimes(3);
    expect(await saved).toBe(true);
    expect(q.failed).toBe(0);
  });

  it('keeps a save that used all its retries, reports it and can retry it', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const onFail = vi.fn();
    const changes = [];
    const q = createSaveQueue({ delays: [0, 0], onFail, onChange: (c) => changes.push({ ...c }) });
    let online = false;
    const send = vi.fn(async () => online);
    expect(await q.enqueue(send, 'block-1')).toBe(false);
    expect(send).toHaveBeenCalledTimes(3);
    expect(onFail).toHaveBeenCalledTimes(1);
    expect(onFail.mock.calls[0][0].label).toBe('block-1');
    expect(q.failed).toBe(1);
    expect(await q.settle()).toBe(false);
    expect(changes.at(-1)).toEqual({ pending: 0, failed: 1 });

    online = true;
    expect(await q.retryFailed()).toBe(true);
    expect(q.failed).toBe(0);
    expect(changes.at(-1)).toEqual({ pending: 0, failed: 0 });
  });

  it('a failed save does not hold back the ones behind it', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const q = createSaveQueue({ delays: [] });
    const first = q.enqueue(async () => false);
    const second = q.enqueue(async () => true);
    expect(await first).toBe(false);
    expect(await second).toBe(true);
    expect(q.failed).toBe(1);
  });

  it('settle() waits for saves queued while it was waiting', async () => {
    const q = createSaveQueue();
    const done = [];
    q.enqueue(async () => {
      q.enqueue(async () => {
        done.push('late');
        return true;
      });
      done.push('first');
      return true;
    });
    await q.settle();
    expect(done).toEqual(['first', 'late']);
  });

  it('hurry() cuts the current backoff short', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const q = createSaveQueue({ delays: [60000] });
    const send = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const saved = q.enqueue(send);
    await new Promise((r) => setTimeout(r, 0));
    expect(send).toHaveBeenCalledTimes(1);
    q.hurry();
    expect(await saved).toBe(true);
    expect(send).toHaveBeenCalledTimes(2);
  });

  it('a throwing callback cannot break the queue', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const q = createSaveQueue({
      delays: [],
      onFail: () => {
        throw new Error('ui');
      },
    });
    expect(await q.enqueue(async () => false)).toBe(false);
    expect(await q.enqueue(async () => true)).toBe(true);
  });
});
