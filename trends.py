# trends.py
# Fetches trending news topics using pytrends for the homepage.
from pytrends.request import TrendReq
import logging

logger = logging.getLogger(__name__)

def get_trending_topics(limit=4):
    try:
        pytrends = TrendReq(hl='en-US', tz=360)  # UTC-6
        trending = pytrends.trending_searches(pn='united_states')  # Or 'world'
        topics = trending[0].tolist()[:limit]  # Top 4 terms
        logger.info(f"Fetched trending topics: {topics}")
        return topics
    except Exception as e:
        logger.error(f"Error fetching trending topics: {e}")
        return ["climate change", "artificial intelligence", "global economy", "health crisis"]  # Fallback