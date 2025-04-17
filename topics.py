import json
import logging
import sqlite3
import threading
from datetime import date, datetime, timedelta
import os
from flask import current_app
import time

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
    
    
    keyword_map = {
        # General sentiments
        "love": "❤️",
        "Love": "❤️",
        "laugh": "😂",
        "Laugh": "😂",
        "good": "👍",
        "Good": "👍",
        "bad": "👎",
        "Bad": "👎",
        "cool": "😎",
        "Cool": "😎",
        "amazing": "✨",
        "Amazing": "✨",
        "great": "🌟",
        "Great": "🌟",
        "terrible": "😣",
        "Terrible": "😣",
        "awesome": "😍",
        "Awesome": "😍",
        "sorry": "🙏",
        "Sorry": "🙏",
        "fun": "🎉",
        "Fun": "🎉",
        "boring": "😪",
        "Boring": "😪",
        "excited": "🥳",
        "Excited": "🥳",
        "fail": "😬",
        "Fail": "😬",
        "happy": "😊",
        "Happy": "😊",
        "sad": "😢",
        "Sad": "😢",
        "angry": "😡",
        "Angry": "😡",
        "surprise": "😮",
        "Surprise": "😮",
        "wow": "🤯",
        "Wow": "🤯",
        "nice": "😊",
        "Nice": "😊",
        "meh": "😐",
        "Meh": "😐",
        "hope": "🤞",
        "Hope": "🤞",

        # Space and science
        "space": "🚀",
        "Space": "🚀",
        "astronaut": "👩‍🚀",
        "Astronaut": "👩‍🚀",
        "lunar": "🌕",
        "Lunar": "🌕",
        "launch": "🚀",
        "Launch": "🚀",
        "fusion": "⚛️",
        "Fusion": "⚛️",
        "breakthrough": "💡",
        "Breakthrough": "💡",
        "mars": "🪐",
        "Mars": "🪐",
        "planet": "🌍",
        "Planet": "🌍",
        "rocket": "🚀",
        "Rocket": "🚀",
        "satellite": "🛰️",
        "Satellite": "🛰️",
        "science": "🔬",
        "Science": "🔬",
        "experiment": "🧪",
        "Experiment": "🧪",
        "discovery": "🔭",
        "Discovery": "🔭",
        "gravity": "🌌",
        "Gravity": "🌌",
        "astronomy": "⭐",
        "Astronomy": "⭐",
        "orbit": "🌀",
        "Orbit": "🌀",
        "blackhole": "🕳️",
        "Blackhole": "🕳️",
        "quantum": "⚛️",
        "Quantum": "⚛️",
        "research": "📚",
        "Research": "📚",
        "galaxy": "🌌",
        "Galaxy": "🌌",
        "star": "⭐",
        "Star": "⭐",
        "meteor": "☄️",
        "Meteor": "☄️",

        # Tech and innovation
        "tech": "💻",
        "Tech": "💻",
        "tesla": "🚗",
        "Tesla": "🚗",
        "robotaxi": "🤖",
        "Robotaxi": "🤖",
        "robot": "🤖",
        "Robot": "🤖",
        "meta": "📱",
        "Meta": "📱",
        "ai": "🤖",
        "AI": "🤖",
        "artificial intelligence": "🤖",
        "Artificial Intelligence": "🤖",
        "twitter": "🐦",
        "Twitter": "🐦",
        "google": "🔍",
        "Google": "🔍",
        "apple": "🍎",
        "Apple": "🍎",
        "software": "🖥️",
        "Software": "🖥️",
        "hardware": "⚙️",
        "Hardware": "⚙️",
        "internet": "🌐",
        "Internet": "🌐",
        "data": "📊",
        "Data": "📊",
        "cyber": "🔒",
        "Cyber": "🔒",
        "blockchain": "⛓️",
        "Blockchain": "⛓️",
        "crypto": "₿",
        "Crypto": "₿",
        "innovation": "💡",
        "Innovation": "💡",
        "cloud": "☁️",
        "Cloud": "☁️",
        "code": "💾",
        "Code": "💾",
        "programming": "⌨️",
        "Programming": "⌨️",
        "security": "🔒",
        "Security": "🔒",
        "hack": "💻",
        "Hack": "💻",
        "network": "🌐",
        "Network": "🌐",
        "database": "🗄️",
        "Database": "🗄️",
        "algorithm": "🧠",
        "Algorithm": "🧠",
        "startup": "🚀",
        "Startup": "🚀",

        # Ethical hacking-specific
        "pentest": "🛡️",
        "Pentest": "🛡️",
        "exploit": "⚔️",
        "Exploit": "⚔️",
        "vulnerability": "🕳️",
        "Vulnerability": "🕳️",
        "firewall": "🧱",
        "Firewall": "🧱",
        "malware": "🦠",
        "Malware": "🦠",
        "phishing": "🎣",
        "Phishing": "🎣",
        "bruteforce": "🔨",
        "Bruteforce": "🔨",
        "encryption": "🔐",
        "Encryption": "🔐",
        "decryption": "🔓",
        "Decryption": "🔓",
        "payload": "💣",
        "Payload": "💣",
        "scan": "🔍",
        "Scan": "🔍",
        "backdoor": "🚪",
        "Backdoor": "🚪",
        "rootkit": "🕵️",
        "Rootkit": "🕵️",
        "trojan": "🐴",
        "Trojan": "🐴",

        # Health and environment
        "measles": "🤒",
        "Measles": "🤒",
        "vaccine": "💉",
        "Vaccine": "💉",
        "heatwave": "🥵",
        "Heatwave": "🥵",
        "pollution": "🌫️",
        "Pollution": "🌫️",
        "climate": "🌍",
        "Climate": "🌍",
        "healthcare": "🏥",
        "Healthcare": "🏥",
        "coronavirus": "🦠",
        "Coronavirus": "🦠",
        "covid": "🦠",
        "Covid": "🦠",
        "covid-19": "🦠",
        "Covid-19": "🦠",
        "pandemic": "🦠",
        "Pandemic": "🦠",
        "disease": "🤢",
        "Disease": "🤢",
        "flood": "🌊",
        "Flood": "🌊",
        "drought": "🏜️",
        "Drought": "🏜️",
        "wildfire": "🔥",
        "Wildfire": "🔥",
        "earthquake": "🌋",
        "Earthquake": "🌋",
        "recycling": "♻️",
        "Recycling": "♻️",
        "nature": "🌳",
        "Nature": "🌳",
        "medicine": "💊",
        "Medicine": "💊",
        "virus": "🦠",
        "Virus": "🦠",
        "air": "💨",
        "Air": "💨",
        "water": "💧",
        "Water": "💧",
        "forest": "🌲",
        "Forest": "🌲",
        "sustainability": "🌱",
        "Sustainability": "🌱",

        # Politics and economics
        "talks": "🗣️",
        "Talks": "🗣️",
        "ceasefire": "☮️",
        "Ceasefire": "☮️",
        "sanctions": "🚫",
        "Sanctions": "🚫",
        "crackdown": "👮",
        "Crackdown": "👮",
        "economic": "💰",
        "Economic": "💰",
        "economy": "💰",
        "Economy": "💰",
        "economics": "💰",
        "Economics": "💰",
        "rate cut": "📉",
        "Rate Cut": "📉",
        "layoffs": "😞",
        "Layoffs": "😞",
        "inflation": "📈",
        "Inflation": "📈",
        "recession": "📉",
        "Recession": "📉",
        "trade": "🤝",
        "Trade": "🤝",
        "election": "🗳️",
        "Election": "🗳️",
        "protest": "✊",
        "Protest": "✊",
        "war": "⚔️",
        "War": "⚔️",
        "peace": "🕊️",
        "Peace": "🕊️",
        "law": "⚖️",
        "Law": "⚖️",
        "tax": "💸",
        "Tax": "💸",
        "budget": "💼",
        "Budget": "💼",
        "strike": "🚩",
        "Strike": "🚩",
        "policy": "📜",
        "Policy": "📜",
        "government": "🏛️",
        "Government": "🏛️",
        "democracy": "🗳️",
        "Democracy": "🗳️",
        "regulation": "📝",
        "Regulation": "📝",
        "debt": "💳",
        "Debt": "💳",

        # Miscellaneous
        "food": "🍽️",
        "Food": "🍽️",
        "dog": "🐶",
        "Dog": "🐶",
        "cat": "🐱",
        "Cat": "🐱",
        "hello": "👋",
        "Hello": "👋",
        "tourism": "✈️",
        "Tourism": "✈️",
        "victories": "🏆",
        "Victories": "🏆",
        "prices": "💸",
        "Prices": "💸",
        "energy": "🔋",
        "Energy": "🔋",
        "energy crisis": "🔋",
        "Energy Crisis": "🔋",
        "nuclear": "💥",
        "Nuclear": "💥",
        "nuclear power": "💥",
        "Nuclear Power": "💥",
        "sports": "⚽",
        "Sports": "⚽",
        "music": "🎶",
        "Music": "🎶",
        "movie": "🎬",
        "Movie": "🎬",
        "art": "🎨",
        "Art": "🎨",
        "fashion": "👗",
        "Fashion": "👗",
        "travel": "🗺️",
        "Travel": "🗺️",
        "game": "🎮",
        "Game": "🎮",
        "party": "🎈",
        "Party": "🎈",
        "school": "🏫",
        "School": "🏫",
        "work": "💼",
        "Work": "💼",
        "money": "💵",
        "Money": "💵",
        "time": "⏳",
        "Time": "⏳",
        "weather": "☀️",
        "Weather": "☀️",
        "rain": "☔",
        "Rain": "☔",
        "snow": "❄️",
        "Snow": "❄️",
        "sun": "☀️",
        "Sun": "☀️",
        "coffee": "☕",
        "Coffee": "☕",
        "book": "📖",
        "Book": "📖",
        "friend": "👯",
        "Friend": "👯",
        "family": "👨‍👩‍👧",
        "Family": "👨‍👩‍👧",
        "dance": "💃",
        "Dance": "💃",
        "photo": "📸",
        "Photo": "📸",
        "video": "🎥",
        "Video": "🎥"
    }
    
    # Check for specific keywords first
    for keyword, emoji in keyword_map.items():
        if keyword in text:
            return emoji
    
    # Default neutral emoji instead of sentiment analysis
    return "📰"

# Fallback topics for different time periods
FALLBACK_TOPICS = {
    "today": [
    ["Power Blackout Hits All of Puerto Rico During Easter", "Puerto Rico Blackout"],
    ["S&P 500 Plummets 5% After Tariff Increase", "S&P 500 Drop"],
    ["Israel Continues Blockade Despite UN Warning", "Israel Blockade"],
    ["American Tariffs Send International Trade into Reverse", "U.S. Tariffs"],
    ["James Webb Space Telescope Detects Life-Associated Gas", "Webb Telescope"],
    ["Massive Nightclub Collapse in Dominican Republic", "Dominican Nightclub"],
    ["Lebanese Army Detains Suspects in Attacks on Israel", "Lebanon Detentions"],
    ["Putin Meets Freed Russian Gaza Hostages", "Putin Hostages"]
    ],
    "last_week": [
        ["Massive Solar Flare Disrupts Global Communications", "Solar Flare"],
        ["U.S. Announces New AI Partnership with Japan at Tech Summit", "AI Summit"],
        ["Protests Erupt in Paris Over Climate Policy Reforms", "Paris Climate"],
        ["India Launches Lunar Rover Mission Chandrayaan-4", "India Lunar"],
        ["Historic Snowstorm Paralyzes Northeastern U.S.", "U.S. Snowstorm"],
        ["China Tests Hypersonic Missile in Pacific, Raising Tensions", "China Missile"],
        ["UN Unveils Plan to Combat Rising Sea Levels by 2030", "Sea Levels"],
        ["Breakthrough in Fusion Energy Achieved at UK Lab", "Fusion Energy"]
    ],
    "last_month": [
        ["Iceland Volcanic Eruption", "Volcanic Iceland"],
        ["U.S. Trade Policy Shift: Trump Imposes Tariffs", "Tariffs Trump"],
        ["Hungarys ICC Withdrawal and Netanyahu Visit", "Netanyahu"],
        ["Middle East Escalation: Israeli Airstrike in Beirut", "Israeli Beirut"],
        ["Malaysia Gas Pipeline Explosion", "Explosion Malaysia"],
        ["Global Tech Talks on AI Regulation", "AI Regulation"],
        ["Meta Releases Llama 4 Models", "Llama Meta"], 
        ["Space Milestone: Fram2 Mission Launches", "fram2"]
        ],
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