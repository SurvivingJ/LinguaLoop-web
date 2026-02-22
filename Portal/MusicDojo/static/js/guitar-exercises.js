/**
 * Guitar Exercises - Main Controller
 * Manages category navigation, exercise list, and progress tracking
 */

class GuitarExercises {
    constructor() {
        this.exercises = [];
        this.currentCategory = null;
        this.categories = [
            { id: 'chromatic', name: 'Chromatic/Spider', icon: '🕷️', count: 6 },
            { id: 'scales', name: 'Scale Runs', icon: '🎼', count: 5 },
            { id: 'legato', name: 'Legato', icon: '🎵', count: 5 },
            { id: 'trills', name: 'Trills', icon: '〰️', count: 5 },
            { id: 'alternate_picking', name: 'Alternate Picking', icon: '⚡', count: 5 },
            { id: 'economy_sweep', name: 'Economy/Sweep', icon: '🌊', count: 5 },
            { id: 'string_skipping', name: 'String Skipping', icon: '⬆️', count: 5 },
            { id: 'bending_vibrato', name: 'Bending/Vibrato', icon: '〜', count: 6 },
            { id: 'chord_transitions', name: 'Chord Transitions', icon: '🎸', count: 5 },
            { id: 'palm_muting', name: 'Palm Muting', icon: '🤚', count: 5 }
        ];
    }

    async init() {
        try {
            // Load all exercises from API
            const response = await fetch('/api/guitar/exercises');
            const data = await response.json();
            this.exercises = data.exercises;

            // Render category navigation
            this.renderCategories();

            // Set up event listeners
            this.setupEventListeners();

            // Load first category by default
            if (this.categories.length > 0) {
                this.loadCategory(this.categories[0].id);
            }
        } catch (error) {
            console.error('Error loading guitar exercises:', error);
            this.showError('Failed to load exercises. Please try again.');
        }
    }

    renderCategories() {
        const container = document.getElementById('guitar-category-nav');
        if (!container) return;

        container.innerHTML = '';

        this.categories.forEach(category => {
            const stats = storageManager.getGuitarCategoryStats(category.id);
            const sessions = stats ? stats.sessions : 0;
            const avgBpm = stats ? Math.round(stats.avg_bpm) : 0;

            const btn = document.createElement('button');
            btn.className = 'category-btn';
            btn.dataset.category = category.id;
            btn.innerHTML = `
                <div class="category-icon">${category.icon}</div>
                <div class="category-name">${category.name}</div>
                <div class="category-stats">
                    <span>${sessions} sessions</span>
                    ${avgBpm > 0 ? `<span>Avg: ${avgBpm} BPM</span>` : ''}
                </div>
            `;

            btn.addEventListener('click', () => this.loadCategory(category.id));
            container.appendChild(btn);
        });
    }

    async loadCategory(categoryId) {
        this.currentCategory = categoryId;

        // Update active button
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === categoryId);
        });

        // Filter exercises by category
        const categoryExercises = this.exercises.filter(ex => ex.category === categoryId);

        // Render exercise list
        this.renderExerciseList(categoryExercises);
    }

    renderExerciseList(exercises) {
        const container = document.getElementById('guitar-exercise-list');
        if (!container) return;

        if (exercises.length === 0) {
            container.innerHTML = '<p class="text-secondary">No exercises found in this category.</p>';
            return;
        }

        container.innerHTML = '';

        exercises.forEach(exercise => {
            const progress = storageManager.getGuitarProgress(exercise.id);
            const card = this.createExerciseCard(exercise, progress);
            container.appendChild(card);
        });
    }

    createExerciseCard(exercise, progress) {
        const card = document.createElement('div');
        card.className = 'exercise-card';

        // Determine progress status
        let progressHTML = '';
        if (progress) {
            const bpm = progress.current_bpm_ceiling;
            const subdivision = progress.current_subdivision;
            const ready = progress.advancement_ready;

            progressHTML = `
                <div class="exercise-progress">
                    <span>Current: ${bpm} BPM (${subdivision})</span>
                    ${ready ? '<span class="advancement-ready">🏆 Ready to advance!</span>' : ''}
                </div>
            `;
        } else {
            progressHTML = '<div class="exercise-progress"><span class="text-secondary">Not started</span></div>';
        }

        // Difficulty badge
        const difficultyClass = exercise.difficulty_tier;
        const difficultyLabel = exercise.difficulty_tier.charAt(0).toUpperCase() + exercise.difficulty_tier.slice(1);

        card.innerHTML = `
            <div class="exercise-header">
                <h4>${exercise.name}</h4>
                <span class="difficulty-badge ${difficultyClass}">${difficultyLabel}</span>
            </div>
            <p class="exercise-description">${exercise.description}</p>
            ${progressHTML}
            <div class="exercise-meta">
                <span>BPM Range: ${exercise.bpm_floor}-${exercise.bpm_ceiling}</span>
                <span>Default: ${exercise.subdivision_default} notes</span>
            </div>
            <div class="exercise-actions">
                <button class="btn btn-primary" data-action="practice" data-exercise-id="${exercise.id}">
                    Practice
                </button>
                <button class="btn btn-secondary" data-action="view-progress" data-exercise-id="${exercise.id}">
                    Progress
                </button>
            </div>
        `;

        return card;
    }

    setupEventListeners() {
        // Delegate click events for exercise actions
        document.addEventListener('click', (e) => {
            const target = e.target;

            // Practice button
            if (target.dataset.action === 'practice') {
                const exerciseId = target.dataset.exerciseId;
                this.startPracticeSession(exerciseId);
            }

            // View progress button
            if (target.dataset.action === 'view-progress') {
                const exerciseId = target.dataset.exerciseId;
                this.viewExerciseProgress(exerciseId);
            }
        });

        // Dashboard button
        const dashboardBtn = document.getElementById('guitar-dashboard-btn');
        if (dashboardBtn) {
            dashboardBtn.addEventListener('click', () => {
                screenManager.showScreen('guitar-dashboard');
                if (window.guitarDashboard) {
                    window.guitarDashboard.init();
                }
            });
        }
    }

    startPracticeSession(exerciseId) {
        // Find the exercise
        const exercise = this.exercises.find(ex => ex.id === exerciseId);
        if (!exercise) {
            console.error('Exercise not found:', exerciseId);
            return;
        }

        // Get current progress
        const progress = storageManager.getGuitarProgress(exerciseId);

        // Navigate to practice session screen
        screenManager.showScreen('guitar-practice-session');

        // Initialize guitar metronome with this exercise
        if (window.guitar_metronome) {
            window.guitar_metronome.init(exercise, progress);
        }
    }

    viewExerciseProgress(exerciseId) {
        const exercise = this.exercises.find(ex => ex.id === exerciseId);
        const progress = storageManager.getGuitarProgress(exerciseId);
        const logs = storageManager.getGuitarPracticeLogs(exerciseId);

        if (!progress || logs.length === 0) {
            alert('No practice data available for this exercise yet.');
            return;
        }

        // Show progress modal or navigate to detailed view
        this.showProgressModal(exercise, progress, logs);
    }

    showProgressModal(exercise, progress, logs) {
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${exercise.name} - Progress</h3>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="progress-summary">
                        <div class="stat-item">
                            <label>Current Level:</label>
                            <value>${progress.current_bpm_ceiling} BPM (${progress.current_subdivision})</value>
                        </div>
                        <div class="stat-item">
                            <label>Best All-Time:</label>
                            <value>${progress.best_bpm_all_time} BPM</value>
                        </div>
                        <div class="stat-item">
                            <label>Sessions at Current:</label>
                            <value>${progress.sessions_at_current_level}</value>
                        </div>
                        <div class="stat-item">
                            <label>Total Sessions:</label>
                            <value>${logs.length}</value>
                        </div>
                        ${progress.advancement_ready ? `
                        <div class="stat-item highlight">
                            <label>Status:</label>
                            <value>🏆 Ready to advance to ${progress.next_bpm} BPM!</value>
                        </div>
                        ` : ''}
                    </div>

                    <h4 class="mt-lg">Recent Sessions</h4>
                    <div class="recent-sessions">
                        ${logs.slice(-10).reverse().map(log => `
                            <div class="session-entry">
                                <div class="session-date">${new Date(log.date).toLocaleDateString()}</div>
                                <div class="session-details">
                                    <span>${log.bpm_achieved} BPM (${log.subdivision})</span>
                                    <span class="accuracy-${log.accuracy_tier}">${log.accuracy_tier.toUpperCase()}</span>
                                    <span>${Math.floor(log.duration_seconds / 60)} min</span>
                                </div>
                                ${log.notes ? `<div class="session-notes">${log.notes}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    showError(message) {
        const container = document.getElementById('guitar-exercise-list');
        if (container) {
            container.innerHTML = `<div class="error-message">${message}</div>`;
        }
    }

    /**
     * Update statistics display
     */
    updateStats() {
        const totalTime = storageManager.getTotalGuitarPracticeTime();
        const streak = storageManager.load('guitar_exercises').practice_streak.count;
        const milestones = storageManager.getGuitarMilestones();

        // Update stats in home screen if visible
        const statsEl = document.getElementById('guitar-stats-summary');
        if (statsEl) {
            statsEl.innerHTML = `
                <div class="stat-item">
                    <span class="stat-value">${Math.floor(totalTime / 3600)}h ${Math.floor((totalTime % 3600) / 60)}m</span>
                    <span class="stat-label">Practice Time</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${streak}</span>
                    <span class="stat-label">Day Streak</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${milestones.length}</span>
                    <span class="stat-label">Milestones</span>
                </div>
            `;
        }
    }
}

// Create singleton instance
const guitar_exercises = new GuitarExercises();
