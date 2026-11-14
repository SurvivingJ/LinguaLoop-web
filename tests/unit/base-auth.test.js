/**
 * static/js/pages/base-head.js + base.js: session renewal.
 *
 *  - the head script renews an expired token and gives up after one budget;
 *  - authFetch waits for that renewal for the same budget;
 *  - a token is renewed shortly before its `exp`, not after a 401.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const HEAD = readFileSync(join(root, 'static/js/pages/base-head.js'), 'utf8');
const BODY = readFileSync(join(root, 'static/js/pages/base.js'), 'utf8');

// Indirect eval: run as a classic script in the global scope.
const run = (code) => (0, eval)(code);

function b64url(obj) {
  return btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function jwt(expiresInSeconds) {
  const claims =
    expiresInSeconds === null
      ? { sub: 'u' }
      : { sub: 'u', exp: Math.floor(Date.now() / 1000) + expiresInSeconds };
  return `${b64url({ alg: 'HS256' })}.${b64url(claims)}.sig`;
}
function jsonResponse(body, ok = true) {
  return {
    ok,
    status: ok ? 200 : 401,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}
const calls = (fetchMock, path) => fetchMock.mock.calls.filter((c) => c[0] === path).length;

let fetchMock;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  localStorage.clear();
  sessionStorage.clear();
  document.head.innerHTML = '';
  document.body.innerHTML = '<main id="main-content"></main>';
  document.getElementById('__lingua_block_paint')?.remove();
  delete window.__ldAuthRenewal;
  window.happyDOM.setURL('http://localhost/tests');
  fetchMock = vi.fn(() => new Promise(() => {}));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('LinguaAuthBoot.tokenExpiryMs', () => {
  beforeEach(() => {
    localStorage.setItem('jwt_token', jwt(3600));
    run(HEAD);
  });

  it('reads exp from an unpadded base64url payload', () => {
    const exp = Math.floor(Date.now() / 1000) + 1234;
    const token = `${b64url({ alg: 'HS256' })}.${b64url({ exp, name: 'ü?>' })}.sig`;
    expect(window.LinguaAuthBoot.tokenExpiryMs(token)).toBe(exp * 1000);
  });

  it('is 0 for a missing or unparseable token and Infinity without exp', () => {
    expect(window.LinguaAuthBoot.tokenExpiryMs(null)).toBe(0);
    expect(window.LinguaAuthBoot.tokenExpiryMs('not-a-jwt')).toBe(0);
    expect(window.LinguaAuthBoot.tokenExpiryMs(jwt(null))).toBe(Infinity);
  });
});

describe('head script renewal', () => {
  it('leaves a page with a live token alone', () => {
    localStorage.setItem('jwt_token', jwt(3600));
    run(HEAD);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(window.__ldAuthRenewal).toBeUndefined();
    expect(document.getElementById('__lingua_block_paint')).toBeNull();
  });

  it('does nothing on a public path', () => {
    window.happyDOM.setURL('http://localhost/login');
    run(HEAD);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(document.getElementById('__lingua_block_paint')).toBeNull();
  });

  it('renews an expired token through the refresh cookie and reveals the page', async () => {
    const fresh = jwt(3600);
    localStorage.setItem('jwt_token', jwt(-60));
    fetchMock.mockImplementation(async () => jsonResponse({ success: true, jwt_token: fresh }));
    run(HEAD);
    expect(document.getElementById('__lingua_block_paint')).not.toBeNull();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/refresh-token');
    await window.__ldAuthRenewal;
    expect(localStorage.getItem('jwt_token')).toBe(fresh);
    expect(document.getElementById('__lingua_block_paint')).toBeNull();
    expect(document.getElementById('__lingua_auth_status')).toBeNull();
    expect(calls(fetchMock, '/api/auth/device-restore')).toBe(0);
  });

  it('falls back to the device cookie when the refresh cookie is rejected', async () => {
    const fresh = jwt(3600);
    fetchMock.mockImplementation(async (url) =>
      url === '/api/auth/refresh-token'
        ? jsonResponse({ success: false }, false)
        : jsonResponse({ success: true, jwt_token: fresh, user: { id: 'u' } })
    );
    run(HEAD);
    await window.__ldAuthRenewal;
    expect(localStorage.getItem('jwt_token')).toBe(fresh);
    expect(JSON.parse(localStorage.getItem('user_data'))).toEqual({ id: 'u' });
    expect(document.getElementById('__lingua_block_paint')).toBeNull();
  });

  it('gives a hung renewal the whole budget before redirecting to login', () => {
    run(HEAD);
    const budget = window.LinguaAuthBoot.RENEWAL_BUDGET_MS;
    expect(budget).toBeGreaterThanOrEqual(5000);
    const status = () => document.getElementById('__lingua_auth_status').textContent;
    expect(status()).toContain('Checking');
    vi.advanceTimersByTime(budget - 1);
    expect(status()).toContain('Checking');
    vi.advanceTimersByTime(1);
    expect(status()).toContain('Redirecting');
    expect(document.getElementById('__lingua_block_paint')).not.toBeNull();
  });
});

describe('authFetch', () => {
  it('waits for the head renewal for the same budget as the failsafe', async () => {
    localStorage.setItem('jwt_token', jwt(3600));
    run(HEAD);
    run(BODY);
    const budget = window.LinguaAuthBoot.RENEWAL_BUDGET_MS;
    window.__ldAuthRenewal = new Promise(() => {});
    fetchMock.mockImplementation(async () => jsonResponse({ ok: 1 }));
    const pending = window.authFetch('/api/thing');
    await vi.advanceTimersByTimeAsync(budget - 1);
    expect(calls(fetchMock, '/api/thing')).toBe(0);
    await vi.advanceTimersByTimeAsync(1);
    await pending;
    expect(calls(fetchMock, '/api/thing')).toBe(1);
  });

  it('sends the renewed token once the head renewal settles', async () => {
    const fresh = jwt(3600);
    localStorage.setItem('jwt_token', jwt(-60));
    let finish;
    fetchMock.mockImplementation((url) =>
      url === '/api/auth/refresh-token'
        ? new Promise((resolve) => {
            finish = () => resolve(jsonResponse({ success: true, jwt_token: fresh }));
          })
        : Promise.resolve(jsonResponse({ ok: 1 }))
    );
    run(HEAD);
    run(BODY);
    const pending = window.authFetch('/api/thing');
    await vi.advanceTimersByTimeAsync(100);
    expect(calls(fetchMock, '/api/thing')).toBe(0);
    finish();
    await pending;
    const sent = fetchMock.mock.calls.find((c) => c[0] === '/api/thing')[1];
    expect(sent.headers.Authorization).toBe(`Bearer ${fresh}`);
  });
});

describe('proactive renewal', () => {
  it('refreshes about a minute before exp, then re-arms for the new token', async () => {
    localStorage.setItem('jwt_token', jwt(600));
    const fresh = jwt(600 + 3600);
    fetchMock.mockImplementation(async () => jsonResponse({ success: true, jwt_token: fresh }));
    run(HEAD);
    run(BODY);

    await vi.advanceTimersByTimeAsync(530 * 1000);
    expect(calls(fetchMock, '/api/auth/refresh-token')).toBe(0);

    await vi.advanceTimersByTimeAsync(15 * 1000);
    expect(calls(fetchMock, '/api/auth/refresh-token')).toBe(1);
    expect(localStorage.getItem('jwt_token')).toBe(fresh);
    expect(window.LINGUADOJO.JWT_TOKEN).toBe(fresh);

    // The replacement lives another hour: nothing more until it nears expiry.
    await vi.advanceTimersByTimeAsync(3000 * 1000);
    expect(calls(fetchMock, '/api/auth/refresh-token')).toBe(1);
    await vi.advanceTimersByTimeAsync(700 * 1000);
    expect(calls(fetchMock, '/api/auth/refresh-token')).toBe(2);
  });

  it('does not retry in a loop when the renewal fails', async () => {
    localStorage.setItem('jwt_token', jwt(120));
    fetchMock.mockImplementation(async () => jsonResponse({ success: false }, false));
    run(HEAD);
    run(BODY);
    await vi.advanceTimersByTimeAsync(3600 * 1000);
    expect(calls(fetchMock, '/api/auth/refresh-token')).toBe(1);
    expect(calls(fetchMock, '/api/auth/device-restore')).toBe(1);
  });

  it('is not scheduled on public pages or without a token', async () => {
    window.happyDOM.setURL('http://localhost/login');
    localStorage.setItem('jwt_token', jwt(120));
    run(HEAD);
    run(BODY);
    await vi.advanceTimersByTimeAsync(3600 * 1000);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
