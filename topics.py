import json
import logging
import sqlite3
import threading
from datetime import date, datetime, timedelta
import os
from flask import current_app
import time
from textblob import TextBlob  # Add this import for sentiment analysis

# Configure logging
logger = logging.getLogger("neutralnews")

# Function to convert text to an appropriate emoji
def text_to_emoji(text):
    """
    Convert a text string to a relevant emoji based on keywords or sentiment.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        str: A single emoji character
    """
    # Convert text to lowercase for consistency
    text = text.lower()
    
    # Expanded keyword map with topic-specific emojis
    keyword_map = {
        # General sentiments
        "love": "❤️",
        "laugh": "😂",
        "good": "👍",
        "bad": "👎",
        "yes": "✅",
        "no": "❌",
        "cool": "😎",
        "amazing": "✨",
        "great": "🌟",
        "terrible": "😣",
        "awesome": "😍",
        "sorry": "🙏",
        "fun": "🎉",
        "boring": "😪",
        "excited": "🥳",
        "fail": "😬",

        # Space and science
        "space": "🚀",
        "astronaut": "👩‍🚀",
        "lunar": "🌕",
        "launch": "🚀",
        "fusion": "⚛️",
        "breakthrough": "💡",
        "mars": "🪐",
        "planet": "🌍",
        "rocket": "🚀",
        "satellite": "🛰️",
        "science": "🔬",
        "experiment": "🧪",
        "discovery": "🔭",
        "gravity": "🌌",

        # Tech and innovation
        "tech": "💻",
        "tesla": "🚗",
        "robotaxi": "🤖",
        "robot": "🤖",
        "meta": "📱",
        "ai": "🤖",
        "AI": "🤖",
        "artificial intelligence": "🤖",
        "twitter": "🐦",
        "google": "🔍",
        "apple": "🍎",
        "software": "🖥️",
        "hardware": "⚙️",
        "internet": "🌐",
        "data": "📊",
        "cyber": "🔒",
        "blockchain": "⛓️",
        "crypto": "₿",
        "innovation": "💡",

        # Health and environment
        "measles": "🤒",
        "vaccine": "💉",
        "heatwave": "🥵",
        "pollution": "🌫️",
        "climate": "🌍",
        "healthcare": "🏥",
        "coronavirus": "🦠",
        "covid": "🦠",
        "covid-19": "🦠",
        "pandemic": "🦠",
        "disease": "🤢",
        "flood": "🌊",
        "drought": "🏜️",
        "wildfire": "🔥",
        "earthquake": "🌋",
        "recycling": "♻️",
        "nature": "🌳",
        "medicine": "💊",
        "virus": "🦠",

        # Politics and economics
        "talks": "🗣️",
        "ceasefire": "☮️",
        "sanctions": "🚫",
        "crackdown": "👮",
        "economic": "💰",
        "economy": "💰",
        "economics": "💰",
        "rate cut": "📉",
        "layoffs": "😞",
        "inflation": "📈",
        "recession": "📉",
        "trade": "🤝",
        "election": "🗳️",
        "protest": "✊",
        "war": "⚔️",
        "peace": "🕊️",
        "law": "⚖️",
        "tax": "💸",
        "budget": "💼",
        "strike": "🚩",
        "policy": "📜",

        # Miscellaneous
        "food": "🍽️",
        "dog": "🐶",
        "cat": "🐱",
        "hello": "👋",
        "tourism": "✈️",
        "victories": "🏆",
        "prices": "💸",
        "energy": "🔋",
        "energy crisis": "🔋",
        "nuclear": "💥",
        "nuclear power": "💥",
        "sports": "⚽",
        "music": "🎶",
        "movie": "🎬",
        "art": "🎨",
        "fashion": "👗",
        "travel": "🗺️",
        "game": "🎮",
        "party": "🎈",
        "school": "🏫",
        "work": "💼",
        "money": "💵",
        "time": "⏳",
        "weather": "☀️",
        "rain": "☔"
    }
    
    # Check for specific keywords first
    for keyword, emoji in keyword_map.items():
        if keyword in text:
            return emoji
    
    # Fallback to sentiment analysis
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.3:
        return "😊"
    elif polarity > 0:
        return "🙂"
    elif polarity < -0.3:
        return "😢"
    elif polarity < 0:
        return "😕"
    else:
        return "😐"

# Fallback topics for different time periods
FALLBACK_TOPICS = {
    "today": [
        ['JFK Files Released with New CIA Revelations', 'JFK assassination files CIA'],
        ['Astronauts Splash Down After 9 Months in Space', 'Sunita Williams ISS return'],
        ['Trump Pushes Ukraine-Russia Ceasefire Talks', 'Trump Zelensky Putin'],
        ['Tech Stocks Rebound After Volatile Week', 'Nasdaq Tesla recovery'],
        ['Sydney Measles Cases Rise After Jetstar Alert', 'measles Sydney outbreak'],
        ['March Madness Kicks Off with Upset Victories', 'NCAA tournament upsets'],
        ['Turkey Escalates Crackdown on Opposition Assets', 'Turkey Imamoglu'],
        ['Philippines Heatwave Prompts Emergency Measures', 'Philippines crisis']
    ],
    "last_week": [
        ['Ukraine-Russia Peace Talks Stall After New Sanctions', 'Ukraine Russia sanctions'],
        ['Tesla Unveils Robotaxi Plans for 2026 Rollout', 'Tesla robotaxi autonomous'],
        ['Federal Reserve Signals Potential Rate Cut', 'Fed interest rates economy'],
        ['Meta AI Assistant Now Available in 40 Languages', 'Meta AI assistant languages'],
        ['Record Temperatures Hit Mediterranean Countries', 'heatwave climate Mediterranean'],
        ['SpaceX Launches First Commercial Lunar Lander', 'SpaceX lunar lander commercial'],
        ['UN Report Warns of Critical Ocean Pollution Levels', 'ocean pollution plastic UN'],
        ['China Unveils New Economic Stimulus Package', 'China economy stimulus package']
    ],
    "last_month": [
        ['US Passes Major Climate Legislation', 'climate bill emissions'],
        ['Twitter Introduces New Content Moderation Tools', 'Twitter moderation content'],
        ['Major Tech Companies Announce Layoffs', 'tech layoffs recession'],
        ['Japan Reopens Borders to International Tourism', 'Japan tourism COVID'],
        ['Breakthrough in Nuclear Fusion Energy Announced', 'fusion energy breakthrough'],
        ['Amazon Acquires Healthcare Provider for $4 Billion', 'Amazon healthcare acquisition'],
        ['Global Wheat Prices Stabilize After Recent Surge', 'wheat prices food'],
        ['New Malaria Vaccine Shows 80% Efficacy in Trials', 'malaria vaccine WHO']
    ]
}

def get_db_path():
    """Get the database path from the application config or environment"""
    try:
        # First try to get from current app context
        return current_app.config.get("DB_PATH")
    except RuntimeError:
        # If outside app context, try environment variable
        db_path = os.environ.get("DB_PATH")
        if db_path:
            return db_path
        # Last resort fallback
        return os.path.join(os.path.dirname(__file__), "data", "search_db.sqlite")

def get_date_for_period(period):
    """Get the date string for a given period"""
    today = date.today()
    if period == "today":
        return str(today)
    elif period == "last_week":
        return str(today - timedelta(days=7))
    elif period == "last_month":
        return str(today - timedelta(days=30))
    else:
        return str(today)

def get_cached_topics(period, fetch_date=None):
    """Get cached topics from database if available
    
    Args:
        period (str): One of 'today', 'last_week', or 'last_month'
        fetch_date (str, optional): Specific date in YYYY-MM-DD format. 
                                  If None, uses default for the period.
    
    Returns:
        list or None: List of topic pairs or None if not in cache
    """
    if fetch_date is None:
        fetch_date = get_date_for_period(period)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT topics FROM hot_topics WHERE period = ? AND fetch_date = ? ORDER BY id DESC LIMIT 1",
                   (period, fetch_date))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        logger.info(f"Using cached {period} trending topics from {fetch_date}")
        return json.loads(result[0])
    
    return None

def cache_topics(topics, period, fetch_date=None):
    """Save topics to database cache
    
    Args:
        topics (list): List of topic pairs to cache
        period (str): One of 'today', 'last_week', or 'last_month'
        fetch_date (str, optional): Specific date in YYYY-MM-DD format.
                                  If None, uses default for the period.
    """
    if fetch_date is None:
        fetch_date = get_date_for_period(period)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO hot_topics (topics, fetch_date, period) VALUES (?, ?, ?)",
                   (json.dumps(topics), fetch_date, period))
    conn.commit()
    conn.close()
    
    logger.info(f"Cached {period} trending topics for {fetch_date}")

def fetch_topics_from_api(period, max_topics=8):
    """Fetch topics from external API or use fallbacks
    
    This would normally call an external API (like Grok), but currently
    returns hardcoded fallbacks.
    
    Args:
        period (str): One of 'today', 'last_week', or 'last_month'
        max_topics (int): Maximum number of topics to return
    
    Returns:
        list: List of topic pairs [headline, keywords]
    """
    logger.info(f"Would fetch {period} topics from API, using fallbacks for '{period}' instead")
    
    # Get the appropriate fallback list
    if period in FALLBACK_TOPICS:
        topics = FALLBACK_TOPICS[period]
        logger.info(f"Using {period.upper()} fallback topics list with {len(topics)} topics")
    else:
        topics = FALLBACK_TOPICS["today"]  # Default fallback
        logger.info(f"Using DEFAULT fallback topics list (today) with {len(topics)} topics")
    
    # Limit to max_topics
    max_topics = min(max(1, max_topics), 8)
    return topics[:max_topics]

def get_trending_topics(period="today", force_refresh=False, max_topics=8):
    """Get trending topics with caching and fallback logic
    
    This is the main function that should be called by routes and other code.
    
    Args:
        period (str): One of 'today', 'last_week', or 'last_month'
        force_refresh (bool): Whether to force a refresh from the API
        max_topics (int): Maximum number of topics to return
    
    Returns:
        list: List of topic pairs [headline, keywords, emoji]
    """
    # Try to get from cache first (unless forced refresh)
    if not force_refresh:
        cached_topics = get_cached_topics(period)
        if cached_topics:
            # Add emoji to each topic if it doesn't already have one
            for i, topic in enumerate(cached_topics):
                if len(topic) < 3:  # If no emoji is present
                    headline = topic[0]
                    emoji = text_to_emoji(headline)
                    if len(topic) == 2:
                        cached_topics[i] = [topic[0], topic[1], emoji]
                    else:
                        cached_topics[i] = [topic[0], "", emoji]
            return cached_topics
    
    # If we get here, we need to fetch from API
    topics = fetch_topics_from_api(period, max_topics)
    
    # Add emoji to each topic
    for i, topic in enumerate(topics):
        headline = topic[0]
        emoji = text_to_emoji(headline)
        if len(topic) == 2:
            topics[i] = [topic[0], topic[1], emoji]
        else:
            topics[i] = [topic[0], "", emoji]
    
    # Cache the results
    if topics:
        cache_topics(topics, period)
    
    return topics

def pregenerate_topic_images(topics):
    """Start background tasks to pregenerate images for topics
    
    Args:
        topics (list): List of topic pairs [headline, keywords]
    """
    if not topics:
        logger.warning("No topics provided for image pregeneration")
        return
    
    try:
        # Import here to avoid circular imports
        from get_img import generate_and_save_image
        
        def generate_images():
            with current_app.app_context():
                for topic in topics:
                    try:
                        # Use the headline as the query
                        headline = topic[0]
                        logger.info(f"Pregenerating image for topic: {headline}")
                        generate_and_save_image(headline)
                        # Sleep briefly to avoid overloading the system
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error generating image for {topic[0]}: {str(e)}")
        
        # Start a background thread
        thread = threading.Thread(target=generate_images)
        thread.daemon = True
        thread.start()
        logger.info(f"Started background task for trending image generation")
    except Exception as e:
        logger.error(f"Error starting image pregeneration: {str(e)}")

def initialize_trending_images():
    """Initialize image generation for all trending topic periods"""
    logger.info("Starting trending image pre-generation for all periods...")
    try:
        # Get trending topics for all periods
        today_topics = get_trending_topics("today")
        last_week_topics = get_trending_topics("last_week")
        last_month_topics = get_trending_topics("last_month")
        
        # Pre-generate images
        pregenerate_topic_images(today_topics)
        pregenerate_topic_images(last_week_topics)
        pregenerate_topic_images(last_month_topics)
        
        logger.info("Trending image pre-generation tasks started for all periods")
    except Exception as e:
        logger.error(f"Error initializing trending images: {str(e)}") 