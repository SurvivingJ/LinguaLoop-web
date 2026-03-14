# WorkoutOS — Addendum: Programs, Body Weight, Play Mode & Notifications

> This document extends `WorkoutOS_Plan.md` with four new feature areas.
> All additions are designed to slot cleanly into the existing architecture.

---

## A1. Body Weight Tracking

### A1.1 Purpose

Two distinct concepts both called "weight" need separate tracking:

| Concept | What it is | Where stored |
|---|---|---|
| **Body weight** | The user's own mass over time | `data/history/body_weight.csv` |
| **Lift weight increments** | Pre-defined jump sizes per exercise category | `config.py` + exercise schema |

### A1.2 Body Weight Log

**New CSV: `data/history/body_weight.csv`**

```
date, weight_kg, time_of_day, notes
2026-01-01, 82.5, morning, "fasted"
2026-01-08, 82.1, morning, ""
```

- Logged via a quick entry on the Dashboard (a single number field + [Log] button)
- `time_of_day` options: morning / evening / post-workout (affects comparability)
- Best practice: always log at the same time; morning fasted is most consistent

**New route:** `POST /body-weight` — appends a row to `body_weight.csv`

**Analytics page addition:**
- Line chart: body weight over time (rolling 7-day average overlaid)
- Annotate chart with session markers (dot on each workout day) so you can
  visually correlate training load with weight trend

### A1.3 Lift Weight Increment Table

Pre-defined increment sizes are stored in `config.py` and used by the
progression engine when suggesting the next weight. The right increment
depends on exercise category and the user's current strength level.

```python
# config.py — Pre-defined increment table
WEIGHT_INCREMENTS = {
    # (category, level): [conservative_kg, standard_kg, aggressive_kg]
    ("barbell_compound",  "beginner"):     [2.5,  5.0, 10.0],
    ("barbell_compound",  "intermediate"): [2.5,  2.5,  5.0],
    ("barbell_compound",  "advanced"):     [1.25, 2.5,  2.5],
    ("barbell_isolation", "beginner"):     [1.25, 2.5,  5.0],
    ("barbell_isolation", "intermediate"): [1.25, 1.25, 2.5],
    ("dumbbell",          "any"):          [2.0,  2.0,  4.0],
    ("cable",             "any"):          [2.5,  2.5,  5.0],
    ("machine",           "any"):          [2.5,  5.0,  5.0],
    ("bodyweight",        "any"):          [None, None, None],  # rep-based only
}
```

**Increment aggressiveness** is set per-exercise in the exercise schema as
`progression_aggression: "conservative" | "standard" | "aggressive"` (default: standard).

**Suggested increment UI** — in the active session, when the progression engine
recommends a weight change next session, it shows:

> "Next session: try **82.5 kg** (+2.5 kg)"
> [Accept] [Use +1.25 kg instead] [Use +5 kg instead]

The user can override with one tap before confirming end of session.

### A1.4 Body Weight ↔ Strength Relationship (Optional Future Feature)

Store the user's body weight at each session log. Over time, calculate
relative strength ratios (e.g. squat 1RM / body weight) and display them
on the analytics page alongside absolute numbers. This is useful for
tracking progress during a bulk or cut where absolute weight may plateau
but relative strength improves.

---

## A2. Programs

### A2.1 Concept

A **Program** is a multi-week training plan that assigns specific **Workout Plans**
to specific days of the week. Programs enable structured periodisation — you design
the full mesocycle once and the app tracks where you are in it automatically.

```
Program: "6-Day PPL — 8 Weeks"
│
├── Week 1–3 (Accumulation)
│   Mon: Push A    Tue: Pull A    Wed: Legs A
│   Thu: Push B    Fri: Pull B    Sat: Legs B    Sun: Rest
│
├── Week 4 (Deload)
│   Mon: Push A*   Tue: Pull A*   Wed: Legs A*   (−40% volume)
│   Thu–Sun: Rest
│
└── Week 5–8 (Intensification) ...
```

### A2.2 Program Schema (plans.json — new top-level array)

```json
{
  "id": "uuid-v4",
  "name": "6-Day PPL — 8 Weeks",
  "description": "Push/pull/legs twice per week, 8-week mesocycle",
  "goal": "hypertrophy",
  "duration_weeks": 8,
  "deload_weeks": [4, 8],
  "deload_volume_pct": 40,
  "started_at": "2026-01-06",
  "active": true,
  "weeks": [
    {
      "week_number": 1,
      "is_deload": false,
      "days": {
        "monday":    { "plan_id": "uuid-push-a", "label": "Push A" },
        "tuesday":   { "plan_id": "uuid-pull-a", "label": "Pull A" },
        "wednesday": { "plan_id": "uuid-legs-a", "label": "Legs A" },
        "thursday":  { "plan_id": "uuid-push-b", "label": "Push B" },
        "friday":    { "plan_id": "uuid-pull-b", "label": "Pull B" },
        "saturday":  { "plan_id": "uuid-legs-b", "label": "Legs B" },
        "sunday":    null
      }
    }
  ],
  "created_at": "2026-01-01T00:00:00"
}
```

Each `day` entry can be:
- A `plan_id` reference → links to an existing Workout Plan
- `null` → Rest day
- `{ "type": "cardio", "notes": "30min steady state" }` → Unstructured day

**Deload handling**: when `is_deload: true`, the progression engine reduces
all set counts by `deload_volume_pct`% when presenting the session. The
underlying plan is unchanged — deload is applied as a session-time modifier,
not a permanent edit.

### A2.3 Program Builder Page

**New route:** `GET /programs/new` → `programs/builder.html`

Layout: a weekly calendar grid (7 columns × N weeks rows).

```
┌───────┬───────┬───────┬───────┬───────┬───────┬───────┐
│  MON  │  TUE  │  WED  │  THU  │  FRI  │  SAT  │  SUN  │
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│Push A │Pull A │Legs A │Push B │Pull B │Legs B │ REST  │  W1
│Push A │Pull A │Legs A │Push B │Pull B │Legs B │ REST  │  W2
│Push A │Pull A │Legs A │Push B │Pull B │Legs B │ REST  │  W3
│DELOAD │DELOAD │DELOAD │ REST  │ REST  │ REST  │ REST  │  W4
└───────┴───────┴───────┴───────┴───────┴───────┴───────┘
[+ Add Week]
```

- Click a cell → dropdown of existing Workout Plans + [Rest] + [Custom note]
- [Copy week] → duplicates a row (saves re-clicking every cell)
- [Mark as deload] → toggles the whole row to deload styling
- Program duration can be 1–52 weeks
- [+ Add Week] appends a new row, copying the pattern from the previous week by default

### A2.4 Dashboard — Active Program Widget

If a program is marked `active: true`, the dashboard shows a widget:

```
┌──────────────────────────────────────────────┐
│  6-Day PPL — Week 3 of 8                      │
│  ████████████░░░░░░░░░░░░░░░░░  37% complete  │
│                                               │
│  TODAY: Push B  →  [Start Workout]            │
│  Tomorrow: Pull B                             │
│  This week: 4/6 sessions done  ✓✓✓✓○○         │
└──────────────────────────────────────────────┘
```

- "Today" is determined by matching today's weekday to the active week's schedule
- If today's session is already logged, show [View Log] instead of [Start Workout]
- Missed days show a warning but are never auto-skipped (user decides)

### A2.5 Routes

| Route | Description |
|---|---|
| `GET /programs` | List all programs |
| `GET /programs/new` | Program builder |
| `GET /programs/<id>/edit` | Edit program |
| `POST /programs` | Save program |
| `POST /programs/<id>/activate` | Set as active program |
| `GET /programs/<id>` | Program detail + progress view |

---

## A3. Play Mode (Auto-Advance Guided Session)

### A3.1 Concept

Play Mode is a hands-free execution layer on top of the existing active session.
After tapping [▶ Play], the app drives itself — announcing exercises, counting
down rests, and advancing automatically. You just do the work; the app handles all
navigation and timing.

### A3.2 Play Mode UI

The existing session page gets a **mode toggle** at the top:

```
[Manual]  [▶ Play]
```

In Play Mode, the bottom of the screen changes to:

```
┌────────────────────────────────────────────────────┐
│                  BENCH PRESS                       │
│                  Set 3 of 4                        │
│           Target: 8–10 reps @ 82.5 kg             │
│                                                    │
│    [−]  [ 9 reps ]  [+]     [−]  [ 82.5kg ]  [+] │
│                                                    │
│         RPE: ○ ○ ● ○ ○ ○ ○ ○ ○ ○                  │
│                                                    │
│         [ ✓  DONE — auto-advance in 3s ]          │
│                        ███░                        │
├────────────────────────────────────────────────────┤
│  REST  01:30  ██████████████░░░░░░░░               │
│  AUTO-ADVANCING to DB Row in 00:05                 │
│                          [ II PAUSE ]              │
└────────────────────────────────────────────────────┘
```

### A3.3 Play Mode Behaviour

**Set completion auto-advance:**
- After tapping [✓ Done], a 3-second grace countdown starts
- The reps/weight/RPE are locked in after 3s and the rest timer begins
- The grace period lets you correct a mis-tap without penalty
- [Cancel] button available during the 3s grace window

**Rest timer auto-advance:**
- When the rest timer hits 0:00, the next set/exercise loads automatically
- A 5-second "buffer" is added before advancing (prevents being rushed off
  the previous exercise — configurable in settings: 0–10 seconds)
- A prominent visual countdown ("Next: DB Row in 5...4...3...") is displayed

**Pause / Resume:**
- [II Pause] freezes both timers and disables auto-advance
- Tap again to resume — timers continue from where they paused
- Physical phone lock-screen pauses automatically (via Page Visibility API)

**Screen Wake Lock:**
- Play Mode activates the browser `WakeLock API` to prevent the screen from
  sleeping mid-workout
- Falls back gracefully if the browser doesn't support it (shows a warning)

```javascript
// active_session.js
async function enableWakeLock() {
    if ('wakeLock' in navigator) {
        wakeLockRef = await navigator.wakeLock.request('screen');
    }
}
```

**Voice Announcements (Web Speech API):**
- Before each set: *"Bench Press. Set 3 of 4. Target 8 to 10 reps at 82 point 5 kilograms."*
- At rest end: *"Rest complete. Starting DB Row."*
- At workout end: *"Workout complete. Great work."*
- Voice is enabled by default in Play Mode; toggleable in settings
- Uses `window.speechSynthesis` — no audio files needed, works offline

```javascript
function announce(text) {
    if (!settings.voiceEnabled) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}
```

### A3.4 Manual Mode vs Play Mode Comparison

| Behaviour | Manual Mode | Play Mode |
|---|---|---|
| Advance to next set | Tap [Complete Set] | Auto after rest timer + buffer |
| Voice announcements | Off | On (toggleable) |
| Screen wake lock | Off | On |
| Timer auto-start | Yes (on set complete) | Yes |
| RPE input | Required before advancing | Optional (can skip) |
| Grace window | N/A | 3 seconds after [Done] tap |
| Mid-rest pause | Timer only | Full pause (all timers) |

---

## A4. Audio & Visual Notifications

### A4.1 Notification Events

Every timed event in a session triggers a combination of sound, visual, and
(on mobile) vibration:

| Event | Sound | Visual | Vibration |
|---|---|---|---|
| Set marked complete | Single soft beep | Green flash on [Done] button | 50ms pulse |
| Rest warning (10s left) | 3 short rising beeps | Timer turns amber, pulses | 3×50ms |
| Rest complete | Ascending 3-note tone | Full-screen green flash (200ms) | 200ms long |
| Play Mode auto-advance | Soft chime | Next exercise slides in | 100ms |
| Workout complete | 5-note fanfare | Confetti + summary overlay | 3×100ms |
| RPE drift warning | Soft low tone | Yellow banner appears | 1×100ms |
| Deload suggestion | None | Blue info banner | None |

### A4.2 Web Audio API Tone Generation

All sounds are generated programmatically via the Web Audio API — no audio files,
no network requests, works fully offline.

```javascript
// static/js/audio.js

const AudioContext = window.AudioContext || window.webkitAudioContext;
const ctx = new AudioContext();

function playTone(frequency, duration, type = 'sine', volume = 0.4) {
    const oscillator = ctx.createOscillator();
    const gainNode   = ctx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);
    gainNode.gain.setValueAtTime(volume, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + duration);
}

// Pre-defined sound events
const Sounds = {
    setComplete:   () => playTone(880, 0.15),
    restWarning:   () => [660, 770, 880].forEach((f, i) =>
                       setTimeout(() => playTone(f, 0.12), i * 120)),
    restComplete:  () => [523, 659, 784].forEach((f, i) =>
                       setTimeout(() => playTone(f, 0.25), i * 150)),
    workoutDone:   () => [523, 587, 659, 698, 784].forEach((f, i) =>
                       setTimeout(() => playTone(f, 0.3), i * 180)),
};
```

**Note on iOS**: Web Audio requires a user gesture to initialise the AudioContext.
The session start button (`[Start Workout]`) calls `ctx.resume()` on tap, which
satisfies this requirement for the entire session.

### A4.3 Visual Flash System

CSS classes applied to `<body>` or a full-screen overlay div, animated via keyframes:

```css
/* base.css */
@keyframes flash-green {
    0%   { background-color: rgba(72, 199, 116, 0); }
    20%  { background-color: rgba(72, 199, 116, 0.35); }
    100% { background-color: rgba(72, 199, 116, 0); }
}
@keyframes flash-amber {
    0%   { background-color: rgba(255, 183, 0, 0); }
    50%  { background-color: rgba(255, 183, 0, 0.3); }
    100% { background-color: rgba(255, 183, 0, 0); }
}
.flash-overlay {
    position: fixed; inset: 0;
    pointer-events: none;
    z-index: 9999;
}
.flash-overlay.rest-complete {
    animation: flash-green 0.6s ease-out forwards;
}
.flash-overlay.rest-warning {
    animation: flash-amber 0.4s ease-in-out 3;
}
```

Triggered from JS:

```javascript
function triggerFlash(type) {
    const overlay = document.getElementById('flash-overlay');
    overlay.className = `flash-overlay ${type}`;
    overlay.addEventListener('animationend', () => overlay.className = 'flash-overlay',
                             { once: true });
}
```

### A4.4 Vibration API

```javascript
// audio.js
const Vibrations = {
    setComplete:  () => navigator.vibrate?.(50),
    restWarning:  () => navigator.vibrate?.([50, 50, 50, 50, 50]),
    restComplete: () => navigator.vibrate?.(200),
    workoutDone:  () => navigator.vibrate?.([100, 80, 100, 80, 300]),
};
```

The `?.` optional chaining means this silently no-ops on desktop browsers.

### A4.5 Notification Settings

A settings panel (accessible from nav) lets you toggle each notification type:

| Setting | Default |
|---|---|
| Sound — set complete | Off |
| Sound — rest warning (10s) | On |
| Sound — rest complete | On |
| Sound — workout complete | On |
| Visual flash | On |
| Vibration | On (mobile) |
| Voice (Play Mode) | On |
| Voice language/accent | System default |
| Rest warning lead time | 10 seconds |
| Auto-advance buffer (Play Mode) | 5 seconds |

Settings stored in `localStorage` as `workoutOS_settings` JSON object.

---

## A5. Updated Route Table (Full)

| Route | Method | Description |
|---|---|---|
| `/` | GET | Dashboard with active program widget + body weight log |
| `/exercises` | GET | Exercise library |
| `/exercises/new` | GET | New exercise form |
| `/exercises/<id>/edit` | GET | Edit exercise |
| `/exercises` | POST | Save exercise |
| `/exercises/<id>` | POST | Update exercise |
| `/exercises/<id>` | DELETE | Delete exercise |
| `/workouts` | GET | All workout plans |
| `/workouts/new` | GET | Workout builder |
| `/workouts/<id>/edit` | GET | Edit plan |
| `/workouts` | POST | Save plan |
| `/workouts/<id>` | POST | Update plan |
| `/workouts/<id>/start` | GET | Active session (Manual or Play) |
| `/programs` | GET | All programs |
| `/programs/new` | GET | Program builder |
| `/programs/<id>/edit` | GET | Edit program |
| `/programs` | POST | Save program |
| `/programs/<id>/activate` | POST | Set active program |
| `/session/complete` | POST | Flush session + sets to CSV |
| `/body-weight` | POST | Append body weight log entry |
| `/analytics` | GET | History, charts, 1RM trends |
| `/settings` | GET | Notification + app preferences |
| `/api/exercises` | GET | JSON list for builder |
| `/api/exercises/<id>/history` | GET | Per-exercise progression JSON |
| `/api/body-weight` | GET | Body weight history JSON for charts |

---

## A6. Updated File Structure

```
workout-os/
├── app.py
├── config.py
├── requirements.txt
│
├── data/
│   ├── exercises/
│   │   ├── exercises.json
│   │   └── mobility.json
│   ├── workouts/
│   │   └── plans.json
│   ├── programs/
│   │   └── programs.json          ← NEW
│   └── history/
│       ├── sessions.csv
│       ├── sets_log.csv
│       └── body_weight.csv        ← NEW
│
├── services/
│   ├── exercise_service.py
│   ├── workout_service.py
│   ├── program_service.py         ← NEW
│   ├── session_service.py
│   ├── body_weight_service.py     ← NEW
│   ├── ordering_algorithm.py
│   └── progression_engine.py
│
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── layout.css
│   │   ├── components.css
│   │   ├── builder.css
│   │   ├── program_builder.css    ← NEW
│   │   └── session.css
│   └── js/
│       ├── exercise_form.js
│       ├── workout_builder.js
│       ├── program_builder.js     ← NEW
│       ├── active_session.js      (updated: play mode, wake lock)
│       ├── audio.js               ← NEW
│       └── analytics.js
│
└── templates/
    ├── base.html
    ├── dashboard.html             (updated: program widget, body weight)
    ├── exercises/
    │   ├── index.html
    │   └── form.html
    ├── workouts/
    │   ├── index.html
    │   └── builder.html
    ├── programs/                  ← NEW
    │   ├── index.html
    │   └── builder.html
    ├── session/
    │   └── active.html            (updated: play mode toggle, flash overlay)
    ├── analytics/
    │   └── index.html             (updated: body weight chart)
    └── settings.html              ← NEW
```
