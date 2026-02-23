/**
 * Ghost Metronome Mode
 * Canvas with fading notes, phase badge, background transitions, progress ring
 */

class GhostMetronome {
    constructor() {
        this.isRunning = false;
        this.tempo = 100;
        this.activeBars = 4;
        this.ghostBars = 2;
        this.beatsPerBar = 4;
        this.currentPhase = 'active';
        this.currentBeat = 1;
        this.currentBar = 1;
        this.cycleCount = 0;
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
        // Fade state
        this.isFadingOut = false;
        this.isFadingIn = false;
        this.fadeProgress = 0;
        this.isMuted = false;
        // Audio scheduling
        this.audioNextBeat = 0;
        this.audioBeatInBar = 0;
        this.audioBarInPhase = 1;
        this.audioPhase = 'active';
    }

    async init() {
        const container = document.getElementById('ghost-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="ghost-tempo" min="60" max="160" value="${this.tempo}">
                    <span id="ghost-tempo-display">${this.tempo}</span> BPM
                </div>
                <div class="control-row">
                    <label>Active Bars:</label>
                    <input type="number" id="ghost-active" min="1" max="8" value="${this.activeBars}">
                </div>
                <div class="control-row">
                    <label>Ghost Bars:</label>
                    <input type="number" id="ghost-ghost" min="1" max="8" value="${this.ghostBars}">
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="ghost-start">Start</button>
                    <button class="btn btn-danger hidden" id="ghost-stop">Stop</button>
                </div>
            </div>

            <div class="cycle-display" id="ghost-cycle-display">
                <span class="cycle-status active" id="ghost-cycle-status">Ready to start</span>
                <span class="phase-badge active" id="ghost-phase-badge">ACTIVE</span>
                <div class="ghost-info">Cycles completed: <strong id="ghost-cycle-count">0</strong></div>
            </div>

            <div class="ghost-canvas-container" id="ghost-canvas-container">
                <canvas class="ghost-canvas" id="ghost-canvas"></canvas>
            </div>
        `;

        document.getElementById('ghost-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('ghost-tempo-display').textContent = this.tempo;
        });
        document.getElementById('ghost-active').addEventListener('input', (e) => {
            this.activeBars = parseInt(e.target.value) || 4;
        });
        document.getElementById('ghost-ghost').addEventListener('input', (e) => {
            this.ghostBars = parseInt(e.target.value) || 2;
        });

        document.getElementById('ghost-start').addEventListener('click', () => this.start());
        document.getElementById('ghost-stop').addEventListener('click', () => this.stop());
    }

    initCanvas() {
        this.canvas = document.getElementById('ghost-canvas');
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
        this.canvas.height = 300 * dpr;
        this.canvas.style.height = '300px';
        this.ctx.scale(dpr, dpr);
        this.canvasWidth = rect.width;
        this.canvasHeight = 300;
        this.hitLineY = this.canvasHeight - 40;
    }

    clearCanvas() {
        const bg = this.currentPhase === 'ghost' ? '#1a365d' : '#1a202c';
        this.ctx.fillStyle = bg;
        this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    }

    drawHitLine() {
        const ctx = this.ctx;
        const isActive = this.currentPhase === 'active';
        ctx.strokeStyle = isActive ? '#48bb78' : '#667eea';
        ctx.lineWidth = 3;
        ctx.shadowColor = isActive ? '#48bb78' : '#667eea';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.moveTo(0, this.hitLineY);
        ctx.lineTo(this.canvasWidth, this.hitLineY);
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    drawNote(note) {
        const ctx = this.ctx;
        if (note.opacity <= 0) return;
        const x = this.canvasWidth / 2;
        const radius = note.isAccent ? 16 : 12;

        ctx.globalAlpha = note.opacity;
        ctx.beginPath();
        ctx.arc(x, note.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = note.isAccent ? '#ecc94b' : '#667eea';
        ctx.fill();

        if (note.isAccent) {
            ctx.shadowColor = '#ecc94b';
            ctx.shadowBlur = 15;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
        ctx.globalAlpha = 1;
    }

    drawProgressRing() {
        const ctx = this.ctx;
        if (this.currentPhase !== 'ghost') return;

        const progress = this.calculateProgress();
        const cx = this.canvasWidth / 2;
        const cy = this.canvasHeight / 2;
        const radius = 60;

        // Background ring
        ctx.strokeStyle = '#4a5568';
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();

        // Progress arc
        ctx.strokeStyle = '#667eea';
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + progress * Math.PI * 2);
        ctx.stroke();
        ctx.lineCap = 'butt';

        // Remaining beats text
        const totalGhostBeats = this.ghostBars * this.beatsPerBar;
        const elapsedBeats = (this.currentBar - 1) * this.beatsPerBar + (this.currentBeat - 1);
        const remaining = Math.max(0, totalGhostBeats - elapsedBeats);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 20px system-ui';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(remaining.toString(), cx, cy);
        ctx.textBaseline = 'alphabetic';
    }

    calculateProgress() {
        const totalBeats = this.ghostBars * this.beatsPerBar;
        const elapsed = (this.currentBar - 1) * this.beatsPerBar + (this.currentBeat - 1);
        return Math.min(1, elapsed / totalBeats);
    }

    spawnNote(beatNum) {
        this.notes.push({
            y: -20,
            beatNumber: beatNum,
            isAccent: beatNum === 1,
            opacity: this.currentPhase === 'active' ? 1 : 0.15,
            spawnedInPhase: this.currentPhase
        });
    }

    updateNotePositions(delta) {
        this.notes.forEach(n => {
            n.y += this.scrollSpeed * delta;
            if (this.currentPhase === 'ghost' || this.isFadingOut) {
                n.opacity = Math.max(0, n.opacity - delta * 2);
            } else if (this.isFadingIn && n.spawnedInPhase === 'active') {
                n.opacity = Math.min(1, n.opacity + delta * 3);
            }
        });
        this.notes = this.notes.filter(n => n.y < this.canvasHeight + 30);
    }

    transitionToActive() {
        this.currentPhase = 'active';
        this.currentBar = 1;
        this.currentBeat = 1;
        this.isMuted = false;
        this.isFadingIn = true;
        this.isFadingOut = false;
        this.updateCycleDisplay();
    }

    transitionToGhost() {
        this.currentPhase = 'ghost';
        this.currentBar = 1;
        this.currentBeat = 1;
        this.cycleCount++;
        this.isMuted = true;
        this.isFadingOut = true;
        this.isFadingIn = false;
        this.updateCycleDisplay();
    }

    incrementBeat() {
        this.currentBeat++;
        if (this.currentBeat > this.beatsPerBar) {
            this.currentBeat = 1;
            this.currentBar++;

            if (this.currentPhase === 'active' && this.currentBar > this.activeBars) {
                this.transitionToGhost();
            } else if (this.currentPhase === 'ghost' && this.currentBar > this.ghostBars) {
                this.transitionToActive();
            }
        }
        this.updateCycleDisplay();
    }

    updateCycleDisplay() {
        const statusEl = document.getElementById('ghost-cycle-status');
        const badgeEl = document.getElementById('ghost-phase-badge');
        const countEl = document.getElementById('ghost-cycle-count');

        if (statusEl) {
            statusEl.textContent = this.currentPhase === 'active'
                ? `Active: Bar ${this.currentBar}/${this.activeBars}`
                : `Ghost: Bar ${this.currentBar}/${this.ghostBars}`;
            statusEl.className = 'cycle-status ' + this.currentPhase;
        }
        if (badgeEl) {
            badgeEl.textContent = this.currentPhase === 'active' ? 'ACTIVE' : 'GHOST';
            badgeEl.className = 'phase-badge ' + this.currentPhase;
        }
        if (countEl) countEl.textContent = this.cycleCount;

        const container = document.getElementById('ghost-canvas-container');
        if (container) {
            container.style.backgroundColor = this.currentPhase === 'ghost' ? '#1a365d' : '';
        }
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;

        if (this.isFadingIn) {
            this.fadeProgress += delta * 3;
            if (this.fadeProgress >= 1) { this.isFadingIn = false; this.fadeProgress = 0; }
        }
        if (this.isFadingOut) {
            this.fadeProgress += delta * 3;
            if (this.fadeProgress >= 1) { this.isFadingOut = false; this.fadeProgress = 0; }
        }

        this.updateNotePositions(delta);

        this.clearCanvas();
        this.drawHitLine();
        this.notes.forEach(n => this.drawNote(n));
        this.drawProgressRing();

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    startAudioScheduler() {
        const ctx = audioManager.context;
        if (!ctx) return;

        this.audioNextBeat = ctx.currentTime;
        this.audioBeatInBar = 0;
        this.audioBarInPhase = 1;
        this.audioPhase = 'active';

        this.schedulerTimerId = setInterval(() => {
            if (!this.isRunning || !audioManager.context) return;
            const now = audioManager.context.currentTime;

            while (this.audioNextBeat < now + 0.1) {
                this.audioBeatInBar++;

                if (this.audioBeatInBar > this.beatsPerBar) {
                    this.audioBeatInBar = 1;
                    this.audioBarInPhase++;

                    if (this.audioPhase === 'active' && this.audioBarInPhase > this.activeBars) {
                        this.audioPhase = 'ghost';
                        this.audioBarInPhase = 1;
                    } else if (this.audioPhase === 'ghost' && this.audioBarInPhase > this.ghostBars) {
                        this.audioPhase = 'active';
                        this.audioBarInPhase = 1;
                    }
                }

                this.spawnNote(this.audioBeatInBar);
                this.incrementBeat();

                if (this.audioPhase === 'active') {
                    const isAccent = this.audioBeatInBar === 1;
                    audioManager.scheduleNote(this.audioNextBeat, isAccent ? 1000 : 700, 0.05, isAccent);
                }

                this.audioNextBeat += getBeatDurationSec(this.tempo);
            }
        }, 25);
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;
        this.currentPhase = 'active';
        this.currentBeat = 1;
        this.currentBar = 1;
        this.cycleCount = 0;
        this.notes = [];
        this.lastTimestamp = 0;
        this.isFadingIn = false;
        this.isFadingOut = false;
        this.isMuted = false;

        document.getElementById('ghost-start').classList.add('hidden');
        document.getElementById('ghost-stop').classList.remove('hidden');

        this.updateCycleDisplay();
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

        document.getElementById('ghost-start').classList.remove('hidden');
        document.getElementById('ghost-stop').classList.add('hidden');
    }
}

window.ghost = new GhostMetronome();
