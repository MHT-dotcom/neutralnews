import requests
from datetime import datetime, timedelta
import logging
from config import (
    NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY, 
    GNEWS_API_KEY, DEFAULT_DAYS_BACK, NYT_API_KEY, MEDIASTACK_API_KEY, 
    NEWSAPI_AI_KEY, MAX_ARTICLES_PER_API
)
from aylienapiclient import textapi
from aylienapiclient.errors import Error as AylienError

# Set up logging
logger = logging.getLogger(__name__)

def fetch_newsapi_org(event, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://newsapi.org/v2/everything?q={event}&from={from_date}&pageSize={MAX_ARTICLES_PER_API}&apiKey={NEWSAPI_ORG_KEY}"
    try:
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles_count = len(data.get('articles', []))
            logger.info(f"NewsAPI.org: Fetched {articles_count} articles for event '{event}' from {from_date}")
            return data.get('articles', [])
        else:
            logger.error(f"NewsAPI.org error: {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from NewsAPI.org")
        return []
    except Exception as e:
        logger.error(f"Error fetching from NewsAPI.org: {e}")
        return []

def fetch_guardian(event, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://content.guardianapis.com/search?q={event}&from-date={from_date}&page-size={MAX_ARTICLES_PER_API}&api-key={GUARDIAN_API_KEY}"
    try:
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles_count = len(data.get('response', {}).get('results', []))
            logger.info(f"The Guardian: Fetched {articles_count} articles for event '{event}' from {from_date}")
            return data.get('response', {}).get('results', [])
        else:
            logger.error(f"The Guardian error: {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from The Guardian")
        return []
    except Exception as e:
        logger.error(f"Error fetching from The Guardian: {e}")
        return []

def fetch_aylien_articles(event, app_id=AYLIEN_APP_ID, api_key=AYLIEN_API_KEY, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
    try:
        client = textapi.Client(app_id, api_key)
        
        # Set timeout for the API call
        import requests
        old_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        old_session.mount('http://', adapter)
        old_session.mount('https://', adapter)
        with requests.Session() as session:
            session.request = lambda method, url, **kwargs: old_session.request(method, url, **kwargs, timeout=5)
            response = client.Stories(
                text=event,
                language=['en'],
                per_page=MAX_ARTICLES_PER_API,
                published_at_start=from_date,
                _request_timeout=5
            )
        
        articles_count = len(response['stories'])
        logger.info(f"Aylien: Fetched {articles_count} articles for event '{event}' from {from_date}")
        return response['stories']
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
    url = f"https://gnews.io/api/v4/search?q={event}&from={from_date}&token={api_key}&max={MAX_ARTICLES_PER_API}"
    try:
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles_count = len(data.get('articles', []))
            logger.info(f"GNews: Fetched {articles_count} articles for event '{event}' from {from_date}")
            return data.get('articles', [])
        else:
            logger.error(f"GNews error: {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from GNews")
        return []
    except Exception as e:
        logger.error(f"Error fetching from GNews: {e}")
        return []

def fetch_nyt_articles(event, api_key=NYT_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Fetch articles from the New York Times API."""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q={event}&api-key={api_key}&begin_date={from_date}&page-size={MAX_ARTICLES_PER_API}"
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

def fetch_mediastack_articles(event, api_key=MEDIASTACK_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Fetch articles from the Mediastack API."""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"http://api.mediastack.com/v1/news?access_key={api_key}&keywords={event}&date={from_date}&languages=en&limit={MAX_ARTICLES_PER_API}"
    try:
        logger.info(f"Mediastack: Making request to API for event '{event}'")
        response = requests.get(url, timeout=5)  # 5 seconds timeout
        if response.status_code == 200:
            data = response.json()
            articles = data.get('data', [])
            articles_count = len(articles)
            logger.info(f"Mediastack: Fetched {articles_count} articles for event '{event}' from {from_date}")
            logger.info(f"Mediastack: Response status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s")
            if articles_count == 0:
                logger.warning(f"Mediastack: No articles found in response: {data}")
            return articles
        else:
            logger.error(f"Mediastack error: {response.status_code}, Response: {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching from Mediastack")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Mediastack: {e}")
        return []

def fetch_newsapi_ai_articles(event, api_key=NEWSAPI_AI_KEY, days_back=DEFAULT_DAYS_BACK):
    """Fetch articles from the NewsAPI.ai API."""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://api.newsapi.ai/api/v1/article/getArticles"
    params = {
        "apiKey": api_key,
        "keyword": event,
        "dateStart": from_date,
        "language": "eng",
        "articlesCount": MAX_ARTICLES_PER_API
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
    except Exception as e:
        logger.error(f"Error fetching from NewsAPI.ai: {e}")
        return []

def fetch_articles(event, days_back=DEFAULT_DAYS_BACK):
    try:
        # Fetch from all sources with the same time window
        newsapi_org_articles = fetch_newsapi_org(event, days_back)
        aylien_articles = fetch_aylien_articles(event, days_back=days_back)
        gnews_articles = fetch_gnews_articles(event, days_back)
        guardian_articles = fetch_guardian(event, days_back)
        nyt_articles = fetch_nyt_articles(event, days_back=days_back)
        mediastack_articles = fetch_mediastack_articles(event, days_back=days_back)
        newsapi_ai_articles = fetch_newsapi_ai_articles(event, days_back=days_back)
        
        # Log counts from each source
        logger.info(f"Article counts for event '{event}' (past {days_back} days) - "
                   f"NewsAPI: {len(newsapi_org_articles)}, "
                   f"Aylien: {len(aylien_articles)}, "
                   f"GNews: {len(gnews_articles)}, "
                   f"Guardian: {len(guardian_articles)}, "
                   f"NYT: {len(nyt_articles)}, "
                   f"Mediastack: {len(mediastack_articles)}, "
                   f"NewsAPI.ai: {len(newsapi_ai_articles)}")
        
        # Combine all articles
        articles = (
            newsapi_org_articles +
            aylien_articles +
            gnews_articles +
            guardian_articles +
            nyt_articles +
            mediastack_articles +
            newsapi_ai_articles
        )
        logger.info(f"Total articles fetched for event '{event}' from past {days_back} days: {len(articles)}")
        return articles
    except Exception as e:
        logger.exception(f"Error in fetch_articles for event '{event}': {e}")
        return []