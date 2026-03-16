# utils/responses.py
"""
Standardized API response helpers.
Ensures consistent response format across all endpoints.

Success shape:  {"status": "success", ...extra_fields}
Error shape:    {"status": "error", "error": "<message>"}
"""

from flask import jsonify
from typing import Any, Optional, Dict, Tuple
from flask.wrappers import Response

# Type alias for Flask route return values
ApiResponse = Tuple[Response, int]


def api_success(data: Dict[str, Any] | None = None, message: str | None = None,
                status_code: int = 200) -> Tuple[Response, int]:
    """Create a standardized success response.

    Data fields are spread at the top level (not nested under 'data')
    to match frontend expectations.
    """
    response: Dict[str, Any] = {'status': 'success'}
    if data is not None:
        response.update(data)
    if message:
        response['message'] = message
    return jsonify(response), status_code


def api_error(message: str, status_code: int = 400, error_code: str | None = None,
              details: Dict | None = None) -> Tuple[Response, int]:
    """Create a standardized error response."""
    response: Dict[str, Any] = {
        'status': 'error',
        'error': message,
    }
    if error_code:
        response['error_code'] = error_code
    if details:
        response['details'] = details
    return jsonify(response), status_code


# Convenience functions for common errors
def not_found(message: str = "Resource not found") -> Tuple[Response, int]:
    """404 Not Found response"""
    return api_error(message, 404, 'NOT_FOUND')


def unauthorized(message: str = "Authentication required") -> Tuple[Response, int]:
    """401 Unauthorized response"""
    return api_error(message, 401, 'UNAUTHORIZED')


def forbidden(message: str = "Access denied") -> Tuple[Response, int]:
    """403 Forbidden response"""
    return api_error(message, 403, 'FORBIDDEN')


def bad_request(message: str = "Invalid request") -> Tuple[Response, int]:
    """400 Bad Request response"""
    return api_error(message, 400, 'BAD_REQUEST')


def server_error(message: str = "Internal server error") -> Tuple[Response, int]:
    """500 Internal Server Error response"""
    return api_error(message, 500, 'SERVER_ERROR')


def service_unavailable(message: str = "Service temporarily unavailable") -> Tuple[Response, int]:
    """503 Service Unavailable response"""
    return api_error(message, 503, 'SERVICE_UNAVAILABLE')
