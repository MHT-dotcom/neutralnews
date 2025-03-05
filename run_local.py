#!/usr/bin/env python
"""
Local development server script for Neutral News.
This script uses the local configuration from config.py instead of config_prod.py.
"""

import os
import sys
import logging
import flask
from flask import Flask
from flask_cors import CORS
from flask_caching import Cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info("Starting Neutral News application in LOCAL mode")

# Import local configuration
from config import (
    cache, MAX_ARTICLES_PER_SOURCE, CACHE_CONFIG,
    USE_NEWSAPI_ORG, USE_GUARDIAN, USE_GNEWS, USE_NYT,
    USE_MEDIASTACK, USE_NEWSAPI_AI, USE_AYLIEN
)

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)  # Enable CORS

# Configure cache
app.config.from_mapping(CACHE_CONFIG or {'CACHE_TYPE': 'SimpleCache'})
logger.info(f"Cache config set: {app.config.get('CACHE_TYPE', 'Not configured')}")
cache.init_app(app)  # Initialize cache with app
logger.info(f"Cache initialized: {cache}")

# Import the processors module after app initialization
from processors import ModelManager

# Preload sentiment model at startup
logger.info("Preloading sentiment analysis model...")
ModelManager.get_instance()  # Trigger preloading here
logger.info("Sentiment analysis model preloaded")

# Log API availability
logger.info("API availability:")
logger.info(f"  NewsAPI.org: {'Enabled' if USE_NEWSAPI_ORG else 'Disabled'}")
logger.info(f"  Guardian: {'Enabled' if USE_GUARDIAN else 'Disabled'}")
logger.info(f"  GNews: {'Enabled' if USE_GNEWS else 'Disabled'}")
logger.info(f"  NYT: {'Enabled' if USE_NYT else 'Disabled'}")
logger.info(f"  Mediastack: {'Enabled' if USE_MEDIASTACK else 'Disabled'}")
logger.info(f"  NewsAPI.ai: {'Enabled' if USE_NEWSAPI_AI else 'Disabled'}")
logger.info(f"  Aylien: {'Enabled' if USE_AYLIEN else 'Disabled'}")

# Import routes after app initialization to avoid circular imports
from routes import routes
app.register_blueprint(routes)

logger.info("Routes blueprint registered")
logger.info(f"Available routes: {app.url_map}")

if __name__ == "__main__":
    # Get port from environment variable or default to 10000
    port = int(os.environ.get("PORT", 10000))
    debug = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t")
    
    logger.info(f"Starting local development server on port {port} (debug={debug})")
    try:
        app.run(host="0.0.0.0", port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}") 