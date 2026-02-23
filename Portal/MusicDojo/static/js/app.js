/**
 * MusicDojo - Main App Initialization
 */

// Global state flag
window.gameActive = false;

// Debug helper - type debugMusicDojo() in browser console
window.debugMusicDojo = function() {
    console.log('=== MusicDojo Debug Info ===');
    console.log('Current screen:', screenManager?.getCurrentScreen());
    console.log('Storage data:', storageManager?.loadAll());
    console.log('Audio context state:', audioManager?.context?.state);
    console.log('Available modes:', {
        direction_trainer: !!window.direction_trainer,
        split_metronome: !!window.split_metronome,
        polyrhythm: !!window.polyrhythm,
        swing: !!window.swing,
        tempo_ramp: !!window.tempo_ramp,
        improv: !!window.improv,
        ghost: !!window.ghost,
        ear_training: !!window.ear_training,
        rhythm_dictation: !!window.rhythm_dictation,
        metronome: !!window.metronome,
        guitar_exercises: !!window.guitar_exercises,
        guitar_metronome: !!window.guitar_metronome
    });
    console.log('=== End Debug Info ===');
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('MusicDojo initializing...');

    try { themeManager.loadTheme(); } catch(e) { console.error('Theme load failed:', e); }
    try { screenManager.updateHomeScreenStats(); } catch(e) { console.error('Stats update failed:', e); }
    try { storageManager.updateStreak(); } catch(e) { console.error('Streak update failed:', e); }

    // Initialize audio context on first user interaction
    document.addEventListener('click', () => {
        audioManager.initialize();
    }, { once: true });

    // Setup navigation buttons - CRITICAL: must succeed for modes to work
    try {
        setupNavigationButtons();
    } catch(e) {
        console.error('CRITICAL: Navigation setup failed:', e);
    }

    try { setupSettingsScreen(); } catch(e) { console.error('Settings setup failed:', e); }
    try { setupStatsScreen(); } catch(e) { console.error('Stats screen setup failed:', e); }
    try { checkAchievements(); } catch(e) { console.error('Achievement check failed:', e); }

    console.log('MusicDojo initialized!');
});

/**
 * Setup navigation buttons on home screen
 */
function setupNavigationButtons() {
    // Training mode buttons
    const modeButtons = {
        'btn-direction': 'direction-trainer',
        'btn-split': 'split-metronome',
        'btn-polyrhythm': 'polyrhythm',
        'btn-swing': 'swing',
        'btn-tempo-ramp': 'tempo-ramp',
        'btn-improv': 'improv',
        'btn-ghost': 'ghost',
        'btn-ear-training': 'ear-training',
        'btn-rhythm-dictation': 'rhythm-dictation',
        'btn-metronome': 'metronome',
        'btn-guitar-exercises': 'guitar-exercises'
    };

    for (const [buttonId, screenId] of Object.entries(modeButtons)) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', () => {
                screenManager.showScreen(screenId);

                // Initialize mode if it has an init function
                const modeName = screenId.replace(/-/g, '_');
                if (window[modeName] && window[modeName].init) {
                    window[modeName].init();
                }
            });
        }
    }

    // Stats button
    const statsBtn = document.getElementById('btn-stats');
    if (statsBtn) {
        statsBtn.addEventListener('click', () => {
            screenManager.showScreen('stats');
            screenManager.updateStatsScreen();
        });
    }

    // Settings button
    const settingsBtn = document.getElementById('btn-settings');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            screenManager.showScreen('settings');
        });
    }

    // Back buttons (on all screens)
    document.querySelectorAll('.btn-back').forEach(btn => {
        btn.addEventListener('click', () => {
            screenManager.showScreen('home');
        });
    });
}

/**
 * Setup settings screen controls
 */
function setupSettingsScreen() {
    const settings = storageManager.load('settings');

    // Sound toggle
    const soundToggle = document.getElementById('settings-sound-toggle');
    if (soundToggle) {
        soundToggle.checked = settings.sound_enabled;
        soundToggle.addEventListener('change', (e) => {
            audioManager.setEnabled(e.target.checked);
        });
    }

    // Volume slider
    const volumeSlider = document.getElementById('settings-volume');
    const volumeValue = document.getElementById('settings-volume-value');
    if (volumeSlider) {
        volumeSlider.value = settings.master_volume * 100;
        if (volumeValue) {
            volumeValue.textContent = Math.round(settings.master_volume * 100) + '%';
        }

        volumeSlider.addEventListener('input', (e) => {
            const volume = e.target.value / 100;
            audioManager.setMasterVolume(volume);
            if (volumeValue) {
                volumeValue.textContent = Math.round(e.target.value) + '%';
            }
        });
    }

    // Metronome sound type
    const metronomeSound = document.getElementById('settings-metronome-sound');
    if (metronomeSound) {
        metronomeSound.value = settings.metronome_sound || 'sine';
        metronomeSound.addEventListener('change', (e) => {
            settings.metronome_sound = e.target.value;
            storageManager.save('settings', settings);
        });
    }

    // Theme selector
    const themeSelector = document.getElementById('settings-theme');
    if (themeSelector) {
        themeSelector.value = settings.theme || 'NEON_PULSE';
        themeSelector.addEventListener('change', (e) => {
            themeManager.applyTheme(e.target.value);
        });
    }

    // Reset progress button
    const resetBtn = document.getElementById('settings-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (storageManager.resetAll()) {
                alert('Progress reset! Reloading...');
                location.reload();
            }
        });
    }

    // Export data button
    const exportBtn = document.getElementById('settings-export');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            storageManager.exportData();
        });
    }

    // Import data button
    const importBtn = document.getElementById('settings-import');
    const importFile = document.getElementById('settings-import-file');
    if (importBtn && importFile) {
        importBtn.addEventListener('click', () => {
            importFile.click();
        });

        importFile.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    if (storageManager.importData(event.target.result)) {
                        alert('Data imported successfully! Reloading...');
                        location.reload();
                    } else {
                        alert('Error importing data. Please check the file.');
                    }
                };
                reader.readAsText(file);
            }
        });
    }
}

/**
 * Setup stats screen
 */
function setupStatsScreen() {
    // Stats will be updated when screen is shown
    // See screenManager.updateStatsScreen()
}

/**
 * Check and award achievements
 */
function checkAchievements() {
    const data = storageManager.loadAll();

    // First Session achievement
    let hasAnySession = false;
    for (const mode in data.mode_progress) {
        if (data.mode_progress[mode].sessions > 0) {
            hasAnySession = true;
            break;
        }
    }
    if (hasAnySession) {
        awardAchievement('first_session', 'First Session', 'Completed your first practice session!');
    }

    // Week Warrior achievement (7-day streak)
    if (data.daily_streak.count >= 7) {
        awardAchievement('week_warrior', 'Week Warrior', '7-day practice streak!');
    }

    // Polyrhythm Master achievement
    const polyProgress = data.mode_progress.polyrhythm;
    if (polyProgress && polyProgress.ratios_mastered && polyProgress.ratios_mastered.includes('5:4')) {
        awardAchievement('polyrhythm_master', 'Polyrhythm Master', 'Mastered the 5:4 polyrhythm!');
    }

    // Speed Demon achievement (200 BPM in tempo ramp)
    const tempoProgress = data.mode_progress.tempo_ramp;
    if (tempoProgress && tempoProgress.max_tempo_reached >= 200) {
        awardAchievement('speed_demon', 'Speed Demon', 'Reached 200 BPM!');
    }

    // Ear Training achievements
    const earProgress = data.mode_progress.ear_training;
    if (earProgress && earProgress.total >= 50 && (earProgress.correct / earProgress.total) >= 0.9) {
        awardAchievement('ear_training_master', 'Ear Training Master', '90% accuracy on 50+ exercises!');
    }

    // Total practice time achievements
    const totalTime = storageManager.getTotalPracticeTime();
    const hours = totalTime / 3600;

    if (hours >= 1) {
        awardAchievement('one_hour', 'First Hour', 'Practiced for 1 hour total!');
    }
    if (hours >= 10) {
        awardAchievement('ten_hours', 'Dedicated Musician', 'Practiced for 10 hours total!');
    }
    if (hours >= 100) {
        awardAchievement('hundred_hours', 'Master Practitioner', 'Practiced for 100 hours total!');
    }
}

/**
 * Award an achievement if not already earned
 */
function awardAchievement(id, name, description) {
    if (storageManager.addAchievement(id)) {
        // Show achievement notification
        showAchievementNotification(name, description);
    }
}

/**
 * Show achievement notification popup
 */
function showAchievementNotification(name, description) {
    const notification = document.createElement('div');
    notification.className = 'achievement-notification';
    notification.innerHTML = `
        <div class="achievement-icon">🏆</div>
        <div class="achievement-content">
            <div class="achievement-name">${name}</div>
            <div class="achievement-desc">${description}</div>
        </div>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    // Remove after 4 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);

    // Play success sound
    audioManager.playChirp();
}

/**
 * Format time in seconds to readable string
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format large numbers with commas
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Calculate beats per measure duration in milliseconds
 */
function getBeatDurationMs(tempo) {
    return 60000 / tempo;
}

/**
 * Calculate beats per measure duration in seconds
 */
function getBeatDurationSec(tempo) {
    return 60 / tempo;
}

/**
 * Clamp a value between min and max
 */
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

/**
 * Get random integer between min and max (inclusive)
 */
function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Get random element from array
 */
function getRandomElement(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Generate unique ID
 */
function generateId() {
    return '_' + Math.random().toString(36).substr(2, 9);
}
