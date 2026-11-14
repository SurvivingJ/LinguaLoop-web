"""Central rate limiting.

Limits are attached by endpoint name after the blueprints are registered, so
route modules stay unaware of them. Each limit is keyed on the verified user
id when the request carries a valid token, otherwise on the client IP (the
real one: ProxyFix resolves X-Forwarded-For before this runs).

Storage comes from RATELIMIT_STORAGE_URI. The default, memory://, counts per
process: with N gunicorn workers a client can reach roughly N times each
limit. Point it at Redis (redis://...) for limits shared across workers.
"""

from flask import g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from middleware.auth import get_optional_user_id

_UNSET = object()


def client_ip():
    return f"ip:{get_remote_address()}"


def user_or_ip():
    """Verified user id, else client IP. The token check goes through the
    auth middleware's validation cache, so the route's own auth decorator
    reuses the result instead of paying for a second round trip."""
    user_id = getattr(g, '_rate_limit_user_id', _UNSET)
    if user_id is _UNSET:
        user_id = g._rate_limit_user_id = get_optional_user_id(request)
    return f"user:{user_id}" if user_id else client_ip()


def email_or_ip():
    """The email an OTP request targets, so one address cannot be flooded
    from many IPs."""
    body = request.get_json(silent=True)
    email = body.get('email') if isinstance(body, dict) else None
    if isinstance(email, str) and email.strip():
        return f"email:{email.strip().lower()[:254]}"
    return client_ip()


# endpoint -> ((limit, key function), ...). Every listed limit applies.
ENDPOINT_LIMITS = {
    # Unauthenticated sign-in surface.
    'auth.send_otp': (
        ('5 per minute; 20 per hour', client_ip),
        ('3 per 10 minutes; 10 per day', email_or_ip),
    ),
    'auth.verify_otp': (
        ('10 per minute; 60 per hour', client_ip),
        ('10 per 10 minutes', email_or_ip),
    ),
    'auth.device_restore': (('30 per minute', client_ip),),
    'auth.refresh_token': (('60 per minute', client_ip),),

    # LLM-backed or otherwise expensive, per user.
    'word_list_import.submit': (('5 per hour; 20 per day', user_or_ip),),
    'extract_vocabulary': (('10 per minute; 100 per day', user_or_ip),),
    'dual_translation.submit': (('10 per minute; 120 per hour', user_or_ip),),
    'tests.moderate_content': (('20 per minute', user_or_ip),),
    'corpus.ingest_corpus': (('10 per hour', user_or_ip),),
    'corpus.analyze_style': (('10 per hour', user_or_ip),),
    'vocab_admin.generate_assets': (('30 per hour', user_or_ip),),
    'vocab_admin.render_exercises': (('30 per hour', user_or_ip),),
    'vocab_admin.upload_words': (('30 per hour', user_or_ip),),
}

EXEMPT_ENDPOINTS = ('health_check',)


def _outside_api():
    return not request.path.startswith('/api/')


def init_rate_limits(app):
    """Attach the limiter. Call after every blueprint and route is registered."""
    enabled = bool(app.config.get('RATELIMIT_ENABLED', True))
    # Under TESTING the limiter stays off unless a test opts in explicitly.
    if app.config.get('TESTING') and not app.config.get('RATELIMIT_ENABLED_IN_TESTS'):
        enabled = False
    # Flask-Limiter reads this key itself and lets it override the argument.
    app.config['RATELIMIT_ENABLED'] = enabled

    limiter = Limiter(
        key_func=user_or_ip,
        default_limits=[app.config.get('RATELIMIT_API_DEFAULT', '300 per minute')],
        default_limits_exempt_when=_outside_api,
        storage_uri=app.config.get('RATELIMIT_STORAGE_URI', 'memory://'),
        strategy='fixed-window',
        headers_enabled=True,
        # A broken limiter store must not take the site down with it.
        swallow_errors=True,
        in_memory_fallback_enabled=True,
        enabled=enabled,
    )
    limiter.init_app(app)
    # The batch-service identity (ADR-014) drives bulk jobs over HTTP.
    limiter.request_filter(lambda: user_or_ip() == 'user:service-account')
    app.extensions['rate_limiter'] = limiter
    if not enabled:
        return limiter

    for endpoint, limits in ENDPOINT_LIMITS.items():
        view = app.view_functions.get(endpoint)
        if view is None:
            app.logger.warning("Rate limit configured for unknown endpoint %s", endpoint)
            continue
        for limit, key_func in limits:
            view = limiter.limit(limit, key_func=key_func)(view)
        app.view_functions[endpoint] = view

    for endpoint in EXEMPT_ENDPOINTS:
        if endpoint in app.view_functions:
            app.view_functions[endpoint] = limiter.exempt(app.view_functions[endpoint])

    if str(app.config.get('RATELIMIT_STORAGE_URI', 'memory://')).startswith('memory://'):
        app.logger.info("Rate limits use in-memory storage: counts are per worker process")
    return limiter
