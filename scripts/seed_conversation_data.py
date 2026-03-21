#!/usr/bin/env python3
"""
Seed Conversation Generation Data

Seeds conversation_domains, personas, persona_pairs, and scenarios
for the conversation generation pipeline.

Run with: python -m scripts.seed_conversation_data
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
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


# ============================================================
# Seed Data
# ============================================================

DOMAINS = [
    {
        'domain_name': 'Football / Soccer',
        'description': 'Discussions about football matches, teams, players, and tactics.',
        'parent_domain': 'sports',
        'keywords': ['match', 'goal', 'team', 'player', 'manager', 'tactics', 'league', 'transfer'],
        'suitable_registers': ['informal', 'semi-formal'],
        'suitable_relationship_types': ['friends', 'colleagues', 'family'],
    },
    {
        'domain_name': 'Cooking & Recipes',
        'description': 'Conversations about cooking techniques, recipes, and food culture.',
        'parent_domain': 'food',
        'keywords': ['recipe', 'ingredient', 'technique', 'flavour', 'dish'],
        'suitable_registers': ['informal', 'semi-formal'],
        'suitable_relationship_types': ['family', 'friends', 'romantic_partners'],
    },
    {
        'domain_name': 'Healthcare & Medical',
        'description': 'Doctor-patient interactions, health discussions, medical appointments.',
        'parent_domain': 'professional',
        'keywords': ['symptom', 'treatment', 'diagnosis', 'medication', 'appointment'],
        'suitable_registers': ['formal', 'semi-formal'],
        'suitable_relationship_types': ['service', 'family'],
    },
    {
        'domain_name': 'Job Interviews',
        'description': 'Interview conversations about qualifications, experience, and roles.',
        'parent_domain': 'workplace',
        'keywords': ['experience', 'qualification', 'responsibility', 'salary', 'team'],
        'suitable_registers': ['formal'],
        'suitable_relationship_types': ['strangers', 'colleagues'],
    },
    {
        'domain_name': 'Travel & Tourism',
        'description': 'Planning trips, booking accommodation, travel experiences.',
        'parent_domain': 'daily_life',
        'keywords': ['booking', 'hotel', 'itinerary', 'transport', 'budget'],
        'suitable_registers': ['informal', 'semi-formal'],
        'suitable_relationship_types': ['friends', 'romantic_partners', 'family'],
    },
    {
        'domain_name': 'Buying / Renting Property',
        'description': 'Real estate discussions about apartments, leases, and property decisions.',
        'parent_domain': 'finance',
        'keywords': ['apartment', 'lease', 'deposit', 'landlord', 'mortgage', 'neighbourhood'],
        'suitable_registers': ['formal', 'semi-formal'],
        'suitable_relationship_types': ['service', 'romantic_partners', 'strangers'],
    },
    {
        'domain_name': 'Relationship & Domestic Conflict',
        'description': 'Arguments, compromises, and emotional discussions between partners or family.',
        'parent_domain': 'social',
        'keywords': ['argument', 'feelings', 'compromise', 'trust', 'apology'],
        'suitable_registers': ['informal'],
        'suitable_relationship_types': ['romantic_partners', 'family', 'friends'],
    },
    {
        'domain_name': 'Business Negotiation',
        'description': 'Contract negotiations, proposals, and business deal discussions.',
        'parent_domain': 'professional',
        'keywords': ['contract', 'terms', 'proposal', 'deadline', 'budget', 'agreement'],
        'suitable_registers': ['formal'],
        'suitable_relationship_types': ['colleagues', 'strangers'],
    },
    {
        'domain_name': 'Family Meals & Gatherings',
        'description': 'Dinner table conversations, holiday gatherings, family traditions.',
        'parent_domain': 'family',
        'keywords': ['food', 'tradition', 'conversation', 'memory', 'expectation'],
        'suitable_registers': ['informal'],
        'suitable_relationship_types': ['family'],
    },
    {
        'domain_name': 'Relationship Milestones',
        'description': 'Discussions about moving in together, marriage, commitment, future plans.',
        'parent_domain': 'social',
        'keywords': ['commitment', 'future', 'moving in', 'marriage', 'expectations'],
        'suitable_registers': ['informal'],
        'suitable_relationship_types': ['romantic_partners'],
    },
    {
        'domain_name': 'Career Decisions',
        'description': 'Weighing career changes, promotions, and professional opportunities.',
        'parent_domain': 'professional',
        'keywords': ['promotion', 'job change', 'salary', 'risk', 'opportunity', 'stability'],
        'suitable_registers': ['informal', 'semi-formal'],
        'suitable_relationship_types': ['friends', 'family', 'romantic_partners', 'colleagues'],
    },
    {
        'domain_name': 'Financial Disagreements',
        'description': 'Discussions about money, budgeting, spending habits, and financial priorities.',
        'parent_domain': 'finance',
        'keywords': ['budget', 'spending', 'saving', 'debt', 'investment', 'priorities'],
        'suitable_registers': ['informal'],
        'suitable_relationship_types': ['romantic_partners', 'family'],
    },
    {
        'domain_name': 'Friends Giving Advice',
        'description': 'Peers offering guidance, sharing opinions, supporting each other.',
        'parent_domain': 'social',
        'keywords': ['problem', 'advice', 'opinion', 'support', 'decision', 'worry'],
        'suitable_registers': ['informal'],
        'suitable_relationship_types': ['friends'],
    },
    {
        'domain_name': 'Customer Service Interactions',
        'description': 'Complaints, refund requests, and service resolution conversations.',
        'parent_domain': 'daily_life',
        'keywords': ['complaint', 'refund', 'policy', 'manager', 'resolution', 'receipt'],
        'suitable_registers': ['semi-formal', 'formal'],
        'suitable_relationship_types': ['service', 'strangers'],
    },
]


# Template-generated starter personas per language
# language_id: 1=Chinese, 2=English, 3=Japanese
PERSONAS = [
    # English personas
    {
        'name': 'Sarah Chen', 'language_id': 2, 'age': 34, 'gender': 'female',
        'nationality': 'British', 'occupation': 'Marketing Manager',
        'archetype': 'professional',
        'personality': {'traits': ['assertive', 'organized', 'empathetic'], 'speaking_style': 'direct but warm'},
        'register': 'semi-formal', 'expertise_domains': ['business', 'marketing', 'social media'],
        'relationship_types': ['colleagues', 'friends'],
        'system_prompt': 'You are Sarah Chen, a 34-year-old British marketing manager. You are assertive and well-organized, but also empathetic. You speak directly but warmly.',
        'generation_method': 'template',
    },
    {
        'name': 'Tom Williams', 'language_id': 2, 'age': 52, 'gender': 'male',
        'nationality': 'British', 'occupation': 'Secondary School Teacher',
        'archetype': 'academic',
        'personality': {'traits': ['patient', 'thoughtful', 'dry humour'], 'speaking_style': 'measured and articulate'},
        'register': 'semi-formal', 'expertise_domains': ['education', 'history', 'sports'],
        'relationship_types': ['colleagues', 'family', 'friends'],
        'system_prompt': 'You are Tom Williams, a 52-year-old British history teacher. You are patient and thoughtful with a dry sense of humour. You speak in a measured, articulate way.',
        'generation_method': 'template',
    },
    {
        'name': 'Priya Patel', 'language_id': 2, 'age': 26, 'gender': 'female',
        'nationality': 'British-Indian', 'occupation': 'Junior Doctor',
        'archetype': 'professional',
        'personality': {'traits': ['caring', 'overworked', 'optimistic'], 'speaking_style': 'warm but sometimes rushed'},
        'register': 'formal', 'expertise_domains': ['healthcare', 'science'],
        'relationship_types': ['service', 'colleagues', 'friends'],
        'system_prompt': 'You are Priya Patel, a 26-year-old junior doctor. You are caring and optimistic despite being overworked. Your speech is warm but can be rushed when stressed.',
        'generation_method': 'template',
    },
    {
        'name': 'Mike O\'Brien', 'language_id': 2, 'age': 45, 'gender': 'male',
        'nationality': 'Irish', 'occupation': 'Electrician',
        'archetype': 'service_worker',
        'personality': {'traits': ['friendly', 'opinionated', 'humorous'], 'speaking_style': 'casual and chatty'},
        'register': 'informal', 'expertise_domains': ['trades', 'sports', 'property'],
        'relationship_types': ['friends', 'family', 'service'],
        'system_prompt': 'You are Mike O\'Brien, a 45-year-old Irish electrician. You are friendly and opinionated with a great sense of humour. You speak casually and love a chat.',
        'generation_method': 'template',
    },
    # Chinese personas
    {
        'name': '张伟', 'language_id': 1, 'age': 38, 'gender': 'male',
        'nationality': 'Chinese', 'occupation': '软件工程师',
        'archetype': 'professional',
        'personality': {'traits': ['理性', '内敛', '负责'], 'speaking_style': '条理清晰，用词精准'},
        'register': 'semi-formal', 'expertise_domains': ['technology', 'business'],
        'relationship_types': ['colleagues', 'friends'],
        'system_prompt': '你是张伟，38岁的软件工程师。你理性内敛，说话条理清晰，用词精准。工作中认真负责。',
        'generation_method': 'template',
    },
    {
        'name': '李芳', 'language_id': 1, 'age': 55, 'gender': 'female',
        'nationality': 'Chinese', 'occupation': '退休教师',
        'archetype': 'elder',
        'personality': {'traits': ['慈祥', '唠叨', '关心家人'], 'speaking_style': '亲切但啰嗦'},
        'register': 'informal', 'expertise_domains': ['education', 'cooking', 'family'],
        'relationship_types': ['family', 'friends'],
        'system_prompt': '你是李芳，55岁的退休教师。你慈祥但有时唠叨，特别关心家人的生活。说话亲切自然。',
        'generation_method': 'template',
    },
    {
        'name': '王小明', 'language_id': 1, 'age': 24, 'gender': 'male',
        'nationality': 'Chinese', 'occupation': '大学生',
        'archetype': 'student',
        'personality': {'traits': ['活泼', '好奇', '有时冲动'], 'speaking_style': '随意，偶尔用网络用语'},
        'register': 'informal', 'expertise_domains': ['technology', 'gaming', 'social media'],
        'relationship_types': ['friends', 'family'],
        'system_prompt': '你是王小明，24岁的大学生。你性格活泼好奇，说话随意，偶尔会用网络流行语。',
        'generation_method': 'template',
    },
    {
        'name': '陈医生', 'language_id': 1, 'age': 42, 'gender': 'female',
        'nationality': 'Chinese', 'occupation': '内科医生',
        'archetype': 'professional',
        'personality': {'traits': ['专业', '耐心', '严谨'], 'speaking_style': '专业术语和通俗解释结合'},
        'register': 'formal', 'expertise_domains': ['healthcare', 'science'],
        'relationship_types': ['service', 'colleagues'],
        'system_prompt': '你是陈医生，42岁的内科医生。你专业严谨，对病人耐心。说话时会将专业术语用通俗易懂的方式解释。',
        'generation_method': 'template',
    },
    # Japanese personas
    {
        'name': '田中太郎', 'language_id': 3, 'age': 35, 'gender': 'male',
        'nationality': 'Japanese', 'occupation': '会社員',
        'archetype': 'professional',
        'personality': {'traits': ['真面目', '気配り', '控えめ'], 'speaking_style': '丁寧で礼儀正しい'},
        'register': 'formal', 'expertise_domains': ['business', 'finance'],
        'relationship_types': ['colleagues', 'strangers'],
        'system_prompt': 'あなたは田中太郎、35歳の会社員です。真面目で気配りができ、控えめな性格です。丁寧で礼儀正しい話し方をします。',
        'generation_method': 'template',
    },
    {
        'name': '佐藤花子', 'language_id': 3, 'age': 28, 'gender': 'female',
        'nationality': 'Japanese', 'occupation': 'カフェ店員',
        'archetype': 'service_worker',
        'personality': {'traits': ['明るい', '親切', 'おしゃべり'], 'speaking_style': 'カジュアルで親しみやすい'},
        'register': 'informal', 'expertise_domains': ['food', 'travel', 'fashion'],
        'relationship_types': ['friends', 'service'],
        'system_prompt': 'あなたは佐藤花子、28歳のカフェ店員です。明るくて親切、おしゃべり好きです。カジュアルで親しみやすい話し方をします。',
        'generation_method': 'template',
    },
    {
        'name': '山田教授', 'language_id': 3, 'age': 60, 'gender': 'male',
        'nationality': 'Japanese', 'occupation': '大学教授',
        'archetype': 'academic',
        'personality': {'traits': ['博識', '穏やか', '几帳面'], 'speaking_style': '格式ばった丁寧語'},
        'register': 'formal', 'expertise_domains': ['education', 'literature', 'history'],
        'relationship_types': ['colleagues', 'family'],
        'system_prompt': 'あなたは山田教授、60歳の大学教授です。博識で穏やかな性格。格式ばった丁寧な話し方をします。',
        'generation_method': 'template',
    },
    {
        'name': '鈴木美咲', 'language_id': 3, 'age': 22, 'gender': 'female',
        'nationality': 'Japanese', 'occupation': '大学生',
        'archetype': 'student',
        'personality': {'traits': ['元気', '好奇心旺盛', '少し天然'], 'speaking_style': 'くだけた若者言葉'},
        'register': 'informal', 'expertise_domains': ['social media', 'music', 'travel'],
        'relationship_types': ['friends', 'family'],
        'system_prompt': 'あなたは鈴木美咲、22歳の大学生です。元気で好奇心旺盛、少し天然ボケなところがあります。くだけた若者言葉で話します。',
        'generation_method': 'template',
    },
]


def seed_domains(db) -> int:
    """Seed conversation domains."""
    existing = db.table('conversation_domains').select('domain_name').execute()
    existing_names = {r['domain_name'] for r in existing.data or []}

    new_domains = [d for d in DOMAINS if d['domain_name'] not in existing_names]
    if not new_domains:
        logger.info("All domains already exist - skipping")
        return 0

    db.table('conversation_domains').insert(new_domains).execute()
    logger.info("Seeded %d conversation domains", len(new_domains))
    return len(new_domains)


def seed_personas(db) -> int:
    """Seed starter personas."""
    existing = db.table('personas').select('name, language_id').execute()
    existing_keys = {(r['name'], r['language_id']) for r in existing.data or []}

    new_personas = [
        p for p in PERSONAS
        if (p['name'], p['language_id']) not in existing_keys
    ]
    if not new_personas:
        logger.info("All personas already exist - skipping")
        return 0

    db.table('personas').insert(new_personas).execute()
    logger.info("Seeded %d personas", len(new_personas))
    return len(new_personas)


def seed_persona_pairs(db) -> int:
    """Create persona pairs within each language using the pairing engine."""
    personas = db.table('personas').select(
        'id, language_id, archetype, register, relationship_types, expertise_domains, age'
    ).eq('is_active', True).execute()

    if not personas.data:
        logger.warning("No personas found - cannot create pairs")
        return 0

    existing = db.table('persona_pairs').select('persona_a_id, persona_b_id').execute()
    existing_pairs = {(r['persona_a_id'], r['persona_b_id']) for r in existing.data or []}

    # Group by language
    by_lang = {}
    for p in personas.data:
        by_lang.setdefault(p['language_id'], []).append(p)

    new_pairs = []
    for lang_id, lang_personas in by_lang.items():
        for i, pa in enumerate(lang_personas):
            for pb in lang_personas[i + 1:]:
                if (pa['id'], pb['id']) in existing_pairs:
                    continue

                score, dynamic_label = pairing_score_pair(pa, pb)
                relationship = derive_relationship_type(pa, pb)
                suitable_domains = get_suitable_domains(pa, pb)

                new_pairs.append({
                    'persona_a_id': pa['id'],
                    'persona_b_id': pb['id'],
                    'compatibility_score': round(min(score, 1.0), 2),
                    'relationship_type': relationship,
                    'dynamic_label': dynamic_label,
                    'suitable_domains': suitable_domains,
                })

    if not new_pairs:
        logger.info("All persona pairs already exist - skipping")
        return 0

    db.table('persona_pairs').insert(new_pairs).execute()
    logger.info("Seeded %d persona pairs", len(new_pairs))
    return len(new_pairs)


def main():
    """Seed all conversation generation data."""
    logger.info("Initializing Supabase...")
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if not db:
        logger.error("Failed to get Supabase admin client")
        sys.exit(1)

    logger.info("Seeding conversation generation data...")

    domain_count = seed_domains(db)
    persona_count = seed_personas(db)
    pair_count = seed_persona_pairs(db)

    logger.info(
        "Seeding complete: %d domains, %d personas, %d pairs",
        domain_count, persona_count, pair_count,
    )


if __name__ == '__main__':
    main()
