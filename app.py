"""
Neutral News MVP Application
This module implements the main Flask application for serving news articles
with sentiment analysis and summarization.
"""

import os
import sys
import logging
import pkg_resources
import time
from logging.config import dictConfig
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Setup basic logging before any imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log diagnostic information
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")
logger.info(f"Python path: {sys.path}")

logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Starting app.py before any module imports")

# Log installed packages
logger.info("[PACKAGES] Installed packages:")
installed_packages = [f"{dist.key} {dist.version}" for dist in pkg_resources.working_set]
logger.info("\n".join(installed_packages))

# Log requirements.txt content
try:
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
        logger.info(f"[REQUIREMENTS] requirements.txt contents:\n{requirements}")
except Exception as e:
    logger.error(f"[REQUIREMENTS] Error reading requirements.txt: {e}")

# Log environment variables (safely)
def log_environment_variables():
    """Log available environment variables (safely, without exposing values)"""
    env_vars = os.environ.keys()
    logger.info(f"[ENV_VARS] Total environment variables: {len(env_vars)}")
    api_key_vars = [v for v in env_vars if any(x in v.upper() for x in ['KEY', 'API', 'TOKEN'])]
    logger.info(f"[ENV_VARS] Potential API key variables: {len(api_key_vars)}")
    known_keys = ['NEWSAPI_ORG_KEY', 'GUARDIAN_API_KEY', 'AYLIEN_APP_ID', 'AYLIEN_API_KEY', 
                  'GNEWS_API_KEY', 'NEWSAPI_AI_KEY', 'MEDIASTACK_API_KEY', 'OPENAI_API_KEY', 'NYT_API_KEY']
    for key in known_keys:
        exists = key in os.environ
        value_length = len(os.environ.get(key, '')) if exists else 0
        logger.info(f"[ENV_VARS] {key}: {'✓' if exists else '✗'} (length: {value_length})")

# Log before importing Flask modules
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - About to import Flask modules")

from flask import request, appcontext_pushed, appcontext_popped, request_started
from flask_cors import CORS

# Log after importing Flask modules
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Finished importing Flask modules")

__version__ = '0.1.0'

def configure_logging():
    """Configure logging for the application"""
    try:
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
                    'filename': 'app.log',
                    'formatter': 'default'
                }
            },
            'root': {
                'level': 'INFO',
                'handlers': ['wsgi', 'file']
            }
        })
        logger.info("[LOGGING] Logging configured successfully")
    except Exception as e:
        logger.error(f"[LOGGING] Error configuring logging: {e}")
        raise

def monitor_app_context(app):
    """Add listeners to monitor application context lifecycle"""
    try:
        @app.before_request
        def log_request_context():
            logger.info(f"[APP_CONTEXT] {time.time()} - Request context created for: {request.path}")

        def log_app_context_pushed(sender, **extra):
            logger.info(f"[APP_CONTEXT] {time.time()} - Application context pushed")

        def log_app_context_popped(sender, **extra):
            logger.info(f"[APP_CONTEXT] {time.time()} - Application context popped")

        def log_request_started(sender, **extra):
            logger.info(f"[APP_CONTEXT] {time.time()} - Request started")

        appcontext_pushed.connect(log_app_context_pushed, app)
        appcontext_popped.connect(log_app_context_popped, app)
        request_started.connect(log_request_started, app)
        logger.info("[APP_INIT] Context monitoring registered")
    except Exception as e:
        logger.error(f"[APP_INIT] Error setting up context monitoring: {e}")
        raise

def create_app():
    """
    Application factory function that creates and configures the Flask application.
    
    Returns:
        Flask application instance
    """
    # Configure logging
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("[APP_INIT] Starting application initialization")

    # Log Python and package versions
    try:
        logger.info(f"[APP_INIT] Python version: {sys.version}")
        logger.info(f"[APP_INIT] Flask version: {pkg_resources.get_distribution('flask').version}")
        logger.info(f"[APP_INIT] pytrends version: {pkg_resources.get_distribution('pytrends').version}")
        logger.info(f"[APP_INIT] requests version: {pkg_resources.get_distribution('requests').version}")
        logger.info(f"[APP_INIT] urllib3 version: {pkg_resources.get_distribution('urllib3').version}")
    except Exception as e:
        logger.error(f"[APP_INIT] Error logging package versions: {e}")

    # Create Flask application
    try:
        app = Flask(__name__)
        logger.info(f"[APP_CONTEXT] {time.time()} - Flask application instance created")
    except Exception as e:
        logger.error(f"[APP_INIT] Failed to create Flask app: {e}")
        raise

    # Enable CORS
    try:
        CORS(app)
        logger.info("[APP_INIT] CORS enabled")
    except Exception as e:
        logger.error(f"[APP_INIT] Failed to enable CORS: {e}")
        raise

    # Detect environment
    try:
        is_production = os.environ.get('RENDER', 'False') in ('true', 'True', '1')
        logger.info(f"[APP_ENV] Running in {'production' if is_production else 'development'} mode")
        
        if not is_production:
            logger.info("[ENV_LOADING] Loading environment from .env file (development mode)")
            load_dotenv()
        else:
            logger.info("[ENV_LOADING] Using environment variables directly (production mode)")
        log_environment_variables()
    except Exception as e:
        logger.error(f"[ENV_LOADING] Error detecting environment: {e}")

    # Configure app from environment variables
    try:
        logger.info(f"[APP_CONFIG] {time.time()} - Setting up Flask configuration")
        app.config.update(
            OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY', ''),
            NEWSAPI_ORG_KEY=os.environ.get('NEWSAPI_ORG_KEY', ''),
            GUARDIAN_API_KEY=os.environ.get('GUARDIAN_API_KEY', ''),
            AYLIEN_APP_ID=os.environ.get('AYLIEN_APP_ID', ''),
            AYLIEN_API_KEY=os.environ.get('AYLIEN_API_KEY', ''),
            GNEWS_API_KEY=os.environ.get('GNEWS_API_KEY', ''),
            NEWSAPI_AI_KEY=os.environ.get('NEWSAPI_AI_KEY', ''),
            MEDIASTACK_API_KEY=os.environ.get('MEDIASTACK_API_KEY', ''),
            NYT_API_KEY=os.environ.get('NYT_API_KEY', ''),
            USE_OPENAI=bool(os.environ.get('OPENAI_API_KEY')),
            USE_NEWSAPI_ORG=bool(os.environ.get('NEWSAPI_ORG_KEY')),
            USE_GUARDIAN=bool(os.environ.get('GUARDIAN_API_KEY')),
            USE_GNEWS=bool(os.environ.get('GNEWS_API_KEY')),
            USE_NYT=bool(os.environ.get('NYT_API_KEY')),
            USE_MEDIASTACK=bool(os.environ.get('MEDIASTACK_API_KEY')),
            USE_NEWSAPI_AI=bool(os.environ.get('NEWSAPI_AI_KEY')),
            USE_AYLIEN=bool(os.environ.get('AYLIEN_APP_ID') and os.environ.get('AYLIEN_API_KEY')),
            NEWSAPI_ENDPOINT='https://newsapi.org/v2',
            GUARDIAN_ENDPOINT='https://content.guardianapis.com',
            GNEWS_ENDPOINT='https://gnews.io/api/v4',
            MODEL_NAME='distilbert-base-uncased-finetuned-sst-2-english',
            MAX_ARTICLES_PER_API=4,
            DEFAULT_TOP_N=3,
            DEFAULT_DAYS_BACK=7,
            SUMMARIZER_BY_GPT=1
        )
        logger.info(f"[APP_CONFIG] {time.time()} - Finished setting up Flask configuration")

        for key in ['NEWSAPI_ORG_KEY', 'GUARDIAN_API_KEY', 'OPENAI_API_KEY', 'MAX_ARTICLES_PER_API', 'DEFAULT_DAYS_BACK']:
            logger.info(f"[APP_CONFIG] Config key '{key}' is {'set' if key in app.config else 'NOT set'}")
            if key in app.config and key.endswith('_KEY'):
                logger.info(f"[APP_CONFIG] Config key '{key}' length: {len(app.config.get(key, ''))}")
    except Exception as e:
        logger.error(f"[APP_CONFIG] Error configuring app: {e}")
        raise

    # Log API availability
    try:
        logger.info("[API_AVAILABILITY] API availability:")
        logger.info(f"[API_AVAILABILITY] NewsAPI.org: {'Enabled' if app.config['USE_NEWSAPI_ORG'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] Guardian: {'Enabled' if app.config['USE_GUARDIAN'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] GNews: {'Enabled' if app.config['USE_GNEWS'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] NYT: {'Enabled' if app.config['USE_NYT'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] Mediastack: {'Enabled' if app.config['USE_MEDIASTACK'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] NewsAPI.ai: {'Enabled' if app.config['USE_NEWSAPI_AI'] else 'Disabled'}")
        logger.info(f"[API_AVAILABILITY] Aylien: {'Enabled' if app.config['USE_AYLIEN'] else 'Disabled'}")
    except Exception as e:
        logger.error(f"[API_AVAILABILITY] Error logging API availability: {e}")

    # Register error handlers
    try:
        @app.errorhandler(404)
        def not_found_error(error):
            return {"error": "Not found"}, 404

        @app.errorhandler(500)
        def internal_error(error):
            return {"error": "Internal server error"}, 500
        logger.info("[APP_INIT] Error handlers registered")
    except Exception as e:
        logger.error(f"[APP_INIT] Error registering error handlers: {e}")
        raise

    # Set up context monitoring
    try:
        monitor_app_context(app)
    except Exception as e:
        logger.error(f"[APP_INIT] Failed to set up context monitoring: {e}")
        raise

    # Register routes
    try:
        logger.info(f"[IMPORT_SEQUENCE] {time.time()} - About to import routes module")
        from routes import routes
        logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Finished importing routes module")
        
        logger.info(f"[APP_INIT] {time.time()} - About to register routes blueprint")
        app.register_blueprint(routes)
        logger.info(f"[APP_INIT] {time.time()} - Finished registering routes blueprint")
    except Exception as e:
        logger.error(f"[APP_INIT] Error importing or registering routes: {e}", exc_info=True)
        raise

    logger.info("[APP_INIT] Application initialization complete")
    return app

# Create the Flask app at module level for Gunicorn
try:
    app = create_app()
    logger.info(f"[APP_SETUP] Flask app created and configured: {app}")
except Exception as e:
    logger.error(f"[APP_SETUP] Failed to create app: {e}", exc_info=True)
    raise

logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Reached end of app.py module definition")

if __name__ == '__main__':
    logger.info(f"[APP_RUN] {time.time()} - Running app directly through __main__")
    load_dotenv()
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"[APP_RUN] Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'))
else:
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - app.py imported, not run directly")