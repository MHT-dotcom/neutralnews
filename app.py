"""
Neutral News MVP Application

This module implements the main application using Quart.
It provides a Flask-like async web framework for serving news articles
with sentiment analysis and summarization.
"""

import os
from quart import Quart
from quart_cors import cors
from flask_caching import Cache
from logging.config import dictConfig
import logging
from config import Config, ProductionConfig

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

def create_app(config_object=None):
    """
    Application factory function that creates and configures the Quart application.
    
    Args:
        config_object: The configuration object or module to use. If None,
                      defaults to production config.
    
    Returns:
        Quart application instance
    """
    # Configure logging first
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Creating application with factory pattern")
    
    # Create Quart app instance with initial config
    app = Quart(__name__)
    app.config.from_object(Config)  # Load base config first
    
    # Configure the app with additional config if provided
    if config_object is None:
        # Default to production config if none specified
        logger.info("No config specified, using production config")
        app.config.from_object(ProductionConfig)
    else:
        logger.info(f"Loading config from: {config_object}")
        app.config.from_object(config_object)
    
    # Enable CORS
    app = cors(app)
    
    # Initialize extensions
    cache.init_app(app)
    
    # Register error handlers
    @app.errorhandler(404)
    async def not_found_error(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    async def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    # Register routes
    from routes import api_bp
    app.register_blueprint(api_bp)
    
    logger.info("Application factory initialization complete")
    return app

# Create the application instance for ASGI servers
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)