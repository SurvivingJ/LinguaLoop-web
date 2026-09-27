Folded into taxonomy.md on 2026-09-28; kept as the review record.

# Taxonomy addendum — `en.phrasal_verb` and `ja.particle_other`

Date: 2026-09-27 (revised the same day after independent review — see §5)
Extends: `taxonomy.md` (2026-09-26). That file is unchanged. Everything in its §0 (scope, norm, classes,
subtlety levels, corruption rules C1–C12, verification checklist V1–V11, polarity, bucket sizing) applies to
the two types below without modification. This addendum adds only what an existing type entry carries, plus
the bucket changes, the DT v6 mapping, and the edits that other files will need.

Why these two: both exist in the live DT v5 taxonomy (`migrations/dt_taxonomy_v5_seed.sql`) and were carried
into the merged v6 draft (`data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json`) with `jev_bucket: null`,
because jev had no equivalent.

Source definitions being ported:
- v5 `phrasal_verb` (en; `fidelity` / `minor`, `treatable: false`, `cloze_suitable: true`): "phrasal verb —
  wrong particle or wrong/avoided phrasal-verb form".
- v5 `particle_other` (ja; `accuracy` / `minor`, treatable, cloze-suitable): 「その他の助詞——並列助詞（や・と・か）、
  取り立て助詞（も・だけ・しか）、終助詞など、格助詞以外の助詞の誤り」.

Both jev types below are **narrower** than their v5 sources (see §4).

---

## 1. English — `en.phrasal_verb`

### 1.1 Type-table row

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `en.phrasal_verb` | Phrasal-verb particles | In an **idiomatic** phrasal verb (verb + particle whose combined meaning is not the verb's own meaning), or in a prepositional verb on the closed list in §1.3, the particle is wrong, missing, or placed wrongly relative to the object. | G | low | Native-level generators produce phrasal verbs fluently. Their phrasal-verb risk is *sense* (`en.target_in_idiom`), not form. The remaining slips are near-miss particles on the same verb, and pronoun objects placed after the particle. | B1 |

**The deciding criterion is idiomaticity.** A combination is in scope only if the verb does not keep its own
meaning (*look up* a word = consult; *turn out* = prove to be; *put up with* = tolerate; *run out of* =
exhaust). Movement (whether the particle can follow the object) is a **secondary diagnostic only**. It tells
you whether an in-scope verb is separable, which decides placement errors. It never brings a verb into scope.

Literal verb + directional particle (*give the pen back*, *carry the box in*, *pick up the cup* = lift) is
**out of scope for both `en.phrasal_verb` and `en.preposition`**. Do not author positives on it. Correct
literal alternations may be used only as `variant_ok`.

Positives come from exactly one of these edits:
1. **Particle swap:** replace the particle with another real particle so that verb + new particle has no valid
   parse in that frame (*put up with* → *put up to*).
2. **Particle deletion:** remove the particle so that the bare verb no longer carries the meaning (*ran out of*
   → *ran of*).
3. **Particle placement:** put a pronoun object after the particle of an idiomatic separable verb (*looked up
   it*), or split an inseparable listed verb around its object (*looks her brother after*). No more than **3 of
   the ≈10** `en.phrasal_verb` positives may be placement items (see §3.1, en.B3 interaction).

v5's "avoided phrasal-verb form" (writing *postpone* where *put off* was expected) is a translation-fidelity
idea. A single generated sentence has no source text to avoid, so under jev this is **never** an error.

### 1.2 Type details

#### `en.phrasal_verb`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | We ran out of milk this morning. | We ran of milk this morning. | Particle *out* deleted from *run out of*. *Run of* is not a verb pattern, so the sentence fails on first read. |
| moderate | I didn't know the word, so I looked it up. | I didn't know the word, so I looked up it. | *Look up* (= consult a reference) is idiomatic and separable. A pronoun object must sit between verb and particle; only a full noun phrase may follow the particle. |
| subtle | We have to put up with the noise from next door. | We have to put up to the noise from next door. | Same-verb near-miss particle: *put up with* = tolerate. *Put up to* exists only as *put someone up to something* (= incite), which needs a person object, so the frame has no valid parse. The surface stays fluent. V9: check COCA for "put up to the". |

Not an error:
- A separable idiomatic phrasal verb with a **noun** object in either position (*look up the word* / *look the
  word up*; *turn down the offer* / *turn the offer down*).
- US/UK particle variants of equal standing: *fill in* / *fill out* a form; *put back* (UK) = postpone; *check
  in* / *check into* a hotel; *meet* / *meet up* / *meet up with*; *wake* / *wake up*.
- An optional completive or intensifying particle where the bare verb is also standard (*eat* / *eat up*,
  *finish* / *finish up*, *clean* / *clean up*, *hurry* / *hurry up*, *find* / *find out* with a that-clause).
- A single-word verb chosen instead of a phrasal verb, or the reverse (*postpone* / *put off*, *tolerate* /
  *put up with*). That is `en.register` at most, never this type.
- Stacked particles used correctly (*put up with*, *get on with*, *catch up on*, *look forward to*).
- Literal verb + directional particle, in either order (*give back the pen* / *give the pen back*, *carry the box
  in*). This is out of scope (§1.1). Use it only as `variant_ok`.
- *off of* (*get off of the bus*) **(contested — exclude)**.
- A long noun object placed between verb and particle (*turned the offer she had waited years for down*).
  This is awkward end-weight, not ungrammatical **(contested — exclude)**.
- *give up to* + noun as "yield to" (*gave up to pressure*): *give (oneself) up to* = surrender to has a valid
  parse **(contested — exclude)**.
- Regional particle uses outside US/UK standard (*cope up with*, *fill up a form*, *pick someone from the
  station*). These are dialect forms: **never use them as positives** (`taxonomy.md` §3.4) and never as
  `variant_ok`.

### 1.3 Boundaries with the nearest types

**Closed list of idiomatic prepositional verbs (inseparable) that count as `en.phrasal_verb`:** *look after*,
*look into*, *come across*, *take after*, *get over*, *run into* (= meet by chance), *go over* (= review),
*put up with*, *run out of*, *get along with*, *give in to*, *come up with*, *catch up on*, *look forward to*.
Every other verb + preposition pairing (*deal with*, *count on*, *care for*, *believe in*, *look at*, *consist
of*, *depend on*, *listen to*, …) is `en.preposition`. The list can be extended only by editing this addendum.

Separable or intransitive idiomatic verbs need no list: idiomaticity decides. Examples authors may use: *give
in*, *run out*, *look up* (a word), *turn out*, *turn down* (= reject), *put off* (= postpone), *find out*,
*call off*, *set off*, *break down*, *bring up* (a topic), *figure out*, *pick up* (= learn, or collect a person).

| Neighbour | Rule | Example routed there |
|---|---|---|
| `en.preposition` | In scope for `en.phrasal_verb` if **both** (a) the combination is idiomatic **and** (b) it is either a separable or intransitive particle verb, or on the closed list above. Otherwise, a preposition selected by a verb, adjective or noun is `en.preposition`. An **extra** preposition after a transitive verb (*discuss about*, *enter into the room*) is `en.preposition`. | *It depends of the weather* → preposition. |
| `en.collocation` | `en.phrasal_verb` edits touch **only the particle**: its choice, presence or position. An edit that changes the **lexical verb** and keeps the particle (*make up a story* → *do up a story*) is `en.collocation`. | *I did a mistake* → collocation. |
| `en.complementation` | The form of what follows the phrasal verb (*look forward to seeing*; *gave up smoking* vs *gave up to smoke*) is `en.complementation`. | *I look forward to see you* → complementation. |
| `en.word_order` | Pronoun placement relative to the particle of an in-scope phrasal verb belongs to `en.phrasal_verb`, not `en.word_order`. `taxonomy.md`'s en.word_order definition does not yet say so (knock-on K1). | *Where she does live?* → word_order. |
| `en.semantic_anomaly` | Case 1: the swapped particle forms a **valid** phrasal verb, and the sentence just describes a different event that is possible (*look after my cat* → *look for my cat*). That is not an error: under V5 a lost-cat context rescues it. Case 2: the new phrasal verb makes the event impossible. Then the edit hits two types at once (C7), so choose a different edit. A positive must leave verb + particle with **no** valid parse in that frame. | — |
| `en.target_in_idiom` / `en.target_absent` | If the **target** is the verb of an idiomatic phrasal verb, the source already fails the target check (C1). If the target lemma **is** a phrasal verb (locked sense of *give up* = quit), a particle edit on it removes the target, so it is `en.target_absent`. Positives must corrupt a **non-target** phrasal verb. | *He gave up smoking* with target *give* = hand over → target_in_idiom. |

### 1.4 Corruption and verification additions

- Use only the three edit kinds in §1.1, on in-scope verbs only. No verb substitution (that is
  `en.collocation`). No literal verb + particle.
- No particle swap whose result is a valid phrasal verb with a plausible meaning (§1.3, semantic_anomaly row).
- Source sentences must contain an in-scope phrasal verb that is **not** the target. This is likely to be the
  binding constraint on sourcing, because P1 sentences are short and many contain no phrasal verb.
- `variant_ok` hard negatives: a particle placed after a **noun** object, *fill in* ↔ *fill out*, optional *up*,
  *put off* ↔ *postpone*, and literal alternations (*give the pen back* / *give back the pen*).
- Run the V9 corpus check (COCA / BNC) on **every** `en.phrasal_verb` item, not only subtle ones. Particle swaps
  are where a "broken" form most often turns out to be attested under a different parse (*put up to 10
  people*). Search verb + particle + the next word, not the pair alone.

---

## 2. Japanese — `ja.particle_other`

### 2.1 Type-table row

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `ja.particle_other` | Focus, limit & listing particles (取り立て・限度・並列の助詞) | A focus, limit, comparison or listing particle that breaks its own rule. Authored positives cover three patterns: (P1) a negative-polarity particle — しか, comparative ほど (A は B ほど ～), も in 誰も/何も/どこも — with an affirmative predicate; (P2) a time-point noun + まで where a one-time action that must be finished by that time needs までに; (P3) non-exhaustive や/とか in a list closed by a count or totalising noun. | G | low–medium | LLM Japanese uses も/だけ fluently. The remaining slips come from English: "by Friday" and "until Friday" both come out as まで, and "and" comes out as や in a closed list. Negative-polarity breaks are rare. | B9 (new) |

**Routing scope vs authored scope.** The particles routed to this type are も (including 誰も・何も・どこも),
だけ, しか, ばかり, さえ, こそ, でも (focus), まで, までに, より, ほど, や, とか, か (listing "or"), と **only in
noun listing** (AとB), and the stacking of は/も after が/を. **Authored positives use only P1–P3.** The other
particles are in scope for **routing only**: a real error on them found in live output is labelled
`ja.particle_other`, but none are authored, because no crisp rule is defined for them. Stacking (本をは, 私がも)
is routing-only for the same reason, and because C6 fails: an LLM essentially never writes it.

まで / までに / ほど are `ja.particle_other` whether they follow a noun or a predicate. However, **authored**
まで/までに positives use only time-point **nouns** + まで(に) (金曜日まで, 五時までに).

Explicitly **outside** this type:
- は and が in any function go to `ja.wa_ga` (structural rules), or are not an error (main-clause choice). The
  one exception is は/も stacked after a retained が/を, which is routed here.
- が, を, に, で, へ, から, and と as comitative / quotative / reciprocal partner → `ja.case_particle`.
- の between nouns, and い/な/の before a noun → `ja.modification`. Nominaliser の vs こと (見るのが好き /
  見ることが好き) is **not covered** by this taxonomy. Do not author it under any type.
- The clause-final connectives listed under `ja.clause_linkage` in `taxonomy.md` (から, ので, のに, けど, が,
  と conditional, ば, たら, ても, ために, ように) → `ja.clause_linkage`.
- Final particles (よ, ね, よね, か, わ, ぜ, ぞ): their choice is pragmatic, or `ja.register` for gendered or
  rough forms. They are never positives of this type.

より: school grammar counts より among the 格助詞. `ja.case_particle`'s closed list (が, を, に, で, へ, と,
から) leaves it out, so comparative より / ほど are routed here. This is a jev convention that keeps the two types
disjoint. DT v5 would file より under `particle_case` (see §4).

### 2.2 Type details

#### `ja.particle_other`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 冷蔵庫に卵が一つだけあります。 | 冷蔵庫に卵が一つしかあります。 | P1. だけ → しか. しか has negative polarity and requires a negative predicate (しかありません). With あります the sentence fails on first read. |
| moderate | 兄と姉の二人に手紙を書きました。 | 兄や姉の二人に手紙を書きました。 | P3. と → や, one slot. や marks a list that is not exhaustive ("A, B and so on"), which clashes with the exact total 二人. A counted, closed list needs と. The predicate is not reciprocal, so a comitative reading of と is not in play. V9: check BCCWJ for "や…の二人". |
| subtle | この本を金曜日までに返してください。 | この本を金曜日まで返してください。 | P2. までに → まで after a time noun. まで marks the end of an action or state that continues until then. A single act (返す) completed before a deadline needs までに. The singular, definite object (この本) blocks an iterative reading. This is a calque of English "by / until". Both are real particles, so the edit is a particle swap, not a dropped kana (C5). |

Not an error:
- だけ + affirmative and しか + negative for the same fact (一つだけある / 一つしかない).
- と and や for an open list, with or without など (りんごやみかんを買った / りんごとみかんを買った /
  りんごとみかんなどを買った). A positive requires や/とか with an **exact** count or an explicitly closed set.
- まで with an action or state that continues until the time (五時まで待つ, 金曜日まで休みです). までに with a
  one-time action. What is never authored as a positive: までに with a continuing action.
- Spatial or range まで, including with one-time verbs (駅まで行く, 駅まで歩く, 東京から大阪まで送る, AからBまで).
- まで meaning "even" (子どもまで知っている).
- Clause + まで / までに (彼が来るまで待つ, 帰るまでに終わらせる). This is correct use. The routing rule above
  applies only if such a clause contains an error.
- ほど in its affirmative uses: approximate quantity (一時間ほど待った, 三人ほど来た); ～ば～ほど
  (読めば読むほど面白い); clause + ほど of degree (涙が出るほど嬉しい); Xほど…はない (彼ほど親切な人はいない);
  set phrases (死ぬほど, 山ほど).
- より + affirmative and comparative ほど + negative (東京は大阪より大きい / 大阪は東京ほど大きくない).
- Case particle + は/も stacking where it is grammatical: に・で・へ・と・から + は/も (東京には, 学校でも,
  友達とも).
- も replacing は or が (already listed as not-an-error under `ja.wa_ga`).
- 誰もが, 何もかも, いつも, どれも with affirmative predicates. These are fixed forms, not negative-polarity も.
- Whether ね / よ / よね / none is used (C8: some context always exists where each one is right).
- Particle omission in casual speech.
- Colloquial listing とか, なんか, でも (お茶でも飲む？) in casual register.
- ～をも in written style **(contested — exclude)**.
- だけしか～ない, which is redundant but common **(contested — exclude)**.
- ばかり vs だけ where both read naturally **(contested — exclude)**: the nuance difference is real, but native
  speakers disagree on where it becomes wrong.

### 2.3 Boundaries with the nearest types

| Neighbour | Rule |
|---|---|
| `ja.case_particle` | Decide by the particle **in the source sentence** at the edit site. If it is one of が, を, に, で, へ, から, or comitative/quotative と, the item is `ja.case_particle`. If it is in §2.1's routing scope, the item is `ja.particle_other`. Do not author an edit that swaps a case particle for a focus particle (駅に → 駅も): it hits both types (C7). Author と → や positives only where a count or totalising noun closes the list, never with a symmetric or reciprocal predicate (太郎と花子が結婚した). |
| `ja.wa_ga` | An edit that inserts, removes or replaces は or が is never `ja.particle_other`, **except** は/も stacked after a retained が/を (本をは, 私がも). That exception is routed here and is never authored (§2.1). |
| `ja.clause_linkage` | The clause_linkage row covers only the connective list in `taxonomy.md` ja.clause_linkage (§2.1 above). まで / までに / ほど are `ja.particle_other` whether they follow a noun or a predicate. でも after a noun (子どもでも分かる) is here. ても after a verb (雨が降っても行く) is clause_linkage. |
| `ja.tam` | まだ + negative form is `ja.tam`. Negative polarity triggered by a **particle** (しか, comparative ほど, 誰も/何も) is `ja.particle_other`. Author P1 positives by editing the particle (だけ → しか), not the predicate, so that the inverse edit (V3) restores the source with a particle change. |
| `ja.contradiction` | や with an exact count is a clash in the particle's meaning, not a world-knowledge contradiction: the facts stated are consistent, and only the list marker is wrong. If a reviewer reads it as a contradiction, relabel it to `ja.particle_other` rather than reject it. |
| `ja.register` | Gendered or rough final particles in a polite sentence are `ja.register`. |
| `ja.modification` | の linking two nouns is `ja.modification` (病気な友達 → 病気の友達). |

### 2.4 Corruption and verification additions

- Edits are particle swaps, insertions or deletions only, restricted to P1–P3. Keep the predicate unchanged.
- Never corrupt to or from は, が, or a case particle (§2.3).
- No final-particle positives and no stacking positives.
- Keep the script mix and the declared register fixed (as in `taxonomy.md` §2.4).
- Run the V9 corpus check (BCCWJ) on every まで/までに and や item. These pairs are the most likely to turn out
  attested in edited text for a particular verb or list.
- V5 on まで items: try an iterative or notice-style reading ("returns accepted up to Friday"). If the object is
  plural or number-neutral, or the verb can be read as repeated or continuing (出す, 送る), make the object
  singular and definite, or reject.

---

## 3. Bucket assignment

### 3.1 en: add to `en.B1` (now 3 types)

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| en.B1 | Articles, prepositions & particles | article_determiner, preposition, phrasal_verb | "Are all articles (a, an, the), other determiners, prepositions and verb particles (as in *look it up*, *run out of*) correct and in the right place?" Test the wording with and without the parenthetical (§0.9). |

Why B1 and not B2 (verb forms & patterns, which also has 2 types):
- The particles (*up, out, in, off, on*) are the same word forms as prepositions, and this type's hardest
  boundary is `en.preposition` (§1.3). With the two types in different buckets, B1's "are the prepositions
  correct?" question would very likely answer "no" on phrasal-verb positives too. That answer would be scored
  as a cross-bucket false positive (§0.10). In the same bucket, the boundary costs nothing at bucket level.
- B2 covers the verb's inflection and complement type. No phrasal-verb edit touches either.

Overlap check: the three members are disjoint under the §1.3 rules. Idiomaticity plus the closed list
separates preposition from phrasal_verb, and articles are a separate word class. ≤3 types: yes.

Sizing: about 10 positives per type (§0.10), so article_determiner and preposition each drop from about 15 to
about 10. Rebalance any B1 authoring plan to match. The B1 hard-negative pool gains the phrasal-verb
`variant_ok` items.

**en.B3 interaction.** The en.B3 question ("words in the right order") also literally covers placement
positives (*looked up it*). Decision: (a) placement is capped at ≤3 of the ≈10 phrasal_verb positives
(§1.1); (b) placement positives are **excluded from en.B3's cross-bucket negative set**, and B3's answers on
them are reported separately as a diagnostic; (c) knock-on K1 amends the en.word_order definition.

### 3.2 ja: new bucket `ja.B9`

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| ja.B9 | 取り立て・並列の助詞 (Focus & listing particles) | particle_other | 「も・だけ・しか・まで／までに・より・ほど、並列の「や」「と」などの助詞は正しく使われていますか。（例：「しか」や比較の「ほど」、「誰も」「何も」を使った文の述語が否定形になっているか。期限を表すときに「までに」が使われているか。数が決まっている並べ方には「や」ではなく「と」が使われているか。）」 Every example is phrased so that yes = clean. Test with and without the parenthetical (§0.9). |

Why a new bucket and not an existing one:
- **ja.B1 is full.** It already holds three types (case_particle, wa_ga, counter). A fourth would break the ≤3
  rule and add load to the bucket where jev was weakest in §3.1.
- **ja.B3 has room (2 types) but the wrong theme.** B3 is about joining words and clauses. Listing や/と would
  fit, but polarity (しか/ほど/誰も) and まで/までに would not. Asking about particles in two different buckets
  would also invite exactly the cross-bucket confusion that the §0.10 design measures.
- **Rejected alternative: move `ja.counter` from B1 to B4** (collocation, kanji_choice, counter), which would
  make B1 a pure particle bucket (case_particle, wa_ga, particle_other). This is thematically clean. But it
  breaks the cross-language B1 comparison (zh `measure_word` is in zh.B1, and `taxonomy.md` §4 uses B1 as the
  function-word comparison), and it changes an assignment already recorded in `jev_grammar_to_merged.csv`.
  Revisit only if B9 performs poorly on its own.

**ja.B1 interaction.** As worded, B1's question ("Are all the particles … used correctly") has the true
answer "no" on a B9 positive: しかあります means the particles are *not* all correct, especially once the
parenthetical list is removed (§0.9). Decision: **exclude B9 positives from ja.B1's cross-bucket negative
set**, and report B1's answers on them separately as a diagnostic. An optional follow-up is knock-on K4.

Sizing: a 1-type bucket needs **30 positives** of `ja.particle_other` (about 10 per subtlety level), plus ≥15
originals and ≥15 `variant_ok` (§0.10). Suggested sub-mix: about 12 P1 (しか / comparative ほど / 誰も・何も),
10 P2 (time noun + まで/までに) and 8 P3 (や/とか in a counted list). `variant_ok` comes from the "Not an error"
list, especially spatial まで, affirmative ほど uses, open-list や and だけ/しか pairs. Source sentences that
contain these particles are rarer than sentences with case particles. If fewer than about 40 suitable confirmed
sources exist, record the shortfall rather than relaxing C1.

### 3.3 Cross-language map additions (extends `taxonomy.md` §4)

| Bucket id | Theme | zh | ja | en |
|---|---|---|---|---|
| B1 | Function words | (unchanged) | (unchanged) | Articles, prepositions & particles — article_determiner, preposition, **phrasal_verb** |
| B9 | Focus & listing particles | — | 取り立て・並列の助詞 — **particle_other** | — |

B9 has no zh or en counterpart and is not part of any cross-language comparison. The §4 comparability note for
B1 should add that en B1 now also covers verb particles (K2).

---

## 4. Mapping back to DT v6 (`merged_taxonomy.json`)

| merged id | Current merged entry | Proposed | jev_bucket |
|---|---|---|---|
| en `phrasal_verb` | class F, `fidelity`, `minor`, treatable false, cloze true, `jev_bucket: null` | **No change to the DT fields.** Keep `fidelity` / `minor` / treatable false / cloze true. DT's subtype is wider (it includes "avoided phrasal-verb form", which is a fidelity notion), and a narrower jev slice should not re-score it. If a dimension change is wanted, raise it as a separate DT decision, backed by the live `dt_error_instance` mix of wrong-particle rows versus avoided-form rows. | **Fill: `"B1"`**, mapping_kind `split`. jev covers only particle choice, omission and placement on idiomatic verbs. "Avoided form" stays DT-only. |
| ja `particle_other` | class G, `accuracy`, `minor`, treatable, cloze, `jev_bucket: null` | Keep class G, `accuracy`, `minor`. Negative-polarity errors are arguably more severe, but the v6 schema does not support severity per subclass. | **Fill: `"B9"`**, mapping_kind `split`. Divergences: (1) jev authors only P1–P3 and excludes final-particle choice, which v5's gloss includes; (2) v5 defines particle_other as 「格助詞以外の助詞」, so v5 files より under `particle_case`, whereas jev routes より here; (3) v5's `particle_case` gloss lists only を・に・で・へ, while jev `case_particle` also covers が・と・から; (4) nominaliser の is not covered by jev. |

---

## 5. Knock-on edits (not done here; this addendum is the only file changed)

- **K1** `taxonomy.md` en.word_order: exclude "particle position relative to the object of an in-scope phrasal
  verb", which moves to `en.phrasal_verb`.
- **K2** `taxonomy.md` §4: add to the B1 comparability note that en B1 now covers verb particles, and add the
  ja-only B9 row. Rebalance en.B1 sizing to about 10 positives per type.
- **K3** `taxonomy.md` §0.10 / authoring plans: B9 positives are excluded from ja.B1's cross-bucket negatives,
  and en.phrasal_verb placement positives are excluded from en.B3's. Both are reported separately as
  diagnostics.
- **K4** (optional) Reword ja.B1's question so it asks about case particles only (「格助詞（が・を・に・で・へ・と・から）と
  「は」、助数詞は…」). If adopted, B9 positives can go back into B1's cross-bucket negative set.
- **K5** `merged_taxonomy.json`: set `jev_bucket` to `"B1"` (en phrasal_verb) and `"B9"` (ja particle_other).
  Replace "jev has no standalone equivalent" in both definitions with a pointer to this addendum. Leave all
  other DT fields unchanged.
- **K6** `jev_grammar_to_merged.csv`: add `en,phrasal_verb,phrasal_verb,split,...` and
  `ja,particle_other,particle_other,split,...`, with the §4 divergences in the notes. `v5_to_merged.csv`: the
  notes on both rows are now stale.
- **K7** v5 historical-alias triage (pre-v5 undifferentiated ja `particle` rows → wa_ga / case_particle /
  particle_other): use the §2.3 boundary table, and note that v5 would put より under particle_case.

---

## 6. Review response

Reviewer: `taxonomy_addendum_2026-09-27_review.json` (8 pass / 15 fix / 1 reject). **All 16 fix/reject items
applied; none held.**

| Review item | Action |
|---|---|
| en subtle *give up to pressure* | Replaced with *put up with → put up to the noise*. *give up to* moved to "Not an error" as contested. |
| Literal-particle contradiction (*give the pen back*) | Idiomaticity is now the deciding test and movement is only a diagnostic. Literal verb + particle is out of scope for both types (`variant_ok` only). The moderate example changed from literal *picked it up* to idiomatic *looked it up*. |
| Prepositional-verb judgement call | Added the closed list in §1.3. Every other verb + preposition → `en.preposition`. |
| en.B3 cross-bucket (placement) | Placement capped at ≤3/10; excluded from B3 cross-bucket negatives; K1 added. |
| en.B1 knock-ons (sizing, §4 note) | Recorded in §3.1 and K2. |
| en.B1 question | Adopted the reviewer's shorter wording. |
| DT en phrasal_verb dimension | Withdrawn. Fidelity kept; only jev_bucket = B1 (split). |
| ja moderate (two-slot edit, C2) | Replaced with a single-slot swap: 兄と姉の二人 → 兄や姉の二人. |
| ja subtle (iterative まで reading) | The object is now この本 (singular, definite). |
| ほど affirmative uses | Definition narrowed to comparative ほど. Four affirmative uses added to "Not an error". |
| Spatial / range まで | Added to "Not an error". Positive restated as time-point noun + まで. |
| Stacking vs wa_ga rule | Stacking is now routing-only (not authored). The exception is stated in the wa_ga row. Its budget moved to P1/P2. |
| ねよ (reject) | Removed from the definition and the budget. |
| Routing-only particles | §2.1 now separates routing scope from authored patterns P1–P3. |
| まで/ほど vs clause_linkage | Stated to be particle_other after a noun or a predicate; clause_linkage limited to its own connective list; authored まで/までに on time nouns only. |
| ja.B1 cross-bucket (B9 positives) | Excluded from B1 cross-bucket negatives, reported as a diagnostic; optional B1 rewording as K4. |
| B9 question polarity | Adopted the reviewer's wording (every example yes = clean; 並列の). |
| ja DT split note | Divergences (より, the v5 particle_case list) added to §4 and K7. |
| Optional: と vs comitative と | Adopted (§2.3 case_particle row). |

---

## 7. zh de_particle — user decision 2026-09-27

This section is a user ruling, not an author/reviewer exchange, and it revokes part of `taxonomy.md`'s
zh `de_particle`/`de_particles` "not an error" scope. It does not touch `en.phrasal_verb` or
`ja.particle_other` above.

`taxonomy.md`'s zh grammar entry lists 的-for-地 as **not an error** (common informal usage), and treats
的-for-得 as contested — barred under C11 as either a positive or a hard negative. The DT v6 merge
(`data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json`) carried the 的-for-地 exemption into its
`de_particle` definition, and a relabel exercise on the DT gold/silver corpus
(`data/eval/taxonomy_merge_2026-09-27/relabel/reconciled.json`) hit the 的-for-得 contested status as a
live blocker: two developer-adjudicated gold items (`zh_seed_11`, `zh_multi_02`) could not be resolved
between author and reviewer and were escalated.

**User ruling (2026-09-27): revoked.** ANY misuse of 的/地/得 — 的 for 得, 的 for 地, 地 for 的, or an
obligatory 得 missing — is an error, never acceptable variation. This applies uniformly:
- 的-for-得 (`zh_seed_11`, `zh_multi_02`): error, `de_particle`/minor. The contested/exclude status under
  C11 no longer applies to this rule.
- 的-for-地 (`zh_silver_20`): error, `de_particle`/minor — the "not an error" list entry for this case is
  revoked.
- 地-for-的 (attributive) (`zh_silver_29`): error, `de_particle`/minor (already the case pre-ruling; the
  v6 definition wording is widened to "wrong 的/得/地 choice" so it literally covers this case).

**Consequences for `taxonomy.md` (not applied here, per this file's own rule of leaving `taxonomy.md`
unmodified — folded in at a future taxonomy.md revision):**
- Remove the 的-for-地 "not an error" list entry from zh `de_particle`.
- Remove 的-for-得 from C11's contested/exclude list; it is now a plain positive under the same rule as
  的-for-地 and 地-for-的.
- `v5_to_merged.csv`'s zh `de_particles` row becomes a 1:1 mapping (was `split`) — see the updated CSV.
- `merged_taxonomy.json`'s zh `de_particle` definition and `tests/fixtures/dt_gold/README.md`'s
  "clean items" provenance line are updated accordingly (ADR-031 Consequences has the full record).

---

## 8. Second port (2026-09-27): plural_number, topic_comment

Status: reviewed once (`taxonomy_addendum_2026-09-27_review2.json`: 11 pass, 19 fix, 0 reject). All 19 fixes
are applied; see §8.7. §0 of `taxonomy.md` (C1–C12, V1–V11, polarity, sizing) applies
unchanged. The §6 review lessons are applied up front:
- no contested form is used as a positive;
- every edit is single-slot (C2);
- each type has **one** decisive boundary test, not a set of competing tests: the *repair-slot test* for
  en and zh, and the *topic-deletion test* for ja (both defined below);
- every open class is replaced by a bounded closed list;
- cross-bucket negatives are decided explicitly;
- bucket questions are written in the language's own convention, with yes = clean.

Sources being ported (v5 `migrations/dt_taxonomy_v5_seed.sql`; carried into `merged_taxonomy.json` with
`jev_bucket: null`):
- en `plural_number` (`accuracy` / `minor`, treatable, cloze-suitable): "plural/number — wrong singular/plural
  form or countability (e.g. a missing -s, or a plural on an uncountable noun)".
- zh `topic_comment` (`naturalness` / `minor`, not treatable, not cloze-suitable): 「话题—评论结构——话题/主语—述题
  结构使用不当（常为母语结构的过度迁移）」.
- ja `topic_comment` (same DT fields): 「主題—解説構造——「は」による主題提示など、主題と解説の組み立て方の誤り」.

All three jev types are **narrower** than their v5 sources (§8.5).

**The repair-slot test (the decisive test for en and zh).** List every one-slot repair (C2) that turns the
broken sentence into a fully correct sentence with the **same meaning**. The item belongs to the new type only
if **every** such repair acts on that type's slot:
- `en.plural_number`: the head noun's number ending;
- `zh.topic_comment`: the pre-verbal subject/topic slot, without moving anything.

If any same-meaning repair acts on another type's slot, the item is that other type. If repairs exist on two
types' slots, the item is invalid under C7. Repairs that change the meaning (for example *two brother* →
*a brother*) do not count.

**The topic-deletion test (the decisive test for ja).** Delete the whole closed-list は-phrase (私の趣味は,
昨日遅れた理由は). The item is `ja.topic_comment` only if the broken sentence is wrong **and** what remains
after the deletion is a fully correct sentence (本を読みます, 医者になりたいです, 電車が止まりました).
`ja.tam`, `ja.conjugation`, `ja.keigo` and `ja.register` errors survive the deletion, so they fail this test.
A slot test does not work for ja, because those types also edit the sentence-final predicate.

### 8.1 English — `en.plural_number`

#### Type-table row

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `en.plural_number` | Noun number | A noun is in the wrong number for a fixed licensor. Either it is singular after a closed-list plural licensor (N1, N2), or it carries a plural ending when it is on the closed list of uncountable nouns (N3). The determiner and the verb are correct and unchanged. | G | low | Native-level en generators mark number reliably. The residual risks are *one of the + singular* inside long noun phrases, and translationese plurals of uncountables (*informations*, *advices*) when the prompt is built from a zh/ja source. | B4 |

**Edit kinds.** Positives use exactly one of these. Each is a single-slot edit on the head noun only.
- **N1: missing plural after a plural licensor.** The closed licensor list is: a cardinal numeral of two or
  more (as a word or a digit), *both*, *several*, *a few*, *a couple of*, *many*. Remove the plural ending (*two
  brothers* → *two brother*). With an irregular noun, swap in its real singular form (*three children* →
  *three child*).
- **N2: singular after *one of*.** The frame is *one of* + determiner + (adjective) + noun (*one of the best
  players* → *one of the best player*).
- **N3: plural on an uncountable noun.** This edit uses only a closed list of nouns that are uncountable in
  their ordinary sense in standard edited English: *advice, information, furniture, luggage, homework,
  housework*. Add *-s*, and keep a number-neutral determiner (*the, some, any, no, my/your/…*, or no
  determiner). A regular *-s* form of these nouns is a wrong paradigm form, not a typo. It is the English
  counterpart of `ja.conjugation`'s wrong-paradigm rule, so C5 is not breached. The source must use the noun
  in its **ordinary** sense (*advice* = guidance), never a commercial or figurative sense (*remittance
  advices*).

**Hard constraints.**
- (a) The edited noun must **not** be the subject of a verb that shows number: a present-tense verb, *was/were*,
  *has/have*, or *does/do*. Otherwise the verb also gives a repair, which is `en.agreement` (C7).
  Existential *there* + *be* + an N1 noun phrase (*There are two brother in my class*) is **excluded**,
  because *there's two …* is standard in speech and invites a second-defect reading.
- (b) The edited noun must not be the target. This keeps B5 and B6 clean, as for `en.phrasal_verb`.
- (c) Never edit a numeral word itself (*two hundreds*, *three dozens*).
- (d) Never produce an over-regularised non-word (*childs, mans, foots, sheeps, mouses*). These fail C5.
- (e) Never edit a noun that is used as a modifier (*a shoe shop* → *a shoes shop*). That is a different rule,
  and *sports car* / *clothes shop* show it is not a clean one.

#### Type details

| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | I have two brothers and a sister. | I have two brother and a sister. | N1. *-s* removed after the numeral *two*. The object is not a subject, so no verb repair exists. |
| moderate | My teacher gave me some useful advice. | My teacher gave me some useful advices. | N3. *Advice* is on the uncountable list. *Some* is number-neutral, so the determiner is correct and the only repair is on the noun. V9: check COCA for "useful advices". |
| subtle | She is one of the best players on the team. | She is one of the best player on the team. | N2. *One of* requires a plural noun. The verb *is* agrees with *she*, so agreement is untouched. The long noun phrase lets the surface pass a skim. |

Not an error:
- Uncountable nouns in the singular, and count use through a unit noun (*some advice*, *two pieces of advice*).
- Nouns that are countable and uncountable in different standard senses, used in their count sense (*two
  coffees*, *the papers*, *many experiences*, *his early works*, *tropical fruits*, *a few grey hairs*, *three
  times*). Only the N3 closed list may carry an N3 positive.
- Zero-plural nouns (*sheep, deer, fish, aircraft, series, species*).
- Plural-only nouns (*trousers, scissors, glasses, clothes*).
- Measure nouns used as modifiers, which are singular (*a five-year-old boy*, *a ten-minute walk*, *a two-week
  holiday*).
- Plural modifier nouns that are standard (*sports car, clothes shop, savings account, arms race*).
- *More than one* + singular (*more than one student*), and *many a* + singular.
- *people* / *persons*.
- *data* / *media* with singular or plural agreement (`taxonomy.md` §3 norm).
- Generic singular vs plural (*The tiger is endangered* / *Tigers are endangered*).
- Collective nouns in the singular form. Their verb agreement belongs to `en.agreement`.

Contested — exclude (C11):
- Distributive singular (*They raised their hand*).
- *these kind of things*.
- *a criteria*, *a phenomena*.
- *a scissor* / *a trouser* (attested as modifiers and in fashion usage).
- *fishes*, *feedbacks*, *researches*, *evidences*, *knowledges*, *equipments*, *baggages* (each attested in
  some edited register, or in a figurative sense).
- Zero or decimal quantities (*0 item(s)*, *1.5 hour(s)*).
- *a ten minutes' walk* (UK genitive of measure; spacing/punctuation would decide it).
- Predicative measure phrases (*He is five year old*).

#### Boundary rules

| Neighbour | Rule (via the repair-slot test) | Example routed there |
|---|---|---|
| `en.agreement` | If a same-meaning repair changes only a **verb**, the item is agreement. Constraint (a) guarantees that plural_number positives never offer one. A subject noun whose number was changed so that it now clashes with its verb (*The dogs barks*) has two repairs, so it is invalid. | *The children plays* → agreement. |
| `en.article_determiner` | Hold the noun fixed. If the **determiner** is wrong for that noun in any number (*an advice*, *many information*, *much books*), the item is article_determiner. Hold the determiner fixed. If the **noun** is in the wrong number for it (*two brother*, *some advices*), the item is plural_number. A numeral or a count determiner combined with an uncountable noun (*two furnitures*, *a furniture*) is article_determiner, and never an N3 positive. | *I need an advice* → article_determiner. |
| `en.lexical_form` | A change of word-family member (*success* / *successful*) is lexical_form. A number inflection is plural_number. | *She is very success* → lexical_form. |
| `en.target_absent` / `target_not_whole_word` | Constraint (b). The target is never the edited noun. | — |

#### Corruption and verification additions
- Use only N1–N3, with constraints (a)–(e).
- The suggested mix for about 10 positives is 4 N1, 3 N2 and 3 N3. **Each edit kind must appear at two or
  more subtlety levels**, so that per-level recall does not just measure the edit kind. Examples:
  - subtle N1 inside a long noun phrase (*both of her older sister*, *a few of the new student*);
  - obvious N2 in a short sentence (*He is one of my friend*);
  - obvious N3 in a short sentence (*I have homeworks*).
- Run the V9 corpus check (COCA / BNC) on **every** N3 item and every subtle item.
- `variant_ok` hard negatives: count senses of dual nouns (*two coffees*), measure modifiers (*a ten-minute
  walk*), zero plurals (*three sheep*), *more than one student*, and *two pieces of advice*.

### 8.2 Chinese — `zh.topic_comment`

#### Scope decision

In a single sentence, most topic–comment mismatches are marked or stylistic rather than wrong, or they are
already owned by `zh.word_order` (whose "not an error" list already accepts topicalization and double
subjects). One pattern is both unambiguously wrong and single-slot, so it is the only **authored** pattern:
- **Z1: expletive 它.** 它 is inserted as a dummy subject of a weather verb, calquing English "it". The closed
  verb list is 下雨, 下雪, 刮风, 起风, 打雷. Mandarin weather predicates take no subject, or take a place or
  time topic (外面, 昨天).

Routing-only patterns are labelled `zh.topic_comment` if they appear in live output, but they are **never
authored**, because each one is contested or collides with another type:
- A resumptive 它 after a fronted inanimate object (这本书我看过它). This is contested.
- A preverbal indefinite subject of a locative predicate (一本书在桌子上). This is contested because a
  quantity reading ("one book, not two") rescues it under V5.
- 关于/对于 introducing a fronted object topic (关于这本书，我很喜欢). This is contested, and it collides with
  `zh.coverb`.
- A 在-phrase used as the subject of 是 (在北京是一个大城市). This collides with `zh.coverb`, because the
  repair deletes a preposition, so it is invalid under C7.
- Expletive 它 with time, temperature or distance predicates (它很冷, 它八点了). 它 can have a referent there,
  which fails C8.

#### Type-table row

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `zh.topic_comment` | Subject/topic slot (话题—主语结构) | The pre-verbal subject/topic slot is filled in an English way that Mandarin does not allow. Authored positives: a dummy 它 as the subject of a closed-list weather verb (Z1). Other English-style fillers of that slot are routing-only. | G | low | LLM zh rarely calques expletive "it". The risk rises in translationese T1 weather sentences built from an English prompt frame ("It rained all night"). | B4 |

#### Type details

| Level | Correct | Broken | What changed |
|---|---|---|---|
| moderate | 下雨了，我们快回家吧。 | 它下雨了，我们快回家吧。 | Z1. Sentence-initial dummy 它, a word-for-word match of English "It's raining", so an English-L1 learner is unlikely to notice. 下雨 takes no subject. |
| moderate | 外面正在下雪。 | 外面它正在下雪。 | Z1. 它 is inserted after the non-referential place topic 外面. 它 cannot resume a locative topic, so it has no referent. |
| moderate | 因为昨天下了一夜的雪，路上很滑。 | 因为昨天它下了一夜的雪，路上很滑。 | Z1 inside a subordinate clause, after a time word. Sentence length does not hide a stray pronoun, so the item is moderate, not subtle. |

**Single-level type (known limitation).** Z1 produces only **moderate** items. Any native reader notices a
stray 它 immediately; an L1-English learner may not. The §0.10 three-way subtlety split cannot be met. This is
recorded as a property of the type, not as a shortfall to fill.

Not an error:
- Weather sentences with no subject, or with a place or time topic (下雨了, 外面下雨了, 山上下雪了,
  昨天刮了一天风).
- 天 as the subject (天下雨了, 天阴了).
- 它 with a real antecedent in the same sentence (那只猫很可爱，它每天都睡在沙发上).
- Topicalization and double subjects (这本书我看过了, 大象鼻子很长). These are already listed under
  `zh.word_order`.
- Subject omission (pro-drop) in any register.
- Indefinite subjects introduced by 有 (有一本书在桌子上 / 桌子上有一本书).
- Dummy-**object** 它 (管它下不下雨, 由它下吧, 睡它一觉). This is correct. It must never be used as a source
  or as a positive.

Contested — exclude (C11):
- Every routing-only pattern above.
- A resumptive 它 right after a fronted topic (那只猫它…, 这场雨它…).
- 它 after a named or demonstrative place topic (伦敦这座城市它经常下雨, 这个地方它…).

#### Boundary rules

| Neighbour | Rule (via the repair-slot test) |
|---|---|
| `zh.word_order` | If a same-meaning repair **moves** a constituent, the item is word_order. A topic_comment repair only deletes, inserts or replaces a word in the pre-verbal subject/topic slot. For Z1 the repair is deleting 它. |
| `zh.coverb` | If the repair replaces a preposition with another preposition, the item is coverb. A preposition used as a topic marker (关于/对于 X，…) is routing-only here and is never authored under either type. |
| `zh.connective` | Topic_comment edits never touch a connective. In the third item, 因为 is unchanged. |
| `zh.semantic_anomaly` | If a blind reviewer reads the item as semantic_anomaly, discard it (V1/V11). If a type's items are often read as anomaly, its examples need reworking (the V11 >30% flag). |
| `zh.aspect_negation` | 了, 正在 and the other aspect marking stay unchanged. |

#### Corruption and verification additions
- The only edit is inserting 它 **as the subject** of a closed-list weather verb. Dummy-object 它 is never
  used.
- The source must contain one of the listed weather verbs and must **not** contain any noun that 它 could
  pick up as an antecedent.
- Any topic before 它 must be non-referential: 外面, or a time word. Never use a named or demonstrative place
  topic.
- V5 check: try a place-antecedent reading ("伦敦呢？——它下雨了"). If the reviewer finds it acceptable, reject
  the item.
- **Diagnostic slice, capped at about 8 positives, all moderate.** Pair every Z1 positive with a
  `variant_ok` item that contains **both** a 它 with a real in-sentence antecedent **and** a weather verb
  (那只猫很可爱，它从来不怕下雨). Spotting 它 alone then scores at chance.
- If fewer than about 6 confirmed sources exist, make `zh.topic_comment` **routing-only in jev** rather than
  relaxing C1.
- Other `variant_ok` items: 天下雨了, and weather sentences with no subject or with a place topic.

### 8.3 Japanese — `ja.topic_comment`

#### Scope decision (は/が)

The brief's rule is that any edit to は or が belongs to `ja.wa_ga`. Under it, a topic–comment error that is
made **by inserting a topic phrase** cannot be authored here. The main examples are an expletive or
redundant topic calqued from English (それは雨が降っています for "It is raining") and a doubled topic (私は私の…).
Both need a は to be inserted, and neither falls under `ja.wa_ga`'s three structural rules. They are therefore
**routing-only** and are **never authored under any type**.

The authorable scope is the **comment side**: 主述のねじれ (topic–predicate mismatch). The は-topic is held
fixed and correct. The sentence-final predicate is replaced with a well-formed predicate that does not fit
the topic noun.
- **J1a.** Topic heads 夢, 目標, 希望, 趣味, 目的 require a nominal comment (～ことです / noun + です). Edit:
  V-る/V-ない + ことです → the plain polite finite form of the same verb (V-ます / V-ません), or, **for 夢, 目標
  and 希望 only**, → V-たいです.
- **J1b.** Topic heads 理由 and 原因 require ～からです / ～ためです. Edit: V-た + からです (or ためです) → V-ました,
  keeping the same tense and polarity.

**C2 basis.** J1 is a **one-constituent replacement** under C2's "replace one … constituent" clause. The
sentence-final predicate complex (verb + auxiliaries + こと/から/ため + です) counts as one constituent. It is
the smallest edit that creates the mismatch without also creating a malformed form: deleting こと alone gives
読むです, which would be `ja.conjugation` (C7). Because the edit changes more than one morpheme, **J1 can
never produce a §0.4 subtle item** (C9 requires a one-morpheme edit). Topic–predicate distance is not used as
a subtlety cue unless §0.4 is first amended to allow it.

#### Type-table row

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `ja.topic_comment` | 主題と述語の対応（主述のねじれ） | The は-topic is a closed-list noun that requires a nominal comment (夢・目標・希望・趣味・目的 → ～ことです; 理由・原因 → ～からです/～ためです), but the sentence ends in a finite verbal predicate instead. は/が themselves are never edited. | G | low | LLM Japanese usually produces 夢は～ことです correctly. The residual risk is a long 理由は-clause that ends in a plain past verb, and the English "My dream is (that) I want to…" calque. | B3 |

#### Type details

| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 私の趣味は本を読むことです。 | 私の趣味は本を読みます。 | J1a. 読むことです → 読みます. The topic 趣味 now has an action verb as its comment ("my hobby reads books"). |
| moderate | 私の夢は医者になることです。 | 私の夢は医者になりたいです。 | J1a (たい). This is the classic ねじれ that 作文指導 corrects. A 夢 topic needs ～ことです. Learners miss it; native readers notice at once. |
| moderate | 昨日遅れた理由は電車が止まったからです。 | 昨日遅れた理由は電車が止まりました。 | J1b. からです → a finite past verb, with the same tense. A 理由 topic needs ～からです. Topic deletion leaves 電車が止まりました, which is correct. There is no comma after 理由は, to avoid the spoken "the reason being: …" reading. The item is moderate because the edit is multi-morpheme (C9). |

J1 is a two-level type (obvious and moderate). Keep 私の in every 趣味 item, because a bare 趣味は invites a
loose "as for hobbies" reading. Prefer sources with no comma after 理由は/原因は.

Not an error:
- Noun comments (趣味は読書です, 夢は医者だ). ～ことだ vs ～ことです is register only.
- うなぎ文 and こんにゃく文 (僕はうなぎだ, こんにゃくは太らない).
- 象は鼻が長い-type double-subject sentences, and 象の鼻は長い.
- ～ということです, ～ことなんです, and 理由は～からだ / ～ためだ / ～ことだ.
- 原因は～ことです.
- 理由 or 夢 used as a plain subject rather than a topic–comment frame (理由が二つあります, 夢を見た).
- Topic heads outside the closed list (今日は, 私は).
- Subject omission.
- A て-form continuation that leaves the frame (趣味は本を読むことで、…).

Contested — exclude (C11):
- An i-adjective comment without こと (この町のいいところは、公園が多いです). This is widespread in speech.
- 理由は～んです / ～のです.
- 目的は～ためです. It is common in edited text and doubtful only on grounds of redundancy. Use it neither as
  a source frame nor as `variant_ok`.
- Expletive or doubled topics (それは雨が降っています, 私は私の部屋を…). These are routing-only (above).

#### Boundary rules

| Neighbour | Rule (via the topic-deletion test) |
|---|---|
| `ja.wa_ga` | topic_comment never edits は or が. The は-topic stays exactly as in the source. An item whose error is on は/が is either wa_ga (only under wa_ga's three structural rules) or not authored. |
| `ja.conjugation` / `ja.tam` / `ja.keigo` / `ja.register` | Their errors survive topic deletion, so they fail the test (読むです stays malformed; a wrong tense stays wrong). J1 edits also keep tense, polarity and です/ます exactly as in the source. |
| `ja.clause_linkage` | clause_linkage items keep two clauses joined by a connector, and the edit swaps the connector. J1b removes the closing から/ため and leaves no clause joined after it. Topic deletion leaves a correct single clause (電車が止まりました). |
| `ja.modification` / nominaliser の | The edits never swap こと ↔ の. Nominaliser の vs こと stays uncovered (§2.1). |
| `ja.semantic_anomaly` / `ja.contradiction` | If a blind reviewer reads the item as semantic_anomaly or contradiction, discard it (V1/V11). If a type's items are often read that way, its examples need reworking (the V11 >30% flag). |

#### Corruption and verification additions
- Use only J1a and J1b, and only the closed topic-head list.
- The target must not be こと, から or ため. If the target is the comment verb, its lemma must survive the edit
  (読む → 読みます).
- Keep the script mix and the register (`taxonomy.md` §2.4).
- **V2/V5 standard (the ja.keigo precedent).** ねじれ is like `ja.keigo`'s お帰りしました for a superior,
  which `taxonomy.md` accepts as a positive ("very common even among natives, but wrong"): it is common in
  native speech but corrected in edited text. The V2 test is whether a learner-textbook editor would correct
  it, and for J1a/J1b the answer is yes. The argument "people say this in conversation" therefore does
  **not** rescue a J1 item. Any **other** rescue, meaning a reading in which the sentence is correct, still
  means reject.
- **Sourcing is the binding constraint.** P1 sentences with a closed-list topic head are rare. If fewer than
  about 13 confirmed sources exist, record the shortfall rather than relaxing C1.

### 8.4 Bucket assignment

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| en.B4 | Word choice & word form | collocation, lexical_form, **plural_number** | "Is each word the one a native speaker would choose, and in the right form: natural word combinations (*make a mistake*, *heavy rain*), the right member of a word family (*successful*, *confidently*), and each noun in the right singular or plural form (*two brothers*, *some advice*)?" |
| zh.B4 | 搭配与主语习惯 (Collocation & subject slot) | collocation, **topic_comment** | 「句中的词语搭配和主语是否都符合汉语母语者的习惯？（省略主语、把话题放在句首都是正常的。）」 |
| ja.B3 | 語・節・主題のつながり (Joining words, clauses & topic) | modification, clause_linkage, **topic_comment** | 「語と語、節と節、主題と述語のつながりは正しいですか。（例：名詞を修飾する形「大きい犬」「静かな部屋」「病気の友達」、「ので」「たら」「ように」などの接続、そして「～は」で示した主題と文末の述語がきちんと対応しているか。）」 |

Every example in the three questions is a correct form, so the polarity is yes = clean. Test each question with
and without the parenthetical (§0.9).

No parenthetical quotes the authored rule or repair, to avoid prompt leakage:
- **zh.B4.** The default parenthetical is a protective note. It keeps pro-drop and topicalization, which are
  this type's own `variant_ok` items, from drawing a "no". A 它/weather example (说天气时不用“它”作主语) is
  tested **only as an ablation**.
- **ja.B3.** The J1 sentences (私の夢は医者になることです, 遅れた理由は電車が止まったからです) are tested
  **only as an ablation**.

Why each bucket was chosen:
- **en.B4.** B1 (article_determiner, preposition, phrasal_verb) and B3 (agreement, word_order, pronoun) are
  both full, although they hold the two nearest neighbours. B2 is about verbs. B4's existing question already
  asks for "the right form of each word", so as worded it would answer "no" on a plural_number positive
  anyway. Putting the type there turns a certain cross-bucket false positive into an in-bucket true positive,
  which is the same reasoning as the §3.1 phrasal_verb decision. `lexical_form` is its nearest morphological
  sibling. The wording says "each noun" to keep `en.agreement` verb errors out of the clause.
  - Rejected alternative: split en.B3 into B3a (agreement, pronoun, plural_number — "do the forms agree?")
    and B3b (word_order), as `taxonomy.md` §3.3 anticipates. That restructures an existing bucket before
    B3 has any results. Revisit it if B4 recall on plural_number is poor.
- **zh.B4.** B1, B2 and B3 are all full. B4 has one type. Both members are "grammatical-looking but
  non-native" types, and both carry the DT dimension `naturalness`. B4's current question ("does every word
  combine with its partner the way a native would say it?") would plausibly answer "no" on 它下雨了, so the same
  in-bucket reasoning applies.
  - Rejected alternative: a new 1-type bucket. Thirty positives of one insertion pattern would teach the
    classifier to spot 它, not to judge the structure.
  - After review, zh.topic_comment is a **capped diagnostic slice** (about 8 positives, §8.2), each paired
    with a 它 + weather-verb `variant_ok`. Collocation keeps about 22 positives, because it carries the real
    zh defect mass (§0.5).
- **ja.B3.** B3 has two types, and its theme, how parts of the sentence are joined, is the topic–predicate
  correspondence. Its hardest neighbour, `clause_linkage` (から in 理由は～からです), is already in B3, so that
  boundary costs nothing at bucket level. B1, B2 and B8 are full. B4 (word choice) is the wrong theme.
- **Cross-language.** zh and ja topic_comment sit in **different** buckets (zh B4, ja B3). This is like
  zh aspect (B1) vs ja tam (B2), and must be noted in the §4 comparability notes (K10). The two types are
  structurally different: zh has an extra subject, ja has a mis-joined predicate.

**Cross-bucket negatives (decided explicitly).**
- en.plural_number N1/N2 positives **are included** in the en.B1 and en.B3 cross-bucket sets. The true answer
  is "yes" by construction, because the determiner and verb are correct. Report them per type.
- en.plural_number **N3** positives are included in en.B3. They are **excluded** from en.B1 and reported
  there separately as a diagnostic, until K8 lands. B1 owns "countability clash", so a B1 rater can
  legitimately read *some advices* as a countability problem. This mirrors the B4 exclusion below.
- en.article_determiner **countability** positives (*an advice*, *many information*) **are excluded** from
  en.B4's cross-bucket set, because the new "singular or plural" clause invites a legitimate "no". Report them
  separately as a diagnostic.
- en.agreement positives stay in en.B4's cross-bucket set. The wording "each noun" makes the true answer
  "yes".
- zh.topic_comment positives **are included** in the zh.B1, zh.B3 and zh.B7 cross-bucket sets. The order,
  prepositions and particles are correct, and 它下雨了 "makes sense", so the true answer is "yes" in all
  three.
- Inbound to zh.B4: zh.connective subject-placement positives (不但他会唱歌…) and zh.word_order positives
  that move the subject **are excluded** from zh.B4's cross-bucket set, because 「主语」 invites a legitimate
  "no". Report them separately as a diagnostic. All other zh positives stay in.
- ja.topic_comment positives **are included** in the ja.B1, ja.B2, ja.B4 and ja.B8 cross-bucket sets. The
  particles, verb forms, word choice and politeness are unchanged, so the true answer is "yes". They **are
  excluded** from ja.B7's set ("makes sense"), where a mis-joined sentence can legitimately read as not making
  sense, and are reported there as a diagnostic.
- Inbound to ja.B3: ja.contradiction and ja.semantic_anomaly positives that have a は-topic (兄は私より三歳年下です)
  **are excluded** from ja.B3's cross-bucket set. There, 「主題と文末の述語が対応しているか」 invites a
  legitimate "no". Report them separately as a diagnostic.
- ja.wa_ga positives stay in ja.B3's cross-bucket set. Report them per type. If the 「～は」 clause causes
  false positives on them, drop 「～は」で示した from the question.

**Sizing (§0.10).**
- en.B4 and ja.B3 become 3-type buckets, with about 10 positives per type. The existing members drop from
  about 15 to about 10.
- zh.B4 becomes a 2-type bucket with about 22 collocation positives and about 8 Z1 positives. All Z1
  positives are moderate, and each is paired with a 它 + weather-verb `variant_ok`. If there are fewer than
  about 6 confirmed Z1 sources, zh.topic_comment becomes routing-only in jev and collocation returns to 30.
- ja.topic_comment's roughly 10 positives are split between obvious and moderate only (§8.3).
- `variant_ok` pools gain the per-type lists above.

### 8.5 Mapping back to DT v6 (`merged_taxonomy.json`)

| merged id | Current merged entry | Proposed | jev_bucket |
|---|---|---|---|
| en `plural_number` | class G, `accuracy`, `minor`, treatable, cloze, `jev_bucket: null` | **No change to the DT fields.** | **Fill: `"B4"`**, mapping_kind `split`. jev covers only noun-side number errors against a fixed licensor (N1–N3). DT's wider scope ("a missing -s" anywhere) also includes subject nouns, whose verb-side repair jev routes to `agreement`. Determiner-side countability (*an advice*) is jev `article_determiner`. Replace "partially overlaps `article_determiner`" in the definition with the noun-side vs determiner-side rule in §8.1. |
| zh `topic_comment` | class D, `naturalness`, `minor`, not treatable, no cloze, `jev_bucket: null` | **Keep class D / `naturalness` / `minor`.** jev authors only an unambiguous error, which alone would argue for `accuracy`. But DT's subtype is wider: it includes L1-transfer structure that is only unnatural, and a narrow jev slice should not re-score it (the same reasoning as §4 phrasal_verb). jev's class G is a jev convention. | **Fill: `"B4"`**, mapping_kind `split`. jev authors only Z1 (expletive 它 with a weather verb), as a capped diagnostic slice. Resumptive 它, indefinite preverbal subjects and 关于-topics are DT-only (contested in jev). Note for relabellers: Z1 is a *subject-prominence* calque (English "it"), the reverse of the "topic-structure over-transfer" at the centre of the v5 gloss. jev's zh.topic_comment does not cover v5's central case. |
| ja `topic_comment` | class D, `naturalness`, `minor`, not treatable, no cloze, `jev_bucket: null` | **Keep class D / `naturalness` / `minor`.** The same reasoning applies. | **Fill: `"B3"`**, mapping_kind `split`. Divergences: (1) v5's gloss centres on 「は」による主題提示 (topic *presentation*), but jev never edits は and covers only the comment side (主述のねじれ, J1a/J1b); (2) the presentation-side errors (expletive or doubled は-topics) remain DT-only; (3) in DT, a wrong は/が choice goes to `particle_wa_ga`, not here. |

### 8.6 Knock-on edits (not done here)

- **K8** `taxonomy.md` en.article_determiner: add "a plural ending on an uncountable noun (*advices*) →
  `en.plural_number`". en.agreement: add "a number change on the subject noun that leaves two repairs is
  invalid (C7)".
- **K9** `taxonomy.md` §3.3 / §2.3 / §1.3: replace the en.B4, ja.B3 and zh.B4 rows with §8.4's rows, and
  apply the sizing changes.
- **K10** `taxonomy.md` §4: en B4 now includes a G type (plural_number). zh B4 and ja B3 gain topic_comment,
  in different buckets, which is not comparable across languages.
- **K11** `taxonomy.md` §0.10 / authoring plans: add the cross-bucket exclusions and inclusions listed in
  §8.4 (both outbound and inbound).
- **K12** `merged_taxonomy.json`: set `jev_bucket` to `"B4"` (en plural_number, zh topic_comment) and `"B3"`
  (ja topic_comment). Replace "jev has no (standalone) equivalent" with a pointer to §8. Leave the other DT
  fields unchanged.
- **K13** `jev_grammar_to_merged.csv`: add rows `en,plural_number,plural_number,split,...`,
  `zh,topic_comment,topic_comment,split,...` and `ja,topic_comment,topic_comment,split,...`, with the §8.5
  divergences. `v5_to_merged.csv`: the notes on those three rows are now stale.
- **K14** `taxonomy.md` ja.wa_ga: add to "Not an error / not authored" that expletive or doubled は-topics
  (それは雨が…) are `ja.topic_comment` routing-only.

### 8.7 Review response

Reviewer: `taxonomy_addendum_2026-09-27_review2.json` (11 pass / 19 fix / 0 reject). **All 19 fix items
applied; none held.** One optional pass-item suggestion (the §8.5 zh note) was also adopted.

| Review item | Action |
|---|---|
| Repair-slot test does not separate ja types | The ja test is now the topic-deletion test (§8 preamble). The repair-slot test is kept for en and zh. |
| en constraint (a): existential *there* | Existential *there* + *be* + an N1 noun phrase is excluded. |
| en N3 list | *equipment* and *baggage* dropped; *equipments*/*baggages* moved to contested. Ordinary-sense-only constraint added. |
| en subtlety confounded with edit kind | Each edit kind must appear at two or more levels; examples added. |
| en.B1 cross-bucket (N3) | N1/N2 included; N3 excluded from en.B1 and reported as a diagnostic until K8 lands. |
| zh obvious item | Relabelled moderate. |
| zh subtle item | Relabelled moderate. zh.topic_comment is declared a single-level type (known limitation). |
| zh 在北京是… reason | Added: collides with zh.coverb, so invalid under C7. |
| semantic_anomaly relabel-into rows (zh, ja) | Replaced with "discard (V1/V11); a V11 >30% rate means the examples need reworking". |
| zh.B4 question leak / vagueness | Adopted the reviewer's wording with the protective note. The 它 example is tested only as an ablation. |
| zh cross-bucket (inbound; B7) | Subject-placement connective and word_order positives are excluded from zh.B4. zh.topic_comment positives are included in zh.B7. |
| zh sizing / hard negatives | Capped at about 8 moderate positives, each paired with a 它 + weather-verb `variant_ok`. Collocation keeps about 22. Routing-only fallback if fewer than about 6 sources. Dummy-object 它 and named/demonstrative place topics are excluded. |
| ja V2/V5 note | Rewritten on the ja.keigo precedent. Conversational frequency does not rescue; any other correct reading still means reject. |
| ja C2 slot | Stated as a one-constituent replacement under C2. J1 cannot produce subtle items. |
| ja subtle item | Relabelled moderate. The comma after 理由は was removed. Prefer comma-free sources. |
| ja clause_linkage row (person-topic test) | Replaced with the topic-deletion test. The connector-swap criterion is stated for clause_linkage. |
| ja "Not an error" | 原因は～ことです added. 目的は～ためです added to contested. |
| ja.B3 question leak | The J1 quotations were removed from the parenthetical and are tested only as an ablation. |
| ja cross-bucket (inbound; B4/B8) | は-topic contradiction and anomaly positives are excluded from ja.B3. ja.topic_comment positives are included in ja.B4 and ja.B8. |
| Optional: §8.5 zh note | Adopted: Z1 is a subject-prominence calque, not v5's central case. |
