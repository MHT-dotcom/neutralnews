import logging
from fetchers import fetch_grok_trending_topics

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    logger.info("Testing Grok API integration")
    topics = fetch_grok_trending_topics(max_topics=4)
    
    print("\nRetrieved topics:")
    for i, (headline, keywords) in enumerate(topics, 1):
        print(f"{i}. {headline} ({keywords})")

if __name__ == "__main__":
    main() 