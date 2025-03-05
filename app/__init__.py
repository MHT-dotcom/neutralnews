"""
Neutral News MVP Application Factory

This module implements the application factory pattern for the Quart application.
It provides flexibility in creating multiple instances with different configurations
and better support for testing.
"""

import os
from quart import Quart
from quart_cors import cors
from flask_caching import Cache
from logging.config import dictConfig
import logging
from .config import Config, ProductionConfig

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
    
    # Register blueprints
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    logger.info("Application factory initialization complete")
    return app

# Create the application instance for ASGI servers
app = create_app()

# Make the app instance importable
__all__ = ['app', 'create_app', 'cache'] 