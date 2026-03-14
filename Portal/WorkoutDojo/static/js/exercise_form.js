// static/js/exercise_form.js — WorkoutOS Exercise Form (S9)
// Client-side behaviour for the exercise create/edit form.

document.addEventListener('DOMContentLoaded', () => {
    const categorySelect     = document.getElementById('category');
    const weightFields       = document.getElementById('weight-fields');
    const isCompoundInput    = document.getElementById('is_compound');
    const muscleSearchInput  = document.getElementById('muscle-search');
    const primaryCheckboxes  = document.querySelectorAll('.primary-muscle-checkbox');
    const secondaryCheckboxes = document.querySelectorAll('.secondary-muscle-checkbox');
    const form               = document.getElementById('exercise-form');

    // ---------------------------------------------------------------------------
    // Category → show/hide weight fields & update is_compound
    // ---------------------------------------------------------------------------

    const COMPOUND_CATEGORIES = ['barbell_compound'];
    const BODYWEIGHT_CATEGORIES = ['bodyweight'];

    function handleCategoryChange() {
        if (!categorySelect) return;
        const cat = categorySelect.value;

        // Show/hide weight-related fields for bodyweight exercises
        if (weightFields) {
            if (BODYWEIGHT_CATEGORIES.includes(cat)) {
                weightFields.style.display = 'none';
            } else {
                weightFields.style.display = '';
            }
        }

        // Update is_compound hidden field based on category
        if (isCompoundInput) {
            isCompoundInput.value = COMPOUND_CATEGORIES.includes(cat) ? 'true' : 'false';
        }

        // Update UI if there's a displayed compound indicator
        const compoundDisplay = document.getElementById('compound-display');
        if (compoundDisplay) {
            if (COMPOUND_CATEGORIES.includes(cat)) {
                compoundDisplay.textContent = 'Compound';
                compoundDisplay.className = 'badge badge-purple';
            } else {
                compoundDisplay.textContent = 'Isolation';
                compoundDisplay.className = 'badge badge-amber';
            }
        }
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', handleCategoryChange);
        // Run on load to set initial state
        handleCategoryChange();
    }

    // ---------------------------------------------------------------------------
    // Muscle group search filtering
    // ---------------------------------------------------------------------------

    function filterMuscleCheckboxes(query) {
        const q = query.toLowerCase().trim();

        // Filter primary muscle checkboxes
        document.querySelectorAll('.muscle-checkbox-item[data-group="primary"]').forEach(item => {
            const label = item.querySelector('label, span')?.textContent?.toLowerCase() || '';
            const input = item.querySelector('input');
            const muscleVal = input?.value?.toLowerCase() || '';
            const matches = !q || label.includes(q) || muscleVal.includes(q);
            item.style.display = matches ? '' : 'none';
        });

        // Filter secondary muscle checkboxes
        document.querySelectorAll('.muscle-checkbox-item[data-group="secondary"]').forEach(item => {
            const label = item.querySelector('label, span')?.textContent?.toLowerCase() || '';
            const input = item.querySelector('input');
            const muscleVal = input?.value?.toLowerCase() || '';
            const matches = !q || label.includes(q) || muscleVal.includes(q);
            item.style.display = matches ? '' : 'none';
        });
    }

    if (muscleSearchInput) {
        muscleSearchInput.addEventListener('input', () => {
            filterMuscleCheckboxes(muscleSearchInput.value);
        });
    }

    // ---------------------------------------------------------------------------
    // Mutual exclusion: if a muscle is primary, disable it in secondary & v.v.
    // ---------------------------------------------------------------------------

    function updateMuscleConflicts() {
        const checkedPrimary = new Set(
            [...primaryCheckboxes]
                .filter(cb => cb.checked)
                .map(cb => cb.value)
        );
        const checkedSecondary = new Set(
            [...secondaryCheckboxes]
                .filter(cb => cb.checked)
                .map(cb => cb.value)
        );

        secondaryCheckboxes.forEach(cb => {
            const item = cb.closest('.muscle-checkbox-item');
            if (checkedPrimary.has(cb.value)) {
                cb.disabled = true;
                cb.checked = false;
                if (item) item.style.opacity = '0.4';
            } else {
                cb.disabled = false;
                if (item) item.style.opacity = '';
            }
        });

        primaryCheckboxes.forEach(cb => {
            const item = cb.closest('.muscle-checkbox-item');
            if (checkedSecondary.has(cb.value)) {
                cb.disabled = true;
                cb.checked = false;
                if (item) item.style.opacity = '0.4';
            } else {
                cb.disabled = false;
                if (item) item.style.opacity = '';
            }
        });
    }

    primaryCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateMuscleConflicts);
    });
    secondaryCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateMuscleConflicts);
    });

    // Initial conflict check
    updateMuscleConflicts();

    // ---------------------------------------------------------------------------
    // Form validation before submit
    // ---------------------------------------------------------------------------

    if (form) {
        form.addEventListener('submit', (e) => {
            let valid = true;
            const errors = [];

            // Name required
            const nameInput = form.querySelector('input[name="name"]');
            if (!nameInput?.value?.trim()) {
                valid = false;
                errors.push('Exercise name is required.');
                nameInput?.classList.add('error');
            } else {
                nameInput?.classList.remove('error');
            }

            // At least one primary muscle
            const anyPrimaryChecked = [...primaryCheckboxes].some(cb => cb.checked);
            if (!anyPrimaryChecked) {
                valid = false;
                errors.push('Please select at least one primary muscle group.');

                // Highlight the primary muscle section
                const primarySection = document.getElementById('primary-muscles-section');
                if (primarySection) {
                    primarySection.style.borderColor = 'var(--danger)';
                    setTimeout(() => {
                        if (primarySection) primarySection.style.borderColor = '';
                    }, 3000);
                }
            }

            // Category required
            if (!categorySelect?.value) {
                valid = false;
                errors.push('Please select a category.');
            }

            if (!valid) {
                e.preventDefault();
                showFormErrors(errors);
                // Scroll to first error
                const firstError = form.querySelector('.error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }

    function showFormErrors(errors) {
        // Remove existing error display
        const existing = document.getElementById('form-error-banner');
        if (existing) existing.remove();

        if (!errors.length) return;

        const banner = document.createElement('div');
        banner.id = 'form-error-banner';
        banner.className = 'banner banner-danger';
        banner.innerHTML = `
            <span class="banner-icon">!</span>
            <div>
                ${errors.map(e => `<div>${e}</div>`).join('')}
            </div>
        `;

        // Insert at top of form
        if (form) {
            form.insertAdjacentElement('afterbegin', banner);
            banner.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Auto-remove after 5s
        setTimeout(() => banner.remove(), 5000);
    }

    // ---------------------------------------------------------------------------
    // Equipment field — optional autocomplete from common values
    // ---------------------------------------------------------------------------

    const equipmentInput = document.getElementById('equipment');
    const COMMON_EQUIPMENT = [
        'Barbell', 'EZ Bar', 'Dumbbell', 'Cable', 'Smith Machine',
        'Lat Pulldown', 'Leg Press', 'Hack Squat', 'Seated Cable Row',
        'Pec Deck', 'Chest Press Machine', 'Shoulder Press Machine',
        'Preacher Curl', 'GHD', 'Pull-up Bar', 'Dip Bars', 'Rings',
        'Resistance Band', 'Kettlebell', 'TRX'
    ];

    if (equipmentInput) {
        let equipmentDropdown = null;

        equipmentInput.addEventListener('input', () => {
            const val = equipmentInput.value.toLowerCase().trim();
            closeEquipmentDropdown();

            if (!val) return;

            const matches = COMMON_EQUIPMENT.filter(eq => eq.toLowerCase().includes(val));
            if (!matches.length) return;

            equipmentDropdown = document.createElement('div');
            equipmentDropdown.className = 'exercise-search-results';
            equipmentDropdown.style.position = 'absolute';
            equipmentDropdown.style.left = '0';
            equipmentDropdown.style.right = '0';
            equipmentDropdown.style.top = '100%';
            equipmentDropdown.style.zIndex = '200';

            matches.slice(0, 6).forEach(eq => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.textContent = eq;
                item.addEventListener('mousedown', (evt) => {
                    evt.preventDefault();
                    equipmentInput.value = eq;
                    closeEquipmentDropdown();
                });
                equipmentDropdown.appendChild(item);
            });

            const wrap = equipmentInput.closest('.form-group') || equipmentInput.parentElement;
            wrap.style.position = 'relative';
            wrap.appendChild(equipmentDropdown);
        });

        equipmentInput.addEventListener('blur', () => {
            setTimeout(closeEquipmentDropdown, 150);
        });

        function closeEquipmentDropdown() {
            if (equipmentDropdown) {
                equipmentDropdown.remove();
                equipmentDropdown = null;
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Voice name field — show character count hint
    // ---------------------------------------------------------------------------

    const voiceNameInput = document.getElementById('voice_name');
    if (voiceNameInput) {
        const nameInput = form?.querySelector('input[name="name"]');
        const voiceHint = document.getElementById('voice-name-hint');

        // Pre-fill hint from name field if voice_name is empty
        if (nameInput && !voiceNameInput.value) {
            voiceNameInput.placeholder = nameInput.value || 'e.g. D B Row';
        }

        if (nameInput) {
            nameInput.addEventListener('input', () => {
                if (!voiceNameInput.value) {
                    voiceNameInput.placeholder = nameInput.value || 'e.g. D B Row';
                }
            });
        }
    }
});
