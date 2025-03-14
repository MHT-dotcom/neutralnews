import logging
import json
from datetime import datetime, timedelta
from fetchers import fetch_grok_trending_topics

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_grok_api():
    """Test the Grok API integration with detailed logging"""
    logger.info("=== STARTING GROK API TEST ===")
    
    # Test for today
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # First test: Get topics for today only
    logger.info("TEST 1: Fetching topics for today only")
    topics_today = fetch_grok_trending_topics(max_topics=4, start_date=today, end_date=today)
    logger.info(f"Results for today: {json.dumps(topics_today, indent=2)}")
    
    # Second test: Get topics for yesterday to today
    logger.info("TEST 2: Fetching topics for yesterday to today")
    topics_range = fetch_grok_trending_topics(max_topics=4, start_date=yesterday, end_date=today)
    logger.info(f"Results for date range: {json.dumps(topics_range, indent=2)}")
    
    # Analyze results
    is_fallback_today = topics_today[0] == ['Ukraine Agrees to Ceasefire After U.S. Talks', 'Ukraine ceasefire']
    is_fallback_range = topics_range[0] == ['Ukraine Agrees to Ceasefire After U.S. Talks', 'Ukraine ceasefire']
    
    logger.info(f"Using fallback for today's topics: {is_fallback_today}")
    logger.info(f"Using fallback for date range topics: {is_fallback_range}")
    
    return {
        "today": topics_today,
        "date_range": topics_range,
        "using_fallback": is_fallback_today
    }

if __name__ == "__main__":
    results = test_grok_api()
    print("\n=== RESULTS SUMMARY ===")
    print(f"Success: {'No, using fallback' if results['using_fallback'] else 'Yes, using API'}")
    print("\nToday's Topics:")
    for i, (headline, keywords) in enumerate(results["today"], 1):
        print(f"{i}. {headline} ({keywords})") 