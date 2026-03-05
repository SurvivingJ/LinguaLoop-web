"""Loyalty offer screenshot parsing via OpenRouter (GPT-4 Vision)."""

import base64
import json
import logging
import re

from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)


def _get_client():
    return OpenAI(
        base_url=Config.OPENROUTER_BASE_URL,
        api_key=Config.OPENROUTER_API_KEY,
    )


def build_extraction_prompt():
    """System prompt for structured offer extraction."""
    return """You are an expert at reading Australian supermarket loyalty program screenshots.

Extract all offers visible in the screenshot. Return a JSON array where each offer has:
- "program": "flybuys" or "everyday_rewards"
- "offer_type": one of "multiplier", "threshold", "category_bonus", "product_specific"
- "title": the offer headline text
- "details": object with type-specific fields:
  - For multiplier: {"multiplier": 10, "category": "Fresh Produce"}
  - For threshold: {"spend_threshold": 100, "bonus_points": 3000}
  - For category_bonus: {"category": "Cadbury", "bonus_points": 2000}
  - For product_specific: {"product": "Coca Cola 24pk", "bonus_points": 500}
- "expiry_date": "YYYY-MM-DD" (estimate from visible text, or null if not shown)

Return ONLY valid JSON. No markdown fences, no explanation."""


def extract_offers_from_screenshots(image_files):
    """Parse uploaded screenshot files to extract loyalty offers.

    Args:
        image_files: list of Flask FileStorage objects
    Returns:
        list of structured offer dicts
    """
    if not Config.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set, cannot parse screenshots")
        return []

    client = _get_client()
    all_offers = []

    for file in image_files:
        try:
            image_bytes = file.read()
            b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Detect mime type
            mime = 'image/jpeg'
            if file.filename and file.filename.lower().endswith('.png'):
                mime = 'image/png'

            response = client.chat.completions.create(
                model=Config.OPENROUTER_DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": build_extraction_prompt()},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                    ]}
                ],
                max_tokens=2000,
            )

            text = response.choices[0].message.content
            offers = parse_vision_response(text)
            all_offers.extend(offers)

        except Exception as e:
            logger.error(f"Failed to parse screenshot {file.filename}: {e}")

    return all_offers


def parse_vision_response(response_text):
    """Parse the LLM response text into structured offer objects."""
    text = response_text.strip()

    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        offers = json.loads(text)
        if isinstance(offers, dict):
            offers = [offers]
        if not isinstance(offers, list):
            return []

        # Validate required fields
        valid = []
        for offer in offers:
            if all(k in offer for k in ('program', 'offer_type', 'title')):
                offer.setdefault('details', {})
                offer.setdefault('expiry_date', None)
                valid.append(offer)

        return valid
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse vision response as JSON: {text[:200]}")
        return []


def classify_offer(title, description=''):
    """Regex-based fallback classifier for offer type detection."""
    combined = f"{title} {description}".lower()

    # Multiplier: "10x points on..."
    match = re.search(r'(\d+)x\s+(?:bonus\s+)?points?\s+(?:on\s+)?(.+)', combined)
    if match:
        return 'multiplier', {
            'multiplier': int(match.group(1)),
            'category': match.group(2).strip().title(),
        }

    # Threshold: "spend $X earn Y points"
    match = re.search(r'spend\s+\$(\d+).*?(?:earn|get)\s+(\d+)\s*points', combined)
    if match:
        return 'threshold', {
            'spend_threshold': int(match.group(1)),
            'bonus_points': int(match.group(2)),
        }

    # Category bonus: "X points on category"
    match = re.search(r'(\d+)\s*(?:bonus\s+)?points?\s+(?:on|when|for)\s+(.+)', combined)
    if match:
        return 'category_bonus', {
            'category': match.group(2).strip().title(),
            'bonus_points': int(match.group(1)),
        }

    return 'product_specific', {'description': title}


def calculate_offer_value(offer, spend_amount):
    """Convert point-based offers to dollar savings.

    Conversion rate: 2000 points = $10, or 0.5 cents per point.
    """
    rate = Config.POINTS_TO_DOLLAR_RATE
    offer_type = offer.get('offer_type', '')
    details = offer.get('details', {})

    if offer_type == 'multiplier':
        multiplier = details.get('multiplier', 1)
        # Extra points = (multiplier - 1) × base points
        # Base points ~ spend / $1 per point (Coles) or similar
        return (multiplier - 1) * spend_amount * rate

    elif offer_type == 'threshold':
        threshold = details.get('spend_threshold', 0)
        bonus = details.get('bonus_points', 0)
        if spend_amount >= threshold:
            return bonus * rate
        return 0

    elif offer_type == 'category_bonus':
        bonus = details.get('bonus_points', 0)
        return bonus * rate

    elif offer_type == 'product_specific':
        bonus = details.get('bonus_points', 0)
        return bonus * rate

    return 0
