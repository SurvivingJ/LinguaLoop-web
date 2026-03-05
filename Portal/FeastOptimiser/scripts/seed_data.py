"""Seed the CSV data store with initial products and default settings."""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.csv_store import CSVStore
from models.product import upsert_product
from models.settings import get_settings


def seed(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'store')

    store = CSVStore(data_dir)
    base_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    # Seed products
    products_file = os.path.join(base_data, 'initial_products.json')
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)

    for product in products:
        upsert_product(store, product)
    print(f"Seeded {len(products)} products")

    # Initialize default settings (get_settings auto-creates defaults)
    settings = get_settings(store)
    print(f"Settings initialized: budget=${settings['weekly_budget']}, theme={settings['theme']}")

    # Seed recipes from skill trees
    from scripts.seed_recipes import seed_recipes
    seed_recipes(data_dir)

    print("Seed complete!")


if __name__ == '__main__':
    seed()
