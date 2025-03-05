import asyncio
import logging
from app.fetchers.base import BaseFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_public_api():
    """Test fetching from a public API (JSONPlaceholder)"""
    fetcher = BaseFetcher("jsonplaceholder", verify_ssl=False)
    try:
        # Test GET request
        url = "https://jsonplaceholder.typicode.com/posts/1"
        logger.info(f"Fetching data from {url}")
        response = await fetcher.fetch_with_retry(url, max_retries=2)
        
        if response:
            logger.info("Successfully fetched data:")
            logger.info(f"Title: {response.get('title', 'No title')}")
            logger.info(f"Body: {response.get('body', 'No body')[:100]}...")
        else:
            logger.error("Failed to fetch data")
    except Exception as e:
        logger.error(f"Error during public API test: {str(e)}")
    finally:
        await fetcher.close()

async def test_rate_limit_handling():
    """Test rapid requests to demonstrate rate limiting"""
    fetcher = BaseFetcher("jsonplaceholder", verify_ssl=False)
    try:
        url = "https://jsonplaceholder.typicode.com/posts"
        logger.info("Making multiple rapid requests to test rate limiting...")
        
        # Make several requests in quick succession
        tasks = []
        for i in range(5):
            tasks.append(fetcher.fetch_with_retry(f"{url}/{i+1}", max_retries=2))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Request {i+1} failed: {str(result)}")
            elif result is None:
                logger.warning(f"Request {i+1} returned None")
            else:
                success_count += 1
                logger.info(f"Request {i+1} succeeded: {result.get('title', 'No title')}")
        
        logger.info(f"Successfully completed {success_count} out of {len(results)} requests")
    except Exception as e:
        logger.error(f"Error during rate limit test: {str(e)}")
    finally:
        await fetcher.close()

async def main():
    logger.info("Starting API tests...")
    
    # Test basic public API
    logger.info("\n=== Testing Public API ===")
    await test_public_api()
    
    # Test rate limit handling
    logger.info("\n=== Testing Rate Limit Handling ===")
    await test_rate_limit_handling()
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 