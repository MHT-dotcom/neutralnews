# This file contains functions to fetch news articles from multiple APIs (NewsAPI.org, Guardian, Aylien, GNews, NYT, Mediastack, NewsAPI.ai)
# for a given event, using API keys from config_prod. Each function retrieves articles from a specific source over a specified time window
# (default 7 days), handles timeouts and errors with logging, and returns standardized article lists. The fetch_articles function combines
# results from all sources. Additionally, it fetches trending topics from the Grok API.

import requests

import json
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
try:
    from config_prod import (
        NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, NYT_API_KEY,
        MEDIASTACK_API_KEY, NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
        USE_NEWSAPI_ORG, USE_GUARDIAN, USE_GNEWS, USE_NYT,
        USE_MEDIASTACK, USE_NEWSDATA, USE_AYLIEN,
        DEFAULT_DAYS_BACK, NEWSAPI_AI_KEY, MAX_ARTICLES_PER_SOURCE,
        GROK_API_KEY  # Added for Grok API
    )
except ImportError:
    raise Exception("Could not load production config")
from aylienapiclient import textapi
from aylienapiclient.errors import Error as AylienError

logger = logging.getLogger(__name__)

# Centralized helper function for fetching with robust error handling, updated to support POST
def fetch_with_error_handling(url, params=None, headers=None, json=None):
    """
    Fetch data from an API with comprehensive error handling, supporting GET and POST.
    
    Args:
        url (str): The API endpoint URL.
        params (dict): Query parameters for the request (GET only).
        headers (dict): Headers for the request (optional).
        json (dict): JSON payload for POST requests (optional).
    
    Returns:
        tuple: (data, error_message) where data is the parsed JSON or None,
               and error_message is a string if an error occurred, or None if successful.
    """
    try:
        method = "POST" if json else "GET"
        response = requests.request(method, url, params=params, headers=headers, json=json, timeout=5)
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        data = response.json()  # Parse JSON response
        logger.debug(f"Successfully fetched from {url}, status: {response.status_code}")
        return data, None
    except requests.exceptions.Timeout as e:
        error_msg = f"{method} Timeout error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except requests.exceptions.TooManyRedirects as e:
        error_msg = f"{method} Too many redirects for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"{method} Request exception for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except json.decoder.JSONDecodeError as e:
        error_msg = f"JSON decoding error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected {method} error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg

def fetch_newsapi_org(event, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": event,
        "from": from_date,
        "pageSize": MAX_ARTICLES_PER_SOURCE,
        "apiKey": NEWSAPI_ORG_KEY
    }
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get("status") == "error":
        logger.error(f"NewsAPI.org API error: {data.get('message')}")
        return []
    articles = data.get('articles', [])
    logger.info(f"NewsAPI.org: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    return articles

def fetch_guardian(event, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://content.guardianapis.com/search"
    params = {
        "q": event,
        "from-date": from_date,
        "page-size": MAX_ARTICLES_PER_SOURCE,
        "api-key": GUARDIAN_API_KEY
    }
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get('response', {}).get('status') != "ok":
        logger.error(f"The Guardian API error: {data.get('response', {}).get('message', 'Unknown error')}")
        return []
    articles = data.get('response', {}).get('results', [])
    logger.info(f"The Guardian: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    return articles

def fetch_aylien_articles(event, app_id=AYLIEN_APP_ID, api_key=AYLIEN_API_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
    try:
        client = textapi.Client(app_id, api_key)
        # Custom session with timeout
        old_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        old_session.mount('http://', adapter)
        old_session.mount('https://', adapter)
        with requests.Session() as session:
            session.request = lambda method, url, **kwargs: old_session.request(method, url, **kwargs, timeout=5)
            response = client.Stories(
                text=event,
                language=['en'],
                per_page=MAX_ARTICLES_PER_SOURCE,
                published_at_start=from_date,
                _request_timeout=5
            )
        articles = response.get('stories', [])
        logger.info(f"Aylien: Fetched {len(articles)} articles for event '{event}' from {from_date}")
        return articles
    except AylienError as e:
        logger.error(f"Aylien API exception: {e}")
        return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from Aylien")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Aylien: {e}")
        return []

def fetch_gnews_articles(event, api_key=GNEWS_API_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": event,
        "from": from_date,
        "token": api_key,
        "max": MAX_ARTICLES_PER_SOURCE
    }
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    articles = data.get('articles', [])
    logger.info(f"GNews: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    return articles

def fetch_nyt_articles(event, api_key=NYT_API_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')  # NYT uses YYYYMMDD format
    url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    params = {
        "q": event,
        "api-key": api_key,
        "begin_date": from_date,
        "page-size": MAX_ARTICLES_PER_SOURCE
    }
    logger.info(f"NYT: Making request for event '{event}'")
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get('status') != "OK":
        logger.error(f"NYT API error: {data.get('fault', {}).get('faultstring', 'Unknown error')}")
        return []
    articles = data.get('response', {}).get('docs', [])
    logger.info(f"NYT: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    return articles

def fetch_mediastack_articles(event, api_key=MEDIASTACK_API_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": api_key,
        "keywords": event,
        "date": from_date,
        "languages": "en",
        "limit": MAX_ARTICLES_PER_SOURCE
    }
    logger.info(f"Mediastack: Making request for event '{event}'")
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get('error'):
        logger.error(f"Mediastack API error: {data.get('error', {}).get('message', 'Unknown error')}")
        return []
    articles = data.get('data', [])
    logger.info(f"Mediastack: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    if not articles:
        logger.warning(f"Mediastack: No articles found in response")
    return articles

def fetch_newsapi_ai_articles(event, api_key=NEWSAPI_AI_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://api.newsapi.ai/api/v1/article/getArticles"
    params = {
        "apiKey": api_key,
        "keyword": event,
        "dateStart": from_date,
        "language": "eng",
        "articlesCount": MAX_ARTICLES_PER_SOURCE
    }
    logger.info(f"NewsAPI.ai: Making request for event '{event}'")
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    articles = data.get('articles', {}).get('results', [])
    logger.info(f"NewsAPI.ai: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    if not articles:
        logger.warning(f"NewsAPI.ai: No articles found in response")
    return articles

def fetch_grok_trending_topics(api_key=GROK_API_KEY, max_topics=4):
    # logger.info(f"Fetching Grok trends with API key: {api_key[:4] if api_key else 'None'}...")
    # # Set date range explicitly
    # today = datetime.now().date()  # March 08, 2025
    # one_week_ago = today - timedelta(days=7)  # March 01, 2025
    # date_str = today.strftime("%B %d, %Y")
    # # More explicit query to demand real events
    # query = f"As of {date_str}, list the 4 most trending news events that occurred between {one_week_ago.strftime('%B %d, %Y')} and {date_str}. Provide only the event titles, numbered 1 to 4."
    # url = "https://api.x.ai/v1/chat/completions"
    # headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # payload = {
    #     "model": "grok-beta",
    #     "messages": [{"role": "user", "content": query}],
    #     "max_tokens": 200
    # }
    # logger.info(f"Grok request payload: {payload}")
    # data, error = fetch_with_error_handling(url, headers=headers, params=None, json=payload)
    # if error or not data:
    #     logger.error(f"Grok fetch failed: {error or 'No data'}")
    #     return ["Bitcoin Price Surge", "Climate Policy Update", "Election Results", "Economic Report"]
    # content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    # logger.info(f"Grok raw response: {content}")
    
    # # Parse into four event titles
    # topics = []
    # lines = content.split("\n")
    # for line in lines:
    #     line = line.strip()
    #     if line and line[0].isdigit() and ". " in line:
    #         topic = line.split(". ", 1)[1].strip().strip("**")  # Remove bold markers
    #         topics.append(topic)
    
    # Ensure exactly 4 topics
    # if len(topics) < 4:
    #     logger.warning(f"Only {len(topics)} topics found, padding with fallbacks")
    #     fallbacks = ["Bitcoin Price Surge", "Climate Policy Update", "Election Results", "Economic Report"]
    #     topics.extend(fallbacks[:4 - len(topics)])
    # elif len(topics) > 4:
    #     topics = topics[:4]
    
    # logger.info(f"Parsed trending topics: {topics}")
    # print("\n\n\n here are the topics: ", topics)
    # print("\n\n\n type: ", type(topics))
    # print("\n\n\n")

    topics = [ [
    'Trump Administration Imposes 25% Tariffs on Mexico and Canada',
    'Significant Lunar Landings by Private Companies',
    'Trump-Zelenskyy Meeting and Ukraine Aid Suspension',
    'South Korea’s Impeached President Yoon Suk Yeol Released from Prison',
    'Bitcoin ETF Sees Record Inflows After Regulatory Shift',
    'EU Sanctions Russian Crypto Exchange Garantex',
    'Pakistan Sets Deadline for Afghan Migrants to Leave',
    'French Rail Disrupted by WWII Bomb Discovery'], ['trump tariffs', 'lunar landings', 'trump zelenskyy', 'yoon suk yeol', 'bitcoin etf', 'eu sanctions', 'pakistan migrants', 'french rail']]
    return topics

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
    
    fetch_functions = [
        fetch_newsapi_ai_articles,
        fetch_guardian,
        fetch_nyt_articles,
        fetch_mediastack_articles,
        fetch_aylien_articles,
        fetch_newsapi_org,
        fetch_gnews_articles
    ]
    
    articles = []
    with ThreadPoolExecutor() as executor:
        future_to_api = {executor.submit(fn, topic, days_back): fn.__name__ for fn in fetch_functions}
        for future in future_to_api:
            try:
                api_articles = future.result()
                articles.extend(api_articles)
            except Exception as e:
                logger.error(f"Error in {future_to_api[future]} for topic '{topic}': {e}")
    
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

def fetch_articles(event, days_back=DEFAULT_DAYS_BACK):
    """
    Fetch articles from all configured APIs for a given event.
    
    Args:
        event (str): The event or query to search for.
        days_back (int): Time window in days (default from config).
    
    Returns:
        list: Combined list of articles from all sources.
    """
    try:
        fetch_functions = [
            (fetch_newsapi_org, USE_NEWSAPI_ORG),
            (fetch_aylien_articles, USE_AYLIEN),
            (fetch_gnews_articles, USE_GNEWS),
            (fetch_guardian, USE_GUARDIAN),
            (fetch_nyt_articles, USE_NYT),
            (fetch_mediastack_articles, USE_MEDIASTACK),
            (fetch_newsapi_ai_articles, USE_NEWSDATA)
        ]
        
        articles = []
        with ThreadPoolExecutor() as executor:
            future_to_api = {
                executor.submit(fn, event, days_back): fn.__name__
                for fn, use_flag in fetch_functions if use_flag
            }
            for future in future_to_api:
                try:
                    api_articles = future.result()
                    articles.extend(api_articles)
                except Exception as e:
                    logger.error(f"Error in {future_to_api[future]} for event '{event}': {e}")
        
        logger.info(f"Total articles fetched for event '{event}' from past {days_back} days: {len(articles)}")
        return articles
    except Exception as e:
        logger.exception(f"Critical error in fetch_articles for event '{event}': {e}")
        return []