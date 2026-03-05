"""Wishlist price tracking and alert checking."""

import logging
from datetime import datetime, timedelta

from models.wishlist import get_active_wishlist, upsert_wishlist_item
from models.price import get_current_prices_all_stores, get_price_history
from services.notifier import send_email, format_price_alert_email

logger = logging.getLogger(__name__)


def check_all_wishlist_items(store):
    """Check all active wishlist items for price drops. Returns alert list."""
    items = get_active_wishlist(store)
    alerts = []
    for item in items:
        alert = check_single_item(store, item)
        if alert:
            alerts.append(alert)
    return alerts


def check_single_item(store, item):
    """Check a single wishlist item against price thresholds."""
    pid = item.get('product_id')
    if not pid:
        return None

    prices = get_current_prices_all_stores(store, pid)
    if not prices:
        return None

    # Find current best
    best_store = None
    best_price = float('inf')
    for store_name, price_info in prices.items():
        if price_info['price'] < best_price:
            best_price = price_info['price']
            best_store = store_name

    # Update current best on wishlist item
    item['current_best_price'] = best_price
    item['current_best_store'] = best_store
    upsert_wishlist_item(store, item)

    # Check alert conditions
    alert = None

    # Target price met
    if item.get('target_price') and best_price <= item['target_price']:
        alert = {
            'type': 'target_met',
            'item': item,
            'current_price': best_price,
            'store': best_store,
            'message': f"{item['product_name']} hit target price ${best_price:.2f} at {best_store}",
        }

    # Percentage drop threshold
    elif item.get('baseline_price') and item.get('alert_threshold_percent'):
        drop_pct = ((item['baseline_price'] - best_price) / item['baseline_price']) * 100
        if drop_pct >= item['alert_threshold_percent']:
            alert = {
                'type': 'threshold_drop',
                'item': item,
                'current_price': best_price,
                'store': best_store,
                'drop_percent': round(drop_pct, 1),
                'message': f"{item['product_name']} dropped {drop_pct:.1f}% to ${best_price:.2f} at {best_store}",
            }

    return alert


def calculate_price_trends(store, item_id, days=30):
    """Analyze historical price data for a wishlist item."""
    from models.wishlist import get_active_wishlist
    items = get_active_wishlist(store)
    item = next((i for i in items if i['id'] == item_id), None)
    if not item or not item.get('product_id'):
        return None

    history = get_price_history(store, item['product_id'], days=days)
    if not history:
        return {
            'trend': 'unknown',
            'average_price': 0,
            'lowest_price': 0,
            'highest_price': 0,
            'current_price': item.get('current_best_price', 0),
        }

    prices = [h['price'] for h in history]
    avg = sum(prices) / len(prices)

    # Determine trend by comparing first-half avg to second-half avg
    mid = len(prices) // 2
    if mid > 0:
        first_half = sum(prices[:mid]) / mid
        second_half = sum(prices[mid:]) / (len(prices) - mid)
        if second_half < first_half * 0.95:
            trend = 'decreasing'
        elif second_half > first_half * 1.05:
            trend = 'increasing'
        else:
            trend = 'stable'
    else:
        trend = 'stable'

    return {
        'trend': trend,
        'average_price': round(avg, 2),
        'lowest_price': round(min(prices), 2),
        'highest_price': round(max(prices), 2),
        'current_price': item.get('current_best_price', 0),
        'history': history,
    }


def send_alerts(alerts):
    """Send email notifications for triggered alerts."""
    if not alerts:
        return
    try:
        html = format_price_alert_email(alerts)
        send_email("FeastOptimizer: Price Alerts", html)
        logger.info(f"Sent {len(alerts)} price alerts")
    except Exception as e:
        logger.error(f"Failed to send alerts: {e}")
