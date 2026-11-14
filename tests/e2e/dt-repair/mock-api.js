/**
 * A stand-in for the DT guided self-repair API (wiki/features/dt-guided-self-repair.tech.md §4).
 *
 * It answers the same endpoints with the same JSON shapes as the real backend, so the sheet,
 * the hosts and the daily player can be developed and verified without it. Classic script:
 * exposes window.DTRepairMock; loaded by tests/e2e/dt-repair/harness.html and (through eval)
 * by the vitest unit tests.
 *
 *   const mock = DTRepairMock.create('en_errors', { latency: 0 });
 *   mock.session            the session payload the submit response would carry (§4.2)
 *   mock.items              the daily payload (§4.11) for the scenario, if it has one
 *   mock.fetch(url, opts)   authFetch-compatible; records every call in mock.calls
 *   mock.fail(action, kind) queue a failure for the next call(s) of an action (see FAILS)
 *
 * The sentences are the real gold-set reproductions the design mockup uses
 * (tests/fixtures/dt_gold_v6); prompts, clues and explanations are illustrative.
 */
(function (root) {
  'use strict';

  const BASE = '/api/dual-translation/repair';
  const cp = (s) => Array.from(s || '').length;
  const norm = (s) =>
    String(s == null ? '' : s)
      .normalize('NFC')
      .replace(/\r\n|\n|\t/g, ' ')
      .replace(/ {2,}/g, ' ')
      .trim();

  function isoDaysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    const p = (x) => String(x).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  // ---- hidden per-item data (what the real server keeps and never sends before the reveal) ----
  const X = {
    sick: {
      prompt: '这是一个在实践中学习的好方法。',
      text: "It's a sick way to learn by doing.",
      ref: "It's a great way to learn by doing.",
      bad: 'sick',
      good: 'great',
      kind: 'Register — how formal it sounds',
      clue: 'One word here is casual slang. The passage is plain, neutral writing.',
      why: '“Sick” for “very good” is slang; neutral writing uses “great”.',
      ok: 'a great way',
    },
    without: {
      prompt: '你可以用它做很多东西。',
      text: 'You can make many things without it.',
      ref: 'You can make many things with it.',
      bad: 'without it',
      good: 'with it',
      kind: 'Opposite meaning',
      clue: 'Read the prompt again: are the things made using it, or not using it?',
      why: '“Without” says the opposite of the prompt (用它 = with it).',
      ok: 'with it',
      ladder: 'short',
    },
    enjoyable: {
      prompt: '用 Arduino 做一个简单的机械臂是一个有趣的 DIY 项目。',
      text: 'Building a simple robot arm with Arduino is an enjoyable DIY project.',
      ref: 'Building a simple robot arm with Arduino is a fun DIY project.',
      bad: 'an enjoyable',
      good: 'a fun',
      why: 'Both words work here; “fun” is the more everyday choice.',
      ok: 'a fun',
      unsure: true,
    },
    ge: {
      prompt: 'My favourite T-shirt is a very special piece of clothing.',
      text: '我最喜欢的T恤是一个非常特别的衣服。',
      ref: '我最喜欢的T恤是一件非常特别的衣服。',
      bad: '一个',
      good: '一件',
      kind: 'Measure word (量词)',
      clue: '衣服 doesn’t take the all-purpose 个. Which measure word goes with clothes worn on the upper body?',
      why: '件 is the measure word for upper-body clothing: 一件衣服.',
      ok: '一件',
      kindLang: 'en',
    },
    le: {
      prompt: "This T-shirt is blue, a really true blue, and it hasn't faded even after many washes.",
      text: '这件T恤是蓝色的，颜色很正，洗很多次也不会褪色。',
      ref: '这件T恤是蓝色的，颜色很正，洗了很多次也不会褪色。',
      bad: '洗很多次',
      good: '洗了很多次',
      kind: 'Aspect marker (了 / 过 / 着)',
      clue: 'The washing has already happened, many times. How does Chinese mark a completed action that comes with a count?',
      why: 'A completed action with a count takes 了 after the verb: 洗了很多次.',
      ok: '洗了很多次',
    },
    relaxed: {
      prompt: 'It makes me feel relaxed and at ease.',
      text: '它让我感到很轻松，很自在。',
      ref: '它让我感到很放松，很自在。',
      bad: '轻松',
      good: '放松',
      why: '放松 is “relaxed”; 轻松 leans towards “easy, light”. Both can be said here.',
      ok: '放松',
      unsure: true,
    },
    learn_on: {
      prompt: '你可以学到机器人和电子方面的知识。',
      text: 'You can learn on robotics and electronics.',
      ref: 'You can learn about robotics and electronics.',
      bad: 'learn on',
      good: 'learn about',
      kind: 'Preposition',
      clue: 'Which small word follows “learn” when you name the subject you study?',
      why: 'You learn about a subject; “on” does not follow “learn” here.',
      ok: 'learn about',
    },
    article: {
      prompt: '首先，你需要一块 Arduino 板。',
      text: 'First, you need Arduino board.',
      ref: 'First, you need an Arduino board.',
      bad: '',
      point: 16, // omission: a point span before "Arduino"
      good: 'an ',
      kind: 'Article (a / an / the)',
      clue: '“Board” is one countable thing, mentioned for the first time.',
      why: 'A singular countable noun needs an article: an Arduino board.',
      ok: 'an Arduino board',
    },
    keep: {
      prompt:
        "I hope this T-shirt can stay with me until it becomes very, very old; even then, I'll put it away carefully as a lovely keepsake.",
      text: '我希望这件T恤能一直陪伴我，直到它变得非常非常旧，但即使那样，我也会把它好好收藏下来，作为一份美好的纪念。',
      ref: '我希望这件T恤能一直陪伴我，直到它变得非常非常旧，但即使那样，我也会把它好好收藏起来，作为一份美好的纪念。',
      bad: '收藏下来',
      good: '收藏起来',
      kind: 'Complement after the verb (起来 / 下来 …)',
      clue: 'Putting something away for safekeeping: which direction word finishes 收藏?',
      why: '收藏起来 means “put away and keep”; 下来 does not combine with 收藏 this way.',
      ok: '收藏起来',
    },
    ja: {
      prompt:
        'You teach the computer, in words it can easily understand (a programming language), how you want the arm to move: instructions such as "move left", "grab the object" and "move right".',
      text: 'アームをどのように動かしたいか、例えば「左に動かす」「物に掴む」「右に動かす」といった指示を、コンピューターに分かりやすい言葉（プログラミング言語）で教え込みます。',
      ref: 'アームをどのように動かしたいか、例えば「左に動かす」「物を掴む」「右に動かす」といった指示を、コンピューターに分かりやすい言葉（プログラミング言語）で教え込みます。',
      bad: '物に掴む',
      good: '物を掴む',
      kind: 'Particle (を / に / で …)',
      clue: '掴む acts directly on the thing that is grabbed. Which particle marks a direct object?',
      why: '掴む takes its object with を: 物を掴む.',
      ok: '物を掴む',
    },
    en_long: {
      prompt: '用 Arduino 做一个简单的机械臂是一个有趣的 DIY 项目。',
      text: 'Building a simple robot arm with Arduino is an enjoyable DIY project.',
      ref: 'Building a simple robot arm with Arduino is a fun DIY project.',
      bad: 'an enjoyable',
      good: 'a fun',
      kind: 'Word choice',
      clue: 'One adjective here is a little more formal than the prompt suggests. What is the everyday word?',
      why: 'Both words work here; “fun” is the more everyday choice.',
      ok: 'a fun',
    },
    direct: {
      prompt: '这个机械臂只是其中一个想法。',
      text: 'This robot arm is just one idea of them.',
      ref: 'This robot arm is just one of the ideas.',
      bad: 'one idea of them',
      good: 'one of the ideas',
      why: '“One of the ideas” is the natural way to pick one from a set.',
      ok: 'one of the ideas',
      ladder: 'none',
    },
  };

  // ---- scenarios -------------------------------------------------------------------------
  const PASSAGE = {
    en: '这是一个在实践中学习的好方法。Arduino 是做 DIY 项目的强大工具。你可以用它做很多东西。这个机械臂只是其中一个想法。',
    zh: "My favourite T-shirt is a very special piece of clothing. It isn't an expensive brand, and it isn't the latest style, but it's my favourite of all my clothes. This T-shirt is blue, a really true blue, and it hasn't faded even after many washes.",
  };

  const SCENARIOS = {
    en_errors: { l1: 'zh', l2: 'en', nClean: 2, passage: PASSAGE.en, steps: ['sick', 'without'], idx: [0, 2] },
    zh_errors: { l1: 'en', l2: 'zh', nClean: 2, passage: PASSAGE.zh, steps: ['ge', 'le'], idx: [0, 2] },
    en_unsure: { l1: 'zh', l2: 'en', nClean: 3, passage: PASSAGE.en, steps: ['enjoyable'], idx: [0], kinds: ['unsure'] },
    zh_unsure: { l1: 'en', l2: 'zh', nClean: 3, passage: PASSAGE.zh, steps: ['relaxed'], idx: [0], kinds: ['unsure'] },
    en_clean: { l1: 'zh', l2: 'en', nClean: 4, passage: PASSAGE.en, steps: [], clean: true },
    zh_clean: { l1: 'en', l2: 'zh', nClean: 2, passage: PASSAGE.zh, steps: [], clean: true },
    en_mixed: {
      l1: 'zh',
      l2: 'en',
      nClean: 1,
      passage: PASSAGE.en,
      steps: ['sick', 'direct', 'article', 'enjoyable'],
      idx: [0, 1, 2, 3],
      kinds: ['repair', 'direct', 'repair', 'unsure'],
    },
    stress_ja: { l1: 'en', l2: 'ja', nClean: 3, passage: X.ja.prompt, steps: ['ja'], idx: [1] },
    stress_zh: { l1: 'en', l2: 'zh', nClean: 3, passage: X.keep.prompt, steps: ['keep'], idx: [1] },
    stress_en: { l1: 'zh', l2: 'en', nClean: 3, passage: PASSAGE.en, steps: ['en_long'], idx: [1] },
  };
  const DAILY = {
    en: { l2: 'en', items: ['learn_on', 'article'], ago: [3, 9] },
    zh: { l2: 'zh', items: ['le', 'keep'], ago: [3, 9] },
  };

  const FAILS = ['network', 'http500', 'error', 'timeout', 'closed', 'inprogress', 'notopened'];

  function create(name, options) {
    const opt = Object.assign({ latency: 0, checkCap: 4, autoAdvanceMs: 1600 }, options || {});
    const sc = SCENARIOS[name];
    const daily = DAILY[String(name).replace(/^daily_/, '')];
    const isDaily = !!daily && String(name).startsWith('daily_');
    if (!sc && !isDaily) throw new Error(`unknown scenario ${name}`);

    const mock = { name, calls: [], failures: {}, items: null, session: null, state: {} };
    let nextId = 7000;

    function rungsFor(x, kind) {
      if (kind === 'unsure' || kind === 'direct' || x.ladder === 'none') return [];
      if (x.ladder === 'short') return [1];
      return [1, 2, 3];
    }

    function makeStep(key, i, kind, idx, surface, from) {
      const x = X[key];
      const id = (isDaily ? 8100 : nextId) + i + 1;
      const k = kind || (x.unsure ? 'unsure' : 'repair');
      const step = {
        item_id: id,
        position: i,
        sentence_index: idx,
        step_kind: k,
        ladder: k === 'direct' ? 'none' : x.ladder === 'short' ? 'short' : k === 'unsure' ? 'short' : 'full',
        prompt_l1: x.prompt,
        learner_sentence: x.text,
        hint_rungs: rungsFor(x, k),
        hint_level: 0,
        where: null,
        last_text: null,
        checks_used: 0,
        check_cap: surface === 'daily_practice' ? 3 : opt.checkCap,
        state: 'open',
        outcome: null,
        from_date: from || null,
      };
      mock.state[id] = { key, x, step, hintLevel: 0, checksUsed: 0, closed: false, outcome: null, answer: null, ids: {}, last: x.text };
      if (surface === 'daily_practice' && step.hint_rungs.includes(1)) {
        step.hint_level = 1;
        step.where = whereFor(x, x.text);
        mock.state[id].hintLevel = 1;
      }
      if (k === 'unsure') step.where = whereFor(x, x.text);
      return step;
    }

    function whereFor(x, text) {
      if (x.point != null) return { start: x.point, end: x.point, text: '', point: true };
      const k = text.indexOf(x.bad);
      if (k < 0 || !x.bad) return null;
      const start = cp(text.slice(0, k));
      return { start, end: start + cp(x.bad), text: x.bad, point: false };
    }

    function answerFor(st, heading) {
      const x = st.x;
      const marks = (text, frag, key) => {
        if (x.point != null && key === 'l') return [];
        const k = text.indexOf(frag);
        if (k < 0 || !frag) return [];
        const s = cp(text.slice(0, k));
        return [[s, s + cp(frag)]];
      };
      return {
        heading: heading || 'compare',
        learner_sentence: x.text,
        learner_marks: marks(x.text, x.bad, 'l'),
        answer_sentence: x.ref,
        answer_marks: marks(x.ref, x.good.trim(), 'a'),
        explanation: x.why,
        explanation_lang: x.kindLang || (st.step.step_kind === 'unsure' ? 'en' : 'en'),
        l2: isDaily ? daily.l2 : sc.l2,
      };
    }

    if (isDaily) {
      mock.items = daily.items.map((key, i) =>
        makeStep(key, i, null, 1 + i, 'daily_practice', isoDaysAgo(daily.ago[i]))
      );
      mock.l2 = daily.l2;
    } else {
      const steps = (sc.steps || []).map((key, i) =>
        makeStep(key, i, sc.kinds ? sc.kinds[i] : null, sc.idx[i], 'repair_pass', null)
      );
      mock.l2 = sc.l2;
      mock.session = {
        session_id: 501,
        submission_id: 9001,
        status: sc.clean ? 'finished' : 'open',
        clean: !!sc.clean,
        surface: 'repair_pass',
        l1: sc.l1,
        l2: sc.l2,
        n_sentences: steps.length + sc.nClean,
        n_clean: sc.nClean,
        prompt_l1_passage: sc.passage,
        auto_advance_ms: opt.autoAdvanceMs,
        steps,
        summary: null,
      };
    }

    function json(status, body) {
      return { ok: status < 400, status, json: async () => body };
    }
    const ok = (body) => json(200, Object.assign({ status: 'success' }, body));
    const err = (status, code, message) => json(status, { status: 'error', error: message || code, error_code: code });

    mock.fail = (action, ...kinds) => {
      (mock.failures[action] = mock.failures[action] || []).push(...kinds);
    };

    async function injected(action, signal) {
      const q = mock.failures[action];
      if (!q || !q.length) return null;
      const kind = q.shift();
      if (kind === 'network') throw new TypeError('Failed to fetch');
      if (kind === 'http500') return err(500, 'INTERNAL', 'boom');
      if (kind === 'closed') return err(409, 'ITEM_CLOSED');
      if (kind === 'inprogress') return err(409, 'CHECK_IN_PROGRESS');
      if (kind === 'notopened') return err(409, 'NOT_OPENED');
      if (kind === 'timeout') {
        await new Promise((resolve, reject) => {
          if (signal) signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        });
      }
      if (kind === 'error') {
        return ok({ item_id: 0, result: 'error', reason: 'call_failed', checks_used: 0, check_cap: opt.checkCap, hints_used: 0, where: null, closed: false, outcome: null, auto_reveal: false, answer: null });
      }
      return null;
    }

    const HINTS = { 1: 'where', 2: 'kind', 3: 'clue' };

    async function route(url, o) {
      const body = o && o.body ? JSON.parse(o.body) : {};
      const path = String(url).replace(BASE, '');
      let m;
      if ((m = path.match(/^\/items\/(\d+)\/(\w+)$/))) {
        const id = Number(m[1]);
        const action = m[2];
        const st = mock.state[id];
        if (!st) return err(404, 'NOT_FOUND');
        const bad = await injected(action, o && o.signal);
        if (bad) return bad;
        if (action === 'open') return ok({ step: Object.assign({}, st.step, { hint_level: st.hintLevel, where: st.hintLevel >= 1 ? whereFor(st.x, st.last) : st.step.where }) });
        if (action === 'hint') {
          if (st.closed) return err(409, 'ITEM_CLOSED');
          const next = st.step.hint_rungs.find((r) => r > st.hintLevel);
          if (!next) return err(409, 'NO_MORE_HINTS');
          st.hintLevel = next;
          const rungs = st.step.hint_rungs;
          const type = HINTS[next];
          const more = rungs.some((r) => r > next);
          return ok({
            item_id: id,
            hint_level: next,
            hint_number: rungs.indexOf(next) + 1,
            hint_total: rungs.length,
            hint: { type, text: type === 'kind' ? st.x.kind : type === 'clue' ? st.x.clue : null, lang: type === 'where' ? null : 'en' },
            where: whereFor(st.x, st.last),
            next: more ? 'hint' : 'answer',
          });
        }
        if (action === 'check') {
          if (st.closed) return err(409, 'ITEM_CLOSED');
          const text = norm(body.text);
          if (body.client_check_id && st.ids[body.client_check_id]) return ok(st.ids[body.client_check_id]);
          const base = { item_id: id, reason: null, check_cap: st.step.check_cap, hints_used: st.step.hint_rungs.filter((r) => r <= st.hintLevel).length, where: null, closed: false, outcome: null, auto_reveal: false, answer: null };
          let res;
          if (text === norm(st.last)) res = Object.assign(base, { result: 'unchanged', checks_used: st.checksUsed });
          else {
            const fixedRe = text.includes(st.x.ok) && (st.x.bad === '' || !text.includes(st.x.bad));
            if (fixedRe) {
              st.closed = true;
              st.outcome = 'self_repaired';
              res = Object.assign(base, { result: 'fixed', checks_used: st.checksUsed, closed: true, outcome: 'self_repaired' });
            } else if (st.x.bad && !text.includes(st.x.bad) && !st.x.point) {
              st.closed = true;
              st.outcome = 'repaired_alternative';
              res = Object.assign(base, { result: 'no_issue_found', checks_used: st.checksUsed, closed: true, outcome: 'repaired_alternative', answer: answerFor(st, 'no_issue') });
            } else if (st.step.step_kind === 'unsure') {
              st.closed = true;
              st.outcome = 'unsure_revised';
              res = Object.assign(base, { result: 'no_issue_found', checks_used: st.checksUsed, closed: true, outcome: 'unsure_revised', answer: answerFor(st, 'no_issue') });
            } else {
              st.checksUsed += 1;
              st.last = text;
              if (st.checksUsed >= st.step.check_cap) {
                st.closed = true;
                st.outcome = 'answer_shown';
                st.hintLevel = 4;
                res = Object.assign(base, { result: 'still_flagged', reason: 'target_present', checks_used: st.checksUsed, closed: true, outcome: 'answer_shown', auto_reveal: true, answer: answerFor(st, 'compare') });
              } else {
                res = Object.assign(base, { result: 'still_flagged', reason: 'target_present', checks_used: st.checksUsed, where: st.hintLevel >= 1 || st.step.step_kind === 'unsure' ? whereFor(st.x, text) : null });
              }
            }
          }
          if (body.client_check_id) st.ids[body.client_check_id] = res;
          return ok(res);
        }
        if (action === 'reveal') {
          st.closed = true;
          st.outcome = st.outcome || (body.reason === 'direct' ? 'shown_directly' : 'answer_shown');
          return ok({ item_id: id, closed: true, outcome: st.outcome, answer: answerFor(st, st.outcome === 'repaired_alternative' ? 'no_issue' : 'compare') });
        }
        if (action === 'dispute') {
          st.closed = true;
          if (st.step.step_kind === 'unsure') {
            st.outcome = 'unsure_dismissed';
            return ok({ item_id: id, closed: true, outcome: 'unsure_dismissed', answer: null });
          }
          st.outcome = 'disputed';
          return ok({ item_id: id, closed: true, outcome: 'disputed', answer: answerFor(st, 'disputed') });
        }
        if (action === 'skip') {
          st.closed = true;
          st.outcome = 'skipped';
          return ok({ item_id: id, closed: true, outcome: 'skipped' });
        }
      }
      if ((m = path.match(/^\/sessions\/(\d+)\/finish$/))) {
        const bad = await injected('finish', o && o.signal);
        if (bad) return bad;
        mock.session.status = 'finished';
        const steps = Object.values(mock.state);
        let fixed = 0;
        let help = 0;
        let saved = 0;
        steps.forEach((st) => {
          const f = st.outcome === 'self_repaired' || st.outcome === 'repaired_alternative';
          if (f) fixed += 1;
          if (st.outcome === 'answer_shown') help += 1;
          if (st.step.step_kind !== 'unsure' && (!st.outcome || ['answer_shown', 'shown_directly', 'skipped'].includes(st.outcome) || (f && st.hintLevel >= 2))) saved += 1;
        });
        return ok({ session_id: Number(m[1]), session_status: 'finished', summary: { fixed_yourself: fixed, needed_help: help, saved_to_practice: saved }, result_available: true });
      }
      if ((m = path.match(/^\/submissions\/(\d+)\/result$/))) {
        const bad = await injected('result', o && o.signal);
        if (bad) return bad;
        if (mock.session && mock.session.status === 'open') return err(409, 'REPAIR_IN_PROGRESS');
        return ok(mock.fullContract());
      }
      if ((m = path.match(/^\/submissions\/(\d+)\/session$/))) {
        if (!mock.session) return err(404, 'NO_SESSION');
        return ok({ session: mock.session });
      }
      if (path.startsWith('/practice/due')) {
        const bad = await injected('due', o && o.signal);
        if (bad) return bad;
        return ok({ total_due: (mock.items || []).length, items: mock.items || [] });
      }
      return err(404, 'NOT_FOUND', `mock has no route ${path}`);
    }

    // The full grade contract the result view renders (shape of routes/dual_translation).
    mock.fullContract = () => ({ status: 'success', scores: { accuracy: 3, fidelity: 2, understandability: 3 }, overall_band: 3, provisional: false, errors: [{ subtype: 'register', severity: 'minor', learner_form: 'sick', corrected_form: 'great' }], diff: [{ op: 'replace', correct: 'great', user: 'sick' }], highlights: [], grader_trace: { tier: 'single_call' } });
    // The redacted contract the submit response carries while the session is open.
    mock.redactedContract = () => ({ status: 'success', scores: { accuracy: 3, fidelity: 2, understandability: 3 }, overall_band: 3, provisional: false, errors: [], diff: [], highlights: [], redacted: true, n_errors: (mock.session && mock.session.steps.length) || 0 });
    mock.submitResponse = () => Object.assign(mock.session && mock.session.clean ? mock.fullContract() : mock.redactedContract(), { repair: mock.session });

    mock.fetch = async (url, o) => {
      const rec = { url: String(url), method: (o && o.method) || 'GET', body: o && o.body ? JSON.parse(o.body) : null };
      mock.calls.push(rec);
      if (opt.latency) await new Promise((r) => setTimeout(r, opt.latency));
      const res = await route(String(url), o);
      rec.status = res.status;
      return res;
    };
    mock.callsTo = (re) => mock.calls.filter((c) => re.test(c.url));
    return mock;
  }

  root.DTRepairMock = { create, SCENARIOS, DAILY, X, FAILS, isoDaysAgo };
})(typeof window !== 'undefined' ? window : globalThis);
