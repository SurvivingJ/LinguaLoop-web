"""
EXPERIMENT 4: attempts-per-item structural blocker.

The never-re-served filter (quoted in docs/results-serving.md SS4, sourced
from migrations/task748_get_recommended_tests_vocab_aware.sql:349-353) means
an item can only accumulate a first-attempt from a user ONCE, ever. For an
item to reach DEFAULT_MIN_ATTEMPTS=20 (the live IRT calibrator's hard gate,
per the task's established findings), 20 DISTINCT users must each be routed
to that exact item.

This is a back-of-envelope order-of-magnitude calculation, not a queueing
simulation - see docs/results-serving.md SS4 for the caveats (uniform
routing is the OPTIMISTIC case; real ELO-band clustering makes it worse).
"""
from __future__ import annotations

MIN_ATTEMPTS = 20
POOL_SIZE_PER_TYPE = 15  # ~121-125 tests/language over 8 types (en/zh), ~59/8 for ja - recon SS6 defect #4
USER_COUNTS = [10, 100, 1000]


def days_to_floor(pool_size: int, n_users: int, min_attempts: int = MIN_ATTEMPTS,
                   items_per_user_per_day: float = 1.0) -> float:
    """Optimistic-uniform model: each active user attempts one NEW item in
    this (language, type) pool per day, spread uniformly across the pool.
    Expected attempts/item/day ~= n_users*items_per_user_per_day/pool_size.
    Days for ANY ONE item to reach min_attempts ~= min_attempts / that rate."""
    rate_per_item_per_day = (n_users * items_per_user_per_day) / pool_size
    if rate_per_item_per_day <= 0:
        return float("inf")
    return min_attempts / rate_per_item_per_day


if __name__ == "__main__":
    print(f"Pool size per (language, type): {POOL_SIZE_PER_TYPE} (order-of-magnitude, see recon SS6 defect #4)")
    print(f"Attempts needed for IRT calibration floor: {MIN_ATTEMPTS}\n")
    for u in USER_COUNTS:
        d = days_to_floor(POOL_SIZE_PER_TYPE, u)
        print(f"  {u:>5} daily active users -> ~{d:.1f} days (OPTIMISTIC uniform-routing case)")
    print("\nReal routing is ELO-band-clustered, not uniform (get_recommended_tests ranks by")
    print("|elo_diff|), so only the sub-population near an item's difficulty band ever gets")
    print("routed to it - realistic time-to-floor is a multiple of the optimistic number above,")
    print("not an upper bound estimated here (would require the real ability distribution).")
    print("\nCurrent real traffic: n=1 user has EVER taken a test (docs/recon-serving.md SS6 #10) -")
    print("at that rate the 20-attempt floor is not 'slow', it is unreached: 'never' is the")
    print("empirically correct answer today, independent of this model.")
