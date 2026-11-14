"""Response security headers."""

from flask import abort, request

# Content-Security-Policy in REPORT-ONLY mode: the browser reports violations
# and blocks nothing, so it is safe while inline <script>/<style> remain.
# 'unsafe-inline' is intentional until that inline code is gone. Bootstrap,
# Font Awesome and Bootstrap Icons are self-hosted under static/vendor/; the
# only third party left is Google Fonts.
CSP_REPORT_ONLY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self'",
    "base-uri 'self'",
    "frame-ancestors 'self'",
])

HSTS = 'max-age=31536000'

STATIC_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}


def init_security_headers(app):
    @app.after_request
    def _apply_security_headers(response):
        for name, value in STATIC_HEADERS.items():
            response.headers.setdefault(name, value)
        # request.is_secure reflects X-Forwarded-Proto through ProxyFix.
        if request.is_secure:
            response.headers.setdefault('Strict-Transport-Security', HSTS)
        if response.headers.get('Content-Type', '').startswith('text/html'):
            response.headers.setdefault('Content-Security-Policy-Report-Only', CSP_REPORT_ONLY)
        return response


def init_request_size_limit(app):
    """Refuse an oversized body before any view runs.

    Flask enforces MAX_CONTENT_LENGTH lazily, when the body is first read; a
    view that reads it inside a broad ``except`` would turn the 413 into a 500.
    """

    @app.before_request
    def _reject_oversized_body():
        limit = app.config.get('MAX_CONTENT_LENGTH')
        if limit and request.content_length and request.content_length > limit:
            abort(413)
