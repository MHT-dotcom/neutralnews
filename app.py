"""
Neutral News MVP Application

This module implements the main Flask application for serving news articles
with sentiment analysis and summarization.
"""

import os
import sys
import logging
import pkg_resources
from logging.config import dictConfig
from dotenv import load_dotenv

# Setup basic logging before any imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log diagnostic information
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")
logger.info(f"Python path: {sys.path}")

# Log installed packages
logger.info("Installed packages:")
installed_packages = [f"{dist.key} {dist.version}" for dist in pkg_resources.working_set]
logger.info("\n".join(installed_packages))

# Log requirements.txt content
try:
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
        logger.info(f"requirements.txt contents:\n{requirements}")
except Exception as e:
    logger.error(f"Error reading requirements.txt: {e}")

from flask import Flask
from flask_cors import CORS
from flask_caching import Cache

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
    logger.info("Starting application initialization")
    
    # Log Python and package versions to identify compatibility issues
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Flask version: {pkg_resources.get_distribution('flask').version}")
    
    try:
        pytrends_version = pkg_resources.get_distribution('pytrends').version
        logger.info(f"pytrends version: {pytrends_version}")
        
        # Log requests and urllib3 versions (often cause compatibility issues)
        requests_version = pkg_resources.get_distribution('requests').version
        urllib3_version = pkg_resources.get_distribution('urllib3').version
        logger.info(f"requests version: {requests_version}")
        logger.info(f"urllib3 version: {urllib3_version}")
    except Exception as e:
        logger.error(f"Error getting package versions: {e}")
    
    # Create Flask application
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Detect environment (development or production)
    is_production = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)
    logger.info(f"Running in {'production' if is_production else 'development'} mode")
    
    # First try environment variables directly (for Render/production)
    # Then fall back to .env file (for local development)
    if not is_production:
        logger.info("Loading environment from .env file (development mode)")
        from dotenv import load_dotenv
        load_dotenv()
    else:
        logger.info("Using environment variables directly (production mode)")
    
    # Log all environment variables (safely)
    log_environment_variables()
    
    # Log environment API keys (existence only, not values)
    logger.info("API Key Status:")
    logger.info(f"  NEWSAPI_ORG_KEY exists: {bool(os.environ.get('NEWSAPI_ORG_KEY'))}")
    logger.info(f"  GUARDIAN_API_KEY exists: {bool(os.environ.get('GUARDIAN_API_KEY'))}")
    logger.info(f"  OPENAI_API_KEY exists: {bool(os.environ.get('OPENAI_API_KEY'))}")
    
    # Configure from environment variables
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
        DEFAULT_TOP_N=3
    )
    
    # Initialize extensions
    # cache.init_app(app)  # Temporarily disabled for faster builds
    
    # Log API availability
    logger.info("API availability:")
    logger.info(f"  NewsAPI.org: {'Enabled' if app.config['USE_NEWSAPI_ORG'] else 'Disabled'}")
    logger.info(f"  Guardian: {'Enabled' if app.config['USE_GUARDIAN'] else 'Disabled'}")
    logger.info(f"  GNews: {'Enabled' if app.config['USE_GNEWS'] else 'Disabled'}")
    logger.info(f"  NYT: {'Enabled' if app.config['USE_NYT'] else 'Disabled'}")
    logger.info(f"  Mediastack: {'Enabled' if app.config['USE_MEDIASTACK'] else 'Disabled'}")
    logger.info(f"  NewsAPI.ai: {'Enabled' if app.config['USE_NEWSAPI_AI'] else 'Disabled'}")
    logger.info(f"  Aylien: {'Enabled' if app.config['USE_AYLIEN'] else 'Disabled'}")
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    # Register routes
    from routes import routes
    app.register_blueprint(routes)
    
    logger.info("Application factory initialization complete")
    return app

def log_environment_variables():
    """Log all environment variables (presence only, not values) to help with debugging."""
    logger = logging.getLogger(__name__)
    import os
    
    # Get all environment variables
    env_vars = os.environ
    
    # List of sensitive keys (partial matches) to mask
    sensitive_keys = ['key', 'password', 'secret', 'token', 'auth']
    
    # Count how many are potentially API keys or credentials
    api_keys_count = 0
    other_vars_count = 0
    
    logger.info("Environment Variables (masked for security):")
    
    # Log existence of each variable (but not its value)
    for key in sorted(env_vars.keys()):
        # Check if this might be a sensitive value
        is_sensitive = any(sensitive_word in key.lower() for sensitive_word in sensitive_keys)
        
        # For sensitive keys, just log that they exist
        if is_sensitive:
            api_keys_count += 1
        else:
            other_vars_count += 1
    
    # Log the counts
    logger.info(f"Found {api_keys_count} potential API keys/credentials and {other_vars_count} other environment variables")
    
    # Check specifically for known required API keys
    api_keys = [
        'NEWSAPI_ORG_KEY',
        'GUARDIAN_API_KEY', 
        'OPENAI_API_KEY',
        'GNEWS_API_KEY',
        'NYT_API_KEY',
        'AYLIEN_APP_ID',
        'AYLIEN_API_KEY',
        'MEDIASTACK_API_KEY',
        'NEWSAPI_AI_KEY'
    ]
    
    missing_keys = [key for key in api_keys if not os.environ.get(key)]
    if missing_keys:
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
    else:
        logger.info("All known API keys are present in environment variables")

# Create the application instance
app = create_app()

if __name__ == '__main__':
    import os
    
    # Get port from environment variable or use default
    # Render sets PORT environment variable
    port = int(os.environ.get('PORT', 10000))
    
    # Make sure to bind to 0.0.0.0 for proper Render connectivity
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '0') == '1')
    logger.info(f"Application starting on port {port}")