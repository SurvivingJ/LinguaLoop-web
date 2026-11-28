# Fat-seed IT authoring (v1, from the ja v7 structure)

Block shapes and plan values (anchor sentence, correct answer, `given`) are
fixed by the Block reference below; never choose them yourself. These eight
sections are where Italian documents lose points.

## 1. Core sentences: whole word, given sense, natural
- `definition` = the given definition. Exactly 10 sentences of 3 to 22 words;
  mined ones first, byte-for-byte. No digits: write "tre anni", "alle otto".
- The target is a free-standing whole word in THIS sense. Not inside another
  word ("porta" is not in portare or portafoglio), not a homograph (porto
  'harbour' excludes "porto la valigia"; ancora 'still' excludes "l'ancora
  della nave"), not another sense (tempo 'weather' excludes "non ho tempo").
- `target_word` is ONE word, exactly as it stands: "andata" in "è andata",
  "alza" in "si alza", "alzarsi" with its clitic. Never use the target elided
  or truncated (quest'anno for questo, buon for buono, un po' for poco).
- Level: A1–A2 presente and passato prossimo only; B1 adds imperfetto, futuro,
  condizionale; congiuntivo and periodo ipotetico from B2. The past is the
  passato prossimo (ho visto), never passato remoto (vidi) below B2.
- Only ordinary collocations: fare una domanda (never chiedere una domanda),
  fare colazione (never mangiare colazione), prendere una decisione (never
  fare una decisione), avere fame (never essere fame), fare una foto (never
  prendere una foto). Standard Italian, one register, Lei for formal address.
- Accents are spelling: perché, è, città, più, può; never perchè or e'.
- Each sentence has a context cue (reason, result, contrast) so the target is
  the only word that fits its slot when blanked.
- Pronunciation: broad IPA with the stress mark, syllable dots and doubled
  long consonants: /teˈlɛ.fo.no/, /ˈpal.la/, /tʃitˈta/. Forms: 3–5 real forms
  of this lemma (buono, buona, buoni, buone).

## 2. level_1 (listening): what English ears miss
- Correct = the headword. Distractors are real words that differ in one sound:
  - single vs double consonant: pala/palla, sete/sette, nono/nonno,
    caro/carro, casa/cassa, pena/penna, note/notte, capello/cappello;
  - gl/l, gn/n, sc/c: figlio/filo, sogno/sono, scena/cena;
  - one vowel: pero/pera, posto/pasto.
- Never: a word spelled like the headword (ancora, subito differ only in
  stress; pesca, venti only in open/closed vowel), a form of the target
  (parlo/parla), a synonym, an invented word.
- Explanation states the sound: "double /ll/ in palla, single /l/ in pala".
- B uses different words. Decline `no_minimal_pairs` when fewer than three
  real neighbours exist (most long words).

## 3. level_3: the frame gives away gender, so distractors must match it
- Articles, fused prepositions and agreement around the blank reveal gender,
  number and first sound. Every distractor copies the answer's gender, number
  and kind of first sound (vowel / s + consonant, z, gn, ps / other
  consonant); a verb copies person, tense and auxiliary.
  - "Ho messo i libri nello ___ e sono uscito." → zaino. Good: specchio,
    stadio, zucchero. Never armadio (needs nell'), never borsa (needs nella,
    and it would fit the meaning).
  - "Ieri Maria è ___ a casa tardi." → tornata. Good: durata, piaciuta. Never
    lavorato (avere, no agreement); never arrivata (it fits too).
- The three distractors fail on meaning only. Start each explanation with its
  failure tag (semantic / collocational / aspectual / register / valency),
  then the reason: "semantic: uno specchio is a mirror; books do not go in
  it". At least two different tags.

## 4. level_6 wrong sentences: grammatical, wrong only in what THIS word means
A native speaker says "questa parola non si usa così", not "è sgrammaticato".
Build each of the three with one move:
- **Move A, other sense or homograph:** teaching piano 'floor of a building',
  use "Parla piano, il bambino dorme."
- **Move B, false friend or near-synonym swap:** write a natural sentence for
  the word learners confuse with the target, then put the target in:
  - libreria ← biblioteca: "Ho preso in prestito un romanzo in libreria."
  - fattoria ← fabbrica: "Lavora in una fattoria che produce automobili."
  - argomento ← litigio: "Ho avuto un argomento con mio fratello e non ci
    parliamo più."
  - sapere ← conoscere: "So Roma molto bene perché ci ho vissuto."
- Never: a gender, agreement, auxiliary or preposition slip ("la problema",
  "ho andato", "dipende di": those are level_7); a sentence that is only odd
  or false but uses the word correctly ("Ho mangiato la libreria"); an error
  on another word; two problems at once.
- Explanation names the confusion: "A place that lends books is a biblioteca;
  a libreria sells them." Three different partners; B uses none of A's.

## 5. level_7: one span, on the target, an error English speakers make
- A new sentence, not a core sentence. The two sentences differ in exactly ONE
  span: the target's auxiliary, irregular form, gender, preposition or
  collocate.
  - "Ieri ho andato al mare." → "Ieri sono andato al mare."
  - "Ha prenduto il treno delle otto." → "Ha preso il treno delle otto."
  - "La problema principale è il traffico." → "Il problema principale…"
  - "Tutto dipende del tempo." → "Tutto dipende dal tempo."
  - "Posso chiedere una domanda?" → "Posso fare una domanda?" (target domanda)
- Never accent-only or spelling-only errors (perchè, citta). For a gender
  error choose a sentence where gender shows once: "la problema difficile è
  risolta" would need three changes.
- error_description names the wrong form, the right form and why: "andare
  takes essere in the passato prossimo".

## 6. synonym_antonym_match: decline unless a dictionary lists the pair
- Return `{"declined": "no_relation"}` unless a dizionario dei sinonimi e
  contrari lists the pair for THIS sense. Valid: grande↔piccolo,
  iniziare↔cominciare, salire↔scendere, accettare↔rifiutare. Not pairs:
  tavolo↔sedia, caffè↔tè, lunedì↔venerdì. A forced key is the worst defect.
- Distractors: same part of speech, in no relation to ANY sense of the word,
  never a form of the target (not felicemente for felice).

## 7. level_4 and explanations everywhere
- Italian drops the subject, so a bare verb slot fits every person: "Ogni
  giorno ___ a scuola" accepts vado, va, andiamo. Name the subject and a time
  expression: "Ieri le ragazze sono ___ presto." → partite; not partita,
  partito, partire.
- Nouns: "In piazza ci sono molti ___." → uomini; not uomo, uomi, uomine.
  Adjectives: the four agreement forms. Decline `no_inflection` for
  invariable words (adverbs, blu, rosa, bar, film).
- Every explanation is specific and true, in English, quoting the Italian: what
  the option means or which form it is, and why that clashes here. Never
  contradict the definition.
- A and B: B shares no distractor word, wrong sentence or error type with A.

## 8. preposition_selection: one preposition, one shape, one answer
- `sentence` is a core sentence with one preposition replaced by ___; that
  preposition is selected by the target or its frame (pensare a, in Italia
  but a Roma, da tre anni, andare dal medico).
- All four options have one shape: all simple, or all fused with the same
  article form.
  - "Penso spesso ___ mia nonna." → a; di, su, per. "di: pensare di takes an
    infinitive (penso di partire); a person you think about takes a".
  - "Domani vado ___ medico." → dal; al, nel, sul. With elision: all', dell',
    nell', sull'. Never mix a with nella.
- Never a blank with two acceptable answers: "un libro ___ storia" (di, su),
  "parlo ___ Marco" (di, con, a); never both tra and fra.
- Decline `{"declined": "no_preposition"}` when no core sentence qualifies.

Not written until their dictionaries exist: level_5 / level_8 (distractors are
the collocations row's wrong_collocates, never invented) and word_family
(real members of one family, the sentence fixes the part of speech: "Dobbiamo
prendere una ___ entro domani." → decisione; not decidere, deciso,
decisamente).
