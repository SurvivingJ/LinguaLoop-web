// static/js/grammar/render.js
// Grammar drills: HTML for sentences (with pinyin as ruby), options, tiles and
// the topic guide. Strings in, strings out; the screens live in app.js.
// Pinyin is always in the markup as <rt>; .gd.is-py shows it (grammar.css).

import { T, escapeHtml } from '../session/dom.js';
import { clozeSegments, displayOption, rubyPairs } from './text.js';

export const t = (key, params, fallback) => T('grammar_drill.' + key, params, fallback);

export const nothingLabel = () => t('nothing', null, '(nothing)');

/** Characters with their pinyin above: [{ ch, py }] -> <ruby>…</ruby>. */
export function rubyHtml(pairs) {
  return pairs
    .map((p) =>
      p.py
        ? '<ruby>' + escapeHtml(p.ch) + '<rt>' + escapeHtml(p.py) + '</rt></ruby>'
        : escapeHtml(p.ch)
    )
    .join('');
}

/** A sentence, with ruby when the pinyin fits it. */
export function sentenceHtml(text, py) {
  const pairs = rubyPairs(text, py);
  return pairs ? rubyHtml(pairs) : escapeHtml(text);
}

/** True when pinyin can be shown for `text`. */
export const hasPinyin = (text, py) => !!rubyPairs(text, py);

/**
 * A cloze question. Before the answer the blanks are empty; with
 * `filled` they hold the right answer, highlighted.
 */
export function clozeHtml(item, filled) {
  return clozeSegments(item)
    .map((seg) => {
      const body = seg.pairs ? rubyHtml(seg.pairs) : escapeHtml(seg.blank ? seg.fill : seg.text);
      if (!seg.blank) return body;
      if (!filled) return '<span class="gd-blank" aria-label="blank"></span>';
      return seg.fill
        ? '<mark class="gd-fill">' + body + '</mark>'
        : '<mark class="gd-fill gd-fill--none">' + escapeHtml(nothingLabel()) + '</mark>';
    })
    .join('');
}

/** Option text as shown on a button. */
export const optionLabel = (opt) => displayOption(opt, nothingLabel());

function exampleHtml(ex) {
  if (!ex) return '';
  return (
    '<li class="gd-ex"><span class="gd-zh" lang="zh">' +
    sentenceHtml(ex.zh, ex.py) +
    '</span>' +
    (ex.en ? '<span class="gd-ex__en">' + escapeHtml(ex.en) + '</span>' : '') +
    '</li>'
  );
}

/** The topic guide: summary, rules, wrong/right contrasts, cheat sheet. */
export function guideHtml(guide) {
  if (!guide) {
    return '<p class="ld-muted">' + escapeHtml(t('guide_missing', null, 'No guide yet.')) + '</p>';
  }
  const subs = new Map((guide.subs || []).map((s) => [s.key, s.label]));
  const parts = [];
  if (guide.summary)
    parts.push('<p class="gd-guide__summary">' + escapeHtml(guide.summary) + '</p>');
  if ((guide.cheat || []).length) {
    parts.push(
      '<section class="ld-card gd-guide__cheat"><h3 class="ld-eyebrow">' +
        escapeHtml(t('guide_cheat', null, 'Cheat sheet')) +
        '</h3><ul>' +
        guide.cheat.map((c) => '<li lang="zh">' + escapeHtml(c) + '</li>').join('') +
        '</ul></section>'
    );
  }
  if ((guide.rules || []).length) {
    parts.push(
      '<h3 class="ld-h2 gd-guide__h">' + escapeHtml(t('guide_rules', null, 'Rules')) + '</h3>'
    );
    guide.rules.forEach((r) => {
      parts.push(
        '<section class="ld-card gd-rule">' +
          (subs.get(r.sub)
            ? '<span class="ld-tag" lang="zh">' + escapeHtml(subs.get(r.sub)) + '</span>'
            : '') +
          '<p class="gd-rule__text" lang="zh">' +
          escapeHtml(r.rule || '') +
          '</p>' +
          (r.pattern
            ? '<p class="gd-rule__pattern" lang="zh">' + escapeHtml(r.pattern) + '</p>'
            : '') +
          '<ul class="gd-exs">' +
          (r.examples || []).map(exampleHtml).join('') +
          '</ul>' +
          (r.note ? '<p class="gd-rule__note" lang="zh">' + escapeHtml(r.note) + '</p>' : '') +
          '</section>'
      );
    });
  }
  if ((guide.contrasts || []).length) {
    parts.push(
      '<h3 class="ld-h2 gd-guide__h">' +
        escapeHtml(t('guide_contrasts', null, 'Wrong and right')) +
        '</h3>'
    );
    guide.contrasts.forEach((c) => {
      const right = c.right || {};
      parts.push(
        '<section class="ld-card gd-contrast">' +
          '<p class="gd-contrast__row gd-contrast__row--bad"><span class="gd-mark" aria-hidden="true">✗</span>' +
          '<span class="visually-hidden">' +
          escapeHtml(t('wrong', null, 'Wrong')) +
          ': </span><span class="gd-zh" lang="zh">' +
          escapeHtml(c.wrong || '') +
          '</span></p>' +
          '<p class="gd-contrast__row gd-contrast__row--ok"><span class="gd-mark" aria-hidden="true">✓</span>' +
          '<span class="visually-hidden">' +
          escapeHtml(t('correct', null, 'Correct')) +
          ': </span><span><span class="gd-zh" lang="zh">' +
          sentenceHtml(right.zh || '', right.py) +
          '</span>' +
          (right.en ? '<span class="gd-ex__en">' + escapeHtml(right.en) + '</span>' : '') +
          '</span></p>' +
          (c.why ? '<p class="gd-contrast__why" lang="zh">' + escapeHtml(c.why) + '</p>' : '') +
          '</section>'
      );
    });
  }
  return '<div class="gd-guide">' + parts.join('') + '</div>';
}
