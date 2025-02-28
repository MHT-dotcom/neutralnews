# # todo: 
# # - add newyorktimes api
import flask
from flask import Flask
from routes import routes
import logging
from config import cache, MAX_ARTICLES_PER_SOURCE  # Ensure cache is imported from config
import sys
from flask_cors import CORS  # Add CORS support
import argparse  # Add argument parser
import os

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

try:
    from config import DEBUG
except ImportError:
    from config_prod import DEBUG

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Neutral News application')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
    port = int(os.environ.get("PORT", 5002))
    logger.info(f"Application configuration complete, starting server on port {port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=DEBUG)  # Enable debug mode
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")