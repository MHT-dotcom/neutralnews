from pytrends.request import TrendReq
import logging
import traceback
import inspect
import sys

logger = logging.getLogger(__name__)

def get_trending_topics(limit=4):
    try:
        # Log pytrends and requests versions
        import pkg_resources
        try:
            pytrends_version = pkg_resources.get_distribution('pytrends').version
            requests_version = pkg_resources.get_distribution('requests').version
            urllib3_version = pkg_resources.get_distribution('urllib3').version
            logger.info(f"Using pytrends v{pytrends_version}, requests v{requests_version}, urllib3 v{urllib3_version}")
        except Exception as pkg_err:
            logger.warning(f"Failed to get package versions: {pkg_err}")
        
        logger.info("Creating TrendReq instance...")
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
        
        # More detailed error logging
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        # Try to get more information about the TrendReq constructor
        try:
            constructor_args = inspect.signature(TrendReq.__init__)
            logger.error(f"TrendReq constructor expected arguments: {constructor_args}")
        except Exception as inspect_err:
            logger.error(f"Failed to inspect TrendReq: {inspect_err}")
        
        fallback = ["Climate Change", "Artificial Intelligence", "Elections", "Global Economy"]
        logger.info(f"Using fallback topics: {fallback[:limit]}")
        return fallback[:limit]