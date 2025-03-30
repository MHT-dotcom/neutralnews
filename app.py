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
from topics import get_trending_topics, initialize_trending_images
import requests
import certifi
from datetime import datetime
from utils import secure_log_key  # Import the secure logging function
import threading
import time
import random
from image_cache import get_instance

# Set up logging
logger = logging.getLogger('neutralnews')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG if os.getenv("FLASK_ENV") == "development" else logging.INFO)

# Create a file handler for app.log
file_handler = logging.FileHandler('app_log.txt')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Record application start time for health checks and uptime monitoring
app_start_time = time.time()

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)

# Set the application start time for health checks
app.start_time = app_start_time

# Import and add middleware to fix source names
try:
    from fix_source_names import fix_source_names_middleware
    app.after_request(fix_source_names_middleware)
    logger.info("Source name fixing middleware added")
except ImportError:
    logger.warning("fix_source_names module not found, source names may not display correctly")

# Load environment variables - Use secure logging to mask API keys
grok_key = secure_log_key(os.getenv("GROK_API_KEY", "Not set"))
logger.info("Before .env load: GROK_API_KEY status: %s", grok_key)
load_dotenv()  # Loads .env from current directory if present
grok_key = secure_log_key(os.getenv("GROK_API_KEY", "Not set"))
logger.info("GROK_API_KEY status: %s", grok_key)

# Determine base path for persistent storage
BASE_PATH = os.getenv("BASE_PATH", os.path.join(os.path.dirname(__file__), "data"))
DB_PATH = os.path.join(BASE_PATH, "search_db.sqlite")
IMAGE_DIR = os.path.join(BASE_PATH, "images")

# Ensure directories exist (locally and on Render)
os.makedirs(BASE_PATH, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# Export paths as app config for use in routes.py
app.config["DB_PATH"] = DB_PATH
app.config["IMAGE_DIRECTORY"] = IMAGE_DIR

# Set app version for health checks and monitoring
app.config["APP_VERSION"] = os.getenv("APP_VERSION", "1.0.0")

# Make environment variables available through the app config
app.config["ENV_DB_PATH"] = os.getenv("DB_PATH")

# Validate critical configuration on startup
def validate_critical_config():
    """Validate critical configuration on startup and log warnings/errors"""
    critical_errors = []
    warnings = []
    
    # Check if DB_PATH is set
    if not os.getenv("DB_PATH") and not app.config["DB_PATH"]:
        critical_errors.append("DB_PATH is not set in environment or app config")
    
    # Check if the image directory is writable
    if not os.access(IMAGE_DIR, os.W_OK):
        critical_errors.append(f"Image directory {IMAGE_DIR} is not writable")
    
    # Check API keys
    api_keys = {
        "NEWSAPI_ORG_KEY": os.getenv("NEWSAPI_ORG_KEY"),
        "GUARDIAN_API_KEY": os.getenv("GUARDIAN_API_KEY"),
        "GNEWS_API_KEY": os.getenv("GNEWS_API_KEY"),
        "NYT_API_KEY": os.getenv("NYT_API_KEY"),
        "MEDIASTACK_API_KEY": os.getenv("MEDIASTACK_API_KEY"),
        "NEWSDATAIO_API_KEY": os.getenv("NEWSDATAIO_API_KEY"),
        "GROK_API_KEY": os.getenv("GROK_API_KEY")
    }
    
    missing_keys = [name for name, key in api_keys.items() if not key]
    if missing_keys:
        warnings.append(f"Missing API keys: {', '.join(missing_keys)}")
        
    # Check required port availability (in development)
    if os.getenv("FLASK_ENV") == "development":
        import socket
        port = int(os.getenv("PORT", 5001))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", port))
            sock.close()
        except socket.error:
            warnings.append(f"Port {port} is already in use")
    
    # Log all issues
    for warning in warnings:
        logger.warning(f"⚠️ Startup warning: {warning}")
    
    for error in critical_errors:
        logger.error(f"❌ Critical startup error: {error}")
    
    # Return overall status
    if critical_errors:
        return False
    return True

# Run validation and log startup status
startup_valid = validate_critical_config()
if startup_valid:
    logger.info("✅ Application startup validation passed")
else:
    logger.warning("⚠️ Application started with configuration warnings/errors - see logs above")

def init_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS search_history
                 (id INTEGER PRIMARY KEY, query TEXT NOT NULL, timestamp DATETIME NOT NULL,
                  summary TEXT, average_sentiment REAL DEFAULT 0.0, articles TEXT, source_distribution TEXT, image_path TEXT)''')
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

# Initialize the database
with app.app_context():
    init_db()

# No need to preload sentiment model anymore
logger.info("Starting app without sentiment analysis")

# Import configuration
from config_prod import cache, CACHE_CONFIG, MAX_ARTICLES_PER_SOURCE, DEBUG

# Configure cache
cache.init_app(app, config=CACHE_CONFIG)
cache.clear()
logger.info("Cache cleared on startup")

# Global trending topics
today_topics = get_trending_topics("today")
last_week_topics = get_trending_topics("last_week")
last_month_topics = get_trending_topics("last_month")

# Start image cache system and optimization task
if not DEBUG:
    # Only run these in production to avoid consuming resources during development
    from get_img import optimize_image_storage
    
    # Run periodic image optimization
    def run_periodic_image_optimization(interval_hours=24):
        """Run image storage optimization periodically."""
        def optimization_worker():
            logger.info("Starting periodic image optimization worker")
            
            while True:
                try:
                    # Sleep first to avoid immediate optimization on startup
                    time.sleep(interval_hours * 3600)
                    
                    logger.info("Running scheduled image storage optimization")
                    # Create new app context for each optimization run
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
    
    run_periodic_image_optimization(interval_hours=12)  # Run every 12 hours
    
    # Delay the trending image initialization slightly to let app start up
    def delayed_image_init():
        time.sleep(30)  # 30 second delay
        # Wrap in app context to avoid "Working outside of application context" errors
        with app.app_context():
            # Set configuration values that might be needed by workers
            from image_cache import get_instance
            cache = get_instance(
                db_path=app.config.get("DB_PATH"),
                image_dir=IMAGE_DIR
            )
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

# Add custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error page"""
    return jsonify({
        'status': 'error',
        'message': 'Requested resource not found',
        'code': 404
    }), 404

@app.errorhandler(500)
def server_error(e):
    """Return a custom 500 error response with helpful debug info"""
    logger.error(f"Server error: {e}", exc_info=True)
    return jsonify({
        'status': 'error',
        'message': 'An internal server error occurred',
        'code': 500,
        'error_type': type(e).__name__ if e else 'Unknown',
        'context': str(e) if e else 'No additional information available'
    }), 500

# Entry point to run the application
if __name__ == "__main__":
    logger.info(f"Starting server on port {os.getenv('PORT', 5001)}")
    logger.info(f"Application initialized at {app_start_time}")
    
    # Collect and log platform and system information for debugging
    import platform
    logger.info("Python version: %s", sys.version)
    logger.info("Flask version: %s", flask.__version__)
    logger.info("Cache type: %s", os.getenv('CACHE_TYPE', 'simple'))
    
    # Start the server
    logger.info("Application fully initialized")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)), debug=os.getenv('FLASK_ENV') == 'development')