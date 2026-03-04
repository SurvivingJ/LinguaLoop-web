# TASKLIST: Auto-Scaling Difficulty for Custom Arithmetic Drill

> **Scope:** Custom arithmetic drill only (+, -, ×, ÷). Financial and poker drills are NOT affected.
>
> **Concept:** Tag every arithmetic problem with structural metadata (carry count, trap facts, scale, etc). Track per-tag accuracy on the frontend. When refetching problems, send weak tags to the backend so it generates 50% targeted problems.

---

## Task 1: Add `TagExtractor` class to `math_engine.py`

**File:** `math_engine.py`
**Location:** Insert BEFORE the `ProblemGenerator` class (after `import uuid`, around line 3)
**Dependencies:** None

Add a new `import re` at the top of the file if not already present.

### Class: `TagExtractor`

```python
class TagExtractor:
    """Extracts deterministic tags from an arithmetic problem's equation and answer."""
```

### Method: `TagExtractor.extract(equation: str, answer: int) -> list[str]`

This is the only public method. It parses the equation string, identifies operands and operators, and returns a deduplicated list of tag strings.

**Parsing approach:**
- Operators in equations use Unicode: `+`, `-`, `×` (`\u00d7`), `÷` (`\u00f7`)
- Extract all integers: `numbers = [int(n) for n in re.findall(r'\d+', equation)]`
- Extract operators: `operators = re.findall(r'[+\-×÷]', equation)`
- For mixed expressions (2-3 operators), tag each operation found but only compute carry/bridge/scale for the first two operands

**Tag extraction logic (implement in this order):**

#### 1. Operation tags
For each unique operator found, emit:
- `+` → `"op:add"`
- `-` → `"op:sub"`
- `×` → `"op:mul"`
- `÷` → `"op:div"`

#### 2. Scale tags (only if exactly 2 operands and 1 operator)
Based on digit count of the two operands:
```python
da, db = len(str(numbers[0])), len(str(numbers[1]))
if max(da, db) >= 4:
    tag = "scale:big"
else:
    tag = f"scale:{da}x{db}"  # e.g., "scale:2x1", "scale:2x2"
```
Normalize: `scale:1x2` and `scale:2x1` are SEPARATE tags (order matters — `12 + 5` is different from `5 + 12` visually).

#### 3. Carry/borrow tags (addition and subtraction only, 2-operand problems)
Implement a helper `_count_carries(a, b)`:
```python
@staticmethod
def _count_carries(a: int, b: int) -> int:
    carry = 0
    count = 0
    while a > 0 or b > 0:
        s = (a % 10) + (b % 10) + carry
        if s >= 10:
            count += 1
            carry = 1
        else:
            carry = 0
        a //= 10
        b //= 10
    return count
```
For addition: count carries directly.
For subtraction: count borrows (where digit_a < digit_b after accounting for prior borrows). Use similar column-by-column simulation.

Map count to tag:
- 0 → `"carry:none"`
- 1 → `"carry:once"`
- 2+ → `"carry:multi"`

#### 4. Multiplication table difficulty (multiplication only, 2-operand)
```python
a, b = numbers[0], numbers[1]
if a <= 5 and b <= 5:
    tag = "table:easy"
elif a >= 10 or b >= 10 or (a >= 7 and b >= 7):
    tag = "table:hard"
else:
    tag = "table:mid"
```

#### 5. Division large dividend
If `÷` in operators and `numbers[0] >= 100`: emit `"div:large"`

#### 6. Trap facts (multiplication and division)
Define a class constant:
```python
TRAPS = {
    frozenset({7, 8}): 'trap:7x8',
    frozenset({6, 7}): 'trap:6x7',
    frozenset({8, 9}): 'trap:8x9',
    frozenset({6, 9}): 'trap:6x9',
}
```
For multiplication: check if `frozenset({a, b})` matches any key.
For division: the dividend is `a*b` where `b` is the divisor. Check if `frozenset({answer, divisor})` matches — since `answer = dividend / divisor`, the original factors were `(answer, divisor)`.

#### 7. Bridge tags (addition and subtraction, 2-operand)
```python
if '+'  in operators:
    result = a + b
    if (a // 100) != (result // 100):
        emit "bridge:hundreds"
    elif (a // 10) != (result // 10):
        emit "bridge:tens"
# For subtraction, check if crossing downward
```

#### 8. Near-round operand
For each operand: if `num % 10 in (1, 9)` and `num > 1`, emit `"near:round"` (only once, not per operand).

#### 9. Borrow-across-zero (subtraction only)
If subtracting and the larger operand has a `0` in a middle/ones digit that requires borrowing through: emit `"borrow:across-zero"`. Detection: check if any digit in `a` is `0` and the corresponding digit in `b` is non-zero.

**Return:** `list(set(tags))` — deduplicated.

### Verification for Task 1
Run in Python shell:
```python
from math_engine import TagExtractor
print(TagExtractor.extract("47 + 6", 53))
# Should include: op:add, scale:2x1, carry:once, bridge:tens
print(TagExtractor.extract("7 × 8", 56))
# Should include: op:mul, scale:1x1, table:mid, trap:7x8
print(TagExtractor.extract("103 - 7", 96))
# Should include: op:sub, scale:3x1, borrow:across-zero
```

---

## Task 2: Add `tags` field to `get_problem_custom()` return value

**File:** `math_engine.py`
**Location:** `ProblemGenerator.get_problem_custom()` method, around line 533
**Dependencies:** Task 1

### Change

Currently returns:
```python
return {
    'id': str(uuid.uuid4()),
    'equation': equation,
    'answer': int(answer),
    'difficulty_rating': 0
}
```

Change to:
```python
return {
    'id': str(uuid.uuid4()),
    'equation': equation,
    'answer': int(answer),
    'difficulty_rating': 0,
    'tags': TagExtractor.extract(equation, int(answer))
}
```

### Verification for Task 2
```python
from math_engine import ProblemGenerator
p = ProblemGenerator.get_problem_custom({'operations': ['addition'], 'mix': False, 'min_digits': 1, 'max_digits': 2})
print(p)  # Should have 'tags' key with list of strings
assert 'tags' in p
assert isinstance(p['tags'], list)
assert 'op:add' in p['tags']
```

---

## Task 3: Add `DrillGenerator` class to `math_engine.py`

**File:** `math_engine.py`
**Location:** After `TagExtractor`, before `ProblemGenerator`
**Dependencies:** Task 1

### Class: `DrillGenerator`

```python
class DrillGenerator:
    """Generates arithmetic problems targeting specific weakness tags,
    while respecting the user's configured operations and digit range."""
```

### Method: `DrillGenerator.generate_targeted(focus_tags, options) -> dict`

**Parameters:**
- `focus_tags`: `list[str]` — e.g., `["carry:multi", "trap:7x8"]`
- `options`: `dict` — `{operations, mix, min_digits, max_digits}` (user's config)

**Returns:** Problem dict with `id`, `equation`, `answer`, `difficulty_rating`, `tags`

**Strategy:**
1. Filter `focus_tags` to only those achievable within the user's config:
   - `carry:*` and `bridge:*` require `addition` or `subtraction` in operations
   - `trap:*` and `table:*` require `multiplication` in operations
   - `div:large` requires `division` in operations
   - `scale:2x2` requires `max_digits >= 2`
2. Pick a random achievable focus tag
3. Call the appropriate builder method (see below)
4. Verify the generated problem contains the target tag using `TagExtractor.extract()`
5. If verification fails after 20 attempts, fall back to `ProblemGenerator.get_problem_custom(options)`

### Builder methods (private, static)

Each returns `(equation: str, answer: int)`.

#### `_build_carry_once(min_d, max_d)`
Generate addition where ones column carries but tens column doesn't:
```python
a = ProblemGenerator._random_operand(min_d, max_d)
ones_a = a % 10
if ones_a < 2:
    ones_a = random.randint(5, 9)
    a = (a // 10) * 10 + ones_a
b_ones = random.randint(10 - ones_a, 9)
b_tens = random.randint(0, 3)  # keep tens small to avoid second carry
b = b_tens * 10 + b_ones
# Clamp b to digit range
```

#### `_build_carry_multi(min_d, max_d)`
Generate addition where both ones AND tens columns carry:
```python
# Both ones digits sum >= 10, both tens digits sum >= 10 (after carry)
a = random.randint(55, 99)  # high digits in both positions
b = random.randint(55, 99)
```
Adjust to fit within `min_d`/`max_d`.

#### `_build_trap(trap_tag, min_d, max_d)`
Extract the two factors from the tag name (e.g., `trap:7x8` → 7, 8).
Only works if `multiplication` is allowed AND `min_d <= 1` (since 7 and 8 are single-digit).
Return `f"{a} × {b}", a * b`.
For variety, randomly swap operand order.

#### `_build_bridge_tens(min_d, max_d)`
Pick `a` with ones digit 7-9, pick `b` so that `a + b` crosses the next ten:
```python
a = ProblemGenerator._random_operand(min_d, max_d)
ones_a = a % 10
if ones_a < 5:
    a = (a // 10) * 10 + random.randint(7, 9)
b = random.randint(10 - (a % 10) + 1, 9)
```

#### `_build_table_hard(min_d, max_d)`
Generate multiplication with at least one factor in 7-12:
```python
a = random.randint(7, 12)
b = random.randint(2, 12)
```

#### `_build_borrow_across_zero(min_d, max_d)`
Generate subtraction from a number containing a 0 digit:
```python
a = random.choice([100, 101, 102, 103, 200, 201, 300, 400, 500])
b = random.randint(1, min(a - 1, 9))
```
Adjust for digit range.

#### `_build_div_large(min_d, max_d)`
Generate division with dividend ≥ 100:
```python
divisor = ProblemGenerator._random_operand(min_d, max_d)
quotient = ProblemGenerator._random_operand(min_d, max_d)
dividend = divisor * quotient
# Ensure dividend >= 100; if not, scale up
```

**Fallback:** For any tag that can't be matched (e.g., `near:round` — not worth a dedicated builder), or if the builder repeatedly fails verification, call `ProblemGenerator.get_problem_custom(options)` as fallback.

### Verification for Task 3
```python
from math_engine import DrillGenerator, TagExtractor
opts = {'operations': ['addition', 'multiplication'], 'mix': False, 'min_digits': 1, 'max_digits': 2}

# Test targeted generation
for _ in range(20):
    p = DrillGenerator.generate_targeted(['carry:multi'], opts)
    assert 'tags' in p
    print(p['equation'], p['tags'])
    # Most should contain 'carry:multi'

for _ in range(20):
    p = DrillGenerator.generate_targeted(['trap:7x8'], opts)
    print(p['equation'], p['tags'])
    # Most should contain 'trap:7x8'
```

---

## Task 4: Modify `get_batch_custom()` to accept `focus_tags`

**File:** `math_engine.py`
**Location:** `ProblemGenerator.get_batch_custom()`, around line 559
**Dependencies:** Tasks 2, 3

### Change

Current:
```python
@staticmethod
def get_batch_custom(count, options):
    """Generate a batch of problems for custom drill options."""
    return [ProblemGenerator.get_problem_custom(options) for _ in range(count)]
```

New:
```python
@staticmethod
def get_batch_custom(count, options, focus_tags=None):
    """Generate a batch of problems for custom drill options.

    If focus_tags provided: 50% targeted problems (via DrillGenerator),
    50% standard problems (via get_problem_custom). All shuffled.
    """
    if not focus_tags:
        return [ProblemGenerator.get_problem_custom(options) for _ in range(count)]

    targeted_count = count // 2
    standard_count = count - targeted_count

    problems = []
    for _ in range(targeted_count):
        problems.append(DrillGenerator.generate_targeted(focus_tags, options))
    for _ in range(standard_count):
        problems.append(ProblemGenerator.get_problem_custom(options))

    random.shuffle(problems)
    return problems
```

### Verification for Task 4
```python
from math_engine import ProblemGenerator
opts = {'operations': ['addition'], 'mix': False, 'min_digits': 1, 'max_digits': 2}

# Without focus_tags — standard behavior
batch1 = ProblemGenerator.get_batch_custom(10, opts)
assert len(batch1) == 10
assert all('tags' in p for p in batch1)

# With focus_tags — should have targeted problems
batch2 = ProblemGenerator.get_batch_custom(10, opts, focus_tags=['carry:multi'])
assert len(batch2) == 10
carry_multi_count = sum(1 for p in batch2 if 'carry:multi' in p['tags'])
print(f"Targeted: {carry_multi_count}/10 contain carry:multi")
# Expect roughly 5 (the targeted half, though not all may verify)
```

---

## Task 5: Pass `focus_tags` through `app.py`

**File:** `app.py`
**Location:** Line 76-77 (the `elif options is not None:` branch)
**Dependencies:** Task 4

### Change

Current:
```python
elif options is not None:
    # Custom drill mode (user-configured operations/digits)
    problems = generator.get_batch_custom(count, options)
```

New:
```python
elif options is not None:
    # Custom drill mode (user-configured operations/digits)
    focus_tags = data.get('focus_tags', None)
    problems = generator.get_batch_custom(count, options, focus_tags=focus_tags)
```

### Verification for Task 5
Start the Flask server. Use curl or browser console:
```bash
curl -X POST http://localhost:5000/api/batch \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "options": {"operations": ["addition"], "mix": false, "min_digits": 1, "max_digits": 2}}'
# Response should include "tags" arrays on each problem

curl -X POST http://localhost:5000/api/batch \
  -H "Content-Type: application/json" \
  -d '{"count": 10, "options": {"operations": ["addition"], "mix": false, "min_digits": 1, "max_digits": 2}, "focus_tags": ["carry:multi"]}'
# Response should have ~50% problems containing "carry:multi" tag
```

---

## Task 6: Create `static/js/session-coach.js`

**File:** `static/js/session-coach.js` **(NEW FILE)**
**Dependencies:** None (pure frontend, no backend dependency)

### Class: `SessionCoach`

```javascript
/**
 * SessionCoach — Tracks per-tag performance for the custom arithmetic drill.
 * Performs dual-layer analysis (recent 10 + full session) every 10 problems.
 * Outputs focus_tags for the next batch request.
 *
 * Usage:
 *   const coach = new SessionCoach();
 *   coach.reset();                         // Call when starting a new drill
 *   coach.record(tags, correct, timeMs);   // Call after each answer
 *   const tags = coach.getFocusTags();     // Call when fetching next batch
 */
class SessionCoach {
    constructor() {
        this.history = [];       // All {tags, correct, timeMs} this session
        this.focusTags = [];     // Current weakness tags (up to 3)
        this.analysisInterval = 10;
    }
```

### Method: `reset()`
Clear `history` and `focusTags`. Call at the start of each drill session.

### Method: `record(tags, correct, timeMs)`
Push `{tags, correct, timeMs}` to `this.history`.
If `this.history.length % this.analysisInterval === 0`, call `this._analyze()`.

### Method: `getFocusTags()`
Return `this.focusTags` (array, possibly empty).

### Method: `_analyze()` (private)
Dual-layer analysis:
1. Compute tag stats for the **last 10 problems** (`recentStats`)
2. Compute tag stats for the **entire session** (`sessionStats`)
3. Apply decision rules to produce `this.focusTags`
4. Log analysis to `console.log` for debugging (prefixed with `[Coach]`)

### Method: `_computeTagStats(records)` (private)
Input: array of `{tags, correct, timeMs}` records
Output: `Map<string, {attempts, errors, errorRate, avgTimeMs}>`

For each record, for each tag in `record.tags`:
- Increment `attempts`
- If `!record.correct`, increment `errors`
- Accumulate `totalTimeMs`

After iterating, compute `errorRate = errors / attempts` and `avgTimeMs = totalTimeMs / attempts`.

### Decision Rules (in `_analyze`)

Apply rules in priority order. Collect candidate tags with priority scores, then take the top 3.

**Rule 1 — Recent crisis (priority 4):**
Any tag in `recentStats` with `attempts >= 2` AND `errorRate >= 0.5`.
These are things the user is getting wrong RIGHT NOW.

**Rule 2 — Persistent weakness (priority 3):**
Any tag in `sessionStats` with `attempts >= 5` AND `errorRate >= 0.4`.
These are consistent trouble spots across the whole session.

**Rule 3 — Slow + error-prone (priority 2):**
Any tag in `sessionStats` where `avgTimeMs` is in the **top 25th percentile** of all tag average times AND `errorRate >= 0.3`.
These are both slow and inaccurate — struggling.

**Rule 4 — Regression (priority 1):**
Any tag where `recentStats.avgTimeMs >= 1.5 × sessionStats.avgTimeMs` for the same tag, AND session `attempts >= 3`.
The user is getting SLOWER on this tag — possible fatigue or confusion.

**Scoring:** Each rule adds its priority value to the tag's score. Sort by score descending. Take top 3 tags. Store in `this.focusTags`.

**If no rules fire:** `this.focusTags = []` (no targeting — backend returns standard problems).

### Helper: `_percentile(arr, n)` (private)
```javascript
_percentile(arr, n) {
    if (arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const idx = Math.ceil((n / 100) * sorted.length) - 1;
    return sorted[Math.max(0, idx)];
}
```

### Console logging format
```
[Coach] Analysis at problem 10:
[Coach]   Recent (last 10): 7/10 correct, avg 3.2s
[Coach]   Session (all 10): 7/10 correct, avg 3.2s
[Coach]   Weaknesses: carry:multi (score 4), trap:7x8 (score 3)
[Coach]   Focus tags: ["carry:multi", "trap:7x8"]
```

### Verification for Task 6
Open browser console. Create instance and test manually:
```javascript
const coach = new SessionCoach();
coach.reset();
// Simulate 10 problems
for (let i = 0; i < 10; i++) {
    coach.record(['op:add', 'carry:multi'], i < 3, 4000); // 3 correct, 7 wrong
}
console.log(coach.getFocusTags()); // Should include "carry:multi"
```

---

## Task 7: Modify `game-manager.js` — add `fetchBatchCustom` and update `loadCustomDrill`

**File:** `static/js/game-manager.js`
**Dependencies:** Task 5 (backend must accept focus_tags)

### 7A. Update `loadCustomDrill()` signature

Current (line 201):
```javascript
async loadCustomDrill(count, options) {
    const problems = await this.fetchBatch(count, options);
```

New:
```javascript
async loadCustomDrill(count, options, focusTags = null) {
    const problems = await this._fetchBatchCustom(count, options, focusTags);
```

The rest of the method body stays the same (concat to queue, return length).

### 7B. Add `_fetchBatchCustom()` method

Insert after `loadCustomDrill()`. This is a new private method that sends both `options` AND `focus_tags` in the request body.

```javascript
/**
 * Fetch custom drill batch with optional focus_tags for adaptive targeting.
 * @param {number} count
 * @param {object} options - {operations, mix, min_digits, max_digits}
 * @param {string[]|null} focusTags - Weakness tags from SessionCoach
 */
async _fetchBatchCustom(count, options, focusTags = null) {
    try {
        const body = { count, options };
        if (focusTags && focusTags.length > 0) {
            body.focus_tags = focusTags;
        }
        const response = await fetch(`${this.apiBase}/api/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!response.ok) throw new Error('API request failed');
        const data = await response.json();
        return data.problems;
    } catch (error) {
        console.error('Error fetching custom batch:', error);
        return Array.from({length: count}, () => this.generateFallbackProblem());
    }
}
```

### Verification for Task 7
Temporarily add `console.log(body)` inside `_fetchBatchCustom` to verify request body shape. Start a drill, observe the first fetch (no focus_tags), then after 10 problems, observe the refetch (should include focus_tags if coach detected weaknesses).

---

## Task 8: Integrate `SessionCoach` into `daily-drill.js`

**File:** `static/js/daily-drill.js`
**Dependencies:** Tasks 6, 7

### 8A. Add coach property in constructor

After line 20 (`this.fetching = false;`), add:
```javascript
this.coach = new SessionCoach();
```

### 8B. Reset coach in `startDrill()`

After line 198 (`this.bestStreak = 0;`), add:
```javascript
this.coach.reset();
```

### 8C. Record answers with coach in `handleAnswer()`

The key change: capture `tags` and `timeElapsed` from the current problem BEFORE calling `loadNextProblem()` (which overwrites `gameManager.currentProblem`).

Replace the `handleAnswer` method body (lines 275-299) with:

```javascript
handleAnswer(userAnswer) {
    if (!this.isActive) return;

    const result = gameManager.checkAnswer(userAnswer);

    // Capture tags before currentProblem gets overwritten
    const tags = gameManager.currentProblem?.tags || [];
    const timeMs = result.timeElapsed * 1000;

    // Record with coach for adaptive analysis
    this.coach.record(tags, result.correct, timeMs);

    if (result.correct) {
        this.correctAnswers++;
        this.currentStreak++;
        if (this.currentStreak > this.bestStreak) {
            this.bestStreak = this.currentStreak;
        }
        this.showFeedback('\u2713', 'var(--neon-green)');
    } else {
        this.wrongAnswers++;
        this.currentStreak = 0;
        this.showFeedback(`\u2717 ${result.correctAnswer}`, 'var(--alert-red)');
    }

    this.updateStats();
    this.inputHandler.clear();
    this.loadNextProblem();
    this.inputHandler.focus();
}
```

### 8D. Pass focus_tags in pre-fetch calls

In `loadNextProblem()`, replace the pre-fetch block (lines 252-257):

Current:
```javascript
if (gameManager.problemQueue.length < 5 && !this.fetching) {
    this.fetching = true;
    gameManager.loadCustomDrill(50, this.getOptions()).then(() => {
        this.fetching = false;
    });
}
```

New:
```javascript
if (gameManager.problemQueue.length < 5 && !this.fetching) {
    this.fetching = true;
    const focusTags = this.coach.getFocusTags();
    gameManager.loadCustomDrill(50, this.getOptions(), focusTags).then(() => {
        this.fetching = false;
    });
}
```

Also update `refetchAndContinue()` (line 265):

Current:
```javascript
await gameManager.loadCustomDrill(50, this.getOptions());
```

New:
```javascript
const focusTags = this.coach.getFocusTags();
await gameManager.loadCustomDrill(50, this.getOptions(), focusTags);
```

The initial load in `startDrill()` (line 211) stays as-is with no focus_tags — the coach has no data yet:
```javascript
await gameManager.loadCustomDrill(50, this.getOptions());
// No focusTags on first load — coach hasn't analyzed anything yet
```

### Verification for Task 8
1. Start custom drill with addition, 1-2 digits
2. Open browser DevTools console
3. Answer 10 problems (deliberately get some wrong)
4. Watch for `[Coach] Analysis at problem 10:` in console
5. Continue until queue refetch triggers (~problem 45-50)
6. Check Network tab — the refetch POST body should include `focus_tags` array

---

## Task 9: Add `session-coach.js` script tag to `index.html`

**File:** `templates/index.html`
**Dependencies:** Task 6

### Change

Find the script tags section (near the bottom of the file). The load order must be:
1. `storage-manager.js`
2. `screen-manager.js`
3. `input-handler.js`
4. `game-manager.js`
5. **`session-coach.js`** ← INSERT HERE
6. `daily-drill.js`
7. `financial-drill.js`
8. `poker-drill.js`

`session-coach.js` must load BEFORE `daily-drill.js` because `CustomDrill`'s constructor creates a `new SessionCoach()`.

Add:
```html
<script src="/static/js/session-coach.js"></script>
```

### Verification for Task 9
Load the page. Open console. Type `new SessionCoach()` — should not throw. Type `customDrill.coach` — should be a `SessionCoach` instance.

---

## Task 10: End-to-End Verification

**Dependencies:** All previous tasks

### Test 1: Standard flow (no targeting)
1. Start custom drill with addition only, 1-2 digits
2. Answer 9 problems correctly
3. Verify no `[Coach]` logs yet (analysis fires at 10)
4. Answer problem 10
5. Verify `[Coach] Analysis at problem 10` appears
6. Verify `Focus tags: []` (all correct = no weaknesses)

### Test 2: Weakness detection
1. Start custom drill with addition + multiplication, 1-2 digits
2. Answer all addition problems correctly, all multiplication wrong
3. After problem 10, verify coach detects `op:mul` or `table:*` or `trap:*` as weak
4. Continue to problem ~45 (queue refetch)
5. Check Network tab: request body should include `focus_tags`
6. Check next batch: should contain more multiplication problems than usual

### Test 3: Financial/Poker unaffected
1. Start financial drill → verify problems do NOT have `tags` field (they have `explanation`)
2. Start poker drill → verify unaffected
3. Neither should reference `SessionCoach`

### Test 4: Edge cases
1. Start drill, answer 3 problems, press BACK (end drill) → no crash
2. Start drill, answer 10 problems all correct fast → coach should produce empty focus_tags
3. Start drill with only division selected → coach should only flag division-related tags

---

## Implementation Order Summary

| Order | Task | File | Estimated Size |
|-------|------|------|---------------|
| 1 | TagExtractor class | math_engine.py | ~100 lines |
| 2 | Add tags to get_problem_custom | math_engine.py | 1 line |
| 3 | DrillGenerator class | math_engine.py | ~150 lines |
| 4 | Modify get_batch_custom | math_engine.py | ~15 lines |
| 5 | Pass focus_tags in app.py | app.py | 2 lines |
| 6 | Create session-coach.js | static/js/session-coach.js | ~120 lines |
| 7 | Update game-manager.js | static/js/game-manager.js | ~30 lines |
| 8 | Integrate coach in daily-drill.js | static/js/daily-drill.js | ~20 lines changed |
| 9 | Add script tag | templates/index.html | 1 line |
| 10 | End-to-end testing | — | Manual testing |

**Total new code:** ~450 lines across 5 files (1 new, 4 modified)
