import asyncio
import logging
import os
from app.fetchers.base import BaseFetcher
from flask import current_app
import requests
import json
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.append('..')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_config(key, default=None):
    """Helper function to safely get config values"""
    try:
        # Try to access the config within application context
        return current_app.config.get(key, default)
    except RuntimeError:
        # If we're outside of application context (e.g., during testing)
        print(f"Accessing {key} outside application context")
        
        # Check environment variables directly as a fallback
        env_key = key.upper()  # Convert to uppercase for environment variable convention
        if env_key in os.environ:
            env_value = os.environ.get(env_key)
            if any(x in key.upper() for x in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                print(f"Found {key} in environment variables (length: {len(env_value)})")
            else:
                print(f"Found {key} in environment variables: {env_value}")
            return env_value
            
        return default

async def test_guardian_api():
    """Test fetching from The Guardian API with authentication"""
    fetcher = BaseFetcher("guardian", verify_ssl=False)
    try:
        # Test search endpoint
        guardian_url = get_config('GUARDIAN_URL', 'https://content.guardianapis.com/search')
        guardian_api_key = get_config('GUARDIAN_API_KEY', '')
        url = f"{guardian_url}?q=technology&api-key={guardian_api_key}&show-fields=all"
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
        guardian_url = get_config('GUARDIAN_URL', 'https://content.guardianapis.com/search')
        guardian_api_key = get_config('GUARDIAN_API_KEY', '')
        logger.info("Making multiple rapid requests to test rate limiting...")
        
        # Make several requests in quick succession
        tasks = []
        for i in range(3):  # Using 3 requests to stay within free tier limits
            url = f"{guardian_url}?q=world&page={i+1}&api-key={guardian_api_key}&show-fields=all"
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
        guardian_url = get_config('GUARDIAN_URL', 'https://content.guardianapis.com/search')
        url = f"{guardian_url}?q=technology&api-key=invalid_key"
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
    guardian_api_key = get_config('GUARDIAN_API_KEY', '')
    if not guardian_api_key:
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