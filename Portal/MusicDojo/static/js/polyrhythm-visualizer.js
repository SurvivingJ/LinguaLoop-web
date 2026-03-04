/**
 * Polyrhythm Visualizer Mode
 * Canvas-based scrolling notes with two vertical lanes
 */

class PolyrhythmVisualizer {
    constructor() {
        this.isRunning = false;
        this.tempo = 90;
        this.ratioLeft = 3;
        this.ratioRight = 2;
        // Canvas state
        this.canvas = null;
        this.ctx = null;
        this.canvasWidth = 0;
        this.canvasHeight = 0;
        this.hitLineY = 0;
        this.laneLeftX = 0;
        this.laneRightX = 0;
        this.notes = [];
        this.scrollSpeed = 200;
        this.noteRadius = 12;
        this.animFrameId = null;
        this.schedulerTimerId = null;
        this.lastTimestamp = 0;
        this.startTime = 0;
        this.lastCycle = -1;
        this.elapsedTime = 0;
        // Audio scheduling
        this.audioNextLeft = 0;
        this.audioNextRight = 0;
        this.audioBeatLeft = 0;
        this.audioBeatRight = 0;
    }

    async init() {
        const container = document.getElementById('polyrhythm-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="poly-tempo" min="40" max="160" value="${this.tempo}">
                    <span id="poly-tempo-display">${this.tempo}</span> BPM
                </div>
                <div class="control-row">
                    <label>Ratio:</label>
                    <select id="poly-ratio">
                        <option value="2:1">2:1</option>
                        <option value="3:2" selected>3:2</option>
                        <option value="4:3">4:3</option>
                        <option value="5:4">5:4</option>
                        <option value="7:4">7:4</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="poly-start">Start</button>
                    <button class="btn btn-danger hidden" id="poly-stop">Stop</button>
                </div>
            </div>

            <div class="canvas-container">
                <canvas id="poly-canvas"></canvas>
            </div>

            <div class="stats-row mt-md">
                <div class="stat">
                    <div class="stat-value" id="poly-elapsed">00:00</div>
                    <div class="stat-label">Time</div>
                </div>
            </div>
        `;

        document.getElementById('poly-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('poly-tempo-display').textContent = this.tempo;
        });

        document.getElementById('poly-ratio').addEventListener('change', (e) => {
            const [left, right] = e.target.value.split(':').map(n => parseInt(n));
            this.ratioLeft = left;
            this.ratioRight = right;
        });

        document.getElementById('poly-start').addEventListener('click', () => this.start());
        document.getElementById('poly-stop').addEventListener('click', () => this.stop());

        // Draw initial empty canvas
        this.initCanvas();
        this.clearCanvas();
        this.drawLanes();
        this.drawHitLine(false);
    }

    gcd(a, b) { return b === 0 ? a : this.gcd(b, a % b); }
    lcm(a, b) { return (a * b) / this.gcd(a, b); }

    initCanvas() {
        this.canvas = document.getElementById('poly-canvas');
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
        this.laneLeftX = this.canvasWidth * 0.35;
        this.laneRightX = this.canvasWidth * 0.65;
    }

    clearCanvas() {
        this.ctx.fillStyle = '#1a202c';
        this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    }

    drawLanes() {
        const ctx = this.ctx;
        ctx.strokeStyle = '#4a5568';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(this.laneLeftX, 0);
        ctx.lineTo(this.laneLeftX, this.canvasHeight);
        ctx.moveTo(this.laneRightX, 0);
        ctx.lineTo(this.laneRightX, this.canvasHeight);
        ctx.stroke();
        ctx.setLineDash([]);

        // Lane labels
        ctx.fillStyle = '#a0aec0';
        ctx.font = 'bold 14px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText(this.ratioLeft.toString(), this.laneLeftX, 20);
        ctx.fillText(this.ratioRight.toString(), this.laneRightX, 20);
    }

    drawHitLine(isAligned) {
        const ctx = this.ctx;
        ctx.strokeStyle = isAligned ? '#ecc94b' : '#667eea';
        ctx.lineWidth = isAligned ? 4 : 3;
        ctx.shadowColor = isAligned ? '#ecc94b' : '#667eea';
        ctx.shadowBlur = isAligned ? 15 : 8;
        ctx.beginPath();
        ctx.moveTo(0, this.hitLineY);
        ctx.lineTo(this.canvasWidth, this.hitLineY);
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    drawNote(note) {
        const ctx = this.ctx;
        const x = note.lane === 'left' ? this.laneLeftX : this.laneRightX;

        let color = note.lane === 'left' ? '#667eea' : '#9f7aea';
        if (note.isAccent) color = '#ecc94b';
        if (note.isAligned) color = '#48bb78';

        ctx.beginPath();
        ctx.arc(x, note.y, this.noteRadius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        if (note.isAccent || note.isAligned) {
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    getAlignedBeats() {
        const l = this.ratioLeft;
        const r = this.ratioRight;
        const lcmVal = this.lcm(l, r);
        const alignedLeft = new Set();
        const alignedRight = new Set();

        for (let i = 0; i < lcmVal; i++) {
            if (i % (lcmVal / l) === 0 && i % (lcmVal / r) === 0) {
                alignedLeft.add(i / (lcmVal / l));
                alignedRight.add(i / (lcmVal / r));
            }
        }
        return { alignedLeft, alignedRight };
    }

    spawnNotes() {
        const l = this.ratioLeft;
        const r = this.ratioRight;
        const cycleDurMs = getBeatDurationMs(this.tempo) * Math.max(l, r);
        const pxPerMs = this.scrollSpeed / 1000;
        const { alignedLeft, alignedRight } = this.getAlignedBeats();

        for (let i = 0; i < l; i++) {
            const timeOffset = (i / l) * cycleDurMs;
            const yOffset = timeOffset * pxPerMs;
            this.notes.push({
                lane: 'left',
                beatIndex: i,
                y: -this.noteRadius - yOffset,
                isAccent: i === 0,
                isAligned: alignedLeft.has(i)
            });
        }

        for (let i = 0; i < r; i++) {
            const timeOffset = (i / r) * cycleDurMs;
            const yOffset = timeOffset * pxPerMs;
            this.notes.push({
                lane: 'right',
                beatIndex: i,
                y: -this.noteRadius - yOffset,
                isAccent: i === 0,
                isAligned: alignedRight.has(i)
            });
        }
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;
        this.elapsedTime += delta;

        // Calculate cycle
        const cycleDurMs = getBeatDurationMs(this.tempo) * Math.max(this.ratioLeft, this.ratioRight);
        const currentCycle = Math.floor((this.elapsedTime * 1000) / cycleDurMs);

        if (currentCycle !== this.lastCycle) {
            this.lastCycle = currentCycle;
            this.spawnNotes();
        }

        // Update positions
        this.notes.forEach(n => { n.y += this.scrollSpeed * delta; });

        // Check alignment at hit line
        let isAligned = false;
        this.notes.forEach(n => {
            if (n.isAligned && Math.abs(n.y - this.hitLineY) < 15) isAligned = true;
        });

        // Cull off-screen
        this.notes = this.notes.filter(n => n.y < this.canvasHeight + 30);

        // Draw
        this.clearCanvas();
        this.drawLanes();
        this.drawHitLine(isAligned);
        this.notes.forEach(n => this.drawNote(n));

        // Update elapsed
        const el = document.getElementById('poly-elapsed');
        if (el) el.textContent = formatTime(this.elapsedTime);

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    startAudioScheduler() {
        const ctx = audioManager.context;
        if (!ctx) return;

        const l = this.ratioLeft;
        const r = this.ratioRight;
        const cycleDur = getBeatDurationSec(this.tempo) * Math.max(l, r);
        const leftInterval = cycleDur / l;
        const rightInterval = cycleDur / r;

        this.audioNextLeft = ctx.currentTime;
        this.audioNextRight = ctx.currentTime;
        this.audioBeatLeft = 0;
        this.audioBeatRight = 0;

        this.schedulerTimerId = setInterval(() => {
            if (!this.isRunning || !audioManager.context) return;
            const now = audioManager.context.currentTime;

            while (this.audioNextLeft < now + 0.1) {
                const isAccent = this.audioBeatLeft % l === 0;
                audioManager.scheduleNote(this.audioNextLeft, isAccent ? 880 : 660, 0.05, isAccent);
                this.audioNextLeft += leftInterval;
                this.audioBeatLeft++;
            }

            while (this.audioNextRight < now + 0.1) {
                const isAccent = this.audioBeatRight % r === 0;
                audioManager.scheduleNote(this.audioNextRight, isAccent ? 440 : 330, 0.05, isAccent);
                this.audioNextRight += rightInterval;
                this.audioBeatRight++;
            }
        }, 25);
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;
        this.notes = [];
        this.lastCycle = -1;
        this.lastTimestamp = 0;
        this.elapsedTime = 0;

        document.getElementById('poly-start').classList.add('hidden');
        document.getElementById('poly-stop').classList.remove('hidden');

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

        document.getElementById('poly-start').classList.remove('hidden');
        document.getElementById('poly-stop').classList.add('hidden');
    }
}

window.polyrhythm = new PolyrhythmVisualizer();
