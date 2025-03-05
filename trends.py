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
        
        # First, try the patched approach for newer urllib3 versions
        try:
            # Try to patch the urllib3.util.retry module to handle the parameter name change
            import urllib3.util.retry
            original_init = urllib3.util.retry.Retry.__init__
            
            def patched_init(self, *args, **kwargs):
                # Convert method_whitelist to allowed_methods for newer urllib3 versions
                if 'method_whitelist' in kwargs and not hasattr(urllib3.util.retry.Retry, 'method_whitelist'):
                    logger.info("Patching urllib3.util.retry.Retry to handle method_whitelist parameter")
                    kwargs['allowed_methods'] = kwargs.pop('method_whitelist')
                original_init(self, *args, **kwargs)
                
            # Apply the patch
            urllib3.util.retry.Retry.__init__ = patched_init
            logger.info("Successfully patched urllib3.util.retry.Retry.__init__")
            
            logger.info("Creating TrendReq instance with patched urllib3...")
            pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=2)
            
            logger.info("Attempting to fetch trending searches from Google Trends")
            trending = pytrends.trending_searches(pn='united_states')
            topics = trending[0].tolist()[:limit]
            logger.info(f"Raw trending topics fetched: {topics}")
        except Exception as patch_error:
            # If patching fails, try directly with minimal parameters
            logger.warning(f"Patched approach failed: {patch_error}. Trying direct approach...")
            logger.info("Creating TrendReq instance with minimal parameters...")
            pytrends = TrendReq(hl='en-US', tz=360)  # Skip retry parameters
            
            logger.info("Attempting to fetch trending searches without retries")
            trending = pytrends.trending_searches(pn='united_states')
            topics = trending[0].tolist()[:limit]
            logger.info(f"Raw trending topics fetched with direct approach: {topics}")
            
        # Process the topics
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