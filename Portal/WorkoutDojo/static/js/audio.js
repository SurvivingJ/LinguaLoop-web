// static/js/audio.js — WorkoutOS Audio & Haptics

const AudioContext = window.AudioContext || window.webkitAudioContext;
let ctx = null;

function getCtx() {
    if (!ctx) ctx = new AudioContext();
    return ctx;
}

function resumeAudio() {
    // Call on user gesture (iOS requirement)
    if (ctx) ctx.resume();
    else ctx = new AudioContext();
}

function playTone(frequency, duration, type = 'sine', volume = 0.4) {
    const c = getCtx();
    const oscillator = c.createOscillator();
    const gainNode   = c.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(c.destination);
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, c.currentTime);
    gainNode.gain.setValueAtTime(volume, c.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
    oscillator.start(c.currentTime);
    oscillator.stop(c.currentTime + duration);
}

const Sounds = {
    setComplete:  () => playTone(880, 0.15),
    restWarning:  () => [660, 770, 880].forEach((f, i) =>
                      setTimeout(() => playTone(f, 0.12), i * 120)),
    restComplete: () => [523, 659, 784].forEach((f, i) =>
                      setTimeout(() => playTone(f, 0.25), i * 150)),
    workoutDone:  () => [523, 587, 659, 698, 784].forEach((f, i) =>
                      setTimeout(() => playTone(f, 0.3), i * 180)),
    autoAdvance:  () => playTone(660, 0.1),
    rpeWarning:   () => playTone(300, 0.2, 'triangle', 0.3),
};

const Vibrations = {
    setComplete:  () => navigator.vibrate?.(50),
    restWarning:  () => navigator.vibrate?.([50, 50, 50, 50, 50]),
    restComplete: () => navigator.vibrate?.(200),
    workoutDone:  () => navigator.vibrate?.([100, 80, 100, 80, 300]),
    autoAdvance:  () => navigator.vibrate?.(100),
};

function triggerFlash(type) {
    const overlay = document.getElementById('flash-overlay');
    if (!overlay) return;
    overlay.className = `flash-overlay ${type}`;
    overlay.addEventListener('animationend', () => overlay.className = 'flash-overlay', { once: true });
}

function announce(text) {
    const settings = getSettings();
    if (!settings.voiceEnabled) return;
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

function getSettings() {
    try {
        return JSON.parse(localStorage.getItem('workoutOS_settings') || '{}');
    } catch { return {}; }
}

function notifyEvent(eventName, overrides = {}) {
    const settings = getSettings();
    const defaults = {
        setComplete:  { sound: false, flash: 'set-complete', vibrate: 'setComplete' },
        restWarning:  { sound: true,  flash: 'rest-warning',  vibrate: 'restWarning' },
        restComplete: { sound: true,  flash: 'rest-complete', vibrate: 'restComplete' },
        workoutDone:  { sound: true,  flash: null,            vibrate: 'workoutDone' },
        autoAdvance:  { sound: true,  flash: null,            vibrate: 'autoAdvance' },
    };
    const cfg = { ...defaults[eventName], ...overrides };

    // Sound
    const soundKey = (eventName === 'setComplete') ? 'soundSetComplete' :
                     (eventName === 'restWarning')  ? 'soundRestWarning' :
                     (eventName === 'restComplete') ? 'soundRestComplete' :
                     (eventName === 'workoutDone')  ? 'soundWorkoutComplete' : null;
    const soundEnabled = soundKey ? (settings[soundKey] !== false) : cfg.sound;
    if (soundEnabled && Sounds[eventName]) Sounds[eventName]();

    // Visual flash
    if (settings.visualFlash !== false && cfg.flash) triggerFlash(cfg.flash);

    // Vibration
    if (settings.vibration !== false && cfg.vibrate) Vibrations[cfg.vibrate]?.();
}
