# middleware/local_only.py
"""Loopback-only guard for the unauthenticated admin blueprints.

``admin_local_bp`` and ``model_arena_bp`` carry no auth decorators — every one
of their ~42 routes is open, and several are destructive
(``/api/vocab/word/<id>/wipe``) or incur real OpenRouter spend
(``/api/run/full-pipeline``). Their safety rests entirely on never being
reachable from off-box, which until now was only a docstring claim.

This module makes the claim enforceable. ``enforce_loopback(bp)`` registers a
``before_request`` hook on the blueprint, so the guard travels with the
blueprint rather than with whichever entry point happens to mount it. Mounting
these blueprints into the production app would therefore fail closed rather
than silently exposing them.

Escape hatch: ``ADMIN_ALLOW_REMOTE=true`` disables the check for the container
case, where requests legitimately arrive from a bridge-network address rather
than 127.0.0.1. It is deliberately loud — a warning is logged at registration
and on every request that the bypass admits — because turning it on genuinely
does expose an unauthenticated remote-code-execution surface.
"""

import ipaddress
import logging
import os

from flask import jsonify, request

logger = logging.getLogger(__name__)


def _allow_remote() -> bool:
    """True when the operator has explicitly opted out of the loopback check."""
    return os.getenv('ADMIN_ALLOW_REMOTE', 'false').strip().lower() == 'true'


def is_loopback(addr: str | None) -> bool:
    """True iff ``addr`` is an IPv4/IPv6 loopback address.

    Handles the three forms Werkzeug can produce: ``127.0.0.1``, ``::1``, and
    the IPv4-mapped ``::ffff:127.0.0.1``. A missing or unparseable address is
    treated as NOT loopback — this gate fails closed, because the cost of a
    false negative (admin can't reach their own dashboard) is trivial next to
    the cost of a false positive (open RCE).
    """
    if not addr:
        return False
    try:
        ip = ipaddress.ip_address(addr.strip())
    except ValueError:
        return False
    # An IPv4-mapped IPv6 address (::ffff:127.0.0.1) is not itself loopback;
    # unwrap it and test the address it actually carries.
    if getattr(ip, 'ipv4_mapped', None) is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback


def enforce_loopback(blueprint) -> None:
    """Refuse non-loopback requests to every route on ``blueprint``."""

    if _allow_remote():
        logger.warning(
            'SECURITY: ADMIN_ALLOW_REMOTE=true — loopback guard DISABLED on '
            'blueprint %r. Its routes are unauthenticated; anyone who can '
            'reach this port can wipe data and spend API credit.',
            blueprint.name,
        )

    @blueprint.before_request
    def _reject_non_loopback():
        if _allow_remote():
            logger.warning(
                'Admin request admitted from %s via ADMIN_ALLOW_REMOTE bypass: %s',
                request.remote_addr, request.path,
            )
            return None
        if is_loopback(request.remote_addr):
            return None
        logger.warning(
            'Blocked non-loopback admin request from %s to %s',
            request.remote_addr, request.path,
        )
        return jsonify({'error': 'Admin endpoints are restricted to localhost'}), 403
