"""Daily price scraping job: fetch prices for all products from Coles/Woolworths."""

import logging

from models.product import get_all_products
from models.price import insert_price
from services.scraper import scrape_store

logger = logging.getLogger(__name__)


def run_daily_scrape(app):
    with app.app_context():
        store = app.store
        products = get_all_products(store)
        logger.info(f"Starting daily scrape for {len(products)} products")

        for store_name in ['coles', 'woolworths']:
            try:
                results = scrape_store(store_name, products)
                saved = 0
                for result in results:
                    insert_price(store, {
                        'product_id': result['product_id'],
                        'store': store_name,
                        'price': result['price'],
                        'unit_price': result.get('unit_price', 0),
                        'promotion_active': result.get('promotion_active', False),
                        'promotion_details': result.get('promotion_details', ''),
                    })
                    saved += 1
                logger.info(f"Scraped {saved} prices from {store_name}")
            except Exception as e:
                logger.error(f"Scrape failed for {store_name}: {e}")

        logger.info("Daily scrape complete")
