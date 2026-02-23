/**
 * Direction Trainer Mode
 * Color-coded instructions, beat pulse, warning system, beat/time counters
 */

class DirectionTrainer {
    constructor() {
        this.isRunning = false;
        this.tempo = 80;
        this.motionType = 'similar';
        this.noteRange = 8;
        this.elapsedTime = 0;
        this.currentBeat = -1;
        this.notesSinceChange = 0;
        this.nextChangeBeat = 4;
        this.warningBeat = -1;
        this.pendingInstruction = null;
        this.currentInstruction = null;
        this.animFrameId = null;
        this.startTime = 0;
        this.lastTimestamp = 0;
        this.leftPos = 1;
        this.rightPos = 1;
    }

    async init() {
        const container = document.getElementById('direction-trainer-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="dir-tempo" min="40" max="160" value="${this.tempo}" step="5">
                    <span id="dir-tempo-display">${this.tempo}</span> BPM
                </div>
                <div class="control-row">
                    <label>Motion Type:</label>
                    <select id="dir-motion">
                        <option value="similar">Similar</option>
                        <option value="contrary">Contrary</option>
                        <option value="oblique">Oblique</option>
                        <option value="mixed">Mixed</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="dir-start">Start Practice</button>
                    <button class="btn btn-danger hidden" id="dir-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <div class="instruction-text" id="dir-instruction">
                    Click Start to begin practicing hand coordination
                </div>
                <div class="beat-indicator" id="dir-beat-indicator"></div>
                <div class="stats-row mt-md">
                    <div class="stat">
                        <div class="stat-value" id="dir-elapsed">00:00</div>
                        <div class="stat-label">Time</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="dir-beat-count">0</div>
                        <div class="stat-label">Beat</div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('dir-tempo').addEventListener('input', (e) => {
            document.getElementById('dir-tempo-display').textContent = e.target.value;
            this.tempo = parseInt(e.target.value);
        });

        document.getElementById('dir-motion').addEventListener('change', (e) => {
            this.motionType = e.target.value;
        });

        document.getElementById('dir-start').addEventListener('click', () => this.start());
        document.getElementById('dir-stop').addEventListener('click', () => this.stop());
    }

    generateInstruction() {
        let right, left, motion;
        const dirs = ['UP', 'DOWN'];
        const motionType = this.motionType === 'mixed'
            ? ['similar', 'contrary', 'oblique'][Math.floor(Math.random() * 3)]
            : this.motionType;

        right = dirs[Math.floor(Math.random() * 2)];

        if (motionType === 'similar') {
            left = right;
            motion = 'SIMILAR';
        } else if (motionType === 'contrary') {
            left = right === 'UP' ? 'DOWN' : 'UP';
            motion = 'CONTRARY';
        } else {
            left = 'HOLD';
            motion = 'OBLIQUE';
        }

        return { right, left, motion };
    }

    updateDirectionDisplay(instruction, isWarning) {
        const el = document.getElementById('dir-instruction');
        if (!el || !instruction) return;

        const rClass = instruction.right === 'UP' ? 'up' : (instruction.right === 'DOWN' ? 'down' : 'hold');
        const lClass = instruction.left === 'UP' ? 'up' : (instruction.left === 'DOWN' ? 'down' : 'hold');

        let html = `<span class="${rClass}">R: ${instruction.right}</span> | <span class="${lClass}">L: ${instruction.left}</span>`;
        html += `<span class="motion">${instruction.motion} MOTION</span>`;
        if (isWarning) {
            html += `<span class="warning">CHANGE COMING</span>`;
        }
        el.innerHTML = html;
    }

    displayBeatIndicator() {
        const el = document.getElementById('dir-beat-indicator');
        if (el) {
            el.classList.add('pulse');
            setTimeout(() => el.classList.remove('pulse'), 100);
        }
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;
        this.elapsedTime += delta;

        const beatDurMs = getBeatDurationMs(this.tempo);
        const newBeat = Math.floor((this.elapsedTime * 1000) / beatDurMs);

        if (newBeat !== this.currentBeat) {
            this.currentBeat = newBeat;
            this.notesSinceChange++;

            // Beat pulse
            this.displayBeatIndicator();
            audioManager.playClick(800, 0.05);

            // Check for warning (2 beats before change)
            if (this.currentBeat === this.nextChangeBeat - 2 && !this.pendingInstruction) {
                this.pendingInstruction = this.generateInstruction();
                this.updateDirectionDisplay(this.currentInstruction, true);
            }

            // Execute direction change
            if (this.currentBeat >= this.nextChangeBeat) {
                this.currentInstruction = this.pendingInstruction || this.generateInstruction();
                this.pendingInstruction = null;
                this.notesSinceChange = 0;
                // Next change in 4-8 beats
                this.nextChangeBeat = this.currentBeat + 4 + Math.floor(Math.random() * 5);
                this.updateDirectionDisplay(this.currentInstruction, false);
            }
        }

        // Update stats
        const elEl = document.getElementById('dir-elapsed');
        if (elEl) elEl.textContent = formatTime(this.elapsedTime);
        const beatEl = document.getElementById('dir-beat-count');
        if (beatEl) beatEl.textContent = this.currentBeat;

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;
        this.currentBeat = -1;
        this.elapsedTime = 0;
        this.lastTimestamp = 0;
        this.notesSinceChange = 0;
        this.nextChangeBeat = 0;
        this.pendingInstruction = null;
        this.currentInstruction = this.generateInstruction();
        this.leftPos = 1;
        this.rightPos = 1;

        this.updateDirectionDisplay(this.currentInstruction, false);
        document.getElementById('dir-start').classList.add('hidden');
        document.getElementById('dir-stop').classList.remove('hidden');

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);

        document.getElementById('dir-start').classList.remove('hidden');
        document.getElementById('dir-stop').classList.add('hidden');
        document.getElementById('dir-instruction').textContent = 'Click Start to begin practicing hand coordination';
    }
}

window.direction_trainer = new DirectionTrainer();
