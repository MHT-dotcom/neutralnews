from pytrends.request import TrendReq
import logging
logger = logging.getLogger(__name__)
def get_trending_topics(limit=4):
    try:
        pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=2)
        logger.info("Attempting to fetch trending searches from Google Trends")
        trending = pytrends.trending_searches(pn='united_states')
        topics = trending[0].tolist()[:limit]
        logger.info(f"Raw trending topics fetched: {topics}")
        cleaned_topics = [topic.strip() for topic in topics if len(topic.strip()) > 3]
        if len(cleaned_topics) < limit:
            logger.warning(f"Fetched only {len(cleaned_topics)} valid topics, padding with fallbacks")
            cleaned_topics.extend(["Climate Change", "Artificial Intelligence", "Elections", "Global Economy"][:limit - len(cleaned_topics)])
        final_topics = cleaned_topics[:limit]
        logger.info(f"Final trending topics: {final_topics}")
        return final_topics
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        fallback = ["Climate Change", "Artificial Intelligence", "Elections", "Global Economy"]
        logger.info(f"Using fallback topics: {fallback[:limit]}")
        return fallback[:limit]