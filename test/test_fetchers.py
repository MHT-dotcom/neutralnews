import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the fetchers module
from fetchers import (
    fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
    fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
    fetch_newsapi_ai_articles, async_fetch_articles,
    fetch_newsapi_org_diversified, async_fetch_newsapi_org_diversified
)

async def test_diversified_fetcher():
    """Test the query expansion feature in the diversified fetcher."""
    query = "wheat prices food"
    logger.info(f"Testing diversified fetcher with query: '{query}'")
    
    # Test with normal fetching
    logger.info("=== Standard fetch ===")
    standard_articles = fetch_newsapi_org(query)
    logger.info(f"Standard NewsAPI.org fetcher: {len(standard_articles)} articles")
    
    # Test with diversified fetching (should use query expansion)
    logger.info("=== Diversified fetch with query expansion ===")
    diversified_articles = await async_fetch_newsapi_org_diversified(query)
    logger.info(f"Diversified NewsAPI.org fetcher: {len(diversified_articles)} articles")
    
    # Show some details about the articles
    if diversified_articles:
        source_counts = {}
        for article in diversified_articles:
            source = article.get('source', {}).get('name', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        logger.info(f"Source distribution in diversified results:")
        for source, count in source_counts.items():
            logger.info(f"  - {source}: {count} articles")
        
        logger.info(f"Sample article titles:")
        for i, article in enumerate(diversified_articles[:5]):  # First 5 articles
            title = article.get('title', 'No title')
            logger.info(f"  {i+1}. {title}")
    
    # Compare results
    if len(diversified_articles) > len(standard_articles):
        logger.info(f"SUCCESS: Query expansion increased article count from {len(standard_articles)} to {len(diversified_articles)}")
    else:
        logger.info(f"FAILURE: Query expansion did not increase article count. Standard: {len(standard_articles)}, Diversified: {len(diversified_articles)}")

if __name__ == "__main__":
    asyncio.run(test_diversified_fetcher()) 