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

# Setup basic logging before any imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log diagnostic information
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")
logger.info(f"Python path: {sys.path}")

# Add detailed timestamps for import sequence tracking
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Starting app.py before any module imports")

# Log loaded environment variables (safely, without values)
def log_environment_variables():
    """Log available environment variables (safely, without exposing values)"""
    env_vars = os.environ.keys()
    logger.info(f"[ENV_VARS] Total environment variables: {len(env_vars)}")
    
    # Count potential API keys (variables with KEY, API, TOKEN in the name)
    api_key_vars = [v for v in env_vars if any(x in v.upper() for x in ['KEY', 'API', 'TOKEN'])]
    logger.info(f"[ENV_VARS] Potential API key variables: {len(api_key_vars)}")
    
    # Log specifically the existence of our known API keys
    known_keys = ['NEWSAPI_ORG_KEY', 'GUARDIAN_API_KEY', 'AYLIEN_APP_ID', 'AYLIEN_API_KEY', 
                  'GNEWS_API_KEY', 'NEWSAPI_AI_KEY', 'MEDIASTACK_API_KEY', 'OPENAI_API_KEY', 'NYT_API_KEY']
    
    for key in known_keys:
        exists = key in os.environ
        value_length = len(os.environ.get(key, '')) if exists else 0
        logger.info(f"[ENV_VARS] {key}: {'✓' if exists else '✗'} (length: {value_length})")

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

# Log before importing Flask modules
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - About to import Flask modules")

from flask import Flask, g, request_started
from flask_cors import CORS
from flask_caching import Cache

# Log after importing Flask modules
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Finished importing Flask modules")

__version__ = '0.1.0'

# Initialize cache with default config
# cache = Cache()  # Temporarily disabled for faster builds

def configure_logging():
    """Configure logging for the application"""
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

# Track when the application context is created and destroyed
def monitor_app_context(app):
    """Add listeners to monitor application context lifecycle"""
    
    @app.before_request
    def log_request_context():
        logger.info(f"[APP_CONTEXT] {time.time()} - Request context created for: {request.path}")
    
    def log_app_context_pushed(sender, **extra):
        logger.info(f"[APP_CONTEXT] {time.time()} - Application context pushed")
        
    def log_app_context_popped(sender, **extra):
        logger.info(f"[APP_CONTEXT] {time.time()} - Application context popped")
        
    def log_request_started(sender, **extra):
        logger.info(f"[APP_CONTEXT] {time.time()} - Request started")
    
    # Register the signal handlers
    from flask import appcontext_pushed, appcontext_popped
    appcontext_pushed.connect(log_app_context_pushed, app)
    appcontext_popped.connect(log_app_context_popped, app)
    request_started.connect(log_request_started, app)

def create_app():
    """
    Application factory function that creates and configures the Flask application.
    
    Returns:
        Flask application instance
    """
    # Configure logging first
    configure_logging()
    
    # Basic diagnostic logging
    import sys
    import os
    import logging
    import pkg_resources
    
    logger = logging.getLogger(__name__)
    logger.info("[APP_INIT] Starting application initialization")
    
    # Log Python and package versions to identify compatibility issues
    logger.info(f"[APP_INIT] Python version: {sys.version}")
    logger.info(f"[APP_INIT] Flask version: {pkg_resources.get_distribution('flask').version}")
    
    try:
        pytrends_version = pkg_resources.get_distribution('pytrends').version
        logger.info(f"[APP_INIT] pytrends version: {pytrends_version}")
        
        # Log requests and urllib3 versions (often cause compatibility issues)
        requests_version = pkg_resources.get_distribution('requests').version
        urllib3_version = pkg_resources.get_distribution('urllib3').version
        logger.info(f"[APP_INIT] requests version: {requests_version}")
        logger.info(f"[APP_INIT] urllib3 version: {urllib3_version}")
    except Exception as e:
        logger.error(f"[APP_INIT] Error getting package versions: {e}")
    
    # Create Flask application
    app = Flask(__name__)
    
    # Set up context monitoring
    monitor_app_context(app)
    
    # Log when the app is created
    logger.info(f"[APP_CONTEXT] {time.time()} - Flask application instance created")
    
    # Enable CORS
    CORS(app)
    
    # Detect environment (development or production)
    is_production = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)
    logger.info(f"[APP_ENV] Running in {'production' if is_production else 'development'} mode")
    
    # First try environment variables directly (for Render/production)
    # Then fall back to .env file (for local development)
    if not is_production:
        logger.info("[ENV_LOADING] Loading environment from .env file (development mode)")
        from dotenv import load_dotenv
        load_dotenv()
    else:
        logger.info("[ENV_LOADING] Using environment variables directly (production mode)")
    
    # Log all environment variables (safely)
    log_environment_variables()
    
    # Log environment API keys (existence only, not values)
    logger.info("[API_KEYS] API Key Status:")
    for key_name in ['NEWSAPI_ORG_KEY', 'GUARDIAN_API_KEY', 'OPENAI_API_KEY', 'GNEWS_API_KEY', 
                    'NYT_API_KEY', 'AYLIEN_API_KEY', 'AYLIEN_APP_ID', 'MEDIASTACK_API_KEY', 'NEWSAPI_AI_KEY']:
        key_exists = bool(os.environ.get(key_name))
        key_length = len(os.environ.get(key_name, '')) if key_exists else 0
        logger.info(f"[API_KEYS] {key_name}: {'Available' if key_exists else 'Missing'} (length: {key_length})")
    
    # Configure from environment variables
    logger.info(f"[APP_CONFIG] {time.time()} - Setting up Flask configuration")
    app.config.update(
        # Cache settings
        # CACHE_TYPE='simple',  # Temporarily disabled for faster builds
        # CACHE_DEFAULT_TIMEOUT=300,  # Temporarily disabled for faster builds
        
        # API Keys
        OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY', ''),
        NEWSAPI_ORG_KEY=os.environ.get('NEWSAPI_ORG_KEY', ''),
        GUARDIAN_API_KEY=os.environ.get('GUARDIAN_API_KEY', ''),
        AYLIEN_APP_ID=os.environ.get('AYLIEN_APP_ID', ''),
        AYLIEN_API_KEY=os.environ.get('AYLIEN_API_KEY', ''),
        GNEWS_API_KEY=os.environ.get('GNEWS_API_KEY', ''),
        NEWSAPI_AI_KEY=os.environ.get('NEWSAPI_AI_KEY', ''),
        MEDIASTACK_API_KEY=os.environ.get('MEDIASTACK_API_KEY', ''),
        NYT_API_KEY=os.environ.get('NYT_API_KEY', ''),
        
        # Feature flags based on API key availability
        USE_OPENAI=bool(os.environ.get('OPENAI_API_KEY')),
        USE_NEWSAPI_ORG=bool(os.environ.get('NEWSAPI_ORG_KEY')),
        USE_GUARDIAN=bool(os.environ.get('GUARDIAN_API_KEY')),
        USE_GNEWS=bool(os.environ.get('GNEWS_API_KEY')),
        USE_NYT=bool(os.environ.get('NYT_API_KEY')),
        USE_MEDIASTACK=bool(os.environ.get('MEDIASTACK_API_KEY')),
        USE_NEWSAPI_AI=bool(os.environ.get('NEWSAPI_AI_KEY')),
        USE_AYLIEN=bool(os.environ.get('AYLIEN_APP_ID') and os.environ.get('AYLIEN_API_KEY')),
        
        # API endpoints
        NEWSAPI_ENDPOINT='https://newsapi.org/v2',
        GUARDIAN_ENDPOINT='https://content.guardianapis.com',
        GNEWS_ENDPOINT='https://gnews.io/api/v4',
        
        # Model settings
        MODEL_NAME='distilbert-base-uncased-finetuned-sst-2-english',
        
        # Default settings
        MAX_ARTICLES_PER_API=4,
        DEFAULT_TOP_N=3,
        DEFAULT_DAYS_BACK=7,
        SUMMARIZER_BY_GPT=1
    )
    logger.info(f"[APP_CONFIG] {time.time()} - Finished setting up Flask configuration")
    
    # Log if specific configuration keys were set
    for key in ['NEWSAPI_ORG_KEY', 'GUARDIAN_API_KEY', 'OPENAI_API_KEY', 'MAX_ARTICLES_PER_API', 'DEFAULT_DAYS_BACK']:
        logger.info(f"[APP_CONFIG] Config key '{key}' is {'set' if key in app.config else 'NOT set'}")
        if key in app.config and key.endswith('_KEY'):
            logger.info(f"[APP_CONFIG] Config key '{key}' length: {len(app.config.get(key, ''))}")
    
    # Initialize extensions
    # cache.init_app(app)  # Temporarily disabled for faster builds
    
    # Log API availability
    logger.info("[API_AVAILABILITY] API availability:")
    logger.info(f"[API_AVAILABILITY] NewsAPI.org: {'Enabled' if app.config['USE_NEWSAPI_ORG'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] Guardian: {'Enabled' if app.config['USE_GUARDIAN'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] GNews: {'Enabled' if app.config['USE_GNEWS'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] NYT: {'Enabled' if app.config['USE_NYT'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] Mediastack: {'Enabled' if app.config['USE_MEDIASTACK'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] NewsAPI.ai: {'Enabled' if app.config['USE_NEWSAPI_AI'] else 'Disabled'}")
    logger.info(f"[API_AVAILABILITY] Aylien: {'Enabled' if app.config['USE_AYLIEN'] else 'Disabled'}")
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    # Log before registering routes
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - About to import routes module")
    
    # Register routes
    from routes import routes
    
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Finished importing routes module")
    logger.info(f"[APP_INIT] {time.time()} - About to register routes blueprint")
    
    app.register_blueprint(routes)
    
    logger.info(f"[APP_INIT] {time.time()} - Finished registering routes blueprint")
    logger.info("[APP_INIT] Application initialization complete")
    
    return app

# Create the Flask app at module level for Gunicorn
app = create_app()

# Log that the app is defined at module level
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Reached end of app.py module definition")

# Only execute this code when the file is run directly, not when imported
if __name__ == '__main__':
    # Log when the app is directly run
    logger.info(f"[APP_RUN] {time.time()} - Running app directly through __main__")
    
    # Load environment variables from .env file (optional, since create_app() already handles this)
    load_dotenv()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 10000))
    
    # Run the application with debug mode
    logger.info(f"[APP_RUN] Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'))
else:
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - app.py imported, not run directly")