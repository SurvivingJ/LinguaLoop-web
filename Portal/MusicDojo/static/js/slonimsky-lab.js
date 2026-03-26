/**
 * SlonimskyLab - Pattern browser with VexFlow notation and Tone.js playback
 * Integrates fretboard and piano visualizers for synchronized display.
 */
class SlonimskyLab {
    constructor() {
        this.library = null;
        this.currentPattern = null;
        this.currentView = 'guitar'; // 'guitar' or 'piano'
        this.synth = null;
        this.isPlaying = false;
        this.scheduledEvents = [];
        this.initialized = false;
    }

    async init() {
        if (!this.initialized) {
            await this.loadLibrary();
            this.bindEvents();
            this.initialized = true;
        }
        this.selectPatternFromControls();
    }

    async loadLibrary() {
        try {
            const response = await fetch('/api/guitar100k/library');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            this.library = await response.json();
        } catch (error) {
            console.error('Failed to load Slonimsky library:', error);
            this.library = { patterns: [] };
            const info = document.getElementById('slonimsky-pattern-info');
            if (info) info.innerHTML = '<p style="color:var(--color-danger)">Library not found. Run generate_slonimsky.py first.</p>';
        }
    }

    bindEvents() {
        // Division/Interpolation/Key dropdowns
        ['slonimsky-division', 'slonimsky-interpolation', 'slonimsky-key'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => this.selectPatternFromControls());
            }
        });

        // View tabs (guitar/piano)
        document.querySelectorAll('.slonimsky-view-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.currentView = tab.dataset.view;
                document.querySelectorAll('.slonimsky-view-tab').forEach(t =>
                    t.classList.toggle('active', t.dataset.view === this.currentView)
                );
                this.renderCurrentPattern();
            });
        });

        // Play/Stop
        const playBtn = document.getElementById('slonimsky-play-btn');
        if (playBtn) playBtn.addEventListener('click', () => this.play());

        const stopBtn = document.getElementById('slonimsky-stop-btn');
        if (stopBtn) stopBtn.addEventListener('click', () => this.stop());

        // Tempo slider
        const tempoSlider = document.getElementById('slonimsky-tempo-slider');
        if (tempoSlider) {
            tempoSlider.addEventListener('input', (e) => {
                document.getElementById('slonimsky-tempo-display').textContent = e.target.value;
            });
        }

        // Add to exercises
        const addBtn = document.getElementById('slonimsky-add-btn');
        if (addBtn) addBtn.addEventListener('click', () => this.addToExercises());
    }

    selectPatternFromControls() {
        const division = document.getElementById('slonimsky-division')?.value;
        const interpolation = document.getElementById('slonimsky-interpolation')?.value;
        const keyOffset = parseInt(document.getElementById('slonimsky-key')?.value || '0');

        if (!this.library || !this.library.patterns) return;

        // Find matching pattern
        const interpKey = interpolation;
        const pattern = this.library.patterns.find(p =>
            p.division === division && p.interpolation_key === interpKey
        );

        if (!pattern) {
            document.getElementById('slonimsky-pattern-info').innerHTML =
                '<p style="color:var(--color-text-secondary)">No pattern found for this combination.</p>';
            return;
        }

        // Apply transposition
        this.currentPattern = this.transposePattern(pattern, keyOffset);
        this.renderCurrentPattern();
    }

    transposePattern(pattern, semitones) {
        if (semitones === 0) return pattern;

        const transposed = JSON.parse(JSON.stringify(pattern));
        transposed.midi_sequence = pattern.midi_sequence.map(m => m + semitones);
        transposed.note_names = transposed.midi_sequence.map(m => this.midiToNoteName(m));
        transposed.vex_keys = transposed.midi_sequence.map(m => this.midiToVexKey(m));

        // Re-calculate guitar fingering for transposed notes
        // (Simple offset - frets shift by semitones)
        transposed.guitar_fingering = pattern.guitar_fingering.map(f => {
            const newMidi = f.midi + semitones;
            return {
                ...f,
                midi: newMidi,
                fret: f.fret + semitones,
                note_name: this.midiToNoteName(newMidi),
                vex_key: this.midiToVexKey(newMidi)
            };
        });

        return transposed;
    }

    renderCurrentPattern() {
        if (!this.currentPattern) return;

        this.renderPatternInfo();
        this.renderNotation();
        this.renderVisualizer();
    }

    renderPatternInfo() {
        const info = document.getElementById('slonimsky-pattern-info');
        if (!info) return;

        const p = this.currentPattern;
        const keyName = this.midiToNoteName(p.midi_sequence[0]);
        info.innerHTML = `
            <strong>${p.name}</strong> in ${keyName.replace(/\d/, '')}
            <br><span style="color:var(--color-text-secondary)">${p.midi_sequence.length} notes | ${p.direction} | ${p.note_names.join(' → ')}</span>
        `;
    }

    renderNotation() {
        const container = document.getElementById('slonimsky-notation');
        if (!container) return;
        container.innerHTML = '';

        // Check if VexFlow is available
        if (typeof Vex === 'undefined') {
            container.innerHTML = '<p style="color:var(--color-text-secondary)">VexFlow not loaded</p>';
            return;
        }

        try {
            const { Renderer, Stave, StaveNote, Voice, Formatter, TabStave, TabNote } = Vex.Flow;

            const width = Math.max(600, this.currentPattern.midi_sequence.length * 40 + 100);
            const div = document.createElement('div');
            container.appendChild(div);

            const renderer = new Renderer(div, Renderer.Backends.SVG);

            if (this.currentView === 'guitar') {
                this.renderGuitarTab(renderer, width);
            } else {
                this.renderPianoNotation(renderer, width);
            }
        } catch (error) {
            console.error('VexFlow render error:', error);
            container.innerHTML = `<p style="color:var(--color-danger)">Notation render error: ${error.message}</p>`;
        }
    }

    renderGuitarTab(renderer, width) {
        const { Stave, StaveNote, TabStave, TabNote, Voice, Formatter } = Vex.Flow;

        renderer.resize(width, 260);
        const context = renderer.getContext();

        // Standard notation stave
        const stave = new Stave(10, 10, width - 20);
        stave.addClef('treble');
        stave.setContext(context).draw();

        // Tab stave below
        const tabStave = new TabStave(10, 120, width - 20);
        tabStave.setContext(context).draw();

        const pattern = this.currentPattern;
        const notes = [];
        const tabNotes = [];

        pattern.guitar_fingering.forEach(f => {
            // Standard notation
            try {
                const staveNote = new StaveNote({
                    keys: [f.vex_key],
                    duration: 'q'
                });
                notes.push(staveNote);
            } catch (e) {
                // Skip notes VexFlow can't render
            }

            // Tab notation
            try {
                const tabNote = new TabNote({
                    positions: [{ str: 6 - f.string, fret: f.fret }],
                    duration: 'q'
                });
                tabNotes.push(tabNote);
            } catch (e) {
                // Skip
            }
        });

        if (notes.length > 0) {
            const voice = new Voice({ num_beats: notes.length, beat_value: 4 });
            voice.setStrict(false);
            voice.addTickables(notes);
            new Formatter().joinVoices([voice]).format([voice], width - 60);
            voice.draw(context, stave);
        }

        if (tabNotes.length > 0) {
            const tabVoice = new Voice({ num_beats: tabNotes.length, beat_value: 4 });
            tabVoice.setStrict(false);
            tabVoice.addTickables(tabNotes);
            new Formatter().joinVoices([tabVoice]).format([tabVoice], width - 60);
            tabVoice.draw(context, tabStave);
        }
    }

    renderPianoNotation(renderer, width) {
        const { Stave, StaveNote, Voice, Formatter } = Vex.Flow;

        renderer.resize(width, 160);
        const context = renderer.getContext();

        const stave = new Stave(10, 20, width - 20);
        stave.addClef('treble');
        stave.setContext(context).draw();

        const pattern = this.currentPattern;
        const notes = [];

        pattern.midi_sequence.forEach(midi => {
            try {
                const vexKey = this.midiToVexKey(midi);
                const staveNote = new StaveNote({
                    keys: [vexKey],
                    duration: 'q'
                });

                // Add accidentals
                const noteName = this.midiToNoteName(midi);
                if (noteName.includes('#')) {
                    staveNote.addModifier(new Vex.Flow.Accidental('#'));
                }

                notes.push(staveNote);
            } catch (e) {
                // Skip notes VexFlow can't render
            }
        });

        if (notes.length > 0) {
            const voice = new Voice({ num_beats: notes.length, beat_value: 4 });
            voice.setStrict(false);
            voice.addTickables(notes);
            new Formatter().joinVoices([voice]).format([voice], width - 60);
            voice.draw(context, stave);
        }
    }

    renderVisualizer() {
        const container = document.getElementById('slonimsky-visualizer');
        if (!container) return;

        if (this.currentView === 'guitar') {
            fretboardVisualizer.render(container);
            if (this.currentPattern.guitar_fingering) {
                fretboardVisualizer.showPattern(this.currentPattern.guitar_fingering);
            }
        } else {
            pianoVisualizer.render(container);
            if (this.currentPattern.midi_sequence) {
                pianoVisualizer.showPattern(this.currentPattern.midi_sequence);
            }
        }
    }

    // ===== TONE.JS PLAYBACK =====

    async play() {
        if (this.isPlaying) this.stop();
        if (!this.currentPattern) return;

        // Initialize Tone.js
        if (typeof Tone === 'undefined') {
            console.error('Tone.js not loaded');
            return;
        }

        await Tone.start();

        if (!this.synth) {
            this.synth = new Tone.Synth({
                oscillator: { type: 'triangle' },
                envelope: { attack: 0.01, decay: 0.3, sustain: 0.2, release: 0.5 }
            }).toDestination();
        }

        const bpm = parseInt(document.getElementById('slonimsky-tempo-slider')?.value || '80');
        const noteDuration = 60 / bpm; // seconds per beat
        const pattern = this.currentPattern;

        this.isPlaying = true;
        this.scheduledEvents = [];

        const startTime = Tone.now() + 0.1;

        pattern.midi_sequence.forEach((midi, i) => {
            const time = startTime + (i * noteDuration);
            const freq = Tone.Frequency(midi, 'midi').toFrequency();

            // Schedule note
            const eventId = Tone.Transport.schedule(() => {
                this.synth.triggerAttackRelease(freq, noteDuration * 0.8);
                this.onNotePlay(i);
            }, time);

            this.scheduledEvents.push(eventId);
        });

        // Schedule stop after all notes
        const endTime = startTime + (pattern.midi_sequence.length * noteDuration);
        Tone.Transport.schedule(() => {
            this.stop();
        }, endTime);

        Tone.Transport.start();

        // Update play button
        const playBtn = document.getElementById('slonimsky-play-btn');
        if (playBtn) playBtn.textContent = '▶ Playing...';
    }

    stop() {
        this.isPlaying = false;

        if (typeof Tone !== 'undefined') {
            Tone.Transport.stop();
            Tone.Transport.cancel();
        }

        this.scheduledEvents = [];

        // Clear visualizer highlights
        if (this.currentView === 'guitar') {
            fretboardVisualizer.clearHighlight();
            if (this.currentPattern) {
                fretboardVisualizer.showPattern(this.currentPattern.guitar_fingering);
            }
        } else {
            pianoVisualizer.clearHighlight();
            if (this.currentPattern) {
                pianoVisualizer.showPattern(this.currentPattern.midi_sequence);
            }
        }

        const playBtn = document.getElementById('slonimsky-play-btn');
        if (playBtn) playBtn.textContent = '▶ Play';
    }

    onNotePlay(index) {
        const pattern = this.currentPattern;
        if (!pattern) return;

        if (this.currentView === 'guitar') {
            fretboardVisualizer.clearHighlight();
            const f = pattern.guitar_fingering[index];
            if (f) {
                fretboardVisualizer.highlightNote(f.string, f.fret, f.note_name);
            }
        } else {
            pianoVisualizer.clearHighlight();
            const midi = pattern.midi_sequence[index];
            if (midi !== undefined) {
                pianoVisualizer.highlightKey(midi);
            }
        }
    }

    // ===== ADD TO EXERCISES =====

    async addToExercises() {
        if (!this.currentPattern) return;

        const pattern = this.currentPattern;
        const instrument = this.currentView === 'piano' ? 'piano' : 'guitar';
        const keyName = this.midiToNoteName(pattern.midi_sequence[0]).replace(/\d/, '');

        try {
            const response = await fetch('/api/guitar100k/exercises', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instrument: instrument,
                    id: `slonimsky_${pattern.id}_${keyName.toLowerCase().replace('#', 's')}`,
                    name: `Slonimsky: ${pattern.name} (${keyName})`,
                    category: 'slonimsky',
                    target_reps: 5000,
                    source: 'slonimsky_lab'
                })
            });

            if (response.status === 409) {
                alert('This pattern is already in your exercises!');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to add exercise');
            }

            alert(`Added "${pattern.name}" to your ${instrument} exercises!`);
        } catch (error) {
            console.error('Error adding exercise:', error);
            alert('Failed to add exercise: ' + error.message);
        }
    }

    // ===== HELPERS =====

    midiToNoteName(midi) {
        const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const octave = Math.floor(midi / 12) - 1;
        return `${names[midi % 12]}${octave}`;
    }

    midiToVexKey(midi) {
        const names = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b'];
        const octave = Math.floor(midi / 12) - 1;
        return `${names[midi % 12]}/${octave}`;
    }
}

// Create singleton instance
window.slonimsky_lab = new SlonimskyLab();
