/**
 * SpaceDefense - Canvas-based game mode
 */
class SpaceDefense {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.isActive = false;
        this.lives = 3;
        this.score = 0;
        this.enemies = [];
        this.particles = [];
        this.stars = [];
        this.problems = [];
        this.animationFrame = null;
        this.spawnTimer = 0;
        this.spawnInterval = 3000; // Start with 3 seconds
        this.gameStartTime = 0;
        this.currentElo = 1000;

        // DOM elements
        this.startButton = document.getElementById('start-space-defense');
        this.livesDisplay = document.getElementById('lives-display');
        this.scoreDisplay = document.getElementById('space-score-display');

        // Input handler
        this.inputHandler = new InputHandler('space-answer-input', (answer) => this.handleAnswer(answer));

        this.colors = null;

        this.setupCanvas();
        this.setupEventListeners();
    }

    /**
     * Setup canvas
     */
    setupCanvas() {
        if (!this.canvas) return;

        // Make canvas responsive
        const resizeCanvas = () => {
            const container = this.canvas.parentElement;
            const rect = container.getBoundingClientRect();
            this.canvas.width = Math.min(600, rect.width - 40);
            this.canvas.height = 400;
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Generate starfield
        this.generateStars();
    }

    /**
     * Generate background stars
     */
    generateStars() {
        this.stars = [];
        for (let i = 0; i < 50; i++) {
            this.stars.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 2
            });
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        if (this.startButton) {
            this.startButton.addEventListener('click', () => this.start());
        }
    }

    /**
     * Start the game
     */
    async start() {
        this.isActive = true;
        window.gameActive = true;
        this.lives = 3;
        this.score = 0;
        this.enemies = [];
        this.particles = [];
        this.spawnTimer = 0;
        this.spawnInterval = 3000;
        this.gameStartTime = Date.now();
        this.currentElo = storageManager.load('user_elo');
        this.colors = themeManager.getCanvasColors();

        // Hide start button
        if (this.startButton) this.startButton.style.display = 'none';

        // Enable input
        this.inputHandler.enable();
        this.inputHandler.clear();
        this.inputHandler.focus();

        // Load problems
        this.problems = await gameManager.fetchBatch(100, this.currentElo);

        // Update displays
        this.updateDisplay();

        // Start game loop
        this.gameLoop();
    }

    /**
     * Main game loop
     */
    gameLoop() {
        if (!this.isActive) return;

        const now = Date.now();
        const deltaTime = 16; // Assume ~60fps

        // Update game state
        this.update(deltaTime);

        // Render
        this.render();

        // Continue loop
        this.animationFrame = requestAnimationFrame(() => this.gameLoop());
    }

    /**
     * Update game state
     */
    update(deltaTime) {
        // Spawn enemies
        this.spawnTimer += deltaTime;
        if (this.spawnTimer >= this.spawnInterval && this.problems.length > 0) {
            this.spawnEnemy();
            this.spawnTimer = 0;

            // Increase difficulty over time (faster spawns)
            const elapsed = (Date.now() - this.gameStartTime) / 1000;
            this.spawnInterval = Math.max(1500, 3000 - (elapsed * 20));
        }

        // Update enemies
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            enemy.y += enemy.speed;

            // Check if reached bottom
            if (enemy.y > this.canvas.height) {
                this.enemies.splice(i, 1);
                this.loseLife();
            }

            // Flash red when near bottom
            enemy.isUrgent = enemy.y > this.canvas.height - 100;
        }

        // Update particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= deltaTime;

            if (p.life <= 0) {
                this.particles.splice(i, 1);
            }
        }

        // Animate stars (slow scroll)
        this.stars.forEach(star => {
            star.y += 0.2;
            if (star.y > this.canvas.height) {
                star.y = 0;
                star.x = Math.random() * this.canvas.width;
            }
        });
    }

    /**
     * Render game
     */
    render() {
        if (!this.ctx) return;

        // Clear canvas
        this.ctx.fillStyle = this.colors ? this.colors.background : '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw stars
        this.ctx.fillStyle = this.colors ? this.colors.star : '#fff';
        this.stars.forEach(star => {
            this.ctx.fillRect(star.x, star.y, star.size, star.size);
        });

        // Draw player ship
        this.drawPlayerShip();

        // Draw enemies
        this.enemies.forEach(enemy => {
            this.drawEnemy(enemy);
        });

        // Draw particles
        this.ctx.fillStyle = this.colors ? this.colors.primary : '#39ff14';
        this.particles.forEach(p => {
            this.ctx.globalAlpha = p.life / 500;
            this.ctx.fillRect(p.x, p.y, 2, 2);
        });
        this.ctx.globalAlpha = 1;
    }

    /**
     * Draw player ship
     */
    drawPlayerShip() {
        const x = this.canvas.width / 2;
        const y = this.canvas.height - 40;

        const shipColor = this.colors ? this.colors.primary : '#39ff14';
        this.ctx.fillStyle = shipColor;
        this.ctx.strokeStyle = shipColor;
        this.ctx.lineWidth = 2;

        // Simple triangle ship
        this.ctx.beginPath();
        this.ctx.moveTo(x, y - 15);
        this.ctx.lineTo(x - 10, y + 5);
        this.ctx.lineTo(x + 10, y + 5);
        this.ctx.closePath();
        this.ctx.stroke();
    }

    /**
     * Draw enemy ship
     */
    drawEnemy(enemy) {
        const color = enemy.isUrgent
            ? (this.colors ? this.colors.danger : '#ff0055')
            : (this.colors ? this.colors.secondary : '#00d9ff');

        this.ctx.fillStyle = color;
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 2;

        // Simple inverted triangle
        this.ctx.beginPath();
        this.ctx.moveTo(enemy.x, enemy.y + 15);
        this.ctx.lineTo(enemy.x - 10, enemy.y - 5);
        this.ctx.lineTo(enemy.x + 10, enemy.y - 5);
        this.ctx.closePath();
        this.ctx.stroke();

        // Draw equation
        this.ctx.font = '16px "Press Start 2P"';
        this.ctx.fillStyle = color;
        this.ctx.textAlign = 'center';
        this.ctx.fillText(enemy.equation, enemy.x, enemy.y - 15);
    }

    /**
     * Spawn new enemy
     */
    spawnEnemy() {
        if (this.problems.length === 0) return;

        const problem = this.problems.shift();
        const enemy = {
            x: Math.random() * (this.canvas.width - 100) + 50,
            y: 20,
            speed: 0.5 + (this.score / 100), // Speed increases with score
            equation: problem.equation,
            answer: problem.answer,
            id: problem.id,
            isUrgent: false
        };

        this.enemies.push(enemy);
    }

    /**
     * Handle answer submission
     */
    handleAnswer(userAnswer) {
        if (!this.isActive) return;

        // Find matching enemy (prioritize lowest/most urgent)
        const matchingEnemies = this.enemies.filter(e => e.answer === userAnswer);

        if (matchingEnemies.length === 0) {
            // Wrong answer
            this.handleWrongAnswer();
            return;
        }

        // Get lowest enemy
        matchingEnemies.sort((a, b) => b.y - a.y);
        const target = matchingEnemies[0];

        // Remove enemy
        const index = this.enemies.indexOf(target);
        if (index > -1) {
            this.enemies.splice(index, 1);
        }

        // Correct answer effects
        this.handleCorrectAnswer(target);

        // Clear input
        this.inputHandler.clear();
        this.inputHandler.focus();
    }

    /**
     * Handle correct answer
     */
    handleCorrectAnswer(enemy) {
        this.score += 10;

        // Create laser effect
        this.createLaser(enemy.x, enemy.y);

        // Create explosion particles
        this.createExplosion(enemy.x, enemy.y);

        // Update Elo
        this.currentElo = storageManager.updateElo(5);

        // Play sound
        this.playSound('laser');

        this.updateDisplay();
    }

    /**
     * Handle wrong answer
     */
    handleWrongAnswer() {
        // Just clear input, no penalty
        this.inputHandler.clear();
        this.playSound('wrong');
    }

    /**
     * Create laser animation
     */
    createLaser(targetX, targetY) {
        if (!this.ctx) return;

        const startX = this.canvas.width / 2;
        const startY = this.canvas.height - 40;

        // Draw laser beam
        this.ctx.strokeStyle = this.colors ? this.colors.primary : '#39ff14';
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.moveTo(startX, startY);
        this.ctx.lineTo(targetX, targetY);
        this.ctx.stroke();

        // Beam fades quickly (handled by game loop)
    }

    /**
     * Create explosion particles
     */
    createExplosion(x, y) {
        for (let i = 0; i < 10; i++) {
            this.particles.push({
                x,
                y,
                vx: (Math.random() - 0.5) * 3,
                vy: (Math.random() - 0.5) * 3,
                life: 500
            });
        }
    }

    /**
     * Lose a life
     */
    loseLife() {
        this.lives--;

        // Update display
        this.updateDisplay();

        // Shake screen
        const screen = document.getElementById('screen-space-defense');
        if (screen) {
            screen.classList.add('shake');
            setTimeout(() => screen.classList.remove('shake'), 300);
        }

        // Play sound
        this.playSound('explosion');

        // Check game over
        if (this.lives <= 0) {
            this.end();
        }
    }

    /**
     * Update displays
     */
    updateDisplay() {
        if (this.livesDisplay) {
            this.livesDisplay.textContent = '❤️'.repeat(Math.max(0, this.lives));
        }

        if (this.scoreDisplay) {
            this.scoreDisplay.textContent = this.score;
        }
    }

    /**
     * Play sound effect
     */
    playSound(soundName) {
        if (window.audioManager) {
            window.audioManager.play(soundName);
        }
    }

    /**
     * End the game
     */
    end() {
        this.isActive = false;
        window.gameActive = false;

        // Stop animation loop
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }

        // Disable input
        this.inputHandler.disable();

        // Calculate stats
        const timeElapsed = Math.floor((Date.now() - this.gameStartTime) / 1000);
        const enemiesDestroyed = Math.floor(this.score / 10);

        // Check for high score
        const isNewHighScore = storageManager.updateHighScore('space_defense', this.score);

        // Update streak
        storageManager.updateStreak();

        // Show results
        this.showResults(this.score, enemiesDestroyed, timeElapsed, this.currentElo, isNewHighScore);

        // Reset UI
        if (this.startButton) this.startButton.style.display = 'block';
    }

    /**
     * Show results screen
     */
    showResults(score, enemiesDestroyed, timeElapsed, newElo, isNewHighScore) {
        document.getElementById('result-score').textContent = score;
        document.getElementById('result-accuracy').textContent = enemiesDestroyed + ' destroyed';
        document.getElementById('result-rate').textContent = timeElapsed + 's survived';
        document.getElementById('result-elo').textContent = newElo;

        const highScoreBanner = document.getElementById('high-score-banner');
        if (highScoreBanner) {
            highScoreBanner.style.display = isNewHighScore ? 'block' : 'none';
        }

        screenManager.showScreen('screen-results');
    }
}

// Initialize when DOM is ready
let spaceDefense;
document.addEventListener('DOMContentLoaded', () => {
    spaceDefense = new SpaceDefense();
});
