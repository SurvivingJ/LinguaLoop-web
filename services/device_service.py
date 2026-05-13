"""Trusted-device service.

Backs the "Remember this device for 6 months" login option. Issues opaque
long-lived refresh credentials, stores only their SHA-256 hashes in the
trusted_devices table, and rotates them on every successful restore.

A rotated token presented later is treated as evidence of theft (OAuth 2.0
BCP refresh-token rotation pattern): the whole user's device family is
revoked and the user is forced to re-authenticate via OTP.

The raw token never persists anywhere server-side beyond the in-memory call
that sets it on the HTTP response cookie.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from supabase import Client, create_client

from config import Config


logger = logging.getLogger(__name__)

REVOKE_REASON_USER = 'user'
REVOKE_REASON_LOGOUT = 'logout'
REVOKE_REASON_REUSE = 'reuse_detected'
REVOKE_REASON_EXPIRED = 'expired'
REVOKE_REASON_ROTATED = 'rotated'


def _hash_token(raw_token: str) -> bytes:
    return hashlib.sha256(raw_token.encode('utf-8')).digest()


def _hash_ip(ip: Optional[str]) -> Optional[bytes]:
    if not ip:
        return None
    salt = Config.DEVICE_IP_HASH_SALT or Config.SECRET_KEY or ''
    return hashlib.sha256((ip + salt).encode('utf-8')).digest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_expires_at() -> datetime:
    return _now() + Config.REMEMBER_DEVICE_DURATION


# ---------------------------------------------------------------------------
# User-Agent → human label
# ---------------------------------------------------------------------------
# Lightweight regex-based parser. Good enough for the settings UI ("Chrome on
# Windows", "Safari on iOS"). Not exhaustive; falls back to "Unknown device".
_BROWSER_PATTERNS = [
    (re.compile(r'Edg/', re.I), 'Edge'),
    (re.compile(r'OPR/|Opera', re.I), 'Opera'),
    (re.compile(r'Chrome/', re.I), 'Chrome'),
    (re.compile(r'Firefox/', re.I), 'Firefox'),
    (re.compile(r'Safari/', re.I), 'Safari'),
]
_OS_PATTERNS = [
    (re.compile(r'Windows', re.I), 'Windows'),
    # iOS before macOS — iOS Safari UA includes "like Mac OS X".
    (re.compile(r'iPhone|iPad|iPod|iOS', re.I), 'iOS'),
    (re.compile(r'Android', re.I), 'Android'),
    (re.compile(r'Mac OS X|Macintosh', re.I), 'macOS'),
    (re.compile(r'Linux', re.I), 'Linux'),
]


def parse_device_label(user_agent: Optional[str]) -> str:
    if not user_agent:
        return 'Unknown device'
    browser = next((name for pat, name in _BROWSER_PATTERNS if pat.search(user_agent)), None)
    os_name = next((name for pat, name in _OS_PATTERNS if pat.search(user_agent)), None)
    if browser and os_name:
        return f'{browser} on {os_name}'
    return browser or os_name or 'Unknown device'


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class DeviceService:
    """Manages the trusted_devices table and the long-lived device tokens."""

    def __init__(self, supabase_admin: Optional[Client] = None):
        # Build our own admin client if one wasn't injected — mirrors AuthService.
        self.supabase_admin = supabase_admin or create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
        )

    # -----------------------------------------------------------------------
    # Issue (first time on a device, after a successful OTP verify)
    # -----------------------------------------------------------------------
    def issue_device_token(
        self,
        user_id: str,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> Tuple[str, datetime]:
        """Mint a new device token. Returns (raw_token, expires_at)."""
        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw_token)
        expires_at = _new_expires_at()

        row = {
            'device_id': self._new_device_id(),
            'user_id': user_id,
            'token_hash': self._encode_bytea(token_hash),
            'generation': 1,
            'device_label': parse_device_label(user_agent),
            'user_agent': (user_agent or '')[:1000] or None,
            'ip_hash': self._encode_bytea(_hash_ip(ip)),
            'expires_at': expires_at.isoformat(),
        }
        self.supabase_admin.table('trusted_devices').insert(row).execute()
        return raw_token, expires_at

    # -----------------------------------------------------------------------
    # Restore (silent re-auth on later visits)
    # -----------------------------------------------------------------------
    def restore_from_token(
        self,
        raw_token: str,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> Optional[Dict]:
        """Validate, rotate, and return a fresh token.

        Returns dict with keys {user_id, user_email, new_raw_token, expires_at}
        on success, or None on any failure (bad token, expired, revoked,
        reuse detected).
        """
        if not raw_token:
            return None

        token_hash = _hash_token(raw_token)
        try:
            rows = (
                self.supabase_admin.table('trusted_devices')
                .select('*')
                .eq('token_hash', self._encode_bytea(token_hash))
                .limit(1)
                .execute()
                .data
            )
        except Exception as e:
            # Most likely cause: trusted_devices migration not applied. Treat
            # any DB failure as a bad token so the user is bounced to /login
            # cleanly instead of getting a 500.
            logger.error('device-restore: token lookup failed: %s', e)
            return None

        if not rows:
            logger.info('device-restore: no row matches incoming token hash')
            return None

        row = rows[0]
        user_id = row['user_id']

        # --- Reuse detection -------------------------------------------------
        # A token that was rotated should never be presented again. If it is,
        # treat the entire user as compromised.
        if row.get('revoked_reason') == REVOKE_REASON_ROTATED:
            logger.warning(
                'device-restore: REUSE DETECTED for user %s — revoking all devices',
                user_id,
            )
            self.revoke_all_for_user(user_id, REVOKE_REASON_REUSE)
            return None

        # --- Already revoked for another reason -----------------------------
        if row.get('revoked_at'):
            logger.info(
                'device-restore: token already revoked (reason=%s)',
                row.get('revoked_reason'),
            )
            return None

        # --- Expired --------------------------------------------------------
        expires_at = self._parse_ts(row['expires_at'])
        if expires_at <= _now():
            self._mark_revoked(row['id'], REVOKE_REASON_EXPIRED)
            logger.info('device-restore: token expired for user %s', user_id)
            return None

        # --- Happy path: rotate ---------------------------------------------
        # 1. Insert new row in the same chain with a fresh token + sliding TTL.
        new_raw_token = secrets.token_urlsafe(48)
        new_expires = _new_expires_at()
        new_row = {
            'device_id': row['device_id'],
            'user_id': user_id,
            'token_hash': self._encode_bytea(_hash_token(new_raw_token)),
            'generation': int(row['generation']) + 1,
            'device_label': row.get('device_label') or parse_device_label(user_agent),
            'user_agent': (user_agent or row.get('user_agent') or '')[:1000] or None,
            'ip_hash': self._encode_bytea(_hash_ip(ip)) or row.get('ip_hash'),
            'expires_at': new_expires.isoformat(),
        }
        self.supabase_admin.table('trusted_devices').insert(new_row).execute()

        # 2. Mark the presented row revoked-with-reason='rotated'. From here
        #    on, replaying the old token will trip reuse detection.
        self._mark_revoked(row['id'], REVOKE_REASON_ROTATED)

        # 3. Look up the email for session minting.
        user_email = self._get_user_email(user_id)
        if not user_email:
            logger.error('device-restore: no email found for user %s', user_id)
            return None

        return {
            'user_id': user_id,
            'user_email': user_email,
            'new_raw_token': new_raw_token,
            'expires_at': new_expires,
        }

    # -----------------------------------------------------------------------
    # Revoke helpers
    # -----------------------------------------------------------------------
    def revoke_by_raw_token(self, raw_token: str, reason: str = REVOKE_REASON_LOGOUT) -> None:
        """Revoke the row matching a raw token. Used on logout."""
        if not raw_token:
            return
        token_hash = _hash_token(raw_token)
        try:
            self.supabase_admin.table('trusted_devices').update({
                'revoked_at': _now().isoformat(),
                'revoked_reason': reason,
            }).eq('token_hash', self._encode_bytea(token_hash)).is_('revoked_at', 'null').execute()
        except Exception as e:
            logger.warning('revoke_by_raw_token failed: %s', e)

    def revoke_all_for_user(self, user_id: str, reason: str) -> None:
        """Mark every unrevoked row for a user as revoked."""
        try:
            self.supabase_admin.table('trusted_devices').update({
                'revoked_at': _now().isoformat(),
                'revoked_reason': reason,
            }).eq('user_id', user_id).is_('revoked_at', 'null').execute()
        except Exception as e:
            logger.error('revoke_all_for_user(%s) failed: %s', user_id, e)

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------
    def _mark_revoked(self, row_id: str, reason: str) -> None:
        self.supabase_admin.table('trusted_devices').update({
            'revoked_at': _now().isoformat(),
            'revoked_reason': reason,
        }).eq('id', row_id).execute()

    def _get_user_email(self, user_id: str) -> Optional[str]:
        result = (
            self.supabase_admin.table('users')
            .select('email')
            .eq('id', user_id)
            .limit(1)
            .execute()
            .data
        )
        return result[0]['email'] if result else None

    @staticmethod
    def _new_device_id() -> str:
        import uuid
        return str(uuid.uuid4())

    @staticmethod
    def _encode_bytea(value: Optional[bytes]) -> Optional[str]:
        # PostgREST accepts hex-escaped bytea via the "\\x..." syntax.
        if value is None:
            return None
        return '\\x' + value.hex()

    @staticmethod
    def _parse_ts(value) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        # Supabase returns ISO 8601 with 'Z' or '+00:00'.
        s = str(value).replace('Z', '+00:00')
        return datetime.fromisoformat(s)
