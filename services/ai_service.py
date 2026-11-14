import logging

logger = logging.getLogger(__name__)


class ModerationServiceError(RuntimeError):
    """Raised when content moderation cannot reach a verdict.

    The route layer surfaces this as HTTP 503 so callers can retry rather
    than silently treat unsafe content as safe. See CR-03 in
    wiki/reviews/code-review-2026-05-24.md.
    """


class AIService:
    """Content moderation over an OpenAI-compatible client."""

    def __init__(self, openai_client, config, prompt_service=None, use_openrouter=False):
        self.client = openai_client
        self.config = config
        self.use_openrouter = use_openrouter

    def moderate_content(self, content):
        """Check content safety using OpenAI's moderation API"""
        try:
            if not content or not content.strip():
                return {
                    'is_safe': False,
                    'flagged_categories': ['empty_content'],
                    'category_scores': {},
                    'error': 'No content provided'
                }

            response = self.client.moderations.create(input=content.strip())

            result = response.results[0]
            is_flagged = result.flagged

            flagged_categories = []
            if is_flagged:
                for category, flagged in result.categories.__dict__.items():
                    if flagged:
                        flagged_categories.append(category)

            category_scores = result.category_scores.__dict__

            return {
                'is_safe': not is_flagged,
                'flagged_categories': flagged_categories,
                'category_scores': category_scores,
                'error': None
            }

        except Exception as e:
            # CR-03: fail CLOSED. Raise so the caller surfaces 503 instead
            # of silently treating unsafe content as safe.
            logger.error("Content moderation error: %s", e, exc_info=True)
            raise ModerationServiceError(
                "Content moderation service unavailable"
            ) from e
