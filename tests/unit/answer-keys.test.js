/** static/js/answer-keys.js: a checked typed answer keeps the keyboard up and Enter moves on. */
import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';

beforeAll(async () => {
  await import('../../static/js/answer-keys.js');
});

const K = () => window.LinguaKeys;

function enter(el, extra = {}) {
  const e = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true, ...extra });
  el.dispatchEvent(e);
  return e;
}

let input, next;
beforeEach(() => {
  document.body.innerHTML = '<form><input id="a" type="text"></form><button id="next">Next</button>';
  input = document.getElementById('a');
  next = document.getElementById('next');
  input.value = 'hito';
});

describe('hold', () => {
  it('keeps a focused box focused and enabled, and Enter calls onNext', () => {
    input.focus();
    const onNext = vi.fn();
    expect(K().hold(input, onNext)).toBe(true);
    expect(document.activeElement).toBe(input);
    expect(input.disabled).toBe(false);
    expect(input.readOnly).toBe(false);
    expect(input.getAttribute('aria-readonly')).toBe('true');
    const e = enter(input);
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(e.defaultPrevented).toBe(true); // no implicit form submit
  });

  it('ignores Enter while an IME is composing', () => {
    input.focus();
    const onNext = vi.fn();
    K().hold(input, onNext);
    enter(input, { isComposing: true });
    enter(input, { keyCode: 229 });
    expect(onNext).not.toHaveBeenCalled();
  });

  it('undoes edits to a held answer', () => {
    input.focus();
    K().hold(input, () => {});
    input.value = 'hitox';
    input.dispatchEvent(new Event('input'));
    expect(input.value).toBe('hito');
  });

  it('holds a box only once', () => {
    input.focus();
    const onNext = vi.fn();
    K().hold(input, onNext);
    expect(K().hold(input, vi.fn())).toBe(false);
    enter(input);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('reports false for a box without focus', () => {
    next.focus();
    expect(K().hold(input, () => {})).toBe(false);
  });
});

describe('afterAnswer', () => {
  it('holds the focused box instead of focusing Next', () => {
    input.focus();
    const click = vi.spyOn(next, 'click');
    K().afterAnswer({ input, nextBtn: next });
    expect(document.activeElement).toBe(input);
    enter(input);
    expect(click).toHaveBeenCalledTimes(1);
  });

  it('focuses Next after a tapped choice (no box)', () => {
    K().afterAnswer({ input: null, nextBtn: next });
    expect(document.activeElement).toBe(next);
  });

  it('calls a given onNext rather than clicking Next', () => {
    input.focus();
    const onNext = vi.fn();
    const click = vi.spyOn(next, 'click');
    K().afterAnswer({ input, nextBtn: next, onNext });
    enter(input);
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(click).not.toHaveBeenCalled();
  });
});

describe('isTyping', () => {
  it('is true for text boxes and textareas only', () => {
    expect(K().isTyping(input)).toBe(true);
    expect(K().isTyping(document.createElement('textarea'))).toBe(true);
    const radio = document.createElement('input');
    radio.type = 'radio';
    expect(K().isTyping(radio)).toBe(false);
    expect(K().isTyping(next)).toBe(false);
    expect(K().isTyping(null)).toBe(false);
  });
});
