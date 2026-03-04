# MusicDojo

Master rhythm, timing, and musicality with this comprehensive music training web application.

## Features

### Training Modes

1. **Direction Trainer** - Practice hand coordination with similar/contrary/oblique motion
2. **Split Metronome** - Dual-tempo practice with independent metronomes
3. **Polyrhythm Visualizer** - Master complex rhythmic ratios (3:2, 4:3, 5:4, etc.)
4. **Swing Trainer** - Practice different swing feels (straight, light, heavy, shuffle)
5. **Tempo Ramp** - Progressive tempo increase with automatic ramping
6. **Improv Generator** - Jazz scale and pattern combinations for improvisation practice
7. **Ghost Metronome** - Internalize the beat with active/silent bar cycling
8. **Ear Training** - Interval, chord, and progression recognition exercises
9. **Rhythm Dictation** - Recognize and identify rhythm patterns
10. **Advanced Metronome** - Full-featured metronome with subdivisions, accent patterns, and tap tempo

### Core Features

- **Elo-based Difficulty System** - Adaptive exercises that match your skill level
- **Progress Tracking** - localStorage-based progress tracking with detailed statistics
- **Daily Streak System** - Track your practice consistency
- **Achievement System** - Unlock badges for milestones
- **8 Visual Themes** - Choose from music-themed color schemes
- **No Login Required** - All progress stored locally in your browser
- **Offline-First** - Works without internet after initial load

## Installation & Setup

### Local Development

1. **Install Dependencies**
   ```bash
   cd Portal/MusicDojo
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the Development Server**
   ```bash
   python app.py
   ```

3. **Open in Browser**
   Navigate to `http://localhost:5000`

### Production Deployment

The app is configured for deployment to platforms like Heroku, Railway, or any WSGI-compatible host.

**Environment Variables:**
- `FLASK_DEBUG` - Set to `true` for debug mode (default: `false`)
- `PORT` - Port number (default: `5000`)

**Deploy Command:**
```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 30
```

## Project Structure

```
MusicDojo/
├── app.py                      # Flask backend server
├── music_engine.py             # Exercise generation logic
├── wsgi.py                     # WSGI entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Deployment configuration
├── templates/
│   └── index.html              # Main SPA template
└── static/
    ├── css/
    │   └── style.css           # Music-themed styling
    └── js/
        ├── app.js              # App initialization
        ├── storage-manager.js  # localStorage wrapper
        ├── screen-manager.js   # Navigation system
        ├── game-manager.js     # API client
        ├── audio-manager.js    # Web Audio API wrapper
        ├── theme-manager.js    # Theme system
        ├── direction-trainer.js
        ├── split-metronome.js
        ├── polyrhythm-visualizer.js
        ├── swing-trainer.js
        ├── tempo-ramp.js
        ├── improv-generator.js
        ├── ghost-metronome.js
        ├── ear-training.js
        ├── rhythm-dictation.js
        └── metronome.js
```

## Architecture

### Backend (Flask)

- **API Endpoints:**
  - `GET /` - Serve main HTML page
  - `GET /api/exercise` - Get single exercise (mode + elo based)
  - `POST /api/batch` - Get batch of exercises
  - `GET /api/scale-info` - Get scale information
  - `GET /health` - Health check

- **Exercise Generators:**
  - DirectionExerciseGenerator
  - PolyrhythmGenerator
  - SwingExerciseGenerator
  - TempoRampGenerator
  - ScalePatternGenerator
  - GhostMetronomeGenerator
  - EarTrainingGenerator
  - RhythmDictationGenerator

### Frontend (SPA)

- **Core Managers (Singletons):**
  - `storageManager` - localStorage persistence
  - `screenManager` - Screen navigation
  - `gameManager` - API communication & exercise management
  - `audioManager` - Web Audio API wrapper
  - `themeManager` - Visual theming

- **Mode Classes:**
  - Each training mode is an independent class
  - Initialized when user navigates to the mode
  - Manages own state, UI, and audio

### Data Persistence

All data stored in localStorage under key `musicdojo_data`:

```javascript
{
  user_elo: 1000,
  daily_streak: { last_played, count },
  high_scores: { ... },
  settings: { sound_enabled, theme, master_volume, metronome_sound },
  mode_progress: { ... },
  achievements: [],
  practice_log: []
}
```

## API Usage

### Get Single Exercise

```http
GET /api/exercise?mode=ear_training&elo=1200
```

Response:
```json
{
  "id": "ex_123456",
  "mode": "ear_training",
  "exercise_type": "interval",
  "interval_name": "Perfect 5th",
  "root_midi": 60,
  "top_midi": 67,
  "choices": ["Perfect 5th", "Perfect 4th", "Major 6th", "Minor 7th"],
  "correct_answer": "Perfect 5th"
}
```

### Get Exercise Batch

```http
POST /api/batch
Content-Type: application/json

{
  "mode": "rhythm_dictation",
  "count": 10,
  "elo": 1000
}
```

## Themes

8 built-in themes:
- **Neon Pulse** (default) - Purple/blue neon
- **Jazz Lounge** - Dark red/gold
- **Classical Concert** - Black/white/gold
- **Retro Synth** - Pink/cyan/purple
- **Forest Acoustic** - Green/brown earth tones
- **Midnight Keys** - Deep blue/silver
- **Sunset Stage** - Orange/pink/yellow
- **Minimal Mono** - Grayscale modern

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari
- Any modern browser with Web Audio API support

## License

Part of the LinguaLoop Portal project.

## Credits

Built with Claude Code - Anthropic's official CLI for Claude.
