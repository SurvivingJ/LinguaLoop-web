# routes/flashcards.py
"""Flashcard routes — SRS review, due cards, stats."""

from flask import Blueprint, request, current_app, g, render_template
from datetime import date, datetime
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from services.supabase_factory import get_supabase_admin
from services.vocabulary.fsrs import CardState, schedule_review
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from utils.responses import ApiResponse, api_success, bad_request, not_found, server_error

logger = logging.getLogger(__name__)
flashcards_bp = Blueprint("flashcards", __name__)

# FSRS rating constants
GOOD = 3


@flashcards_bp.route('/page')
@supabase_jwt_required
def flashcard_page() -> str:
    """Render the flashcard review page."""
    return render_template('flashcards.html')


@flashcards_bp.route('/due', methods=['GET'])
@supabase_jwt_required
def get_due_cards() -> ApiResponse:
    """Fetch all due flashcards for today.

    Query params:
        language_id: required
    """
    try:
        current_user_id = g.current_user_id

        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        db = get_supabase_admin()
        today = date.today().isoformat()

        response = db.table('user_flashcards') \
            .select(
                'id, sense_id, stability, difficulty, due_date, last_review, '
                'reps, lapses, state, example_sentence, audio_url, '
                'dim_word_senses(id, definition, pronunciation, example_sentence, '
                '  dim_vocabulary(lemma, language_id, frequency_rank))'
            ) \
            .eq('user_id', current_user_id) \
            .eq('language_id', language_id) \
            .or_(f'due_date.lte.{today},state.eq.new') \
            .order('due_date') \
            .execute()

        cards = []
        for row in (response.data or []):
            sense = row.get('dim_word_senses') or {}
            vocab = sense.get('dim_vocabulary') or {}
            cards.append({
                'card_id': row['id'],
                'sense_id': row['sense_id'],
                'lemma': vocab.get('lemma', ''),
                'definition': sense.get('definition', ''),
                'pronunciation': sense.get('pronunciation', ''),
                'example_sentence': row.get('example_sentence') or sense.get('example_sentence', ''),
                'audio_url': row.get('audio_url'),
                'state': row['state'],
                'reps': row['reps'],
                'due_date': row.get('due_date'),
            })

        return api_success({'cards': cards, 'total': len(cards)})

    except Exception as e:
        current_app.logger.error(f"Get due cards error: {e}")
        return server_error("Failed to fetch flashcards")


@flashcards_bp.route('/review', methods=['POST'])
@supabase_jwt_required
def submit_review() -> ApiResponse:
    """Submit a flashcard review rating.

    Accepts:
        {"card_id": 123, "rating": 3}  // 1=again, 2=hard, 3=good, 4=easy
    """
    try:
        current_user_id = g.current_user_id

        data = request.get_json() or {}
        card_id = data.get('card_id')
        rating = data.get('rating')

        if not card_id or rating not in (1, 2, 3, 4):
            return bad_request("card_id and valid rating (1-4) required")

        db = get_supabase_admin()

        card_resp = db.table('user_flashcards') \
            .select('id, sense_id, language_id, stability, difficulty, due_date, '
                    'last_review, reps, lapses, state') \
            .eq('id', card_id) \
            .eq('user_id', current_user_id) \
            .single() \
            .execute()

        if not card_resp.data:
            return not_found("Card not found")

        row = card_resp.data

        last_review = None
        if row.get('last_review'):
            last_review = datetime.fromisoformat(row['last_review'].replace('Z', '+00:00')).date()

        card = CardState(
            stability=row.get('stability', 0),
            difficulty=row.get('difficulty', 0.3),
            due_date=date.fromisoformat(row['due_date']) if row.get('due_date') else None,
            last_review=last_review,
            reps=row.get('reps', 0),
            lapses=row.get('lapses', 0),
            state=row.get('state', 'new'),
        )

        new_card = schedule_review(card, rating)

        update_data = {
            'stability': new_card.stability,
            'difficulty': new_card.difficulty,
            'due_date': new_card.due_date.isoformat() if new_card.due_date else None,
            'last_review': date.today().isoformat(),
            'reps': new_card.reps,
            'lapses': new_card.lapses,
            'state': new_card.state,
            'updated_at': 'now()',
        }

        db.table('user_flashcards') \
            .update(update_data) \
            .eq('id', card_id) \
            .execute()

        # Also update BKT — treat good/easy as correct, again as wrong
        knowledge_svc = VocabularyKnowledgeService(db)
        is_correct = rating >= GOOD
        knowledge_svc.update_from_word_test(
            user_id=current_user_id,
            sense_id=row['sense_id'],
            is_correct=is_correct,
            language_id=row['language_id'],
            exercise_type='text_flashcard',
        )

        return api_success({
            'next_due': new_card.due_date.isoformat() if new_card.due_date else None,
            'new_state': new_card.state,
            'stability': round(new_card.stability, 2),
        })

    except Exception as e:
        current_app.logger.error(f"Flashcard review error: {e}")
        return server_error("Failed to submit review")


@flashcards_bp.route('/stats', methods=['GET'])
@supabase_jwt_required
def get_stats() -> ApiResponse:
    """Get flashcard statistics for the user."""
    try:
        current_user_id = g.current_user_id

        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        db = get_supabase_admin()
        today = date.today().isoformat()

        all_resp = db.table('user_flashcards') \
            .select('state', count='exact') \
            .eq('user_id', current_user_id) \
            .eq('language_id', language_id) \
            .execute()

        by_state = {}
        for r in (all_resp.data or []):
            s = r['state']
            by_state[s] = by_state.get(s, 0) + 1
        total = sum(by_state.values())

        new_count = by_state.get('new', 0)
        due_resp = db.table('user_flashcards') \
            .select('id', count='exact') \
            .eq('user_id', current_user_id) \
            .eq('language_id', language_id) \
            .neq('state', 'new') \
            .lte('due_date', today) \
            .execute()
        due_today = new_count + (due_resp.count or 0)

        return api_success({
            'stats': {
                'total_cards': total,
                'due_today': due_today,
                'by_state': by_state,
            }
        })

    except Exception as e:
        current_app.logger.error(f"Flashcard stats error: {e}")
        return server_error("Failed to fetch stats")


@flashcards_bp.route('/skip', methods=['POST'])
@supabase_jwt_required
def skip_card() -> ApiResponse:
    """Delete/archive a flashcard the user doesn't want."""
    try:
        current_user_id = g.current_user_id

        data = request.get_json() or {}
        card_id = data.get('card_id')

        if not card_id:
            return bad_request("card_id required")

        db = get_supabase_admin()
        db.table('user_flashcards') \
            .delete() \
            .eq('id', card_id) \
            .eq('user_id', current_user_id) \
            .execute()

        return api_success()

    except Exception as e:
        current_app.logger.error(f"Skip card error: {e}")
        return server_error("Failed to skip card")
