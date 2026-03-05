"""Offer expiry cleanup job: remove expired loyalty offers."""

import logging

from models.offer import expire_old_offers

logger = logging.getLogger(__name__)


def run_offer_cleanup(app):
    with app.app_context():
        store = app.store
        logger.info("Starting offer cleanup")

        try:
            deleted = expire_old_offers(store)
            if deleted:
                logger.info(f"Removed {deleted} expired offers")
            else:
                logger.info("No expired offers to clean up")
        except Exception as e:
            logger.error(f"Offer cleanup failed: {e}")
