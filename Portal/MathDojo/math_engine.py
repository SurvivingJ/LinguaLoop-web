import random
import re
import uuid


class TagExtractor:
    """Extracts deterministic tags from an arithmetic problem's equation and answer."""

    TRAPS = {
        frozenset({7, 8}): 'trap:7x8',
        frozenset({6, 7}): 'trap:6x7',
        frozenset({8, 9}): 'trap:8x9',
        frozenset({6, 9}): 'trap:6x9',
    }

    OP_MAP = {'+': 'op:add', '-': 'op:sub', '\u00d7': 'op:mul', '\u00f7': 'op:div'}

    @staticmethod
    def extract(equation, answer):
        """Extract tags from equation string and answer. Returns deduplicated list."""
        tags = []
        numbers = [int(n) for n in re.findall(r'\d+', equation)]
        operators = re.findall(r'[+\-\u00d7\u00f7]', equation)

        if not numbers or not operators:
            return tags

        # Operation tags
        seen_ops = set()
        for op in operators:
            tag = TagExtractor.OP_MAP.get(op)
            if tag and tag not in seen_ops:
                tags.append(tag)
                seen_ops.add(tag)

        # For 2-operand, single-operator problems: detailed analysis
        is_simple = len(numbers) == 2 and len(operators) == 1
        if is_simple:
            a, b = numbers[0], numbers[1]
            op = operators[0]

            # Scale tags
            da, db = len(str(a)), len(str(b))
            if max(da, db) >= 4:
                tags.append('scale:big')
            else:
                tags.append(f'scale:{da}x{db}')

            # Carry/borrow tags (addition and subtraction)
            if op == '+':
                carries = TagExtractor._count_carries(a, b)
                if carries == 0:
                    tags.append('carry:none')
                elif carries == 1:
                    tags.append('carry:once')
                else:
                    tags.append('carry:multi')

                # Bridge detection
                result = a + b
                if (a // 100) != (result // 100):
                    tags.append('bridge:hundreds')
                elif (a // 10) != (result // 10):
                    tags.append('bridge:tens')

            elif op == '-':
                borrows = TagExtractor._count_borrows(a, b)
                if borrows == 0:
                    tags.append('carry:none')
                elif borrows == 1:
                    tags.append('carry:once')
                else:
                    tags.append('carry:multi')

                # Borrow across zero
                if TagExtractor._has_borrow_across_zero(a, b):
                    tags.append('borrow:across-zero')

                # Bridge detection (downward)
                result = a - b
                if (a // 100) != (result // 100):
                    tags.append('bridge:hundreds')
                elif (a // 10) != (result // 10):
                    tags.append('bridge:tens')

            # Multiplication table difficulty
            elif op == '\u00d7':
                if a <= 5 and b <= 5:
                    tags.append('table:easy')
                elif a >= 10 or b >= 10 or (a >= 7 and b >= 7):
                    tags.append('table:hard')
                else:
                    tags.append('table:mid')

                # Trap facts
                key = frozenset({a, b})
                if key in TagExtractor.TRAPS:
                    tags.append(TagExtractor.TRAPS[key])

            # Division large dividend
            elif op == '\u00f7':
                if a >= 100:
                    tags.append('div:large')
                # Trap detection for division: answer and divisor are the original factors
                key = frozenset({answer, b})
                if key in TagExtractor.TRAPS:
                    tags.append(TagExtractor.TRAPS[key])

            # Near-round operand
            for num in [a, b]:
                if num > 1 and num % 10 in (1, 9):
                    tags.append('near:round')
                    break

        return list(set(tags))

    @staticmethod
    def _count_carries(a, b):
        """Count number of carries when adding a + b."""
        carry = 0
        count = 0
        while a > 0 or b > 0:
            s = (a % 10) + (b % 10) + carry
            if s >= 10:
                count += 1
                carry = 1
            else:
                carry = 0
            a //= 10
            b //= 10
        return count

    @staticmethod
    def _count_borrows(a, b):
        """Count number of borrows when computing a - b (a >= b)."""
        borrow = 0
        count = 0
        while a > 0 or b > 0:
            da = (a % 10) - borrow
            db = b % 10
            if da < db:
                count += 1
                borrow = 1
            else:
                borrow = 0
            a //= 10
            b //= 10
        return count

    @staticmethod
    def _has_borrow_across_zero(a, b):
        """Check if subtraction a - b requires borrowing through a 0 digit in a."""
        borrow = 0
        while a > 0 or b > 0:
            da = (a % 10) - borrow
            db = b % 10
            if da < db:
                borrow = 1
                # Check if the next digit of a is 0 (borrow across zero)
                next_digit = (a // 10) % 10
                if next_digit == 0 and a // 10 > 0:
                    return True
            else:
                borrow = 0
            a //= 10
            b //= 10
        return False


class DrillGenerator:
    """Generates arithmetic problems targeting specific weakness tags,
    while respecting the user's configured operations and digit range."""

    # Tags that require specific operations
    _ADD_SUB_TAGS = {'carry:once', 'carry:multi', 'bridge:tens', 'bridge:hundreds',
                     'borrow:across-zero', 'near:round'}
    _MUL_TAGS = {'table:easy', 'table:mid', 'table:hard',
                 'trap:7x8', 'trap:6x7', 'trap:8x9', 'trap:6x9'}
    _DIV_TAGS = {'div:large'}

    TRAP_FACTORS = {
        'trap:7x8': (7, 8),
        'trap:6x7': (6, 7),
        'trap:8x9': (8, 9),
        'trap:6x9': (6, 9),
    }

    @staticmethod
    def generate_targeted(focus_tags, options):
        """Generate a problem matching at least one focus_tag within user config.

        Args:
            focus_tags: list of tag strings to target
            options: dict with operations, mix, min_digits, max_digits

        Returns: problem dict with id, equation, answer, difficulty_rating, tags
        """
        ops = options.get('operations', ['addition'])
        min_d = options.get('min_digits', 1)
        max_d = options.get('max_digits', 2)

        # Filter focus_tags to those achievable with user's config
        has_add = 'addition' in ops
        has_sub = 'subtraction' in ops
        has_mul = 'multiplication' in ops
        has_div = 'division' in ops
        has_add_sub = has_add or has_sub

        achievable = []
        for tag in focus_tags:
            if tag in DrillGenerator._ADD_SUB_TAGS and has_add_sub:
                achievable.append(tag)
            elif tag in DrillGenerator._MUL_TAGS and has_mul:
                achievable.append(tag)
            elif tag in DrillGenerator._DIV_TAGS and has_div:
                achievable.append(tag)
            elif tag.startswith('scale:'):
                achievable.append(tag)
            elif tag.startswith('op:'):
                achievable.append(tag)

        if not achievable:
            return ProblemGenerator.get_problem_custom(options)

        target = random.choice(achievable)

        # Try up to 20 times to generate a matching problem
        for _ in range(20):
            eq, ans = DrillGenerator._build_for_tag(target, ops, min_d, max_d)
            if eq is not None:
                tags = TagExtractor.extract(eq, int(ans))
                if target in tags:
                    return {
                        'id': str(uuid.uuid4()),
                        'equation': eq,
                        'answer': int(ans),
                        'difficulty_rating': 0,
                        'tags': tags
                    }

        # Fallback to standard generation
        return ProblemGenerator.get_problem_custom(options)

    @staticmethod
    def _build_for_tag(tag, ops, min_d, max_d):
        """Dispatch to the appropriate builder. Returns (equation, answer) or (None, None)."""
        rand = ProblemGenerator._random_operand

        if tag == 'carry:once':
            return DrillGenerator._build_carry_once(ops, min_d, max_d)
        elif tag == 'carry:multi':
            return DrillGenerator._build_carry_multi(ops, min_d, max_d)
        elif tag.startswith('trap:'):
            return DrillGenerator._build_trap(tag, min_d, max_d)
        elif tag == 'bridge:tens':
            return DrillGenerator._build_bridge_tens(ops, min_d, max_d)
        elif tag == 'bridge:hundreds':
            return DrillGenerator._build_bridge_hundreds(ops, min_d, max_d)
        elif tag == 'borrow:across-zero':
            return DrillGenerator._build_borrow_across_zero(min_d, max_d)
        elif tag.startswith('table:'):
            return DrillGenerator._build_table(tag, min_d, max_d)
        elif tag == 'div:large':
            return DrillGenerator._build_div_large(min_d, max_d)
        elif tag == 'near:round':
            return DrillGenerator._build_near_round(ops, min_d, max_d)
        else:
            # For op: and scale: tags, use standard generation
            return None, None

    @staticmethod
    def _build_carry_once(ops, min_d, max_d):
        """Addition with exactly one carry in the ones column."""
        a = ProblemGenerator._random_operand(min_d, max_d)
        ones_a = a % 10
        if ones_a < 2:
            a = (a // 10) * 10 + random.randint(5, 9)
            ones_a = a % 10
        b_ones = random.randint(10 - ones_a, 9)
        # Keep tens small to avoid second carry
        b = b_ones if min_d <= 1 else random.randint(1, 3) * 10 + b_ones
        if 'addition' in ops:
            return f"{a} + {b}", a + b
        elif 'subtraction' in ops:
            total = a + b
            return f"{total} - {a}", b
        return None, None

    @staticmethod
    def _build_carry_multi(ops, min_d, max_d):
        """Addition with 2+ carries."""
        if max_d >= 2:
            a = random.randint(55, 99)
            b = random.randint(55, 99)
        else:
            a = random.randint(6, 9)
            b = random.randint(6, 9)
        if 'addition' in ops:
            return f"{a} + {b}", a + b
        elif 'subtraction' in ops and max_d >= 2:
            total = a + b
            return f"{total} - {a}", b
        return None, None

    @staticmethod
    def _build_trap(tag, min_d, max_d):
        """Multiplication using a notorious fact pair."""
        if tag not in DrillGenerator.TRAP_FACTORS:
            return None, None
        a, b = DrillGenerator.TRAP_FACTORS[tag]
        if random.choice([True, False]):
            a, b = b, a
        return f"{a} \u00d7 {b}", a * b

    @staticmethod
    def _build_bridge_tens(ops, min_d, max_d):
        """Addition/subtraction crossing a tens boundary."""
        a = ProblemGenerator._random_operand(min_d, max_d)
        ones_a = a % 10
        if ones_a < 5:
            a = (a // 10) * 10 + random.randint(7, 9)
            ones_a = a % 10
        b = random.randint(10 - ones_a + 1, 9)
        if 'addition' in ops:
            return f"{a} + {b}", a + b
        elif 'subtraction' in ops:
            result = a + b
            return f"{result} - {b}", a
        return None, None

    @staticmethod
    def _build_bridge_hundreds(ops, min_d, max_d):
        """Addition/subtraction crossing a hundreds boundary."""
        if max_d < 2:
            return None, None
        base = random.choice([90, 91, 92, 93, 94, 95, 96, 97, 98, 99])
        b = random.randint(10 - (base % 10) + 1, 20)
        if 'addition' in ops:
            return f"{base} + {b}", base + b
        elif 'subtraction' in ops:
            result = base + b
            return f"{result} - {b}", base
        return None, None

    @staticmethod
    def _build_borrow_across_zero(min_d, max_d):
        """Subtraction borrowing through a 0 digit."""
        if max_d < 3:
            # 2-digit with zero: e.g., 30 - 7
            a = random.choice([20, 30, 40, 50, 60, 70, 80, 90])
            b = random.randint(1, 9)
        else:
            a = random.choice([100, 101, 102, 103, 200, 201, 300, 400, 500])
            b = random.randint(1, min(a - 1, 9))
        return f"{a} - {b}", a - b

    @staticmethod
    def _build_table(tag, min_d, max_d):
        """Multiplication with specific table difficulty."""
        if tag == 'table:easy':
            a = random.randint(2, 5)
            b = random.randint(2, 5)
        elif tag == 'table:mid':
            a = random.randint(6, 9)
            b = random.randint(2, 9)
        else:  # table:hard
            a = random.randint(7, 12)
            b = random.randint(7, 12)
        return f"{a} \u00d7 {b}", a * b

    @staticmethod
    def _build_div_large(min_d, max_d):
        """Division with dividend >= 100."""
        divisor = random.randint(2, 12)
        min_q = max(2, 100 // divisor + 1)
        quotient = random.randint(min_q, min_q + 10)
        dividend = divisor * quotient
        return f"{dividend} \u00f7 {divisor}", quotient

    @staticmethod
    def _build_near_round(ops, min_d, max_d):
        """Problem with an operand near a round number (±1 from multiple of 10)."""
        near_vals = [9, 11, 19, 21, 29, 31, 39, 41, 49, 51, 59, 61, 69, 71, 79, 81, 89, 91, 99]
        a = random.choice([v for v in near_vals if len(str(v)) <= max_d])
        b = ProblemGenerator._random_operand(min_d, max_d)
        if 'addition' in ops:
            return f"{a} + {b}", a + b
        elif 'subtraction' in ops:
            if a < b:
                a, b = b, a
            return f"{a} - {b}", a - b
        elif 'multiplication' in ops:
            b = random.randint(2, 9)
            return f"{a} \u00d7 {b}", a * b
        return None, None


class ProblemGenerator:
    """Generates math problems with difficulty scaling based on Elo rating."""

    @staticmethod
    def elo_to_difficulty(elo):
        """
        Convert Elo rating to difficulty score (0-100).

        Elo 800-1000 → difficulty 0-20
        Elo 1000-1200 → difficulty 20-50
        Elo 1200-1400 → difficulty 50-80
        Elo 1400+ → difficulty 80-100
        """
        if elo < 1000:
            return max(0, min(20, (elo - 800) * 0.1))
        elif elo < 1200:
            return 20 + (elo - 1000) * 0.15
        elif elo < 1400:
            return 50 + (elo - 1200) * 0.15
        else:
            return min(100, 80 + (elo - 1400) * 0.1)

    # ── Helper methods for problem generation ──────────────────────────

    @staticmethod
    def _single_digit_add_easy():
        """Single-digit addition with small numbers (1-5)."""
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        return f"{a} + {b}", a + b

    @staticmethod
    def _single_digit_add_full():
        """Single-digit addition, full range (sums can exceed 10)."""
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        return f"{a} + {b}", a + b

    @staticmethod
    def _single_digit_sub():
        """Single-digit subtraction (positive results)."""
        a = random.randint(3, 9)
        b = random.randint(1, a - 1)
        return f"{a} - {b}", a - b

    @staticmethod
    def _two_digit_one_digit_no_carry():
        """2-digit ± 1-digit without carrying/borrowing."""
        tens = random.randint(1, 8)
        ones = random.randint(1, 4)
        a = tens * 10 + ones
        if random.choice([True, False]):
            b = random.randint(1, 9 - ones)  # No carry
            return f"{a} + {b}", a + b
        else:
            b = random.randint(1, ones)  # No borrow
            return f"{a} - {b}", a - b

    @staticmethod
    def _two_digit_one_digit_carry():
        """2-digit ± 1-digit with carrying/borrowing."""
        if random.choice([True, False]):
            # Addition with carry: ones digits sum > 9
            ones_a = random.randint(5, 9)
            a = random.randint(1, 8) * 10 + ones_a
            b = random.randint(10 - ones_a, 9)
            return f"{a} + {b}", a + b
        else:
            # Subtraction with borrow: ones digit of a < b
            ones_a = random.randint(0, 4)
            a = random.randint(2, 9) * 10 + ones_a
            b = random.randint(ones_a + 1, 9)
            return f"{a} - {b}", a - b

    @staticmethod
    def _two_digit_two_digit():
        """2-digit ± 2-digit with carry/borrow."""
        a = random.randint(20, 99)
        b = random.randint(11, 79)
        if random.choice([True, False]):
            return f"{a} + {b}", a + b
        else:
            if a < b:
                a, b = b, a
            return f"{a} - {b}", a - b

    @staticmethod
    def _multiplication_tables(allowed_factors=None):
        """Multiplication from times tables."""
        if allowed_factors is None:
            allowed_factors = list(range(2, 13))
        a = random.choice(allowed_factors)
        b = random.randint(2, 12)
        return f"{a} × {b}", a * b

    @staticmethod
    def _two_digit_times_one_digit(max_a=49, max_b=9):
        """2-digit × 1-digit."""
        a = random.randint(10, max_a)
        b = random.randint(2, max_b)
        return f"{a} × {b}", a * b

    @staticmethod
    def _squares(min_val=2, max_val=15):
        """Perfect squares."""
        a = random.randint(min_val, max_val)
        return f"{a}²", a * a

    @staticmethod
    def _division(allowed_divisors=None):
        """Integer division (reverse multiplication to guarantee whole answers)."""
        if allowed_divisors is None:
            allowed_divisors = list(range(2, 13))
        b = random.choice(allowed_divisors)
        a = random.randint(2, 12)
        product = a * b
        return f"{product} ÷ {b}", a

    @staticmethod
    def _three_digit_two_digit():
        """3-digit ± 2-digit."""
        a = random.randint(100, 999)
        b = random.randint(10, 99)
        if random.choice([True, False]):
            return f"{a} + {b}", a + b
        else:
            return f"{a} - {b}", a - b

    @staticmethod
    def _two_digit_times_two_digit(max_a=19, max_b=19):
        """2-digit × 2-digit."""
        a = random.randint(11, max_a)
        b = random.randint(11, max_b)
        return f"{a} × {b}", a * b

    @staticmethod
    def _two_operations():
        """Two-operation expression. Always produces integer results."""
        pattern = random.choice([
            'mult_add', 'mult_sub', 'add_mult', 'sub_mult'
        ])

        if pattern == 'mult_add':
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            c = random.randint(1, 30)
            return f"{a} × {b} + {c}", a * b + c

        elif pattern == 'mult_sub':
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            c = random.randint(1, a * b - 1)
            return f"{a} × {b} - {c}", a * b - c

        elif pattern == 'add_mult':
            a = random.randint(2, 20)
            b = random.randint(2, 20)
            c = random.randint(2, 9)
            return f"({a} + {b}) × {c}", (a + b) * c

        else:  # sub_mult
            a = random.randint(10, 30)
            b = random.randint(1, a - 2)
            c = random.randint(2, 6)
            return f"({a} - {b}) × {c}", (a - b) * c

    @staticmethod
    def _order_of_operations():
        """Expressions requiring BODMAS awareness. Integer results guaranteed."""
        pattern = random.choice([
            'add_mult', 'sub_mult', 'div_add', 'div_sub'
        ])

        if pattern == 'add_mult':
            # a + b × c  (must compute b*c first)
            b = random.randint(2, 9)
            c = random.randint(2, 9)
            a = random.randint(1, 30)
            return f"{a} + {b} × {c}", a + b * c

        elif pattern == 'sub_mult':
            # a - b × c  (ensure positive result)
            b = random.randint(2, 7)
            c = random.randint(2, 7)
            a = random.randint(b * c + 1, b * c + 30)
            return f"{a} - {b} × {c}", a - b * c

        elif pattern == 'div_add':
            # a ÷ b + c
            b = random.randint(2, 12)
            quotient = random.randint(2, 12)
            a = quotient * b
            c = random.randint(1, 30)
            return f"{a} ÷ {b} + {c}", quotient + c

        else:  # div_sub
            # a ÷ b - c  (ensure positive result)
            b = random.randint(2, 12)
            quotient = random.randint(5, 15)
            a = quotient * b
            c = random.randint(1, quotient - 1)
            return f"{a} ÷ {b} - {c}", quotient - c

    @staticmethod
    def _three_operations():
        """Three-operation expressions. Integer results at every step."""
        pattern = random.choice([
            'mult_add_div', 'paren_mult_sub', 'div_add_mult', 'mult_sub_add'
        ])

        if pattern == 'mult_add_div':
            # a × b + c ÷ d
            a = random.randint(2, 9)
            b = random.randint(2, 9)
            d = random.randint(2, 9)
            quotient = random.randint(1, 9)
            c = quotient * d
            return f"{a} × {b} + {c} ÷ {d}", a * b + quotient

        elif pattern == 'paren_mult_sub':
            # (a + b) × c - d
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            c = random.randint(2, 6)
            product = (a + b) * c
            d = random.randint(1, min(product - 1, 30))
            return f"({a} + {b}) × {c} - {d}", product - d

        elif pattern == 'div_add_mult':
            # (a ÷ b + c) × d
            b = random.randint(2, 9)
            quotient = random.randint(2, 9)
            a = quotient * b
            c = random.randint(1, 10)
            d = random.randint(2, 6)
            return f"({a} ÷ {b} + {c}) × {d}", (quotient + c) * d

        else:  # mult_sub_add
            # a × b - c + d
            a = random.randint(2, 9)
            b = random.randint(2, 9)
            product = a * b
            c = random.randint(1, product - 1)
            d = random.randint(1, 20)
            return f"{a} × {b} - {c} + {d}", product - c + d

    # ── Main generation method ─────────────────────────────────────────

    @staticmethod
    def get_problem(difficulty_score, ops=None):
        """
        Generate a math problem based on difficulty score (0-100).

        15 difficulty tiers:
          0-3:   Single-digit add (easy, 1-5)
          4-7:   Single-digit add (full range)
          8-10:  Single-digit subtract
          11-15: 2d ± 1d, no carry
          16-20: 2d ± 1d, with carry
          21-26: 2d ± 2d
          27-35: Multiplication tables 2-12
          36-45: 2d × 1d
          46-50: Squares (2-15)
          51-60: Integer division
          61-67: 3d ± 2d
          68-75: 2d × 2d
          76-85: Two-operation expressions
          86-93: Order of operations / division combos
          94-100: Three-operation expressions
        """
        gen = ProblemGenerator

        if difficulty_score <= 3:
            equation, answer = gen._single_digit_add_easy()

        elif difficulty_score <= 7:
            equation, answer = gen._single_digit_add_full()

        elif difficulty_score <= 10:
            equation, answer = gen._single_digit_sub()

        elif difficulty_score <= 15:
            equation, answer = gen._two_digit_one_digit_no_carry()

        elif difficulty_score <= 20:
            equation, answer = gen._two_digit_one_digit_carry()

        elif difficulty_score <= 26:
            equation, answer = gen._two_digit_two_digit()

        elif difficulty_score <= 35:
            equation, answer = gen._multiplication_tables()

        elif difficulty_score <= 45:
            # Scale operand size within this range
            max_a = 25 if difficulty_score <= 40 else 49
            max_b = 7 if difficulty_score <= 40 else 9
            equation, answer = gen._two_digit_times_one_digit(max_a, max_b)

        elif difficulty_score <= 50:
            max_val = 12 if difficulty_score <= 47 else 15
            equation, answer = gen._squares(2, max_val)

        elif difficulty_score <= 60:
            equation, answer = gen._division()

        elif difficulty_score <= 67:
            equation, answer = gen._three_digit_two_digit()

        elif difficulty_score <= 75:
            max_a = 15 if difficulty_score <= 70 else 19
            max_b = 15 if difficulty_score <= 70 else 19
            equation, answer = gen._two_digit_times_two_digit(max_a, max_b)

        elif difficulty_score <= 85:
            equation, answer = gen._two_operations()

        elif difficulty_score <= 93:
            equation, answer = gen._order_of_operations()

        else:
            equation, answer = gen._three_operations()

        return {
            'id': str(uuid.uuid4()),
            'equation': equation,
            'answer': answer,
            'difficulty_rating': int(difficulty_score)
        }

    # ── Custom drill generation ──────────────────────────────────────

    @staticmethod
    def _random_operand(min_digits, max_digits):
        """Generate a random integer with digit count between min_digits and max_digits."""
        digits = random.randint(min_digits, max_digits)
        if digits == 1:
            return random.randint(1, 9)
        low = 10 ** (digits - 1)
        high = 10 ** digits - 1
        return random.randint(low, high)

    @staticmethod
    def _custom_single_op(op, min_digits, max_digits):
        """Generate a single-operation problem with given op and digit constraints."""
        if op == 'addition':
            a = ProblemGenerator._random_operand(min_digits, max_digits)
            b = ProblemGenerator._random_operand(min_digits, max_digits)
            return f"{a} + {b}", a + b

        elif op == 'subtraction':
            a = ProblemGenerator._random_operand(min_digits, max_digits)
            b = ProblemGenerator._random_operand(min_digits, max_digits)
            if a < b:
                a, b = b, a
            return f"{a} - {b}", a - b

        elif op == 'multiplication':
            a = ProblemGenerator._random_operand(min_digits, max_digits)
            b = ProblemGenerator._random_operand(min_digits, max_digits)
            return f"{a} × {b}", a * b

        elif op == 'division':
            # Reverse-multiply to guarantee integer results
            divisor = ProblemGenerator._random_operand(min_digits, max_digits)
            quotient = ProblemGenerator._random_operand(min_digits, max_digits)
            dividend = divisor * quotient
            return f"{dividend} ÷ {divisor}", quotient

        return "1 + 1", 2  # fallback

    @staticmethod
    def _custom_mixed_expression(ops, min_digits, max_digits):
        """Generate a 2-3 operation expression using selected ops. Integer results guaranteed."""
        num_ops = random.choice([2, 3])
        chosen_ops = [random.choice(ops) for _ in range(num_ops)]

        if num_ops == 2:
            return ProblemGenerator._custom_two_op(chosen_ops, min_digits, max_digits)
        else:
            return ProblemGenerator._custom_three_op(chosen_ops, min_digits, max_digits)

    @staticmethod
    def _custom_two_op(ops, min_digits, max_digits):
        """Build a 2-operation expression from selected ops."""
        op1, op2 = ops[0], ops[1]
        rand = ProblemGenerator._random_operand

        # a OP1 b OP2 c — build left to right, ensuring integer/positive results
        a = rand(min_digits, max_digits)
        b = rand(min_digits, max_digits)

        # Compute first result
        if op1 == 'addition':
            mid = a + b
            eq = f"{a} + {b}"
        elif op1 == 'subtraction':
            if a < b:
                a, b = b, a
            mid = a - b
            eq = f"{a} - {b}"
        elif op1 == 'multiplication':
            mid = a * b
            eq = f"{a} × {b}"
        elif op1 == 'division':
            quotient = a
            a = a * b  # make a divisible by b
            mid = quotient
            eq = f"{a} ÷ {b}"
        else:
            mid = a + b
            eq = f"{a} + {b}"

        c = rand(min_digits, max_digits)

        # Apply second operation
        if op2 == 'addition':
            answer = mid + c
            eq = f"{eq} + {c}"
        elif op2 == 'subtraction':
            if mid < c:
                c = random.randint(1, max(1, mid - 1)) if mid > 1 else 1
            answer = mid - c
            eq = f"{eq} - {c}"
        elif op2 == 'multiplication':
            answer = mid * c
            eq = f"({eq}) × {c}"
        elif op2 == 'division':
            # Make mid divisible by c
            if c == 0:
                c = 1
            remainder = mid % c
            mid = mid - remainder  # adjust mid down
            if mid == 0:
                mid = c
            # Recalculate — rebuild from scratch for clean division
            quotient_val = rand(min_digits, max_digits)
            c_val = rand(min_digits, max_digits)
            if c_val == 0:
                c_val = 1
            mid_val = quotient_val * c_val

            # Rebuild first part to produce mid_val
            if op1 == 'addition':
                a2 = rand(min_digits, max_digits)
                b2 = mid_val - a2
                if b2 <= 0:
                    b2 = rand(min_digits, max_digits)
                    a2 = mid_val - b2
                eq = f"({a2} + {b2}) ÷ {c_val}"
            else:
                eq = f"{mid_val} ÷ {c_val}"
            answer = quotient_val
        else:
            answer = mid + c
            eq = f"{eq} + {c}"

        return eq, answer

    @staticmethod
    def _custom_three_op(ops, min_digits, max_digits):
        """Build a 3-operation expression. Falls back to chaining simple ops."""
        # Simple approach: a OP1 b OP2 c OP3 d, evaluated left to right with parens
        rand = ProblemGenerator._random_operand

        # Generate as (a OP1 b) OP2 c OP3 d
        a = rand(min_digits, max_digits)
        b = rand(min_digits, max_digits)
        c = rand(min_digits, max_digits)
        d = rand(min_digits, max_digits)

        parts = [a]
        result = a
        eq_parts = [str(a)]

        for i, op in enumerate(ops):
            operand = [b, c, d][i] if i < 3 else rand(min_digits, max_digits)

            if op == 'addition':
                result = result + operand
                eq_parts.append(f"+ {operand}")
            elif op == 'subtraction':
                if result < operand:
                    operand = random.randint(1, max(1, result - 1)) if result > 1 else 1
                result = result - operand
                eq_parts.append(f"- {operand}")
            elif op == 'multiplication':
                result = result * operand
                # Wrap previous in parens
                prev = ' '.join(eq_parts)
                eq_parts = [f"({prev}) × {operand}"]
            elif op == 'division':
                if operand == 0:
                    operand = 1
                # Adjust result to be divisible
                remainder = result % operand
                result = result - remainder
                if result == 0:
                    result = operand
                result = result // operand
                prev = ' '.join(eq_parts)
                eq_parts = [f"({prev}) ÷ {operand}"]

        return ' '.join(eq_parts), result

    @staticmethod
    def get_problem_custom(options):
        """
        Generate a problem based on custom drill options.

        options dict:
            operations: list of str ('addition', 'subtraction', 'multiplication', 'division')
            mix: bool — if True, generate multi-op expressions
            min_digits: int (1-4)
            max_digits: int (1-4)
        """
        gen = ProblemGenerator
        ops = options.get('operations', ['addition'])
        mix = options.get('mix', False)
        min_d = options.get('min_digits', 1)
        max_d = options.get('max_digits', 2)

        if mix and len(ops) >= 1:
            equation, answer = gen._custom_mixed_expression(ops, min_d, max_d)
        else:
            op = random.choice(ops)
            equation, answer = gen._custom_single_op(op, min_d, max_d)

        return {
            'id': str(uuid.uuid4()),
            'equation': equation,
            'answer': int(answer),
            'difficulty_rating': 0,
            'tags': TagExtractor.extract(equation, int(answer))
        }

    # ── Batch generation ───────────────────────────────────────────────

    @staticmethod
    def get_batch(count, elo):
        """Generate a batch of problems for a given Elo rating."""
        difficulty = ProblemGenerator.elo_to_difficulty(elo)
        return ProblemGenerator.get_batch_by_difficulty(count, difficulty)

    @staticmethod
    def get_batch_by_difficulty(count, difficulty):
        """Generate a batch of problems for a given difficulty score (0-100)."""
        problems = []
        for _ in range(count):
            varied = difficulty + random.randint(-3, 3)
            varied = max(0, min(100, varied))
            problems.append(ProblemGenerator.get_problem(varied))
        return problems

    @staticmethod
    def get_batch_custom(count, options, focus_tags=None):
        """Generate a batch of problems for custom drill options.

        If focus_tags provided: 50% targeted problems (via DrillGenerator),
        50% standard problems. All shuffled.
        """
        if not focus_tags:
            return [ProblemGenerator.get_problem_custom(options) for _ in range(count)]

        targeted_count = count // 2
        standard_count = count - targeted_count

        problems = []
        for _ in range(targeted_count):
            problems.append(DrillGenerator.generate_targeted(focus_tags, options))
        for _ in range(standard_count):
            problems.append(ProblemGenerator.get_problem_custom(options))

        random.shuffle(problems)
        return problems


class FinancialProblemGenerator:
    """Generates financial mental math problems across 8 categories."""

    # ── Category A: Time Value / Compounding Rules ────────────────────

    @staticmethod
    def _rule_of_72(difficulty):
        """Rule of 72: years to double given rate, or rate given years."""
        if difficulty == 'easy':
            rates = [4, 6, 8, 9, 12]
        elif difficulty == 'hard':
            rates = [2, 3, 7, 8, 9, 18, 24, 36]
        else:
            rates = [2, 3, 4, 6, 8, 9, 12, 18, 24]

        if random.choice([True, False]):
            # Forward: given rate, find years
            rate = random.choice(rates)
            answer = round(72 / rate, 1)
            eq = f"At {rate}% return, years to double?"
            expl = f"Rule of 72: 72 / {rate} = {answer} years"
        else:
            # Reverse: given years, find rate
            years_options = [y for y in [2, 3, 4, 6, 8, 9, 12, 18, 24, 36] if 72 / y == int(72 / y)]
            if difficulty == 'easy':
                years_options = [y for y in years_options if y in [4, 6, 8, 9, 12]]
            years = random.choice(years_options)
            answer = round(72 / years, 1)
            eq = f"Double in {years} years. Required rate %?"
            expl = f"Rule of 72: 72 / {years} = {answer}%"
        return eq, answer, 1, expl

    @staticmethod
    def _rule_of_114(difficulty):
        """Rule of 114: years to triple."""
        rates = [3, 6, 12, 19] if difficulty == 'easy' else [2, 3, 6, 12, 19, 38]
        if random.choice([True, False]):
            rate = random.choice(rates)
            answer = round(114 / rate, 1)
            eq = f"At {rate}% return, years to triple?"
            expl = f"Rule of 114: 114 / {rate} = {answer} years"
        else:
            years_options = [3, 6, 12, 19, 38, 57]
            if difficulty == 'easy':
                years_options = [6, 19, 38]
            years = random.choice(years_options)
            answer = round(114 / years, 1)
            eq = f"Triple in {years} years. Required rate %?"
            expl = f"Rule of 114: 114 / {years} = {answer}%"
        return eq, answer, 1, expl

    @staticmethod
    def _rule_of_144(difficulty):
        """Rule of 144: years to quadruple."""
        rates = [4, 6, 8, 12] if difficulty == 'easy' else [3, 4, 6, 8, 9, 12, 16, 18, 24, 48]
        if random.choice([True, False]):
            rate = random.choice(rates)
            answer = round(144 / rate, 1)
            eq = f"At {rate}% return, years to 4x?"
            expl = f"Rule of 144: 144 / {rate} = {answer} years"
        else:
            years_options = [y for y in [3, 4, 6, 8, 9, 12, 16, 18, 24, 48] if 144 / y == int(144 / y)]
            if difficulty == 'easy':
                years_options = [6, 8, 12, 24]
            years = random.choice(years_options)
            answer = round(144 / years, 1)
            eq = f"Quadruple in {years} years. Required rate %?"
            expl = f"Rule of 144: 144 / {years} = {answer}%"
        return eq, answer, 1, expl

    # ── Category B: Interest Calculations ─────────────────────────────

    @staticmethod
    def _simple_interest(difficulty):
        """Simple interest: SI = P × r × t."""
        if difficulty == 'easy':
            principals = [1000, 2000, 5000, 10000]
            rates = [2, 4, 5, 10]
            times = [1, 2, 3, 5]
        elif difficulty == 'hard':
            principals = [3000, 7500, 8000, 12000, 15000, 25000]
            rates = [3, 4, 6, 7, 8, 9, 11]
            times = [2, 3, 4, 5, 7]
        else:
            principals = [1000, 2000, 4000, 5000, 8000, 10000, 20000]
            rates = [2, 3, 4, 5, 6, 8, 10]
            times = [1, 2, 3, 4, 5]

        variant = random.choice(['find_si', 'find_rate'])
        p = random.choice(principals)
        r = random.choice(rates)
        t = random.choice(times)
        si = p * r * t / 100

        if variant == 'find_si':
            eq = f"SI on ${p:,} at {r}% for {t} yr?"
            answer = si
            tol = 0
            expl = f"SI = P x r x t = {p:,} x {r}% x {t}\n= {p:,} x {r/100} x {t} = ${si:,.0f}"
        else:
            eq = f"${int(si):,} SI on ${p:,} for {t} yr. Rate %?"
            answer = r
            tol = 0.1
            expl = f"SI = P x r x t → r = SI / (P x t)\n= {int(si):,} / ({p:,} x {t}) = {int(si):,} / {p*t:,} = {r}%"
        return eq, answer, tol, expl

    @staticmethod
    def _compound_interest(difficulty):
        """Compound interest for 2-3 years."""
        if difficulty == 'easy':
            principals = [1000, 2000, 5000, 10000]
            rates = [5, 10, 20]
            years = [2]
        elif difficulty == 'hard':
            principals = [2000, 5000, 8000, 10000, 25000]
            rates = [4, 6, 7, 8, 12]
            years = [2, 3]
        else:
            principals = [1000, 2000, 5000, 10000]
            rates = [5, 8, 10, 12]
            years = [2, 3]

        p = random.choice(principals)
        r = random.choice(rates)
        t = random.choice(years)
        final = p * ((1 + r / 100) ** t)
        final = round(final, 2)

        variant = random.choice(['final', 'interest'])
        if variant == 'final':
            eq = f"${p:,} at {r}% compounded, {t} yr. Final $?"
            answer = round(final)
            tol = max(5, round(final * 0.01)) if t >= 3 and difficulty != 'easy' else 0
            steps = f"Final = P x (1 + r)^t = {p:,} x (1.{r:02d})^{t}"
            if t == 2:
                mid = round(p * (1 + r/100), 2)
                steps += f"\nYr 1: {p:,} x 1.{r:02d} = {mid:,.0f}\nYr 2: {mid:,.0f} x 1.{r:02d} = {answer:,}"
            else:
                steps += f" = ${answer:,}"
            expl = steps
        else:
            interest = round(final - p)
            eq = f"Interest: ${p:,} at {r}% compound for {t} yr?"
            answer = interest
            tol = max(5, round(interest * 0.02)) if t >= 3 and difficulty != 'easy' else 0
            expl = f"Final = {p:,} x (1.{r:02d})^{t} = {round(final):,}\nInterest = {round(final):,} - {p:,} = ${interest:,}"
        return eq, answer, tol, expl

    # ── Category C: Accounting Ratios ─────────────────────────────────

    @staticmethod
    def _margin_problem(difficulty):
        """Gross/net/operating margin percentage."""
        margin_type = random.choice(['gross', 'net', 'operating'])

        if difficulty == 'easy':
            revenues = [100, 200, 500, 1000]
            margin_pcts = [10, 15, 20, 25, 30, 40, 50]
        elif difficulty == 'hard':
            revenues = [100, 200, 250, 400, 500, 800, 1000]
            margin_pcts = [8, 12, 15, 18, 22, 28, 32, 35, 42]
        else:
            revenues = [100, 200, 300, 400, 500, 600, 800, 1000]
            margin_pcts = [10, 12, 15, 20, 25, 30, 35, 40, 50]

        # Ensure clean integer results: pick rev/pct combos where rev*pct/100 is integer
        for _ in range(20):
            rev = random.choice(revenues)
            pct = random.choice(margin_pcts)
            if (rev * pct) % 100 == 0:
                break

        if margin_type == 'gross':
            cost_or_income = int(rev * (100 - pct) / 100)
        else:
            cost_or_income = int(rev * pct / 100)

        if margin_type == 'gross':
            cogs = cost_or_income
            gp = rev - cogs
            eq = f"Revenue ${rev}M, COGS ${cogs}M. Gross margin %?"
            answer = pct
            expl = f"Gross profit = {rev} - {cogs} = {gp}\nMargin = {gp}/{rev} = {pct}%"
        elif margin_type == 'net':
            ni = cost_or_income
            eq = f"Revenue ${rev}M, Net income ${ni}M. Net margin %?"
            answer = pct
            expl = f"Net margin = NI/Revenue = {ni}/{rev} = {pct}%"
        else:
            oi = cost_or_income
            eq = f"Revenue ${rev}M, Op income ${oi}M. Op margin %?"
            answer = pct
            expl = f"Op margin = OI/Revenue = {oi}/{rev} = {pct}%"
        return eq, answer, 0, expl

    @staticmethod
    def _return_ratio(difficulty):
        """ROE or ROA percentage."""
        ratio_type = random.choice(['roe', 'roa'])

        if difficulty == 'easy':
            bases = [100, 200, 300, 500, 1000]
            pcts = [5, 10, 15, 20, 25]
        elif difficulty == 'hard':
            bases = [150, 250, 350, 450, 600, 750, 900]
            pcts = [3, 6, 8, 12, 14, 16, 18, 22]
        else:
            bases = [100, 200, 300, 400, 500, 600, 800]
            pcts = [5, 8, 10, 12, 15, 20, 25]

        # Ensure clean integer NI: base*pct must be divisible by 100
        for _ in range(20):
            base = random.choice(bases)
            pct = random.choice(pcts)
            if (base * pct) % 100 == 0:
                break
        ni = int(base * pct / 100)

        if ratio_type == 'roe':
            eq = f"Net income ${ni}M, equity ${base}M. ROE %?"
            expl = f"ROE = NI/Equity = {ni}/{base} = {pct}%"
        else:
            eq = f"Net income ${ni}M, assets ${base}M. ROA %?"
            expl = f"ROA = NI/Assets = {ni}/{base} = {pct}%"
        return eq, pct, 0, expl

    @staticmethod
    def _liquidity_ratio(difficulty):
        """Current ratio, D/E ratio, or quick ratio."""
        ratio_type = random.choice(['current', 'de', 'quick'])

        # Generate clean ratios (multiples of 0.5 for easy, 0.1 for hard)
        if difficulty == 'easy':
            target_ratios = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        elif difficulty == 'hard':
            target_ratios = [0.6, 0.8, 1.2, 1.3, 1.5, 1.7, 1.8, 2.2, 2.5, 3.0]
        else:
            target_ratios = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]

        denominators = [50, 80, 100, 120, 150, 160, 200, 250, 300, 400, 500]
        if difficulty == 'easy':
            denominators = [100, 200, 500]

        target = random.choice(target_ratios)
        denom = random.choice(denominators)
        numer = round(denom * target)

        if ratio_type == 'current':
            eq = f"Current assets ${numer}M, liabilities ${denom}M. Current ratio?"
            answer = target
            tol = 0.05
            expl = f"Current ratio = CA/CL = {numer}/{denom} = {target}"
        elif ratio_type == 'de':
            eq = f"Debt ${numer}M, equity ${denom}M. D/E ratio?"
            answer = target
            tol = 0.05
            expl = f"D/E = Debt/Equity = {numer}/{denom} = {target}"
        else:
            # Quick ratio: split numerator into cash + receivables
            cash = random.randint(int(numer * 0.3), int(numer * 0.7))
            ar = numer - cash
            eq = f"Cash ${cash}M, receivables ${ar}M, CL ${denom}M. Quick ratio?"
            answer = target
            tol = 0.05
            expl = f"Quick ratio = (Cash + AR) / CL\n= ({cash} + {ar}) / {denom} = {numer}/{denom} = {target}"
        return eq, answer, tol, expl

    # ── Category D: Valuation Shortcuts ───────────────────────────────

    @staticmethod
    def _earnings_yield(difficulty):
        """Earnings yield from P/E or P/E from yield."""
        if random.choice([True, False]):
            # P/E → earnings yield
            pe_values = [5, 8, 10, 12.5, 15, 20, 25, 50]
            if difficulty == 'easy':
                pe_values = [5, 10, 20, 25, 50]
            pe = random.choice(pe_values)
            answer = round(100 / pe, 1)
            eq = f"P/E is {pe}. Earnings yield %?"
            tol = 0.1
            expl = f"Earnings yield = 1/PE = 100/{pe} = {answer}%"
        else:
            # Yield → P/E
            yields = [2, 4, 5, 8, 10, 12.5, 20]
            if difficulty == 'easy':
                yields = [2, 4, 5, 10, 20]
            y = random.choice(yields)
            answer = round(100 / y, 1)
            eq = f"Earnings yield {y}%. What P/E?"
            tol = 0.1
            expl = f"P/E = 1/yield = 100/{y} = {answer}"
        return eq, answer, tol, expl

    @staticmethod
    def _peg_ratio(difficulty):
        """PEG = P/E ÷ growth rate."""
        if difficulty == 'easy':
            pes = [10, 15, 20, 25, 30]
            growths = [5, 10, 15, 20, 25, 30]
        elif difficulty == 'hard':
            pes = [8, 12, 14, 18, 22, 28, 35]
            growths = [7, 9, 12, 14, 16, 18, 22]
        else:
            pes = [10, 12, 15, 18, 20, 25, 30]
            growths = [5, 10, 12, 15, 20, 25]

        pe = random.choice(pes)
        g = random.choice(growths)
        answer = round(pe / g, 1)
        eq = f"P/E {pe}, EPS growth {g}%. PEG ratio?"
        expl = f"PEG = P/E / Growth = {pe} / {g} = {answer}"
        return eq, answer, 0.1, expl

    @staticmethod
    def _rule_of_20(difficulty):
        """Fair P/E = 20 - inflation."""
        inflations = [1, 2, 3, 4, 5, 6, 7, 8]
        if difficulty == 'easy':
            inflations = [2, 3, 4, 5]
        inf = random.choice(inflations)
        answer = 20 - inf
        eq = f"Inflation {inf}%. Fair P/E (Rule of 20)?"
        expl = f"Rule of 20: Fair P/E = 20 - Inflation\n= 20 - {inf} = {answer}"
        return eq, answer, 0, expl

    @staticmethod
    def _ev_ebitda(difficulty):
        """EV/EBITDA or stock price from P/E × EPS."""
        if random.choice([True, False]):
            # EV/EBITDA
            if difficulty == 'easy':
                evs = [100, 200, 300, 500, 900, 1000]
                ebitdas = [10, 20, 25, 50, 100]
            else:
                evs = [120, 180, 250, 350, 480, 600, 750, 900]
                ebitdas = [15, 20, 30, 40, 50, 60, 75, 100]
            ev = random.choice(evs)
            ebitda = random.choice([e for e in ebitdas if e < ev])
            if not ebitda:
                ebitda = random.choice(ebitdas)
            answer = round(ev / ebitda, 1)
            eq = f"EV ${ev}M, EBITDA ${ebitda}M. EV/EBITDA?"
            tol = 0.1
            expl = f"EV/EBITDA = {ev} / {ebitda} = {answer}"
        else:
            # Stock price = EPS × P/E
            eps_values = [2, 3, 4, 5, 6, 8, 10, 12]
            pe_values = [8, 10, 12, 15, 18, 20, 25]
            if difficulty == 'easy':
                eps_values = [2, 4, 5, 10]
                pe_values = [10, 12, 15, 20]
            eps = random.choice(eps_values)
            pe = random.choice(pe_values)
            answer = eps * pe
            eq = f"EPS ${eps}, P/E {pe}. Stock price $?"
            tol = 0
            expl = f"Stock price = EPS x P/E = {eps} x {pe} = ${answer}"
        return eq, answer, tol, expl

    # ── Category E: Gordon Growth / Perpetuity ────────────────────────

    @staticmethod
    def _gordon_growth(difficulty):
        """Gordon Growth Model: P = D/(r-g) or implied return."""
        if random.choice([True, False]):
            # Find fair price
            if difficulty == 'easy':
                divs = [2, 3, 4, 5, 6, 10]
                spreads = [(8, 3), (10, 5), (10, 2), (12, 4), (9, 3)]
            elif difficulty == 'hard':
                divs = [1.5, 2.5, 3, 4, 5, 7, 8]
                spreads = [(7, 2), (8, 3), (9, 4), (10, 3), (11, 5), (12, 4), (8, 5)]
            else:
                divs = [2, 3, 4, 5, 6, 8]
                spreads = [(8, 3), (9, 4), (10, 5), (10, 2), (12, 4), (15, 5)]
            div = random.choice(divs)
            r, g = random.choice(spreads)
            spread = (r - g) / 100
            answer = round(div / spread)
            eq = f"Div ${div}, req return {r}%, growth {g}%. Fair price $?"
            tol = 2 if difficulty != 'easy' else 0
            spread_pct = r - g
            expl = f"GGM: Price = Div / (r - g)\n= {div} / ({r}% - {g}%) = {div} / {spread_pct}%\n= {div} / {spread} = ${answer}"
        else:
            # Implied return = D/P + g
            prices = [25, 40, 50, 60, 80, 100]
            divs_for_price = {25: [1, 2], 40: [2, 3], 50: [2, 3, 4], 60: [3, 4], 80: [4, 5], 100: [4, 5, 6]}
            growths = [2, 3, 4, 5]
            p = random.choice(prices)
            d = random.choice(divs_for_price.get(p, [2]))
            g = random.choice(growths)
            div_yield = round(d / p * 100, 1)
            answer = round(d / p * 100 + g, 1)
            eq = f"Stock ${p}, div ${d}, growth {g}%. Implied return %?"
            tol = 0.5
            expl = f"Implied return = Div yield + Growth\n= ({d}/{p} x 100) + {g}%\n= {div_yield}% + {g}% = {answer}%"
        return eq, answer, tol, expl

    @staticmethod
    def _perpetuity(difficulty):
        """Perpetuity or growing perpetuity: V = CF/r or CF/(r-g)."""
        if random.choice([True, False]):
            # Simple perpetuity
            cfs = [5, 10, 15, 20, 25, 50]
            rates = [2, 4, 5, 8, 10, 12, 20, 25]
            if difficulty == 'easy':
                rates = [5, 10, 20, 25]
            cf = random.choice(cfs)
            r = random.choice(rates)
            answer = round(cf / (r / 100))
            eq = f"${cf}M FCF forever, discount {r}%. Value $M?"
            tol = 0
            expl = f"Perpetuity = CF / r\n= {cf} / {r}% = {cf} / {r/100} = ${answer}M"
        else:
            # Growing perpetuity
            cfs = [5, 10, 20, 50]
            spreads = [(8, 3), (7, 2), (10, 5), (9, 4), (10, 2), (12, 4)]
            if difficulty == 'easy':
                spreads = [(10, 5), (10, 2), (8, 3)]
            cf = random.choice(cfs)
            r, g = random.choice(spreads)
            spread = (r - g) / 100
            answer = round(cf / spread)
            eq = f"${cf}M FCF, growth {g}%, WACC {r}%. Terminal value $M?"
            tol = 5 if difficulty == 'hard' else 0
            spread_pct = r - g
            expl = f"Growing perpetuity = CF / (r - g)\n= {cf} / ({r}% - {g}%) = {cf} / {spread_pct}%\n= {cf} / {spread} = ${answer}M"
        return eq, answer, tol, expl

    # ── Category F: DCF / NPV Approximation ───────────────────────────

    @staticmethod
    def _terminal_value(difficulty):
        """Terminal value = FCF/(WACC - g)."""
        if difficulty == 'easy':
            fcfs = [10, 20, 50, 100]
            spreads = [(8, 3), (10, 5), (10, 2)]
        elif difficulty == 'hard':
            fcfs = [15, 25, 35, 50, 75, 85]
            spreads = [(7, 2), (8, 3), (9, 4), (10, 3), (11, 4), (12, 5)]
        else:
            fcfs = [10, 20, 30, 50, 100]
            spreads = [(8, 3), (9, 4), (10, 5), (10, 2), (12, 4)]

        fcf = random.choice(fcfs)
        wacc, g = random.choice(spreads)
        spread = (wacc - g) / 100
        answer = round(fcf / spread)
        eq = f"FCF ${fcf}M, growth {g}%, WACC {wacc}%. Terminal value $M?"
        tol = max(10, round(answer * 0.03)) if difficulty == 'hard' else 0
        spread_pct = wacc - g
        expl = f"Terminal value = FCF / (WACC - g)\n= {fcf} / ({wacc}% - {g}%) = {fcf} / {spread_pct}%\n= {fcf} / {spread} = ${answer}M"
        return eq, answer, tol, expl

    @staticmethod
    def _pv_single_cashflow(difficulty):
        """PV of a single future cash flow: CF/(1+r)^t."""
        if difficulty == 'easy':
            cfs = [1000, 2000, 5000, 10000]
            rates = [5, 10]
            years = [1, 2]
        elif difficulty == 'hard':
            cfs = [1000, 2500, 5000, 10000, 50000]
            rates = [6, 7, 8, 10, 12]
            years = [2, 3, 4, 5]
        else:
            cfs = [1000, 2000, 5000, 10000]
            rates = [5, 8, 10, 12]
            years = [2, 3]

        cf = random.choice(cfs)
        r = random.choice(rates)
        t = random.choice(years)
        factor = (1 + r / 100) ** t
        answer = round(cf / factor)
        eq = f"${cf:,} in {t} yr, discount {r}%. PV $?"
        tol = max(5, round(answer * 0.03)) if t >= 3 else 0
        expl = f"PV = CF / (1 + r)^t\n= {cf:,} / (1.{r:02d})^{t} = {cf:,} / {factor:.4f}\n= ${answer:,}"
        return eq, answer, tol, expl

    @staticmethod
    def _cagr_approximation(difficulty):
        """CAGR via Rule of 72/114: if doubled in N years, CAGR ≈ 72/N."""
        variant = random.choice(['double', 'triple'])
        if variant == 'double':
            years_opts = [4, 6, 8, 9, 12, 18, 24]
            if difficulty == 'easy':
                years_opts = [6, 8, 9, 12]
            y = random.choice(years_opts)
            answer = round(72 / y, 1)
            eq = f"Investment doubled in {y} years. Approx CAGR %?"
            expl = f"Doubled → Rule of 72\nCAGR ≈ 72 / {y} = {answer}%"
        else:
            years_opts = [6, 12, 19, 38]
            if difficulty == 'easy':
                years_opts = [6, 19, 38]
            y = random.choice(years_opts)
            answer = round(114 / y, 1)
            eq = f"Revenue tripled in {y} years. Approx CAGR %?"
            expl = f"Tripled → Rule of 114\nCAGR ≈ 114 / {y} = {answer}%"
        return eq, answer, 1, expl

    # ── Category G: Bond / Duration ───────────────────────────────────

    @staticmethod
    def _duration_impact(difficulty):
        """Bond price change ≈ -Duration × Δyield."""
        if difficulty == 'easy':
            durations = [2, 3, 5, 7, 10]
            yield_changes = [1]
        elif difficulty == 'hard':
            durations = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15]
            yield_changes = [0.5, 1, 1.5, 2]
        else:
            durations = [3, 5, 7, 10]
            yield_changes = [1, 2]

        dur = random.choice(durations)
        dy = random.choice(yield_changes)
        direction = random.choice(['rises', 'drops'])

        if direction == 'rises':
            answer = round(-dur * dy, 1)
            eq = f"Duration {dur}, yield rises {dy}%. Price change %?"
            expl = f"Price change ≈ -Duration x Δyield\n= -{dur} x {dy}% = {answer}%"
        else:
            answer = round(dur * dy, 1)
            eq = f"Duration {dur}, yield drops {dy}%. Price change %?"
            expl = f"Price change ≈ -Duration x Δyield\n= -{dur} x (-{dy}%) = +{answer}%"
        return eq, answer, 0.5, expl

    @staticmethod
    def _bond_yield(difficulty):
        """Current yield = coupon/price, or coupon from rate."""
        if random.choice([True, False]):
            # Current yield
            pars = [1000]
            coupon_rates = [3, 4, 5, 6, 7, 8]
            if difficulty == 'easy':
                prices = [1000]
            else:
                prices = [900, 950, 980, 1000, 1020, 1050, 1100]

            par = random.choice(pars)
            cr = random.choice(coupon_rates)
            coupon = par * cr / 100
            price = random.choice(prices)
            answer = round(coupon / price * 100, 1)
            eq = f"Bond price ${price}, coupon ${int(coupon)}. Current yield %?"
            tol = 0.2
            expl = f"Current yield = Coupon / Price x 100\n= {int(coupon)} / {price} x 100 = {answer}%"
        else:
            # Annual coupon from rate
            par = 1000
            cr = random.choice([3, 4, 5, 6, 7, 8, 10])
            answer = par * cr / 100
            eq = f"Par $1,000, coupon rate {cr}%. Annual coupon $?"
            tol = 0
            expl = f"Annual coupon = Par x Rate\n= 1,000 x {cr}% = ${int(answer)}"
        return eq, answer, tol, expl

    # ── Category H: Break-Even Analysis ───────────────────────────────

    @staticmethod
    def _breakeven(difficulty):
        """Break-even units, revenue, or contribution margin."""
        variant = random.choice(['units', 'revenue', 'cm'])

        if variant == 'units':
            if difficulty == 'easy':
                fixed_costs = [10000, 20000, 50000, 100000]
                prices = [20, 25, 50, 100]
                var_costs_pct = [0.4, 0.5, 0.6]
            elif difficulty == 'hard':
                fixed_costs = [30000, 75000, 120000, 200000, 500000]
                prices = [15, 30, 45, 60, 80, 120]
                var_costs_pct = [0.3, 0.4, 0.5, 0.6, 0.7]
            else:
                fixed_costs = [20000, 50000, 100000, 200000]
                prices = [20, 40, 50, 80, 100]
                var_costs_pct = [0.4, 0.5, 0.6]

            fc = random.choice(fixed_costs)
            price = random.choice(prices)
            vc = round(price * random.choice(var_costs_pct))
            cm = price - vc
            if cm <= 0:
                cm = 10
                vc = price - cm
            answer = round(fc / cm)
            eq = f"Fixed ${fc:,}, price ${price}, var cost ${int(vc)}. BE units?"
            tol = 0
            expl = f"CM per unit = Price - VC = {price} - {int(vc)} = {cm}\nBE units = Fixed / CM = {fc:,} / {cm} = {answer:,}"

        elif variant == 'revenue':
            if difficulty == 'easy':
                fixed_costs = [30, 60, 90, 120]
                cm_pcts = [20, 25, 30, 40, 50]
            else:
                fixed_costs = [45, 60, 75, 90, 120, 150, 200]
                cm_pcts = [15, 20, 25, 30, 40, 50, 60]
            fc = random.choice(fixed_costs)
            cm_pct = random.choice(cm_pcts)
            answer = round(fc / (cm_pct / 100))
            eq = f"Fixed ${fc}K, contribution margin {cm_pct}%. BE revenue $K?"
            tol = 0
            expl = f"BE revenue = Fixed / CM%\n= {fc} / {cm_pct}% = {fc} / {cm_pct/100} = ${answer}K"

        else:
            # Contribution margin %
            prices = [20, 40, 50, 60, 80, 100, 120, 150]
            cm_pcts = [20, 25, 30, 35, 40, 50, 60]
            price = random.choice(prices)
            pct = random.choice(cm_pcts)
            vc = round(price * (1 - pct / 100))
            eq = f"Price ${price}, variable cost ${vc}. CM %?"
            answer = pct
            tol = 0
            cm = price - vc
            expl = f"CM = Price - VC = {price} - {vc} = {cm}\nCM% = {cm}/{price} x 100 = {pct}%"

        return eq, answer, tol, expl

    # ── Main generation interface ─────────────────────────────────────

    CATEGORY_MAP = {
        'rules': ['rule_of_72', 'rule_of_114', 'rule_of_144'],
        'interest': ['simple_interest', 'compound_interest'],
        'ratios': ['margin', 'return_ratio', 'liquidity_ratio'],
        'valuation': ['earnings_yield', 'peg_ratio', 'rule_of_20', 'ev_ebitda'],
        'ggm': ['gordon_growth', 'perpetuity'],
        'dcf': ['terminal_value', 'pv_single', 'cagr'],
        'bonds': ['duration_impact', 'bond_yield'],
        'breakeven': ['breakeven'],
    }

    METHOD_MAP = {
        'rule_of_72': '_rule_of_72',
        'rule_of_114': '_rule_of_114',
        'rule_of_144': '_rule_of_144',
        'simple_interest': '_simple_interest',
        'compound_interest': '_compound_interest',
        'margin': '_margin_problem',
        'return_ratio': '_return_ratio',
        'liquidity_ratio': '_liquidity_ratio',
        'earnings_yield': '_earnings_yield',
        'peg_ratio': '_peg_ratio',
        'rule_of_20': '_rule_of_20',
        'ev_ebitda': '_ev_ebitda',
        'gordon_growth': '_gordon_growth',
        'perpetuity': '_perpetuity',
        'terminal_value': '_terminal_value',
        'pv_single': '_pv_single_cashflow',
        'cagr': '_cagr_approximation',
        'duration_impact': '_duration_impact',
        'bond_yield': '_bond_yield',
        'breakeven': '_breakeven',
    }

    TYPE_TO_CATEGORY = {
        'rule_of_72': 'rules', 'rule_of_114': 'rules', 'rule_of_144': 'rules',
        'simple_interest': 'interest', 'compound_interest': 'interest',
        'margin': 'ratios', 'return_ratio': 'ratios', 'liquidity_ratio': 'ratios',
        'earnings_yield': 'valuation', 'peg_ratio': 'valuation',
        'rule_of_20': 'valuation', 'ev_ebitda': 'valuation',
        'gordon_growth': 'ggm', 'perpetuity': 'ggm',
        'terminal_value': 'dcf', 'pv_single': 'dcf', 'cagr': 'dcf',
        'duration_impact': 'bonds', 'bond_yield': 'bonds',
        'breakeven': 'breakeven',
    }

    @classmethod
    def generate(cls, categories=None, difficulty='normal', problem_type=None):
        """Generate a single financial problem from selected categories."""
        if categories is None:
            categories = ['rules']

        if problem_type is None:
            # Build pool of problem types from selected categories
            pool = []
            for cat in categories:
                pool.extend(cls.CATEGORY_MAP.get(cat, []))
            if not pool:
                pool = cls.CATEGORY_MAP['rules']
            problem_type = random.choice(pool)

        method_name = cls.METHOD_MAP[problem_type]
        method = getattr(cls, method_name)
        result = method(difficulty)
        equation, answer, tolerance = result[0], result[1], result[2]
        explanation = result[3] if len(result) > 3 else ''

        # Round answer for clean display
        if isinstance(answer, float) and answer == int(answer):
            answer = int(answer)
        elif isinstance(answer, float):
            answer = round(answer, 2)

        category = cls.TYPE_TO_CATEGORY.get(problem_type, categories[0] if categories else 'rules')

        return {
            'id': str(uuid.uuid4()),
            'equation': equation,
            'answer': answer,
            'tolerance': tolerance,
            'difficulty_rating': 0,
            'explanation': explanation,
            'tags': [category, problem_type],
        }

    @classmethod
    def generate_targeted(cls, focus_tags, categories, difficulty):
        """Generate a problem targeting a specific weakness tag."""
        available_types = []
        for cat in categories:
            available_types.extend(cls.CATEGORY_MAP.get(cat, []))

        for tag in focus_tags:
            if tag in cls.METHOD_MAP and tag in available_types:
                return cls.generate(categories, difficulty, problem_type=tag)

        # Fallback: focus tag not in user's selected categories
        return cls.generate(categories, difficulty)

    @classmethod
    def generate_batch(cls, count, options, focus_tags=None):
        """Generate a batch of financial problems."""
        categories = options.get('categories', ['rules'])
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
