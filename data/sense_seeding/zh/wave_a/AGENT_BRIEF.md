# Definition-writing brief (zh, wave_a)

You are writing two-level Chinese dictionary definitions for LinguaLoop. Work only from
files. Make no database calls and no API calls. Do not run any upload script.

Full rules: `.claude/skills/batch-sense-generation/SKILL.md`, section "Stage 2". Summary:

For each batch file you are assigned (`data/sense_seeding/zh/wave_a/batch_NNN.json`), write
`data/sense_seeding/zh/wave_a/batch_NNN.senses.json` beside it: a JSON list with exactly one
entry per `vocab_id` in that batch's `items` (no extras, no omissions).

Entry shape (define) — all text in Simplified Chinese:
  {"vocab_id": 12345, "lemma": "环境", "part_of_speech": 1, "confidence": 0.95,
   "simple": "<child-register definition, ages 4-9: everyday words, one idea per sentence>",
   "standard": "<ordinary dictionary definition: precise, genus + distinguishing property>",
   "example": "<one short natural sentence that uses the word, child register, under 60 chars>"}
Entry shape (skip):
  {"vocab_id": 12345, "lemma": "欧洲", "skip": true, "reason": "proper noun (place name)"}

Rules:
- `part_of_speech` is an INTEGER from the batch's `pos_legend` (1 noun, 2 verb, 3 adjective,
  4 adverb, 5 pronoun, 6 preposition, 7 conjunction, 8 particle, 9 measure_word, 10 idiom,
  11 numeral, 0 other). Omit the key rather than guess. The `part_of_speech` string already
  on an item (jieba codes like n, v, ns) is only a hint.
- `simple` and `standard` are written for different readers, not short/long versions of the
  same sentence. `simple` must avoid any word the definition itself would need to explain.
- `confidence` 0-1, honest. Below 0.7 the row is stored unvalidated.
- The sense to define is the word's PRIMARY, most common everyday sense (rank 1). One sense only.
- Function words (的, 了, 在, 和, 吗 …), measure words, aspect particles ARE words: define
  them (what they do in a sentence), POS 8 particle / 6 preposition / 9 measure_word etc.
- Skip: proper nouns (people, places, brands, dynasties), pure numerals, symbols, fragments
  that are not words, obscene words, and dictionary variants with no independent meaning.
- When `existing_standard` is present, read it; keep it if correct (improve only if wrong or
  vague) and add the missing `simple`.
- Preserve characters exactly; no pinyin, no English in the definitions.

Before finishing, validate each file with:
  python3 -c "import json,sys; b=json.load(open('BATCH')); a=json.load(open('SENSES')); ids=[x['vocab_id'] for x in b['items']]; got=[x['vocab_id'] for x in a]; assert sorted(ids)==sorted(got), (set(ids)^set(got)); assert all(isinstance(x.get('part_of_speech',0),int) for x in a); assert all(x.get('skip') or (x.get('simple') and x.get('standard') and x.get('example')) for x in a); print('ok', len(a), sum(1 for x in a if x.get('skip')), 'skips')"
Report back one line per batch: file, defined count, skip count.
