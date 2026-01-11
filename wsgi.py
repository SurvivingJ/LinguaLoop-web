"""
WSGI entry point for production deployment
This file avoids relative import issues by serving as the top-level entry point
"""
from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    # This allows running the WSGI file directly for testing
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
