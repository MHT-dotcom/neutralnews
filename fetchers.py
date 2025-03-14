# This file contains functions to fetch news articles from multiple APIs (NewsAPI.org, Guardian, Aylien, GNews, NYT, Mediastack, NewsAPI.ai)
# for a given event, using API keys from config_prod. Each function retrieves articles from a specific source over a specified time window
# (default 7 days), handles timeouts and errors with logging, and returns standardized article lists. The fetch_articles function combines
# results from all sources. Additionally, it fetches trending topics from the Grok API.

import requests
import random
import json
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import socket
import ssl
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
logger.setLevel(logging.DEBUG)

# Add a handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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

def fetch_grok_trending_topics(max_topics=8, start_date=None, end_date=None, time_period="current"):
    """
    Fetch trending news topics from Grok API for a specified date range and return them as a 2D list.
    Falls back to hardcoded topics if API fails.
    
    Args:
        max_topics (int): Number of trending topics to fetch.
        start_date (str, optional): Start date in "YYYY-MM-DD" format. Defaults to today if None.
        end_date (str, optional): End date in "YYYY-MM-DD" format. Defaults to today if None.
        time_period (str): Either "current" or "last_week" to determine which fallback list to use.
    
    Returns:
        list: 2D list of [headline, keywords] pairs, e.g., [['Headline', 'kw1 kw2'], ...].
    """
    logger.info(f"Starting fetch_grok_trending_topics function for {time_period} topics")
    
    # Hardcoded fallback topics for CURRENT week
    current_fallback_topics = [
        ['Ukraine-Russia Peace Talks Stall After New Sanctions', 'Ukraine Russia sanctions'],
        ['Tesla Unveils Robotaxi Plans for 2026 Rollout', 'Tesla robotaxi autonomous'],
        ['Federal Reserve Signals Potential Rate Cut', 'Fed interest rates economy'],
        ['Meta AI Assistant Now Available in 40 Languages', 'Meta AI assistant languages'],
        ['Record Temperatures Hit Mediterranean Countries', 'heatwave climate Mediterranean'],
        ['SpaceX Launches First Commercial Lunar Lander', 'SpaceX lunar lander commercial'],
        ['UN Report Warns of Critical Ocean Pollution Levels', 'ocean pollution plastic UN'],
        ['China Unveils New Economic Stimulus Package', 'China economy stimulus package']
    ]
    
    # Hardcoded fallback topics for LAST week
    last_week_fallback_topics = [
        ['US Passes Major Climate Legislation', 'climate bill emissions'],
        ['Twitter Introduces New Content Moderation Tools', 'Twitter moderation content'],
        ['Major Tech Companies Announce Layoffs', 'tech layoffs recession'],
        ['Japan Reopens Borders to International Tourism', 'Japan tourism COVID'],
        ['Breakthrough in Nuclear Fusion Energy Announced', 'fusion energy breakthrough'],
        ['Amazon Acquires Healthcare Provider for $4 Billion', 'Amazon healthcare acquisition'],
        ['Global Wheat Prices Stabilize After Recent Surge', 'wheat prices food'],
        ['New Malaria Vaccine Shows 80% Efficacy in Trials', 'malaria vaccine WHO']
    ]
    
    # Select appropriate fallback topics based on time_period
    if time_period == "last_week":
        fallback_topics = last_week_fallback_topics
        logger.info("Using LAST WEEK fallback topics list")
    else:
        fallback_topics = current_fallback_topics
        logger.info("Using CURRENT fallback topics list")
    
    # Ensure max_topics is between 1 and 8
    max_topics = min(max(1, max_topics), 8)
    
    # Set default dates if not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")  # e.g., "2025-03-13"
    if start_date is None:
        start_date = end_date  # Single day (today) if no range specified
    
    # Format dates for user-friendly display
    start_date_str = datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d, %Y")  # e.g., "March 6, 2025"
    end_date_str = datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d, %Y")  # e.g., "March 12, 2025"
    
    # Construct the prompt for Grok
    date_range_text = f"from {start_date_str} to {end_date_str}" if start_date != end_date else f"for {start_date_str}"
    
    prompt = (
        f"Analyze news and social media data {date_range_text} to identify the {max_topics} "
        "most talked-about news topics, including a mix of general news, technology, "
        "and business stories. For each topic, generate a concise, neutral headline (title only, "
        "no content) with no sentiment or sensationalism, and provide 2-3 relevant keywords "
        "that summarize the core elements of the story as a space-separated string.\n\n"
        "Return the results as a list of lists, where each inner list contains exactly two elements: "
        "the headline and the keyword string. Format the output exactly as: "
        "[['Headline', 'keyword1 keyword2'], ...]. Example: "
        "[['Trump raises tariffs on China', 'Trump tariffs'], ...]. "
        "Use current web search results and social media trends to determine prominence, prioritizing "
        "diverse, high-impact stories across categories like geopolitics, tech innovation, "
        "business developments, and political events."
    )
    
    # CORRECT API endpoint for xAI's Grok
    url = "https://api.x.ai/v1/chat/completions"
    logger.info(f"Using Grok API endpoint: {url}")
    
    # Log API key details (safely)
    if not GROK_API_KEY:
        logger.error("No GROK_API_KEY found")
        return fallback_topics
    
    key_preview = f"{GROK_API_KEY[:8]}...{GROK_API_KEY[-8:]}" if len(GROK_API_KEY) > 16 else "[key too short]"
    logger.info(f"Using API key: {key_preview}")
    
    # Use the full API key including the xai- prefix
    api_key = GROK_API_KEY  # Keep the original key with xai- prefix
    
    # Prepare headers for x.ai API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare payload in OpenAI-compatible format with CORRECT model name
    payload = {
        "model": "grok-2",  # UPDATED: This is the model name that works
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 800,
        "top_p": 1.0
    }
    
    logger.debug(f"Request payload structure: {list(payload.keys())}")
    
    try:
        # Make the API request
        logger.info(f"Making request to Grok API for {date_range_text}")
        
        # Use certifi for proper certificate verification
        import certifi
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=15,
            verify=certifi.where()  # Use certifi's certificate bundle
        )
        
        # Log response details
        logger.info(f"Grok API response status: {response.status_code}")
        
        # Check for successful response
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Parse response - OpenAI compatible format should have 'choices'
                if isinstance(data, dict) and "choices" in data and len(data["choices"]) > 0:
                    # Extract the content from the first choice
                    content = data["choices"][0]["message"]["content"]
                    logger.debug(f"Raw content: {content[:200]}...")
                    
                    # Parse the content to extract the list of lists
                    try:
                        # Try to safely evaluate the string representation of the list
                        import ast
                        topics = ast.literal_eval(content.strip())
                        
                        # Validate format
                        if (isinstance(topics, list) and 
                            all(isinstance(item, list) and len(item) == 2 and 
                                isinstance(item[0], str) and isinstance(item[1], str) 
                                for item in topics)):
                            
                            logger.info(f"Successfully parsed {len(topics)} topics from Grok API")
                            
                            # Limit to max_topics
                            if len(topics) > max_topics:
                                topics = topics[:max_topics]
                            
                            return topics
                        else:
                            logger.error(f"Invalid format in parsed content: {topics}")
                    except (SyntaxError, ValueError) as e:
                        logger.error(f"Failed to parse response content: {e}")
                        
                        # Attempt a more robust parsing approach for malformed responses
                        try:
                            # Look for list-like patterns in the text
                            import re
                            pattern = r"\[\s*['\"](.*?)['\"]\s*,\s*['\"](.*?)['\"]?\s*\]"
                            matches = re.findall(pattern, content)
                            
                            if matches and len(matches) >= 1:
                                parsed_topics = [[headline.strip(), keywords.strip()] for headline, keywords in matches]
                                logger.info(f"Recovered {len(parsed_topics)} topics with regex")
                                
                                # Limit to max_topics
                                if len(parsed_topics) > max_topics:
                                    parsed_topics = parsed_topics[:max_topics]
                                
                                return parsed_topics
                        except Exception as parse_e:
                            logger.error(f"Secondary parsing also failed: {parse_e}")
                else:
                    logger.error(f"Unexpected response format: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
        else:
            # Log error details
            logger.error(f"Grok API error: {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {error_data}")
                
                # If we get an authentication error, try alternative formats
                if response.status_code == 401 or response.status_code == 400:
                    logger.info("Trying alternative authentication format...")
                    
                    # Try with original key including xai- prefix
                    alt_headers = {
                        "Authorization": f"Bearer {GROK_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    logger.info(f"Trying with full key including xai- prefix")
                    alt_response = requests.post(
                        url, 
                        json=payload, 
                        headers=alt_headers, 
                        timeout=15,
                        verify=certifi.where()
                    )
                    
                    logger.info(f"Alternative auth response status: {alt_response.status_code}")
                    
                    if alt_response.status_code == 200:
                        # Process successful response
                        try:
                            data = alt_response.json()
                            content = data["choices"][0]["message"]["content"]
                            import ast
                            topics = ast.literal_eval(content.strip())
                            return topics[:max_topics]
                        except Exception as e:
                            logger.error(f"Failed to process alternative auth response: {e}")
            except:
                logger.error(f"Raw error response: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Exception details")
    
    # If we got here, something failed, return the appropriate fallback topics
    logger.warning(f"Falling back to hardcoded {time_period} topics")
    return fallback_topics[:max_topics]

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

def test_grok_api():
    """
    Test function to validate Grok API functionality
    """
    logger.info("=== Starting Grok API Test ===")
    
    # Test with specific dates
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Testing fetch_grok_trending_topics with dates: {start_date} to {end_date}")
    
    try:
        topics = fetch_grok_trending_topics(
            max_topics=3,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Received topics: {topics}")
        return topics
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        logger.exception("Full traceback:")
        return None

# Different payload formats to test
payload_formats = [
    # Current format
    {"query": "Get trending topics"},
    
    # OpenAI-like format
    {"model": "grok-2", "messages": [{"role": "user", "content": "Get trending topics"}]},
    
    # Simple prompt format
    {"prompt": "Get trending topics"},
    
    # More complex format
    {
        "model": "grok-2",
        "prompt": "Get trending topics",
        "max_tokens": 1000,
        "temperature": 0.7
    }
]

def check_domain(domain):
    """Check if a domain resolves correctly"""
    try:
        ip = socket.gethostbyname(domain)
        print(f"Domain {domain} resolves to {ip}")
        return True
    except socket.gaierror:
        print(f"Domain {domain} does not resolve")
        return False

# Test domains
check_domain("api.xai.com")
check_domain("api.x.ai")
check_domain("x.ai")

def verify_key_format(key):
    """Check if key follows expected pattern"""
    import re
    # Check if key has expected format (this is a guess based on the key you shared)
    if re.match(r'^xai-[a-zA-Z0-9]{64,}$', key):
        print("Key format appears valid")
    else:
        print("Key format may be incorrect")
    
    # Check key length
    print(f"Key length: {len(key)} characters")

# Verify the key
verify_key_format(GROK_API_KEY)

def raw_request_test(base_url, api_key):
    """Make a request with minimal dependencies"""
    import http.client
    import urllib.parse
    import json
    
    # Parse URL
    parsed = urllib.parse.urlparse(base_url)
    conn = http.client.HTTPSConnection(parsed.netloc, port=443, context=ssl._create_unverified_context())
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Payload
    payload = json.dumps({"query": "Get trending topics"})
    
    # Make request
    path = parsed.path
    print(f"Making raw request to {parsed.netloc}{path}")
    conn.request("POST", path, payload, headers)
    
    # Get response
    response = conn.getresponse()
    data = response.read()
    
    print(f"Status: {response.status} {response.reason}")
    print(f"Headers: {response.getheaders()}")
    print(f"Body: {data.decode('utf-8')}")
    
    conn.close()

# Comment out or remove this line:
# raw_request_test("https://api.x.ai/grok/v1/query", GROK_API_KEY)

def check_example_usage():
    """
    Look up the official API documentation and follow exactly the format shown.
    This is a template - we'll need to fill in the actual example from the docs.
    """
    # Example assumes this is how the docs show it
    import requests
    
    url = "https://api.x.ai/v1/completions"  # Replace with documented URL
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Using exact payload format from docs
    payload = {
        "model": "grok-2",
        "prompt": "Get the top 3 trending news topics right now",
        "max_tokens": 500
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")

# Checking if request validation is the issue
def test_empty_request(url, key):
    """Test if the API requires specific fields"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    # Empty payload to see validation errors
    response = requests.post(url, json={}, headers=headers)
    print(f"Empty request status: {response.status_code}")
    print(f"Response: {response.text}")