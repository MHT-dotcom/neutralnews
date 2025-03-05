"""
Neutral News MVP Application

This module implements the main Flask application for serving news articles
with sentiment analysis and summarization.
"""

import os
import sys
import logging
from logging.config import dictConfig

# Setup basic logging before any imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log diagnostic information
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")
logger.info(f"Python path: {sys.path}")

from flask import Flask
from flask_cors import CORS
from flask_caching import Cache

__version__ = '0.1.0'

# Initialize cache with default config
cache = Cache()

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
    logger = logging.getLogger(__name__)
    logger.info("Creating application with factory pattern")
    
    # Create Flask app instance
    app = Flask(__name__)
    
    # Configure from environment variables
    app.config.update(
        # Cache settings
        CACHE_TYPE='simple',
        CACHE_DEFAULT_TIMEOUT=300,
        
        # API Keys
        NEWSAPI_ORG_KEY=os.environ.get('NEWSAPI_ORG_KEY', ''),
        GUARDIAN_API_KEY=os.environ.get('GUARDIAN_API_KEY', ''),
        AYLIEN_APP_ID=os.environ.get('AYLIEN_APP_ID', ''),
        AYLIEN_API_KEY=os.environ.get('AYLIEN_API_KEY', ''),
        GNEWS_API_KEY=os.environ.get('GNEWS_API_KEY', ''),
        NEWSAPI_AI_KEY=os.environ.get('NEWSAPI_AI_KEY', ''),
        MEDIASTACK_API_KEY=os.environ.get('MEDIASTACK_API_KEY', ''),
        NYT_API_KEY=os.environ.get('NYT_API_KEY', ''),
        
        # Feature flags based on API key availability
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
    
    # Enable CORS
    CORS(app)
    
    # Initialize extensions
    cache.init_app(app)
    
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

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )