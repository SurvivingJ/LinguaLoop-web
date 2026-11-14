"""App-level error handling.

API paths get the utils.responses error envelope
(``{"status": "error", "error": ..., "error_code": ...}``); pages get a
redirect to login for unknown URLs and templates/error.html for failures.
"""

from flask import current_app, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.routing import RoutingException

from utils.responses import api_error

# status -> (error_code, message). A message of None uses the exception's own.
_API_ERRORS = {
    400: ('BAD_REQUEST', None),
    401: ('UNAUTHORIZED', None),
    403: ('FORBIDDEN', None),
    404: ('NOT_FOUND', 'Endpoint not found'),
    405: ('METHOD_NOT_ALLOWED', 'Method not allowed'),
    413: ('PAYLOAD_TOO_LARGE', 'Request body too large'),
    429: ('RATE_LIMITED', 'Too many requests. Please try again later.'),
    500: ('SERVER_ERROR', 'Internal server error'),
    503: ('SERVICE_UNAVAILABLE', None),
}
_PASSTHROUGH_HEADERS = ('Allow', 'Retry-After')


def _is_api_request():
    return request.path.startswith('/api/')


def _json_error(exc):
    status = exc.code or 500
    error_code, message = _API_ERRORS.get(status, (None, None))
    response, _ = api_error(message or exc.description or exc.name, status, error_code)
    upstream = exc.get_response().headers
    for header in _PASSTHROUGH_HEADERS:
        if header in upstream:
            response.headers[header] = upstream[header]
    return response, status


def _error_page(status=500):
    try:
        return render_template('error.html', status=status), status
    except Exception:
        # The failure may be in the base template or its context itself.
        current_app.logger.exception("error.html failed to render")
        return 'Something went wrong. Please try again in a moment.', status


def register_error_handlers(app):

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        if exc.code is None or exc.response is not None or isinstance(exc, RoutingException):
            return exc
        # 405 has always answered in JSON, pages included.
        if _is_api_request() or exc.code == 405:
            return _json_error(exc)
        if exc.code == 404:
            return redirect(url_for('login'))
        if exc.code >= 500:
            return _error_page(exc.code)
        return exc

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc):
        # Keep the interactive debugger when running with FLASK_DEBUG.
        if current_app.debug:
            raise exc
        current_app.logger.exception(
            "Unhandled exception on %s %s", request.method, request.path
        )
        if _is_api_request():
            return api_error('Internal server error', 500, 'SERVER_ERROR')
        return _error_page(500)
