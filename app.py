# # todo: 
# # - add newyorktimes api
import flask
from flask import Flask
from routes import routes
import logging
from config import cache, MAX_ARTICLES_PER_SOURCE  # Ensure cache is imported from config
import sys
from flask_cors import CORS  # Add CORS support

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure cache
cache.init_app(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log initial startup
logger.info("Starting Neutral News application")
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")

# Check if cache is initialized before accessing its config
if cache:
    logger.info(f"Cache type: {cache.config.get('CACHE_TYPE', 'Not configured')}")
else:
    logger.warning("Cache is not initialized.")

# Register the routes blueprint
logger.info("About to register routes blueprint")
logger.info(f"Available routes before registration: {app.url_map}")
app.register_blueprint(routes)
logger.info("Routes blueprint registered")
logger.info(f"Available routes after registration: {app.url_map}")
logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")

if __name__ == '__main__':
    logger.info("Application configuration complete, starting server")
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)  # Enable debug mode
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")