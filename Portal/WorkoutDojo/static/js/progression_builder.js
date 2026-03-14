// static/js/progression_builder.js — WorkoutOS Progression Builder
// Drag-and-drop exercise chain with transition rule editors.

document.addEventListener('DOMContentLoaded', () => {

    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------

    let progression = {
        name: '',
        exercises: [],   // [{exercise_id, exercise}] in order
        rules: [],       // [{from_exercise_id, to_exercise_id, trigger_reps, trigger_sets, transition, blend_new_sets, blend_old_sets}]
    };

    let allExercises = [];
    let dragSrcIndex = null;

    // ---------------------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------------------

    loadExercises().then(() => {
        if (window.BUILDER_DATA?.progression) {
            const p = window.BUILDER_DATA.progression;
            progression.name = p.name || '';

            // Rebuild exercises array from IDs
            progression.exercises = (p.exercises || []).map(exId => ({
                exercise_id: exId,
                exercise: allExercises.find(e => e.id === exId) || null,
            }));

            progression.rules = (p.rules || []).map(r => ({ ...r }));

            const nameInput = document.getElementById('prog-name');
            if (nameInput) nameInput.value = progression.name;

            renderList();
        }
    });

    // ---------------------------------------------------------------------------
    // Load exercises
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
    // Add exercise
    // ---------------------------------------------------------------------------

    function addExercise(exerciseId) {
        const exercise = allExercises.find(e => e.id === exerciseId);
        if (!exercise) return;

        // Don't allow duplicates
        if (progression.exercises.some(e => e.exercise_id === exerciseId)) {
            showToast('Exercise already in progression.', 'warning');
            return;
        }

        const entry = { exercise_id: exerciseId, exercise };
        progression.exercises.push(entry);

        // Auto-create rule from previous exercise
        if (progression.exercises.length >= 2) {
            const prev = progression.exercises[progression.exercises.length - 2];
            // Only add if no rule already exists for this pair
            const exists = progression.rules.some(
                r => r.from_exercise_id === prev.exercise_id && r.to_exercise_id === exerciseId
            );
            if (!exists) {
                progression.rules.push({
                    from_exercise_id: prev.exercise_id,
                    to_exercise_id: exerciseId,
                    trigger_reps: 10,
                    trigger_sets: 3,
                    transition: 'replace',
                    blend_new_sets: 1,
                    blend_old_sets: 2,
                });
            }
        }

        renderList();
    }

    // ---------------------------------------------------------------------------
    // Remove exercise
    // ---------------------------------------------------------------------------

    function removeExercise(index) {
        const removed = progression.exercises[index];
        if (!removed) return;

        progression.exercises.splice(index, 1);

        // Remove rules referencing the removed exercise
        progression.rules = progression.rules.filter(
            r => r.from_exercise_id !== removed.exercise_id &&
                 r.to_exercise_id !== removed.exercise_id
        );

        // Rebuild rules for new adjacent pairs
        rebuildMissingRules();
        renderList();
    }

    // ---------------------------------------------------------------------------
    // Rebuild missing rules for adjacent pairs
    // ---------------------------------------------------------------------------

    function rebuildMissingRules() {
        for (let i = 0; i < progression.exercises.length - 1; i++) {
            const fromId = progression.exercises[i].exercise_id;
            const toId = progression.exercises[i + 1].exercise_id;

            const exists = progression.rules.some(
                r => r.from_exercise_id === fromId && r.to_exercise_id === toId
            );

            if (!exists) {
                progression.rules.push({
                    from_exercise_id: fromId,
                    to_exercise_id: toId,
                    trigger_reps: 10,
                    trigger_sets: 3,
                    transition: 'replace',
                    blend_new_sets: 1,
                    blend_old_sets: 2,
                });
            }
        }

        // Remove rules for non-adjacent pairs
        const adjacentPairs = new Set();
        for (let i = 0; i < progression.exercises.length - 1; i++) {
            adjacentPairs.add(
                progression.exercises[i].exercise_id + ':' + progression.exercises[i + 1].exercise_id
            );
        }
        progression.rules = progression.rules.filter(
            r => adjacentPairs.has(r.from_exercise_id + ':' + r.to_exercise_id)
        );
    }

    // ---------------------------------------------------------------------------
    // Find rule for a pair
    // ---------------------------------------------------------------------------

    function findRule(fromId, toId) {
        return progression.rules.find(
            r => r.from_exercise_id === fromId && r.to_exercise_id === toId
        );
    }

    // ---------------------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------------------

    function renderList() {
        const list = document.getElementById('chain-list');
        if (!list) return;
        list.innerHTML = '';

        if (!progression.exercises.length) {
            list.innerHTML = `
                <div class="chain-list-empty">
                    <div style="font-size:32px;opacity:0.4">+</div>
                    <p>Add exercises above to build your progression chain.</p>
                </div>
            `;
            return;
        }

        progression.exercises.forEach((entry, idx) => {
            const name = entry.exercise?.name || 'Unknown Exercise';
            const cat = entry.exercise?.category || '';

            // Exercise card
            const card = document.createElement('div');
            card.className = 'chain-entry';
            card.draggable = true;
            card.dataset.index = idx;

            card.innerHTML = `
                <div class="chain-entry-header">
                    <span class="drag-handle" title="Drag to reorder">&#8942;&#8942;</span>
                    <span class="chain-entry-order">${idx + 1}</span>
                    <div style="flex:1;min-width:0">
                        <div class="chain-entry-name">${escHtml(name)}</div>
                        <div class="chain-entry-cat">${formatCategory(cat)}</div>
                    </div>
                    <button class="chain-entry-remove" data-index="${idx}" title="Remove">&#10005;</button>
                </div>
            `;

            // Events
            card.addEventListener('dragstart', onDragStart);
            card.addEventListener('dragover', onDragOver);
            card.addEventListener('dragleave', onDragLeave);
            card.addEventListener('drop', onDrop);
            card.addEventListener('dragend', onDragEnd);

            card.querySelector('.chain-entry-remove')?.addEventListener('click', (e) => {
                e.stopPropagation();
                removeExercise(parseInt(e.currentTarget.dataset.index));
            });

            list.appendChild(card);

            // Rule editor between this and next exercise
            if (idx < progression.exercises.length - 1) {
                const nextEntry = progression.exercises[idx + 1];
                const rule = findRule(entry.exercise_id, nextEntry.exercise_id);

                if (rule) {
                    const connector = document.createElement('div');
                    connector.className = 'rule-connector';

                    const nextName = nextEntry.exercise?.name || 'Unknown';
                    const isBlend = rule.transition === 'blend';

                    connector.innerHTML = `
                        <div class="rule-editor" data-rule-from="${entry.exercise_id}" data-rule-to="${nextEntry.exercise_id}">
                            <div class="rule-editor-header">Transition Rule</div>

                            <div class="rule-trigger">
                                <span>When you hit</span>
                                <input type="number" class="rule-reps" min="1" max="100" value="${rule.trigger_reps}">
                                <span>reps for</span>
                                <input type="number" class="rule-sets" min="1" max="20" value="${rule.trigger_sets}">
                                <span>sets</span>
                            </div>

                            <div class="rule-transition-toggle">
                                <button class="${!isBlend ? 'active' : ''}" data-transition="replace">Replace</button>
                                <button class="${isBlend ? 'active' : ''}" data-transition="blend">Blend</button>
                            </div>

                            <div class="blend-config" style="display:${isBlend ? 'flex' : 'none'}">
                                <input type="number" class="rule-blend-new" min="0" max="20" value="${rule.blend_new_sets}">
                                <span>sets of ${escHtml(nextName)} +</span>
                                <input type="number" class="rule-blend-old" min="0" max="20" value="${rule.blend_old_sets}">
                                <span>sets of ${escHtml(name)}</span>
                            </div>
                        </div>
                    `;

                    // Wire up rule editor events
                    const editor = connector.querySelector('.rule-editor');

                    editor.querySelector('.rule-reps')?.addEventListener('input', (e) => {
                        rule.trigger_reps = parseInt(e.target.value) || 1;
                    });
                    editor.querySelector('.rule-sets')?.addEventListener('input', (e) => {
                        rule.trigger_sets = parseInt(e.target.value) || 1;
                    });

                    editor.querySelectorAll('.rule-transition-toggle button').forEach(btn => {
                        btn.addEventListener('click', () => {
                            rule.transition = btn.dataset.transition;
                            editor.querySelectorAll('.rule-transition-toggle button').forEach(b =>
                                b.classList.toggle('active', b === btn)
                            );
                            const blendCfg = editor.querySelector('.blend-config');
                            if (blendCfg) blendCfg.style.display = rule.transition === 'blend' ? 'flex' : 'none';
                        });
                    });

                    editor.querySelector('.rule-blend-new')?.addEventListener('input', (e) => {
                        rule.blend_new_sets = parseInt(e.target.value) || 0;
                    });
                    editor.querySelector('.rule-blend-old')?.addEventListener('input', (e) => {
                        rule.blend_old_sets = parseInt(e.target.value) || 0;
                    });

                    list.appendChild(connector);
                }
            }
        });
    }

    // ---------------------------------------------------------------------------
    // Drag-and-drop
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
        if (e.currentTarget.dataset.index !== String(dragSrcIndex)) {
            e.currentTarget.classList.add('drag-over');
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

        const [moved] = progression.exercises.splice(dragSrcIndex, 1);
        progression.exercises.splice(targetIndex, 0, moved);

        // Rebuild rules for new adjacency
        rebuildMissingRules();

        dragSrcIndex = null;
        renderList();
    }

    function onDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
        document.querySelectorAll('.chain-entry').forEach(el => el.classList.remove('drag-over'));
        dragSrcIndex = null;
    }

    // ---------------------------------------------------------------------------
    // Name live update
    // ---------------------------------------------------------------------------

    const nameInput = document.getElementById('prog-name');
    if (nameInput) {
        nameInput.addEventListener('input', () => {
            progression.name = nameInput.value;
        });
    }

    // ---------------------------------------------------------------------------
    // Save
    // ---------------------------------------------------------------------------

    async function save() {
        if (nameInput) progression.name = nameInput.value.trim();

        if (!progression.name) {
            showToast('Please enter a progression name.', 'danger');
            nameInput?.focus();
            return;
        }
        if (progression.exercises.length < 2) {
            showToast('Add at least 2 exercises to form a progression.', 'danger');
            return;
        }

        const payload = {
            name: progression.name,
            exercises: progression.exercises.map(e => e.exercise_id),
            rules: progression.rules.map(r => ({
                from_exercise_id: r.from_exercise_id,
                to_exercise_id: r.to_exercise_id,
                trigger_reps: r.trigger_reps,
                trigger_sets: r.trigger_sets,
                transition: r.transition,
                blend_new_sets: r.blend_new_sets,
                blend_old_sets: r.blend_old_sets,
            })),
        };

        const progId = window.BUILDER_DATA?.progression?.id;
        const url = progId ? `/progressions/${progId}` : '/progressions/';

        const saveBtn = document.querySelector('.save-bar button');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving\u2026'; }

        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.error || `HTTP ${resp.status}`);
            }

            showToast('Progression saved!', 'success');
            setTimeout(() => window.location.href = '/progressions/', 800);

        } catch (err) {
            console.error('save error:', err);
            showToast(`Save failed: ${err.message}`, 'danger');
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = progId ? 'Update Progression' : 'Save Progression';
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
    // Expose globals
    // ---------------------------------------------------------------------------

    window.addExerciseToProgression = function(id) {
        addExercise(id);
    };
    window.saveProgression = save;

    // Initial render
    renderList();
});
