# app.py
import flask
from flask import Flask, jsonify
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
load_dotenv()

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

@app.route('/test-grok')
def test_grok():
    from fetchers import test_grok_api
    result = test_grok_api()
    return jsonify(result)

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
    <p><a href='/test-grok-key'>Test Grok API Key</a></p>
    """

@app.route('/test-grok-key')
def test_grok_key():
    """Test endpoint to try different API key formats with the Grok API"""
    # Get original key
    api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return "No API key found!"
    
    # Format 1: Original with xai- prefix
    format1 = api_key
    
    # Format 2: Without xai- prefix
    format2 = api_key[4:] if api_key.startswith("xai-") else api_key
    
    # Test URL
    url = "https://api.x.ai/v1/chat/completions"
    
    formats = [
        {"name": "Original with xai- prefix", "key": format1, "header": f"Bearer {format1}"},
        {"name": "Without xai- prefix", "key": format2, "header": f"Bearer {format2}"},
        {"name": "No Bearer, just raw key", "key": format2, "header": format2},
        {"name": "X-API-Key header", "key": format1, "header": None, "x_api_key": format1}
    ]
    
    # Simple request payload
    payload = {
        "model": "grok-1",
        "messages": [{"role": "user", "content": "Hello, what's the current date?"}],
        "max_tokens": 100
    }
    
    # Test each format
    results = []
    for fmt in formats:
        try:
            headers = {"Content-Type": "application/json"}
            
            if fmt.get("header"):
                headers["Authorization"] = fmt["header"]
            
            if fmt.get("x_api_key"):
                headers["X-API-Key"] = fmt["x_api_key"]
            
            logger.info(f"Testing format: {fmt['name']}")
            logger.info(f"Headers: {headers}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=10,
                verify=certifi.where()
            )
            
            results.append({
                "format": fmt["name"],
                "status_code": response.status_code,
                "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            })
            
            logger.info(f"Status code: {response.status_code}")
            
            # If successful, log the full response
            if response.status_code == 200:
                logger.info(f"SUCCESS with format: {fmt['name']}")
                logger.info(f"Response: {response.text[:500]}...")
        except Exception as e:
            logger.error(f"Error testing format {fmt['name']}: {e}")
            results.append({
                "format": fmt["name"],
                "error": str(e)
            })
    
    # Format results as HTML
    html = "<h1>Grok API Key Testing Results</h1>"
    html += "<style>table {border-collapse: collapse; width: 100%;} th, td {padding: 8px; text-align: left; border: 1px solid #ddd;} tr:nth-child(even) {background-color: #f2f2f2;} pre {white-space: pre-wrap; word-wrap: break-word;}</style>"
    html += "<table><tr><th>Format</th><th>Status</th><th>Response</th></tr>"
    
    for result in results:
        html += f"<tr><td>{result['format']}</td>"
        
        if "error" in result:
            html += f"<td colspan='2'>Error: {result['error']}</td>"
        else:
            status_color = "green" if result["status_code"] == 200 else "red"
            html += f"<td style='color:{status_color}'>{result['status_code']}</td><td><pre>{result['response']}</pre></td>"
        
        html += "</tr>"
    
    html += "</table>"
    html += "<p><a href='/'>Return to Homepage</a></p>"
    return html

@app.route('/test-models')
def test_grok_models():
    """Test endpoint to try different model names with the Grok API"""
    import requests
    import json
    import certifi
    
    # Get original key with xai- prefix
    api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return "No API key found!"
    
    # Test URL
    url = "https://api.x.ai/v1/chat/completions"
    
    # Models to test
    models = [
        "grok-1",
        "grok-2", 
        "grok",
        "grok-lite",
        "xai-grok",
        "claude-3-opus-20240229",  # Try a common model name format
        "gpt-4"  # Try a common model name
    ]
    
    # Simple request payload
    base_payload = {
        "messages": [{"role": "user", "content": "Hello, what's the current date?"}],
        "max_tokens": 100
    }
    
    # Authentication headers - use full key with xai- prefix
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test each model
    results = []
    for model in models:
        try:
            payload = base_payload.copy()
            payload["model"] = model
            
            logging.info(f"Testing model: {model}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=10,
                verify=certifi.where()
            )
            
            results.append({
                "model": model,
                "status_code": response.status_code,
                "response": response.text[:300] + "..." if len(response.text) > 300 else response.text
            })
            
            logging.info(f"Status code: {response.status_code}")
            
            # If successful, log the full response
            if response.status_code == 200:
                logging.info(f"SUCCESS with model: {model}")
                logging.info(f"Response: {response.text[:500]}...")
        except Exception as e:
            logging.error(f"Error testing model {model}: {e}")
            results.append({
                "model": model,
                "error": str(e)
            })
    
    # Format results as HTML
    html = "<h1>Grok API Model Testing Results</h1>"
    html += "<style>table {border-collapse: collapse; width: 100%;} th, td {padding: 8px; text-align: left; border: 1px solid #ddd;} tr:nth-child(even) {background-color: #f2f2f2;} pre {white-space: pre-wrap; word-wrap: break-word;}</style>"
    html += "<table><tr><th>Model</th><th>Status</th><th>Response</th></tr>"
    
    for result in results:
        html += f"<tr><td>{result['model']}</td>"
        
        if "error" in result:
            html += f"<td colspan='2'>Error: {result['error']}</td>"
        else:
            status_color = "green" if result["status_code"] == 200 else "red"
            html += f"<td style='color:{status_color}'>{result['status_code']}</td><td><pre>{result['response']}</pre></td>"
        
        html += "</tr>"
    
    html += "</table>"
    html += "<p><a href='/'>Return to Homepage</a></p>"
    return html

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Application configuration complete, starting server on port {port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=DEBUG)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")