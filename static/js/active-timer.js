// static/js/active-timer.js
// Active-time measurement for the weekly "Studied this week" minutes
// (wiki/features/weekly-minutes.tech.md, TASK-893).
//
// A timer counts only while the tab is visible AND the learner has produced a
// pointer / key / touch / wheel event in the last IDLE_MS (45 s). Time beyond
// the idle window, and time with the tab hidden, is dropped. The server clamps
// whatever we send, so this is a measurement, never an authority.
//
// Classic <script>: exposes window.ActiveTimer.
//   ActiveTimer.start()  begin (or restart from zero) the shared timer
//   ActiveTimer.stop()   -> integer ms of active time since start(); stops it
//   ActiveTimer.reset()  discard accumulated time and stop
//   ActiveTimer.create() independent timer with the same API (for tests/players)
//   ActiveTimer.newEventId() uuid for client_event_id (crypto.randomUUID or uuid4 fallback)
//   ActiveTimer.IDLE_MS
(function (root) {
  'use strict';

  const IDLE_MS = 45000;
  const ACTIVITY_EVENTS = ['pointerdown', 'pointermove', 'mousedown', 'keydown', 'touchstart', 'wheel', 'scroll'];

  function uuidFallback() {
    const bytes = new Array(16);
    const cryptoObj = root.crypto;
    for (let i = 0; i < 16; i++) {
      bytes[i] =
        cryptoObj && typeof cryptoObj.getRandomValues === 'function'
          ? cryptoObj.getRandomValues(new Uint8Array(1))[0]
          : Math.floor(Math.random() * 256);
    }
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10xx
    const hex = bytes.map(function (b) {
      return (b + 0x100).toString(16).slice(1);
    });
    return (
      hex.slice(0, 4).join('') + '-' + hex.slice(4, 6).join('') + '-' +
      hex.slice(6, 8).join('') + '-' + hex.slice(8, 10).join('') + '-' +
      hex.slice(10, 16).join('')
    );
  }

  function newEventId() {
    if (root.crypto && typeof root.crypto.randomUUID === 'function') {
      try {
        return root.crypto.randomUUID();
      } catch {
        /* insecure context etc. - fall through */
      }
    }
    return uuidFallback();
  }

  function isVisible() {
    const doc = root.document;
    return !doc || doc.visibilityState === undefined || doc.visibilityState === 'visible';
  }

  function create() {
    let running = false;
    let total = 0; // ms
    let lastTick = 0; // last time we accounted up to
    let lastActivity = 0;
    let visible = true;

    function account(now) {
      if (running && visible) {
        const upTo = Math.min(now, lastActivity + IDLE_MS);
        if (upTo > lastTick) total += upTo - lastTick;
      }
      if (now > lastTick) lastTick = now;
    }

    function onActivity() {
      const now = Date.now();
      account(now);
      lastActivity = now;
    }

    function onVisibility() {
      const now = Date.now();
      account(now);
      visible = isVisible();
      if (visible) {
        // Coming back to the tab counts as activity.
        lastTick = now;
        lastActivity = now;
      }
    }

    function attach() {
      const doc = root.document;
      if (!doc) return;
      ACTIVITY_EVENTS.forEach(function (ev) {
        doc.addEventListener(ev, onActivity, { capture: true, passive: true });
      });
      doc.addEventListener('visibilitychange', onVisibility);
    }

    function detach() {
      const doc = root.document;
      if (!doc) return;
      ACTIVITY_EVENTS.forEach(function (ev) {
        doc.removeEventListener(ev, onActivity, { capture: true });
      });
      doc.removeEventListener('visibilitychange', onVisibility);
    }

    return {
      start: function () {
        if (running) detach();
        const now = Date.now();
        total = 0;
        lastTick = now;
        lastActivity = now; // showing the card/passage is itself an interaction
        visible = isVisible();
        running = true;
        attach();
      },
      stop: function () {
        if (!running) return 0;
        account(Date.now());
        running = false;
        detach();
        const ms = Math.max(0, Math.round(total));
        total = 0;
        return ms;
      },
      reset: function () {
        if (running) detach();
        running = false;
        total = 0;
      },
      isRunning: function () {
        return running;
      },
    };
  }

  const shared = create();
  const api = {
    start: shared.start,
    stop: shared.stop,
    reset: shared.reset,
    isRunning: shared.isRunning,
    create: create,
    newEventId: newEventId,
    IDLE_MS: IDLE_MS,
  };

  root.ActiveTimer = api;
})(typeof window !== 'undefined' ? window : globalThis);
