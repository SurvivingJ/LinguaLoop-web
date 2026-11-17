---
title: LinguaDojo Logo Studies — Round One
type: overview
status: in-progress
last_updated: 2026-11-17
open_questions:
  - "Which direction (or combination of mark + palette) goes forward to round two? OPEN"
  - "Does the chosen palette replace the 'Dojo' theme tokens shipped with the mobile redesign (ADR-048)? OPEN"
---

# LinguaDojo Logo Studies — Round One

## Purpose
First exploration of a unified mark and palette for the LinguaDojo brand. The live app has a text-only wordmark, a 🎓 emoji on the login page and a teal/orange palette, so it has no single identity yet.

## Brief
- Positioning from [[decisions/ADR-004-brand-name]]: rigour over comfort, for skeptical self-taught professionals, explicitly not a gamified app (no mascots, no streak shaming, no neon green).
- Owner answers (2026-11-17): **abstract marks only** (no ensō, hanko or other Japanese imagery, because learners study zh/ja/es/en); concepts **LD monogram**, **correction mark**, **loop**; a mix of typographic voices; palettes **cobalt/bone/sand**, **cream/vermillion**, **cream/emerald**, plus other pairings taken from nature.

## The ten studies
Specimen page: `wiki/design/brand/logo-studies.html`. Standalone `mark.svg`, `app-icon.svg` and `lockup.svg` for each study are in `wiki/design/brand/logos/NN-slug/`.

| # | Name | Concept | Palette | Wordmark face |
|---|------|---------|---------|---------------|
| 01 | Single Stroke | LD monogram | Delft & Dune (cobalt, bone, sand) | Fraunces |
| 02 | The Circled Word | Correction mark | Persimmon (vermillion, rice paper, lamp black) | Gloock |
| 03 | Inward Spiral | Loop / LD monogram | Moss Garden (emerald, cream, deep moss) | Young Serif |
| 04 | Breakout Tick | Correction mark | Kingfisher (blue, rust, riverbank) | Schibsted Grotesk |
| 05 | Overprint | LD monogram | Lichen on Slate | Familjen Grotesk |
| 06 | Insertion Caret | Correction mark | Oxblood & Oat | Instrument Serif |
| 07 | Dial | Loop | Basalt & Ochre | Bricolage Grotesque (current display face) |
| 08 | Linked Pair | Loop | Heather & Peat | Newsreader |
| 09 | Negative Space | LD monogram | Fjord & Glacier | Syne |
| 10 | Loop to Tick | Loop + correction | Tidepool (kelp, anemone, shell) | Red Hat Display |

## Constraints & Edge Cases
Wordmarks are set in live Google Fonts, so they are typographic sketches. The chosen direction must be redrawn and outlined before production. The standalone `lockup.svg` files depend on the fonts being installed.

## Related Pages
- [[decisions/ADR-004-brand-name]]
- [[decisions/ADR-048-mobile-app-shell]] — the current "Dojo" theme tokens
- [[overview/project]] § Brand & Theming
