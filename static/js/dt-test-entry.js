/* Dual translation entry on the test preview page (2026-11-17).
 *
 * "Translate a passage from this test": shown only when the test has a 2-4
 * sentence window whose reviewed references in the learner's language clear
 * the quality bar (GET /api/dual-translation/test-available, the prestudy
 * Produce rule). It opens /dual-translation?test_id=<id>, where every passage
 * comes from this test. A passage of a test not taken yet says so on screen.
 * Best effort: any failure leaves the link hidden.
 */
(function () {
  'use strict';

  function slugFromPath(path) {
    const m = /^\/test\/([^/]+)\/preview\/?$/.exec(path || '');
    return m ? decodeURIComponent(m[1]) : '';
  }

  async function reveal(link, fetchFn, path) {
    const slug = slugFromPath(path);
    if (!link || !slug || typeof fetchFn !== 'function') return false;
    try {
      const res = await fetchFn(
        '/api/dual-translation/test-available?slug=' + encodeURIComponent(slug)
      );
      if (!res || !res.ok) return false;
      const data = await res.json();
      if (!data || data.available !== true || !/^[0-9a-fA-F-]{36}$/.test(data.test_id || '')) {
        return false;
      }
      link.href = '/dual-translation?test_id=' + encodeURIComponent(data.test_id);
      link.classList.remove('d-none');
      return true;
    } catch {
      return false;
    }
  }

  window.DTTestEntry = { slugFromPath: slugFromPath, reveal: reveal };

  document.addEventListener('DOMContentLoaded', function () {
    reveal(document.getElementById('dtFromTest'), window.authFetch, window.location.pathname);
  });
})();
