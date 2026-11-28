export const meta = {
  name: 'new-language-pack',
  description: 'Agent team that builds the content pack for a new study language as local files (profile, lexicon, senses, dictionaries, grammar drills, exercise documents, wiring plan)',
  whenToUse: 'Run from the new-language-swarm skill, after `language_pack.py init` and `lexicon-candidates`. args: {lang, name, languageId, repo, glossLanguages, scale, models, skip}',
  phases: [
    { title: 'Profile', detail: 'profiler, then an independent reviewer' },
    { title: 'Lexicon', detail: 'curators over the frequency candidates' },
    { title: 'Senses', detail: 'author and reviewer per batch' },
    { title: 'Dictionaries', detail: 'author and reviewer per lookup table' },
    { title: 'Grammar', detail: 'plan, guides, then author and blind reviewer per batch' },
    { title: 'Exercises', detail: 'cheat sheet, then fat-seed author and reviewer' },
    { title: 'Wiring', detail: 'pending SQL and engineering tasks' },
  ],
}

// ---- arguments -----------------------------------------------------------
const A = args || {}
if (!A.lang || !A.name || !A.languageId || !A.repo) {
  throw new Error('args need lang, name, languageId and repo')
}
const lang = A.lang
const S = Object.assign({
  lexiconRows: 300,     // candidate rows curated (from rank 1)
  lexiconChunk: 300,    // rows per curator
  senseWords: 50,       // words defined
  senseBatch: 25,       // words per sense batch
  dictRows: 60,         // rows per dictionary
  guideTopics: 3,       // topics that get a guide and batches (0 = every topic of the plan)
  batchesPerTopic: 1,   // batches written per topic (0 = the plan's count)
  batchItems: 50,       // items per batch; the plan's batch_size at full scale
  fatseedSenses: 6,     // exercise documents
  fatseedGroup: 3,      // documents per author
}, A.scale || {})
const M = Object.assign({ lead: undefined, author: 'sonnet', reviewer: undefined, clerk: 'haiku' }, A.models || {})
const skip = new Set(A.skip || [])
const gloss = (A.glossLanguages || ['en']).join(', ')
const SK = '.claude/skills/new-language-swarm'
const PACK = `data/language_packs/${lang}`
const TOOL = `python scripts/language_pack.py`

const brief = (role, task) =>
  `You are a member of the agent team building the ${A.name} content pack for LinguaLoop.\n` +
  `Work from the repository root: ${A.repo}\n` +
  `Read ${SK}/briefs/COMMON.md and ${SK}/briefs/${role}.md first; they are your instructions.\n` +
  `Language: ${A.name} (code "${lang}"). PACK = ${PACK}/. Tool: ${TOOL} <command> ${lang} ...\n\n` +
  `Your task: ${task}`

const REPORT = {
  type: 'object',
  properties: {
    wrote: { type: 'array', items: { type: 'string' }, description: 'paths written' },
    counts: { type: 'string', description: 'what was produced, in numbers' },
    validator_ok: { type: 'boolean', description: 'the validator named in the brief ended with OK' },
    doubts: { type: 'array', items: { type: 'string' }, description: 'unresolved doubts and rule conflicts' },
  },
  required: ['wrote', 'counts', 'validator_ok', 'doubts'],
}
const withList = (key, description) => ({
  type: 'object',
  properties: Object.assign({}, REPORT.properties, { [key]: { type: 'array', items: { type: 'string' }, description } }),
  required: REPORT.required.concat([key]),
})
const clerk = (label, phaseName, commands, key, description) =>
  agent(
    `Work from the repository root: ${A.repo}\nRun exactly these commands, in order, and nothing else. ` +
    `Do not edit any file.\n${commands.map(c => '  ' + c).join('\n')}\n` +
    `Report what they printed. Put the list the last command printed in "${key}".`,
    { label, phase: phaseName, model: M.clerk, effort: 'low', schema: withList(key, description) })
const range = n => Array.from({ length: n }, (_, i) => i)
const nn = i => String(i + 1).padStart(2, '0')
const done = []
const keep = (stage, r) => { if (r) done.push(Object.assign({ stage }, r)); return r }

// ---- 1. profile (everything depends on it) ---------------------------------
phase('Profile')
let dictKeys = A.dictionaries || []
if (!skip.has('profile')) {
  const p = keep('profile', await agent(
    brief('profiler', `Write ${PACK}/profile.json. proposed_language_id = ${A.languageId}; gloss_languages = [${gloss}]. ` +
      `Return the dictionary keys in "dictionaries".`),
    { label: 'profiler', phase: 'Profile', model: M.lead, schema: withList('dictionaries', 'dictionary keys of the profile') }))
  if (!p) throw new Error('the profiler did not finish')
  const r = keep('profile-review', await agent(
    brief('profile-reviewer', `Review and fix ${PACK}/profile.json. Return the final dictionary keys in "dictionaries".`),
    { label: 'profile reviewer', phase: 'Profile', model: M.reviewer, schema: withList('dictionaries', 'final dictionary keys') }))
  dictKeys = (r || p).dictionaries
}
log(`profile done; dictionaries: ${dictKeys.join(', ') || 'none'}`)

// ---- 2. branches that only need the profile -------------------------------
const cheat = skip.has('exercises') ? Promise.resolve(null) : agent(
  brief('cheatsheet', `Write .claude/skills/fat-seed-authoring/cheatsheets/${lang}.md.`),
  { label: 'cheat sheet', phase: 'Exercises', model: M.lead, schema: REPORT }).then(r => keep('cheatsheet', r))

const wiring = skip.has('wiring') ? Promise.resolve(null) : agent(
  brief('wiring', `Write ${PACK}/wiring/pending_language.sql, tasks.md and prompt_tasks.txt. proposed_language_id = ${A.languageId}.`),
  { label: 'wiring planner', phase: 'Wiring', model: M.lead, schema: REPORT }).then(r => keep('wiring', r))

// lexicon -> (senses -> exercise documents) and (dictionaries)
const chunks = range(Math.ceil(S.lexiconRows / S.lexiconChunk))
const lexicon = skip.has('lexicon') ? Promise.resolve([]) : parallel(chunks.map(i => () => {
  const from = i * S.lexiconChunk + 1
  const to = Math.min(S.lexiconRows, (i + 1) * S.lexiconChunk)
  return agent(
    brief('lexicon', `Curate candidate rows ${from} to ${to} (the rank column) of ${PACK}/lexicon/candidates.tsv into ` +
      `${PACK}/lexicon/lexicon_${nn(i)}.jsonl.`),
    { label: `lexicon ${from}-${to}`, phase: 'Lexicon', model: M.author, schema: REPORT }).then(r => keep('lexicon', r))
}))

const senses = lexicon.then(async () => {
  if (skip.has('senses')) return null
  const cut = await clerk('cut sense batches', 'Senses',
    [`${TOOL} validate-lexicon ${lang}`, `${TOOL} sense-batches ${lang} --size ${S.senseBatch} --limit ${S.senseWords}`],
    'batches', 'file names of the write_NNN.in.json batches the last command created')
  const names = (cut && cut.batches || []).map(b => b.replace('.in.json', ''))
  log(`${names.length} sense batches`)
  await pipeline(names,
    name => agent(
      brief('sense-author', `Write ${PACK}/senses/${name}.out.json from ${PACK}/senses/${name}.in.json. Gloss languages: ${gloss}.`),
      { label: `senses ${name}`, phase: 'Senses', model: M.author, schema: REPORT }).then(r => keep('sense-author', r)),
    (prev, name) => agent(
      brief('sense-reviewer', `Review ${PACK}/senses/${name}.out.json; write ${name}.reviewed.json and ${name}.verdict.json beside it.`),
      { label: `review ${name}`, phase: 'Senses', model: M.reviewer, schema: REPORT }).then(r => keep('sense-review', r)))
  return names
})

const exercises = Promise.all([senses, cheat]).then(async ([names]) => {
  if (skip.has('exercises') || !names || !names.length || !S.fatseedSenses) return null
  const wl = await clerk('pick exercise senses', 'Exercises',
    [`${TOOL} merge-senses ${lang}`, `${TOOL} fatseed-worklist ${lang} --n ${S.fatseedSenses}`],
    'senses', 'the document file names the last command printed')
  const docs = wl && wl.senses || []
  const groups = range(Math.ceil(docs.length / S.fatseedGroup)).map(i => docs.slice(i * S.fatseedGroup, (i + 1) * S.fatseedGroup))
  await pipeline(groups,
    g => agent(
      brief('fatseed-author', `Write the documents ${g.join(', ')} (the "doc" field of ${PACK}/fat_seed/worklist.json) to ${PACK}/fat_seed/words/.`),
      { label: `exercises ${g[0]}…`, phase: 'Exercises', model: M.author, schema: REPORT }).then(r => keep('fatseed-author', r)),
    (prev, g) => agent(
      brief('fatseed-reviewer', `Review the documents ${g.join(', ')} in ${PACK}/fat_seed/words/; write the reviewed copies and verdict lines.`),
      { label: `review ${g[0]}…`, phase: 'Exercises', model: M.reviewer, schema: REPORT }).then(r => keep('fatseed-review', r)))
  return docs
})

const dictionaries = lexicon.then(() => skip.has('dictionaries') ? null : pipeline(dictKeys,
  key => agent(
    brief('dictionary-author', `Write ${S.dictRows} rows of the dictionary "${key}" to ${PACK}/dictionaries/${key}_01.jsonl.`),
    { label: `dictionary ${key}`, phase: 'Dictionaries', model: M.author, schema: REPORT }).then(r => keep('dictionary-author', r)),
  (prev, key) => agent(
    brief('dictionary-reviewer', `Review ${PACK}/dictionaries/${key}_01.jsonl; write ${PACK}/dictionaries/reviewed/${key}_01.jsonl and its verdict file.`),
    { label: `review ${key}`, phase: 'Dictionaries', model: M.reviewer, schema: REPORT }).then(r => keep('dictionary-review', r))))

// grammar: plan -> per topic: guide -> per batch: author -> blind reviewer
const grammar = skip.has('grammar') ? Promise.resolve(null) : (async () => {
  let topics = A.topics
  if (!topics) {
    const plan = keep('grammar-plan', await agent(
      brief('grammar-planner', `Write ${PACK}/grammar/plan.json with batch_size ${S.batchItems >= 100 ? S.batchItems : 100}. ` +
        `Return the topic slugs, most important first, in "topics".`),
      { label: 'grammar planner', phase: 'Grammar', model: M.lead, schema: withList('topics', 'topic slugs, most important first') }))
    if (!plan) return null
    topics = plan.topics
  }
  const chosen = S.guideTopics ? topics.slice(0, S.guideTopics) : topics
  if (chosen.length < topics.length) log(`grammar: ${chosen.length} of ${topics.length} planned topics are built in this run`)
  await pipeline(chosen,
    slug => agent(
      brief('guide-writer', `Write ${PACK}/grammar/guides/${slug}.json for the topic "${slug}".`),
      { label: `guide ${slug}`, phase: 'Grammar', model: M.lead, schema: REPORT }).then(r => keep('guide', r)),
    (prev, slug, ti) => !prev || !prev.validator_ok || !S.batchesPerTopic ? prev : pipeline(range(S.batchesPerTopic),
      b => agent(
        brief('drill-author', `Write batch ${nn(b)} of the topic "${slug}": ${PACK}/grammar/batches/${slug}-${nn(b)}.jsonl, ` +
          `${S.batchItems} items (validate with --min-items ${S.batchItems}). Themes: take themes number ` +
          `${(ti * 3 + b * 5) % 20 + 1}, ${(ti * 3 + b * 5 + 7) % 20 + 1} and ${(ti * 3 + b * 5 + 13) % 20 + 1} of the plan's list.`),
        { label: `drills ${slug}-${nn(b)}`, phase: 'Grammar', model: M.author, schema: REPORT }).then(r => keep('drill-author', r)),
      (p2, b) => agent(
        brief('drill-reviewer', `Review batch ${slug}-${nn(b)}.jsonl (blind solve first). Minimum ${Math.floor(S.batchItems * 0.9)} items ` +
          `in the reviewed file (--min-items ${Math.floor(S.batchItems * 0.9)}).`),
        { label: `review ${slug}-${nn(b)}`, phase: 'Grammar', model: M.reviewer, schema: REPORT }).then(r => keep('drill-review', r))))
  return chosen
})()

const [topicsBuilt, , docsBuilt] = await Promise.all([grammar, dictionaries, exercises, wiring, cheat])

return {
  language: lang,
  scale: S,
  dictionaries: dictKeys,
  topics_built: topicsBuilt,
  exercise_documents: docsBuilt,
  agents: done.length,
  not_ok: done.filter(d => !d.validator_ok).map(d => ({ stage: d.stage, wrote: d.wrote, counts: d.counts })),
  doubts: done.filter(d => d.doubts && d.doubts.length).map(d => ({ stage: d.stage, wrote: (d.wrote || [])[0], doubts: d.doubts })),
  reports: done.map(d => ({ stage: d.stage, counts: d.counts, ok: d.validator_ok })),
}
