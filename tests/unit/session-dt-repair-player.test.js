/**
 * static/js/session/players/dt_repair.js (tech §8.8): the daily "fix your sentences" block.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/dt_repair.js';

const flush = () => new Promise((r) => setTimeout(r, 0));
const ITEMS = [{ item_id: 8101, step_kind: 'repair', hint_rungs: [1, 2, 3] }];

let ctx;
let container;
let sheet;

beforeEach(() => {
  ctx = { languageId: 7, onComplete: vi.fn(), onSkip: vi.fn() };
  container = document.createElement('div');
  document.body.appendChild(container);
  sheet = { opened: null, dispose: vi.fn(), close: vi.fn() };
  window.DTRepairSheet = {
    open: vi.fn((o) => {
      sheet.opened = o;
      return sheet;
    }),
  };
});

afterEach(() => {
  container.remove();
  delete window.authFetch;
  delete window.DTRepairSheet;
});

const due = (items, status = 200) => {
  window.authFetch = vi.fn(async () => ({
    ok: status < 400,
    status,
    json: async () => ({ status: 'success', items, total_due: items.length }),
  }));
};

describe('dt_repair player', () => {
  it('asks for the due items of the session language', async () => {
    due(ITEMS);
    mount(container, ctx);
    await flush();
    expect(window.authFetch).toHaveBeenCalledWith(
      '/api/dual-translation/repair/practice/due?language_id=7'
    );
  });

  it('nothing due completes the block without opening the sheet', async () => {
    due([]);
    mount(container, ctx);
    await flush();
    expect(ctx.onComplete).toHaveBeenCalledWith({ dt_repair: 0 });
    expect(window.DTRepairSheet.open).not.toHaveBeenCalled();
  });

  it('opens the sheet in daily mode with the items; finishing completes the block', async () => {
    due(ITEMS);
    mount(container, ctx);
    await flush();
    expect(sheet.opened.mode).toBe('daily');
    expect(sheet.opened.items).toEqual(ITEMS);
    sheet.opened.onDone({ completed: 1, closedEarly: false });
    expect(ctx.onComplete).toHaveBeenCalledWith({ dt_repair: 1 });
    expect(ctx.onSkip).not.toHaveBeenCalled();
  });

  it('closing the sheet early skips the block', async () => {
    due(ITEMS);
    mount(container, ctx);
    await flush();
    sheet.opened.onDone({ completed: 0, closedEarly: true });
    expect(ctx.onSkip).toHaveBeenCalled();
    expect(ctx.onComplete).not.toHaveBeenCalled();
  });

  it('a failing fetch shows the unavailable card with Skip for now', async () => {
    due([], 500);
    mount(container, ctx);
    await flush();
    container.querySelector('[data-dtr-skip]').click();
    expect(ctx.onSkip).toHaveBeenCalled();
  });

  it('a missing sheet script degrades to the same card', async () => {
    delete window.DTRepairSheet;
    due(ITEMS);
    mount(container, ctx);
    await flush();
    expect(container.querySelector('[data-dtr-skip]')).not.toBeNull();
  });

  it('destroy() disposes the sheet and silences callbacks', async () => {
    due(ITEMS);
    const handle = mount(container, ctx);
    await flush();
    handle.destroy();
    expect(sheet.dispose).toHaveBeenCalled();
    sheet.opened.onDone({ completed: 1 });
    expect(ctx.onComplete).not.toHaveBeenCalled();
  });
});
