/**
 * static/js/dt-test-entry.js: the test preview page's "Translate a passage
 * from this test" link is shown only when the server says a passage is ready,
 * and then opens /dual-translation scoped to that test.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SCRIPT = readFileSync(join(root, 'static/js/dt-test-entry.js'), 'utf8');
const ID = 'bbbbbbbb-0000-0000-0000-000000000002';

let api;
beforeEach(() => {
  document.body.innerHTML =
    '<a class="ld-btn d-none" id="dtFromTest" href="/dual-translation">Translate</a>';
  window.eval(SCRIPT);
  api = window.DTTestEntry;
});

function fetchReturning(status, body, seen) {
  return async (url) => {
    if (seen) seen.push(url);
    return { ok: status < 400, status, json: async () => body };
  };
}

describe('dt-test-entry', () => {
  it('reads the slug from the preview path only', () => {
    expect(api.slugFromPath('/test/my-test-1/preview')).toBe('my-test-1');
    expect(api.slugFromPath('/test/my-test-1')).toBe('');
    expect(api.slugFromPath('/tests')).toBe('');
  });

  it('shows the link scoped to the test when a passage is ready', async () => {
    const seen = [];
    const link = document.getElementById('dtFromTest');
    const shown = await api.reveal(
      link,
      fetchReturning(200, { available: true, test_id: ID }, seen),
      '/test/my-test-1/preview'
    );
    expect(shown).toBe(true);
    expect(seen).toEqual(['/api/dual-translation/test-available?slug=my-test-1']);
    expect(link.classList.contains('d-none')).toBe(false);
    expect(link.getAttribute('href')).toBe(`/dual-translation?test_id=${ID}`);
  });

  it.each([
    [200, { available: false, test_id: ID }],
    [200, { available: true, test_id: 'not-a-uuid' }],
    [404, { error: 'Test not found' }],
    [500, {}],
  ])('stays hidden for %s %j', async (status, body) => {
    const link = document.getElementById('dtFromTest');
    expect(await api.reveal(link, fetchReturning(status, body), '/test/x/preview')).toBe(false);
    expect(link.classList.contains('d-none')).toBe(true);
  });

  it('stays hidden when the request throws', async () => {
    const link = document.getElementById('dtFromTest');
    const boom = async () => {
      throw new Error('offline');
    };
    expect(await api.reveal(link, boom, '/test/x/preview')).toBe(false);
    expect(link.classList.contains('d-none')).toBe(true);
  });
});
