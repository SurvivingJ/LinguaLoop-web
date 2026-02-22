/**
 * Split Metronome Mode - Simplified
 * Two independent metronomes
 */

class SplitMetronome {
    constructor() {
        this.isRunning = false;
        this.tempoLeft = 60;
        this.tempoRight = 60;
    }

    async init() {
        const container = document.getElementById('split-metronome-content');
        if (!container) return;

        container.innerHTML = `
            <div class="controls">
                <div class="control-row">
                    <label>Left Tempo:</label>
                    <input type="range" id="split-left" min="40" max="200" value="60">
                    <span id="split-left-display">60</span> BPM
                </div>
                <div class="control-row">
                    <label>Right Tempo:</label>
                    <input type="range" id="split-right" min="40" max="200" value="60">
                    <span id="split-right-display">60</span> BPM
                </div>
                <div class="control-row">
                    <button class="btn btn-primary" id="split-start">Start</button>
                    <button class="btn btn-danger hidden" id="split-stop">Stop</button>
                </div>
            </div>

            <div class="display-area">
                <p>Practice with two independent metronomes - left and right channels</p>
            </div>
        `;

        document.getElementById('split-left').addEventListener('input', (e) => {
            this.tempoLeft = parseInt(e.target.value);
            document.getElementById('split-left-display').textContent = this.tempoLeft;
        });

        document.getElementById('split-right').addEventListener('input', (e) => {
            this.tempoRight = parseInt(e.target.value);
            document.getElementById('split-right-display').textContent = this.tempoRight;
        });

        document.getElementById('split-start').addEventListener('click', () => this.start());
        document.getElementById('split-stop').addEventListener('click', () => this.stop());
    }

    start() {
        window.gameActive = true;
        audioManager.initialize();
        this.isRunning = true;

        document.getElementById('split-start').classList.add('hidden');
        document.getElementById('split-stop').classList.remove('hidden');

        // Start both metronomes
        this.startMetronomes();
    }

    startMetronomes() {
        const intervalLeft = (60 / this.tempoLeft) * 1000;
        const intervalRight = (60 / this.tempoRight) * 1000;

        this.intervalLeft = setInterval(() => {
            if (!this.isRunning) return;
            audioManager.playClick(700, 0.05);
        }, intervalLeft);

        this.intervalRight = setInterval(() => {
            if (!this.isRunning) return;
            audioManager.playClick(900, 0.05);
        }, intervalRight);
    }

    stop() {
        window.gameActive = false;
        this.isRunning = false;

        if (this.intervalLeft) clearInterval(this.intervalLeft);
        if (this.intervalRight) clearInterval(this.intervalRight);

        document.getElementById('split-start').classList.remove('hidden');
        document.getElementById('split-stop').classList.add('hidden');
    }
}

const split_metronome = new SplitMetronome();
