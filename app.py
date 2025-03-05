# This file initializes the Flask application, sets up logging, loads environment variables, 
# preloads the sentiment analysis model, and registers the routes blueprint.

import flask
from flask import Flask
from dotenv import load_dotenv
import os
import logging
import sys
from flask_cors import CORS
from flask_caching import Cache
from config_prod import MAX_ARTICLES_PER_SOURCE, DEBUG, CACHE_CONFIG
from processors import ModelManager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)  # Enable CORS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info("Starting Neutral News application")

# Configure cache
app.config.from_mapping(CACHE_CONFIG)
logger.info(f"Cache config set: {CACHE_CONFIG}")
cache = Cache(app)
logger.info(f"Cache initialized: {cache}")

# Preload sentiment model at startup
logger.info("Preloading sentiment analysis model...")
ModelManager.get_instance()
logger.info("Sentiment analysis model preloaded")

# Log initial startup details
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")
logger.info(f"Cache type: {CACHE_CONFIG.get('CACHE_TYPE', 'Not configured')}")
logger.info(f"Debug mode: {DEBUG}")
logger.info(f"Max articles per source: {MAX_ARTICLES_PER_SOURCE}")

# Register routes blueprint
from routes import routes
app.register_blueprint(routes)
logger.info("Routes blueprint registered")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=DEBUG)