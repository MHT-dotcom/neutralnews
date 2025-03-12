# app.py
import flask
from flask import Flask, render_template
from dotenv import load_dotenv
import os
import logging
import sys
from flask_cors import CORS
from processors import ModelManager
from fetchers import fetch_grok_trending_topics

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Load environment variables
# Load environment variables with explicit path
env_path = '/Users/maxteeuwen/neutralnews/.env'
logger.info(f"Loading .env from: {env_path}")
load_dotenv(env_path)
logger.info(f".env loaded. GROK_API_KEY from os.environ: {os.environ.get('GROK_API_KEY', 'Not found')}")

# Check environment variables loading
logger.info("Checking API key availability:")

from config_prod import (
    NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, 
    NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
    NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
    GROK_API_KEY
)

logger.info(f"NEWSAPI_ORG_KEY available: {'Yes' if NEWSAPI_ORG_KEY else 'No'}")
logger.info(f"GUARDIAN_API_KEY available: {'Yes' if GUARDIAN_API_KEY else 'No'}")
logger.info(f"GNEWS_API_KEY available: {'Yes' if GNEWS_API_KEY else 'No'}")
logger.info(f"NYT_API_KEY available: {'Yes' if NYT_API_KEY else 'No'}")
logger.info(f"OPENAI_API_KEY available: {'Yes' if OPENAI_API_KEY else 'No'}")
logger.info(f"MEDIASTACK_API_KEY available: {'Yes' if MEDIASTACK_API_KEY else 'No'}")
logger.info(f"NEWSDATA_API_KEY available: {'Yes' if NEWSDATA_API_KEY else 'No'}")
logger.info(f"AYLIEN keys available: {'Yes' if AYLIEN_APP_ID and AYLIEN_API_KEY else 'No'}")
logger.info(f"GROK_API_KEY available: {'Yes' if GROK_API_KEY else 'No'}")

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

# Preload sentiment model at startup
logger.info("Preloading sentiment analysis model...")
ModelManager.get_instance()  # Trigger preloading here
logger.info("Sentiment analysis model preloaded")

# Import configuration
from config_prod import cache, CACHE_CONFIG, MAX_ARTICLES_PER_SOURCE, DEBUG

# Configure cache
cache.init_app(app, config=CACHE_CONFIG)
cache.clear()  # Clear cache on startup
logger.info("Cache cleared on startup")

# Global trending topics
# trending_topics = ["Bitcoin", "Climate", "Elections", "Economy"]  # Fallback

def update_trending_topics():
    """Fetch trending topics from Grok API at startup."""
    global trending_topics
    topics = fetch_grok_trending_topics(max_topics=8)  # Fetch 8 topics as per your latest request
    if topics:
        trending_topics = topics  # Now a list of [event, keywords] pairs
    logger.info(f"Trending topics set to: {trending_topics}")

# Run at startup
update_trending_topics()
# logger.info(f"Trending topics set to: {trending_topics}")

# Log initial startup details
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")
logger.info(f"Cache type: {CACHE_CONFIG.get('CACHE_TYPE', 'Not configured')}")

# Register the routes blueprint with a unique name
logger.info("About to register routes blueprint")
logger.info(f"Available routes before registration: {app.url_map}")
from routes import routes
app.register_blueprint(routes, name='news_routes')
logger.info("Routes blueprint registered")
logger.info(f"Available routes after registration: {app.url_map}")
logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")


# Add a basic route to render the template (assuming this was in routes.py before)
@app.route('/')
def index():
    logger.info(f"Passing trending_data to template: {trending_topics}")
    return render_template(
        'index.html',
        trending_data=trending_topics,  # Pass the 2D list directly
        event=None,  # Adjust as needed based on your app logic
        summary=None,
        articles=None,
        error=None
    )

# Application fully initialized
logger.info("Application fully initialized")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Application configuration complete, starting server on port {port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=DEBUG)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")