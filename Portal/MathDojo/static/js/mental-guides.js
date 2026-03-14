/**
 * MentalGuides - Contextual mental arithmetic hints.
 * Maps problem tags to concise calculation tricks and manages the hint UI.
 */
class MentalGuides {
    static GUIDES = [
        // ── Addition ──────────────────────────────────────────────
        {
            id: 'add-round',
            title: 'ADD: ROUND & ADJUST',
            body: '<strong>Round</strong> one number to the nearest 10 or 100, add, then adjust.\n' +
                  'E.g. 298 + 45 → 300 + 45 − 2 = <strong>343</strong>\n' +
                  '47 + 29 → 47 + 30 − 1 = <strong>76</strong>',
            match(tags) {
                if (!tags.includes('op:add') || !tags.includes('near:round')) return 0;
                return 20; // High priority — rounding is the most impactful trick
            }
        },
        {
            id: 'add-make10',
            title: 'MAKE 10',
            body: 'Find the <strong>complement to 10</strong>, then add the rest.\n' +
                  '7 + 5 → 7 + <strong>3</strong> + 2 = <strong>12</strong>\n' +
                  '8 + 6 → 8 + <strong>2</strong> + 4 = <strong>14</strong>',
            match(tags) {
                if (!tags.includes('op:add') || !tags.includes('scale:1x1')) return 0;
                return 10;
            }
        },
        {
            id: 'add-2d1d-carry',
            title: 'ADD 2+1 DIGIT',
            body: '<strong>Add 10</strong>, then subtract the difference.\n' +
                  '47 + 8 → 47 + 10 − 2 = <strong>55</strong>\n' +
                  'Or bridge through the ten: 47 + 3 + 5 = <strong>55</strong>',
            match(tags) {
                if (!tags.includes('op:add')) return 0;
                if (!tags.includes('scale:1x2') && !tags.includes('scale:2x1')) return 0;
                if (tags.includes('carry:once') || tags.includes('carry:multi')) return 8;
                return 5;
            }
        },
        {
            id: 'add-2d-nocarry',
            title: 'ADD TENS, THEN ONES',
            body: 'Add the <strong>tens</strong> first, then the <strong>ones</strong>.\n' +
                  '34 + 25 → 30 + 20 = 50, then 4 + 5 = 9 → <strong>59</strong>\n' +
                  'No carrying needed — just combine place values.',
            match(tags) {
                if (!tags.includes('op:add') || !tags.includes('scale:2x2')) return 0;
                if (tags.includes('carry:none')) return 8;
                return 0;
            }
        },
        {
            id: 'add-2d-carry',
            title: 'ADD 2-DIGIT (CARRY)',
            body: '<strong>Round up</strong> one number, add, then subtract.\n' +
                  '47 + 38 → <strong>50</strong> + 38 − 3 = <strong>85</strong>\n' +
                  'Or: add tens (40+30=70), add ones (7+8=15), combine → <strong>85</strong>',
            match(tags) {
                if (!tags.includes('op:add') || !tags.includes('scale:2x2')) return 0;
                if (tags.includes('carry:once') || tags.includes('carry:multi')) return 8;
                return 0;
            }
        },
        {
            id: 'add-3d',
            title: 'ADD LARGE NUMBERS',
            body: 'Add in <strong>parts</strong>, largest place first.\n' +
                  '347 + 86 → 347 + 80 + 6 = 427 + 6 = <strong>433</strong>\n' +
                  'Or round: 347 + 86 → 350 + 86 − 3 = <strong>433</strong>',
            match(tags) {
                if (!tags.includes('op:add')) return 0;
                const has3 = tags.some(t => t.startsWith('scale:') && t.includes('3'));
                if (has3) return 6;
                if (tags.includes('scale:big')) return 6;
                return 0;
            }
        },

        // ── Subtraction ───────────────────────────────────────────
        {
            id: 'sub-round',
            title: 'SUBTRACT: ROUND & ADJUST',
            body: '<strong>Round</strong> the number being subtracted, then adjust.\n' +
                  '83 − 19 → 83 − <strong>20</strong> + 1 = <strong>64</strong>\n' +
                  '145 − 98 → 145 − <strong>100</strong> + 2 = <strong>47</strong>',
            match(tags) {
                if (!tags.includes('op:sub') || !tags.includes('near:round')) return 0;
                return 20;
            }
        },
        {
            id: 'sub-countup',
            title: 'COUNT UP',
            body: 'Start at the <strong>smaller number</strong> and count up.\n' +
                  '13 − 7 → start at 7, count to 13: <strong>6</strong>\n' +
                  'Think: 7 + ? = 13',
            match(tags) {
                if (!tags.includes('op:sub') || !tags.includes('scale:1x1')) return 0;
                return 10;
            }
        },
        {
            id: 'sub-2d',
            title: 'SUBTRACT IN PARTS',
            body: 'Subtract the <strong>tens first</strong>, then the ones.\n' +
                  '83 − 47 → 83 − 40 = 43, then 43 − 7 = <strong>36</strong>\n' +
                  'Or count up: 47 + 3 = 50, + 33 = 83 → <strong>36</strong>',
            match(tags) {
                if (!tags.includes('op:sub') || !tags.includes('scale:2x2')) return 0;
                return 7;
            }
        },
        {
            id: 'sub-borrow-zero',
            title: 'BORROW ACROSS ZERO',
            body: 'Use the <strong>complement method</strong>: subtract each digit from 9, last from 10.\n' +
                  '400 − 267 → 9−2=7, 9−6=3, 10−7=3 → <strong>133</strong>\n' +
                  'Or: 400 − 267 → 400 − 270 + 3 = <strong>133</strong>',
            match(tags) {
                if (!tags.includes('op:sub') || !tags.includes('borrow:across-zero')) return 0;
                return 12;
            }
        },
        {
            id: 'sub-3d',
            title: 'SUBTRACT LARGE NUMBERS',
            body: 'Subtract in <strong>parts</strong> or use <strong>counting up</strong>.\n' +
                  '500 − 173 → complement: 9−1=8, 9−7=2, 10−3=7 → wait, that\'s from 1000.\n' +
                  'Better: 173 + ? = 500 → 173 + 27 = 200, + 300 = 500 → <strong>327</strong>',
            match(tags) {
                if (!tags.includes('op:sub')) return 0;
                const has3 = tags.some(t => t.startsWith('scale:') && t.includes('3'));
                if (has3) return 6;
                if (tags.includes('scale:big')) return 6;
                return 0;
            }
        },

        // ── Multiplication ────────────────────────────────────────
        {
            id: 'mul-round',
            title: 'MULTIPLY: ROUND & ADJUST',
            body: '<strong>Round</strong> one factor to 10 or 20, multiply, then adjust.\n' +
                  '19 × 6 → <strong>20</strong> × 6 − 6 = 120 − 6 = <strong>114</strong>\n' +
                  '21 × 8 → <strong>20</strong> × 8 + 8 = 160 + 8 = <strong>168</strong>',
            match(tags) {
                if (!tags.includes('op:mul') || !tags.includes('near:round')) return 0;
                return 20;
            }
        },
        {
            id: 'mul-trap',
            title: 'TRAP FACTS',
            body: '<strong>Mnemonics</strong> for the trickiest times tables:\n' +
                  '5, 6, 7, 8 → <strong>56 = 7 × 8</strong>\n' +
                  '6 × 7 = <strong>42</strong> | 6 × 9 = <strong>54</strong> | 8 × 9 = <strong>72</strong>\n' +
                  'Drill these until automatic — they trip everyone up.',
            match(tags) {
                if (tags.some(t => t.startsWith('trap:'))) return 15;
                return 0;
            }
        },
        {
            id: 'mul-easy',
            title: 'EASY TABLES (2-5)',
            body: '<strong>Doubling chains</strong> make these fast:\n' +
                  '×2 = double | ×4 = double twice | ×3 = double + once\n' +
                  '×5 = half of ×10 (e.g. 5 × 7 = 70 ÷ 2 = <strong>35</strong>)',
            match(tags) {
                if (!tags.includes('op:mul') || !tags.includes('table:easy')) return 0;
                return 8;
            }
        },
        {
            id: 'mul-mid',
            title: 'TABLES 6-7',
            body: '<strong>Break it down</strong> using 5× as anchor:\n' +
                  '6× = 5× + 1× → 6 × 8 = 40 + 8 = <strong>48</strong>\n' +
                  '7× = 5× + 2× → 7 × 9 = 45 + 18 = <strong>63</strong>',
            match(tags) {
                if (!tags.includes('op:mul') || !tags.includes('table:mid')) return 0;
                return 8;
            }
        },
        {
            id: 'mul-hard',
            title: 'TABLES 8-9',
            body: '<strong>Use 10× as anchor:</strong>\n' +
                  '9× = 10× − 1× → 9 × 7 = 70 − 7 = <strong>63</strong>\n' +
                  '8× = 10× − 2× → 8 × 6 = 60 − 12 = <strong>48</strong>\n' +
                  'Or 8× = double, double, double.',
            match(tags) {
                if (!tags.includes('op:mul') || !tags.includes('table:hard')) return 0;
                return 8;
            }
        },
        {
            id: 'mul-2d1d',
            title: 'MULTIPLY 2d × 1d',
            body: '<strong>Distribute</strong>: split the 2-digit number.\n' +
                  '23 × 7 → (20 × 7) + (3 × 7) = 140 + 21 = <strong>161</strong>\n' +
                  '45 × 6 → (40 × 6) + (5 × 6) = 240 + 30 = <strong>270</strong>',
            match(tags) {
                if (!tags.includes('op:mul')) return 0;
                if (tags.includes('scale:1x2') || tags.includes('scale:2x1')) return 7;
                return 0;
            }
        },
        {
            id: 'mul-2d2d',
            title: 'MULTIPLY 2d × 2d',
            body: '<strong>Round one factor</strong> to the nearest 10:\n' +
                  '23 × 17 → 23 × <strong>20</strong> − 23 × 3 = 460 − 69 = <strong>391</strong>\n' +
                  'Or distribute: (20+3)(10+7) = 200+140+30+21 = <strong>391</strong>',
            match(tags) {
                if (!tags.includes('op:mul') || !tags.includes('scale:2x2')) return 0;
                return 7;
            }
        },

        // ── Division ──────────────────────────────────────────────
        {
            id: 'div-basic',
            title: 'REVERSE THE TIMES TABLE',
            body: 'Think: <strong>what × divisor = dividend?</strong>\n' +
                  '56 ÷ 8 → 8 × ? = 56 → <strong>7</strong>\n' +
                  'If stuck, try multiples: 8, 16, 24, 32, 40, 48, 56 ✓',
            match(tags) {
                if (!tags.includes('op:div')) return 0;
                if (tags.includes('div:large')) return 0; // Large division has its own guide
                return 8;
            }
        },
        {
            id: 'div-large',
            title: 'SPLIT THE DIVIDEND',
            body: 'Break into <strong>friendly parts</strong> divisible by the divisor.\n' +
                  '144 ÷ 12 → (120 + 24) ÷ 12 = 10 + 2 = <strong>12</strong>\n' +
                  '156 ÷ 12 → (120 + 36) ÷ 12 = 10 + 3 = <strong>13</strong>',
            match(tags) {
                if (!tags.includes('op:div') || !tags.includes('div:large')) return 0;
                return 10;
            }
        },

        // ── Multi-operation ───────────────────────────────────────
        {
            id: 'mixed-ops',
            title: 'ORDER OF OPERATIONS',
            body: '<strong>PEMDAS</strong>: Parentheses → Exponents → Multiply/Divide → Add/Subtract\n' +
                  'Do × and ÷ <strong>before</strong> + and −.\n' +
                  'Same rank? Work <strong>left to right</strong>.\n' +
                  '3 + 4 × 5 = 3 + 20 = <strong>23</strong> (not 35)',
            match(tags) {
                const opCount = tags.filter(t => t.startsWith('op:')).length;
                if (opCount >= 2) return 5;
                return 0;
            }
        }
    ];

    // Current guide per screen prefix
    static _current = {};

    /**
     * Find the best matching guide for the given tags.
     * Returns the guide object or null.
     */
    static getGuide(tags) {
        if (!tags || tags.length === 0) return null;

        let best = null;
        let bestScore = 0;

        for (const guide of MentalGuides.GUIDES) {
            const score = guide.match(tags);
            if (score > bestScore) {
                bestScore = score;
                best = guide;
            }
        }

        return best;
    }

    /**
     * Update the hint button and store guide content for a screen.
     * @param {string[]} tags - Current problem's tags
     * @param {string} prefix - 'drill' or 'tt'
     */
    static update(tags, prefix) {
        const btn = document.getElementById(`${prefix}-hint-btn`);
        const panel = document.getElementById(`${prefix}-hint-panel`);
        if (!btn) return;

        const guide = MentalGuides.getGuide(tags);
        MentalGuides._current[prefix] = guide;

        if (guide) {
            btn.style.display = 'block';
        } else {
            btn.style.display = 'none';
        }

        // Always hide panel when loading a new problem
        if (panel) {
            panel.style.display = 'none';
        }
        if (btn) {
            btn.classList.remove('active');
        }
    }

    /**
     * Toggle the hint panel visibility.
     * @param {string} prefix - 'drill' or 'tt'
     */
    static toggle(prefix) {
        const btn = document.getElementById(`${prefix}-hint-btn`);
        const panel = document.getElementById(`${prefix}-hint-panel`);
        const guide = MentalGuides._current[prefix];
        if (!panel || !guide) return;

        const isVisible = panel.style.display !== 'none';

        if (isVisible) {
            panel.style.display = 'none';
            if (btn) btn.classList.remove('active');
        } else {
            const title = document.getElementById(`${prefix}-hint-title`);
            const body = document.getElementById(`${prefix}-hint-body`);
            if (title) title.textContent = guide.title;
            if (body) body.innerHTML = guide.body.replace(/\n/g, '<br>');
            panel.style.display = 'block';
            if (btn) btn.classList.add('active');
        }
    }

    /**
     * Hide the hint panel (called on answer submit).
     * @param {string} prefix - 'drill' or 'tt'
     */
    static hide(prefix) {
        const btn = document.getElementById(`${prefix}-hint-btn`);
        const panel = document.getElementById(`${prefix}-hint-panel`);
        if (panel) panel.style.display = 'none';
        if (btn) btn.classList.remove('active');
    }

    /**
     * Initialize click listeners for all hint buttons.
     */
    static init() {
        ['drill', 'tt'].forEach(prefix => {
            const btn = document.getElementById(`${prefix}-hint-btn`);
            if (btn) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    MentalGuides.toggle(prefix);
                });
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    MentalGuides.init();
});
