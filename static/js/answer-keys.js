/**
 * LinguaKeys — keep the on-screen keyboard open between typed answers, and
 * keep answer feedback in view above it.
 *
 * On a phone the keyboard closes as soon as the focused text box is disabled
 * or focus moves to a button, and it only reopens on a tap. So after an
 * answer is checked the box stays focused but frozen (hold), Enter / "Go" on
 * the keyboard moves on, and the next item's box takes the focus while the
 * keyboard is still up (focus). Feedback is scrolled into the part of the
 * screen the keyboard and any sticky bottom bar leave visible (reveal).
 *
 * Plain script (window.LinguaKeys) so classic pages and ES-module players can
 * both use it; every call is a no-op when an element is missing.
 */
(function (root) {
  'use strict';

  // Fixed / sticky bars at the bottom of the screen that can cover feedback.
  const BOTTOM_BARS = '[data-bottom-bar]';
  const MARGIN = 12;

  function isTyping(el) {
    if (!el) return false;
    if (el.tagName === 'TEXTAREA') return true;
    if (el.tagName !== 'INPUT') return false;
    const t = (el.getAttribute('type') || 'text').toLowerCase();
    return ['text', 'search', 'email', 'url', 'tel', 'number', 'password'].includes(t);
  }

  /** Bottom edge (viewport px) of the screen area nothing covers. */
  function visibleBottom() {
    const vv = root.visualViewport;
    let bottom = vv ? vv.offsetTop + vv.height : root.innerHeight;
    document.querySelectorAll(BOTTOM_BARS).forEach((bar) => {
      if (!bar.offsetParent && getComputedStyle(bar).position !== 'fixed') return;
      const r = bar.getBoundingClientRect();
      if (r.height && r.top < bottom && r.bottom > r.top) bottom = Math.min(bottom, r.top);
    });
    return bottom;
  }

  /** Top edge (viewport px) below any sticky header. */
  function visibleTop() {
    const vv = root.visualViewport;
    let top = vv ? vv.offsetTop : 0;
    const head = document.querySelector('header.sticky-top');
    if (head && getComputedStyle(head).position === 'sticky') {
      const r = head.getBoundingClientRect();
      if (r.bottom > top && r.top <= top + 1) top = r.bottom;
    }
    return top;
  }

  /**
   * Scroll so `el` is fully visible above the keyboard and bottom bars. When
   * it is taller than the space left, its top is kept in view instead.
   * `keep` (optional) is an element whose top should stay visible if possible
   * (e.g. the question prompt above the feedback).
   */
  function reveal(el, keep) {
    if (!el || !el.getBoundingClientRect) return;
    const run = () => {
      const r = el.getBoundingClientRect();
      if (!r.height) return;
      const top = visibleTop() + MARGIN;
      const bottom = visibleBottom() - MARGIN;
      let dy = 0;
      if (r.bottom > bottom) dy = r.bottom - bottom;
      if (r.top - dy < top) dy = r.top - top; // too tall: show its start
      if (keep && dy > 0) {
        const k = keep.getBoundingClientRect();
        // Prefer keeping the prompt on screen when the feedback still fits.
        if (k.top - dy < top && r.bottom - (k.top - top) <= bottom) dy = k.top - top;
      }
      if (Math.abs(dy) > 2) root.scrollBy({ top: dy, behavior: 'smooth' });
    };
    // After layout (and after a keyboard resize that the same tap caused).
    root.requestAnimationFrame(() => root.requestAnimationFrame(run));
  }

  /**
   * Focus a text box without the browser's jumpy scroll, then bring it (and
   * `keep`, usually the prompt) into the visible area.
   */
  function focus(input, keep) {
    if (!input) return;
    try {
      input.focus({ preventScroll: true });
    } catch (_) {
      input.focus();
    }
    lastKeep = keep || null;
    reveal(input, keep);
  }

  // The keyboard opens (or resizes) after focus: whenever the visible area
  // shrinks, bring the focused answer box back above it and any bottom bar.
  let lastKeep = null;
  let lastHeight = root.visualViewport ? root.visualViewport.height : root.innerHeight;
  function onViewportResize() {
    const h = root.visualViewport ? root.visualViewport.height : root.innerHeight;
    const shrank = h < lastHeight - 40;
    lastHeight = h;
    const el = document.activeElement;
    if (!shrank || !isTyping(el)) return;
    reveal(el, lastKeep && lastKeep.isConnected ? lastKeep : null);
  }
  if (root.visualViewport) root.visualViewport.addEventListener('resize', onViewportResize);
  else if (root.addEventListener) root.addEventListener('resize', onViewportResize);

  /**
   * After an answer is checked: freeze the text box but leave it focused so
   * the keyboard stays up, and make Enter call `onNext`. Returns true when
   * the box had the focus (callers then skip moving focus to a button).
   */
  function hold(input, onNext) {
    if (!input || input.dataset.llHeld) return false;
    const hadFocus = document.activeElement === input;
    const value = input.value;
    input.dataset.llHeld = '1';
    input.setAttribute('aria-readonly', 'true');
    input.classList.add('ll-held');
    // readOnly would close the keyboard on some phones; undo edits instead.
    const undo = () => {
      if (input.value !== value) input.value = value;
    };
    input.addEventListener('beforeinput', (e) => {
      if (e.cancelable) e.preventDefault();
    });
    input.addEventListener('input', undo);
    input.addEventListener('compositionend', () => root.setTimeout(undo, 0));
    input.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (typeof onNext === 'function') onNext();
    });
    if (!hadFocus && document.activeElement && isTyping(document.activeElement)) return false;
    return hadFocus;
  }

  /**
   * The usual end of a checked typed item: hold the box when it has focus,
   * otherwise focus `nextBtn` (desktop Enter, and taps on choices); then
   * reveal the feedback.
   */
  function afterAnswer({ input, nextBtn, feedback, keep, onNext }) {
    const next = onNext || (nextBtn ? () => nextBtn.click() : null);
    const held = input && document.activeElement === input ? hold(input, next) : false;
    if (!held && nextBtn && !isTyping(document.activeElement)) {
      try {
        nextBtn.focus({ preventScroll: true });
      } catch (_) {
        nextBtn.focus();
      }
    }
    reveal(feedback || nextBtn, keep);
  }

  root.LinguaKeys = { hold, focus, reveal, afterAnswer, isTyping };
})(typeof window !== 'undefined' ? window : globalThis);
