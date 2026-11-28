export const meta = {
  name: 'language-pack-scale',
  description: 'Scale an existing language pack: fan out author and reviewer agents over named batches of lexicon, senses, dictionaries, grammar, tests and exercise documents',
  whenToUse: 'After the pilot (workflow.js). The profile, plan and input batches already exist; args.work names what to build. Files only.',
  phases: [
    { title: 'Lexicon', detail: 'curators over candidate ranges' },
    { title: 'Guides', detail: 'one guide writer per topic' },
    { title: 'Senses', detail: 'author and reviewer per batch' },
    { title: 'Dictionaries', detail: 'author and reviewer per file, files of one table in sequence' },
    { title: 'Drills', detail: 'author and blind reviewer per batch' },
    { title: 'Tests', detail: 'planners; per batch author, blind reviewer, cold solver, fixer' },
    { title: 'Exercises', detail: 'fat-seed author and reviewer per group' },
  ],
}

// args: {lang, name, repo, models?, work}
// work (every key optional):
//   lexicon:   {start, end, chunk, firstFile}            candidate ranks -> lexicon_NN.jsonl
//   guides:    [slug, ...]
//   senses:    {first, last}                              write_NNN.in.json must exist (sense-batches)
//   dicts:     [{key, firstFile, files, rows}]            files of one key run one after another
//   drills:    [{slug, first, last, items}]               batch numbers first..last
//   testPlans: [{tier, tests, perBatch, firstBatch}]      planner per tier -> tests/plan/t<tier>.json
//   tests:     [{tier, first, last}]                      batches t<tier>-NN of the tier's plan
//   fatseed:   {groups: [[doc, ...], ...]}                docs from fat_seed/worklist.json
const A = args || {}
if (!A.lang || !A.name || !A.repo || !A.work) throw new Error('args need lang, name, repo and work')
const lang = A.lang
const W = A.work
const M = Object.assign({ lead: undefined, author: 'sonnet', reviewer: 'opus' }, A.models || {})
const SK = '.claude/skills/new-language-swarm'
const PACK = `data/language_packs/${lang}`
const TOOL = 'python3 scripts/language_pack.py'
const nn = i => String(i).padStart(2, '0')
const nnn = i => String(i).padStart(3, '0')
const seq = (a, b) => Array.from({ length: Math.max(0, b - a + 1) }, (_, i) => a + i)

const brief = (role, task) =>
  `You are a member of the agent team building the ${A.name} content pack for LinguaLoop.\n` +
  `Work from the repository root: ${A.repo}\n` +
  `Read ${SK}/briefs/COMMON.md and ${SK}/briefs/${role}.md first; they are your instructions.\n` +
  `Language: ${A.name} (code "${lang}"). PACK = ${PACK}/. Tool: ${TOOL} <command> ${lang} ...\n` +
  `Other agents are writing other files of this pack at the same time: touch only the files named in your task.\n\n` +
  `Your task: ${task}`

const REPORT = {
  type: 'object',
  properties: {
    wrote: { type: 'array', items: { type: 'string' } },
    counts: { type: 'string', description: 'what was produced or changed, in numbers' },
    validator_ok: { type: 'boolean' },
    doubts: { type: 'array', items: { type: 'string' }, description: 'at most 5: unresolved doubts and rule conflicts' },
  },
  required: ['wrote', 'counts', 'validator_ok', 'doubts'],
}
const done = []
const run = (stage, phaseName, label, role, task, model) =>
  agent(brief(role, task), { label, phase: phaseName, model, schema: REPORT })
    .then(r => { if (r) done.push({ stage, label, ok: r.validator_ok, counts: r.counts, doubts: r.doubts || [] }); return r })
// author, then reviewer only when the author's file validated
const pair = (stage, phaseName, label, a, r) =>
  run(stage, phaseName, label, a.role, a.task, M.author)
    .then(res => (res && res.validator_ok)
      ? run(stage + '-review', phaseName, 'review ' + label, r.role, r.task, M.reviewer)
      : (done.push({ stage: stage + '-review', label: 'review ' + label, ok: false, counts: 'skipped: author file did not validate', doubts: [] }), null))

const jobs = []

if (W.lexicon) {
  const L = W.lexicon
  let file = L.firstFile
  for (let from = L.start; from <= L.end; from += L.chunk) {
    const to = Math.min(L.end, from + L.chunk - 1)
    const f = nn(file++)
    jobs.push(() => run('lexicon', 'Lexicon', `lexicon ${from}-${to}`, 'lexicon',
      `Curate candidate rows ${from} to ${to} (the rank column) of ${PACK}/lexicon/candidates.tsv into ` +
      `${PACK}/lexicon/lexicon_${f}.jsonl. Validate your own file only: run "${TOOL} validate-lexicon ${lang}" and ` +
      `fix the problems reported for lexicon_${f}.jsonl; ignore lines about other files (other curators are writing ` +
      `them now), and do not chase duplicates of lemmas in other files: they are removed afterwards.`, M.author))
  }
}

for (const slug of W.guides || []) {
  jobs.push(() => run('guide', 'Guides', `guide ${slug}`, 'guide-writer',
    `Write ${PACK}/grammar/guides/${slug}.json for the topic "${slug}".`, M.lead))
}

if (W.senses) {
  for (const i of seq(W.senses.first, W.senses.last)) {
    const name = `write_${nnn(i)}`
    jobs.push(() => pair('senses', 'Senses', name,
      { role: 'sense-author', task: `Write ${PACK}/senses/${name}.out.json from ${PACK}/senses/${name}.in.json. Gloss languages: en.` },
      { role: 'sense-reviewer', task: `Review ${PACK}/senses/${name}.out.json; write ${name}.reviewed.json and ${name}.verdict.json beside it.` }))
  }
}

for (const d of W.dicts || []) {
  // one table's files in sequence, so each author can see the rows already written
  jobs.push(async () => {
    for (const i of seq(d.firstFile, d.firstFile + d.files - 1)) {
      const f = `${d.key}_${nn(i)}`
      await pair('dictionary', 'Dictionaries', f,
        { role: 'dictionary-author', task: `Write ${d.rows} NEW rows of the dictionary "${d.key}" to ${PACK}/dictionaries/${f}.jsonl. ` +
            `Read the earlier files ${PACK}/dictionaries/${d.key}_*.jsonl first and do not repeat any row's unique key ` +
            `(validate-dict checks uniqueness across all files of the table).` },
        { role: 'dictionary-reviewer', task: `Review ${PACK}/dictionaries/${f}.jsonl; write ${PACK}/dictionaries/reviewed/${f}.jsonl and its verdict file.` })
    }
  })
}

for (const d of W.drills || []) {
  for (const b of seq(d.first, d.last)) {
    const f = `${d.slug}-${nn(b)}`
    const t = (d.slug.length * 7 + b * 5) % 20
    jobs.push(() => pair('drills', 'Drills', f,
      { role: 'drill-author', task: `Write batch ${nn(b)} of the topic "${d.slug}": ${PACK}/grammar/batches/${f}.jsonl, ${d.items} items ` +
          `(validate with --min-items ${d.items}). Themes: numbers ${t + 1}, ${(t + 7) % 20 + 1} and ${(t + 13) % 20 + 1} of the plan's list. ` +
          `Earlier batches of this topic may exist in ${PACK}/grammar/reviewed/: skim their sentences and do not reuse them.` },
      { role: 'drill-reviewer', task: `Review batch ${f}.jsonl (blind solve first). Minimum ${Math.floor(d.items * 0.9)} items in the reviewed file ` +
          `(--min-items ${Math.floor(d.items * 0.9)}).` }))
  }
}

for (const p of W.testPlans || []) {
  jobs.push(() => run('test-plan', 'Tests', `test plan T${p.tier}`, 'test-planner',
    `Write ${PACK}/tests/plan/t${p.tier}.json: ${p.tests} tests for tier ${p.tier}, in batches of ${p.perBatch} numbered from ${nn(p.firstBatch || 1)}.`, M.lead))
}

for (const t of W.tests || []) {
  for (const b of seq(t.first, t.last)) {
    const f = `t${t.tier}-${nn(b)}`
    jobs.push(() => pair('tests', 'Tests', f,
      { role: 'test-author', task: `Write the tests of batch "${f}" in ${PACK}/tests/plan/t${t.tier}.json to ${PACK}/tests/batches/${f}.jsonl.` },
      { role: 'test-reviewer', task: `Review ${PACK}/tests/batches/${f}.jsonl (blind solve first); write ${PACK}/tests/reviewed/${f}.jsonl and the verdict file.` })
      // a solver who has seen nothing answers the reviewed questions without the passages; a fixer repairs what it got
      .then(r => (r && r.validator_ok) ? run('tests-cold', 'Tests', 'cold ' + f, 'test-cold-solver',
        `Cold-solve the reviewed batch ${f}.`, M.reviewer) : null)
      .then(r => (r && r.validator_ok) ? run('tests-fix', 'Tests', 'fix ' + f, 'test-fixer',
        `Repair the questions of ${PACK}/tests/reviewed/${f}.jsonl that the cold solver answered without the passage.`, M.reviewer) : null))
  }
}

for (const g of (W.fatseed && W.fatseed.groups) || []) {
  jobs.push(() => pair('fatseed', 'Exercises', `exercises ${g[0]}`,
    { role: 'fatseed-author', task: `Write the documents ${g.join(', ')} (the "doc" field of ${PACK}/fat_seed/worklist.json) to ${PACK}/fat_seed/words/.` },
    { role: 'fatseed-reviewer', task: `Review the documents ${g.join(', ')} in ${PACK}/fat_seed/words/; write the reviewed copies and verdict lines.` }))
}

log(`${jobs.length} job chains`)
await parallel(jobs)

const byStage = {}
for (const d of done) {
  const s = byStage[d.stage] || (byStage[d.stage] = { agents: 0, ok: 0 })
  s.agents++
  if (d.ok) s.ok++
}
return {
  language: lang,
  stages: byStage,
  not_ok: done.filter(d => !d.ok).map(d => ({ stage: d.stage, label: d.label, counts: d.counts })),
  doubts: done.filter(d => d.doubts.length).map(d => ({ label: d.label, doubts: d.doubts.slice(0, 5) })),
}
