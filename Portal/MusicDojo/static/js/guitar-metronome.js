/**
 * Guitar Metronome - Practice Session Controller
 * Extends metronome functionality with BPM ladder, session logging, and progression tracking
 */

class GuitarMetronome {
    constructor() {
        this.currentExercise = null;
        this.currentProgress = null;
        this.bpmLadder = [];
        this.currentLadderIndex = 0;
        this.sessionStartTime = null;
        this.tempo = 60;
        this.subdivision = 'eighth';
        this.isPlaying = false;
        this.intervalId = null;

        // Session log data
        this.sessionData = {
            maxBpmAchieved: 0,
            qualityRating: 2,  // Default: focused
            accuracyTier: 'silver',  // Default: silver
            notes: ''
        };
    }

    async init(exercise, progress) {
        this.currentExercise = exercise;
        this.currentProgress = progress;

        // Load BPM ladder from API
        await this.loadBPMLadder();

        // Set initial tempo
        if (progress && progress.current_bpm_ceiling) {
            this.tempo = progress.current_bpm_ceiling;
            this.subdivision = progress.current_subdivision || exercise.subdivision_default;
        } else {
            this.tempo = exercise.bpm_floor;
            this.subdivision = exercise.subdivision_default;
        }

        // Render UI
        this.render();

        // Set up event listeners
        this.setupEventListeners();

        // Reset session timer
        this.sessionStartTime = null;
        this.sessionData.maxBpmAchieved = this.tempo;
    }

    async loadBPMLadder() {
        try {
            const startBpm = this.currentProgress?.current_bpm_ceiling || this.currentExercise.bpm_floor;
            const ceilingBpm = this.currentExercise.bpm_ceiling;

            const response = await fetch(
                `/api/guitar/bpm-ladder/${this.currentExercise.id}?start_bpm=${startBpm}&ceiling_bpm=${ceilingBpm}`
            );
            const data = await response.json();
            this.bpmLadder = data.ladder;

            // Find current index in ladder
            this.currentLadderIndex = this.bpmLadder.findIndex(bpm => bpm >= this.tempo);
            if (this.currentLadderIndex === -1) {
                this.currentLadderIndex = this.bpmLadder.length - 1;
            }
        } catch (error) {
            console.error('Error loading BPM ladder:', error);
            // Fallback: simple ladder
            this.bpmLadder = [this.tempo];
        }
    }

    render() {
        const container = document.getElementById('guitar-practice-content');
        if (!container) return;

        // Render BPM ladder
        const ladderHTML = this.bpmLadder.map((bpm, index) => {
            let className = 'ladder-rung';
            if (bpm < this.tempo) className += ' completed';
            if (bpm === this.tempo) className += ' current';
            return `<span class="${className}" data-bpm="${bpm}">${bpm}</span>`;
        }).join('');

        // Advancement status
        let advancementHTML = '';
        if (this.currentProgress && this.currentProgress.advancement_ready) {
            advancementHTML = `
                <div class="advancement-notice">
                    🏆 You're ready to advance to ${this.currentProgress.next_bpm} BPM!
                    <button class="btn btn-sm btn-success" id="advance-bpm-btn">Advance Now</button>
                </div>
            `;
        }

        container.innerHTML = `
            <div class="practice-header">
                <h3>${this.currentExercise.name}</h3>
                <button class="btn-back" id="back-to-exercises">← Back to Exercises</button>
            </div>

            ${advancementHTML}

            <div class="exercise-description-box">
                <h4>Exercise Description:</h4>
                <p>${this.currentExercise.description}</p>
            </div>

            <div class="bpm-ladder-container">
                <h4>BPM Progression Ladder</h4>
                <div class="bpm-ladder">${ladderHTML}</div>
            </div>

            <div class="metronome-display">
                <div class="tempo-display" id="tempo-display">${this.tempo}</div>
                <div class="subdivision-display" id="subdivision-display">${this.subdivision} notes</div>
            </div>

            <div class="metronome-controls">
                <button class="btn btn-lg btn-primary" id="metro-start">Start</button>
                <button class="btn btn-lg btn-danger hidden" id="metro-stop">Stop</button>
                <div class="tempo-adjustment">
                    <button class="btn btn-secondary" id="tempo-down">-5 BPM</button>
                    <button class="btn btn-secondary" id="tempo-up">+5 BPM</button>
                </div>
                <button class="btn btn-secondary" id="next-rung">Next BPM Rung (${this.getNextRung() || '—'})</button>
            </div>

            <div class="subdivision-controls mt-md">
                <label>Subdivision:</label>
                <select id="subdivision-select">
                    <option value="quarter" ${this.subdivision === 'quarter' ? 'selected' : ''}>Quarter Notes</option>
                    <option value="eighth" ${this.subdivision === 'eighth' ? 'selected' : ''}>Eighth Notes</option>
                    <option value="sixteenth" ${this.subdivision === 'sixteenth' ? 'selected' : ''}>16th Notes</option>
                    <option value="sextuplet" ${this.subdivision === 'sextuplet' ? 'selected' : ''}>Sextuplets</option>
                </select>
            </div>

            <div class="session-timer mt-md">
                <span class="timer-label">Session Time:</span>
                <span id="session-timer" class="timer-display">00:00</span>
            </div>

            <div class="session-log-section mt-lg">
                <h4>Log This Session</h4>

                <div class="form-row">
                    <label>Max Clean BPM Achieved:</label>
                    <input type="number" id="log-bpm" value="${this.tempo}" min="${this.currentExercise.bpm_floor}" max="${this.currentExercise.bpm_ceiling}">
                </div>

                <div class="form-row">
                    <label>Subdivision:</label>
                    <select id="log-subdivision">
                        <option value="quarter">Quarter Notes</option>
                        <option value="eighth" selected>Eighth Notes</option>
                        <option value="sixteenth">16th Notes</option>
                        <option value="sextuplet">Sextuplets</option>
                    </select>
                </div>

                <div class="form-row">
                    <label>Quality (Effort Level):</label>
                    <div class="quality-buttons">
                        <button class="quality-btn" data-quality="1">😴 Easy</button>
                        <button class="quality-btn active" data-quality="2">💪 Focused</button>
                        <button class="quality-btn" data-quality="3">🔥 Hard Push</button>
                    </div>
                </div>

                <div class="form-row">
                    <label>Accuracy:</label>
                    <div class="accuracy-buttons">
                        <button class="accuracy-btn gold" data-tier="gold">🥇 Gold (≥90%)</button>
                        <button class="accuracy-btn silver active" data-tier="silver">🥈 Silver (70-89%)</button>
                        <button class="accuracy-btn bronze" data-tier="bronze">🥉 Bronze (<70%)</button>
                    </div>
                </div>

                <div class="form-row">
                    <label>Notes (optional):</label>
                    <textarea id="log-notes" rows="3" placeholder="Any observations, challenges, or breakthroughs..."></textarea>
                </div>

                <button class="btn btn-primary btn-large" id="save-session-btn">Save Session</button>
            </div>
        `;

        // Set initial log subdivision
        document.getElementById('log-subdivision').value = this.subdivision;
    }

    setupEventListeners() {
        // Back button
        document.getElementById('back-to-exercises')?.addEventListener('click', () => {
            this.stop();
            screenManager.showScreen('guitar-exercises');
        });

        // Advance BPM button (if present)
        document.getElementById('advance-bpm-btn')?.addEventListener('click', () => {
            if (this.currentProgress.next_bpm) {
                this.tempo = this.currentProgress.next_bpm;
                this.updateDisplay();
                alert(`Advanced to ${this.tempo} BPM! Keep up the great work!`);
            }
        });

        // Start/Stop buttons
        document.getElementById('metro-start')?.addEventListener('click', () => this.start());
        document.getElementById('metro-stop')?.addEventListener('click', () => this.stop());

        // Tempo adjustment
        document.getElementById('tempo-down')?.addEventListener('click', () => {
            this.tempo = Math.max(this.currentExercise.bpm_floor, this.tempo - 5);
            this.updateDisplay();
        });

        document.getElementById('tempo-up')?.addEventListener('click', () => {
            this.tempo = Math.min(this.currentExercise.bpm_ceiling, this.tempo + 5);
            this.updateDisplay();
        });

        // Next rung button
        document.getElementById('next-rung')?.addEventListener('click', () => {
            const nextBpm = this.getNextRung();
            if (nextBpm) {
                this.tempo = nextBpm;
                this.currentLadderIndex++;
                this.updateDisplay();
                this.updateLadderDisplay();
            }
        });

        // BPM ladder rungs - click to jump to that BPM
        document.querySelectorAll('.ladder-rung').forEach(rung => {
            rung.addEventListener('click', () => {
                const bpm = parseInt(rung.dataset.bpm);
                this.tempo = bpm;
                this.currentLadderIndex = this.bpmLadder.indexOf(bpm);
                this.updateDisplay();
                this.updateLadderDisplay();
            });
        });

        // Subdivision select
        document.getElementById('subdivision-select')?.addEventListener('change', (e) => {
            this.subdivision = e.target.value;
            this.updateDisplay();
        });

        // Quality buttons
        document.querySelectorAll('.quality-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.sessionData.qualityRating = parseInt(btn.dataset.quality);
            });
        });

        // Accuracy buttons
        document.querySelectorAll('.accuracy-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.accuracy-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.sessionData.accuracyTier = btn.dataset.tier;
            });
        });

        // Save session button
        document.getElementById('save-session-btn')?.addEventListener('click', () => this.saveSession());
    }

    start() {
        if (this.isPlaying) return;

        window.gameActive = true;
        audioManager.initialize();
        this.isPlaying = true;

        // Start session timer if not already started
        if (!this.sessionStartTime) {
            this.sessionStartTime = Date.now();
            this.startSessionTimer();
        }

        // Show/hide buttons
        document.getElementById('metro-start')?.classList.add('hidden');
        document.getElementById('metro-stop')?.classList.remove('hidden');

        // Start metronome
        this.startMetronome();

        // Track max BPM achieved
        if (this.tempo > this.sessionData.maxBpmAchieved) {
            this.sessionData.maxBpmAchieved = this.tempo;
            document.getElementById('log-bpm').value = this.tempo;
        }
    }

    stop() {
        window.gameActive = false;
        this.isPlaying = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        // Show/hide buttons
        document.getElementById('metro-start')?.classList.remove('hidden');
        document.getElementById('metro-stop')?.classList.add('hidden');
    }

    startMetronome() {
        const subdivisionMultiplier = {
            quarter: 1,
            eighth: 2,
            sixteenth: 4,
            sextuplet: 6
        };

        const beatsPerSecond = this.tempo / 60;
        const clicksPerSecond = beatsPerSecond * subdivisionMultiplier[this.subdivision];
        const interval = 1000 / clicksPerSecond;

        let clickCount = 0;

        this.intervalId = setInterval(() => {
            if (!this.isPlaying) return;

            clickCount++;
            const isAccent = (clickCount % subdivisionMultiplier[this.subdivision] === 1);

            audioManager.playClick(isAccent ? 1000 : 800, 0.05, isAccent);
        }, interval);
    }

    startSessionTimer() {
        const timerEl = document.getElementById('session-timer');
        if (!timerEl) return;

        const updateTimer = () => {
            if (!this.sessionStartTime) return;

            const elapsed = Math.floor((Date.now() - this.sessionStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

            if (this.sessionStartTime) {
                requestAnimationFrame(updateTimer);
            }
        };

        requestAnimationFrame(updateTimer);
    }

    getNextRung() {
        if (this.currentLadderIndex < this.bpmLadder.length - 1) {
            return this.bpmLadder[this.currentLadderIndex + 1];
        }
        return null;
    }

    updateDisplay() {
        const tempoEl = document.getElementById('tempo-display');
        const subdivisionEl = document.getElementById('subdivision-display');
        const nextRungBtn = document.getElementById('next-rung');

        if (tempoEl) tempoEl.textContent = this.tempo;
        if (subdivisionEl) subdivisionEl.textContent = `${this.subdivision} notes`;
        if (nextRungBtn) nextRungBtn.textContent = `Next BPM Rung (${this.getNextRung() || '—'})`;

        // If playing, restart metronome with new tempo
        if (this.isPlaying) {
            clearInterval(this.intervalId);
            this.startMetronome();
        }

        // Update ladder display
        this.updateLadderDisplay();
    }

    updateLadderDisplay() {
        document.querySelectorAll('.ladder-rung').forEach(rung => {
            const bpm = parseInt(rung.dataset.bpm);
            rung.className = 'ladder-rung';
            if (bpm < this.tempo) {
                rung.classList.add('completed');
            }
            if (bpm === this.tempo) {
                rung.classList.add('current');
            }
        });
    }

    saveSession() {
        const durationSeconds = this.sessionStartTime
            ? Math.floor((Date.now() - this.sessionStartTime) / 1000)
            : 0;

        if (durationSeconds < 10) {
            alert('Session too short to log (minimum 10 seconds).');
            return;
        }

        const bpmAchieved = parseInt(document.getElementById('log-bpm').value);
        const subdivision = document.getElementById('log-subdivision').value;
        const notes = document.getElementById('log-notes').value.trim();

        // Log the practice session
        const logEntry = storageManager.logGuitarPractice(
            this.currentExercise.id,
            bpmAchieved,
            subdivision,
            this.sessionData.qualityRating,
            this.sessionData.accuracyTier,
            durationSeconds,
            notes,
            this.currentExercise
        );

        // Check for new milestones
        const newMilestones = storageManager.checkGuitarMilestones();
        if (newMilestones.length > 0) {
            const milestoneNames = newMilestones.map(m => m.name).join(', ');
            alert(`🎉 New Milestone${newMilestones.length > 1 ? 's' : ''} Unlocked: ${milestoneNames}!`);
        }

        // Show success message
        alert('Session logged successfully! Keep up the great work!');

        // Reset session and go back to exercises
        this.stop();
        screenManager.showScreen('guitar-exercises');

        // Update guitar exercises stats
        if (window.guitar_exercises) {
            window.guitar_exercises.updateStats();
        }
    }
}

// Create singleton instance
const guitar_metronome = new GuitarMetronome();
