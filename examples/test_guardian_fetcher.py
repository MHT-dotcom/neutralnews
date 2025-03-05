import asyncio
import logging
import os
from app.fetchers.base import BaseFetcher
import config_prod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_guardian_api():
    """Test fetching from The Guardian API with authentication"""
    fetcher = BaseFetcher("guardian", verify_ssl=False)
    try:
        # Test search endpoint
        url = f"{config_prod.GUARDIAN_URL}?q=technology&api-key={config_prod.GUARDIAN_API_KEY}&show-fields=all"
        logger.info("Testing Guardian API search endpoint...")
        response = await fetcher.fetch_with_retry(url, max_retries=2)
        
        if response and 'response' in response:
            results = response['response'].get('results', [])
            logger.info(f"Successfully fetched {len(results)} articles from The Guardian")
            
            # Display first article details
            if results:
                article = results[0]
                logger.info("\nFirst Article Details:")
                logger.info(f"Title: {article.get('webTitle', 'No title')}")
                logger.info(f"Section: {article.get('sectionName', 'No section')}")
                logger.info(f"Published: {article.get('webPublicationDate', 'No date')}")
        else:
            logger.error("Failed to fetch data from The Guardian API")
            if response:
                logger.error(f"Error response: {response}")
    except Exception as e:
        logger.error(f"Error during Guardian API test: {str(e)}")
    finally:
        await fetcher.close()

async def test_rate_limit_handling():
    """Test rapid requests to demonstrate rate limiting"""
    fetcher = BaseFetcher("guardian", verify_ssl=False)
    try:
        base_url = config_prod.GUARDIAN_URL
        logger.info("Making multiple rapid requests to test rate limiting...")
        
        # Make several requests in quick succession
        tasks = []
        for i in range(3):  # Using 3 requests to stay within free tier limits
            url = f"{base_url}?q=world&page={i+1}&api-key={config_prod.GUARDIAN_API_KEY}&show-fields=all"
            tasks.append(fetcher.fetch_with_retry(url, max_retries=2))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Request {i+1} failed: {str(result)}")
            elif result is None:
                logger.warning(f"Request {i+1} returned None")
            else:
                success_count += 1
                articles = result.get('response', {}).get('results', [])
                logger.info(f"Request {i+1} succeeded: fetched {len(articles)} articles")
        
        logger.info(f"Successfully completed {success_count} out of {len(results)} requests")
    except Exception as e:
        logger.error(f"Error during rate limit test: {str(e)}")
    finally:
        await fetcher.close()

async def test_error_handling():
    """Test error handling with invalid API key"""
    fetcher = BaseFetcher("guardian", verify_ssl=False)
    try:
        # Test with invalid API key
        url = f"{config_prod.GUARDIAN_URL}?q=technology&api-key=invalid_key"
        logger.info("Testing error handling with invalid API key...")
        response = await fetcher.fetch_with_retry(url, max_retries=1)
        
        if response is None:
            logger.info("Successfully handled invalid API key error")
        else:
            logger.warning("Unexpected success with invalid API key")
    except Exception as e:
        logger.info(f"Successfully caught error with invalid API key: {str(e)}")
    finally:
        await fetcher.close()

async def main():
    logger.info("Starting Guardian API tests...")
    
    # Verify API key is available
    if not config_prod.GUARDIAN_API_KEY:
        logger.error("No Guardian API key found in environment variables!")
        return
    
    # Test basic API functionality
    logger.info("\n=== Testing Guardian API Basic Functionality ===")
    await test_guardian_api()
    
    # Test rate limit handling
    logger.info("\n=== Testing Rate Limit Handling ===")
    await test_rate_limit_handling()
    
    # Test error handling
    logger.info("\n=== Testing Error Handling ===")
    await test_error_handling()
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 