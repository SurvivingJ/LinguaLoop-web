/**
 * Guitar 100K - Rep Tracker Dashboard Controller
 * Manages the 100,000 rep tracking dashboard with exercise cards,
 * log modal, rep calculator, and instrument switching.
 */
class Guitar100K {
    constructor() {
        this.currentInstrument = 'guitar';
        this.exercises = [];
        this.initialized = false;
    }

    async init() {
        if (this.initialized) {
            // Re-fetch on re-entry to pick up changes
            await this.fetchExercises(this.currentInstrument);
            this.renderDashboard();
            return;
        }

        this.bindEvents();
        await this.fetchExercises(this.currentInstrument);
        this.renderDashboard();
        this.initialized = true;
    }

    bindEvents() {
        // Instrument tabs
        document.querySelectorAll('.g100k-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchInstrument(tab.dataset.instrument);
            });
        });

        // Slonimsky Lab button
        const labBtn = document.getElementById('g100k-lab-btn');
        if (labBtn) {
            labBtn.addEventListener('click', () => {
                screenManager.showScreen('slonimsky-lab');
                if (window.slonimsky_lab && window.slonimsky_lab.init) {
                    window.slonimsky_lab.init();
                }
            });
        }

        // Export button
        const exportBtn = document.getElementById('g100k-export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportData());
        }

        // Modal close
        const closeBtn = document.getElementById('g100k-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeLogModal());
        }

        // Modal overlay click to close
        const modal = document.getElementById('g100k-log-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeLogModal();
            });
        }

        // Calculator inputs
        ['g100k-calc-time', 'g100k-calc-bpm', 'g100k-calc-subdivision'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => this.updateCalculator());
            }
        });

        // Submit log
        const submitBtn = document.getElementById('g100k-log-submit');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitLog());
        }

        // Slonimsky Lab back button
        const slonimskyBack = document.getElementById('slonimsky-back-btn');
        if (slonimskyBack) {
            slonimskyBack.addEventListener('click', (e) => {
                e.preventDefault();
                screenManager.showScreen('guitar-100k');
            });
        }
    }

    async fetchExercises(instrument) {
        try {
            const response = await fetch(`/api/guitar100k/exercises/${instrument}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            this.exercises = data.exercises || [];
        } catch (error) {
            console.error('Failed to fetch exercises:', error);
            this.exercises = [];
        }
    }

    renderDashboard() {
        this.renderOverallProgress();
        this.renderExerciseGrid();
    }

    renderOverallProgress() {
        const totalReps = this.exercises.reduce((sum, ex) => sum + (ex.total_reps || 0), 0);
        const totalTarget = this.exercises.reduce((sum, ex) => sum + (ex.target_reps || 5000), 0);
        const pct = totalTarget > 0 ? Math.min(100, (totalReps / totalTarget) * 100) : 0;

        const bar = document.getElementById('g100k-overall-bar');
        const text = document.getElementById('g100k-overall-text');

        if (bar) bar.style.width = `${pct}%`;
        if (text) text.textContent = `${totalReps.toLocaleString()} / ${totalTarget.toLocaleString()} reps (${pct.toFixed(1)}%)`;
    }

    renderExerciseGrid() {
        const grid = document.getElementById('g100k-exercise-grid');
        if (!grid) return;

        if (this.exercises.length === 0) {
            grid.innerHTML = '<p class="text-secondary">No exercises found. Add some from the Slonimsky Lab!</p>';
            return;
        }

        // Group by category
        const grouped = {};
        this.exercises.forEach(ex => {
            const cat = ex.category || 'other';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(ex);
        });

        let html = '';
        for (const [category, exercises] of Object.entries(grouped)) {
            html += `<div class="g100k-category-label">${this.formatCategory(category)}</div>`;
            exercises.forEach(ex => {
                const pct = ex.target_reps > 0 ? Math.min(100, (ex.total_reps / ex.target_reps) * 100) : 0;
                const completed = pct >= 100;
                html += `
                    <div class="g100k-exercise-card ${completed ? 'completed' : ''}" data-id="${ex.id}">
                        <div class="g100k-card-header">
                            <span class="g100k-card-name">${ex.name}</span>
                            ${ex.source === 'slonimsky_lab' ? '<span class="g100k-badge-slonimsky">S</span>' : ''}
                            ${completed ? '<span class="g100k-badge-complete">✓</span>' : ''}
                        </div>
                        <div class="g100k-card-progress">
                            <div class="g100k-card-bar-wrapper">
                                <div class="g100k-card-bar-fill" style="width:${pct}%"></div>
                            </div>
                            <span class="g100k-card-reps">${ex.total_reps.toLocaleString()} / ${ex.target_reps.toLocaleString()}</span>
                        </div>
                        <div class="g100k-card-footer">
                            <span class="g100k-card-bpm">${ex.latest_bpm > 0 ? ex.latest_bpm + ' BPM' : '—'}</span>
                            ${ex.best_bpm > 0 ? `<span class="g100k-card-best">Best: ${ex.best_bpm}</span>` : ''}
                            <button class="btn btn-sm btn-primary g100k-log-btn" data-id="${ex.id}">Log</button>
                        </div>
                    </div>
                `;
            });
        }

        grid.innerHTML = html;

        // Bind log buttons
        grid.querySelectorAll('.g100k-log-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openLogModal(btn.dataset.id);
            });
        });
    }

    formatCategory(category) {
        const labels = {
            technique: '🕷️ Technique',
            chromatic: '🎵 Chromatic',
            scales: '🎼 Scales',
            legato: '🎶 Legato',
            picking: '⚡ Picking',
            sweep: '🌊 Sweep',
            expression: '〜 Expression',
            rhythm: '🥁 Rhythm',
            slonimsky: '🔬 Slonimsky',
            arpeggios: '🎵 Arpeggios',
            intervals: '↕️ Intervals',
            articulation: '✋ Articulation',
            chords: '🎸 Chords',
            accompaniment: '🎹 Accompaniment',
            independence: '🤲 Independence',
            other: '📋 Other'
        };
        return labels[category] || `📋 ${category.charAt(0).toUpperCase() + category.slice(1)}`;
    }

    openLogModal(exerciseId) {
        const exercise = this.exercises.find(ex => ex.id === exerciseId);
        if (!exercise) return;

        document.getElementById('g100k-modal-title').textContent = `Log: ${exercise.name}`;
        document.getElementById('g100k-log-exercise-id').value = exerciseId;
        document.getElementById('g100k-manual-reps').value = '';
        document.getElementById('g100k-log-bpm').value = exercise.latest_bpm || 60;
        document.getElementById('g100k-calc-bpm').value = exercise.latest_bpm || 60;

        this.updateCalculator();
        document.getElementById('g100k-log-modal').style.display = 'flex';
    }

    closeLogModal() {
        document.getElementById('g100k-log-modal').style.display = 'none';
    }

    updateCalculator() {
        const time = parseFloat(document.getElementById('g100k-calc-time').value) || 0;
        const bpm = parseFloat(document.getElementById('g100k-calc-bpm').value) || 0;
        const sub = parseFloat(document.getElementById('g100k-calc-subdivision').value) || 1;
        const reps = Math.floor(time * bpm * sub);

        document.getElementById('g100k-calc-reps').textContent = reps.toLocaleString();
    }

    async submitLog() {
        const exerciseId = document.getElementById('g100k-log-exercise-id').value;
        const manualReps = document.getElementById('g100k-manual-reps').value;
        const bpm = parseInt(document.getElementById('g100k-log-bpm').value) || 60;
        const time = parseFloat(document.getElementById('g100k-calc-time').value) || 5;
        const calcBpm = parseFloat(document.getElementById('g100k-calc-bpm').value) || 60;
        const sub = parseFloat(document.getElementById('g100k-calc-subdivision').value) || 1;

        const reps = manualReps ? parseInt(manualReps) : Math.floor(time * calcBpm * sub);
        const duration = Math.round(time * 60); // Convert minutes to seconds

        if (reps <= 0) {
            alert('Reps must be greater than 0');
            return;
        }

        try {
            const response = await fetch('/api/guitar100k/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instrument: this.currentInstrument,
                    exercise_id: exerciseId,
                    reps: reps,
                    bpm: bpm,
                    duration: duration
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to log practice');
            }

            this.closeLogModal();
            await this.fetchExercises(this.currentInstrument);
            this.renderDashboard();
        } catch (error) {
            console.error('Error logging practice:', error);
            alert('Failed to log practice: ' + error.message);
        }
    }

    async switchInstrument(instrument) {
        this.currentInstrument = instrument;

        // Update tab active state
        document.querySelectorAll('.g100k-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.instrument === instrument);
        });

        await this.fetchExercises(instrument);
        this.renderDashboard();
    }

    exportData() {
        window.location.href = '/api/guitar100k/export';
    }
}

// Create singleton instance
window.guitar_100k = new Guitar100K();
