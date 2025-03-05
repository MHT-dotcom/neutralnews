"""
Special runner script that adds extra diagnostic logging to track import sequence
and configuration access patterns.
"""

import os
import sys
import time
import logging
from logging.config import dictConfig

# Set up initial logging before any imports
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app_startup.log',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    }
})

logger = logging.getLogger(__name__)
logger.info(f"[RUNNER] {time.time()} - Starting diagnostic run of Flask application")

# Log the Python path
logger.info(f"[RUNNER] Python path: {sys.path}")

# Log environment for API keys (existence only, not values)
logger.info("[RUNNER] Environment variables:")
for key in os.environ:
    if any(x in key.upper() for x in ['KEY', 'API', 'PASSWORD', 'SECRET', 'TOKEN']):
        logger.info(f"[RUNNER] {key}: {'EXISTS' if os.environ.get(key) else 'EMPTY'} (length: {len(os.environ.get(key, ''))})")

# Import and create the Flask application
logger.info(f"[RUNNER] {time.time()} - About to import app module")
from app import create_app
logger.info(f"[RUNNER] {time.time()} - App module imported")

# Create the Flask application
logger.info(f"[RUNNER] {time.time()} - About to create Flask application instance")
app = create_app()
logger.info(f"[RUNNER] {time.time()} - Flask application instance created")

# Print the config (without API keys)
logger.info("[RUNNER] Flask application configuration:")
for key in sorted(app.config.keys()):
    # Skip internal flask config and sensitive keys
    if key.startswith('_') or any(x in key.upper() for x in ['KEY', 'PASSWORD', 'SECRET', 'TOKEN']):
        logger.info(f"[RUNNER] {key}: <SENSITIVE_VALUE>")
    else:
        logger.info(f"[RUNNER] {key}: {app.config.get(key)}")

# Create a test client
logger.info(f"[RUNNER] {time.time()} - Creating test client")
client = app.test_client()

# Log request to trigger the application
logger.info(f"[RUNNER] {time.time()} - Making test request to root endpoint")
with app.app_context():
    logger.info(f"[RUNNER] {time.time()} - Entered application context")
    
    # Log all API flags
    api_flags = {
        'USE_NEWSAPI_ORG': app.config.get('USE_NEWSAPI_ORG', False),
        'USE_GUARDIAN': app.config.get('USE_GUARDIAN', False),
        'USE_GNEWS': app.config.get('USE_GNEWS', False),
        'USE_NYT': app.config.get('USE_NYT', False),
        'USE_MEDIASTACK': app.config.get('USE_MEDIASTACK', False),
        'USE_NEWSAPI_AI': app.config.get('USE_NEWSAPI_AI', False),
        'USE_AYLIEN': app.config.get('USE_AYLIEN', False),
        'USE_OPENAI': app.config.get('USE_OPENAI', False)
    }
    logger.info(f"[RUNNER] API flags (within context): {api_flags}")
    
    # Log API key lengths
    api_keys = {
        'NEWSAPI_ORG_KEY': len(app.config.get('NEWSAPI_ORG_KEY', '')),
        'GUARDIAN_API_KEY': len(app.config.get('GUARDIAN_API_KEY', '')),
        'OPENAI_API_KEY': len(app.config.get('OPENAI_API_KEY', '')),
        'GNEWS_API_KEY': len(app.config.get('GNEWS_API_KEY', '')),
        'NYT_API_KEY': len(app.config.get('NYT_API_KEY', '')),
        'AYLIEN_API_KEY': len(app.config.get('AYLIEN_API_KEY', '')),
        'MEDIASTACK_API_KEY': len(app.config.get('MEDIASTACK_API_KEY', '')),
        'NEWSAPI_AI_KEY': len(app.config.get('NEWSAPI_AI_KEY', ''))
    }
    logger.info(f"[RUNNER] API key lengths (within context): {api_keys}")

# Make an actual HTTP request
response = client.get('/')
logger.info(f"[RUNNER] {time.time()} - Response from test request: status={response.status_code}")

logger.info(f"[RUNNER] {time.time()} - Diagnostic run completed")

if __name__ == "__main__":
    logger.info("[RUNNER] Running Flask application")
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 10000))
    
    # Run the application
    logger.info(f"[RUNNER] Starting Flask application on {host}:{port}")
    app.run(host=host, port=port, debug=False) 