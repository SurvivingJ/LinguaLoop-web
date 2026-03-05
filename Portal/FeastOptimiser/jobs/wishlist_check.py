"""Wishlist price check job: check thresholds and send email alerts."""

import logging

from services.wishlist_tracker import check_all_wishlist_items, send_alerts

logger = logging.getLogger(__name__)


def run_wishlist_check(app):
    with app.app_context():
        store = app.store
        logger.info("Starting wishlist check")

        try:
            alerts = check_all_wishlist_items(store)
            if alerts:
                send_alerts(alerts)
                logger.info(f"Triggered {len(alerts)} wishlist alerts")
            else:
                logger.info("No wishlist alerts triggered")
        except Exception as e:
            logger.error(f"Wishlist check failed: {e}")
