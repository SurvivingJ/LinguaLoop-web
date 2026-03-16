# routes/payments.py
"""Payment routes — token packages and Stripe payment intents."""

from flask import Blueprint, request, g
from flask_jwt_extended import get_jwt_identity
import stripe
import logging

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error
from models.requests import PaymentIntentRequest
from pydantic import ValidationError

logger = logging.getLogger(__name__)
payments_bp = Blueprint("payments", __name__)


@payments_bp.route('/token-packages', methods=['GET'])
def get_token_packages() -> ApiResponse:
    """Get available token packages"""
    return api_success({"packages": Config.TOKEN_PACKAGES})


@payments_bp.route('/create-intent', methods=['POST'])
@supabase_jwt_required
def create_payment_intent() -> ApiResponse:
    """Create Stripe PaymentIntent for token purchase"""
    try:
        if not stripe.api_key:
            return server_error("Payment system not configured")

        try:
            body = PaymentIntentRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return bad_request(e.errors()[0]['msg'])

        if body.package_id not in Config.TOKEN_PACKAGES:
            return bad_request("Invalid package")

        package = Config.TOKEN_PACKAGES[body.package_id]
        current_user_email = get_jwt_identity()

        intent = stripe.PaymentIntent.create(
            amount=package['price_cents'],
            currency='usd',
            metadata={
                'user_email': current_user_email,
                'package_id': body.package_id,
                'tokens': package['tokens']
            }
        )

        return api_success({
            "client_secret": intent.client_secret,
            "amount": package['price_cents'],
            "tokens": package['tokens'],
        })
    except Exception as e:
        logger.error(f"Payment intent error: {e}")
        return server_error("Failed to create payment intent")
