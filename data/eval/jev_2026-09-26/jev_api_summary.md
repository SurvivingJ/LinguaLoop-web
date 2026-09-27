# Jev (typesafe/jev-1.13) on OpenRouter — Technical Summary

Sources: https://openrouter.ai/docs/guides/community/jev-tutorial · https://openrouter.ai/docs/guides/community/jev ·
https://openrouter.ai/typesafe/jev-1.13 · https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request ·
https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-classification · https://openrouter.ai/api/v1/models
(fetched 2026-09-26)

## 1. What Jev is

- **Maker:** TypeSafe (docs.typesafe.ai). OpenRouter routes requests to TypeSafe and bills them to the OpenRouter account; no separate TypeSafe account/API key needed.
- **Category:** Not an LLM / not a chat model. It is a **"System One" structured decision model** — the first of that family. It answers narrow, typed questions about a piece of state and returns **typed values with probabilities**, never free text, reasoning traces, or explanations. Positioned to replace "prompt an LLM + parse its text answer" for routing, classification, verification, and ranking decision points.
- **Model ID:** `typesafe/jev-1.13` (dated snapshot suffix appears in responses, e.g. `typesafe/jev-1.13-20260917`). Alias `~typesafe/jev-latest` tracks the newest release; pin `jev-1.13` for stability.
- **Context length:** 32,000 tokens — covers the `state` object plus all `questions` combined.
- **Pricing:** **CONFIRMED** — $0.042 / 1M input tokens, **$0 / 1M output tokens** (input-only billing; output tokens are free). Every response includes `usage.cost` in USD for that exact call. Live smoke-test call cost $0.000018396 for 438 input / 58 output tokens.
- **Latency:** P50 ≈ 0.22s (best provider, TypeSafe is sole provider). Uptime ~100%, availability ~99.91% (3-day window at fetch time).
- **Language support (Chinese/Japanese):** **Not explicitly documented anywhere in the tutorial, hub page, model page, or API reference.** No claim of multilingual support, no claim restricting it to English either. State/instructions/criteria are plain JSON string fields with no language parameter. A live smoke test (see §5) sent a Chinese sentence in `state` plus English instructions/criteria and got a coherent, well-calibrated response (noul 0.96 for a correct translation; choice "casual" 0.87 for a casual-register sentence), suggesting Chinese input is at least handled, but this is a single anecdotal test, not documented guaranteed support. Treat as an open question if language coverage is load-bearing for a decision.

## 2. Modes ("primitives")

All three are declared per-question inside one `questions` object in a single request; every question is evaluated **in parallel** against the same `state` and **cannot see each other's answers**. A single request can mix multiple questions of different types.

Endpoint (all modes): `POST https://openrouter.ai/api/alpha/decisions`
Headers: `Authorization: Bearer <OPENROUTER_API_KEY>`, `Content-Type: application/json`

Common request shape:
```json
{
  "model": "typesafe/jev-1.13",
  "state": { "<arbitrary-key>": "<string or JSON value>", "...": "..." },
  "questions": {
    "<question_key>": {
      "type": "noul | choice | score",
      "instructions": "<the question, in plain language, referring to fields in state>",
      "criteria": { "...": "..." }   // shape depends on type, see below
    }
  }
}
```
Note the field is **`instructions`**, not "prompt" or "system prompt" — there is no separate system-prompt convention; you phrase the question directly in `instructions` and put option/threshold definitions in `criteria`. `state` holds the actual content being judged (e.g. `ticket`, `sentence_zh`) — `instructions` should refer to it ("the post", "the customer", "sentence_zh") rather than repeating the text.

### 2a. Yes/No mode — `type: "noul"`
Answers a yes/no question and returns the probability of "yes".

Request field for this question:
```json
"is_bug": {
  "type": "noul",
  "instructions": "Is the customer reporting a software defect?",
  "criteria": {
    "true": "The customer describes broken or unexpected product behavior.",
    "false": "The customer is asking a question or requesting a feature."
  }
}
```
`criteria.true` / `criteria.false` are descriptive anchors for what counts as yes/false — not required to be present per the schema (marked optional-ish in practice) but shown in every example; include them for calibration.

Response for this question:
```json
"is_bug": { "type": "noul", "noul": 0.96 }
```
- `noul` is a float in `[0, 1]` = P(yes). 0.96 ≈ confidently yes; ~0.5 = genuinely uncertain (NOT "medium" — there is no ordinal meaning).
- No separate `confidence` field is emitted for `noul` (confidence is only on `choice`/`score`).

### 2b. Choice mode — `type: "choice"`
Picks one option from a defined set and returns a probability per option.

Request field:
```json
"team": {
  "type": "choice",
  "instructions": "Which team should own this ticket?",
  "criteria": {
    "payments": "Checkout, billing, or payment processing issues.",
    "frontend": "Rendering, layout, or browser compatibility issues.",
    "account": "Login, permissions, or profile issues."
  }
}
```
- **The option set IS the key-set of `criteria`** (an object, not an array) — there is no separate `options` field. Each key is the option's identifier (returned verbatim in `choice`); each value is a plain-language description of when that option applies.
- Choice always picks exactly one of the listed keys — if your categories don't exhaustively cover the input space, add an explicit `"other"` key to `criteria` yourself (the docs' classification cookbook does this).

Response field:
```json
"team": {
  "type": "choice",
  "choice": "payments",
  "confidence": 0.67,
  "probabilities": { "payments": 0.78, "frontend": 0.22, "account": 0 }
}
```
- `choice` — the selected option key (highest-probability option).
- `probabilities` — a probability per option key from `criteria`, summing to ~1.
- `confidence` — a scalar summarizing how concentrated the distribution is (high = one option dominates).

### 2c. Score mode — `type: "score"` (bonus third primitive, ordered scale)
Places input on an ordered scale defined by an array (not object) of level descriptions, and returns a probability-weighted position.

Request:
```json
"urgency": {
  "type": "score",
  "instructions": "How urgent is this ticket?",
  "criteria": [
    "Can wait for the next release",
    "Should be fixed this week",
    "Blocking revenue right now"
  ]
}
```
`criteria` here is an **array** — levels are implicitly indexed 0, 1, 2, ... in order.

Response:
```json
"urgency": {
  "type": "score",
  "score": 1.99,
  "confidence": 0.99,
  "probabilities": { "0": 0, "1": 0, "2": 0.99 },
  "legend": {
    "0": "Can wait for the next release",
    "1": "Should be fixed this week",
    "2": "Blocking revenue right now"
  }
}
```
- `score` — probability-weighted position on the 0..N-1 scale (float, e.g. 1.99 ≈ almost entirely level 2).
- `probabilities` — probability mass per index (string keys "0","1","2",...).
- `legend` — echoes your level descriptions keyed by index, for convenience.

### Full example request/response (verbatim, from the tutorial — combines all 3 modes in one call)

Request:
```bash
curl --request POST \
  --url https://openrouter.ai/api/alpha/decisions \
  --header "Authorization: Bearer $OPENROUTER_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "typesafe/jev-1.13",
    "state": {
      "customer_tier": "enterprise",
      "ticket": "My checkout page shows a blank screen after I click Pay. I have tried two browsers."
    },
    "questions": {
      "is_bug": {
        "type": "noul",
        "instructions": "Is the customer reporting a software defect?",
        "criteria": {
          "true": "The customer describes broken or unexpected product behavior.",
          "false": "The customer is asking a question or requesting a feature."
        }
      },
      "team": {
        "type": "choice",
        "instructions": "Which team should own this ticket?",
        "criteria": {
          "payments": "Checkout, billing, or payment processing issues.",
          "frontend": "Rendering, layout, or browser compatibility issues.",
          "account": "Login, permissions, or profile issues."
        }
      },
      "urgency": {
        "type": "score",
        "instructions": "How urgent is this ticket?",
        "criteria": [
          "Can wait for the next release",
          "Should be fixed this week",
          "Blocking revenue right now"
        ]
      }
    }
  }'
```

Response:
```json
{
  "id": "gen-dec-1790015143-AIaTutprXsJ5EwohRSjb",
  "model": "typesafe/jev-1.13-20260917",
  "provider": "TypeSafe",
  "answers": {
    "is_bug": { "type": "noul", "noul": 0.96 },
    "team": {
      "type": "choice",
      "choice": "payments",
      "confidence": 0.67,
      "probabilities": { "payments": 0.78, "frontend": 0.22, "account": 0 }
    },
    "urgency": {
      "type": "score",
      "score": 1.99,
      "confidence": 0.99,
      "probabilities": { "0": 0, "1": 0, "2": 1 },
      "legend": {
        "0": "Can wait for the next release",
        "1": "Should be fixed this week",
        "2": "Blocking revenue right now"
      }
    }
  },
  "usage": { "input_tokens": 476, "output_tokens": 70, "cost": 0.000019992 }
}
```
Top-level response fields: `id`, `model` (dated snapshot actually served), `provider` (always `"TypeSafe"` currently — sole provider), `answers` (keyed by your question keys), `usage.{input_tokens,output_tokens,cost}`.

## 3. Limits, caveats, batching, rate limits

- **Max options in choice mode:** **Not documented / no explicit numeric limit found** in any fetched page. Options are just object keys in `criteria`; no schema constraint on count was stated.
- **Non-English questions/options:** **Not documented either way.** No language restriction is stated. See §1 — smoke-tested informally with Chinese `state` content and it worked, but this is not an official guarantee.
- **Batching:** Not a single-call batch-array feature. Instead: "put every independent question about the same state in one request" (multiple `questions` keys = parallel answers in one call, sharing one `state`/token cost). For classifying **many separate items**, the docs' pattern is one Decisions request **per item**, run **concurrently** with your own worker pool + backoff (the classification cookbook's `runBatch` helper): fixed number of concurrent workers pulling from a queue, `withRetry` handling transient errors, all workers pausing/resuming together on rate-limit signals.
- **Rate limits / transient errors:**
  - `429` = rate limited (retryable, honor `Retry-After` header).
  - `402` has two meanings: (a) transient — in-flight spending budget exhausted, body has `limit_source: "openrouter_in_flight_budget"`, retry after `Retry-After`; (b) non-transient — credits or key limit exhausted (permanent failure for that item).
  - Full documented status code set: `200, 400, 401, 402, 403, 404, 413, 429, 500, 502, 503, 524, 529`.
  - Recommended pattern: treat network errors, 429, and 5xx as retryable; treat other 4xx as fatal for that item.
- **Latency:** ~0.22s P50 per call (single provider, TypeSafe) — fast enough for per-request/per-item synchronous use, but at scale (thousands of items) you must parallelize with your own concurrency-limited batch runner, not expect a native multi-item batch endpoint.
- **No reasoning/explanation output ever** — if you need a justification, either (a) use Jev for the decision then a separate chat model to explain it, or (b) route low-confidence cases to a human/chat model.
- Sole provider is TypeSafe itself (not routed across multiple third-party providers like typical OpenRouter models).

## 4. Rubric design / calibration / prompt-style guidance

- Write each **`noul`** instruction as a direct yes/no question about the item in `state` (not the item text — refer to it, e.g. "the post", "the customer").
- Put **category/option definitions in `criteria`**, not crammed into `instructions` — `instructions` should be the bare question, `criteria` carries the rubric text per option/level.
- For **`choice`**, if your option set may not be exhaustive, add an explicit `"other"` key with its own criteria description — Jev will always pick one of the listed keys, never invent a new one.
- `confidence` (on `choice`/`score`) and `usage.cost` are effectively optional/nullable in some SDK-side schemas (the cookbook's Zod schema marks them optional) — code consuming responses should handle their absence (e.g., route missing-confidence answers to manual review) rather than assume they're always present.
- For threshold-based decisions (e.g., "is this a bug" gating an action), pick per-tag/per-question thresholds from a small human-labeled calibration sample rather than assuming 0.5 is universally correct — this is the documented workflow in the classification cookbook (measure on a labeled sample, choose thresholds, then compute a cost budget from real usage figures).
- Further conceptual/calibration guidance is deferred to external TypeSafe docs (`docs.typesafe.ai/primitives`, `docs.typesafe.ai/confidence`) which were referenced but not directly fetched in this pass.

## 5. Live smoke test (performed 2026-09-26)

Request sent (key redacted, read from `WebApp/.env`'s `OPENROUTER_API_KEY`):
```json
POST https://openrouter.ai/api/alpha/decisions
{
  "model": "typesafe/jev-1.13",
  "state": {
    "sentence_zh": "我今天很开心，因为天气很好。",
    "translation": "I am very happy today because the weather is nice."
  },
  "questions": {
    "is_correct": {
      "type": "noul",
      "instructions": "Does the translation accurately convey the meaning of sentence_zh?",
      "criteria": {
        "true": "The translation is an accurate rendering of the Chinese sentence.",
        "false": "The translation misses or distorts the meaning."
      }
    },
    "register": {
      "type": "choice",
      "instructions": "What register/tone does sentence_zh use?",
      "criteria": {
        "casual": "Informal, conversational tone.",
        "formal": "Formal or written tone.",
        "neutral": "Neither clearly casual nor formal."
      }
    }
  }
}
```

Raw response received (HTTP 200, key never present in response):
```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "is_correct": { "type": "noul", "noul": 0.96 },
    "register": {
      "type": "choice",
      "choice": "casual",
      "probabilities": { "neutral": 0.13, "formal": 0, "casual": 0.87 },
      "confidence": 0.8
    }
  },
  "usage": { "input_tokens": 438, "output_tokens": 58, "cost": 0.000018396 },
  "id": "gen-dec-1790397692-rBTrISREBD3BHAMGN3mT",
  "provider": "TypeSafe"
}
```

**Result:** Format confirmed working exactly as documented — `noul` yes/no probability and `choice` selection + per-option `probabilities` + `confidence` both returned correctly, cost matches the $0.042/M-input / $0-output pricing model (438 input tokens × $0.042/1M ≈ $0.0000184, matches `usage.cost` of $0.000018396), and Chinese-language content in `state` was handled without any apparent issue (register correctly identified as "casual" with 0.87 probability, translation correctly judged accurate with 0.96 probability).
