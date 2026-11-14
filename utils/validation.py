import re
from functools import wraps

from flask import request
from werkzeug.exceptions import BadRequest

from utils.responses import bad_request

def validate_email(email: str) -> bool:
    """
    Validate email address format using regex.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email format is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Remove whitespace and convert to lowercase
    email = email.strip().lower()
    
    # Basic email regex pattern
    # Matches: user@domain.com, user.name+tag@domain.co.uk, etc.
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return re.match(email_regex, email) is not None


def json_body(silent: bool = False) -> dict:
    """The request's JSON object; ``{}`` when the body is empty or null.

    ``silent`` also turns an unparseable body or a non-JSON content type into
    ``{}`` instead of a 400/415. A body that is JSON but not an object is a 400.
    """
    data = request.get_json(silent=silent) or {}
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object")
    return data


def require_language_id(fn):
    """Pass the ``language_id`` query parameter to the view as an int keyword
    argument, or answer 400 when it is missing, zero or not a number."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")
        return fn(*args, language_id=language_id, **kwargs)
    return wrapper
