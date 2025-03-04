"""
This module provides mock implementations of key services for testing.
It includes mock versions of API fetchers, processors, and other services
to avoid making real API calls during testing.
"""

import json
import time
from mock_data import (
    MOCK_ARTICLES, 
    MOCK_NEWSAPI_RESPONSE, 
    MOCK_GUARDIAN_RESPONSE, 
    MOCK_GNEWS_RESPONSE,
    MOCK_SENTIMENT_RESULTS,
    MOCK_SUMMARY_RESULTS,
    get_mock_articles
)

class MockResponse:
    """Mock response object that mimics requests.Response"""
    def __init__(self, json_data, status_code=200, text=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text or json.dumps(json_data)
        self.ok = 200 <= status_code < 300
    
    def json(self):
        return self.json_data

# Mock API fetchers
def mock_fetch_newsapi(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of NewsAPI fetcher"""
    time.sleep(0.1)  # Simulate network delay
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        # Ensure source is properly structured
        if 'source' not in article or not isinstance(article['source'], dict) or 'name' not in article['source']:
            article['source'] = {"name": f"Mock Source {i+1}"}
        articles.append(article)
    return articles

# Add all the fetcher functions needed by routes.py
def fetch_newsapi_org(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of NewsAPI.org fetcher"""
    return mock_fetch_newsapi(query, api_key, days_back, max_articles)

def fetch_guardian(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of Guardian API fetcher"""
    time.sleep(0.1)  # Simulate network delay
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": "The Guardian"}
        articles.append(article)
    return articles

def fetch_aylien_articles(query, app_id=None, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of Aylien API fetcher"""
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": f"Aylien Source {i+1}"}
        articles.append(article)
    return articles

def fetch_gnews_articles(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of GNews API fetcher"""
    time.sleep(0.1)  # Simulate network delay
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": f"GNews Source {i+1}"}
        articles.append(article)
    return articles

def fetch_nyt_articles(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of NYT API fetcher"""
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": "The New York Times"}
        articles.append(article)
    return articles

def fetch_mediastack_articles(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of Mediastack API fetcher"""
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": f"Mediastack Source {i+1}"}
        articles.append(article)
    return articles

def fetch_newsapi_ai_articles(query, api_key=None, days_back=7, max_articles=10):
    """Mock implementation of NewsAPI.ai fetcher"""
    articles = []
    for i in range(min(max_articles, len(MOCK_ARTICLES))):
        article = MOCK_ARTICLES[i].copy()
        article['source'] = {"name": f"NewsAPI.ai Source {i+1}"}
        articles.append(article)
    return articles

# Mock processors
def mock_analyze_sentiment(text):
    """Mock implementation of sentiment analysis"""
    time.sleep(0.05)  # Simulate processing delay
    return MOCK_SENTIMENT_RESULTS.get(text, 0.0)

def mock_generate_summary(text, max_length=100, min_length=30):
    """Mock implementation of text summarization"""
    time.sleep(0.1)  # Simulate processing delay
    return MOCK_SUMMARY_RESULTS.get(text, "This is a mock summary.")

def mock_calculate_relevance(article, query):
    """Mock implementation of relevance calculation"""
    return 0.8  # Return a fixed relevance score for testing

def mock_calculate_popularity(article):
    """Mock implementation of popularity calculation"""
    return 0.7  # Return a fixed popularity score for testing

# Mock processor functions needed by routes.py
def process_articles(articles, query):
    """Mock implementation of article processing"""
    for article in articles:
        article["sentiment_score"] = mock_analyze_sentiment(article.get("content", ""))
        article["relevance_score"] = mock_calculate_relevance(article, query)
        article["popularity_score"] = mock_calculate_popularity(article)
        article["combined_score"] = 0.8 * article["relevance_score"] + 0.2 * article["popularity_score"]
        article["summary"] = mock_generate_summary(article.get("content", ""))
    return articles

def remove_duplicates(articles):
    """Mock implementation of duplicate removal"""
    # Just return the articles as is for testing
    return articles

def filter_relevant_articles(articles, threshold=0.05):
    """Mock implementation of relevance filtering"""
    # Just return the articles as is for testing
    return articles

def summarize_articles(articles, query):
    """Mock implementation of article summarization"""
    return "This is a mock summary of all the articles about " + query

# Mock trends function
def get_trending_topics(limit=4):
    """
    Mock implementation of trending topics.
    
    Args:
        limit (int): Maximum number of topics to return. Defaults to 4.
        
    Returns:
        list: A list of trending topic strings
    """
    topics = ["Climate Change", "Technology", "Politics", "Economy"]
    return topics[:limit]

# Mock ModelManager for testing
class MockModelManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MockModelManager()
        return cls._instance
    
    def __init__(self):
        self.sentiment_model = "mock_sentiment_model"
        self.summarizer_model = "mock_summarizer_model"
    
    def analyze_sentiment(self, text):
        return mock_analyze_sentiment(text)
    
    def generate_summary(self, text, max_length=100, min_length=30):
        return mock_generate_summary(text, max_length, min_length)
    
    def get_sentiment_analyzer(self):
        """Mock method to return a sentiment analyzer"""
        return self
    
    def get_summarizer(self):
        """Mock method to return a summarizer"""
        return self
    
    def clear_models(self):
        """Mock method to clear models"""
        pass
    
    def __call__(self, texts):
        """Make the MockModelManager callable to simulate sentiment analysis"""
        if isinstance(texts, list):
            return [{'score': 0.8, 'label': 'POSITIVE'} for _ in texts]  # Return positive sentiment for all texts
        return {'score': 0.8, 'label': 'POSITIVE'}  # Return positive sentiment for a single text

# Function to patch modules for testing
def patch_modules():
    """
    Patch key modules with mock implementations for testing.
    This function should be called at the beginning of tests.
    """
    import sys
    import types
    
    # Create mock modules
    mock_fetchers = types.ModuleType('fetchers')
    mock_processors = types.ModuleType('processors')
    mock_trends = types.ModuleType('trends')
    
    # Add mock functions to fetchers module
    mock_fetchers.fetch_newsapi = mock_fetch_newsapi
    mock_fetchers.fetch_newsapi_org = fetch_newsapi_org
    mock_fetchers.fetch_guardian = fetch_guardian
    mock_fetchers.fetch_aylien_articles = fetch_aylien_articles
    mock_fetchers.fetch_gnews_articles = fetch_gnews_articles
    mock_fetchers.fetch_nyt_articles = fetch_nyt_articles
    mock_fetchers.fetch_mediastack_articles = fetch_mediastack_articles
    mock_fetchers.fetch_newsapi_ai_articles = fetch_newsapi_ai_articles
    
    # Add mock functions to processors module
    mock_processors.analyze_sentiment = mock_analyze_sentiment
    mock_processors.generate_summary = mock_generate_summary
    mock_processors.calculate_relevance = mock_calculate_relevance
    mock_processors.calculate_popularity = mock_calculate_popularity
    mock_processors.process_articles = process_articles
    mock_processors.remove_duplicates = remove_duplicates
    mock_processors.filter_relevant_articles = filter_relevant_articles
    mock_processors.summarize_articles = summarize_articles
    mock_processors.ModelManager = MockModelManager
    
    # Add mock functions to trends module
    mock_trends.get_trending_topics = get_trending_topics
    
    # Replace real modules with mock modules in sys.modules
    sys.modules['fetchers'] = mock_fetchers
    sys.modules['processors'] = mock_processors
    sys.modules['trends'] = mock_trends
    
    return {
        'fetchers': mock_fetchers,
        'processors': mock_processors,
        'trends': mock_trends
    } 