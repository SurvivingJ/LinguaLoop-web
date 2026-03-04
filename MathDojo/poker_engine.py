"""
Poker Math Problem Generator
Generates training problems for 5 poker math modes.
Pure Python — no external poker libraries required.
"""
import random
import uuid

# ── Card Constants ──────────────────────────────────────

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['s', 'h', 'd', 'c']
RANK_INDEX = {r: i for i, r in enumerate(RANKS)}
SUIT_SYMBOLS = {'s': '\u2660', 'h': '\u2665', 'd': '\u2666', 'c': '\u2663'}

FULL_DECK = [r + s for r in RANKS for s in SUITS]


def card_display(card_str):
    """Convert 'As' to 'A\u2660' for display."""
    rank = card_str[0]
    suit = card_str[1]
    display_rank = '10' if rank == 'T' else rank
    return f"{display_rank}{SUIT_SYMBOLS[suit]}"


def deal_cards(n, exclude=None):
    """Deal n cards from a deck excluding specified cards."""
    available = [c for c in FULL_DECK if c not in (exclude or [])]
    return random.sample(available, n)


# ── Combo Counting Helpers ──────────────────────────────

def count_pair_combos(rank, removed_cards):
    """Count remaining combos of a pocket pair (e.g. AA) given removed cards."""
    available = [s for s in SUITS if f"{rank}{s}" not in removed_cards]
    n = len(available)
    return n * (n - 1) // 2


def count_unpaired_combos(rank1, rank2, suited, removed_cards):
    """Count remaining combos of an unpaired hand (e.g. AKs or AKo)."""
    avail_r1 = [s for s in SUITS if f"{rank1}{s}" not in removed_cards]
    avail_r2 = [s for s in SUITS if f"{rank2}{s}" not in removed_cards]
    if suited:
        return sum(1 for s in SUITS if s in avail_r1 and s in avail_r2)
    else:
        return sum(1 for s1 in avail_r1 for s2 in avail_r2 if s1 != s2)


# ── Equity via Rule of 2/4 ─────────────────────────────

def rule_of_2_4(outs, streets_remaining):
    """
    Approximate equity from outs.
    streets_remaining=2 (flop, seeing turn+river): outs*4 - max(0, outs-8)
    streets_remaining=1 (turn, seeing river): outs*2.2
    """
    if streets_remaining == 2:
        return round(outs * 4 - max(0, outs - 8))
    else:
        return round(outs * 2.2)


# ── Pre-computed Range Tables ───────────────────────────

RANGE_SPOTS = {
    # ── EASY (tight ranges, 10-15% of hands) ──
    'utg_open_6max_easy': {
        'description': 'UTG Open Range (6-max)',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT',
            'AKs', 'AKo', 'AQs', 'AJs', 'KQs',
        ],
    },
    'ep_open_easy': {
        'description': 'Early Position Open (9-max)',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'KQs',
        ],
    },
    'utg_3bet_easy': {
        'description': 'UTG 3-Bet Range vs CO Open',
        'range': [
            'AA', 'KK', 'QQ', 'AKs', 'AKo',
        ],
    },

    # ── NORMAL (standard ranges, 20-35% of hands) ──
    'co_open_normal': {
        'description': 'Cutoff Open Range (6-max)',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'AJo', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KQo', 'KJs', 'KJo', 'KTs', 'K9s',
            'QJs', 'QJo', 'QTs', 'Q9s',
            'JTs', 'J9s',
            'T9s', 'T8s',
            '98s', '87s', '76s', '65s', '54s',
        ],
    },
    'btn_open_normal': {
        'description': 'Button Open Range (6-max)',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'AJo', 'ATs', 'ATo', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KQo', 'KJs', 'KJo', 'KTs', 'KTo', 'K9s', 'K8s', 'K7s',
            'QJs', 'QJo', 'QTs', 'QTo', 'Q9s', 'Q8s',
            'JTs', 'JTo', 'J9s', 'J8s',
            'T9s', 'T9o', 'T8s',
            '98s', '98o', '97s',
            '87s', '87o', '86s',
            '76s', '75s', '65s', '64s', '54s', '53s', '43s',
        ],
    },
    'bb_defend_vs_btn_normal': {
        'description': 'BB Defend vs Button Open',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'AJo', 'ATs', 'ATo', 'A9s', 'A9o', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KQo', 'KJs', 'KJo', 'KTs', 'KTo', 'K9s', 'K9o', 'K8s', 'K7s', 'K6s', 'K5s',
            'QJs', 'QJo', 'QTs', 'QTo', 'Q9s', 'Q8s', 'Q7s',
            'JTs', 'JTo', 'J9s', 'J8s', 'J7s',
            'T9s', 'T9o', 'T8s', 'T7s',
            '98s', '98o', '97s', '96s',
            '87s', '87o', '86s', '85s',
            '76s', '76o', '75s',
            '65s', '65o', '64s',
            '54s', '53s', '43s',
        ],
    },

    # ── HARD (wide/mixed ranges, 40%+ or marginal) ──
    'sb_open_hard': {
        'description': 'Small Blind Open Range (6-max)',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'AJo', 'ATs', 'ATo', 'A9s', 'A9o', 'A8s', 'A8o', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KQo', 'KJs', 'KJo', 'KTs', 'KTo', 'K9s', 'K9o', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s',
            'QJs', 'QJo', 'QTs', 'QTo', 'Q9s', 'Q9o', 'Q8s', 'Q7s', 'Q6s',
            'JTs', 'JTo', 'J9s', 'J9o', 'J8s', 'J7s',
            'T9s', 'T9o', 'T8s', 'T8o', 'T7s',
            '98s', '98o', '97s', '96s',
            '87s', '87o', '86s', '85s',
            '76s', '76o', '75s',
            '65s', '65o', '64s',
            '54s', '54o', '53s',
            '43s', '43o',
        ],
    },
    'btn_3bet_vs_co_hard': {
        'description': 'Button 3-Bet vs Cutoff Open',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'ATs', 'A5s', 'A4s',
            'KQs', 'KJs',
            'QJs',
            'JTs',
            'T9s',
            '98s', '87s', '76s',
        ],
    },
    'bb_3bet_vs_btn_hard': {
        'description': 'BB 3-Bet vs Button Open',
        'range': [
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
            'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'ATs', 'A9s', 'A5s', 'A4s', 'A3s',
            'KQs', 'KJs', 'KTs',
            'QJs', 'QTs',
            'JTs', 'J9s',
            'T9s',
            '98s', '87s', '76s', '65s',
        ],
    },
}

# Group spots by difficulty
SPOTS_BY_DIFFICULTY = {
    'easy': [k for k in RANGE_SPOTS if k.endswith('_easy')],
    'normal': [k for k in RANGE_SPOTS if k.endswith('_normal')],
    'hard': [k for k in RANGE_SPOTS if k.endswith('_hard')],
}


# ── Equity Scenario Templates ──────────────────────────

EQUITY_SCENARIOS = [
    # (description, outs, template_builder_name)
    ('flush_draw', 9, '_build_flush_draw'),
    ('open_ended_straight_draw', 8, '_build_oesd'),
    ('gutshot', 4, '_build_gutshot'),
    ('overcards', 6, '_build_overcards'),
    ('combo_draw', 15, '_build_combo_draw'),
    ('two_pair_draw', 4, '_build_two_pair_draw'),
]


# ── Main Generator Class ───────────────────────────────

class PokerProblemGenerator:
    """Generates poker math training problems across 5 modes."""

    CATEGORY_MAP = {
        'pot_odds': ['pot_odds'],
        'auto_profit': ['auto_profit'],
        'combinatorics': ['combinatorics'],
        'equity': ['equity_intuition'],
        'range': ['range_painter'],
    }

    METHOD_MAP = {
        'pot_odds': '_pot_odds',
        'auto_profit': '_auto_profit',
        'combinatorics': '_combinatorics',
        'equity_intuition': '_equity_intuition',
        'range_painter': '_range_painter',
    }

    # Scenario names for targeting equity sub-types
    EQUITY_SCENARIO_NAMES = [s[0] for s in EQUITY_SCENARIOS]

    TYPE_TO_CATEGORY = {
        'pot_odds': 'pot_odds',
        'auto_profit': 'auto_profit',
        'combinatorics': 'combinatorics',
        'flush_draw': 'equity',
        'open_ended_straight_draw': 'equity',
        'gutshot': 'equity',
        'overcards': 'equity',
        'combo_draw': 'equity',
        'two_pair_draw': 'equity',
        'range_painter': 'range',
    }

    # ── Mode 1: Pot Odds ────────────────────────────

    @staticmethod
    def _pot_odds(difficulty):
        """Pot odds: what equity % do you need to call?"""
        if difficulty == 'easy':
            pot = random.choice([50, 100, 200, 400])
            bet = random.choice([25, 50, 100])
        elif difficulty == 'hard':
            pot = random.randint(50, 500)
            bet = random.randint(20, 300)
        else:
            pot = random.choice([60, 80, 100, 120, 150, 200, 250])
            bet = random.choice([30, 40, 50, 60, 75, 100, 125])

        # Equity needed = call amount / (pot + bet + call)
        # Call amount = bet, new pot = pot + bet + bet
        equity_needed = round(bet / (pot + 2 * bet) * 100, 1)
        new_pot = pot + 2 * bet

        equation = f"Pot: ${pot}. Villain bets ${bet}. What % equity to call?"
        explanation = (
            f"Call = ${bet}\n"
            f"New pot = ${pot} + ${bet} + ${bet} = ${new_pot}\n"
            f"Equity needed = {bet}/{new_pot} = {equity_needed}%"
        )

        return equation, equity_needed, 1, 'pot_odds', {'explanation': explanation}

    # ── Mode 2: Auto-Profit (Bluff Break-Even) ─────

    @staticmethod
    def _auto_profit(difficulty):
        """Break-even bluff %: how often must villain fold?"""
        if difficulty == 'easy':
            pot = random.choice([50, 100, 200])
            bet = random.choice([50, 100, 200])
        elif difficulty == 'hard':
            pot = random.randint(50, 500)
            bet = random.randint(20, 400)
        else:
            pot = random.choice([60, 80, 100, 150, 200])
            bet = random.choice([40, 50, 75, 100, 150])

        break_even = round(bet / (pot + bet) * 100, 1)
        total = pot + bet

        equation = f"Pot: ${pot}. You bet ${bet}. Fold % needed to auto-profit?"
        explanation = (
            f"Risk = ${bet}\n"
            f"Reward if they fold = ${pot}\n"
            f"Break-even = {bet}/({pot}+{bet}) = {bet}/{total} = {break_even}%"
        )

        return equation, break_even, 1, 'auto_profit', {'explanation': explanation}

    # ── Mode 3: Combinatorics ──────────────────────

    @staticmethod
    def _combinatorics(difficulty):
        """Count remaining combos of a target hand given blockers."""
        # Pick a target hand type
        if difficulty == 'easy':
            # Pairs only — simpler blocker math
            target_rank = random.choice(RANKS[6:])  # 8 through A
            target_label = target_rank + target_rank  # e.g. "AA"
            is_pair = True
        elif difficulty == 'hard':
            # Mix of pairs, suited, and offsuit
            choice = random.choice(['pair', 'suited', 'offsuit'])
            if choice == 'pair':
                target_rank = random.choice(RANKS[4:])
                target_label = target_rank + target_rank
                is_pair = True
            else:
                r1, r2 = random.sample(RANKS[6:], 2)
                if RANK_INDEX[r1] < RANK_INDEX[r2]:
                    r1, r2 = r2, r1
                is_pair = False
                if choice == 'suited':
                    target_label = r1 + r2 + 's'
                else:
                    target_label = r1 + r2 + 'o'
                target_rank = (r1, r2)
        else:
            # Normal: pairs and some suited hands
            if random.random() < 0.6:
                target_rank = random.choice(RANKS[5:])
                target_label = target_rank + target_rank
                is_pair = True
            else:
                r1, r2 = random.sample(RANKS[7:], 2)
                if RANK_INDEX[r1] < RANK_INDEX[r2]:
                    r1, r2 = r2, r1
                target_label = r1 + r2 + 's'
                target_rank = (r1, r2)
                is_pair = False

        # Deal hero hand and board (ensuring at least 1 blocker for interest)
        num_board = random.choice([3, 4]) if difficulty != 'easy' else 3
        hero = deal_cards(2)
        board = deal_cards(num_board, exclude=hero)
        removed = hero + board

        # Calculate answer
        if is_pair:
            answer = count_pair_combos(target_rank, removed)
        else:
            r1, r2 = target_rank
            suited = target_label.endswith('s')
            answer = count_unpaired_combos(r1, r2, suited, removed)

        hero_display = ' '.join(card_display(c) for c in hero)
        board_display = ' '.join(card_display(c) for c in board)
        equation = f"Hero: {hero_display} | Board: {board_display} | Combos of {target_label}?"

        # Build explanation
        if is_pair:
            avail_suits = [s for s in SUITS if f"{target_rank}{s}" not in removed]
            blocked_cards = [card_display(f"{target_rank}{s}") for s in SUITS if f"{target_rank}{s}" in removed]
            n = len(avail_suits)
            blocked_str = ', '.join(blocked_cards) if blocked_cards else 'none'
            explanation = (
                f"Target: {target_label} (pocket pair)\n"
                f"4 suits total. Blocked by: {blocked_str}\n"
                f"Available suits: {n}\n"
                f"C({n},2) = {n}x{max(n-1,0)}/2 = {answer} combos"
            )
        else:
            r1, r2 = target_rank
            suited = target_label.endswith('s')
            avail_r1 = [s for s in SUITS if f"{r1}{s}" not in removed]
            avail_r2 = [s for s in SUITS if f"{r2}{s}" not in removed]
            if suited:
                explanation = (
                    f"Target: {target_label} (suited)\n"
                    f"{r1} available suits: {len(avail_r1)}, {r2} available suits: {len(avail_r2)}\n"
                    f"Count matching suits = {answer} combos"
                )
            else:
                explanation = (
                    f"Target: {target_label} (offsuit)\n"
                    f"{r1} available suits: {len(avail_r1)}, {r2} available suits: {len(avail_r2)}\n"
                    f"Cross product minus suited = {len(avail_r1)}x{len(avail_r2)} - suited = {answer} combos"
                )

        return equation, answer, 0, 'combinatorics', {
            'hero': hero,
            'board': board,
            'target': target_label,
            'explanation': explanation,
        }

    # ── Mode 4: Equity Intuition ───────────────────

    @staticmethod
    def _equity_intuition(difficulty, scenario_type=None):
        """Estimate equity using Rule of 2/4 with scenario templates."""
        if difficulty == 'easy':
            # Simple draws only
            scenarios = [s for s in EQUITY_SCENARIOS if s[1] <= 9]
        elif difficulty == 'hard':
            scenarios = EQUITY_SCENARIOS  # all scenarios including combo draws
        else:
            scenarios = [s for s in EQUITY_SCENARIOS if s[1] <= 9 or s[0] == 'combo_draw']

        # If targeting a specific scenario, filter to that type
        if scenario_type is not None:
            targeted = [s for s in scenarios if s[0] == scenario_type]
            if targeted:
                scenarios = targeted

        name, outs, builder = random.choice(scenarios)
        builder_fn = getattr(PokerProblemGenerator, builder)

        streets = random.choice([1, 2]) if difficulty != 'easy' else 2
        hero, villain, board = builder_fn()
        equity = rule_of_2_4(outs, streets)

        street_label = 'Flop' if streets == 2 else 'Turn'
        hero_display = ' '.join(card_display(c) for c in hero)
        villain_display = ' '.join(card_display(c) for c in villain)
        board_display = ' '.join(card_display(c) for c in board[:3] if streets == 2) if streets == 2 else ' '.join(card_display(c) for c in board)

        equation = f"{street_label} | Hero: {hero_display} vs {villain_display}"

        draw_names = {
            'flush_draw': 'Flush draw',
            'open_ended_straight_draw': 'Open-ended straight draw',
            'gutshot': 'Gutshot straight draw',
            'overcards': 'Two overcards',
            'combo_draw': 'Combo draw (flush + straight)',
            'two_pair_draw': 'Two pair draw',
        }
        draw_label = draw_names.get(name, name)
        cards_to_come = '2 cards to come' if streets == 2 else '1 card to come'
        if streets == 2:
            rule_str = f"Rule of 4: {outs} x 4 - max(0, {outs}-8) = {equity}%"
        else:
            rule_str = f"Rule of 2: {outs} x 2.2 = {equity}%"

        explanation = (
            f"Draw: {draw_label} ({outs} outs)\n"
            f"Street: {street_label} ({cards_to_come})\n"
            f"{rule_str}"
        )

        return equation, equity, 5, 'equity', {
            'hero': hero,
            'villain': villain,
            'board': board[:3] if streets == 2 else board,
            'streets': streets,
            'outs': outs,
            'explanation': explanation,
            'scenario_type': name,
        }

    # ── Equity Scenario Builders ───────────────────

    @staticmethod
    def _build_flush_draw():
        """Hero has flush draw vs made hand. 9 outs."""
        suit = random.choice(SUITS)
        other_suits = [s for s in SUITS if s != suit]

        # Hero: two cards of the suit (not making a pair with board)
        hero_ranks = random.sample(RANKS[5:], 2)  # mid-high cards
        hero = [f"{hero_ranks[0]}{suit}", f"{hero_ranks[1]}{suit}"]

        # Board: 2 of the same suit + 1 off-suit (flop)
        board_flush_ranks = random.sample([r for r in RANKS if r not in hero_ranks], 2)
        off_rank = random.choice([r for r in RANKS if r not in hero_ranks and r not in board_flush_ranks])
        board = [
            f"{board_flush_ranks[0]}{suit}",
            f"{board_flush_ranks[1]}{suit}",
            f"{off_rank}{random.choice(other_suits)}",
        ]

        # Villain: overpair or top pair (non-flush suit)
        v_ranks = random.sample([r for r in RANKS[8:] if r not in hero_ranks and r not in board_flush_ranks and r != off_rank], 2)
        villain = [f"{v_ranks[0]}{random.choice(other_suits)}", f"{v_ranks[1]}{random.choice(other_suits)}"]

        return hero, villain, board

    @staticmethod
    def _build_oesd():
        """Hero has open-ended straight draw. 8 outs."""
        # Pick 4 consecutive ranks for the draw
        start = random.randint(1, 8)  # 3 through T as starting rank (index 1-8)
        draw_ranks = RANKS[start:start + 4]

        hero_ranks = [draw_ranks[0], draw_ranks[3]]
        board_ranks = [draw_ranks[1], draw_ranks[2]]

        suits = random.sample(SUITS, 4)
        hero = [f"{hero_ranks[0]}{suits[0]}", f"{hero_ranks[1]}{suits[1]}"]
        off_rank = random.choice([r for r in RANKS if r not in draw_ranks])
        board = [
            f"{board_ranks[0]}{suits[2]}",
            f"{board_ranks[1]}{suits[3]}",
            f"{off_rank}{random.choice(SUITS)}",
        ]

        v_rank = random.choice([r for r in RANKS[8:] if r not in draw_ranks and r != off_rank])
        villain = [f"{v_rank}{suits[0]}", f"{v_rank}{suits[1]}"]

        return hero, villain, board

    @staticmethod
    def _build_gutshot():
        """Hero has gutshot straight draw. 4 outs."""
        start = random.randint(0, 8)
        needed_ranks = RANKS[start:start + 5]

        # Remove middle card to create gutshot
        missing_idx = random.choice([1, 2, 3])
        hero_ranks = [needed_ranks[0], needed_ranks[4]]
        board_ranks = [r for i, r in enumerate(needed_ranks[1:4]) if i != missing_idx - 1]

        suits = random.sample(SUITS, 4)
        hero = [f"{hero_ranks[0]}{suits[0]}", f"{hero_ranks[1]}{suits[1]}"]
        off_rank = random.choice([r for r in RANKS if r not in needed_ranks])
        board = [
            f"{board_ranks[0]}{suits[2]}",
            f"{board_ranks[1]}{suits[3]}",
            f"{off_rank}{random.choice(SUITS)}",
        ]

        v_rank = random.choice([r for r in RANKS[8:] if r not in needed_ranks and r != off_rank])
        villain = [f"{v_rank}{suits[2]}", f"{v_rank}{suits[3]}"]

        return hero, villain, board

    @staticmethod
    def _build_overcards():
        """Hero has two overcards vs a pair. 6 outs."""
        board_pair_rank = random.choice(RANKS[4:9])
        hero_ranks = random.sample(RANKS[RANK_INDEX[board_pair_rank] + 1:], 2)

        suits = random.sample(SUITS, 4)
        hero = [f"{hero_ranks[0]}{suits[0]}", f"{hero_ranks[1]}{suits[1]}"]

        off_rank = random.choice([r for r in RANKS[:RANK_INDEX[board_pair_rank]] if r != board_pair_rank])
        board = [
            f"{board_pair_rank}{suits[2]}",
            f"{off_rank}{suits[3]}",
            f"{random.choice([r for r in RANKS[:RANK_INDEX[board_pair_rank]] if r != board_pair_rank and r != off_rank])}{random.choice(SUITS)}",
        ]

        villain = [f"{board_pair_rank}{suits[0]}", f"{board_pair_rank}{suits[1]}"]

        return hero, villain, board

    @staticmethod
    def _build_combo_draw():
        """Hero has flush draw + straight draw. ~15 outs."""
        suit = random.choice(SUITS)
        other_suits = [s for s in SUITS if s != suit]

        # OESD + flush draw
        start = random.randint(2, 7)
        draw_ranks = RANKS[start:start + 4]

        hero = [f"{draw_ranks[0]}{suit}", f"{draw_ranks[3]}{suit}"]
        off_rank = random.choice([r for r in RANKS if r not in draw_ranks])
        board = [
            f"{draw_ranks[1]}{suit}",
            f"{draw_ranks[2]}{random.choice(other_suits)}",
            f"{off_rank}{random.choice(other_suits)}",
        ]

        v_rank = random.choice([r for r in RANKS[9:] if r not in draw_ranks and r != off_rank])
        v_suits = random.sample(other_suits, 2)
        villain = [f"{v_rank}{v_suits[0]}", f"{v_rank}{v_suits[1]}"]

        return hero, villain, board

    @staticmethod
    def _build_two_pair_draw():
        """Hero has one pair, drawing to two pair. ~4 outs (hitting second pair)."""
        hero_rank = random.choice(RANKS[5:10])
        kicker_rank = random.choice([r for r in RANKS[7:] if r != hero_rank])

        suits = random.sample(SUITS, 4)
        hero = [f"{hero_rank}{suits[0]}", f"{kicker_rank}{suits[1]}"]

        board_pair_rank = random.choice([r for r in RANKS[8:] if r != hero_rank and r != kicker_rank])
        off_rank = random.choice([r for r in RANKS[:5] if r != hero_rank])
        board = [
            f"{hero_rank}{suits[2]}",
            f"{board_pair_rank}{suits[3]}",
            f"{off_rank}{random.choice(SUITS)}",
        ]

        villain = [f"{board_pair_rank}{suits[0]}", f"{board_pair_rank}{suits[1]}"]

        return hero, villain, board

    # ── Mode 5: Range Painter ──────────────────────

    @staticmethod
    def _range_painter(difficulty):
        """Pick a spot and return the correct range for painting."""
        spots = SPOTS_BY_DIFFICULTY.get(difficulty, SPOTS_BY_DIFFICULTY['normal'])
        spot_key = random.choice(spots)
        spot = RANGE_SPOTS[spot_key]

        equation = f"Paint the range: {spot['description']}"
        correct_range = spot['range']

        return equation, 0, 0, 'range', {
            'correct_range': correct_range,
            'spot_id': spot_key,
        }

    # ── Generation Interface ───────────────────────

    @classmethod
    def generate(cls, categories=None, difficulty='normal', problem_type=None, scenario_type=None):
        """Generate a single poker problem from selected categories."""
        if categories is None:
            categories = ['pot_odds']

        if problem_type is None:
            pool = []
            for cat in categories:
                pool.extend(cls.CATEGORY_MAP.get(cat, []))
            if not pool:
                pool = cls.CATEGORY_MAP['pot_odds']
            problem_type = random.choice(pool)

        method_name = cls.METHOD_MAP[problem_type]
        method = getattr(cls, method_name)

        # Pass scenario_type through for equity problems
        if problem_type == 'equity_intuition' and scenario_type is not None:
            equation, answer, tolerance, mode, extra_data = method(difficulty, scenario_type=scenario_type)
        else:
            equation, answer, tolerance, mode, extra_data = method(difficulty)

        # Determine type tag (equity uses scenario_type from extra_data)
        if problem_type == 'equity_intuition':
            type_tag = extra_data.get('scenario_type', problem_type)
        else:
            type_tag = problem_type

        category = cls.TYPE_TO_CATEGORY.get(type_tag, problem_type)

        return {
            'id': str(uuid.uuid4()),
            'equation': equation,
            'answer': answer,
            'tolerance': tolerance,
            'difficulty_rating': 0,
            'poker_mode': mode,
            'extra_data': extra_data,
            'tags': [category, type_tag],
        }

    @classmethod
    def generate_targeted(cls, focus_tags, categories, difficulty):
        """Generate a problem targeting a specific weakness tag."""
        available_types = []
        for cat in categories:
            available_types.extend(cls.CATEGORY_MAP.get(cat, []))

        for tag in focus_tags:
            # Direct match: tag is a METHOD_MAP key (pot_odds, combinatorics, etc.)
            if tag in cls.METHOD_MAP and tag in available_types:
                return cls.generate(categories, difficulty, problem_type=tag)
            # Equity scenario match: tag is a scenario name (flush_draw, gutshot, etc.)
            if tag in cls.EQUITY_SCENARIO_NAMES and 'equity_intuition' in available_types:
                return cls.generate(categories, difficulty, problem_type='equity_intuition', scenario_type=tag)

        return cls.generate(categories, difficulty)

    @classmethod
    def generate_batch(cls, count, options, focus_tags=None):
        """Generate a batch of poker problems."""
        categories = options.get('categories', ['pot_odds'])
        difficulty = options.get('difficulty', 'normal')

        if not focus_tags:
            return [cls.generate(categories, difficulty) for _ in range(count)]

        targeted_count = count // 2
        standard_count = count - targeted_count
        problems = []
        for _ in range(targeted_count):
            problems.append(cls.generate_targeted(focus_tags, categories, difficulty))
        for _ in range(standard_count):
            problems.append(cls.generate(categories, difficulty))

        random.shuffle(problems)
        return problems
