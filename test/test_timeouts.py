#!/usr/bin/env python3
import asyncio
import logging
import sys
from fetchers import async_fetch_newsapi_org, fetch_with_error_handling, REQUEST_TIMEOUT, log_request_timeout_settings
from config_prod import NEWSAPI_ORG_KEY

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("timeout_test")

async def test_async_timeout():
    """Test async fetching with timeout"""
    logger.info(f"Testing async fetch with {REQUEST_TIMEOUT}s timeout")
    try:
        # Test fetching news about a popular topic
        results = await async_fetch_newsapi_org("ukraine")
        logger.info(f"Successfully fetched {len(results)} articles")
        
        # Show a sample result
        if results:
            sample = results[0]
            logger.info(f"Sample article: {sample.get('title', 'No title')} - {sample.get('source', {}).get('name', 'Unknown source')}")
    except Exception as e:
        logger.error(f"Error during async fetch: {e}")

def test_sync_timeout():
    """Test synchronous fetching with timeout"""
    logger.info(f"Testing sync fetch with {REQUEST_TIMEOUT}s timeout")
    try:
        # Test with NewsAPI.org
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "technology",
            "pageSize": 10,
            "apiKey": NEWSAPI_ORG_KEY
        }
        data, error = fetch_with_error_handling(url, params=params)
        if error:
            logger.warning(f"Error occurred: {error}")
        else:
            logger.info(f"Successfully fetched {len(data.get('articles', []))} articles")
            # Show a sample result
            if data.get('articles'):
                sample = data['articles'][0]
                logger.info(f"Sample article: {sample.get('title', 'No title')} - {sample.get('source', {}).get('name', 'Unknown source')}")
    except Exception as e:
        logger.error(f"Error during sync fetch: {e}")

async def main():
    logger.info("Starting timeout tests")
    
    # Log the timeout settings
    log_request_timeout_settings()
    
    # Test async fetching
    await test_async_timeout()
    
    # Test sync fetching
    test_sync_timeout()
    
    logger.info("Timeout tests completed")

if __name__ == "__main__":
    asyncio.run(main()) 