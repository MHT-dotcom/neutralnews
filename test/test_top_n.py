import requests
import json
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_article_count(query):
    """Test the article count for a specific query."""
    logger.info(f"Testing article count for query: '{query}'")
    
    try:
        # Make a request to the API
        response = requests.post(
            "http://localhost:5001/data",
            json={"event": query},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            
            # Count articles per source
            source_counts = {}
            for article in articles:
                source = article.get("source", "Unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
            
            logger.info(f"Query: '{query}'")
            logger.info(f"Total articles: {len(articles)}")
            logger.info(f"Total sources: {len(source_counts)}")
            logger.info(f"Articles per source: {source_counts}")
            
            if query.lower() == "wheat prices food":
                if len(articles) > 5:
                    logger.info(f"SUCCESS: The fix for '{query}' is working! Returned {len(articles)} articles.")
                    return True
                else:
                    logger.warning(f"FAILURE: The fix for '{query}' is not working. Only returned {len(articles)} articles.")
                    return False
            
            return len(articles)
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 0

def main():
    """Run the test for the problematic query and a comparison query."""
    logger.info("=" * 50)
    logger.info("TESTING TOP_N SPECIAL CASE FIX")
    logger.info("=" * 50)
    
    # Test the problematic query
    wheat_result = test_article_count("wheat prices food")
    
    # Test a comparison query
    ukraine_result = test_article_count("Ukraine")
    
    # Report results
    logger.info("=" * 50)
    logger.info("TEST RESULTS")
    logger.info("=" * 50)
    
    if wheat_result and isinstance(wheat_result, bool):
        logger.info("The fix for 'wheat prices food' is working!")
    elif isinstance(wheat_result, bool):
        logger.error("The fix for 'wheat prices food' is NOT working.")
    
    if isinstance(ukraine_result, int) and ukraine_result > 0:
        logger.info(f"The comparison query 'Ukraine' returned {ukraine_result} articles (for reference).")

if __name__ == "__main__":
    main() 