// static/js/session/prefetch.js
// Helpers for the optional per-player `prefetch(item, ctx)` hook. The registry
// stores what the hook returns on `item.prefetch` while the previous item is
// still in progress; the player takes it once when it mounts and falls back to
// its own request when there is nothing usable.
//
// A prefetch is a promise of { ok, data, ... } that never rejects.

/** GET `url` as JSON: resolves { ok, status, data }. */
export async function prefetchJson(url) {
  try {
    const res = await window.authFetch(url);
    if (!res || !res.ok) return { ok: false, status: res ? res.status : 0, data: null };
    return { ok: true, status: res.status, data: await res.json() };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

/** Take an item's prefetch (once). Resolves the result, or null if unusable. */
export async function takePrefetch(item) {
  const pending = item && item.prefetch;
  if (!pending) return null;
  delete item.prefetch;
  try {
    const res = await pending;
    return res && res.ok ? res : null;
  } catch {
    return null;
  }
}

/** Start downloading an audio file ahead of its player. */
export function warmAudio(url) {
  if (!url || typeof window.Audio !== 'function') return null;
  try {
    const audio = new window.Audio();
    audio.preload = 'auto';
    audio.src = url;
    return audio;
  } catch {
    return null;
  }
}

/**
 * Put a warmed audio element in place of the player's own <audio>, so the
 * bytes already downloaded are the ones played. Returns the element to use.
 */
export function adoptAudio(placeholder, warmed, url) {
  if (!warmed || !placeholder || warmed.getAttribute('src') !== url) {
    placeholder.src = url;
    return placeholder;
  }
  warmed.id = placeholder.id;
  placeholder.replaceWith(warmed);
  return warmed;
}
