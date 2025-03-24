import requests
import json
import logging
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_query(query, description=None):
    """Test a specific query against the API."""
    if description:
        logger.info(f"Testing query: '{query}' ({description})")
    else:
        logger.info(f"Testing query: '{query}'")
    
    start_time = time.time()
    
    # Make request to local API
    try:
        response = requests.post(
            "http://localhost:5001/data",
            json={"event": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant information
            articles = data.get("articles", [])
            summary = data.get("summary", "No summary provided")
            
            # Calculate source distribution
            source_distribution = {}
            for article in articles:
                source = article.get("source", "Unknown")
                source_distribution[source] = source_distribution.get(source, 0) + 1
            
            # Log results
            logger.info(f"Status: Success")
            logger.info(f"Number of articles: {len(articles)}")
            logger.info(f"Source distribution: {source_distribution}")
            logger.info(f"Summary: {summary[:100]}...")
            
            # If we have articles, log details about the first few
            if articles:
                logger.info(f"Sample articles:")
                for i, article in enumerate(articles[:3]):  # First 3 articles
                    title = article.get("title", "No title")
                    source = article.get("source", "Unknown")
                    logger.info(f"  {i+1}. {title} (Source: {source})")
            
            # Check if number of articles is sufficient
            if len(articles) <= 5:
                logger.warning(f"Query '{query}' only returned {len(articles)} articles")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Request completed in {elapsed_time:.2f} seconds\n")
            return len(articles), source_distribution
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return 0, {}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return 0, {}

def main():
    """Run tests for the problematic query and alternatives."""
    logger.info("=" * 50)
    logger.info("TESTING QUERY EXPANSION SOLUTION")
    logger.info("=" * 50)
    
    # Test the original problematic query
    original_count, original_sources = test_query("wheat prices food", "Original problematic query")
    
    # Test some alternative queries for comparison
    alt_queries = [
        "Ukraine", 
        "artificial intelligence",
        "climate change"
    ]
    
    alt_results = {}
    for query in alt_queries:
        count, sources = test_query(query, "Comparison query")
        alt_results[query] = (count, sources)
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Original query 'wheat prices food': {original_count} articles from {len(original_sources)} sources")
    
    for query, (count, sources) in alt_results.items():
        logger.info(f"Alternative query '{query}': {count} articles from {len(sources)} sources")
    
    # Verdict
    if original_count > 5:
        logger.info("SUCCESS: Query expansion solution is working! The problematic query now returns more than 5 articles.")
    else:
        logger.info("FAILURE: Query expansion solution is not effective. The problematic query still returns 5 or fewer articles.")

if __name__ == "__main__":
    main() 