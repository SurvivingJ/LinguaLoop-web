// static/js/program_builder.js — WorkoutOS Program Builder (S10)
// Weekly calendar grid for building multi-week training programs.

document.addEventListener('DOMContentLoaded', () => {

    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------

    const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const DAY_SHORT = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

    let program = {
        name:              '',
        description:       '',
        goal:              'general',
        duration_weeks:    4,
        deload_weeks:      [],
        deload_volume_pct: 40,
        started_at:        '',
        weeks:             [],
    };

    // All plans loaded from API
    let allPlans = [];

    // Active dropdown state
    let activeDropdown = null; // { weekIndex, day, el }

    // ---------------------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------------------

    loadPlans().then(() => {
        if (window.EDIT_PROGRAM) {
            Object.assign(program, {
                name:              window.EDIT_PROGRAM.name              || '',
                description:       window.EDIT_PROGRAM.description       || '',
                goal:              window.EDIT_PROGRAM.goal              || 'general',
                duration_weeks:    window.EDIT_PROGRAM.duration_weeks    || 4,
                deload_weeks:      window.EDIT_PROGRAM.deload_weeks      || [],
                deload_volume_pct: window.EDIT_PROGRAM.deload_volume_pct || 40,
                started_at:        window.EDIT_PROGRAM.started_at        || '',
                weeks:             (window.EDIT_PROGRAM.weeks || []).map(w => ({
                    week_number: w.week_number,
                    is_deload:   w.is_deload || false,
                    days:        { ...makeEmptyDays(), ...w.days },
                })),
            });

            // Populate meta fields
            setInputVal('program-name',       program.name);
            setInputVal('program-description', program.description);
            setInputVal('program-goal',        program.goal);
            setInputVal('program-started-at',  program.started_at);
            setInputVal('deload-volume-pct',   program.deload_volume_pct);
        }

        // Ensure at least one week exists
        if (!program.weeks.length) {
            addWeek();
        }

        renderGrid();
        bindMetaFields();
    });

    // ---------------------------------------------------------------------------
    // Load plans from API
    // ---------------------------------------------------------------------------

    async function loadPlans() {
        try {
            const resp = await fetch('/api/exercises'); // fallback; swap to /api/plans if available
            // Try plans endpoint first
            const plansResp = await fetch('/api/plans').catch(() => null);
            if (plansResp && plansResp.ok) {
                allPlans = await plansResp.json();
            } else {
                allPlans = [];
            }
        } catch {
            allPlans = [];
        }
    }

    // ---------------------------------------------------------------------------
    // Week management
    // ---------------------------------------------------------------------------

    function makeEmptyDays() {
        return DAYS.reduce((acc, d) => { acc[d] = null; return acc; }, {});
    }

    function addWeek() {
        const weekNum = program.weeks.length + 1;
        let days = makeEmptyDays();

        // Copy pattern from previous week (if exists)
        if (program.weeks.length > 0) {
            const prev = program.weeks[program.weeks.length - 1];
            DAYS.forEach(d => {
                days[d] = prev.days[d] ? { ...prev.days[d] } : null;
            });
        }

        program.weeks.push({
            week_number: weekNum,
            is_deload:   false,
            days,
        });

        renderGrid();
    }

    function removeWeek(weekIndex) {
        if (program.weeks.length <= 1) {
            showToast('At least one week is required.', 'warning');
            return;
        }
        program.weeks.splice(weekIndex, 1);
        // Re-number
        program.weeks.forEach((w, i) => w.week_number = i + 1);
        renderGrid();
    }

    function copyWeek(weekIndex) {
        const src = program.weeks[weekIndex];
        if (!src) return;

        const newWeek = {
            week_number: program.weeks.length + 1,
            is_deload:   src.is_deload,
            days:        DAYS.reduce((acc, d) => {
                acc[d] = src.days[d] ? { ...src.days[d] } : null;
                return acc;
            }, {}),
        };
        program.weeks.push(newWeek);
        renderGrid();
    }

    function toggleDeload(weekIndex) {
        const week = program.weeks[weekIndex];
        if (!week) return;
        week.is_deload = !week.is_deload;
        renderGrid();
    }

    function assignDay(weekIndex, day, planEntry) {
        const week = program.weeks[weekIndex];
        if (!week) return;
        week.days[day] = planEntry; // null = rest, { plan_id, label } = plan
        renderGrid();
    }

    // ---------------------------------------------------------------------------
    // Render the full grid
    // ---------------------------------------------------------------------------

    function renderGrid() {
        const container = document.getElementById('program-grid');
        if (!container) return;

        container.innerHTML = '';

        // Day headers row
        const headerRow = document.createElement('div');
        headerRow.className = 'day-headers';
        headerRow.innerHTML = '<div class="day-header-spacer"></div>' +
            DAY_SHORT.map(d => `<div class="day-header">${d}</div>`).join('');
        container.appendChild(headerRow);

        // Week rows
        program.weeks.forEach((week, weekIndex) => {
            const row = document.createElement('div');
            row.className = `week-row${week.is_deload ? ' is-deload' : ''}`;
            row.dataset.week = weekIndex;

            // Week controls column
            const controls = document.createElement('div');
            controls.className = 'week-controls';
            controls.innerHTML = `
                <span class="week-label">W${week.week_number}</span>
                <button class="week-action-btn btn-copy-week" data-week="${weekIndex}" title="Copy week">⧉</button>
                <button class="week-action-btn deload-toggle${week.is_deload ? ' active' : ''}" data-week="${weekIndex}" title="Toggle deload">DL</button>
                <button class="week-action-btn btn-remove-week" data-week="${weekIndex}" title="Remove week">✕</button>
            `;
            row.appendChild(controls);

            // Day cells
            DAYS.forEach(day => {
                const cell = document.createElement('div');
                const assignment = week.days[day];
                let cellClass = 'day-cell';
                if (assignment) cellClass += ' assigned';
                else cellClass += ' rest';
                if (week.is_deload && assignment) cellClass += ' deload-row';

                cell.className = cellClass;
                cell.dataset.week = weekIndex;
                cell.dataset.day  = day;

                if (assignment) {
                    cell.innerHTML = `
                        <div class="day-cell-label">${escHtml(assignment.label || '')}</div>
                        ${week.is_deload ? '<div class="deload-badge-row">DELOAD</div>' : ''}
                    `;
                } else {
                    cell.innerHTML = `<div class="day-cell-label" style="color:var(--text-secondary);font-weight:400;font-style:italic">REST</div>`;
                }

                cell.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openDayDropdown(cell, weekIndex, day);
                });

                row.appendChild(cell);
            });

            container.appendChild(row);
        });

        // Add week button
        const addBtn = document.createElement('div');
        addBtn.className = 'add-week-row';
        addBtn.innerHTML = `<button class="btn btn-ghost" id="add-week-btn" style="width:100%;margin-top:8px">+ Add Week</button>`;
        container.appendChild(addBtn);

        // Bind controls
        container.querySelectorAll('.btn-copy-week').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                copyWeek(parseInt(btn.dataset.week));
            });
        });
        container.querySelectorAll('.deload-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleDeload(parseInt(btn.dataset.week));
            });
        });
        container.querySelectorAll('.btn-remove-week').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                removeWeek(parseInt(btn.dataset.week));
            });
        });
        document.getElementById('add-week-btn')?.addEventListener('click', addWeek);
    }

    // ---------------------------------------------------------------------------
    // Day dropdown (inline plan selector)
    // ---------------------------------------------------------------------------

    function openDayDropdown(cell, weekIndex, day) {
        // Close existing dropdown
        closeActiveDropdown();

        const dropdown = document.createElement('div');
        dropdown.className = 'day-dropdown';

        // REST option
        const restItem = document.createElement('div');
        restItem.className = 'day-dropdown-item rest-option';
        restItem.textContent = 'REST';
        restItem.addEventListener('click', (e) => {
            e.stopPropagation();
            assignDay(weekIndex, day, null);
            closeActiveDropdown();
        });
        dropdown.appendChild(restItem);

        // Plan options
        allPlans.forEach(plan => {
            const item = document.createElement('div');
            item.className = 'day-dropdown-item';
            item.innerHTML = `<strong>${escHtml(plan.name)}</strong>`;
            if (plan.description) {
                item.innerHTML += `<div style="font-size:10px;color:var(--text-secondary)">${escHtml(plan.description.slice(0, 40))}</div>`;
            }
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                assignDay(weekIndex, day, { plan_id: plan.id, label: plan.name });
                closeActiveDropdown();
            });
            dropdown.appendChild(item);
        });

        // Custom note option
        const customItem = document.createElement('div');
        customItem.className = 'day-dropdown-item';
        customItem.style.color = 'var(--text-secondary)';
        customItem.textContent = '✎ Custom note…';
        customItem.addEventListener('click', (e) => {
            e.stopPropagation();
            const note = prompt('Enter a note for this day (e.g. "Cardio — 30min"):');
            if (note !== null) {
                assignDay(weekIndex, day, { plan_id: null, label: note.trim() || 'Custom' });
            }
            closeActiveDropdown();
        });
        dropdown.appendChild(customItem);

        // Clear option (if currently assigned)
        const week = program.weeks[weekIndex];
        if (week?.days[day]) {
            const clearItem = document.createElement('div');
            clearItem.className = 'day-dropdown-item clear-option';
            clearItem.textContent = '✕ Clear';
            clearItem.addEventListener('click', (e) => {
                e.stopPropagation();
                assignDay(weekIndex, day, null);
                closeActiveDropdown();
            });
            dropdown.appendChild(clearItem);
        }

        cell.style.position = 'relative';
        cell.appendChild(dropdown);

        activeDropdown = { weekIndex, day, el: dropdown, cell };

        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', handleOutsideClick, { once: true });
        }, 0);
    }

    function handleOutsideClick() {
        closeActiveDropdown();
    }

    function closeActiveDropdown() {
        if (activeDropdown) {
            activeDropdown.el.remove();
            activeDropdown = null;
        }
    }

    // ---------------------------------------------------------------------------
    // Meta field binding
    // ---------------------------------------------------------------------------

    function bindMetaFields() {
        const fields = {
            'program-name':       (v) => program.name = v,
            'program-description': (v) => program.description = v,
            'program-goal':       (v) => program.goal = v,
            'program-started-at': (v) => program.started_at = v,
            'deload-volume-pct':  (v) => program.deload_volume_pct = parseInt(v) || 40,
        };

        Object.entries(fields).forEach(([id, setter]) => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => setter(el.value));
                el.addEventListener('change', () => setter(el.value));
            }
        });
    }

    // ---------------------------------------------------------------------------
    // Save program
    // ---------------------------------------------------------------------------

    const saveBtn = document.getElementById('save-program-btn');

    if (saveBtn) {
        saveBtn.addEventListener('click', saveProgram);
    }

    async function saveProgram() {
        // Validate
        if (!program.name.trim()) {
            showToast('Please enter a program name.', 'danger');
            document.getElementById('program-name')?.focus();
            return;
        }
        if (!program.weeks.length) {
            showToast('Add at least one week.', 'danger');
            return;
        }

        const payload = {
            name:              program.name.trim(),
            description:       program.description.trim(),
            goal:              program.goal,
            duration_weeks:    program.weeks.length,
            deload_weeks:      program.weeks.reduce((acc, w, i) => {
                if (w.is_deload) acc.push(i + 1);
                return acc;
            }, []),
            deload_volume_pct: program.deload_volume_pct,
            started_at:        program.started_at || null,
            weeks:             program.weeks.map(w => ({
                week_number: w.week_number,
                is_deload:   w.is_deload,
                days:        w.days,
            })),
        };

        const programId = window.EDIT_PROGRAM?.id;
        const url       = programId ? `/programs/${programId}` : '/programs/';
        const method    = 'POST';

        saveBtn.disabled    = true;
        saveBtn.textContent = 'Saving…';

        try {
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(payload),
            });

            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.error || `HTTP ${resp.status}`);
            }

            showToast('Program saved!', 'success');
            setTimeout(() => window.location.href = '/programs/', 800);

        } catch (err) {
            console.error('saveProgram error:', err);
            showToast(`Save failed: ${err.message}`, 'danger');
        } finally {
            saveBtn.disabled    = false;
            saveBtn.textContent = programId ? 'Update Program' : 'Save Program';
        }
    }

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    function setInputVal(id, value) {
        const el = document.getElementById(id);
        if (el && value !== undefined && value !== null) el.value = value;
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
        toast.style.pointerEvents = 'none';

        let container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            document.body.appendChild(container);
        }

        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }
});
