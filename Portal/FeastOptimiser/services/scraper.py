"""Price scraping for Coles and Woolworths."""

import logging
import random
import time
import requests
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)


def get_random_user_agent():
    return random.choice(Config.SCRAPE_USER_AGENTS)


def rate_limited_request(url, headers=None, delay_range=(1.0, 3.0)):
    """Make HTTP request with random delay to avoid rate limiting."""
    time.sleep(random.uniform(*delay_range))
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', get_random_user_agent())

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.warning(f"Request failed for {url}: {e}")
        return None


def scrape_coles(product_list):
    """Scrape current prices from Coles for all products in the list.

    Note: Coles website structure changes frequently. Selectors may need updating.
    """
    results = []
    for product in product_list:
        mappings = product.get('store_mappings', {})
        coles_info = mappings.get('coles', {})
        url = coles_info.get('url', '')
        if not url:
            continue

        resp = rate_limited_request(url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            price_data = _extract_coles_price(soup)
            if price_data:
                price_data['product_id'] = product['id']
                price_data['store'] = 'coles'
                results.append(price_data)
        except Exception as e:
            logger.warning(f"Failed to parse Coles page for {product['id']}: {e}")

    return results


def _extract_coles_price(soup):
    """Extract price data from Coles product page HTML.

    Selectors are defensive — try multiple patterns.
    """
    price = None
    unit_price = None
    promo = False
    promo_details = None

    # Try common Coles price selectors
    for selector in ['.price__value', '[data-testid="product-pricing"]', '.product-price', '.price']:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            price = _parse_price_text(text)
            if price:
                break

    # Unit price
    for selector in ['.price__calculation_method', '.unit-price', '.price-per-unit']:
        el = soup.select_one(selector)
        if el:
            unit_price = _parse_price_text(el.get_text(strip=True))
            break

    # Promotion
    for selector in ['.badge--promotion', '.promo-badge', '.special-badge']:
        el = soup.select_one(selector)
        if el:
            promo = True
            promo_details = el.get_text(strip=True)
            break

    if price is None:
        return None

    return {
        'price': price,
        'unit_price': unit_price,
        'promotion_active': promo,
        'promotion_details': promo_details,
    }


def scrape_woolworths(product_list):
    """Scrape current prices from Woolworths for all products in the list."""
    results = []
    for product in product_list:
        mappings = product.get('store_mappings', {})
        woolies_info = mappings.get('woolworths', {})
        url = woolies_info.get('url', '')
        if not url:
            continue

        resp = rate_limited_request(url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            price_data = _extract_woolworths_price(soup)
            if price_data:
                price_data['product_id'] = product['id']
                price_data['store'] = 'woolworths'
                results.append(price_data)
        except Exception as e:
            logger.warning(f"Failed to parse Woolworths page for {product['id']}: {e}")

    return results


def _extract_woolworths_price(soup):
    """Extract price data from Woolworths product page HTML."""
    price = None
    unit_price = None
    promo = False
    promo_details = None

    for selector in ['.price--large', '.product-price', '.price', '[class*="price"]']:
        el = soup.select_one(selector)
        if el:
            price = _parse_price_text(el.get_text(strip=True))
            if price:
                break

    for selector in ['.price-per-cup', '.unit-price', '[class*="cup-price"]']:
        el = soup.select_one(selector)
        if el:
            unit_price = _parse_price_text(el.get_text(strip=True))
            break

    for selector in ['.product-tag--saving', '.special', '[class*="saving"]']:
        el = soup.select_one(selector)
        if el:
            promo = True
            promo_details = el.get_text(strip=True)
            break

    if price is None:
        return None

    return {
        'price': price,
        'unit_price': unit_price,
        'promotion_active': promo,
        'promotion_details': promo_details,
    }


def scrape_store(store_name, product_list):
    """Dispatcher for store-specific scraping."""
    if store_name == 'coles':
        return scrape_coles(product_list)
    elif store_name == 'woolworths':
        return scrape_woolworths(product_list)
    else:
        logger.warning(f"Unknown store: {store_name}")
        return []


def _parse_price_text(text):
    """Extract numeric price from text like '$12.50' or '12.50'."""
    import re
    match = re.search(r'\$?(\d+\.?\d*)', text)
    if match:
        return float(match.group(1))
    return None
