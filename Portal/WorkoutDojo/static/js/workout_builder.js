// static/js/workout_builder.js — WorkoutOS Workout Builder (S7)
// Drag-and-drop exercise list with set management.

document.addEventListener('DOMContentLoaded', () => {

    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------

    let plan = {
        name: '',
        description: '',
        entries: [],
    };

    // Track all exercises fetched from the API
    let allExercises = [];

    // Drag state
    let dragSrcIndex = null;

    // ---------------------------------------------------------------------------
    // Init — load exercises and pre-populate if editing
    // ---------------------------------------------------------------------------

    loadExercises().then(() => {
        if (window.EDIT_PLAN) {
            plan.name        = window.EDIT_PLAN.name        || '';
            plan.description = window.EDIT_PLAN.description || '';
            plan.entries     = (window.EDIT_PLAN.entries || []).map(e => ({
                exercise_id:    e.exercise_id,
                exercise:       allExercises.find(ex => ex.id === e.exercise_id) || null,
                order:          e.order,
                superset_group: e.superset_group || null,
                filler_id:      e.filler_id      || null,
                filler_type:    e.filler_type    || 'none',
                starting_weight_kg: e.starting_weight_kg || null,
                sets: (e.sets || []).map(s => ({ ...s })),
            }));

            const nameInput = document.getElementById('plan-name');
            const descInput = document.getElementById('plan-desc');
            if (nameInput) nameInput.value = plan.name;
            if (descInput) descInput.value = plan.description;

            renderExerciseList();
        }
    });

    // ---------------------------------------------------------------------------
    // Load exercises from API
    // ---------------------------------------------------------------------------

    async function loadExercises() {
        try {
            const resp = await fetch('/api/exercises');
            if (!resp.ok) throw new Error('Failed to fetch exercises');
            allExercises = await resp.json();
        } catch (err) {
            console.error('loadExercises:', err);
            allExercises = [];
        }
    }

    // ---------------------------------------------------------------------------
    // Exercise search
    // ---------------------------------------------------------------------------

    // Exercise search is handled by the template's inline filterPickerList().
    // The template calls addExerciseToWorkout() globally — exposed below.

    // ---------------------------------------------------------------------------
    // Add exercise to plan
    // ---------------------------------------------------------------------------

    function addExercise(exercise) {
        const entry = {
            exercise_id:    exercise.id,
            exercise:       exercise,
            order:          plan.entries.length + 1,
            superset_group: null,
            filler_id:      null,
            filler_type:    'none',
            starting_weight_kg: null,
            sets: [
                { rep_min: 8, rep_max: 10, rest_seconds: 90, is_warmup: false, target_rpe: null }
            ],
        };
        plan.entries.push(entry);
        renderExerciseList();
    }

    // ---------------------------------------------------------------------------
    // Remove exercise
    // ---------------------------------------------------------------------------

    function removeExercise(index) {
        plan.entries.splice(index, 1);
        // Re-number orders
        plan.entries.forEach((e, i) => e.order = i + 1);
        renderExerciseList();
    }

    // ---------------------------------------------------------------------------
    // Add set to entry
    // ---------------------------------------------------------------------------

    function addSet(entryIndex, isWarmup = false) {
        const entry = plan.entries[entryIndex];
        if (!entry) return;
        const lastSet = entry.sets[entry.sets.length - 1] || {};
        entry.sets.push({
            rep_min:      lastSet.rep_min      || 8,
            rep_max:      lastSet.rep_max      || 10,
            rest_seconds: lastSet.rest_seconds || 90,
            is_warmup:    isWarmup,
            target_rpe:   null,
        });
        renderExerciseList();
    }

    // ---------------------------------------------------------------------------
    // Remove set from entry
    // ---------------------------------------------------------------------------

    function removeSet(entryIndex, setIndex) {
        const entry = plan.entries[entryIndex];
        if (!entry) return;
        if (entry.sets.length <= 1) return; // always keep at least 1 set
        entry.sets.splice(setIndex, 1);
        renderExerciseList();
    }

    // ---------------------------------------------------------------------------
    // Render the exercise list
    // ---------------------------------------------------------------------------

    function renderExerciseList() {
        const list = document.getElementById('entry-list');
        if (!list) return;

        list.innerHTML = '';

        if (!plan.entries.length) {
            list.innerHTML = `
                <div class="entry-list-empty">
                    <div style="font-size:32px;opacity:0.4">+</div>
                    <p>Search for exercises above to add them to your workout.</p>
                </div>
            `;
            return;
        }

        plan.entries.forEach((entry, entryIndex) => {
            const item = document.createElement('div');
            item.className = 'entry-card';
            item.draggable = true;
            item.dataset.index = entryIndex;

            const exerciseName = entry.exercise?.name || 'Unknown Exercise';
            const category     = entry.exercise?.category || '';
            const supersetBadge = entry.superset_group
                ? `<span class="superset-group-indicator">SS: ${escHtml(entry.superset_group)}</span>`
                : '';

            item.innerHTML = `
                <div class="entry-card-header">
                    <span class="drag-handle" title="Drag to reorder">&#8942;&#8942;</span>
                    <div style="flex:1;min-width:0">
                        <div class="entry-name">${escHtml(exerciseName)}</div>
                        <div style="font-size:12px;color:var(--text-secondary)">${formatCategory(category)} ${supersetBadge}</div>
                    </div>
                    <button class="btn-remove-exercise set-row-remove" data-index="${entryIndex}" title="Remove exercise">✕</button>
                </div>

                <div class="entry-card-body">
                    <div class="set-row-headers">
                        <span class="set-col-label"></span>
                        <span class="set-col-label">Reps Min</span>
                        <span class="set-col-label">Reps Max</span>
                        <span class="set-col-label">Rest (s)</span>
                        <span class="set-col-label"></span>
                    </div>
                    <div class="set-rows-list">
                        ${entry.sets.map((set, setIndex) => renderSetRow(entryIndex, setIndex, set)).join('')}
                    </div>
                    <div class="entry-extras" style="margin-bottom:10px;">
                        <div class="form-group">
                            <label style="font-size:10px;margin-bottom:4px;">Starting Weight (kg)</label>
                            <input type="number" class="form-control input-starting-weight" data-entry="${entryIndex}"
                                   min="0" step="0.5" placeholder="Optional"
                                   value="${entry.starting_weight_kg || ''}"
                                   style="font-size:13px;padding:7px 10px;min-height:36px;">
                        </div>
                    </div>
                    <div class="entry-actions">
                        <button class="btn btn-ghost btn-sm add-set-btn" data-entry="${entryIndex}">+ Add Set</button>
                        <button class="btn btn-ghost btn-sm add-warmup-btn" data-entry="${entryIndex}">+ Warmup</button>
                    </div>
                </div>
            `;

            // Attach drag events
            item.addEventListener('dragstart', onDragStart);
            item.addEventListener('dragover',  onDragOver);
            item.addEventListener('dragleave', onDragLeave);
            item.addEventListener('drop',      onDrop);
            item.addEventListener('dragend',   onDragEnd);

            // Remove exercise button
            item.querySelector('.btn-remove-exercise')?.addEventListener('click', (e) => {
                e.stopPropagation();
                removeExercise(parseInt(e.currentTarget.dataset.index));
            });

            // Add set buttons
            item.querySelector('.add-set-btn')?.addEventListener('click', (e) => {
                addSet(parseInt(e.currentTarget.dataset.entry), false);
            });

            item.querySelector('.add-warmup-btn')?.addEventListener('click', (e) => {
                addSet(parseInt(e.currentTarget.dataset.entry), true);
            });

            // Starting weight listener
            item.querySelector('.input-starting-weight')?.addEventListener('input', (e) => {
                const ei = parseInt(e.target.dataset.entry);
                if (plan.entries[ei]) {
                    const val = parseFloat(e.target.value);
                    plan.entries[ei].starting_weight_kg = isNaN(val) ? null : val;
                }
            });

            // Set input listeners (live update plan state)
            item.querySelectorAll('.set-row').forEach(row => {
                const ei = parseInt(row.dataset.entry);
                const si = parseInt(row.dataset.set);

                row.querySelector('.input-rep-min')?.addEventListener('input', (e) => {
                    if (plan.entries[ei]?.sets[si])
                        plan.entries[ei].sets[si].rep_min = parseInt(e.target.value) || 0;
                });
                row.querySelector('.input-rep-max')?.addEventListener('input', (e) => {
                    if (plan.entries[ei]?.sets[si])
                        plan.entries[ei].sets[si].rep_max = parseInt(e.target.value) || 0;
                });
                row.querySelector('.input-rest')?.addEventListener('input', (e) => {
                    if (plan.entries[ei]?.sets[si])
                        plan.entries[ei].sets[si].rest_seconds = parseInt(e.target.value) || 60;
                });
                row.querySelector('.btn-remove-set')?.addEventListener('click', () => {
                    removeSet(ei, si);
                });
            });

            list.appendChild(item);
        });
    }

    function renderSetRow(entryIndex, setIndex, set) {
        const warmupDot = set.is_warmup
            ? `<span class="set-row-num" style="color:var(--warning);font-weight:700">W</span>`
            : `<span class="set-row-num">${setIndex + 1}</span>`;

        return `
            <div class="set-row" data-entry="${entryIndex}" data-set="${setIndex}" style="${set.is_warmup ? 'opacity:0.75' : ''}">
                ${warmupDot}
                <input class="input-rep-min" type="number" min="1" max="100" value="${set.rep_min}" placeholder="8">
                <input class="input-rep-max" type="number" min="1" max="100" value="${set.rep_max}" placeholder="10">
                <input class="input-rest" type="number" min="0" max="600" value="${set.rest_seconds}" placeholder="90">
                <button class="set-row-remove btn-remove-set" title="Remove set">✕</button>
            </div>
        `;
    }

    // ---------------------------------------------------------------------------
    // Drag-and-drop (HTML5 draggable API)
    // ---------------------------------------------------------------------------

    function onDragStart(e) {
        dragSrcIndex = parseInt(e.currentTarget.dataset.index);
        e.currentTarget.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', dragSrcIndex);
    }

    function onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const target = e.currentTarget;
        if (target.dataset.index !== String(dragSrcIndex)) {
            target.classList.add('drag-over');
        }
    }

    function onDragLeave(e) {
        e.currentTarget.classList.remove('drag-over');
    }

    function onDrop(e) {
        e.preventDefault();
        const targetIndex = parseInt(e.currentTarget.dataset.index);
        e.currentTarget.classList.remove('drag-over');

        if (dragSrcIndex === null || dragSrcIndex === targetIndex) return;

        // Reorder entries
        const [moved] = plan.entries.splice(dragSrcIndex, 1);
        plan.entries.splice(targetIndex, 0, moved);

        // Re-number orders
        plan.entries.forEach((entry, i) => entry.order = i + 1);

        dragSrcIndex = null;
        renderExerciseList();
    }

    function onDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
        document.querySelectorAll('.entry-card').forEach(el => el.classList.remove('drag-over'));
        dragSrcIndex = null;
    }

    // ---------------------------------------------------------------------------
    // Plan name / description live update
    // ---------------------------------------------------------------------------

    const planNameInput = document.getElementById('plan-name');
    const planDescInput = document.getElementById('plan-desc');

    if (planNameInput) {
        planNameInput.addEventListener('input', () => {
            plan.name = planNameInput.value;
        });
    }
    if (planDescInput) {
        planDescInput.addEventListener('input', () => {
            plan.description = planDescInput.value;
        });
    }

    // ---------------------------------------------------------------------------
    // Save plan
    // ---------------------------------------------------------------------------

    // Save is triggered by the template's onclick="saveWorkout()" — exposed below.

    async function savePlan() {
        // Sync name/description from inputs (in case not updated via events)
        if (planNameInput) plan.name = planNameInput.value.trim();
        if (planDescInput) plan.description = planDescInput.value.trim();

        // Validate
        if (!plan.name) {
            showToast('Please enter a workout name.', 'danger');
            planNameInput?.focus();
            return;
        }
        if (!plan.entries.length) {
            showToast('Add at least one exercise before saving.', 'danger');
            return;
        }

        // Build payload
        const payload = {
            name:        plan.name,
            description: plan.description,
            entries:     plan.entries.map((e, i) => ({
                exercise_id:    e.exercise_id,
                order:          i + 1,
                superset_group: e.superset_group || null,
                filler_id:      e.filler_id      || null,
                filler_type:    e.filler_type    || 'none',
                starting_weight_kg: e.starting_weight_kg || null,
                sets:           e.sets.map(s => ({
                    rep_min:      s.rep_min,
                    rep_max:      s.rep_max,
                    rest_seconds: s.rest_seconds,
                    is_warmup:    s.is_warmup,
                    target_rpe:   s.target_rpe || null,
                })),
            })),
        };

        // Determine URL (new vs edit)
        const planId  = window.EDIT_PLAN?.id;
        const url     = planId ? `/workouts/${planId}` : '/workouts/';
        const method  = 'POST';

        const saveBtn = document.querySelector('.save-bar button');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }

        try {
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.error || `HTTP ${resp.status}`);
            }

            showToast('Workout saved!', 'success');
            setTimeout(() => window.location.href = '/workouts/', 800);

        } catch (err) {
            console.error('savePlan error:', err);
            showToast(`Save failed: ${err.message}`, 'danger');
        } finally {
            if (saveBtn) {
                saveBtn.disabled  = false;
                saveBtn.textContent = planId ? 'Update Workout' : 'Save Workout';
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    function formatCategory(cat) {
        if (!cat) return '';
        return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `flash-message ${type}`;
        toast.textContent = message;
        toast.style.cssText = 'pointer-events:none; margin-bottom:8px;';

        let container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            document.body.appendChild(container);
        }

        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // ---------------------------------------------------------------------------
    // Expose globals for template onclick handlers
    // ---------------------------------------------------------------------------

    window.addExerciseToWorkout = function(id, name, category) {
        const exercise = allExercises.find(ex => ex.id === id) || { id, name, category };
        addExercise(exercise);
    };
    window.saveWorkout = savePlan;

    // Initial render
    renderExerciseList();
});
