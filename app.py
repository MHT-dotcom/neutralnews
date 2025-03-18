# app.py
import flask
from flask import Flask, jsonify, request, g
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
import requests
import certifi
from datetime import datetime
from utils import secure_log_key  # Import the secure logging function
import threading
import time
import random

# Set up logging
logger = logging.getLogger('neutralnews')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG if os.getenv("FLASK_ENV") == "development" else logging.INFO)

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)

# Load environment variables - Use secure logging to mask API keys
grok_key = secure_log_key(os.getenv("GROK_API_KEY", "Not set"))
logger.info("Before .env load: GROK_API_KEY: %s", grok_key)
load_dotenv()  # Loads .env from current directory if present
grok_key = secure_log_key(os.getenv("GROK_API_KEY", "Not set"))
logger.info(".env loading attempted. GROK_API_KEY from os.environ: %s", grok_key)

# Determine base path for persistent storage
BASE_PATH = os.getenv("BASE_PATH", os.path.join(os.path.dirname(__file__), "data"))
DB_PATH = os.path.join(BASE_PATH, "search_db.sqlite")
IMAGE_DIR = os.path.join(BASE_PATH, "images")

# Ensure directories exist (locally and on Render)
os.makedirs(BASE_PATH, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# Export paths as app config for use in routes.py
app.config["DB_PATH"] = DB_PATH
app.config["IMAGE_DIR"] = IMAGE_DIR

# Log paths for debugging
logger.info("Using BASE_PATH: %s", BASE_PATH)
logger.info("Database path: %s", DB_PATH)
logger.info("Image directory: %s", IMAGE_DIR)

# Check environment variables
logger.info("Checking API key availability:")
from config_prod import (
    NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, 
    NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
    NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
    GROK_API_KEY, get_api_key_status
)

# Log API key availability securely
logger.info(f"NEWSAPI_ORG_KEY: {get_api_key_status('NEWSAPI_ORG_KEY', NEWSAPI_ORG_KEY)}")
logger.info(f"GUARDIAN_API_KEY: {get_api_key_status('GUARDIAN_API_KEY', GUARDIAN_API_KEY)}")
logger.info(f"GNEWS_API_KEY: {get_api_key_status('GNEWS_API_KEY', GNEWS_API_KEY)}")
logger.info(f"NYT_API_KEY: {get_api_key_status('NYT_API_KEY', NYT_API_KEY)}")
logger.info(f"OPENAI_API_KEY: {get_api_key_status('OPENAI_API_KEY', OPENAI_API_KEY)}")
logger.info(f"MEDIASTACK_API_KEY: {get_api_key_status('MEDIASTACK_API_KEY', MEDIASTACK_API_KEY)}")
logger.info(f"NEWSDATA_API_KEY: {get_api_key_status('NEWSDATA_API_KEY', NEWSDATA_API_KEY)}")
logger.info(f"AYLIEN keys: {get_api_key_status('AYLIEN', AYLIEN_APP_ID and AYLIEN_API_KEY)}")
logger.info(f"GROK_API_KEY: {get_api_key_status('GROK_API_KEY', GROK_API_KEY)}")

def init_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS search_history
                 (id INTEGER PRIMARY KEY, query TEXT NOT NULL, timestamp DATETIME NOT NULL,
                  summary TEXT, average_sentiment REAL, articles TEXT, source_distribution TEXT, image_path TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hot_topics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, topics TEXT NOT NULL, fetch_date DATE NOT NULL)''')
    try:
        c.execute("ALTER TABLE hot_topics ADD COLUMN period TEXT NOT NULL DEFAULT 'today'")
    except sqlite3.OperationalError:
        pass
    c.execute("UPDATE hot_topics SET period = 'today' WHERE period IS NULL")
    
    # Add search_count column for image caching if not exists
    try:
        c.execute("ALTER TABLE search_history ADD COLUMN search_count INTEGER DEFAULT 1")
        logger.info("Added search_count column to search_history")
    except sqlite3.OperationalError:
        logger.info("search_count column already exists")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", app.config["DB_PATH"])

def get_hot_topics(period="today"):
    """Fetch trending topics from Grok API or retrieve from cache for a given period."""
    conn = sqlite3.connect(app.config["DB_PATH"])
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

# Function to pregenerate images for trending topics
def initialize_trending_images():
    """Initialize image generation for trending topics."""
    logger.info("Starting trending image pre-generation...")
    try:
        from get_img import pregenerate_trending_images
        
        # Get trending topics
        today_topics = get_hot_topics("today")
        last_week_topics = get_hot_topics("last_week")
        
        # Pre-generate images for both sets
        with app.app_context():
            pregenerate_trending_images(today_topics)
            pregenerate_trending_images(last_week_topics)
        
        logger.info("Trending image pre-generation tasks started")
    except Exception as e:
        logger.error(f"Error initializing trending images: {str(e)}")

# Background task to optimize image storage periodically
def run_periodic_image_optimization(interval_hours=24):
    """Run image storage optimization periodically."""
    def optimization_worker():
        logger.info("Starting periodic image optimization worker")
        from get_img import optimize_image_storage
        
        while True:
            try:
                # Sleep first to avoid immediate optimization on startup
                time.sleep(interval_hours * 3600)
                
                logger.info("Running scheduled image storage optimization")
                with app.app_context():
                    # Optimize with 30-day retention and 500MB target size
                    optimize_image_storage(max_age_days=30, target_size_mb=500)
                
                logger.info(f"Image optimization complete, next run in {interval_hours} hours")
            except Exception as e:
                logger.error(f"Error in image optimization worker: {str(e)}")
                # Continue loop even after error
    
    # Start background thread
    thread = threading.Thread(target=optimization_worker)
    thread.daemon = True
    thread.start()
    logger.info(f"Image optimization scheduler started (interval: {interval_hours} hours)")

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

# Start image cache system and optimization task
if not DEBUG:
    # Only run these in production to avoid consuming resources during development
    run_periodic_image_optimization(interval_hours=12)  # Run every 12 hours
    
    # Delay the trending image initialization slightly to let app start up
    def delayed_image_init():
        time.sleep(30)  # 30 second delay
        initialize_trending_images()
    
    threading.Thread(target=delayed_image_init, daemon=True).start()
    logger.info("Scheduled delayed trending image initialization")

# Log startup details
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask version: {flask.__version__}")
logger.info(f"Cache type: {CACHE_CONFIG.get('CACHE_TYPE', 'Not configured')}")

# Register routes blueprint
logger.info("About to register routes blueprint")
logger.info(f"Available routes before registration: {app.url_map}")
logger.info("Starting app.py execution")
logger.info("About to import routes module")
from routes import routes
logger.info("Successfully imported routes module")
app.register_blueprint(routes, name='news_routes')
logger.info("Routes blueprint registered")
logger.info(f"Available routes after registration: {app.url_map}")
logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")

# Application initialized
logger.info("Application fully initialized")

@app.before_request
def log_cache_usage():
    if hasattr(app, 'config') and app.config.get('CACHE_TYPE') == 'simple':
        logger.info("=== CACHE INSPECTION ===")
        # Add logging to inspect the cache

@app.route('/clear-cache')
def clear_cache():
    """Clear the application cache and force a fresh fetch"""
    cache.clear()
    logger.info("Cache manually cleared")
    return """
    <h2>Cache cleared!</h2>
    <p>The application cache has been cleared. All data will be fetched fresh on next access.</p>
    <p><a href='/'>Return to Homepage</a></p>
    """

@app.route('/check-topics')
def check_topics():
    """Check that current and last week topics are different"""
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Force refresh to ensure we're not using cached data
    today_topics = fetch_grok_trending_topics(
        max_topics=8, 
        start_date=today, 
        end_date=today,
        time_period="current"
    )
    
    last_week_topics = fetch_grok_trending_topics(
        max_topics=8, 
        start_date=last_week, 
        end_date=last_week,
        time_period="last_week"
    )
    
    html = "<h1>Topic Comparison</h1>"
    html += "<style>table {border-collapse: collapse; width: 100%;} th, td {padding: 8px; text-align: left; border: 1px solid #ddd;} tr:nth-child(even) {background-color: #f2f2f2;}</style>"
    
    # Display today's topics
    html += "<h2>Current Topics:</h2>"
    html += "<table><tr><th>#</th><th>Headline</th><th>Keywords</th></tr>"
    for i, (headline, keywords) in enumerate(today_topics, 1):
        html += f"<tr><td>{i}</td><td>{headline}</td><td>{keywords}</td></tr>"
    html += "</table>"
    
    # Display last week's topics
    html += "<h2>Last Week's Topics:</h2>"
    html += "<table><tr><th>#</th><th>Headline</th><th>Keywords</th></tr>"
    for i, (headline, keywords) in enumerate(last_week_topics, 1):
        html += f"<tr><td>{i}</td><td>{headline}</td><td>{keywords}</td></tr>"
    html += "</table>"
    
    # Check if they're different
    are_different = today_topics[0][0] != last_week_topics[0][0]
    html += f"<p><strong>Topics are different: {'Yes' if are_different else 'No'}</strong></p>"
    
    html += "<p><a href='/'>Return to Homepage</a></p>"
    return html

# Create a Flask app middleware for monitoring API health and performance
def setup_request_monitoring(app):
    @app.before_request
    def before_request():
        # Store start time for request duration tracking
        g = flask.g
        g.start_time = time.time()
        g.request_id = f"{int(time.time())}-{random.randint(1000, 9999)}"
        logger.info(f"[Request {g.request_id}] Starting {request.method} request to {request.path}")
        
        # Log request details in debug mode
        if app.debug:
            logger.debug(f"[Request {g.request_id}] Headers: {dict(request.headers)}")
            logger.debug(f"[Request {g.request_id}] Args: {dict(request.args)}")
            if request.form:
                logger.debug(f"[Request {g.request_id}] Form: {dict(request.form)}")
    
    @app.after_request
    def after_request(response):
        # Calculate request duration
        g = flask.g
        if hasattr(g, 'start_time'):
            elapsed_time = time.time() - g.start_time
            response.headers['X-Request-Time'] = f"{elapsed_time:.3f}s"
            
            # Log response details
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            log_message = f"[Request {g.request_id}] Completed {request.method} {request.path} - Status: {response.status_code}, Time: {elapsed_time:.3f}s"
            logger.log(log_level, log_message)
            
            # Log slow requests
            if elapsed_time > 5.0:  # More than 5 seconds is considered slow
                logger.warning(f"[Slow Request] {request.method} {request.path} took {elapsed_time:.3f}s")
                
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred',
            'message': str(e) if app.debug else 'Please try again later'
        }), 500
    
    @app.route('/api/healthcheck')
    def api_healthcheck():
        """An expanded health check endpoint with more detailed status"""
        status = {'status': 'healthy'}
        
        # Check database connection
        try:
            conn = sqlite3.connect(app.config["DB_PATH"])
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM search_history")
            row_count = c.fetchone()[0]
            conn.close()
            status['database'] = {
                'connected': True,
                'rows': row_count
            }
        except Exception as e:
            status['database'] = {
                'connected': False,
                'error': str(e)
            }
            status['status'] = 'degraded'
        
        # Check image directory
        try:
            img_dir = app.config["IMAGE_DIR"]
            if os.path.exists(img_dir) and os.path.isdir(img_dir):
                image_count = len([f for f in os.listdir(img_dir) if f.endswith('.png')])
                status['images'] = {
                    'available': True,
                    'directory': img_dir,
                    'count': image_count
                }
            else:
                status['images'] = {
                    'available': False,
                    'error': 'Directory not found'
                }
                status['status'] = 'degraded'
        except Exception as e:
            status['images'] = {
                'available': False,
                'error': str(e)
            }
            status['status'] = 'degraded'
        
        # Add system info
        status['system'] = {
            'uptime': time.time() - app.start_time,
            'python_version': sys.version,
        }
        
        return jsonify(status)

def create_app():
    """App factory function"""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Store app start time for uptime tracking
    app.start_time = time.time()
    
    # Load configuration
    try:
        import config_prod
        app.config.from_object(config_prod)
    except ImportError:
        logger.error("Could not import config_prod, using default values")
    
    # Setup cross-origin resource sharing
    CORS(app)
    
    # Register the blueprint
    from routes import routes
    app.register_blueprint(routes)
    
    # Setup request monitoring
    setup_request_monitoring(app)
    
    logger.info(f"Application initialized at {app.start_time}")
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    
    # Create the application
    app = create_app()
    
    # Run the server
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For gunicorn and other WSGI servers
    app = create_app()