#!/usr/bin/env python3
"""
Bulk Persona Seeder

Seeds the personas table with diverse characters across all 26 archetypes.
Uses template-based generation (fast, deterministic) and optionally LLM-based
generation (richer, more unique).

Run with: python -m scripts.seed_personas
Options:
    --languages 1,2,3    Comma-separated language IDs (default: 1,2,3)
    --llm                Enable LLM-based persona generation (2 per archetype)
    --per-archetype N    Template personas per archetype (default: 4)
    --dry-run            Generate but don't insert into database
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.conversation_generation.template_generator import TemplatePersonaGenerator
from services.conversation_generation.archetypes import ARCHETYPES
from services.conversation_generation.agents.persona_designer import PersonaDesigner
from services.conversation_generation.pairing import (
    score_pair as pairing_score_pair,
    derive_relationship_type,
    get_suitable_domains,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}


def parse_args():
    parser = argparse.ArgumentParser(description='Bulk persona seeder')
    parser.add_argument('--languages', default='1,2,3',
                        help='Comma-separated language IDs (default: 1,2,3)')
    parser.add_argument('--llm', action='store_true',
                        help='Enable LLM-based persona generation')
    parser.add_argument('--per-archetype', type=int, default=4,
                        help='Template personas per archetype (default: 4)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate but do not insert into database')
    return parser.parse_args()


def get_existing_persona_keys(db):
    """Get set of (name, language_id) for existing personas."""
    response = db.table('personas').select('name, language_id').execute()
    return {(r['name'], r['language_id']) for r in response.data or []}


def get_existing_pair_keys(db):
    """Get set of (persona_a_id, persona_b_id) for existing pairs."""
    response = db.table('persona_pairs').select('persona_a_id, persona_b_id').execute()
    return {(r['persona_a_id'], r['persona_b_id']) for r in response.data or []}


def generate_template_personas(language_id: int, per_archetype: int) -> list[dict]:
    """Generate template-based personas for a language."""
    generator = TemplatePersonaGenerator(language_id)
    return generator.generate_all_archetypes(per_archetype=per_archetype)


def generate_llm_personas(language_id: int, count_per_archetype: int = 2) -> list[dict]:
    """Generate LLM-based personas for a language."""
    designer = PersonaDesigner()
    language_name = LANGUAGE_NAMES[language_id]

    # Build a simple prompt template for archetype-constrained generation
    prompt_template = _get_llm_prompt_template(language_id)

    personas = []
    for archetype_key, archetype_info in ARCHETYPES.items():
        for i in range(count_per_archetype):
            try:
                persona = designer.design_persona_from_archetype(
                    archetype_key=archetype_key,
                    archetype_info=archetype_info,
                    language_id=language_id,
                    language_name=language_name,
                    prompt_template=prompt_template,
                )
                personas.append(persona)
            except Exception as exc:
                logger.error(
                    "Failed LLM persona %d/%d for %s (lang=%d): %s",
                    i + 1, count_per_archetype, archetype_key, language_id, exc,
                )

    logger.info("Generated %d LLM personas for language %d", len(personas), language_id)
    return personas


def _get_llm_prompt_template(language_id: int) -> str:
    """Return a prompt template for LLM persona generation."""
    templates = {
        1: (
            '请为"{language_name}"语言学习对话系统创建一个角色。\n\n'
            '角色原型: {archetype_label} ({archetype_key})\n'
            '描述: {archetype_description}\n'
            '类别: {category}\n'
            '适合的语域: {typical_registers}\n'
            '适合的关系类型: {typical_relationship_types}\n'
            '年龄范围: {age_min}-{age_max}岁\n\n'
            '请返回一个JSON对象，包含以下字段:\n'
            '- name: 中文姓名\n'
            '- age: 年龄（在指定范围内）\n'
            '- gender: 性别 (male/female)\n'
            '- nationality: 国籍\n'
            '- occupation: 职业（用中文）\n'
            '- personality: {{"traits": ["特征1", "特征2", "特征3", "特征4"], "speaking_style": "说话风格描述"}}\n'
            '- system_prompt: 角色的系统提示词（用中文，描述这个角色的背景和说话方式）\n'
            '- expertise_domains: ["领域1", "领域2"]\n'
        ),
        2: (
            'Create a persona for a "{language_name}" language learning conversation system.\n\n'
            'Archetype: {archetype_label} ({archetype_key})\n'
            'Description: {archetype_description}\n'
            'Category: {category}\n'
            'Suitable registers: {typical_registers}\n'
            'Suitable relationship types: {typical_relationship_types}\n'
            'Age range: {age_min}-{age_max}\n\n'
            'Return a JSON object with these fields:\n'
            '- name: Full English name\n'
            '- age: Age (within specified range)\n'
            '- gender: male or female\n'
            '- nationality: Nationality\n'
            '- occupation: Occupation\n'
            '- personality: {{"traits": ["trait1", "trait2", "trait3", "trait4"], "speaking_style": "description of how they speak"}}\n'
            '- system_prompt: A system prompt describing this character (in English)\n'
            '- expertise_domains: ["domain1", "domain2"]\n'
        ),
        3: (
            '「{language_name}」の言語学習会話システム用のペルソナを作成してください。\n\n'
            'アーキタイプ: {archetype_label} ({archetype_key})\n'
            '説明: {archetype_description}\n'
            'カテゴリ: {category}\n'
            '適切なレジスター: {typical_registers}\n'
            '適切な関係タイプ: {typical_relationship_types}\n'
            '年齢範囲: {age_min}-{age_max}歳\n\n'
            '以下のフィールドを含むJSONオブジェクトを返してください:\n'
            '- name: 日本語のフルネーム\n'
            '- age: 年齢（指定範囲内）\n'
            '- gender: male または female\n'
            '- nationality: 国籍\n'
            '- occupation: 職業（日本語で）\n'
            '- personality: {{"traits": ["特徴1", "特徴2", "特徴3", "特徴4"], "speaking_style": "話し方の説明"}}\n'
            '- system_prompt: キャラクターのシステムプロンプト（日本語で）\n'
            '- expertise_domains: ["分野1", "分野2"]\n'
        ),
    }
    return templates[language_id]


def dedup_personas(personas: list[dict], existing_keys: set) -> list[dict]:
    """Remove personas whose (name, language_id) already exists."""
    unique = []
    seen = set(existing_keys)
    for p in personas:
        key = (p['name'], p['language_id'])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def generate_pairs(db, language_id: int, existing_pair_keys: set, min_compatibility: float = 0.45):
    """Generate persona pairs for a language using the pairing engine."""
    response = db.table('personas').select(
        'id, language_id, archetype, register, relationship_types, expertise_domains, age'
    ).eq('language_id', language_id).eq('is_active', True).execute()

    if not response.data or len(response.data) < 2:
        logger.warning("Not enough personas for language %d to create pairs", language_id)
        return 0

    personas = response.data
    new_pairs = []

    for i, pa in enumerate(personas):
        for pb in personas[i + 1:]:
            if (pa['id'], pb['id']) in existing_pair_keys:
                continue

            score, dynamic_label = pairing_score_pair(pa, pb)
            if score < min_compatibility:
                continue

            relationship = derive_relationship_type(pa, pb)
            suitable_domains = get_suitable_domains(pa, pb)

            new_pairs.append({
                'persona_a_id': pa['id'],
                'persona_b_id': pb['id'],
                'compatibility_score': round(score, 2),
                'relationship_type': relationship,
                'dynamic_label': dynamic_label,
                'suitable_domains': suitable_domains,
            })

    if not new_pairs:
        logger.info("No new pairs to create for language %d", language_id)
        return 0

    db.table('persona_pairs').insert(new_pairs).execute()
    logger.info("Created %d persona pairs for language %d", len(new_pairs), language_id)
    return len(new_pairs)


def main():
    args = parse_args()
    language_ids = [int(x) for x in args.languages.split(',')]
    use_llm = args.llm or os.getenv('CONV_GEN_SEED_LLM', 'false').lower() == 'true'

    logger.info("Initializing Supabase...")
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if not db:
        logger.error("Failed to get Supabase admin client")
        sys.exit(1)

    existing_keys = get_existing_persona_keys(db)
    existing_pair_keys = get_existing_pair_keys(db)

    total_inserted = 0
    total_pairs = 0

    for lang_id in language_ids:
        logger.info("=== Processing language %d (%s) ===",
                     lang_id, LANGUAGE_NAMES.get(lang_id, 'unknown'))

        # Template generation
        template_personas = generate_template_personas(lang_id, args.per_archetype)
        logger.info("Template generator produced %d personas", len(template_personas))

        # LLM generation (optional)
        llm_personas = []
        if use_llm:
            llm_personas = generate_llm_personas(lang_id, count_per_archetype=2)
            logger.info("LLM generator produced %d personas", len(llm_personas))

        # Combine and dedup
        all_personas = template_personas + llm_personas
        unique_personas = dedup_personas(all_personas, existing_keys)
        logger.info("After dedup: %d unique personas (from %d total)",
                     len(unique_personas), len(all_personas))

        if args.dry_run:
            logger.info("DRY RUN - skipping database insert for %d personas", len(unique_personas))
            for p in unique_personas[:5]:
                logger.info("  Sample: %s (%s, %s)", p['name'], p['archetype'], p['generation_method'])
            total_inserted += len(unique_personas)
            continue

        if unique_personas:
            db.table('personas').insert(unique_personas).execute()
            total_inserted += len(unique_personas)
            logger.info("Inserted %d personas for language %d", len(unique_personas), lang_id)

            # Update existing keys for next language dedup
            for p in unique_personas:
                existing_keys.add((p['name'], p['language_id']))

        # Generate pairs
        if not args.dry_run:
            pair_count = generate_pairs(db, lang_id, existing_pair_keys)
            total_pairs += pair_count

    logger.info("=" * 60)
    logger.info("Seeding complete: %d personas inserted, %d pairs created", total_inserted, total_pairs)
    if use_llm:
        logger.info("LLM generation was enabled")
    if args.dry_run:
        logger.info("DRY RUN - no data was written to database")


if __name__ == '__main__':
    main()
