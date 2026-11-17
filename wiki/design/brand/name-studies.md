---
title: Brand Name Studies — Round Two
type: overview
status: in-progress
last_updated: 2026-11-17
open_questions:
  - "Keep LinguaDojo (with a Latin motto) or rename? OPEN"
  - "ADR-004's alternative-name list is stale: Verbarium, Caesura, Fermata and Hapax are now registered on .app as well. Update or supersede ADR-004 once a name is chosen. OPEN"
  - "No trademark search has been run on any candidate. OPEN"
---

# Brand Name Studies — Round Two

## Purpose
Follows [[design/brand/logo-studies]]. The owner asked for alternative names, first Latin and then non-Latin, then for logos, colour schemes and app mockups for the recommended names.

## Name research (2026-11-17)
Registry lookups (RDAP: Verisign for .com, Google Registry for .app, Identity Digital for .io) and web searches for existing brands with the same name. Main finding: **every real single word checked, Latin or not, is registered on .com.** Ownable names are coinages or two-word phrases.

| Name | Meaning | .com | .app / .io | Same name already in use? |
|---|---|---|---|---|
| Linguatim | "Language by language" (cf. *verbatim*, *gradatim*) | registered 2026-03 | free / free | none found |
| Labor Limae | Horace, Ars Poetica: "the work of the file" (careful revision) | parked on Sedo | free / free | none found |
| LinguaDojo + motto *Usus magister optimus* | current name; "practice is the best teacher" | owned | free / free | — |
| Lingwright | a maker of language (cf. *playwright*) | **free** | free / free | none (nearest: Lingright, Lightwright) |
| Étude | a study piece that drills one technique | taken | taken (etudelab.io, lingetude.com free) | no language app |

Ruled out, with reasons: Verbifex (sounds like Verifex), Assidua (Asidua, Assidus), Linguafex (Linguifex), Stet (four writing tools), Wordhoard (an existing vocabulary app), Askesis (a coaching platform and a habit tracker), Kwoon (in US English it sounds close to a racial slur). Usus, Palaestra, Pensum, Tirocinium and Linguarium have their .com taken or listed for sale on Afternic.

## Studies
Specimen page: `wiki/design/brand/name-studies.html`, built by `gen_names.py`. Each name gets two marks and two palettes. Mockup A shows the Today screen in light mode; mockup B shows exercise feedback after a wrong answer in dark mode. SVGs are in `wiki/design/brand/names/<slug>/`.

| Name | Mark A · palette | Mark B · palette |
|---|---|---|
| Linguatim | Courses · Lapis & Limestone | Ligature (lt) · Juniper & Frost |
| Labor Limae | Filed Smooth (handwritten loops into a line) · Iron & Linen | Two Ls · Walnut & Brass |
| LinguaDojo | Doorway (D as arch) · Delft & Dune | Coin (motto around the monogram) · Persimmon |
| Lingwright | Try Square · Oak & Graphite | Dovetail · Spruce & Copper |
| Étude | The Accent (É) · Fig & Pistachio | Repeat Sign · Lake & Reed |

## Constraints & Edge Cases
Wordmarks are live Google Fonts sketches. Pronunciation in the learners' languages is untested; for example, Lingwright in katakana is リングライト, which already means "ring light".

## Related Pages
- [[design/brand/logo-studies]]
- [[decisions/ADR-004-brand-name]]
- [[pages/app-shell]] — the Today / Practice / Tests / Me structure used in the mockups
