"""
This file contains functions to fetch news articles from multiple APIs.
Each function retrieves articles from a specific source over a specified time window,
handles timeouts and errors with logging, and returns standardized article lists.
"""
import requests
import json
import time
import inspect
import os
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from flask import current_app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log when this module is imported
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Fetchers module is being imported")

# Log the call stack to see who's importing this module
current_frame = inspect.currentframe()
try:
    call_stack = inspect.getouterframes(current_frame)
    caller_info = ", ".join([f"{frame.filename}:{frame.lineno}" for frame in call_stack[1:4]])
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Fetchers module imported by: {caller_info}")
except Exception as e:
    logger.error(f"[IMPORT_SEQUENCE] Error getting call stack: {e}")
finally:
    del current_frame  # Prevent reference cycles

# Track configuration access attempts
config_access_attempts = {}

def get_config(key, default=None):
    """Helper function to safely get config values"""
    try:
        # Try to access the config within application context
        return current_app.config.get(key, default)
    except RuntimeError:
        # If we're outside of application context (e.g., during testing)
        logger.warning(f"Accessing {key} outside application context")
        
        # Check environment variables directly as a fallback
        env_key = key.upper()  # Convert to uppercase for environment variable convention
        if env_key in os.environ:
            env_value = os.environ.get(env_key)
            # Log the fact that we found the value in environment variables
            if any(x in key.upper() for x in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                logger.info(f"Found {key} in environment variables (length: {len(env_value)})")
            else:
                logger.info(f"Found {key} in environment variables: {env_value}")
            return env_value
            
        return default

def fetch_newsapi_org(event, days_back=None):
    """Fetch articles from NewsAPI.org"""
    logger.info(f"[FETCHER_CALL] {time.time()} - fetch_newsapi_org called for event: {event}")
    
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    max_articles = get_config('MAX_ARTICLES_PER_API', 4)
    api_key = get_config('NEWSAPI_ORG_KEY', '')

    if not api_key or not get_config('USE_NEWSAPI_ORG', False):
        logger.info(f"NewsAPI.org is disabled or missing API key (key length: {len(api_key)})")
        use_flag = get_config('USE_NEWSAPI_ORG', False)
        logger.info(f"USE_NEWSAPI_ORG flag value: {use_flag}")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://newsapi.org/v2/everything?q={event}&from={from_date}&pageSize={max_articles}&apiKey={api_key}"
    
    logger.info(f"NewsAPI.org: Requesting articles for '{event}' from {from_date}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            logger.info(f"NewsAPI.org: Fetched {len(articles)} articles for event '{event}' from {from_date}")
            return articles
        else:
            logger.error(f"NewsAPI.org error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"NewsAPI.org exception: {str(e)}")
        return []

def fetch_guardian(event, days_back=None):
    """Fetch articles from The Guardian"""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    max_articles = get_config('MAX_ARTICLES_PER_API', 4)
    api_key = get_config('GUARDIAN_API_KEY', '')

    if not api_key or not get_config('USE_GUARDIAN', False):
        logger.info("The Guardian is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://content.guardianapis.com/search?q={event}&from-date={from_date}&page-size={max_articles}&api-key={api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('response', {}).get('results', [])
            logger.info(f"The Guardian: Fetched {len(articles)} articles for event '{event}' from {from_date}")
            return articles
        else:
            logger.error(f"The Guardian error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching from The Guardian: {e}")
        return []

def fetch_aylien_articles(event, app_id=None, api_key=None, days_back=None):
    """Fetch articles from Aylien"""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    app_id = app_id or get_config('AYLIEN_APP_ID', '')
    api_key = api_key or get_config('AYLIEN_API_KEY', '')

    if not app_id or not api_key or not get_config('USE_AYLIEN', False):
        logger.info("Aylien is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
    try:
        # Use the newer aylien-news-api client instead of the deprecated aylien-apiclient
        import aylien_news_api
        from aylien_news_api.rest import ApiException
        
        # Configure API key authorization
        configuration = aylien_news_api.Configuration()
        configuration.api_key['X-AYLIEN-NewsAPI-Application-ID'] = app_id
        configuration.api_key['X-AYLIEN-NewsAPI-Application-Key'] = api_key
        
        # Create an instance of the API class
        api_instance = aylien_news_api.DefaultApi(aylien_news_api.ApiClient(configuration))
        
        # Set timeout for the API call
        import requests
        old_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        old_session.mount('http://', adapter)
        old_session.mount('https://', adapter)
        
        # Set up parameters for the stories endpoint
        opts = {
            'title': event,
            'language': ['en'],
            'published_at_start': from_date,
            'per_page': get_config('MAX_ARTICLES_PER_API', 4),
            'sort_by': 'relevance'
        }
        
        # Make the API call with timeout
        with requests.Session() as session:
            session.request = lambda method, url, **kwargs: old_session.request(method, url, **kwargs, timeout=5)
            api_response = api_instance.list_stories(**opts)
        
        stories = api_response.stories
        articles_count = len(stories)
        logger.info(f"Aylien: Fetched {articles_count} articles for event '{event}' from {from_date}")
        
        # Convert the response to the expected format
        articles = []
        for story in stories:
            article = {
                'title': story.title,
                'description': story.summary.sentences[0] if story.summary and story.summary.sentences else "",
                'url': story.links.permalink,
                'urlToImage': story.media[0].url if story.media and len(story.media) > 0 else None,
                'publishedAt': story.published_at.isoformat() if story.published_at else None,
                'source': {'name': story.source.name if story.source and story.source.name else 'Aylien'},
                'content': story.body
            }
            articles.append(article)
        
        return articles
    except ApiException as e:
        logger.error(f"Aylien API exception: {e}")
        return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from Aylien")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Aylien: {e}")
        return []

def fetch_gnews_articles(event, api_key=None, days_back=None):
    """Fetch articles from GNews"""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    api_key = api_key or get_config('GNEWS_API_KEY', '')

    if not api_key or not get_config('USE_GNEWS', False):
        logger.info("GNews is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://gnews.io/api/v4/search?q={event}&from={from_date}&token={api_key}&max={get_config('MAX_ARTICLES_PER_API', 4)}"
    try:
        logger.info(f"GNews: Making request to API for event '{event}'")
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles_count = len(data.get('articles', []))
            logger.info(f"GNews: Fetched {articles_count} articles for event '{event}' from {from_date}")
            return data.get('articles', [])
        elif response.status_code == 403:
            logger.error(f"GNews authorization error (403): Invalid API key or subscription expired")
            return []
        else:
            try:
                data = response.json()
                error_msg = data.get('errors', {})
                logger.error(f"GNews error: {response.status_code}, Error details: {error_msg}")
            except:
                logger.error(f"GNews error: {response.status_code}, Response: {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from GNews")
        return []
    except Exception as e:
        logger.error(f"Error fetching from GNews: {e}")
        return []

def fetch_nyt_articles(event, api_key=None, days_back=None):
    """Fetch articles from the New York Times API."""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    api_key = api_key or get_config('NYT_API_KEY', '')

    if not api_key or not get_config('USE_NYT', False):
        logger.info("The New York Times is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q={event}&api-key={api_key}&begin_date={from_date}&page-size={get_config('MAX_ARTICLES_PER_API', 4)}"
    try:
        logger.info(f"NYT: Making request to {url} for event '{event}'")
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles = data.get('response', {}).get('docs', [])
            articles_count = len(articles)
            logger.info(f"NYT: Fetched {articles_count} articles for event '{event}' from {from_date}")
            logger.info(f"NYT: Response status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s")
            return articles
        else:
            logger.error(f"NYT error: {response.status_code}, Response: {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from NYT")
        return []
    except Exception as e:
        logger.error(f"Error fetching from NYT: {e}")
        return []

def fetch_mediastack_articles(event, api_key=None, days_back=None):
    """Fetch articles from the Mediastack API."""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    api_key = api_key or get_config('MEDIASTACK_API_KEY', '')

    if not api_key or not get_config('USE_MEDIASTACK', False):
        logger.info("Mediastack is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"http://api.mediastack.com/v1/news?access_key={api_key}&keywords={event}&date={from_date}&languages=en&limit={get_config('MAX_ARTICLES_PER_API', 4)}"
    try:
        logger.info(f"Mediastack: Making request to API for event '{event}'")
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            # Check for rate limit error in the response
            if data.get('error') and 'usage limit' in data.get('error', {}).get('message', '').lower():
                logger.error(f"Mediastack rate limit exceeded: {data['error']['message']}")
                return []
            
            articles = data.get('data', [])
            articles_count = len(articles)
            logger.info(f"Mediastack: Fetched {articles_count} articles for event '{event}' from {from_date}")
            logger.info(f"Mediastack: Response status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s")
            if articles_count == 0:
                logger.warning(f"Mediastack: No articles found in response: {data}")
            return articles
        else:
            # Check for rate limit in error response
            try:
                data = response.json()
                if data.get('error') and 'usage limit' in data.get('error', {}).get('message', '').lower():
                    logger.error(f"Mediastack rate limit exceeded: {data['error']['message']}")
                else:
                    logger.error(f"Mediastack error: {response.status_code}, Response: {response.text}")
            except:
                logger.error(f"Mediastack error: {response.status_code}, Response: {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from Mediastack")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Mediastack: {e}")
        return []

def fetch_newsapi_ai_articles(event, api_key=None, days_back=None):
    """Fetch articles from the NewsAPI.ai API."""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    api_key = api_key or get_config('NEWSAPI_AI_KEY', '')

    if not api_key or not get_config('USE_NEWSAPI_AI', False):
        logger.info("NewsAPI.ai is disabled or missing API key")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://api.newsapi.ai/api/v1/article/getArticles"
    params = {
        "apiKey": api_key,
        "keyword": event,
        "dateStart": from_date,
        "language": "eng",
        "articlesCount": get_config('MAX_ARTICLES_PER_API', 4)
    }
    try:
        logger.info(f"NewsAPI.ai: Making request to API for event '{event}' with params: {params}")
        response = requests.get(url, params=params, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', {}).get('results', [])
            articles_count = len(articles)
            logger.info(f"NewsAPI.ai: Fetched {articles_count} articles for event '{event}' from {from_date}")
            logger.info(f"NewsAPI.ai: Response status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s")
            if articles_count == 0:
                logger.warning(f"NewsAPI.ai: No articles found in response: {data}")
            return articles
        else:
            logger.error(f"NewsAPI.ai error: {response.status_code}, Response: {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from NewsAPI.ai")
        return []
    except requests.exceptions.ConnectionError as e:
        if "Failed to resolve" in str(e) or "Name or service not known" in str(e):
            logger.error(f"DNS resolution error for NewsAPI.ai: {e}")
        else:
            logger.error(f"Connection error for NewsAPI.ai: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching from NewsAPI.ai: {e}")
        return []

def fetch_articles_for_topic(topic, max_articles=3, days_back=7):
    """
    Fetch articles related to a specific trending topic from all configured APIs.
    
    Args:
        topic (str): The trending topic to search for.
        max_articles (int): Maximum number of articles to return (default: 3).
        days_back (int): Time window in days to search articles (default: 7).
    
    Returns:
        list: List of standardized article dictionaries.
    """
    logger.info(f"Fetching articles for topic: {topic}")
    
    # Use existing fetch functions (assume they are defined as fetch_newsapi_articles, fetch_guardian_articles, etc.)
    fetch_functions = [
        fetch_newsapi_ai_articles,
        fetch_guardian,
        fetch_nyt_articles,
        fetch_mediastack_articles,
        fetch_aylien_articles,
        fetch_newsapi_org,
        fetch_gnews_articles
        # Add other API fetchers as needed
    ]
    
    articles = []
    with ThreadPoolExecutor() as executor:
        # Fetch articles in parallel from all APIs
        future_to_api = {executor.submit(fn, topic, days_back): fn.__name__ for fn in fetch_functions}
        for future in future_to_api:
            try:
                api_articles = future.result()
                articles.extend(api_articles)
            except Exception as e:
                logger.error(f"Error in {future_to_api[future]} for topic '{topic}': {e}")
    
    # Sort by relevance (assuming articles have a 'published_at' or similar field) and limit
    articles = sorted(articles, key=lambda x: x.get('published_at', ''), reverse=True)[:max_articles]
    logger.info(f"Fetched {len(articles)} articles for topic: {topic}")
    return articles

def fetch_trending_articles(topics, max_articles_per_topic=3):
    """
    Fetch articles for a list of trending topics.
    
    Args:
        topics (list): List of trending topic strings.
        max_articles_per_topic (int): Number of articles per topic (default: 3).
    
    Returns:
        dict: Dictionary mapping topics to their articles.
    """
    trending_data = {}
    with ThreadPoolExecutor() as executor:
        future_to_topic = {executor.submit(fetch_articles_for_topic, topic, max_articles_per_topic): topic for topic in topics}
        for future in future_to_topic:
            topic = future_to_topic[future]
            try:
                trending_data[topic] = future.result()
            except Exception as e:
                logger.error(f"Error fetching articles for topic '{topic}': {e}")
                trending_data[topic] = []
    return trending_data

def fetch_articles(event, days_back=None):
    """Fetch articles from all configured sources"""
    days_back = days_back or get_config('DEFAULT_DAYS_BACK', 7)
    
    try:
        # Only fetch from enabled sources
        articles = []
        
        if get_config('USE_NEWSAPI_ORG'):
            articles.extend(fetch_newsapi_org(event, days_back))
        
        if get_config('USE_GUARDIAN'):
            articles.extend(fetch_guardian(event, days_back))
            
        if get_config('USE_AYLIEN'):
            articles.extend(fetch_aylien_articles(event, days_back=days_back))
            
        if get_config('USE_GNEWS'):
            articles.extend(fetch_gnews_articles(event, days_back))
            
        if get_config('USE_NYT'):
            articles.extend(fetch_nyt_articles(event, days_back=days_back))
            
        if get_config('USE_MEDIASTACK'):
            articles.extend(fetch_mediastack_articles(event, days_back=days_back))
            
        if get_config('USE_NEWSAPI_AI'):
            articles.extend(fetch_newsapi_ai_articles(event, days_back=days_back))
        
        logger.info(f"Total articles fetched for event '{event}' from past {days_back} days: {len(articles)}")
        return articles
        
    except Exception as e:
        logger.exception(f"Error in fetch_articles for event '{event}': {e}")
        return []