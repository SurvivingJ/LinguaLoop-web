# utils/responses.py
"""
Standardized API response helpers.
Ensures consistent response format across all endpoints.
"""

from flask import jsonify
from typing import Any, Optional, Dict


def api_success(data: Any = None, message: str = None, status_code: int = 200):
    """
    Create a standardized success response.

    Args:
        data: Response data (any JSON-serializable type)
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': True,
        'status': 'success',
    }
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    return jsonify(response), status_code


def api_error(message: str, status_code: int = 400, error_code: str = None,
              details: Dict = None):
    """
    Create a standardized error response.

    Args:
        message: Error message for the client
        status_code: HTTP status code (default 400)
        error_code: Optional error code for client handling
        details: Optional additional error details

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': False,
        'status': 'error',
        'error': message,
    }
    if error_code:
        response['error_code'] = error_code
    if details:
        response['details'] = details
    return jsonify(response), status_code


# Convenience functions for common errors
def not_found(message: str = "Resource not found"):
    """404 Not Found response"""
    return api_error(message, 404, 'NOT_FOUND')


def unauthorized(message: str = "Authentication required"):
    """401 Unauthorized response"""
    return api_error(message, 401, 'UNAUTHORIZED')


def forbidden(message: str = "Access denied"):
    """403 Forbidden response"""
    return api_error(message, 403, 'FORBIDDEN')


def bad_request(message: str = "Invalid request"):
    """400 Bad Request response"""
    return api_error(message, 400, 'BAD_REQUEST')


def server_error(message: str = "Internal server error"):
    """500 Internal Server Error response"""
    return api_error(message, 500, 'SERVER_ERROR')


def service_unavailable(message: str = "Service temporarily unavailable"):
    """503 Service Unavailable response"""
    return api_error(message, 503, 'SERVICE_UNAVAILABLE')
