/**
 * Split Metronome Mode
 * Two-panel layout with animated circle indicators per side
 */

class SplitMetronome {
    constructor() {
        this.isRunning = false;
        this.tempoLeft = 60;
        this.tempoRight = 60;
        this.visualEnabledLeft = true;
        this.audioEnabledLeft = true;
        this.visualEnabledRight = true;
        this.audioEnabledRight = true;
        this.lastSubLeft = -1;
        this.lastSubRight = -1;
        this.animFrameId = null;
        this.startTime = 0;
        this.elapsedTime = 0;
        this.lastTimestamp = 0;
    }

    async init() {
        const container = document.getElementById('split-metronome-content');
        if (!container) return;

        container.innerHTML = `
            <div class="split-container">
                <div class="metronome-side">
                    <h3>Triplets (3)</h3>
                    <div class="control-row" style="justify-content:center">
                        <label>BPM</label>
                        <input type="number" id="split-left-bpm" value="${this.tempoLeft}" min="40" max="200">
                    </div>
                    <div class="visual-indicator" id="split-visual-left">3</div>
                    <div class="toggle-row">
                        <button class="btn-toggle on" id="split-tog-vis-l">Visual</button>
                        <button class="btn-toggle on" id="split-tog-aud-l">Audio</button>
                    </div>
                </div>
                <div class="metronome-side">
                    <h3>Quavers (2)</h3>
                    <div class="control-row" style="justify-content:center">
                        <label>BPM</label>
                        <input type="number" id="split-right-bpm" value="${this.tempoRight}" min="40" max="200">
                    </div>
                    <div class="visual-indicator" id="split-visual-right">2</div>
                    <div class="toggle-row">
                        <button class="btn-toggle on" id="split-tog-vis-r">Visual</button>
                        <button class="btn-toggle on" id="split-tog-aud-r">Audio</button>
                    </div>
                </div>
            </div>

            <div class="display-area" style="min-height:60px;margin-top:15px">
                <div class="stat">
                    <div class="stat-value" id="split-elapsed">00:00</div>
                    <div class="stat-label">Elapsed</div>
                </div>
            </div>

            <div class="control-row" style="justify-content:center;margin-top:15px">
                <button class="btn btn-primary" id="split-start">Start</button>
                <button class="btn btn-danger hidden" id="split-stop">Stop</button>
            </div>
        `;

        document.getElementById('split-left-bpm').addEventListener('input', (e) => {
            this.tempoLeft = parseInt(e.target.value) || 60;
        });
        document.getElementById('split-right-bpm').addEventListener('input', (e) => {
            this.tempoRight = parseInt(e.target.value) || 60;
        });

        // Toggle buttons
        this.setupToggle('split-tog-vis-l', 'visualEnabledLeft');
        this.setupToggle('split-tog-aud-l', 'audioEnabledLeft');
        this.setupToggle('split-tog-vis-r', 'visualEnabledRight');
        this.setupToggle('split-tog-aud-r', 'audioEnabledRight');

        document.getElementById('split-start').addEventListener('click', () => this.start());
        document.getElementById('split-stop').addEventListener('click', () => this.stop());
    }

    setupToggle(btnId, prop) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        btn.addEventListener('click', () => {
            this[prop] = !this[prop];
            btn.className = 'btn-toggle ' + (this[prop] ? 'on' : 'off');
        });
    }

    getSubdivision(elapsedMs, tempo, divs) {
        const beatDur = getBeatDurationMs(tempo);
        const subDur = beatDur / divs;
        return Math.floor((elapsedMs % beatDur) / subDur);
    }

    updateVisualLeft(sub) {
        const el = document.getElementById('split-visual-left');
        if (el) {
            el.className = 'visual-indicator' + (this.visualEnabledLeft ? ' a' + sub : '');
            el.textContent = sub;
        }
    }

    updateVisualRight(sub) {
        const el = document.getElementById('split-visual-right');
        if (el) {
            el.className = 'visual-indicator' + (this.visualEnabledRight ? ' a' + sub : '');
            el.textContent = sub;
        }
    }

    animationLoop(timestamp) {
        if (!this.isRunning) return;

        if (this.lastTimestamp === 0) this.lastTimestamp = timestamp;
        const delta = (timestamp - this.lastTimestamp) / 1000;
        this.lastTimestamp = timestamp;
        this.elapsedTime += delta;

        const elapsedMs = this.elapsedTime * 1000;

        // Left: triplets (3 subdivisions)
        const subL = this.getSubdivision(elapsedMs, this.tempoLeft, 3);
        if (subL !== this.lastSubLeft) {
            this.lastSubLeft = subL;
            this.updateVisualLeft(subL);
            if (this.audioEnabledLeft) {
                audioManager.playClick(subL === 0 ? 880 : 660, 0.04);
            }
        }

        // Right: quavers (2 subdivisions)
        const subR = this.getSubdivision(elapsedMs, this.tempoRight, 2);
        if (subR !== this.lastSubRight) {
            this.lastSubRight = subR;
            this.updateVisualRight(subR);
            if (this.audioEnabledRight) {
                audioManager.playClick(subR === 0 ? 440 : 330, 0.04);
            }
        }

        // Update elapsed time
        const el = document.getElementById('split-elapsed');
        if (el) el.textContent = formatTime(this.elapsedTime);

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;
        this.lastSubLeft = -1;
        this.lastSubRight = -1;
        this.lastTimestamp = 0;
        this.elapsedTime = 0;

        document.getElementById('split-start').classList.add('hidden');
        document.getElementById('split-stop').classList.remove('hidden');

        this.animFrameId = requestAnimationFrame((t) => this.animationLoop(t));
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);

        document.getElementById('split-start').classList.remove('hidden');
        document.getElementById('split-stop').classList.add('hidden');
    }
}

window.split_metronome = new SplitMetronome();
