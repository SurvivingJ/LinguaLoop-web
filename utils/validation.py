import re
from typing import Optional

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

def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input by trimming whitespace and limiting length.
    
    Args:
        input_str (str): Input string to sanitize
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized string
    """
    if not input_str:
        return ""
    
    return input_str.strip()[:max_length]
