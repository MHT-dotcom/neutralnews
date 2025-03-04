# trends.py
# Fetches trending news topics using pytrends for the homepage.

# trends.py
from pytrends.request import TrendReq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_trending_topics(limit=4):
    """
    Fetch top trending topics from Google Trends for the United States.
    
    Args:
        limit (int): Number of trending topics to return (default: 4).
    
    Returns:
        list: List of trending topic strings.
    """
    try:
        pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=1)
        trending = pytrends.trending_searches(pn='united_states')
        topics = trending[0].tolist()[:limit]  # Get top 'limit' terms
        logger.info(f"Successfully fetched trending topics: {topics}")
        return topics
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        # Fallback list if pytrends fails
        fallback = ["Climate Change", "Artificial Intelligence", "Elections", "Global Economy"]
        logger.info(f"Using fallback topics: {fallback}")
        return fallback