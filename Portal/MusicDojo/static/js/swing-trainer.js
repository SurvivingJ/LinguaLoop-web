/**
 * Swing Trainer Mode
 * Canvas-based scrolling notes showing downbeat vs swung offbeat
 */

class SwingTrainer {
    constructor() {
        this.isRunning = false;
        this.tempo = 100;
        this.swingStyle = 'light';
        // Canvas state
        this.canvas = null;
        this.ctx = null;
        this.canvasWidth = 0;
        this.canvasHeight = 0;
        this.hitLineY = 0;
        this.notes = [];
        this.scrollSpeed = 200;
        this.animFrameId = null;
        this.schedulerTimerId = null;
        this.lastTimestamp = 0;
        this.elapsedTime = 0;
        this.currentBeat = -1;
        this.beatsPerMeasure = 4;
        // Audio scheduling
        this.audioNextBeat = 0;
        this.audioBeatCount = 0;
    }

    getSwingPercentage() {
        const map = { straight: 50, light: 58, heavy: 66, shuffle: 75 };
        return map[this.swingStyle] || 50;
    }

    async init() {
        const container = document.getElementById('swing-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="swing-tempo" min="60" max="200" value="${this.tempo}">
                    <span id="swing-tempo-display">${this.tempo}</span> BPM
                </div>
                <div class="control-row">
                    <label>Swing Style:</label>
                    <select id="swing-style">
                        <option value="straight">Straight (50%)</option>
                        <option value="light" selected>Light Swing (58%)</option>
                        <option value="heavy">Heavy Swing (66%)</option>
                        <option value="shuffle">Shuffle (75%)</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="swing-start">Start</button>
                    <button class="btn btn-danger hidden" id="swing-stop">Stop</button>
                </div>
            </div>

            <div class="canvas-container">
                <canvas id="swing-canvas"></canvas>
            </div>

            <div class="stats-row mt-md">
                <div class="stat">
                    <div class="stat-value" id="swing-elapsed">00:00</div>
                    <div class="stat-label">Time</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="swing-beat">0</div>
                    <div class="stat-label">Beat</div>
                </div>
            </div>
        `;

        document.getElementById('swing-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('swing-tempo-display').textContent = this.tempo;
        });

        document.getElementById('swing-style').addEventListener('change', (e) => {
            this.swingStyle = e.target.value;
        });

        document.getElementById('swing-start').addEventListener('click', () => this.start());
        document.getElementById('swing-stop').addEventListener('click', () => this.stop());

        // Draw initial empty canvas
        this.initCanvas();
        this.clearCanvas();
        this.drawLane();
        this.drawHitLine();
    }

    initCanvas() {
        this.canvas = document.getElementById('swing-canvas');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();
        this._resizeHandler = () => this.resizeCanvas();
        window.addEventListener('resize', this._resizeHandler);
    }

    resizeCanvas() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = 350 * dpr;
        this.canvas.style.height = '350px';
        this.ctx.scale(dpr, dpr);
        this.canvasWidth = rect.width;
        this.canvasHeight = 350;
        this.hitLineY = this.canvasHeight - 50;
    }

    clearCanvas() {
        this.ctx.fillStyle = '#1a202c';
        this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    }

    drawLane() {
        const ctx = this.ctx;
        const centerX = this.canvasWidth / 2;
        ctx.strokeStyle = '#4a5568';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(centerX, 0);
        ctx.lineTo(centerX, this.canvasHeight);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#a0aec0';
        ctx.font = 'bold 14px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText(`${this.getSwingPercentage()}% Swing`, centerX, 20);
    }

    drawHitLine() {
        const ctx = this.ctx;
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#667eea';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.moveTo(0, this.hitLineY);
        ctx.lineTo(this.canvasWidth, this.hitLineY);
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    drawNote(note) {
        const ctx = this.ctx;
        const x = this.canvasWidth / 2;
        const radius = note.isDownbeat ? 14 : 10;

        let color = note.isDownbeat ? '#667eea' : '#9f7aea';
        if (note.isAccent) color = '#ecc94b';

        ctx.beginPath();
        ctx.arc(x, note.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        if (note.isAccent) {
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    spawnNotes() {
        const beatDurMs = getBeatDurationMs(this.tempo);
        const swingPct = this.getSwingPercentage();
        const offbeatDelay = beatDurMs * (swingPct / 100);
        const pxPerMs = this.scrollSpeed / 1000;
        const isAccent = this.currentBeat % this.beatsPerMeasure === 0;

        // Downbeat
        this.notes.push({
            y: -14,
            isDownbeat: true,
            isAccent: isAccent
        });

        // Swung offbeat (offset in y based on swing delay)
        const offbeatYOffset = offbeatDelay * pxPerMs;
        this.notes.push({
            y: -10 - offbeatYOffset,
            isDownbeat: false,
            isAccent: false
        });
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;
        this.elapsedTime += delta;

        // Calculate beat
        const beatDurMs = getBeatDurationMs(this.tempo);
        const newBeat = Math.floor((this.elapsedTime * 1000) / beatDurMs);

        if (newBeat !== this.currentBeat) {
            this.currentBeat = newBeat;
            this.spawnNotes();
        }

        // Update positions
        this.notes.forEach(n => { n.y += this.scrollSpeed * delta; });
        this.notes = this.notes.filter(n => n.y < this.canvasHeight + 30);

        // Draw
        this.clearCanvas();
        this.drawLane();
        this.drawHitLine();
        this.notes.forEach(n => this.drawNote(n));

        // Update stats
        const elEl = document.getElementById('swing-elapsed');
        if (elEl) elEl.textContent = formatTime(this.elapsedTime);
        const beatEl = document.getElementById('swing-beat');
        if (beatEl) beatEl.textContent = this.currentBeat;

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    startAudioScheduler() {
        const ctx = audioManager.context;
        if (!ctx) return;

        const beatDur = getBeatDurationSec(this.tempo);
        this.audioNextBeat = ctx.currentTime;
        this.audioBeatCount = 0;

        this.schedulerTimerId = setInterval(() => {
            if (!this.isRunning || !audioManager.context) return;
            const now = audioManager.context.currentTime;
            const swingPct = this.getSwingPercentage();

            while (this.audioNextBeat < now + 0.1) {
                const beatDurNow = getBeatDurationSec(this.tempo);
                const isAccent = this.audioBeatCount % this.beatsPerMeasure === 0;
                // Downbeat
                audioManager.scheduleNote(this.audioNextBeat, isAccent ? 900 : 700, 0.05, isAccent);
                // Swung offbeat
                const offbeatTime = this.audioNextBeat + beatDurNow * (swingPct / 100);
                audioManager.scheduleNote(offbeatTime, 500, 0.04, false);

                this.audioNextBeat += beatDurNow;
                this.audioBeatCount++;
            }
        }, 25);
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;
        this.notes = [];
        this.currentBeat = -1;
        this.lastTimestamp = 0;
        this.elapsedTime = 0;

        document.getElementById('swing-start').classList.add('hidden');
        document.getElementById('swing-stop').classList.remove('hidden');

        this.initCanvas();
        this.startAudioScheduler();
        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
        if (this.schedulerTimerId) clearInterval(this.schedulerTimerId);
        if (this._resizeHandler) window.removeEventListener('resize', this._resizeHandler);
        this.notes = [];

        document.getElementById('swing-start').classList.remove('hidden');
        document.getElementById('swing-stop').classList.add('hidden');
    }
}

window.swing = new SwingTrainer();
