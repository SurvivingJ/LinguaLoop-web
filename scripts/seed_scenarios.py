#!/usr/bin/env python3
"""
Seed Scenarios via LLM

Generates conversation scenarios for all domains and languages using the
ScenarioBatchGenerator. Also provides CLI modes for reviewing unvalidated
scenarios and marking them as validated or rejected.

Usage:
  python -m scripts.seed_scenarios                              # Generate all (10 per domain, all languages)
  python -m scripts.seed_scenarios --language-id 2              # English only
  python -m scripts.seed_scenarios --language-id 2 --domain-id 3  # Single domain+language
  python -m scripts.seed_scenarios --target 5 --batch-size 5    # Custom counts

  python -m scripts.seed_scenarios --report                     # Coverage report
  python -m scripts.seed_scenarios --review --language-id 2     # List unvalidated
  python -m scripts.seed_scenarios --validate 14 15 16 17       # Mark as validated
  python -m scripts.seed_scenarios --reject 22 23               # Soft-delete (deactivate)
"""

import sys
import os
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Language ID to display name
LANG_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}


def print_coverage_report(gen, language_ids):
    """Print a formatted coverage report."""
    report = gen.get_coverage_report(language_ids=language_ids)

    for lang_id, lang_data in report['by_language'].items():
        print(f"\n{'='*60}")
        print(f"  {lang_data['language_name']} (language_id={lang_id})")
        print(f"  Total: {lang_data['total']}  |  Validated: {lang_data['validated']}  |  Ready: {'YES' if lang_data['ready'] else 'NO'}")
        print(f"{'='*60}")
        print(f"  {'Domain':<35} {'Total':>6} {'Valid':>6} {'Status':>8}")
        print(f"  {'-'*55}")

        for d in lang_data['domains']:
            status = 'OK' if d['ready'] else 'NEEDS'
            print(f"  {d['domain_name']:<35} {d['total']:>6} {d['validated']:>6} {status:>8}")

    print(f"\n  Overall ready for Stage 5: {'YES' if report['overall_ready'] else 'NO'}")


def print_review(gen, language_id, domain_id, limit):
    """Print unvalidated scenarios for review."""
    candidates = gen.get_validation_candidates(
        domain_id=domain_id,
        language_id=language_id,
        limit=limit,
    )

    if not candidates:
        print("No unvalidated scenarios found.")
        return

    print(f"\nUnvalidated scenarios ({len(candidates)} found):\n")
    for s in candidates:
        print(f"  ID: {s.id}  |  Domain: {s.domain_id}  |  Lang: {s.language_id}  |  Tier: {s.complexity_tier or '?'}")
        print(f"  Title: {s.title}")
        print(f"  Context: {s.context_description[:120]}...")
        goals = s.goals or {}
        print(f"  Goal A: {goals.get('persona_a', '?')[:80]}")
        print(f"  Goal B: {goals.get('persona_b', '?')[:80]}")
        if s.cultural_note:
            print(f"  Cultural: {s.cultural_note[:80]}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Seed conversation scenarios via LLM')
    parser.add_argument('--language-id', type=int, choices=[1, 2, 3],
                        help='Language ID (1=Chinese, 2=English, 3=Japanese)')
    parser.add_argument('--domain-id', type=int, help='Specific domain ID')
    parser.add_argument('--target', type=int, default=10,
                        help='Scenarios per domain per language (default: 10)')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Scenarios per LLM call (default: 5)')

    # Mode flags
    parser.add_argument('--report', action='store_true',
                        help='Print coverage report and exit')
    parser.add_argument('--review', action='store_true',
                        help='List unvalidated scenarios for review')
    parser.add_argument('--review-limit', type=int, default=50,
                        help='Max scenarios to show in review (default: 50)')
    parser.add_argument('--validate', nargs='+', type=int, metavar='ID',
                        help='Scenario IDs to mark as validated')
    parser.add_argument('--reject', nargs='+', type=int, metavar='ID',
                        help='Scenario IDs to deactivate (soft-delete)')
    parser.add_argument('--validate-all', action='store_true',
                        help='Validate all unvalidated active scenarios')

    args = parser.parse_args()

    # Initialize Supabase
    logger.info("Initializing Supabase...")
    SupabaseFactory.initialize()

    from services.conversation_generation.scenario_generator import ScenarioBatchGenerator
    gen = ScenarioBatchGenerator()

    language_ids = [args.language_id] if args.language_id else [1, 2, 3]

    # ---- Report mode ----
    if args.report:
        print_coverage_report(gen, language_ids)
        return

    # ---- Review mode ----
    if args.review:
        print_review(gen, args.language_id, args.domain_id, args.review_limit)
        return

    # ---- Validate-all mode ----
    if args.validate_all:
        candidates = gen.get_validation_candidates(
            domain_id=args.domain_id,
            language_id=args.language_id,
            limit=500,
        )
        if not candidates:
            print("No unvalidated scenarios found.")
            return
        ids = [s.id for s in candidates]
        count = gen.db.validate_scenarios(ids)
        print(f"Validated {count} scenario(s)")
        return

    # ---- Validate mode ----
    if args.validate:
        count = gen.db.validate_scenarios(args.validate)
        print(f"Validated {count} scenario(s): {args.validate}")
        return

    # ---- Reject mode ----
    if args.reject:
        count = gen.db.deactivate_scenarios(args.reject)
        print(f"Deactivated {count} scenario(s): {args.reject}")
        return

    # ---- Generation mode (default) ----
    if args.domain_id:
        if not args.language_id:
            parser.error("--domain-id requires --language-id")

        ids = gen.generate_for_domain(
            domain_id=args.domain_id,
            language_id=args.language_id,
            target_count=args.target,
            batch_size=args.batch_size,
        )
        logger.info("Generated %d scenarios for domain_id=%d, language_id=%d", len(ids), args.domain_id, args.language_id)
    else:
        summary = gen.generate_all(
            language_ids=language_ids,
            target_per_domain=args.target,
            batch_size=args.batch_size,
        )
        logger.info("Generation complete: %s", summary)

    # Print coverage after generation
    print("\n--- Post-generation coverage ---")
    gen.db.clear_caches()
    print_coverage_report(gen, language_ids)


if __name__ == '__main__':
    main()
