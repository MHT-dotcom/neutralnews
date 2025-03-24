import asyncio
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import fetcher functions
from fetchers import (
    fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
    fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
    fetch_newsapi_ai_articles, async_fetch_articles,
    fetch_newsapi_org_diversified, async_fetch_newsapi_org_diversified
)

async def check_api_responses():
    """Check API responses for 'wheat prices food' query."""
    query = "wheat prices food"
    logger.info(f"Testing API responses for query: '{query}'")
    
    # Fetch articles from all sources
    results = await async_fetch_articles(query)
    
    newsapi_org_articles, guardian_articles, aylien_articles, gnews_articles, nyt_articles, mediastack_articles, newsapi_ai_articles = results
    
    # Log the number of articles from each source
    sources = {
        "NewsAPI.org": newsapi_org_articles,
        "Guardian": guardian_articles,
        "Aylien": aylien_articles,
        "GNews": gnews_articles,
        "NYT": nyt_articles,
        "Mediastack": mediastack_articles,
        "NewsAPI.ai": newsapi_ai_articles
    }
    
    logger.info(f"=== API Response Summary for '{query}' ===")
    total_articles = 0
    for source_name, articles in sources.items():
        article_count = len(articles)
        total_articles += article_count
        logger.info(f"{source_name}: {article_count} articles")
        
        # If there are articles, log some details about the first few
        if article_count > 0:
            logger.info(f"Sample articles from {source_name}:")
            for i, article in enumerate(articles[:3]):  # Show up to 3 articles
                title = article.get('title', 'No title')
                url = article.get('url', 'No URL')
                logger.info(f"  {i+1}. {title[:60]}... | {url}")
    
    logger.info(f"Total articles across all sources: {total_articles}")
    
    # Test the diversified fetcher
    logger.info("\n=== Testing NewsAPI.org Diversified Fetcher ===")
    diversified_articles = await async_fetch_newsapi_org_diversified(query)
    logger.info(f"NewsAPI.org Diversified: {len(diversified_articles)} articles")
    
    if diversified_articles:
        source_counts = {}
        for article in diversified_articles:
            source = article.get('source', {}).get('name', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        logger.info(f"Source distribution in diversified results:")
        for source, count in source_counts.items():
            logger.info(f"  - {source}: {count} articles")
    
    logger.info("=== API Response Testing Complete ===")

if __name__ == "__main__":
    asyncio.run(check_api_responses()) 