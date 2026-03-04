/**
 * Sight Reading Mode
 * Generates and displays sheet music for guitar and piano with audio playback
 */

class SightReading {
    constructor() {
        this.currentExercise = null;
        this.currentElo = 1000;
        this.session = {
            correct: 0,
            total: 0,
            startTime: null
        };
        this.isPlaying = false;
        this.synth = null;
        this.scheduledEvents = [];
        this.noteElements = [];
        this.showTab = true;
        this.initialized = false;
    }

    /**
     * Initialize the sight reading mode
     */
    async init() {
        const container = document.getElementById('sight-reading-content');
        if (!container) return;

        // Load saved preferences
        const progress = storageManager.load('mode_progress');
        const prefs = (progress && progress.sight_reading && progress.sight_reading.preferences) || {
            instrument: 'piano',
            guitar_tone: 'acoustic',
            scales: ['random'],
            tempo: null,
            note_types: ['random'],
            measures: 4
        };

        container.innerHTML = `
            <div class="controls" id="sr-controls">
                <!-- Instrument Selection -->
                <div class="control-row">
                    <label>Instrument:</label>
                    <div class="instrument-toggle">
                        <button class="btn ${prefs.instrument === 'piano' ? 'active' : ''}" id="sr-btn-piano" data-instrument="piano">🎹 Piano</button>
                        <button class="btn ${prefs.instrument === 'guitar' ? 'active' : ''}" id="sr-btn-guitar" data-instrument="guitar">🎸 Guitar</button>
                    </div>
                </div>

                <!-- Guitar Tone (hidden when piano selected) -->
                <div class="control-row ${prefs.instrument === 'piano' ? 'hidden' : ''}" id="sr-guitar-tone-row">
                    <label>Guitar Tone:</label>
                    <div class="instrument-toggle">
                        <button class="btn ${prefs.guitar_tone === 'acoustic' ? 'active' : ''}" id="sr-btn-acoustic" data-tone="acoustic">Acoustic</button>
                        <button class="btn ${prefs.guitar_tone === 'electric' ? 'active' : ''}" id="sr-btn-electric" data-tone="electric">Electric</button>
                    </div>
                </div>

                <!-- Settings Panel -->
                <div class="sr-settings-panel">
                    <button class="btn btn-secondary sr-settings-toggle" id="sr-toggle-settings">⚙ Exercise Settings</button>
                    <div class="sr-settings-body hidden" id="sr-settings-body">
                        <!-- Scale Selection -->
                        <div class="control-row">
                            <label>Scale:</label>
                            <div class="sr-scale-selector">
                                <label class="sr-checkbox-label">
                                    <input type="checkbox" id="sr-scale-random" ${prefs.scales[0] === 'random' ? 'checked' : ''}>
                                    Random (based on difficulty)
                                </label>
                                <div id="sr-scale-options" class="${prefs.scales[0] === 'random' ? 'hidden' : ''}">
                                    <!-- Populated dynamically -->
                                </div>
                            </div>
                        </div>

                        <!-- Tempo -->
                        <div class="control-row">
                            <label>Tempo:</label>
                            <div class="sr-tempo-selector">
                                <label class="sr-checkbox-label">
                                    <input type="checkbox" id="sr-tempo-random" ${prefs.tempo === null ? 'checked' : ''}>
                                    Random (based on difficulty)
                                </label>
                                <div id="sr-tempo-manual" class="${prefs.tempo === null ? 'hidden' : ''}">
                                    <input type="range" id="sr-tempo-slider" min="40" max="200" value="${prefs.tempo || 80}">
                                    <span id="sr-tempo-value">${prefs.tempo || 80} BPM</span>
                                </div>
                            </div>
                        </div>

                        <!-- Note Types -->
                        <div class="control-row">
                            <label>Note Types:</label>
                            <div class="sr-note-type-selector">
                                <label class="sr-checkbox-label">
                                    <input type="checkbox" id="sr-notes-random" ${prefs.note_types[0] === 'random' ? 'checked' : ''}>
                                    Random (based on difficulty)
                                </label>
                                <div id="sr-note-type-options" class="${prefs.note_types[0] === 'random' ? 'hidden' : ''}">
                                    <label class="sr-checkbox-label"><input type="checkbox" data-note-type="w" ${prefs.note_types.includes('w') ? 'checked' : ''}> Whole</label>
                                    <label class="sr-checkbox-label"><input type="checkbox" data-note-type="h" ${prefs.note_types.includes('h') ? 'checked' : ''}> Half</label>
                                    <label class="sr-checkbox-label"><input type="checkbox" data-note-type="q" ${prefs.note_types.includes('q') ? 'checked' : ''}> Quarter</label>
                                    <label class="sr-checkbox-label"><input type="checkbox" data-note-type="8" ${prefs.note_types.includes('8') ? 'checked' : ''}> Eighth</label>
                                    <label class="sr-checkbox-label"><input type="checkbox" data-note-type="16" ${prefs.note_types.includes('16') ? 'checked' : ''}> 16th</label>
                                </div>
                            </div>
                        </div>

                        <!-- Measures -->
                        <div class="control-row">
                            <label>Measures:</label>
                            <div class="instrument-toggle">
                                <button class="btn ${prefs.measures === 2 ? 'active' : ''}" data-measures="2">2</button>
                                <button class="btn ${prefs.measures === 4 ? 'active' : ''}" data-measures="4">4</button>
                                <button class="btn ${prefs.measures === 8 ? 'active' : ''}" data-measures="8">8</button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="control-row">
                    <button class="btn btn-primary" id="sr-start">Start Session</button>
                </div>
            </div>

            <!-- Exercise Area -->
            <div id="sr-exercise-area" class="display-area hidden">
                <div class="sr-exercise-info" id="sr-exercise-info">
                    <!-- Scale name, key, tempo displayed here -->
                </div>

                <div id="sr-notation-container">
                    <!-- VexFlow renders here -->
                </div>

                <div class="sr-playback-controls">
                    <button class="btn btn-success" id="sr-play">▶ Play</button>
                    <button class="btn btn-secondary" id="sr-stop-playback" disabled>■ Stop</button>
                    <span id="sr-tempo-display"></span>
                    <label class="sr-checkbox-label ${prefs.instrument === 'piano' ? 'hidden' : ''}" id="sr-tab-toggle-label">
                        <input type="checkbox" id="sr-tab-toggle" checked> Show TAB
                    </label>
                </div>

                <!-- Self Assessment -->
                <div class="sr-assessment" id="sr-assessment">
                    <p>How did you do?</p>
                    <div class="sr-assessment-buttons">
                        <button class="btn btn-success" id="sr-got-it">✓ Got It</button>
                        <button class="btn btn-danger" id="sr-struggled">✗ Struggled</button>
                    </div>
                </div>

                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="sr-session-correct">0</div>
                        <div class="stat-label">Got It</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="sr-session-total">0</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="sr-session-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                </div>

                <div class="mt-lg">
                    <button class="btn btn-primary" id="sr-next">Next Exercise</button>
                    <button class="btn btn-danger" id="sr-end-session">End Session</button>
                </div>
            </div>

            <!-- Results -->
            <div id="sr-results" class="display-area hidden">
                <h3>Session Complete!</h3>
                <div class="stats-row mt-lg">
                    <div class="stat">
                        <div class="stat-value" id="sr-results-correct">0</div>
                        <div class="stat-label">Got It</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="sr-results-accuracy">0%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="sr-results-elo">+0</div>
                        <div class="stat-label">Elo Change</div>
                    </div>
                </div>
                <div class="mt-lg">
                    <button class="btn btn-primary" id="sr-restart">New Session</button>
                </div>
            </div>
        `;

        this.setupEventListeners();
        this.loadAvailableScales();
        this.initialized = true;
    }

    /**
     * Get current preferences from UI state
     */
    getPreferences() {
        const instrument = document.querySelector('.instrument-toggle .active[data-instrument]');
        const guitarTone = document.querySelector('#sr-guitar-tone-row .active[data-tone]');
        const measures = document.querySelector('[data-measures].active');

        const scaleRandom = document.getElementById('sr-scale-random');
        const tempoRandom = document.getElementById('sr-tempo-random');
        const notesRandom = document.getElementById('sr-notes-random');

        let scales = ['random'];
        if (scaleRandom && !scaleRandom.checked) {
            const checked = document.querySelectorAll('#sr-scale-options input[type="checkbox"]:checked');
            scales = Array.from(checked).map(cb => cb.dataset.scale).filter(Boolean);
            if (scales.length === 0) scales = ['random'];
        }

        let tempo = null;
        if (tempoRandom && !tempoRandom.checked) {
            const slider = document.getElementById('sr-tempo-slider');
            tempo = slider ? parseInt(slider.value) : 80;
        }

        let noteTypes = ['random'];
        if (notesRandom && !notesRandom.checked) {
            const checked = document.querySelectorAll('#sr-note-type-options input[data-note-type]:checked');
            noteTypes = Array.from(checked).map(cb => cb.dataset.noteType).filter(Boolean);
            if (noteTypes.length === 0) noteTypes = ['random'];
        }

        return {
            instrument: instrument ? instrument.dataset.instrument : 'piano',
            guitar_tone: guitarTone ? guitarTone.dataset.tone : 'acoustic',
            scales,
            tempo,
            note_types: noteTypes,
            measures: measures ? parseInt(measures.dataset.measures) : 4
        };
    }

    /**
     * Save preferences to storage
     */
    savePreferences() {
        const prefs = this.getPreferences();
        const data = storageManager.loadAll();
        if (!data.mode_progress.sight_reading) {
            data.mode_progress.sight_reading = { sessions: 0, exercises_completed: 0, correct: 0, total: 0, total_time: 0, preferences: prefs };
        } else {
            data.mode_progress.sight_reading.preferences = prefs;
        }
        storageManager.saveAll(data);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Instrument toggle
        document.querySelectorAll('.instrument-toggle [data-instrument]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.instrument-toggle [data-instrument]').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                const isGuitar = e.currentTarget.dataset.instrument === 'guitar';
                const toneRow = document.getElementById('sr-guitar-tone-row');
                const tabLabel = document.getElementById('sr-tab-toggle-label');
                if (toneRow) toneRow.classList.toggle('hidden', !isGuitar);
                if (tabLabel) tabLabel.classList.toggle('hidden', !isGuitar);
                this.savePreferences();
            });
        });

        // Guitar tone toggle
        document.querySelectorAll('#sr-guitar-tone-row [data-tone]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#sr-guitar-tone-row [data-tone]').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.savePreferences();
            });
        });

        // Measures toggle
        document.querySelectorAll('[data-measures]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-measures]').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.savePreferences();
            });
        });

        // Settings toggle
        const settingsToggle = document.getElementById('sr-toggle-settings');
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => {
                const body = document.getElementById('sr-settings-body');
                if (body) body.classList.toggle('hidden');
            });
        }

        // Scale random toggle
        const scaleRandom = document.getElementById('sr-scale-random');
        if (scaleRandom) {
            scaleRandom.addEventListener('change', (e) => {
                const opts = document.getElementById('sr-scale-options');
                if (opts) opts.classList.toggle('hidden', e.target.checked);
                this.savePreferences();
            });
        }

        // Tempo random toggle
        const tempoRandom = document.getElementById('sr-tempo-random');
        if (tempoRandom) {
            tempoRandom.addEventListener('change', (e) => {
                const manual = document.getElementById('sr-tempo-manual');
                if (manual) manual.classList.toggle('hidden', e.target.checked);
                this.savePreferences();
            });
        }

        // Tempo slider
        const tempoSlider = document.getElementById('sr-tempo-slider');
        if (tempoSlider) {
            tempoSlider.addEventListener('input', (e) => {
                const display = document.getElementById('sr-tempo-value');
                if (display) display.textContent = `${e.target.value} BPM`;
            });
            tempoSlider.addEventListener('change', () => this.savePreferences());
        }

        // Note types random toggle
        const notesRandom = document.getElementById('sr-notes-random');
        if (notesRandom) {
            notesRandom.addEventListener('change', (e) => {
                const opts = document.getElementById('sr-note-type-options');
                if (opts) opts.classList.toggle('hidden', e.target.checked);
                this.savePreferences();
            });
        }

        // Note type checkboxes
        document.querySelectorAll('#sr-note-type-options input[data-note-type]').forEach(cb => {
            cb.addEventListener('change', () => this.savePreferences());
        });

        // TAB toggle
        const tabToggle = document.getElementById('sr-tab-toggle');
        if (tabToggle) {
            tabToggle.addEventListener('change', (e) => {
                this.showTab = e.target.checked;
                if (this.currentExercise) this.renderNotation(this.currentExercise);
            });
        }

        // Start button
        const startBtn = document.getElementById('sr-start');
        if (startBtn) startBtn.addEventListener('click', () => this.startSession());

        // Play/Stop buttons
        const playBtn = document.getElementById('sr-play');
        if (playBtn) playBtn.addEventListener('click', () => this.playExercise());

        const stopBtn = document.getElementById('sr-stop-playback');
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopPlayback());

        // Self-assessment buttons
        const gotItBtn = document.getElementById('sr-got-it');
        if (gotItBtn) gotItBtn.addEventListener('click', () => this.handleAssessment(true));

        const struggledBtn = document.getElementById('sr-struggled');
        if (struggledBtn) struggledBtn.addEventListener('click', () => this.handleAssessment(false));

        // Next / End session
        const nextBtn = document.getElementById('sr-next');
        if (nextBtn) nextBtn.addEventListener('click', () => this.loadNextExercise());

        const endBtn = document.getElementById('sr-end-session');
        if (endBtn) endBtn.addEventListener('click', () => this.endSession());

        // Restart
        const restartBtn = document.getElementById('sr-restart');
        if (restartBtn) restartBtn.addEventListener('click', () => this.init());
    }

    /**
     * Load available scales from the API
     */
    async loadAvailableScales() {
        const scaleOptions = document.getElementById('sr-scale-options');
        if (!scaleOptions) return;

        const elo = storageManager.load('user_elo') || 1000;

        try {
            const response = await fetch(`/api/sight-reading/scales?elo=${elo}`);
            const data = await response.json();

            const prefs = this.getPreferences();
            scaleOptions.innerHTML = data.scales.map(scale =>
                `<label class="sr-checkbox-label">
                    <input type="checkbox" data-scale="${scale}" ${prefs.scales.includes(scale) ? 'checked' : ''}>
                    ${scale}
                </label>`
            ).join('');

            // Add change listeners
            scaleOptions.querySelectorAll('input[data-scale]').forEach(cb => {
                cb.addEventListener('change', () => this.savePreferences());
            });
        } catch (e) {
            scaleOptions.innerHTML = '<span>Could not load scales</span>';
        }
    }

    /**
     * Start a new session
     */
    async startSession() {
        window.gameActive = true;
        this.currentElo = storageManager.load('user_elo') || 1000;
        this.session = { correct: 0, total: 0, startTime: Date.now() };

        document.getElementById('sr-controls').classList.add('hidden');
        document.getElementById('sr-exercise-area').classList.remove('hidden');

        await this.loadNextExercise();
    }

    /**
     * Load next exercise from API
     */
    async loadNextExercise() {
        const prefs = this.getPreferences();

        // Re-enable assessment buttons
        const assessment = document.getElementById('sr-assessment');
        if (assessment) {
            assessment.querySelectorAll('button').forEach(b => b.disabled = false);
            assessment.classList.remove('assessed');
        }

        try {
            const response = await fetch('/api/sight-reading/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    elo: this.currentElo,
                    instrument: prefs.instrument,
                    scales: prefs.scales,
                    tempo: prefs.tempo,
                    note_types: prefs.note_types,
                    measures: prefs.measures
                })
            });

            this.currentExercise = await response.json();

            // Update info display
            const info = document.getElementById('sr-exercise-info');
            if (info) {
                info.innerHTML = `
                    <span class="sr-info-badge">${this.currentExercise.scale_name}</span>
                    <span class="sr-info-badge">${this.currentExercise.time_signature[0]}/${this.currentExercise.time_signature[1]}</span>
                    <span class="sr-info-badge">♩ = ${this.currentExercise.tempo}</span>
                `;
            }

            const tempoDisplay = document.getElementById('sr-tempo-display');
            if (tempoDisplay) tempoDisplay.textContent = `♩ = ${this.currentExercise.tempo}`;

            this.renderNotation(this.currentExercise);

        } catch (error) {
            console.error('Error loading sight reading exercise:', error);
            // Fallback: generate a simple local exercise
            this.currentExercise = this.generateLocalFallback();
            this.renderNotation(this.currentExercise);
        }
    }

    /**
     * Generate a simple local fallback exercise
     */
    generateLocalFallback() {
        return {
            id: 'sr_local_' + Math.random().toString(36).substr(2, 9),
            mode: 'sight_reading',
            difficulty: 1,
            instrument: 'piano',
            time_signature: [4, 4],
            key_signature: 'C',
            scale_name: 'C Major',
            tempo: 80,
            staves: 1,
            measures: [
                {
                    clef: 'treble',
                    notes: [
                        { keys: ['c/4'], duration: 'q', midi: [60], is_rest: false, dots: 0, accidentals: [] },
                        { keys: ['d/4'], duration: 'q', midi: [62], is_rest: false, dots: 0, accidentals: [] },
                        { keys: ['e/4'], duration: 'q', midi: [64], is_rest: false, dots: 0, accidentals: [] },
                        { keys: ['f/4'], duration: 'q', midi: [65], is_rest: false, dots: 0, accidentals: [] }
                    ]
                }
            ],
            bass_measures: []
        };
    }

    /**
     * Render notation using VexFlow
     */
    renderNotation(data) {
        const container = document.getElementById('sr-notation-container');
        if (!container) return;
        container.innerHTML = '';

        // Check if VexFlow is loaded
        if (typeof Vex === 'undefined') {
            container.innerHTML = '<p>Music notation library is loading...</p>';
            return;
        }

        const VF = Vex.Flow;
        this.noteElements = [];

        const isGuitar = data.instrument === 'guitar';
        const showTab = isGuitar && this.showTab;
        const hasBass = data.staves === 2 && data.bass_measures && data.bass_measures.length > 0;
        const measureCount = data.measures.length;

        // Calculate dimensions
        const staveWidth = Math.max(200, Math.min(300, (window.innerWidth - 80) / measureCount));
        const leftPadding = 10;
        const totalWidth = staveWidth * measureCount + leftPadding + 20;

        let trebleY = 10;
        let bassY = trebleY + 120;
        let tabY = hasBass ? bassY + 120 : trebleY + 120;
        let totalHeight = trebleY + 140;

        if (hasBass) totalHeight = bassY + 140;
        if (showTab) totalHeight = tabY + 140;

        // Create renderer
        const renderer = new VF.Renderer(container, VF.Renderer.Backends.SVG);
        renderer.resize(totalWidth, totalHeight);
        const context = renderer.getContext();

        // Render each measure
        for (let i = 0; i < measureCount; i++) {
            const x = leftPadding + i * staveWidth;
            const measure = data.measures[i];
            const isFirst = i === 0;

            // --- Treble Stave ---
            const trebleStave = new VF.Stave(x, trebleY, staveWidth);
            if (isFirst) {
                trebleStave.addClef('treble');
                trebleStave.addKeySignature(data.key_signature);
                trebleStave.addTimeSignature(`${data.time_signature[0]}/${data.time_signature[1]}`);
            }
            if (i === measureCount - 1) {
                trebleStave.setEndBarType(VF.Barline.type.END);
            }
            trebleStave.setContext(context).draw();

            // Create VexFlow notes
            const trebleNotes = this.createVexNotes(measure.notes, VF);
            if (trebleNotes.length > 0) {
                try {
                    const voice = new VF.Voice({
                        num_beats: data.time_signature[0],
                        beat_value: data.time_signature[1]
                    }).setStrict(false);
                    voice.addTickables(trebleNotes);
                    new VF.Formatter().joinVoices([voice]).format([voice], staveWidth - (isFirst ? 90 : 30));
                    voice.draw(context, trebleStave);

                    // Store note elements for highlighting
                    trebleNotes.forEach((n, idx) => {
                        this.noteElements.push({
                            element: n,
                            measureIndex: i,
                            noteIndex: idx,
                            noteData: measure.notes[idx]
                        });
                    });
                } catch (e) {
                    console.warn('VexFlow render error in treble measure', i, e);
                }
            }

            // --- Bass Stave (piano grand staff) ---
            if (hasBass && data.bass_measures[i]) {
                const bassStave = new VF.Stave(x, bassY, staveWidth);
                if (isFirst) {
                    bassStave.addClef('bass');
                    bassStave.addKeySignature(data.key_signature);
                    bassStave.addTimeSignature(`${data.time_signature[0]}/${data.time_signature[1]}`);
                }
                if (i === measureCount - 1) {
                    bassStave.setEndBarType(VF.Barline.type.END);
                }
                bassStave.setContext(context).draw();

                const bassMeasure = data.bass_measures[i];
                const bassNotes = this.createVexNotes(bassMeasure.notes, VF);
                if (bassNotes.length > 0) {
                    try {
                        const bassVoice = new VF.Voice({
                            num_beats: data.time_signature[0],
                            beat_value: data.time_signature[1]
                        }).setStrict(false);
                        bassVoice.addTickables(bassNotes);
                        new VF.Formatter().joinVoices([bassVoice]).format([bassVoice], staveWidth - (isFirst ? 90 : 30));
                        bassVoice.draw(context, bassStave);
                    } catch (e) {
                        console.warn('VexFlow render error in bass measure', i, e);
                    }
                }

                // Draw brace connecting treble and bass on first measure
                if (isFirst) {
                    const brace = new VF.StaveConnector(trebleStave, bassStave);
                    brace.setType(VF.StaveConnector.type.BRACE);
                    brace.setContext(context).draw();
                }
            }

            // --- TAB Stave (guitar) ---
            if (showTab) {
                const tabStave = new VF.TabStave(x, tabY, staveWidth);
                if (isFirst) {
                    tabStave.addClef('tab');
                }
                if (i === measureCount - 1) {
                    tabStave.setEndBarType(VF.Barline.type.END);
                }
                tabStave.setContext(context).draw();

                const tabNotes = this.createTabNotes(measure.notes, VF);
                if (tabNotes.length > 0) {
                    try {
                        const tabVoice = new VF.Voice({
                            num_beats: data.time_signature[0],
                            beat_value: data.time_signature[1]
                        }).setStrict(false);
                        tabVoice.addTickables(tabNotes);
                        new VF.Formatter().joinVoices([tabVoice]).format([tabVoice], staveWidth - (isFirst ? 60 : 30));
                        tabVoice.draw(context, tabStave);
                    } catch (e) {
                        console.warn('VexFlow render error in tab measure', i, e);
                    }
                }

                // Connect standard notation stave to tab
                if (isFirst) {
                    const connector = new VF.StaveConnector(trebleStave, tabStave);
                    connector.setType(VF.StaveConnector.type.SINGLE_LEFT);
                    connector.setContext(context).draw();
                }
            }
        }
    }

    /**
     * Create VexFlow StaveNote objects from note data
     */
    createVexNotes(notes, VF) {
        if (!notes || notes.length === 0) return [];

        return notes.map(note => {
            const duration = note.is_rest ? note.duration + 'r' : note.duration;
            const staveNote = new VF.StaveNote({
                keys: note.keys,
                duration: duration,
            });

            // Add accidentals
            if (note.accidentals && !note.is_rest) {
                note.accidentals.forEach(acc => {
                    staveNote.addModifier(new VF.Accidental(acc.type), acc.index);
                });
            }

            // Add dots
            if (note.dots) {
                for (let d = 0; d < note.dots; d++) {
                    VF.Dot.buildAndAttach([staveNote]);
                }
            }

            return staveNote;
        });
    }

    /**
     * Create VexFlow TabNote objects from note data
     */
    createTabNotes(notes, VF) {
        if (!notes || notes.length === 0) return [];

        return notes.map(note => {
            if (note.is_rest) {
                return new VF.TabNote({
                    positions: [{ str: 1, fret: '' }],
                    duration: note.duration + 'r'
                });
            }

            const tab = note.tab;
            const positions = tab
                ? [{ str: tab.string, fret: tab.fret }]
                : [{ str: 1, fret: 0 }];

            return new VF.TabNote({
                positions: positions,
                duration: note.duration
            });
        });
    }

    /**
     * Play the current exercise using Tone.js
     */
    async playExercise() {
        if (this.isPlaying || !this.currentExercise) return;

        // Check if Tone.js is loaded
        if (typeof Tone === 'undefined') {
            console.error('Tone.js not loaded');
            return;
        }

        this.isPlaying = true;
        const playBtn = document.getElementById('sr-play');
        const stopBtn = document.getElementById('sr-stop-playback');
        if (playBtn) playBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;

        await Tone.start();

        // Create synth based on instrument and tone
        this.disposeSynth();
        const prefs = this.getPreferences();
        this.synth = this.createSynth(prefs.instrument, prefs.guitar_tone);

        const data = this.currentExercise;
        const bpm = data.tempo;
        const quarterDuration = 60 / bpm;

        // Duration code to seconds
        const durationToSec = (code, dots) => {
            const map = { 'w': 4, 'h': 2, 'q': 1, '8': 0.5, '16': 0.25 };
            let beats = map[code] || 1;
            if (dots) beats *= 1.5;
            return beats * quarterDuration;
        };

        // Schedule all notes
        let time = Tone.now() + 0.1;
        this.scheduledEvents = [];

        const allMeasures = data.measures;
        let noteIdx = 0;

        for (let m = 0; m < allMeasures.length; m++) {
            const measure = allMeasures[m];
            for (let n = 0; n < measure.notes.length; n++) {
                const note = measure.notes[n];
                const durSec = durationToSec(note.duration, note.dots);

                if (!note.is_rest && note.midi && note.midi.length > 0) {
                    const freqs = note.midi.map(midi => Tone.Frequency(midi, 'midi').toFrequency());
                    const currentNoteIdx = noteIdx;

                    const eventTime = time;
                    this.synth.triggerAttackRelease(freqs, durSec * 0.85, eventTime);

                    // Schedule highlight
                    const highlightId = Tone.Transport.schedule(() => {
                        this.highlightNote(currentNoteIdx, true);
                    }, eventTime);
                    this.scheduledEvents.push(highlightId);

                    const unhighlightId = Tone.Transport.schedule(() => {
                        this.highlightNote(currentNoteIdx, false);
                    }, eventTime + durSec * 0.8);
                    this.scheduledEvents.push(unhighlightId);
                }

                time += durSec;
                noteIdx++;
            }
        }

        // Schedule end
        const endTime = time + 0.2;
        setTimeout(() => {
            this.stopPlayback();
        }, (endTime - Tone.now()) * 1000);
    }

    /**
     * Create a Tone.js synth based on instrument type
     */
    createSynth(instrument, guitarTone) {
        if (instrument === 'piano') {
            return new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: 'triangle' },
                envelope: { attack: 0.01, decay: 0.5, sustain: 0.3, release: 1.0 }
            }).toDestination();
        } else if (guitarTone === 'acoustic') {
            return new Tone.PolySynth(Tone.AMSynth, {
                harmonicity: 2,
                oscillator: { type: 'triangle' },
                envelope: { attack: 0.01, decay: 0.8, sustain: 0.2, release: 0.8 },
                modulation: { type: 'square' },
                modulationEnvelope: { attack: 0.5, decay: 0.1, sustain: 0.2, release: 0.1 }
            }).toDestination();
        } else {
            // Electric clean
            return new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: 'triangle' },
                envelope: { attack: 0.02, decay: 0.3, sustain: 0.1, release: 0.5 }
            }).toDestination();
        }
    }

    /**
     * Dispose the current synth
     */
    disposeSynth() {
        if (this.synth) {
            try { this.synth.dispose(); } catch (e) { /* ignore */ }
            this.synth = null;
        }
    }

    /**
     * Highlight or unhighlight a note during playback
     */
    highlightNote(noteIdx, active) {
        if (noteIdx >= 0 && noteIdx < this.noteElements.length) {
            const noteInfo = this.noteElements[noteIdx];
            if (noteInfo && noteInfo.element && noteInfo.element.getSVGElement) {
                try {
                    const svgEl = noteInfo.element.getSVGElement();
                    if (svgEl) {
                        if (active) {
                            svgEl.classList.add('sr-note-active');
                        } else {
                            svgEl.classList.remove('sr-note-active');
                        }
                    }
                } catch (e) { /* SVG element not available */ }
            }
        }
    }

    /**
     * Stop audio playback
     */
    stopPlayback() {
        this.isPlaying = false;

        // Clear scheduled events
        this.scheduledEvents.forEach(id => {
            try { Tone.Transport.clear(id); } catch (e) { /* ignore */ }
        });
        this.scheduledEvents = [];

        this.disposeSynth();

        // Clear all highlights
        this.noteElements.forEach((_, idx) => this.highlightNote(idx, false));

        const playBtn = document.getElementById('sr-play');
        const stopBtn = document.getElementById('sr-stop-playback');
        if (playBtn) playBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
    }

    /**
     * Handle self-assessment response
     */
    handleAssessment(gotIt) {
        this.session.total++;
        if (gotIt) this.session.correct++;

        // ELO adjustment
        const difficulty = this.currentExercise ? this.currentExercise.difficulty : 5;
        const eloChange = gotIt ? Math.round(5 + difficulty) : -Math.round(3 + difficulty * 0.5);
        this.currentElo = storageManager.updateElo(eloChange);

        // Update session stats display
        this.updateSessionStats();

        // Disable assessment buttons after answering
        const assessment = document.getElementById('sr-assessment');
        if (assessment) {
            assessment.querySelectorAll('button').forEach(b => b.disabled = true);
            assessment.classList.add('assessed');
        }

        // Visual feedback
        const clickedBtn = gotIt ? document.getElementById('sr-got-it') : document.getElementById('sr-struggled');
        if (clickedBtn) {
            clickedBtn.classList.add(gotIt ? 'correct' : 'incorrect');
            setTimeout(() => clickedBtn.classList.remove('correct', 'incorrect'), 1000);
        }
    }

    /**
     * Update session stats display
     */
    updateSessionStats() {
        const correctEl = document.getElementById('sr-session-correct');
        const totalEl = document.getElementById('sr-session-total');
        const accuracyEl = document.getElementById('sr-session-accuracy');

        if (correctEl) correctEl.textContent = this.session.correct;
        if (totalEl) totalEl.textContent = this.session.total;
        if (accuracyEl) {
            const pct = this.session.total > 0 ? Math.round((this.session.correct / this.session.total) * 100) : 0;
            accuracyEl.textContent = `${pct}%`;
        }
    }

    /**
     * End the current session
     */
    endSession() {
        window.gameActive = false;
        this.stopPlayback();

        const duration = this.session.startTime ? Math.round((Date.now() - this.session.startTime) / 1000) : 0;

        // Save progress
        const progress = storageManager.load('mode_progress');
        const sr = progress.sight_reading || { sessions: 0, exercises_completed: 0, correct: 0, total: 0, total_time: 0 };
        sr.sessions++;
        sr.exercises_completed += this.session.total;
        sr.correct += this.session.correct;
        sr.total += this.session.total;
        sr.total_time += duration;
        progress.sight_reading = { ...sr, preferences: this.getPreferences() };
        storageManager.save('mode_progress', progress);
        storageManager.logPracticeSession('sight_reading', duration, {
            correct: this.session.correct,
            total: this.session.total
        });

        // Show results
        document.getElementById('sr-exercise-area').classList.add('hidden');
        document.getElementById('sr-results').classList.remove('hidden');

        const resultsCorrect = document.getElementById('sr-results-correct');
        const resultsAccuracy = document.getElementById('sr-results-accuracy');
        const resultsElo = document.getElementById('sr-results-elo');

        if (resultsCorrect) resultsCorrect.textContent = this.session.correct;
        if (resultsAccuracy) {
            const pct = this.session.total > 0 ? Math.round((this.session.correct / this.session.total) * 100) : 0;
            resultsAccuracy.textContent = `${pct}%`;
        }
        if (resultsElo) {
            const startElo = 1000;  // Approximate
            const diff = Math.round(this.currentElo - startElo);
            resultsElo.textContent = diff >= 0 ? `+${diff}` : `${diff}`;
        }
    }
}

// Create singleton instance
window.sight_reading = new SightReading();
