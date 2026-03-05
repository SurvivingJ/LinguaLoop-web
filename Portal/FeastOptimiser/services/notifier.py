"""Email notification service using Gmail SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config

logger = logging.getLogger(__name__)


def send_email(subject, html_body):
    """Send an HTML email via Gmail SMTP."""
    if not all([Config.NOTIFICATION_EMAIL, Config.EMAIL_PASSWORD, Config.USER_EMAIL]):
        logger.warning("Email credentials not configured, skipping send")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = Config.NOTIFICATION_EMAIL
    msg['To'] = Config.USER_EMAIL
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(Config.NOTIFICATION_EMAIL, Config.EMAIL_PASSWORD)
            server.sendmail(Config.NOTIFICATION_EMAIL, Config.USER_EMAIL, msg.as_string())
        logger.info(f"Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def format_price_alert_email(alerts):
    """Format price drop alerts as an HTML email."""
    rows = ''
    for alert in alerts:
        item = alert.get('item', {})
        rows += f"""
        <tr>
            <td>{item.get('product_name', 'Unknown')}</td>
            <td>${alert.get('current_price', 0):.2f}</td>
            <td>{alert.get('store', 'Unknown').title()}</td>
            <td>{alert.get('drop_percent', 'N/A')}%</td>
            <td>{alert.get('type', '').replace('_', ' ').title()}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #E63946;">FeastOptimizer Price Alerts</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
            <thead>
                <tr style="background: #f8f9fa;">
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Price</th>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Store</th>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Drop</th>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Type</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>
    """


def format_gift_reminder_email(gifts):
    """Format upcoming gift reminders as an HTML email."""
    rows = ''
    for gift in gifts:
        days = gift.get('days_remaining', '?')
        rows += f"""
        <tr>
            <td>{gift.get('recipient', 'Unknown')}</td>
            <td>{gift.get('occasion', '')}</td>
            <td>{gift.get('occasion_date', '')}</td>
            <td>{days} days</td>
            <td>${gift.get('current_best_price', 'N/A')}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #F4A261;">Upcoming Gift Reminders</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
            <thead>
                <tr style="background: #f8f9fa;">
                    <th style="padding: 8px; text-align: left;">Recipient</th>
                    <th style="padding: 8px; text-align: left;">Occasion</th>
                    <th style="padding: 8px; text-align: left;">Date</th>
                    <th style="padding: 8px; text-align: left;">Remaining</th>
                    <th style="padding: 8px; text-align: left;">Best Price</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>
    """
