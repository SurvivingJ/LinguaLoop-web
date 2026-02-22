/**
 * AudioManager - Handles Web Audio API for all sound generation
 */
class AudioManager {
    constructor() {
        this.context = null;
        this.masterGain = null;
        this.schedulerTimerId = null;
        this.nextNoteTime = 0;
        this.scheduleAheadTime = 0.1; // Schedule 100ms ahead
        this.lookahead = 25; // How often to check for scheduling (ms)
        this.isEnabled = true;
    }

    /**
     * Initialize Audio Context (must be called after user interaction)
     */
    initialize() {
        if (!this.context) {
            this.context = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (this.context.state === 'suspended') {
            this.context.resume();
        }

        if (!this.masterGain) {
            this.masterGain = this.context.createGain();
            const settings = storageManager.load('settings');
            this.masterGain.gain.value = settings.master_volume || 0.5;
            this.masterGain.connect(this.context.destination);
        }
    }

    /**
     * Set master volume (0.0 to 1.0)
     */
    setMasterVolume(volume) {
        if (this.masterGain) {
            this.masterGain.gain.value = Math.max(0, Math.min(1, volume));
        }

        // Save to storage
        const settings = storageManager.load('settings');
        settings.master_volume = volume;
        storageManager.save('settings', settings);
    }

    /**
     * Enable/disable sound
     */
    setEnabled(enabled) {
        this.isEnabled = enabled;
        const settings = storageManager.load('settings');
        settings.sound_enabled = enabled;
        storageManager.save('settings', settings);
    }

    /**
     * Play a click sound (metronome tick)
     */
    playClick(frequency = 800, duration = 0.05, isAccent = false) {
        if (!this.isEnabled || !this.context) return;

        this.scheduleNote(this.context.currentTime, frequency, duration, isAccent);
    }

    /**
     * Schedule a note to play at a specific time
     */
    scheduleNote(time, frequency, duration = 0.05, isAccent = false) {
        if (!this.isEnabled || !this.context) return;

        const osc = this.context.createOscillator();
        const gain = this.context.createGain();

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.frequency.value = frequency;

        const settings = storageManager.load('settings');
        osc.type = settings.metronome_sound || 'sine';

        const vol = isAccent ? 0.4 : 0.25;
        gain.gain.setValueAtTime(vol, time);
        gain.gain.exponentialRampToValueAtTime(0.001, time + duration);

        osc.start(time);
        osc.stop(time + duration);
    }

    /**
     * Play a chirp sound (for warnings/notifications)
     */
    playChirp() {
        if (!this.isEnabled || !this.context) return;

        const time = this.context.currentTime;
        const osc = this.context.createOscillator();
        const gain = this.context.createGain();

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.frequency.setValueAtTime(1200, time);
        osc.frequency.exponentialRampToValueAtTime(600, time + 0.15);
        osc.type = 'sine';

        gain.gain.setValueAtTime(0.3, time);
        gain.gain.exponentialRampToValueAtTime(0.001, time + 0.15);

        osc.start(time);
        osc.stop(time + 0.15);
    }

    /**
     * Play a musical note (for ear training, etc.)
     */
    playNote(midiNumber, duration = 0.5) {
        if (!this.isEnabled || !this.context) return;

        const frequency = this.midiToFrequency(midiNumber);
        const time = this.context.currentTime;

        const osc = this.context.createOscillator();
        const gain = this.context.createGain();

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.frequency.value = frequency;
        osc.type = 'sine';

        gain.gain.setValueAtTime(0.3, time);
        gain.gain.exponentialRampToValueAtTime(0.001, time + duration);

        osc.start(time);
        osc.stop(time + duration);
    }

    /**
     * Play multiple notes simultaneously (chord)
     */
    playChord(midiNumbers, duration = 1.0) {
        midiNumbers.forEach(midi => {
            this.playNote(midi, duration);
        });
    }

    /**
     * Play notes in sequence (melody)
     */
    playMelody(midiNumbers, noteDuration = 0.3, gap = 0.05) {
        if (!this.isEnabled || !this.context) return;

        let time = this.context.currentTime;

        midiNumbers.forEach((midi, i) => {
            const frequency = this.midiToFrequency(midi);

            const osc = this.context.createOscillator();
            const gain = this.context.createGain();

            osc.connect(gain);
            gain.connect(this.masterGain);

            osc.frequency.value = frequency;
            osc.type = 'sine';

            gain.gain.setValueAtTime(0.3, time);
            gain.gain.exponentialRampToValueAtTime(0.001, time + noteDuration);

            osc.start(time);
            osc.stop(time + noteDuration);

            time += noteDuration + gap;
        });
    }

    /**
     * Play a rhythm pattern (for rhythm dictation)
     */
    playRhythm(pattern, tempo = 100) {
        if (!this.isEnabled || !this.context) return;

        const beatDuration = 60.0 / tempo; // Duration of one quarter note in seconds
        let time = this.context.currentTime + 0.1; // Small delay

        pattern.forEach((noteValue) => {
            const duration = noteValue * beatDuration;

            // Play click at the start of each note
            this.scheduleNote(time, 800, 0.05, false);

            time += duration;
        });
    }

    /**
     * Convert MIDI number to frequency
     */
    midiToFrequency(midiNumber) {
        return 440.0 * Math.pow(2.0, (midiNumber - 69) / 12.0);
    }

    /**
     * Speak instruction using Text-to-Speech
     */
    speak(text) {
        if (!this.isEnabled) return;

        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.2;
            speechSynthesis.speak(utterance);
        }
    }

    /**
     * Stop all audio
     */
    stopAll() {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }

        if (this.schedulerTimerId) {
            clearInterval(this.schedulerTimerId);
            this.schedulerTimerId = null;
        }

        // Close and recreate context to stop all sounds
        if (this.context) {
            this.context.close();
            this.context = null;
            this.masterGain = null;
        }
    }

    /**
     * Get current time from audio context
     */
    getCurrentTime() {
        return this.context ? this.context.currentTime : 0;
    }
}

// Create singleton instance
const audioManager = new AudioManager();
