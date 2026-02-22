# MusicDojo - Quick Start Guide

## ✅ Implementation Status: COMPLETE

All features requested have been implemented:
- ✅ Complete Portal Integration (Flask backend + SPA frontend)
- ✅ All 7 existing modes ported (Direction, Split, Polyrhythm, Swing, Tempo Ramp, Improv, Ghost)
- ✅ Ear Training mode (intervals, chords, progressions)
- ✅ Rhythm Dictation mode (pattern recognition)
- ✅ Advanced Metronome (subdivisions, accents, tap tempo)

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd Portal/MusicDojo
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Server

```bash
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

## 🎵 What You'll See

**Home Screen:**
- 10 training mode buttons
- Your stats (Elo, Streak, Practice Time, Achievements)
- Stats and Settings buttons

**Training Modes:**
1. Direction Trainer - Hand coordination
2. Split Metronome - Dual tempos
3. Polyrhythm - Complex ratios
4. Swing Trainer - Feel the groove
5. Tempo Ramp - Progressive speed
6. Improv Generator - Jazz scales
7. Ghost Metronome - Internalize beat
8. **Ear Training** - Recognize intervals/chords ⭐
9. **Rhythm Dictation** - Identify patterns ⭐
10. **Advanced Metronome** - Full-featured ⭐

## 🎮 Quick Test

1. **Click "Ear Training"**
   - Click "Start Session"
   - Listen to the interval/chord
   - Select your answer from 4 choices
   - Get instant feedback!

2. **Try "Advanced Metronome"**
   - Adjust tempo, subdivisions, accent patterns
   - Try "Tap Tempo" - tap 4+ times to set tempo
   - Start and feel the beat!

3. **Check Stats**
   - Click "📊 Stats" from home
   - See your progress across all modes

## 🎨 Customize

**Settings Screen:**
- Toggle sound on/off
- Adjust master volume
- Choose metronome sound (sine/square/triangle/sawtooth)
- Select from 8 visual themes
- Export/import your data
- Reset progress

## 📊 Progress Tracking

Everything is saved to your browser's localStorage:
- ✅ Elo rating (adaptive difficulty)
- ✅ Daily practice streak
- ✅ High scores per mode
- ✅ Session history
- ✅ Achievements earned
- ✅ Mode-specific stats

**No login required!** All data stays in your browser.

## 🔧 API Endpoints

The Flask backend provides these endpoints:

- `GET /` - Main app
- `GET /api/exercise?mode=ear_training&elo=1000` - Single exercise
- `POST /api/batch` - Batch of exercises
- `GET /api/scale-info?key=C&scale_type=Major` - Scale info
- `GET /health` - Health check

## 🎯 Architecture Highlights

**Backend (Flask):**
- 8 exercise generators with Elo-based difficulty
- CORS enabled for localhost + production domains
- RESTful API design

**Frontend (SPA):**
- 5 core managers (storage, screen, game, audio, theme)
- 10 training mode classes
- Web Audio API integration
- Responsive design

**Data Flow:**
```
User Action → Mode Class → Game Manager → Flask API →
Exercise Generator → Response → Audio Manager → User Feedback
```

## 🐛 Troubleshooting

**Server won't start?**
```bash
# Make sure virtual environment is activated
# Check if port 5000 is available
lsof -i :5000  # Mac/Linux
netstat -ano | findstr :5000  # Windows
```

**No sound?**
- Click anywhere on the page first (browsers require user interaction to enable audio)
- Check Settings → Sound Enabled
- Adjust Master Volume

**Progress not saving?**
- Check browser console for localStorage errors
- Make sure cookies/localStorage are enabled

## 🚀 Deployment

Ready to deploy to production!

**Heroku:**
```bash
heroku create musicdojo
git push heroku main
```

**Railway/Render:**
- Connect GitHub repo
- Auto-detects Procfile
- Sets PORT environment variable

**Environment Variables:**
- `FLASK_DEBUG=false` (production)
- `PORT=5000` (or auto-assigned)

## 📈 Next Steps

**Enhance Existing Modes:**
- Add canvas visualizations to polyrhythm
- Implement keyboard/fretboard for improv
- Add more complex ear training progressions

**New Features (from plan):**
- MIDI input support
- Backing track generator
- Practice session planner
- Progressive Web App (PWA)

**Integration:**
- Add to portal hub
- Link from LinguaLoop main site
- Deploy to music.linguadojo.com

## 📝 Notes

- All modes use simplified but functional implementations
- Can be enhanced with more features later
- Architecture is modular and extensible
- Follows MathDojo pattern for consistency

## 🎉 You're Ready!

The app is **fully functional** and ready to use. Start practicing and master your musical skills! 🎵

---

**Built with Claude Code** - Anthropic's official CLI
