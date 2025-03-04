import flask
from flask import Flask
from dotenv import load_dotenv
import os
import logging
import sys
from flask_cors import CORS
from flask_caching import Cache
import importlib

# Load environment variables from .env.test if it exists
if os.path.exists('.env.test'):
    load_dotenv('.env.test')
else:
    load_dotenv()  # Fallback to regular .env

# Determine which config to use based on environment variable
config_module_name = os.getenv('FLASK_CONFIG', 'config_test')
config_module = importlib.import_module(config_module_name)

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)  # Enable CORS

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for testing
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info(f"Starting Neutral News application in TEST mode using config: {config_module_name}")

# Configure cache properly
CACHE_CONFIG = getattr(config_module, 'CACHE_CONFIG', {'CACHE_TYPE': 'SimpleCache'})
app.config.from_mapping(CACHE_CONFIG)
logger.info(f"Test cache config set: {CACHE_CONFIG}")
cache = Cache(app)  # Initialize cache with app
logger.info(f"Test cache initialized: {cache}")

# Preload sentiment model at startup if not in mock mode
MOCK_MODELS = getattr(config_module, 'MOCK_MODELS', False)
if not MOCK_MODELS:
    logger.info("Preloading sentiment analysis model...")
    from processors import ModelManager
    ModelManager.get_instance()  # Trigger preloading here
    logger.info("Sentiment analysis model preloaded")
else:
    logger.info("Using mock models for testing")

# Log initial startup details
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")
logger.info(f"Cache type: {CACHE_CONFIG.get('CACHE_TYPE', 'Not configured')}")
logger.info(f"Debug mode: {getattr(config_module, 'DEBUG', True)}")
logger.info(f"Max articles per source: {getattr(config_module, 'MAX_ARTICLES_PER_SOURCE', 'Not configured')}")

# Import routes after app initialization to avoid circular imports
from routes import routes
app.register_blueprint(routes)

logger.info("Routes blueprint registered")
logger.info(f"Available routes after registration: {app.url_map}")

# Application fully initialized
logger.info("Test application fully initialized")

if __name__ == "__main__":
    # Get port from environment variable or default to 10001 (different from production)
    port = int(os.environ.get("TEST_PORT", 10001))
    logger.info(f"Test application configuration complete, starting server on port {port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start test server: {str(e)}") 