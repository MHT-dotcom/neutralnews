# app.py
import flask
from flask import Flask
from dotenv import load_dotenv
import os
import logging
import sys
import sqlite3
import json
from datetime import date, timedelta
from flask_cors import CORS
from processors import ModelManager
from fetchers import fetch_grok_trending_topics

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = '/Users/maxteeuwen/neutralnews/.env'
logger.info(f"Loading .env from: {env_path}")
load_dotenv(env_path)
logger.info(f".env loaded. GROK_API_KEY from os.environ: {os.environ.get('GROK_API_KEY', 'Not found')}")

# Check environment variables
logger.info("Checking API key availability:")
from config_prod import (
    NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, 
    NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
    NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
    GROK_API_KEY
)

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)

def init_db():
    conn = sqlite3.connect('search_db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS search_history
                 (id INTEGER PRIMARY KEY, query TEXT NOT NULL, timestamp DATETIME NOT NULL,
                  summary TEXT, average_sentiment REAL, articles TEXT, source_distribution TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hot_topics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, topics TEXT NOT NULL, fetch_date DATE NOT NULL)''')
    try:
        c.execute("ALTER TABLE hot_topics ADD COLUMN period TEXT NOT NULL DEFAULT 'today'")
    except sqlite3.OperationalError:
        pass
    c.execute("UPDATE hot_topics SET period = 'today' WHERE period IS NULL")
    conn.commit()
    conn.close()

def get_hot_topics(period="today"):
    """Fetch trending topics from Grok API or retrieve from cache for a given period."""
    conn = sqlite3.connect('search_db.sqlite')
    cursor = conn.cursor()
    
    today = date.today()
    fetch_date = str(today) if period == "today" else str(today - timedelta(days=7))
    
    cursor.execute("SELECT topics FROM hot_topics WHERE period = ? AND fetch_date = ? ORDER BY id DESC LIMIT 1",
                   (period, fetch_date))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        logger.info(f"Using cached {period} trending topics from {fetch_date}")
        return json.loads(result[0])
    
    if period == "today":
        new_topics = fetch_grok_trending_topics(max_topics=8)
    else:  # last_week
        last_week_end = today - timedelta(days=1)
        last_week_start = last_week_end - timedelta(days=6)
        new_topics = fetch_grok_trending_topics(max_topics=8, 
                                               start_date=last_week_start.strftime("%Y-%m-%d"),
                                               end_date=last_week_end.strftime("%Y-%m-%d"))
    
    if new_topics:
        cursor.execute("INSERT INTO hot_topics (topics, fetch_date, period) VALUES (?, ?, ?)",
                       (json.dumps(new_topics), fetch_date, period))
        conn.commit()
        logger.info(f"Fetched and cached new {period} trending topics: {new_topics}")
    else:
        logger.warning(f"Failed to fetch {period} topics, using fallback")
        new_topics = [["No headline available", "no, keywords, available"]] * 8
    conn.close()
    return new_topics

# Initialize the database
with app.app_context():
    init_db()

# Preload sentiment model
logger.info("Preloading sentiment analysis model...")
ModelManager.get_instance()
logger.info("Sentiment analysis model preloaded")

# Import configuration
from config_prod import cache, CACHE_CONFIG, MAX_ARTICLES_PER_SOURCE, DEBUG

# Configure cache
cache.init_app(app, config=CACHE_CONFIG)
cache.clear()
logger.info("Cache cleared on startup")

# Global trending topics
today_topics = get_hot_topics("today")
last_week_topics = get_hot_topics("last_week")

# Log startup details
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")
logger.info(f"Cache type: {CACHE_CONFIG.get('CACHE_TYPE', 'Not configured')}")

# Register routes blueprint
logger.info("About to register routes blueprint")
logger.info(f"Available routes before registration: {app.url_map}")
logger.info("Starting app.py execution")
# ... existing code ...
logger.info("About to import routes module")
from routes import routes
logger.info("Successfully imported routes module")
app.register_blueprint(routes, name='news_routes')
logger.info("Routes blueprint registered")
logger.info(f"Available routes after registration: {app.url_map}")
logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")

# Application initialized
logger.info("Application fully initialized")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Application configuration complete, starting server on port {port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=DEBUG)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")