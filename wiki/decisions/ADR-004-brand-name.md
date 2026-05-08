---
title: "ADR-004: Brand name — LinguaDojo"
status: accepted
date: 2026-05-07
---

# ADR-004: Brand name — LinguaDojo

## Context

The wiki documentation has called the project `LinguaLoop` since inception, while the actual production codebase has used `LinguaDojo` as the public-facing brand text throughout — page titles, logo wordmark, the `window.LINGUADOJO` global, four locales of i18n strings (en/es/ja/zh), production subdomain routing (`audio.linguadojo.com`, `library.linguadojo.com`, `math.linguadojo.com`, `feast.linguadojo.com`), and the Cloudflare R2 audio bucket name. The `Project Knowledge` corpus explicitly notes: *"Product Name: LinguaDojo (formerly LinguaLoop)"* and the glossary records: *"The project uses both names. LinguaLoop is the project name; LinguaDojo appears in code and public-facing URLs."*

This ADR formally adopts **LinguaDojo** as the canonical brand name, reconciling the wiki documentation with what the codebase already does, and locking the casing.

A brand-architect interrogation in the same session also produced a research pass over ~20 etymologically-rich alternative candidates, surfacing 7 with credible domain availability (Stoa, Caesura, Verbarium, Fermata, Hapax, Refrain, Phrasis). None were adopted. The exploration is preserved below so the work isn't lost; the chosen path retains the existing brand identity rather than replacing it.

The brief that informed both the decision and the rejected candidates:

- **Audience:** the autodidact professional (25–45, knowledge worker, skeptical of gimmicks, rewards depth).
- **Moral core:** rigour over comfort. Honest difficulty. Dojo, not playground.
- **Anti-positioning:** explicitly NOT Duolingo / gamified consumer apps. No mascots, streak shaming, neon greens, cartoon characters.

The `LinguaDojo` name aligns naturally with the brief — the dojo metaphor is the rigour-over-comfort principle made literal in the wordmark.

## Decision

The brand text is **LinguaDojo** (camel-case, capital `L` and capital `D`, no space).

- This is the form already in production code (templates, i18n, URLs, R2 bucket).
- The `Lingua-` stem and the `-Dojo` suffix are both retained from existing usage; nothing is changed.
- `LinguaLoop` becomes a historical project name, used in the wiki and `CLAUDE.md` for continuity but not on any user-facing surface.
- `Linguadojo` (lowercase `d`) is **not** an accepted form. References in any new asset, doc, or copy must use `LinguaDojo`.

This decision is brand-text only. The internal repo directory is named `WebApp` and `LinguaLoop` references in older wiki pages and `CLAUDE.md` are not retroactively renamed; that is a separate cleanup scope.

## Consequences

- **Easier:** No code migration required — the codebase, i18n, and infrastructure already use `LinguaDojo`. Wiki pages still saying "LinguaLoop" can be updated incrementally; nothing breaks if they aren't.
- **Easier:** Brand positioning is self-explanatory. "Dojo" reads in one syllable as serious, disciplined, explicitly opposed to the gamified-app aesthetic — the anti-positioning is built into the name.
- **Easier:** Visual brand work (palette, type) inherits the dojo metaphor cleanly — parchment, ink, the single red mark of the master's correction.
- **Harder:** "Dojo" is a borrowed Japanese word in English usage; for non-English markets it may read as either exotic or generic depending on local familiarity.
- **Constrained:** The brand commits to the dojo metaphor publicly. Future product directions that drift from the rigour-over-comfort axis (e.g., a casual social-language mode) would create brand dissonance.
- **Note:** `linguadojo.com` is already in use as the production root domain (per `Portal/hub/app.py` and various subdomains in the codebase). Domain ownership is therefore already established for the primary TLD; the alternative-name domain checks below are archival.

## Alternatives Considered

A research pass screened seven etymologically-rich candidates with credible domain-availability signals. None were adopted, but the analysis is preserved here so future brand reviews can revisit the work without redoing it.

**Caveat on domain checks:** The screening used web search and HTTP fetches to detect *active brand collisions*; it could not perform Whois lookups. "Connection refused" / "no search results" is a strong but not perfect signal of registrability. Any future revisit must confirm via a registrar before purchase.

### 1. Stoa — *Tier A, highest availability confidence*
- **Etymology:** Greek στοά — the colonnaded walkway in ancient Athens where Zeno taught and the Stoic school took its name. A place where serious thought walks slowly.
- **Resonance:** Philosophical seriousness, dignified instruction, a covered space for sustained study. The dojo with a Greek roof.
- **Domain status:** stoa.com / stoa.io / stoa.app all returned ECONNREFUSED with no active brand surfacing in search. Strongest availability signal of the set.
- **Risk:** Single-syllable Greek roots are coveted; price likely premium even if registerable.

### 2. Caesura — *Tier A*
- **Etymology:** Latin *caesūra* (a cutting) — the deliberate metrical pause inside a line of verse where meaning gathers.
- **Resonance:** Argues that comprehension lives in the pause, not the streak. Beautiful on the page.
- **Domain status:** caesura.com 301-redirects to accidentalist.com (owned but parked-by-redirect). caesura.app returned ECONNREFUSED — caesura.app would be the recommended primary. Only academic/literary references in search; no commercial brand operating under the name.
- **Risk:** Four syllables, slightly harder to spell — needs a clean wordmark.

### 3. Verbarium — *Tier A, coined*
- **Etymology:** Constructed Latin compound — *verbum* (word) + *-arium* (a place where, as in *herbarium*, *aquarium*). "A place where words are kept and studied."
- **Resonance:** Self-explaining for a literate audience. Implies a curated, taxonomic, library-grade approach to vocabulary — directly antithetical to gamification.
- **Domain status:** Zero search results across .com/.io/.app — coinages are typically free at registrar. High confidence of full availability.
- **Risk:** Slightly long; doubles as a strength (memorable) and a weakness (typing).

### 4. Fermata — *Tier A*
- **Etymology:** Italian (musical) — the symbol indicating a note held longer than its written value. The instruction to dwell.
- **Resonance:** Adjacent metaphor (music, not language) but the connection is exact: *the held repetition*, *the deliberate dwell on the difficult passage*. Pairs cleanly with the existing "Loop" concept.
- **Domain status:** Zero commercial search results across all three TLDs. High confidence.
- **Risk:** May read as a music-tech brand; offset with strong language-focused copy.

### 5. Hapax — *Tier B*
- **Etymology:** From the Greek philological term *hapax legomenon* — "a thing said only once," used in classical scholarship to describe a word that appears exactly once in an entire surviving corpus. The rarest object in linguistics.
- **Resonance:** Most intellectually flattering name on the list. Whoever knows what it means is precisely the autodidact target; whoever doesn't will look it up. Signals filter, not friction.
- **Domain status:** hapax.com 301-redirects to hapax.org (owned but redirected). hapax.app currently displays only the placeholder text "Hapax" — likely parked or in early development. hapax.io status uncertain — would have been the primary acquisition target.
- **Risk:** Highest of Tier A/B for current ownership; only viable if .io can be secured or the parked .app/.com can be negotiated.

### 6. Refrain — *Tier B*
- **Etymology:** Latin *refringere* via Old French — the recurring poetic line that returns each stanza, the pattern that names the song. A loop with literary pedigree. Doubly apt: also the verb of *self-restraint*.
- **Resonance:** Plain English, immediately understandable, but with a poetic spine.
- **Domain status:** No commercial collisions found. refrain.app returned 403 (blocked but registered — status uncertain). refrain.com / .io status unclear from passive checks.
- **Risk:** Common English word — registrar prices likely premium.

### 7. Phrasis — *Tier C, conditional*
- **Etymology:** Greek φράσις — diction, manner of speech, the way meaning is shaped. The root of *phrase* and *paraphrase*.
- **Resonance:** Compact, quietly Greek, language-native.
- **Domain status:** phrasis.com is listed for sale on DomainMarket as a premium domain — registerable only at premium price (typically four to five figures). phrasis.app returned 503; .io status unclear.
- **Risk:** Cost. Listed only because the etymology is so on-target; deprioritized if budget is constrained.

## Eliminated Candidates (appendix)

The following were screened during the same research pass and eliminated for active brand collisions. Recorded so a future review does not need to redo the search.

| Name | Cause |
|---|---|
| Volute | volute.io (Volta Communications), volute.app (Volute Games), volute.education (active learning platform) |
| Tessera | Tessera Therapeutics, Tessera Data, Tessera (recruitment), Tessera Web3 — heavy crowding |
| Marginalia | marginalia.nu (active search engine), marginaliaapp.com, Steam game |
| Whetstone | Whetstone Apps, Whetstone Studio, Whetstone Education, Whetstone Magazine |
| Acumen | acumen.io (acquired by Via), acumen.app (productivity tool) |
| Aporia | aporia.com active AI control platform (acquired by Coralogix) |
| Sodality | sodality.app — active white-label app platform |
| Recurse | recurse.com — Recurse Center (well-known programmer retreat) |
| Etymon | etymon.io word-ideation tool, Etymon Technologies |
| Volta | volta.io (Volta Communications), Volta CLI, Volta Labs, multiple others |
| Capstan | Capstan Incorporated (industrial) |
| Gnomon | gnomon.com active, gnomon.app (TurisGo), Gnomon School (famous CG education) |
| Strophe | strophe.im — well-known XMPP library, dev-audience collision |
| Trivium | trivium.com (HR/payroll), trivium.app (trivia game) |
| Ligature | ligature.vc (VC fund), ligaturetype.com — typography-adjacent collision |
| Ostinato | ostinato.org (network packet generator), Ostinato Institute (music education) |
| Logogram | logogram.io — active AI logo generator |
| Lectio | lectia.app is an active language-learning app from University of Maryland NFLC — phonetic + category collision |
| Ostracon | ostracon.app — active social platform "Where every voice finds its space" |
