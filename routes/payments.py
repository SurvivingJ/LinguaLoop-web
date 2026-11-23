# routes/payments.py
"""Payment routes — token packages."""

import logging

from flask import Blueprint

from config import Config
from utils.responses import ApiResponse, api_success

logger = logging.getLogger(__name__)
payments_bp = Blueprint("payments", __name__)


@payments_bp.route('/token-packages', methods=['GET'])
def get_token_packages() -> ApiResponse:
    """Get available token packages"""
    return api_success({"packages": Config.TOKEN_PACKAGES})


# POST /create-intent (Stripe PaymentIntent creation) is intentionally not registered:
# no verified webhook route exists to credit tokens after a completed payment, so a
# paid intent would never be fulfilled. Restore it together with a webhook that checks
# the signature with stripe.Webhook.construct_event and calls
# PaymentService.handle_successful_payment.
