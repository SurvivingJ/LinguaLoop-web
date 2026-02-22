/**
 * Swing Trainer Mode - Simplified
 */

class SwingTrainer {
    constructor() {
        this.isRunning = false;
        this.tempo = 100;
        this.swingStyle = 'light';
    }

    async init() {
        const container = document.getElementById('swing-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Tempo:</label>
                    <input type="range" id="swing-tempo" min="80" max="200" value="100">
                    <span id="swing-tempo-display">100</span> BPM
                </div>
                <div class="control-row">
                    <label>Swing Style:</label>
                    <select id="swing-style">
                        <option value="straight">Straight</option>
                        <option value="light" selected>Light Swing</option>
                        <option value="heavy">Heavy Swing</option>
                        <option value="shuffle">Shuffle</option>
                    </select>
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="swing-start">Start</button>
                    <button class="btn btn-danger hidden" id="swing-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <h3 id="swing-display">Light Swing</h3>
                <p>Feel the swing rhythm</p>
            </div>
        `;

        document.getElementById('swing-tempo').addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            document.getElementById('swing-tempo-display').textContent = this.tempo;
        });

        document.getElementById('swing-style').addEventListener('change', (e) => {
            this.swingStyle = e.target.value;
            document.getElementById('swing-display').textContent = e.target.options[e.target.selectedIndex].text;
        });

        document.getElementById('swing-start').addEventListener('click', () => this.start());
        document.getElementById('swing-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        document.getElementById('swing-start').classList.add('hidden');
        document.getElementById('swing-stop').classList.remove('hidden');

        this.playSwing();
    }

    playSwing() {
        const swingPercentages = { straight: 50, light: 58, heavy: 66, shuffle: 75 };
        const swingPct = swingPercentages[this.swingStyle];
        const beatDuration = (60 / this.tempo) * 1000;
        const offbeatDelay = beatDuration * (swingPct / 100);

        let downbeat = true;
        this.intervalId = setInterval(() => {
            if (!this.isRunning) return;

            if (downbeat) {
                audioManager.playClick(900, 0.05, true);
                setTimeout(() => {
                    if (this.isRunning) audioManager.playClick(700, 0.04);
                }, offbeatDelay);
            }

            downbeat = !downbeat;
        }, beatDuration / 2);
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.intervalId) clearInterval(this.intervalId);

        document.getElementById('swing-start').classList.remove('hidden');
        document.getElementById('swing-stop').classList.add('hidden');
    }
}

const swing = new SwingTrainer();
