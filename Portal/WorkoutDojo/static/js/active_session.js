// static/js/active_session.js — WorkoutOS Active Session Engine
// Sections: S13, S15, S17, S18, S19, S20, S21, S22, S28
//
// Requires: SESSION_DATA global set in template:
//   { plan, exercises, mobility, sessionId, suggestions, isDeload, deloadPct }
// Requires: audio.js loaded before this file (provides notifyEvent, announce, resumeAudio, triggerFlash)

'use strict';

// ---------------------------------------------------------------------------
// Settings helpers
// ---------------------------------------------------------------------------

function getSettings() {
    try {
        return JSON.parse(localStorage.getItem('workoutOS_settings') || '{}');
    } catch { return {}; }
}

function getSetting(key, defaultValue) {
    const s = getSettings();
    return (s[key] !== undefined && s[key] !== null) ? s[key] : defaultValue;
}

// ---------------------------------------------------------------------------
// Session state machine
// ---------------------------------------------------------------------------

const state = {
    mode:                        'manual',  // 'manual' | 'play'
    phase:                       'set',     // 'set' | 'grace' | 'rest' | 'complete'
    currentStepIndex:            0,
    reps:                        0,
    weight:                      0,
    rpe:                         null,
    restSecondsTotal:            0,
    restSecondsRemaining:        0,
    graceSecondsRemaining:       3,
    autoAdvanceSecondsRemaining: 5,
    paused:                      false,
    wakeLock:                    null,
    loggedSets:                  [],         // accumulates set records for submission
    sessionStartTime:            Date.now(),
    restTimerInterval:           null,
    graceTimerInterval:          null,
    autoAdvanceInterval:         null,
    restWarningFired:            false,
    // Timed exercise state
    isTimedSet:                  false,
    setDurationTotal:            0,
    setDurationRemaining:        0,
    setTimerInterval:            null,
    timedGraceFired:             false,  // tracks if grace countdown was shown for timed set
    // Progression overrides (user can change suggested weight at end)
    progressionOverrides:        {},
};

// ---------------------------------------------------------------------------
// Build flat session sequence from SESSION_DATA
// ---------------------------------------------------------------------------

// Each step: { type: 'set'|'rest'|'transition', exercise?, set_spec?, set_num?, total_sets?, filler?, seconds?, message?, superset_group? }
let sessionSequence = [];

function buildSequence() {
    const plan      = SESSION_DATA.plan;
    const exercises = SESSION_DATA.exercises; // dict: id -> exercise object

    if (!plan || !plan.entries) return;

    const mobility = SESSION_DATA.mobility || {}; // dict: id -> mobility object

    const sortedEntries = [...plan.entries].sort((a, b) => a.order - b.order);

    // Group entries by superset
    const supersetGroups = {};
    const standalone     = [];

    sortedEntries.forEach(entry => {
        if (entry.superset_group) {
            if (!supersetGroups[entry.superset_group]) supersetGroups[entry.superset_group] = [];
            supersetGroups[entry.superset_group].push(entry);
        } else {
            standalone.push(entry);
        }
    });

    const sequence       = [];
    const processedGroups = new Set();

    sortedEntries.forEach(entry => {
        if (entry.superset_group) {
            if (processedGroups.has(entry.superset_group)) return;
            processedGroups.add(entry.superset_group);

            const group = supersetGroups[entry.superset_group];
            // Compute superset rest: max rest across group + 15s per extra exercise, capped 180s
            let maxRest = 0;
            group.forEach(e => {
                (e.sets || []).forEach(s => {
                    if (s.rest_seconds > maxRest) maxRest = s.rest_seconds;
                });
            });
            const groupRest = Math.min(maxRest + 15 * (group.length - 1), 180);
            const maxSets   = Math.max(...group.map(e => e.sets.length));

            for (let setIdx = 0; setIdx < maxSets; setIdx++) {
                group.forEach(gEntry => {
                    const ex = exercises[gEntry.exercise_id];
                    if (!ex || setIdx >= gEntry.sets.length) return;

                    sequence.push({
                        type:           'set',
                        exercise:       ex,
                        set_spec:       gEntry.sets[setIdx],
                        set_num:        setIdx + 1,
                        total_sets:     gEntry.sets.length,
                        superset_group: gEntry.superset_group,
                        entry_id:       gEntry.exercise_id,
                        filler:         null,
                    });
                });

                // Rest after each superset round except the last
                if (setIdx < maxSets - 1) {
                    sequence.push({
                        type:    'rest',
                        seconds: groupRest,
                        filler:  null,
                    });
                }
            }

            // Transition after superset group
            sequence.push({ type: 'transition', message: 'Moving to next exercise' });

        } else {
            const ex = exercises[entry.exercise_id];
            if (!ex) return;

            const filler = (entry.filler_id && mobility[entry.filler_id]) ? mobility[entry.filler_id] : null;
            const sets   = entry.sets || [];

            sets.forEach((setSpec, setIdx) => {
                sequence.push({
                    type:           'set',
                    exercise:       ex,
                    set_spec:       setSpec,
                    set_num:        setIdx + 1,
                    total_sets:     sets.length,
                    superset_group: null,
                    entry_id:       entry.exercise_id,
                    filler:         filler,
                });

                // Rest after every set except the last
                if (setIdx < sets.length - 1) {
                    sequence.push({
                        type:    'rest',
                        seconds: setSpec.rest_seconds,
                        filler:  filler,
                    });
                }
            });

            // Transition to next exercise
            sequence.push({ type: 'transition', message: 'Moving to next exercise' });
        }
    });

    return sequence;
}

// ---------------------------------------------------------------------------
// DOM element references
// ---------------------------------------------------------------------------

const els = {
    // Set phase
    exerciseDisplay:    document.getElementById('exercise-display'),
    exerciseName:       document.getElementById('current-exercise-name'),
    setCounter:         document.getElementById('set-counter'),
    targetDisplay:      document.getElementById('target-display'),
    warmupLabel:        document.getElementById('warmup-label'),
    supersetLabel:      document.getElementById('superset-label'),
    deloadBadge:        document.getElementById('deload-badge'),
    repsDisplay:        document.getElementById('reps-display'),
    weightDisplay:      document.getElementById('weight-display'),
    weightAdjuster:     document.getElementById('weight-adjuster'),
    rpeSelector:        document.getElementById('rpe-selector'),
    completeSetBtn:     document.getElementById('complete-set-btn'),

    // Rest phase
    restArea:           document.getElementById('rest-area'),
    restTimer:          document.getElementById('rest-timer'),
    restProgressFill:   document.getElementById('rest-progress-fill'),
    fillerCard:         document.getElementById('filler-card'),
    fillerName:         document.getElementById('filler-name'),
    fillerInstructions: document.getElementById('filler-instructions'),
    fillerDuration:     document.getElementById('filler-duration'),
    fillerTypeLabel:    document.getElementById('filler-type-label'),
    autoAdvanceArea:    document.getElementById('auto-advance-area'),
    nextExerciseName:   document.getElementById('next-exercise-name'),
    autoAdvanceCount:   document.getElementById('auto-advance-count'),

    // Grace overlay
    graceOverlay:       document.getElementById('grace-overlay'),
    graceCountdown:     document.getElementById('grace-countdown'),
    cancelGraceBtn:     document.getElementById('cancel-grace-btn'),

    // Controls
    pauseBtn:           document.getElementById('pause-btn'),
    modeManualBtn:      document.getElementById('mode-manual-btn'),
    modePlayBtn:        document.getElementById('mode-play-btn'),

    // Session progress
    sessionProgress:    document.getElementById('session-progress-fill'),

    // Complete overlay
    completeOverlay:    document.getElementById('complete-overlay'),
    totalSetsDisplay:   document.getElementById('total-sets-display'),
    totalVolumeDisplay: document.getElementById('total-volume-display'),
    durationDisplay:    document.getElementById('duration-display'),
    suggestionsArea:    document.getElementById('suggestions-area'),
    sessionNotes:       document.getElementById('session-notes'),
    saveExitBtn:        document.getElementById('save-exit-btn'),

    // Flash overlay (in DOM, used by audio.js)
    flashOverlay:       document.getElementById('flash-overlay'),

    // Confetti canvas
    confettiCanvas:     document.getElementById('confetti-canvas'),
};

// ---------------------------------------------------------------------------
// Initialise session
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    sessionSequence = buildSequence();

    if (!sessionSequence || !sessionSequence.length) {
        showToast('No exercises in this workout.', 'danger');
        return;
    }

    // Skip any leading transitions
    while (
        state.currentStepIndex < sessionSequence.length &&
        sessionSequence[state.currentStepIndex].type === 'transition'
    ) {
        state.currentStepIndex++;
    }

    // Bind UI events
    bindButtons();
    bindRpeSelector();

    // Show initial set
    showCurrentStep();
});

// ---------------------------------------------------------------------------
// Bind buttons
// ---------------------------------------------------------------------------

function bindButtons() {
    // Complete set button — also satisfies iOS AudioContext requirement on first tap
    if (els.completeSetBtn) {
        els.completeSetBtn.addEventListener('click', () => {
            resumeAudio(); // iOS requirement
            handleCompleteSetTap();
        }, { once: true });

        els.completeSetBtn.addEventListener('click', handleCompleteSetTap);
    }

    // +/- reps
    document.getElementById('reps-plus')?.addEventListener('click', () => {
        state.reps++;
        updateRepsDisplay();
    });
    document.getElementById('reps-minus')?.addEventListener('click', () => {
        if (state.reps > 0) { state.reps--; updateRepsDisplay(); }
    });

    // +/- weight
    document.getElementById('weight-plus')?.addEventListener('click', () => {
        state.weight = roundWeight(state.weight + weightStep());
        updateWeightDisplay();
    });
    document.getElementById('weight-minus')?.addEventListener('click', () => {
        const next = state.weight - weightStep();
        state.weight = roundWeight(Math.max(0, next));
        updateWeightDisplay();
    });

    // Mode toggle
    if (els.modeManualBtn) {
        els.modeManualBtn.addEventListener('click', () => switchMode('manual'));
    }
    if (els.modePlayBtn) {
        els.modePlayBtn.addEventListener('click', () => switchMode('play'));
    }

    // Pause
    if (els.pauseBtn) {
        els.pauseBtn.addEventListener('click', togglePause);
    }

    // Cancel grace
    if (els.cancelGraceBtn) {
        els.cancelGraceBtn.addEventListener('click', cancelGrace);
    }

    // Save & exit
    if (els.saveExitBtn) {
        els.saveExitBtn.addEventListener('click', saveAndExit);
    }

    // Page visibility: auto-pause when phone locks
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && state.phase === 'rest' && !state.paused) {
            pauseSession();
        }
    });

    // Wake lock re-request on visibility regain (Play Mode)
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && state.mode === 'play' && !state.paused) {
            enableWakeLock();
        }
    });
}

// ---------------------------------------------------------------------------
// RPE selector
// ---------------------------------------------------------------------------

function bindRpeSelector() {
    if (!els.rpeSelector) return;

    els.rpeSelector.addEventListener('click', (e) => {
        const dot = e.target.closest('.rpe-dot');
        if (!dot) return;
        const rpe = parseFloat(dot.dataset.rpe);
        state.rpe = state.rpe === rpe ? null : rpe; // toggle
        updateRpeDots();
    });
}

function updateRpeDots() {
    if (!els.rpeSelector) return;
    els.rpeSelector.querySelectorAll('.rpe-dot').forEach(dot => {
        const dotRpe = parseFloat(dot.dataset.rpe);
        dot.classList.toggle('selected', dotRpe === state.rpe);
    });
}

// ---------------------------------------------------------------------------
// Step navigation helpers
// ---------------------------------------------------------------------------

function currentStep() {
    return sessionSequence[state.currentStepIndex] || null;
}

function nextNonTransitionStep(fromIndex) {
    let i = fromIndex;
    while (i < sessionSequence.length) {
        const step = sessionSequence[i];
        if (step.type !== 'transition') return step;
        i++;
    }
    return null;
}

function advanceStepIndex() {
    state.currentStepIndex++;
    // Skip transitions automatically
    while (
        state.currentStepIndex < sessionSequence.length &&
        sessionSequence[state.currentStepIndex].type === 'transition'
    ) {
        state.currentStepIndex++;
    }
}

// ---------------------------------------------------------------------------
// Show current step
// ---------------------------------------------------------------------------

function showCurrentStep() {
    const step = currentStep();
    if (!step) {
        // No more steps
        completeWorkout();
        return;
    }

    if (step.type === 'set') {
        showSetPhase(step);
    } else if (step.type === 'rest') {
        showRestPhase(step.seconds, step.filler);
    } else {
        // Transition — skip
        advanceStepIndex();
        showCurrentStep();
    }

    updateSessionProgress();
}

// ---------------------------------------------------------------------------
// SET PHASE
// ---------------------------------------------------------------------------

function showSetPhase(step) {
    state.phase = 'set';
    state.rpe   = null;

    // Detect timed exercise
    const isTimed = !!step.exercise.is_timed && step.set_spec.duration_seconds > 0;
    state.isTimedSet = isTimed;
    state.timedGraceFired = false;

    // Clear any lingering set timer
    clearInterval(state.setTimerInterval);
    state.setTimerInterval = null;

    // Determine starting reps/weight from suggestion or last logged
    const suggestion = (SESSION_DATA.suggestions || {})[step.exercise.id];

    if (isTimed) {
        // Timed exercise: duration from set_spec
        state.setDurationTotal = step.set_spec.duration_seconds;
        state.setDurationRemaining = step.set_spec.duration_seconds;
        state.reps = 0;
    } else {
        // Rep-based exercise
        const targetReps = step.set_spec.rep_max || step.set_spec.rep_min || 8;
        state.reps = targetReps;
    }

    // Weight: per-set plan > suggestion > last logged > 0
    const setWeightPlan = (SESSION_DATA.setWeightPlans || {})[step.exercise.id];
    if (setWeightPlan && setWeightPlan.set_weights && step.set_num <= setWeightPlan.set_weights.length) {
        state.weight = setWeightPlan.set_weights[step.set_num - 1];
    } else if (suggestion && suggestion.suggested_weight_kg > 0) {
        state.weight = suggestion.suggested_weight_kg;
    } else {
        const lastLogged = [...state.loggedSets]
            .reverse()
            .find(s => s.exercise_id === step.exercise.id && !s.is_warmup);
        state.weight = lastLogged ? lastLogged.weight_kg : 0;
    }

    // Show elements
    showEl(els.exerciseDisplay);
    hideEl(els.restArea);
    hideEl(els.graceOverlay);

    // Toggle reps stepper vs duration countdown
    const repsGroup = document.getElementById('reps-stepper-group');
    const durationGroup = document.getElementById('duration-countdown-group');
    if (repsGroup) repsGroup.style.display = isTimed ? 'none' : '';
    if (durationGroup) durationGroup.style.display = isTimed ? '' : 'none';

    // Exercise name
    if (els.exerciseName) {
        els.exerciseName.textContent = step.exercise.voice_name || step.exercise.name;
    }

    // Set counter
    if (els.setCounter) {
        els.setCounter.textContent = `Set ${step.set_num} of ${step.total_sets}`;
    }

    // Warmup label
    if (els.warmupLabel) {
        toggleElVisibility(els.warmupLabel, !!step.set_spec.is_warmup);
    }

    // Superset label
    if (els.supersetLabel) {
        if (step.superset_group) {
            const isAuto = !!step.auto_superset;
            els.supersetLabel.textContent = isAuto
                ? `Auto Superset ${step.superset_group}`
                : `Superset ${step.superset_group}`;
            showEl(els.supersetLabel);
        } else {
            hideEl(els.supersetLabel);
        }
    }

    // Deload badge
    if (els.deloadBadge) {
        toggleElVisibility(els.deloadBadge, !!SESSION_DATA.isDeload);
    }

    // Target display
    if (els.targetDisplay) {
        if (isTimed) {
            const weightStr = state.weight > 0 ? ` @ ${state.weight} kg` : '';
            els.targetDisplay.textContent = `Hold for ${step.set_spec.duration_seconds}s${weightStr}`;
        } else {
            // Show per-set weight label if available
            const label = setWeightPlan?.labels?.[step.set_num - 1];
            const isBodyweight = step.exercise.category === 'bodyweight';
            if (label && !isBodyweight) {
                els.targetDisplay.textContent = `${label} — ${step.set_spec.rep_min}–${step.set_spec.rep_max} reps @ ${state.weight} kg`;
            } else if (isBodyweight) {
                els.targetDisplay.textContent = `Target: ${step.set_spec.rep_min}–${step.set_spec.rep_max} reps`;
            } else {
                const weightStr = state.weight > 0 ? ` @ ${state.weight} kg` : '';
                els.targetDisplay.textContent = `Target: ${step.set_spec.rep_min}–${step.set_spec.rep_max} reps${weightStr}`;
            }
        }
    }

    // Weight adjuster visibility (hide for bodyweight and timed-bodyweight)
    const isBodyweight = step.exercise.category === 'bodyweight';
    if (els.weightAdjuster) {
        toggleElVisibility(els.weightAdjuster, !isBodyweight && step.exercise.uses_weights !== false);
    }

    // Update displays
    if (!isTimed) {
        updateRepsDisplay();
    }
    updateWeightDisplay();
    updateRpeDots();

    // Update duration timer display for timed exercises
    if (isTimed) {
        updateSetTimerDisplay();
    }

    // Show RPE target hint
    if (step.set_spec.target_rpe) {
        const rpeHint = document.getElementById('rpe-target-hint');
        if (rpeHint) rpeHint.textContent = `Target RPE: ${step.set_spec.target_rpe}`;
    }

    // Voice announcement in Play Mode
    if (state.mode === 'play') {
        announceSet(step);
    }

    // Update complete button text
    if (els.completeSetBtn) {
        if (isTimed) {
            els.completeSetBtn.textContent = '▶ Start Timer';
        } else if (state.mode === 'play') {
            els.completeSetBtn.textContent = '✓ DONE';
        } else {
            els.completeSetBtn.textContent = '✓ Complete Set';
        }
    }

    // Show/hide pause button
    if (els.pauseBtn) {
        toggleElVisibility(els.pauseBtn, state.mode === 'play' || isTimed);
    }

    // Auto-start timed exercise with 3s grace countdown
    if (isTimed) {
        startTimedGrace();
    }
}

// ---------------------------------------------------------------------------
// Handle complete-set button tap
// ---------------------------------------------------------------------------

function handleCompleteSetTap() {
    if (state.phase !== 'set') return;

    // Timed exercise: if timer is running, stop early
    if (state.isTimedSet && state.setTimerInterval) {
        clearInterval(state.setTimerInterval);
        state.setTimerInterval = null;
        logCurrentSet();
        proceedAfterSet();
        return;
    }

    // Timed exercise: if grace hasn't fired yet, start it
    if (state.isTimedSet && !state.timedGraceFired) {
        startTimedGrace();
        return;
    }

    if (state.mode === 'play') {
        // Start 3-second grace countdown
        startGrace();
    } else {
        // Manual mode: log immediately, start rest
        logCurrentSet();
        proceedAfterSet();
    }
}

// ---------------------------------------------------------------------------
// GRACE PHASE (Play Mode only — 3s to cancel)
// ---------------------------------------------------------------------------

function startGrace() {
    state.phase                   = 'grace';
    state.graceSecondsRemaining   = 3;

    showEl(els.graceOverlay);
    updateGraceDisplay();

    state.graceTimerInterval = setInterval(() => {
        state.graceSecondsRemaining--;
        updateGraceDisplay();

        if (state.graceSecondsRemaining <= 0) {
            clearInterval(state.graceTimerInterval);
            state.graceTimerInterval = null;
            // Lock in values and proceed
            hideEl(els.graceOverlay);
            logCurrentSet();
            proceedAfterSet();
        }
    }, 1000);
}

function updateGraceDisplay() {
    if (els.graceCountdown) {
        els.graceCountdown.textContent = state.graceSecondsRemaining;
    }
}

function cancelGrace() {
    clearInterval(state.graceTimerInterval);
    state.graceTimerInterval = null;
    hideEl(els.graceOverlay);
    state.phase = 'set';
    // Return to set phase — no changes to state.reps / state.weight
}

// ---------------------------------------------------------------------------
// Log the current set
// ---------------------------------------------------------------------------

function logCurrentSet() {
    const step = currentStep();
    if (!step || step.type !== 'set') return;

    const isTimed = state.isTimedSet;
    const actualDuration = isTimed
        ? (state.setDurationTotal - state.setDurationRemaining)
        : null;

    const record = {
        exercise_id:      step.exercise.id,
        exercise_name:    step.exercise.name,
        set_num:          step.set_num,
        reps:             isTimed ? 0 : state.reps,
        weight_kg:        step.exercise.category === 'bodyweight' ? 0 : state.weight,
        rpe:              state.rpe,
        is_warmup:        !!step.set_spec.is_warmup,
        duration_seconds: actualDuration,
        timestamp:        new Date().toISOString(),
    };

    state.loggedSets.push(record);
    notifyEvent('setComplete');
}

// ---------------------------------------------------------------------------
// Proceed after set is logged — determine next phase
// ---------------------------------------------------------------------------

function proceedAfterSet() {
    const currentStepCopy = state.currentStepIndex;
    advanceStepIndex(); // advances past current set step

    const nextStep = currentStep();

    if (!nextStep) {
        // All done
        completeWorkout();
        return;
    }

    if (nextStep.type === 'rest') {
        showRestPhase(nextStep.seconds, nextStep.filler);
    } else if (nextStep.type === 'set') {
        // No rest between these (e.g. last set of an entry with no explicit rest, or superset)
        showCurrentStep();
    } else {
        // Transition / end
        advanceStepIndex();
        showCurrentStep();
    }
}

// ---------------------------------------------------------------------------
// REST PHASE
// ---------------------------------------------------------------------------

function showRestPhase(seconds, filler) {
    state.phase                = 'rest';
    state.restSecondsTotal     = seconds;
    state.restSecondsRemaining = seconds;
    state.restWarningFired     = false;

    showEl(els.restArea);
    hideEl(els.exerciseDisplay);
    hideEl(els.graceOverlay);
    hideEl(els.autoAdvanceArea);

    // Filler card
    if (els.fillerCard) {
        if (filler) {
            if (els.fillerName) els.fillerName.textContent = filler.name || '';
            if (els.fillerInstructions) els.fillerInstructions.textContent = filler.instructions || '';
            if (els.fillerDuration) els.fillerDuration.textContent = `${filler.duration_seconds || 30}s`;
            if (els.fillerTypeLabel) els.fillerTypeLabel.textContent = (filler.filler_type || 'mobility').toUpperCase();
            showEl(els.fillerCard);
        } else {
            hideEl(els.fillerCard);
        }
    }

    // Show pause button in Play Mode
    if (els.pauseBtn) {
        toggleElVisibility(els.pauseBtn, state.mode === 'play');
        els.pauseBtn.textContent = state.paused ? '▶ Resume' : 'II Pause';
        els.pauseBtn.classList.toggle('paused', state.paused);
    }

    updateRestTimerDisplay();
    startRestTimer();
}

// ---------------------------------------------------------------------------
// Rest timer
// ---------------------------------------------------------------------------

function startRestTimer() {
    clearInterval(state.restTimerInterval);

    state.restTimerInterval = setInterval(() => {
        if (state.paused) return;

        state.restSecondsRemaining--;
        updateRestTimerDisplay();

        const warningLeadTime = getSetting('restWarningLeadTime', 10);

        // Warning trigger
        if (!state.restWarningFired && state.restSecondsRemaining <= warningLeadTime && state.restSecondsRemaining > 0) {
            state.restWarningFired = true;
            notifyEvent('restWarning');
            if (els.restTimer) els.restTimer.classList.add('warning');
            if (els.restProgressFill) els.restProgressFill.classList.add('warning');
        }

        // Rest complete
        if (state.restSecondsRemaining <= 0) {
            clearInterval(state.restTimerInterval);
            state.restTimerInterval = null;
            onRestComplete();
        }
    }, 1000);
}

function updateRestTimerDisplay() {
    if (els.restTimer) {
        els.restTimer.textContent = formatTime(state.restSecondsRemaining);
        els.restTimer.classList.toggle('warning',
            state.restSecondsRemaining <= getSetting('restWarningLeadTime', 10) && state.restSecondsRemaining > 0
        );
    }

    if (els.restProgressFill && state.restSecondsTotal > 0) {
        const pct = (state.restSecondsRemaining / state.restSecondsTotal) * 100;
        els.restProgressFill.style.width = `${pct}%`;
    }
}

function onRestComplete() {
    notifyEvent('restComplete');

    // Advance past rest step
    advanceStepIndex();

    const nextStep = currentStep();
    if (!nextStep) {
        completeWorkout();
        return;
    }

    // Voice: "Rest complete. [Next exercise name]."
    if (state.mode === 'play' && nextStep.type === 'set') {
        const nextName = nextStep.exercise?.voice_name || nextStep.exercise?.name || '';
        announce(`Rest complete. ${nextName}.`);
    }

    if (state.mode === 'play') {
        // Auto-advance buffer countdown before showing next set
        startAutoAdvanceBuffer(nextStep);
    } else {
        // Manual: go straight to next step
        showCurrentStep();
    }
}

// ---------------------------------------------------------------------------
// Auto-advance buffer (Play Mode — 5s after rest complete)
// ---------------------------------------------------------------------------

function startAutoAdvanceBuffer(nextStep) {
    const buffer = getSetting('autoAdvanceBuffer', 5);
    state.autoAdvanceSecondsRemaining = buffer;

    if (els.autoAdvanceArea) showEl(els.autoAdvanceArea);

    if (nextStep && nextStep.type === 'set') {
        const name = nextStep.exercise?.name || 'next exercise';
        if (els.nextExerciseName) els.nextExerciseName.textContent = name;
    }

    updateAutoAdvanceDisplay();

    if (buffer <= 0) {
        // No buffer — advance immediately
        hideEl(els.autoAdvanceArea);
        showCurrentStep();
        return;
    }

    clearInterval(state.autoAdvanceInterval);
    state.autoAdvanceInterval = setInterval(() => {
        if (state.paused) return;

        state.autoAdvanceSecondsRemaining--;
        updateAutoAdvanceDisplay();

        if (state.autoAdvanceSecondsRemaining <= 0) {
            clearInterval(state.autoAdvanceInterval);
            state.autoAdvanceInterval = null;
            hideEl(els.autoAdvanceArea);
            notifyEvent('autoAdvance');
            showCurrentStep();
        }
    }, 1000);
}

function updateAutoAdvanceDisplay() {
    if (els.autoAdvanceCount) {
        els.autoAdvanceCount.textContent = state.autoAdvanceSecondsRemaining;
    }
}

// ---------------------------------------------------------------------------
// PAUSE / RESUME (S22)
// ---------------------------------------------------------------------------

function togglePause() {
    if (state.paused) {
        resumeSession();
    } else {
        pauseSession();
    }
}

function pauseSession() {
    state.paused = true;
    releaseWakeLock();

    if (els.pauseBtn) {
        els.pauseBtn.textContent = '▶ Resume';
        els.pauseBtn.classList.add('paused');
    }

    // Timers remain running but skip decrement when paused
    showToast('Paused', 'info');
}

function resumeSession() {
    state.paused = false;

    if (state.mode === 'play') {
        enableWakeLock();
    }

    if (els.pauseBtn) {
        els.pauseBtn.textContent = 'II Pause';
        els.pauseBtn.classList.remove('paused');
    }
}

// ---------------------------------------------------------------------------
// SCREEN WAKE LOCK (S19)
// ---------------------------------------------------------------------------

async function enableWakeLock() {
    if ('wakeLock' in navigator) {
        try {
            if (state.wakeLock) return; // already held
            state.wakeLock = await navigator.wakeLock.request('screen');
            state.wakeLock.addEventListener('release', () => {
                state.wakeLock = null;
            });
        } catch (e) {
            console.warn('Wake lock failed:', e);
        }
    }
}

function releaseWakeLock() {
    if (state.wakeLock) {
        state.wakeLock.release().catch(() => {});
        state.wakeLock = null;
    }
}

// ---------------------------------------------------------------------------
// VOICE ANNOUNCEMENTS (S20)
// ---------------------------------------------------------------------------

function announceSet(step) {
    if (!step || step.type !== 'set') return;
    const name      = step.exercise.voice_name || step.exercise.name;
    const isTimed   = !!step.exercise.is_timed && step.set_spec.duration_seconds > 0;

    if (isTimed) {
        const weight = state.weight > 0 ? ` at ${state.weight} kilograms` : '';
        announce(`${name}. Set ${step.set_num} of ${step.total_sets}. Hold for ${step.set_spec.duration_seconds} seconds${weight}.`);
    } else {
        const repMin    = step.set_spec.rep_min;
        const repMax    = step.set_spec.rep_max;
        const isBodyweight = step.exercise.category === 'bodyweight';

        if (isBodyweight) {
            announce(`${name}. Set ${step.set_num} of ${step.total_sets}. Target ${repMin} to ${repMax} reps.`);
        } else {
            const weight = state.weight > 0 ? `at ${state.weight} kilograms` : '';
            announce(`${name}. Set ${step.set_num} of ${step.total_sets}. Target ${repMin} to ${repMax} reps ${weight}.`.trim());
        }
    }
}

// ---------------------------------------------------------------------------
// MODE TOGGLE
// ---------------------------------------------------------------------------

function switchMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;

    // Update button styles
    if (els.modeManualBtn) els.modeManualBtn.classList.toggle('active', mode === 'manual');
    if (els.modePlayBtn)   els.modePlayBtn.classList.toggle('active', mode === 'play');

    // Show/hide pause button
    if (els.pauseBtn) {
        toggleElVisibility(els.pauseBtn, mode === 'play');
    }

    if (mode === 'play') {
        enableWakeLock();
        // Announce current step if we're on a set
        const step = currentStep();
        if (step && step.type === 'set') {
            announceSet(step);
        }
    } else {
        // Manual: release wake lock, cancel auto-advance
        releaseWakeLock();
        clearInterval(state.autoAdvanceInterval);
        state.autoAdvanceInterval = null;
        hideEl(els.autoAdvanceArea);
    }

    // Re-render current step UI with new mode context
    if (state.phase === 'set') {
        const step = currentStep();
        if (step && step.type === 'set') {
            showSetPhase(step);
        }
    }
}

// ---------------------------------------------------------------------------
// SESSION PROGRESS BAR
// ---------------------------------------------------------------------------

function updateSessionProgress() {
    if (!els.sessionProgress) return;
    const totalSteps = sessionSequence.filter(s => s.type === 'set').length;
    const doneSteps  = state.loggedSets.length;
    const pct        = totalSteps > 0 ? (doneSteps / totalSteps) * 100 : 0;
    els.sessionProgress.style.width = `${pct}%`;
}

// ---------------------------------------------------------------------------
// WORKOUT COMPLETE (S28)
// ---------------------------------------------------------------------------

function completeWorkout() {
    // Prevent double-calling
    if (state.phase === 'complete') return;
    state.phase = 'complete';

    clearAllTimers();
    releaseWakeLock();
    window.speechSynthesis?.cancel();

    notifyEvent('workoutDone');
    announce('Workout complete. Great work.');

    // Show complete overlay
    showEl(els.completeOverlay);

    // Stats
    const workingSets = state.loggedSets.filter(s => !s.is_warmup);
    const totalSets   = workingSets.length;
    const totalVolume = workingSets.reduce((sum, s) => sum + (s.reps * (s.weight_kg || 0)), 0);
    const durationMs  = Date.now() - state.sessionStartTime;
    const durationMin = Math.floor(durationMs / 60000);
    const durationSec = Math.floor((durationMs % 60000) / 1000);

    if (els.totalSetsDisplay)   els.totalSetsDisplay.textContent   = totalSets;
    if (els.totalVolumeDisplay) els.totalVolumeDisplay.textContent = `${Math.round(totalVolume)} kg`;
    if (els.durationDisplay)    els.durationDisplay.textContent    = `${durationMin}:${String(durationSec).padStart(2, '0')}`;

    // Progression suggestions
    renderSuggestions();

    // Confetti!
    triggerConfetti();
}

// ---------------------------------------------------------------------------
// PROGRESSION SUGGESTIONS DISPLAY
// ---------------------------------------------------------------------------

function renderSuggestions() {
    if (!els.suggestionsArea) return;
    const suggestions = SESSION_DATA.suggestions || [];
    if (!suggestions.length) {
        els.suggestionsArea.innerHTML = '<p style="color:var(--text-secondary);font-size:13px">No progression data yet.</p>';
        return;
    }

    els.suggestionsArea.innerHTML = suggestions.map((sug, i) => {
        const exercise = SESSION_DATA.exercises[sug.exercise_id];
        const name     = exercise?.name || sug.exercise_id;

        const rpeDrift  = sug.rpe_drift_warning
            ? `<div class="banner banner-warning" style="margin-top:8px;margin-bottom:0"><span class="banner-icon">⚠</span><div>RPE trending up — consider a deload</div></div>`
            : '';

        // Alternative buttons
        const altBtns = (sug.alternatives || []).map(alt =>
            `<button class="suggestion-btn" data-sug="${i}" data-weight="${alt}">
                ${alt > sug.current_weight_kg ? '+' : ''}${(alt - sug.current_weight_kg).toFixed(2).replace(/\.?0+$/, '')} kg (${alt} kg)
             </button>`
        ).join('');

        const acceptBtn = sug.suggested_weight_kg > 0 && sug.increment_kg > 0
            ? `<button class="suggestion-btn selected" data-sug="${i}" data-weight="${sug.suggested_weight_kg}">
                   ✓ ${sug.suggested_weight_kg} kg (+${sug.increment_kg} kg)
               </button>`
            : '';

        return `
            <div class="suggestion-card">
                <div class="suggestion-exercise">${escHtml(name)}</div>
                <div class="suggestion-reason">${escHtml(sug.reason)}</div>
                <div class="suggestion-actions">
                    ${acceptBtn}
                    ${altBtns}
                </div>
                ${rpeDrift}
            </div>
        `;
    }).join('');

    // Bind suggestion buttons
    els.suggestionsArea.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sugIndex = parseInt(btn.dataset.sug);
            const weight   = parseFloat(btn.dataset.weight);
            const sug      = suggestions[sugIndex];
            if (!sug) return;

            // Update override
            state.progressionOverrides[sug.exercise_id] = weight;

            // Update button states in this card
            const card = btn.closest('.suggestion-card');
            card?.querySelectorAll('.suggestion-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });
}

// ---------------------------------------------------------------------------
// SAVE & EXIT (POST to /session/complete)
// ---------------------------------------------------------------------------

async function saveAndExit() {
    if (els.saveExitBtn) {
        els.saveExitBtn.disabled    = true;
        els.saveExitBtn.textContent = 'Saving…';
    }

    const notes = els.sessionNotes?.value?.trim() || '';

    const payload = {
        session_id:            SESSION_DATA.sessionId,
        plan_id:               SESSION_DATA.plan?.id,
        logged_sets:           state.loggedSets,
        notes,
        duration_seconds:      Math.round((Date.now() - state.sessionStartTime) / 1000),
        progression_overrides: state.progressionOverrides,
    };

    try {
        const resp = await fetch('/session/complete', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        window.location.href = '/workouts/';

    } catch (err) {
        console.error('saveAndExit error:', err);
        showToast('Could not save session. Please try again.', 'danger');
        if (els.saveExitBtn) {
            els.saveExitBtn.disabled    = false;
            els.saveExitBtn.textContent = 'Save & Exit';
        }
    }
}

// ---------------------------------------------------------------------------
// CONFETTI (S28)
// ---------------------------------------------------------------------------

function triggerConfetti() {
    const canvas = els.confettiCanvas;
    if (!canvas) return;

    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    showEl(canvas);

    const ctx2d      = canvas.getContext('2d');
    const COLORS     = ['#6c63ff', '#48c774', '#ffb700', '#ff3860', '#00d1ff', '#ff7e5f'];
    const TOTAL      = 200;
    const DURATION   = 3500; // ms
    const startTime  = performance.now();

    const particles = Array.from({ length: TOTAL }, () => ({
        x:     Math.random() * canvas.width,
        y:     Math.random() * canvas.height * -0.5,
        vx:    (Math.random() - 0.5) * 4,
        vy:    Math.random() * 4 + 2,
        angle: Math.random() * Math.PI * 2,
        spin:  (Math.random() - 0.5) * 0.3,
        size:  Math.random() * 8 + 4,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        shape: Math.random() > 0.5 ? 'rect' : 'circle',
    }));

    function draw(now) {
        const elapsed = now - startTime;
        if (elapsed > DURATION) {
            ctx2d.clearRect(0, 0, canvas.width, canvas.height);
            hideEl(canvas);
            return;
        }

        ctx2d.clearRect(0, 0, canvas.width, canvas.height);

        const alpha = elapsed > DURATION - 800 ? 1 - (elapsed - (DURATION - 800)) / 800 : 1;
        ctx2d.globalAlpha = alpha;

        particles.forEach(p => {
            p.x     += p.vx;
            p.y     += p.vy;
            p.angle += p.spin;
            p.vy    += 0.08; // gravity

            if (p.y > canvas.height + 20) {
                p.y  = -20;
                p.x  = Math.random() * canvas.width;
                p.vy = Math.random() * 4 + 2;
            }

            ctx2d.save();
            ctx2d.translate(p.x, p.y);
            ctx2d.rotate(p.angle);
            ctx2d.fillStyle = p.color;

            if (p.shape === 'rect') {
                ctx2d.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
            } else {
                ctx2d.beginPath();
                ctx2d.arc(0, 0, p.size / 2, 0, Math.PI * 2);
                ctx2d.fill();
            }

            ctx2d.restore();
        });

        ctx2d.globalAlpha = 1;
        requestAnimationFrame(draw);
    }

    requestAnimationFrame(draw);
}

// ---------------------------------------------------------------------------
// Value display helpers
// ---------------------------------------------------------------------------

function updateRepsDisplay() {
    if (els.repsDisplay) {
        els.repsDisplay.textContent = state.reps;
    }
}

function updateWeightDisplay() {
    if (els.weightDisplay) {
        els.weightDisplay.textContent = state.weight > 0 ? `${state.weight} kg` : 'BW';
    }
}

function weightStep() {
    // Determine increment based on exercise category
    const step = currentStep();
    if (!step || !step.exercise) return 2.5;
    const cat = step.exercise.category;
    if (cat === 'barbell_compound' || cat === 'barbell_isolation') return 2.5;
    if (cat === 'dumbbell')  return 2.0;
    if (cat === 'cable')     return 2.5;
    if (cat === 'machine')   return 2.5;
    return 2.5;
}

function roundWeight(w) {
    // Round to nearest 0.25 kg
    return Math.round(w * 4) / 4;
}

// ---------------------------------------------------------------------------
// Timer utilities
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// TIMED EXERCISE — grace countdown + set timer
// ---------------------------------------------------------------------------

function startTimedGrace() {
    state.timedGraceFired = true;
    state.phase = 'grace';
    state.graceSecondsRemaining = 3;

    // Reuse existing grace overlay
    const graceArea = document.getElementById('grace-countdown-area');
    const graceLabel = document.getElementById('grace-exercise-label');
    const graceCountEl = document.getElementById('grace-countdown');

    if (graceArea) graceArea.classList.add('visible');
    if (graceLabel) graceLabel.textContent = 'Get into position…';
    if (graceCountEl) graceCountEl.textContent = state.graceSecondsRemaining;

    clearInterval(state.graceTimerInterval);
    state.graceTimerInterval = setInterval(() => {
        state.graceSecondsRemaining--;
        if (graceCountEl) graceCountEl.textContent = Math.max(0, state.graceSecondsRemaining);

        if (state.graceSecondsRemaining <= 0) {
            clearInterval(state.graceTimerInterval);
            state.graceTimerInterval = null;
            if (graceArea) graceArea.classList.remove('visible');
            state.phase = 'set';
            startSetTimer();
        }
    }, 1000);
}

function startSetTimer() {
    // Update button to "Stop"
    if (els.completeSetBtn) {
        els.completeSetBtn.textContent = '■ Stop';
    }

    clearInterval(state.setTimerInterval);
    state.setTimerInterval = setInterval(() => {
        if (state.paused) return;

        state.setDurationRemaining--;
        updateSetTimerDisplay();

        // Warning at 5 seconds
        if (state.setDurationRemaining <= 5 && state.setDurationRemaining > 0) {
            const timerEl = document.getElementById('duration-timer-display');
            if (timerEl) timerEl.classList.add('warning');
        }

        if (state.setDurationRemaining <= 0) {
            clearInterval(state.setTimerInterval);
            state.setTimerInterval = null;
            notifyEvent('timedSetComplete');
            const timerEl = document.getElementById('duration-timer-display');
            if (timerEl) {
                timerEl.classList.remove('warning');
                timerEl.classList.add('complete');
            }
            // Auto-complete the set
            logCurrentSet();
            proceedAfterSet();
        }
    }, 1000);
}

function updateSetTimerDisplay() {
    const timerEl = document.getElementById('duration-timer-display');
    if (timerEl) {
        timerEl.textContent = formatTime(Math.max(0, state.setDurationRemaining));
    }

    const fill = document.getElementById('duration-progress-fill');
    if (fill && state.setDurationTotal > 0) {
        const pct = (state.setDurationRemaining / state.setDurationTotal) * 100;
        fill.style.width = `${Math.max(0, pct)}%`;
    }
}

// ---------------------------------------------------------------------------
// UTILITY TIMERS
// ---------------------------------------------------------------------------

function clearAllTimers() {
    clearInterval(state.restTimerInterval);
    clearInterval(state.graceTimerInterval);
    clearInterval(state.autoAdvanceInterval);
    clearInterval(state.setTimerInterval);
    state.restTimerInterval    = null;
    state.graceTimerInterval   = null;
    state.autoAdvanceInterval  = null;
    state.setTimerInterval     = null;
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.max(0, seconds % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function showEl(el) {
    if (el) el.classList.remove('hidden');
}

function hideEl(el) {
    if (el) el.classList.add('hidden');
}

function toggleElVisibility(el, visible) {
    if (!el) return;
    if (visible) showEl(el); else hideEl(el);
}

function escHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `flash-message ${type}`;
    toast.textContent = message;
    toast.style.cssText = 'pointer-events:none;margin-bottom:8px;';

    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
