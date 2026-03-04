# RetroMind Math 🕹️

A retro 80s-style mental math trainer with three game modes and zero friction - no login required!

## Features

- **Time Trial**: 60-second speed challenge with dynamic difficulty scaling
- **Space Defense**: Arcade-style game where you shoot down falling enemies by solving equations
- **Daily Drill**: Structured 50-level progression system with "The Coach" feedback
- **Elo Rating System**: Adaptive difficulty based on your performance
- **Local Storage**: All progress saved in your browser - no account needed
- **Retro Aesthetic**: CRT scanlines, neon green text, pixel fonts

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask server:
```bash
python app.py
```

4. Open your browser to: `http://localhost:5000`

## Game Modes

### Time Trial
- 60 seconds to solve as many problems as possible
- Difficulty increases every 5 correct answers
- Earn Elo points faster for quick answers

### Space Defense
- Enemies fall from the top with equations
- Type the answer and press Enter to fire your laser
- Don't let enemies reach the bottom (3 lives)

### Daily Drill
- 50 structured levels from basic addition to advanced mixed operations
- Pass criteria: accuracy and time limits
- Unlock up to 3 new levels per day
- "The Coach" provides personalized feedback

## Technology Stack

**Backend:**
- Flask (Python)
- Math problem generator with difficulty scaling

**Frontend:**
- Vanilla JavaScript (ES6+)
- HTML5 Canvas for Space Defense
- CSS3 with retro CRT effects
- localStorage for persistence

## File Structure

```
MathDojo/
├── app.py                  # Flask server
├── math_engine.py          # Problem generation logic
├── requirements.txt
├── templates/
│   └── index.html          # Main SPA
└── static/
    ├── css/
    │   └── style.css       # Retro styling
    └── js/
        ├── game-manager.js
        ├── storage-manager.js
        ├── screen-manager.js
        ├── input-handler.js
        ├── time-trial.js
        ├── space-defense.js
        ├── daily-drill.js
        └── app.js
```

## License

MIT
