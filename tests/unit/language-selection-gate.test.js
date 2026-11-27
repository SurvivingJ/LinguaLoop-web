/** static/js/pages/language-selection.js: the onboarding gate (vocab-placement tech §8, TASK-1085). */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const code = readFileSync(join(process.cwd(), 'static/js/pages/language-selection.js'), 'utf8');

function mount({ onboarding }) {
  localStorage.clear();
  sessionStorage.clear();
  if (onboarding) sessionStorage.setItem('ld_onboarding', '1');
  document.body.innerHTML = `
    <button class="language-card" data-id="1"><i class="check-icon"></i></button>
    <button class="language-card" data-id="2"><i class="check-icon"></i></button>
    <button class="language-card" data-id="3"><i class="check-icon"></i></button>
    <section id="langGate" hidden>
      <h2 id="langGateTitle"></h2>
      <button data-studied="yes"></button>
      <button data-studied="few"></button>
      <button data-studied="no"></button>
      <p id="langGateHint" hidden></p>
    </section>
    <a id="placement-btn" hidden data-placement-url="/placement" href="/placement"></a>
    <button id="continue-btn" class="ld-btn" disabled data-session-url="/session"></button>
    <a id="browse-tests-link" href="/tests"></a>`;
  window.LinguaMetadata = { load: () => Promise.resolve(null) };
  window.LinguaI18n = undefined;
  eval(code);
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

const $ = (sel) => document.querySelector(sel);

describe('onboarding gate on the language page', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('stays hidden outside onboarding', () => {
    mount({ onboarding: false });
    $('.language-card[data-id="3"]').click();
    expect($('#langGate').hidden).toBe(true);
    expect($('#placement-btn').hidden).toBe(true);
  });

  it('asks once a language is chosen and names it', () => {
    mount({ onboarding: true });
    expect($('#langGate').hidden).toBe(true);
    $('.language-card[data-id="3"]').click();
    expect($('#langGate').hidden).toBe(false);
    expect($('#langGateTitle').textContent).toBe('Have you studied ja before?');
    expect($('#placement-btn').hidden).toBe(true);
    expect($('#continue-btn').disabled).toBe(false);
  });

  it('"Yes" offers the placement for the chosen language and keeps the session as the skip', () => {
    mount({ onboarding: true });
    $('.language-card[data-id="1"]').click();
    $('[data-studied="yes"]').click();
    expect($('#placement-btn').hidden).toBe(false);
    expect($('#placement-btn').getAttribute('href')).toBe('/placement?lang=1');
    expect($('#langGateHint').hidden).toBe(false);
    expect($('#langGateHint').textContent).toContain('About 7 minutes');
    expect($('#continue-btn').classList.contains('ld-btn--ghost')).toBe(true);
    expect($('#browse-tests-link').hidden).toBe(true);
    $('.language-card[data-id="2"]').click();
    expect($('#placement-btn').getAttribute('href')).toBe('/placement?lang=2');
    expect($('#langGateHint').textContent).toContain('About 5 minutes');
  });

  it('"Only a few words" and "No" offer nothing', () => {
    mount({ onboarding: true });
    $('.language-card[data-id="3"]').click();
    $('[data-studied="yes"]').click();
    for (const answer of ['few', 'no']) {
      $(`[data-studied="${answer}"]`).click();
      expect($('#placement-btn').hidden).toBe(true);
      expect($('#langGateHint').hidden).toBe(true);
      expect($('#continue-btn').classList.contains('ld-btn--ghost')).toBe(false);
      expect($('#browse-tests-link').hidden).toBe(false);
    }
  });

  it('stores no answer; taking the placement saves only the language and ends onboarding', () => {
    mount({ onboarding: true });
    $('.language-card[data-id="3"]').click();
    $('[data-studied="yes"]').click();
    $('#placement-btn').addEventListener('click', (e) => e.preventDefault());
    $('#placement-btn').click();
    expect(sessionStorage.getItem('ld_onboarding')).toBeNull();
    expect(Object.keys(localStorage)).toEqual(['selectedLanguageId']);
    expect(localStorage.getItem('selectedLanguageId')).toBe('3');
    expect(sessionStorage.length).toBe(0);
  });
});
