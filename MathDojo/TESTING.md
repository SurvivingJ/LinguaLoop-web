# Testing Guide for RetroMind Math

## Quick Start
1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open browser to: `http://localhost:5000`

## Manual Testing Checklist

### Backend API Testing
- [x] GET `/api/problem?elo=1000` returns valid problem JSON
- [x] POST `/api/batch` with `{"count": 5, "elo": 1200}` returns array of problems
- [ ] Verify difficulty scaling at different Elo levels (800, 1000, 1200, 1400)
- [ ] Check that division problems always return whole numbers
- [ ] Verify all math operations are correct

### Frontend Testing

#### Main Menu
- [ ] Menu loads with retro aesthetic (CRT scanlines, neon green text)
- [ ] Streak and Elo display correctly from localStorage
- [ ] All four menu buttons navigate to correct screens
- [ ] Settings button works

#### Time Trial Mode
- [ ] Click START begins 60-second countdown
- [ ] Equation displays correctly with Unicode symbols (×, ÷, ²)
- [ ] Input accepts numeric answers
- [ ] Pressing Enter submits answer
- [ ] Correct answer: green flash, score increments, next problem loads
- [ ] Wrong answer: red flash, screen shake, shows correct answer
- [ ] Timer reaches 0: game ends, shows results screen
- [ ] Results screen displays: score, accuracy, problems/min, new Elo
- [ ] High score is saved and "NEW HIGH SCORE" banner appears
- [ ] Back to menu button works

#### Space Defense Mode
- [ ] Canvas renders with starfield background
- [ ] Click START spawns enemies with equations
- [ ] Enemies fall from top at increasing speed
- [ ] Typing correct answer + Enter fires laser and destroys enemy
- [ ] Explosion particle effect plays
- [ ] Enemy reaching bottom decreases life (hearts)
- [ ] Lives reach 0: game ends
- [ ] Score increases for each destroyed enemy
- [ ] Results screen shows score, enemies destroyed, time survived

#### Daily Drill Mode
- [ ] Level grid displays 50 levels
- [ ] Level 1 is unlocked by default
- [ ] Future levels show lock icon 🔒
- [ ] Clicking unlocked level navigates to drill game screen
- [ ] Click START begins level with timer and problem count
- [ ] Problems load from queue
- [ ] Progress counter updates (e.g., "5/10")
- [ ] Completing all problems with >90% accuracy: PASS
- [ ] Coach modal appears with feedback message
- [ ] Passing unlocks next level
- [ ] Daily limit (3 levels/day) enforced
- [ ] "Too easy" auto-skip works (>20% time remaining)
- [ ] Completed levels show amber color
- [ ] Can replay completed levels

#### Settings Screen
- [ ] Sound toggle switches between ON/OFF
- [ ] Difficulty offset slider works (-10 to +10)
- [ ] Reset progress button shows confirmation
- [ ] Reset actually clears localStorage and reloads

#### localStorage Persistence
- [ ] Refresh page: Elo, streak, high scores persist
- [ ] Complete Time Trial: Elo updates correctly (+10, +5, +2, -15 based on speed)
- [ ] Daily streak increments when playing
- [ ] Daily streak resets if day missed
- [ ] Level progress saves correctly

### Cross-Browser Testing
- [ ] Chrome/Edge: all features work
- [ ] Firefox: all features work
- [ ] Safari: all features work (if Mac available)
- [ ] Mobile Chrome: responsive layout, touch-friendly buttons
- [ ] Mobile Safari: responsive layout, touch-friendly buttons

### Performance Testing
- [ ] Time Trial: zero delay between problems
- [ ] Space Defense: smooth 60fps animation
- [ ] Canvas renders correctly on different screen sizes
- [ ] No memory leaks during extended gameplay

### Edge Cases
- [ ] API unreachable: fallback problems generate client-side
- [ ] Empty input submission: ignored
- [ ] Negative numbers work (e.g., subtraction results)
- [ ] Escape key returns to menu (when game not active)
- [ ] Browser refresh during active game: warns before leaving
- [ ] localStorage quota (unlikely but handle gracefully)

## Known Limitations (Current Version)
- Audio uses silent placeholder sounds (replace with actual 8-bit WAV files)
- No actual sound effects yet (AudioManager is ready)
- Deployment config included but not tested on Heroku/Render

## Future Enhancements
- Add actual 8-bit sound effects
- Add more visual effects (CRT glow, text flicker)
- Add statistics dashboard
- Add achievements system
- Add practice mode for specific operation types
