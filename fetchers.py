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
from urllib.parse import quote
import os
import sys
import inspect
import asyncio
import aiohttp
import time
from utils import secure_log_key
from dotenv import load_dotenv
try:
    from config_prod import (
        NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, NYT_API_KEY,
        MEDIASTACK_API_KEY, NEWSDATAIO_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
        USE_NEWSAPI_ORG, USE_GUARDIAN, USE_GNEWS, USE_NYT,
        USE_MEDIASTACK, USE_NEWSDATAIO, USE_AYLIEN, USE_NEWSAPI_AI,
        DEFAULT_DAYS_BACK, NEWSAPI_AI_KEY, MAX_ARTICLES_PER_SOURCE,
        DEBUG
    )
except ImportError:
    raise Exception("Could not load production config")

# Add timeout constants at the top after imports
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 2
BACKOFF_FACTOR = 1.5

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_request_timeout_settings():
    """Log the current request timeout settings for diagnostics"""
    logger.info(f"Request timeout settings: TIMEOUT={REQUEST_TIMEOUT}s, MAX_RETRIES={MAX_RETRIES}, BACKOFF_FACTOR={BACKOFF_FACTOR}")

# Create dummy Aylien objects since we can't properly import the package
class AylienError(Exception):
    pass

class DummyClient:
    def __init__(self, *args, **kwargs):
        pass
    def Stories(self, *args, **kwargs):
        logger.error("Aylien API client not available")
        return {'stories': []}

class DummyTextAPI:
    Client = DummyClient

textapi = DummyTextAPI()

# Centralized helper function for fetching with robust error handling, updated to support POST
async def async_fetch_with_error_handling(url, params=None, headers=None, json=None, ssl_verify=None, retry_count=0, max_retries=None, backoff_factor=None):
    """Asynchronous version of fetch_with_error_handling using aiohttp with retry mechanism"""
    # Use global constants if not specified
    max_retries = max_retries if max_retries is not None else MAX_RETRIES
    backoff_factor = backoff_factor if backoff_factor is not None else BACKOFF_FACTOR
    
    method = "GET" if json is None else "POST"
    try:
        logger.debug(f"Making {method} request to {url} (retry {retry_count}/{max_retries})")
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)  # Use global timeout constant
        
        # SSL context for bypassing verification if needed
        ssl_context = None
        if ssl_verify is False:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning(f"SSL verification disabled for {url}")
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if method == "GET":
                async with session.get(url, params=params, headers=headers, ssl=ssl_context) as response:
                    if response.status == 429:  # Rate limited
                        if retry_count < max_retries:
                            retry_delay = backoff_factor ** retry_count
                            logger.warning(f"Rate limited for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            return await async_fetch_with_error_handling(
                                url, params, headers, json, ssl_verify, 
                                retry_count + 1, max_retries, backoff_factor
                            )
                        else:
                            error_msg = f"Rate limit exceeded for {url} after {max_retries} retries"
                            logger.error(error_msg)
                            return None, error_msg
                    elif response.status == 503 or response.status == 502:  # Service unavailable or bad gateway
                        if retry_count < max_retries:
                            retry_delay = backoff_factor ** retry_count
                            logger.warning(f"Service unavailable for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            return await async_fetch_with_error_handling(
                                url, params, headers, json, ssl_verify, 
                                retry_count + 1, max_retries, backoff_factor
                            )
                        else:
                            error_msg = f"Service unavailable for {url} after {max_retries} retries"
                            logger.error(error_msg)
                            return None, error_msg
                    elif response.status != 200:
                        error_msg = f"HTTP error {response.status} for {url}"
                        logger.error(error_msg)
                        return None, error_msg
                    return await response.json(), None
            else:
                async with session.post(url, params=params, headers=headers, json=json, ssl=ssl_context) as response:
                    if response.status == 429:  # Rate limited
                        if retry_count < max_retries:
                            retry_delay = backoff_factor ** retry_count
                            logger.warning(f"Rate limited for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            return await async_fetch_with_error_handling(
                                url, params, headers, json, ssl_verify, 
                                retry_count + 1, max_retries, backoff_factor
                            )
                        else:
                            error_msg = f"Rate limit exceeded for {url} after {max_retries} retries"
                            logger.error(error_msg)
                            return None, error_msg
                    elif response.status == 503 or response.status == 502:  # Service unavailable or bad gateway
                        if retry_count < max_retries:
                            retry_delay = backoff_factor ** retry_count
                            logger.warning(f"Service unavailable for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            return await async_fetch_with_error_handling(
                                url, params, headers, json, ssl_verify, 
                                retry_count + 1, max_retries, backoff_factor
                            )
                        else:
                            error_msg = f"Service unavailable for {url} after {max_retries} retries"
                            logger.error(error_msg)
                            return None, error_msg
                    elif response.status != 200:
                        error_msg = f"HTTP error {response.status} for {url}"
                        logger.error(error_msg)
                        return None, error_msg
                    return await response.json(), None
    except aiohttp.ClientError as e:
        error_msg = f"{method} request error for {url}: {e}"
        logger.error(error_msg)
        # If we got an SSL error and haven't tried disabling verification yet, retry with verification disabled
        if "SSL" in str(e) and ssl_verify is None:
            logger.warning(f"SSL error encountered for {url}, retrying with verification disabled")
            return await async_fetch_with_error_handling(url, params, headers, json, ssl_verify=False)
        # For connection errors, retry with backoff if we haven't exceeded max retries
        if retry_count < max_retries and isinstance(e, (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError)):
            retry_delay = backoff_factor ** retry_count
            logger.warning(f"Connection error for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
            await asyncio.sleep(retry_delay)
            return await async_fetch_with_error_handling(
                url, params, headers, json, ssl_verify, 
                retry_count + 1, max_retries, backoff_factor
            )
        return None, error_msg
    except asyncio.TimeoutError:
        error_msg = f"{method} request timeout for {url}"
        logger.error(error_msg)
        # Retry timeouts with backoff if we haven't exceeded max retries
        if retry_count < max_retries:
            retry_delay = backoff_factor ** retry_count
            logger.warning(f"Timeout for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{max_retries})")
            await asyncio.sleep(retry_delay)
            return await async_fetch_with_error_handling(
                url, params, headers, json, ssl_verify, 
                retry_count + 1, max_retries, backoff_factor
            )
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected {method} error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg

def fetch_with_error_handling(url, params=None, headers=None, json=None, retry_count=0):
    """Synchronous HTTP request with error handling and retries"""
    try:
        method = "POST" if json else "GET"
        logger.debug(f"Making {method} request to {url} (retry {retry_count}/{MAX_RETRIES})")
        
        response = requests.request(
            method, 
            url, 
            params=params, 
            headers=headers, 
            json=json, 
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        data = response.json()  # Parse JSON response
        logger.debug(f"Successfully fetched from {url}, status: {response.status_code}")
        return data, None
    except requests.exceptions.Timeout as e:
        error_msg = f"{method} Timeout error for {url}: {e}"
        logger.error(error_msg)
        # Retry timeouts with backoff if we haven't exceeded max retries
        if retry_count < MAX_RETRIES:
            retry_delay = BACKOFF_FACTOR ** retry_count
            logger.warning(f"Timeout for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{MAX_RETRIES})")
            time.sleep(retry_delay)
            return fetch_with_error_handling(url, params, headers, json, retry_count + 1)
        return None, error_msg
    except requests.exceptions.TooManyRedirects as e:
        error_msg = f"{method} Too many redirects for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"{method} Request exception for {url}: {e}"
        logger.error(error_msg)
        # Retry connection errors with backoff if we haven't exceeded max retries
        if retry_count < MAX_RETRIES and isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.SSLError)):
            retry_delay = BACKOFF_FACTOR ** retry_count
            logger.warning(f"Connection error for {url}, retrying after {retry_delay:.2f}s (retry {retry_count+1}/{MAX_RETRIES})")
            time.sleep(retry_delay)
            return fetch_with_error_handling(url, params, headers, json, retry_count + 1)
        return None, error_msg
    except json.decoder.JSONDecodeError as e:
        error_msg = f"JSON decoding error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected {method} error for {url}: {e}"
        logger.error(error_msg)
        return None, error_msg

# High-quality source lists for diversity
HIGH_QUALITY_SOURCES = {
    "us_mainstream": "cnn,the-washington-post,the-wall-street-journal,usa-today,associated-press,reuters,bloomberg",
    "us_diverse": "fox-news,the-american-conservative,national-review,the-huffington-post,vice-news,the-hill",
    "international": "bbc-news,al-jazeera-english,the-guardian,the-globe-and-mail,der-spiegel,le-monde",
    "tech": "wired,techcrunch,ars-technica,the-verge,engadget",
    "business": "financial-times,business-insider,fortune,the-economist",
    "science": "national-geographic,scientific-american,new-scientist"
}

# Define tiers of news sources for quality scoring
TIER1_SOURCES = {
    "associated-press", "reuters", "bbc-news", "the-washington-post", 
    "the-new-york-times", "the-wall-street-journal", "the-economist",
    "bloomberg", "financial-times", "the-guardian"
}

TIER2_SOURCES = {
    "al-jazeera-english", "cnn", "usa-today", "politico", "the-hill",
    "fox-news", "nbc-news", "abc-news", "cbs-news", "time",
    "der-spiegel", "le-monde"
}

def score_article_quality(article):
    """
    Score article quality based on multiple factors.
    
    Args:
        article (dict): The article to score
        
    Returns:
        int: Quality score (higher is better)
    """
    score = 0
    
    # Favor longer, more substantive articles
    content_length = len(article.get("content", "") or article.get("description", ""))
    if content_length > 2000:
        score += 3
    elif content_length > 1000:
        score += 2
    elif content_length > 500:
        score += 1
    
    # Favor articles with images
    if article.get("urlToImage"):
        score += 1
    
    # Favor articles from known high-quality sources
    source_name = article.get("source", {}).get("name", "").lower()
    if source_name in TIER1_SOURCES:
        score += 3
    elif source_name in TIER2_SOURCES:
        score += 2
    
    # Favor articles that mention the query in the title
    title = article.get("title", "").lower()
    description = article.get("description", "").lower()
    
    query_terms = article.get("_query", "").lower().split()
    main_terms = [term for term in query_terms if len(term) > 3]  # Skip short words
    
    for term in main_terms:
        if term in title:
            score += 2
        elif term in description:
            score += 1
    
    # Penalize for very short titles (often clickbait)
    if len(title) < 30:
        score -= 1
    
    return score

# Original fetch_newsapi_org function remains for backward compatibility 
# but we'll add a new enhanced function

async def async_fetch_newsapi_org_diversified(event, days_back=7, intl_ratio=0.2, quality_ratio=0.8):
    """Async wrapper for fetch_newsapi_org_diversified"""
    try:
        return fetch_newsapi_org_diversified(event, days_back, intl_ratio, quality_ratio)
    except Exception as e:
        logger.error(f"Error in async_fetch_newsapi_org_diversified: {e}")
        return []

def fetch_newsapi_org_diversified(event, days_back=7, intl_ratio=0.2, quality_ratio=0.8):
    """
    Enhanced version of fetch_newsapi_org that makes multiple requests to different source groups
    to ensure article quality and source diversity.
    
    Args:
        event (str): The search query
        days_back (int): Number of days back to search
        intl_ratio (float): Ratio of international to US sources (0.0 to 1.0)
        quality_ratio (float): Ratio of high-quality to standard sources (0.0 to 1.0)
    
    Returns:
        list: List of articles from diverse sources
    """
    if not NEWSAPI_ORG_KEY:
        logger.warning("NewsAPI.org API key not found")
        return []
    
    logger.info(f"Making diversified requests to NewsAPI.org for '{event}' (intl_ratio={intl_ratio}, quality_ratio={quality_ratio})")
    
    # Define the API URL
    url = "https://newsapi.org/v2/everything"
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    # Implement query expansion for topics with limited results
    expanded_queries = [event]
    
    # Define keywords that might benefit from query expansion
    limited_result_topics = {
        "wheat": ["grain", "agriculture", "farming", "crop"],
        "food": ["agriculture", "nutrition", "grocery", "supply chain"],
        "prices": ["inflation", "costs", "market", "economy"],
        "agriculture": ["farming", "crops", "production"],
        "commodity": ["trading", "market", "prices", "futures"]
    }
    
    # Check if current query contains any keywords needing expansion
    query_terms = event.lower().split()
    expansion_needed = False
    for term in query_terms:
        if term in limited_result_topics:
            expansion_needed = True
            break
    
    if expansion_needed:
        # Create expanded queries by adding related terms
        for term in query_terms:
            if term in limited_result_topics:
                for related_term in limited_result_topics[term][:2]:  # Take up to 2 related terms
                    expanded_query = f"{event} {related_term}"
                    if expanded_query not in expanded_queries:
                        expanded_queries.append(expanded_query)
        
        logger.info(f"Query expansion for '{event}': {expanded_queries}")
    
    # Calculate the distribution for mainstream, diverse and international sources
    total_articles = 50  # Total target
    mainstream_articles = int(total_articles * 0.4 * (1 - intl_ratio))  # 40% mainstream US 
    diverse_articles = int(total_articles * 0.4 * (1 - intl_ratio))     # 40% diverse US
    international_articles = int(total_articles * intl_ratio)           # 20% international
    
    # Ensure we have at least some articles from each category
    mainstream_articles = max(1, mainstream_articles)
    diverse_articles = max(1, diverse_articles)
    international_articles = max(1, international_articles)
    
    logger.info(f"Article distribution: Mainstream={mainstream_articles}, Diverse={diverse_articles}, International={international_articles}")
    
    # Define parameters for three requests
    # 1. US mainstream sources
    mainstream_params = {
        "q": event,
        "apiKey": NEWSAPI_ORG_KEY,
        "language": "en",
        "from": from_date,
        "pageSize": mainstream_articles,
        "sortBy": "relevancy",
        "sources": ",".join([
            "cnn", "the-washington-post", "the-wall-street-journal", 
            "bloomberg", "associated-press", "reuters", "politico",
            "usa-today", "abc-news", "nbc-news", "cbs-news"
        ])
    }
    
    # 2. US diverse sources
    diverse_params = {
        "q": event,
        "apiKey": NEWSAPI_ORG_KEY,
        "language": "en",
        "from": from_date,
        "pageSize": diverse_articles,
        "sortBy": "relevancy",
        "sources": ",".join([
            "fox-news", "the-american-conservative", "breitbart-news",
            "national-review", "the-hill", "newsweek", "time",
            "vice-news", "the-verge", "wired", "techcrunch", 
            "ars-technica", "business-insider", "fortune"
        ])
    }
    
    # 3. International sources
    international_params = {
        "q": event,
        "apiKey": NEWSAPI_ORG_KEY,
        "from": from_date,
        "pageSize": international_articles,
        "sortBy": "relevancy",
        "sources": ",".join([
            "bbc-news", "al-jazeera-english", "the-hindu",
            "the-times-of-india", "the-globe-and-mail", "the-irish-times",
            "independent", "australian-financial-review"
        ])
    }
    
    # Execute the requests and collect articles
    all_articles = []
    
    # First try with the original query
    logger.info(f"NewsAPI.org diversified request #1: sources={mainstream_params['sources'][:35]}... pageSize={mainstream_params['pageSize']}")
    data, error = fetch_with_error_handling(url, params=mainstream_params)
    mainstream_articles_resp = data.get('articles', []) if not error and data.get('status') != 'error' else []
    logger.info(f"NewsAPI.org: Fetched {len(mainstream_articles_resp)} articles in request #1")
    all_articles.extend(mainstream_articles_resp)
    
    logger.info(f"NewsAPI.org diversified request #2: sources={diverse_params['sources'][:35]}... pageSize={diverse_params['pageSize']}")
    data, error = fetch_with_error_handling(url, params=diverse_params)
    diverse_articles_resp = data.get('articles', []) if not error and data.get('status') != 'error' else []
    logger.info(f"NewsAPI.org: Fetched {len(diverse_articles_resp)} articles in request #2")
    all_articles.extend(diverse_articles_resp)
    
    logger.info(f"NewsAPI.org diversified request #3: sources={international_params['sources'][:35]}... pageSize={international_params['pageSize']}")
    data, error = fetch_with_error_handling(url, params=international_params)
    international_articles_resp = data.get('articles', []) if not error and data.get('status') != 'error' else []
    logger.info(f"NewsAPI.org: Fetched {len(international_articles_resp)} articles in request #3")
    all_articles.extend(international_articles_resp)
    
    # If we have few articles and query expansion is enabled, try expanded queries
    if len(all_articles) < 5 and len(expanded_queries) > 1:
        logger.info(f"Initial query returned only {len(all_articles)} articles, trying expanded queries")
        
        for expanded_query in expanded_queries[1:]:  # Skip the original query
            # Update the query for each parameter set
            mainstream_params["q"] = expanded_query
            diverse_params["q"] = expanded_query
            international_params["q"] = expanded_query
            
            # Make additional requests with expanded queries
            logger.info(f"NewsAPI.org expanded request with '{expanded_query}' to mainstream sources")
            data, error = fetch_with_error_handling(url, params=mainstream_params)
            expanded_mainstream = data.get('articles', []) if not error and data.get('status') != 'error' else []
            logger.info(f"NewsAPI.org: Fetched {len(expanded_mainstream)} articles with expanded query")
            all_articles.extend(expanded_mainstream)
            
            logger.info(f"NewsAPI.org expanded request with '{expanded_query}' to diverse sources")
            data, error = fetch_with_error_handling(url, params=diverse_params)
            expanded_diverse = data.get('articles', []) if not error and data.get('status') != 'error' else []
            logger.info(f"NewsAPI.org: Fetched {len(expanded_diverse)} articles with expanded query")
            all_articles.extend(expanded_diverse)
            
            logger.info(f"NewsAPI.org expanded request with '{expanded_query}' to international sources")
            data, error = fetch_with_error_handling(url, params=international_params)
            expanded_international = data.get('articles', []) if not error and data.get('status') != 'error' else []
            logger.info(f"NewsAPI.org: Fetched {len(expanded_international)} articles with expanded query")
            all_articles.extend(expanded_international)
            
            # If we have enough articles, stop making additional requests
            if len(all_articles) >= 15:
                logger.info(f"Collected sufficient articles ({len(all_articles)}) with expanded queries")
                break
    
    logger.info(f"NewsAPI.org: Total articles fetched across all diversified requests: {len(all_articles)}")
    
    # If requested quality ratio is less than 1.0, add some standard articles 
    if quality_ratio < 1.0 and quality_ratio > 0:
        # Calculate how many standard articles to add
        high_quality_count = len(all_articles)
        target_high_quality_ratio = quality_ratio
        target_high_quality_count = int(high_quality_count / target_high_quality_ratio)
        standard_articles_needed = target_high_quality_count - high_quality_count
        
        if standard_articles_needed > 0:
            logger.info(f"Adding {standard_articles_needed} standard articles to maintain quality ratio of {quality_ratio}")
            # Make a general request for standard articles
            standard_params = {
                "q": event,
                "apiKey": NEWSAPI_ORG_KEY,
                "language": "en",
                "from": from_date,
                "pageSize": standard_articles_needed,
                "sortBy": "relevancy",
            }
            
            data, error = fetch_with_error_handling(url, params=standard_params)
            standard_articles = data.get('articles', []) if not error and data.get('status') != 'error' else []
            logger.info(f"Added {len(standard_articles)} standard articles")
            all_articles.extend(standard_articles)
    
    # Remove duplicates based on URL
    unique_urls = set()
    unique_articles = []
    
    for article in all_articles:
        url = article.get("url")
        if url and url not in unique_urls:
            unique_urls.add(url)
            unique_articles.append(article)
    
    duplicates_removed = len(all_articles) - len(unique_articles)
    logger.info(f"NewsAPI.org: {duplicates_removed} duplicates removed")
    
    # Score articles for quality and sort
    scored_articles = []
    for article in unique_articles:
        score = score_article_quality(article)
        article["quality_score"] = score
        scored_articles.append(article)
    
    # Sort by quality score
    scored_articles.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    
    # Log article quality scores
    if scored_articles:
        min_score = min(a.get("quality_score", 0) for a in scored_articles)
        max_score = max(a.get("quality_score", 0) for a in scored_articles)
        avg_score = sum(a.get("quality_score", 0) for a in scored_articles) / len(scored_articles)
        logger.info(f"Article quality scores - Min: {min_score}, Max: {max_score}, Avg: {avg_score:.1f}")
        
        # Log top articles by score
        for i, article in enumerate(scored_articles[:3]):
            title = article.get("title", "")[:40] + "..."
            score = article.get("quality_score", 0)
            source = article.get("source", {}).get("name", "Unknown")
            logger.info(f"Top {i+1}: [{score}] {title} ({source})")
    
    return scored_articles

async def async_fetch_newsapi_org(event, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_newsapi_org"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    url = "https://newsapi.org/v2/everything"
    # Using a hard limit of 30 articles instead of MAX_ARTICLES_PER_SOURCE to control costs
    hardlimit = 30
    params = {
        "q": event,
        "from": from_date,
        "pageSize": hardlimit,
        "sortBy": "relevancy",  # Sort by relevance to get the most relevant articles
        "apiKey": NEWSAPI_ORG_KEY
    }
    logger.info(f"NewsAPI.org: Requesting {params['pageSize']} articles for event '{event}' (hard limit applied)")
    data, error = await async_fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get("status") == "error":
        logger.error(f"NewsAPI.org API error: {data.get('message')}")
        return []
    articles = data.get('articles', [])
    logger.info(f"NewsAPI.org: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    logger.info(f"NewsAPI.org: Total results available: {data.get('totalResults', 0)}")
    return articles

def fetch_newsapi_org(event, days_back=DEFAULT_DAYS_BACK):
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    url = "https://newsapi.org/v2/everything"
    # Using a hard limit of 30 articles instead of MAX_ARTICLES_PER_SOURCE to control costs
    hardlimit = 30
    params = {
        "q": event,
        "from": from_date,
        "pageSize": hardlimit,
        "sortBy": "relevancy",  # Sort by relevance to get the most relevant articles
        "apiKey": NEWSAPI_ORG_KEY
    }
    logger.info(f"NewsAPI.org: Requesting {params['pageSize']} articles for event '{event}' (hard limit applied)")
    data, error = fetch_with_error_handling(url, params=params)
    if error:
        return []
    if data.get("status") == "error":
        logger.error(f"NewsAPI.org API error: {data.get('message')}")
        return []
    articles = data.get('articles', [])
    logger.info(f"NewsAPI.org: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    logger.info(f"NewsAPI.org: Total results available: {data.get('totalResults', 0)}")
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

async def async_fetch_guardian(event, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_guardian"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://content.guardianapis.com/search"
    params = {
        "q": event,
        "from-date": from_date,
        "page-size": MAX_ARTICLES_PER_SOURCE,
        "api-key": GUARDIAN_API_KEY
    }
    data, error = await async_fetch_with_error_handling(url, params=params)
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

async def async_fetch_aylien_articles(event, app_id=AYLIEN_APP_ID, api_key=AYLIEN_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_aylien_articles - Note: The Aylien API client doesn't support async,
    so we'll run it in a separate thread with asyncio.to_thread (requires Python 3.9+)"""
    from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
    
    # This function will be executed in a separate thread
    def _fetch_aylien():
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
    
    # Run the function in a thread pool
    return await asyncio.to_thread(_fetch_aylien)

async def async_fetch_gnews_articles(event, api_key=GNEWS_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_gnews_articles"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": event,
        "from": from_date,
        "token": api_key,
        "max": MAX_ARTICLES_PER_SOURCE
    }
    data, error = await async_fetch_with_error_handling(url, params=params)
    if error:
        return []
    articles = data.get('articles', [])
    logger.info(f"GNews: Fetched {len(articles)} articles for event '{event}' from {from_date}")
    return articles

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

async def async_fetch_nyt_articles(event, api_key=NYT_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_nyt_articles"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')  # NYT uses YYYYMMDD format
    url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    params = {
        "q": event,
        "api-key": api_key,
        "begin_date": from_date,
        "page-size": MAX_ARTICLES_PER_SOURCE
    }
    data, error = await async_fetch_with_error_handling(url, params=params)
    if error:
        return []
    articles = data.get('response', {}).get('docs', [])
    logger.info(f"NYT: Fetched {len(articles)} articles for event '{event}' from {from_date}")
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

async def async_fetch_mediastack_articles(event, api_key=MEDIASTACK_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_mediastack_articles"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": api_key,
        "keywords": event,
        "date": f"{from_date},{datetime.now().strftime('%Y-%m-%d')}",
        "limit": MAX_ARTICLES_PER_SOURCE
    }
    data, error = await async_fetch_with_error_handling(url, params=params)
    if error:
        return []
    articles = data.get('data', [])
    logger.info(f"Mediastack: Fetched {len(articles)} articles for event '{event}' from {from_date}")
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

async def async_fetch_newsapi_ai_articles(event, api_key=NEWSAPI_AI_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_newsapi_ai_articles"""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = "https://eventregistry.org/api/v1/article/getArticles"
    payload = {
        "action": "getArticles",
        "keyword": event,
        "dateStart": from_date,
        "dateEnd": datetime.now().strftime('%Y-%m-%d'),
        "articlesCount": MAX_ARTICLES_PER_SOURCE,
        "resultType": "articles",
        "apiKey": api_key,
        "lang": "eng"
    }
    data, error = await async_fetch_with_error_handling(url, json=payload)
    if error:
        return []
    articles = data.get('articles', {}).get('results', [])
    logger.info(f"NewsAPI.ai: Fetched {len(articles)} articles for event '{event}' from {from_date}")
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
    max_topics = min(max(1, max_topics), 8)
    logger.info("Bypassing Grok API, returning fallback topics directly")
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
        fetch_newsapi_org_diversified,
        fetch_mediastack_articles,
        fetch_gnews_articles,
        fetch_nyt_articles,
        fetch_aylien_articles,
        fetch_newsapi_ai_articles,
        fetch_newsdata_io_articles,
        fetch_guardian
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

async def async_fetch_newsdata_io_articles(event, api_key=NEWSDATAIO_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Async version of fetch_newsdata_io_articles to get articles from NewsData.io"""
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": api_key,
        "q": event,
        "language": "en",
        "size": MAX_ARTICLES_PER_SOURCE  # Number of articles to return
    }
    
    logger.info(f"NewsData.io: Making async request for event '{event}'")
    data, error = await async_fetch_with_error_handling(url, params=params)
    
    if error:
        logger.error(f"NewsData.io: Error fetching articles: {error}")
        return []
        
    if data.get('status') != "success":
        logger.error(f"NewsData.io API error: {data.get('results', {}).get('message', 'Unknown error')}")
        return []
        
    articles = data.get('results', [])
    logger.info(f"NewsData.io: Fetched {len(articles)} articles for event '{event}'")
    
    # Transform NewsData.io format to our standard format
    standardized_articles = []
    for article in articles:
        source_name = article.get("source_name", article.get("source_id", ""))
        
        standardized_article = {
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "content": article.get("content", ""),
            "url": article.get("link", ""),
            "urlToImage": article.get("image_url", ""),
            "publishedAt": article.get("pubDate", ""),
            "source": {
                "id": article.get("source_id", ""),
                "name": source_name
            },
            "keywords": article.get("keywords", []),
            "creator": article.get("creator", []),
            "video_url": article.get("video_url", ""),
            "full_description": article.get("description", ""),
            "_query": event,
            "provider": "NewsData.io"  # Add a provider field to indicate it came from NewsData.io
        }
        standardized_articles.append(standardized_article)
    
    return standardized_articles

def fetch_newsdata_io_articles(event, api_key=NEWSDATAIO_API_KEY, days_back=DEFAULT_DAYS_BACK):
    """Fetches articles from NewsData.io API"""
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": api_key,
        "q": event,
        "language": "en",
        "size": MAX_ARTICLES_PER_SOURCE  # Number of articles to return
    }
    
    logger.info(f"NewsData.io: Making request for event '{event}'")
    data, error = fetch_with_error_handling(url, params=params)
    
    if error:
        logger.error(f"NewsData.io: Error fetching articles: {error}")
        return []
        
    if data.get('status') != "success":
        logger.error(f"NewsData.io API error: {data.get('results', {}).get('message', 'Unknown error')}")
        return []
        
    articles = data.get('results', [])
    logger.info(f"NewsData.io: Fetched {len(articles)} articles for event '{event}'")
    
    # Transform NewsData.io format to our standard format
    standardized_articles = []
    for article in articles:
        source_name = article.get("source_name", article.get("source_id", ""))
        
        standardized_article = {
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "content": article.get("content", ""),
            "url": article.get("link", ""),
            "urlToImage": article.get("image_url", ""),
            "publishedAt": article.get("pubDate", ""),
            "source": {
                "id": article.get("source_id", ""),
                "name": source_name
            },
            "keywords": article.get("keywords", []),
            "creator": article.get("creator", []),
            "video_url": article.get("video_url", ""),
            "full_description": article.get("description", ""),
            "_query": event,
            "provider": "NewsData.io"  # Add a provider field to indicate it came from NewsData.io
        }
        standardized_articles.append(standardized_article)
    
    return standardized_articles

async def async_fetch_articles(event, days_back=DEFAULT_DAYS_BACK, min_articles=15):
    """
    Asynchronously fetch articles from multiple sources using asyncio with priority-based fetching.
    Groups APIs into tiers based on speed and reliability, starts all fetches concurrently,
    but processes results in priority order for faster response times.
    """
    logger.info(f"Starting priority-based parallel fetching for '{event}'")
    # Log the current timeout settings
    log_request_timeout_settings()
    
    # Define API tiers based on typical speed/reliability
    tier1_apis = [
        (async_fetch_newsapi_org_diversified, "NewsAPI.org (Diversified)", USE_NEWSAPI_ORG),
        (async_fetch_mediastack_articles, "Mediastack", USE_MEDIASTACK)
    ]
    
    tier2_apis = [
        (async_fetch_gnews_articles, "GNews", USE_GNEWS),
        (async_fetch_nyt_articles, "NYT", USE_NYT)
    ]
    
    tier3_apis = [
        (async_fetch_aylien_articles, "Aylien", USE_AYLIEN),
        (async_fetch_newsapi_ai_articles, "NewsAPI.ai", USE_NEWSAPI_AI),
        (async_fetch_newsdata_io_articles, "NewsData.io", USE_NEWSDATAIO),
        (async_fetch_guardian, "Guardian", USE_GUARDIAN)
    ]
    
    # Initialize results array with empty lists for each API
    all_results = [[] for _ in range(8)]  # Updated to 8 APIs total with NewsData.io
    api_names = []
    api_tasks = {}
    
    # Track indices for mapping task results back to the correct position
    api_indices = {}
    current_index = 0
    
    # Start all fetch operations concurrently
    for tier in [tier1_apis, tier2_apis, tier3_apis]:
        for func, name, enabled in tier:
            if enabled:
                logger.info(f"Creating task for {name}")
                task = asyncio.create_task(func(event, days_back=days_back))
                api_tasks[task] = (name, current_index)
                api_indices[name] = current_index
                api_names.append(name)
                current_index += 1
    
    if not api_tasks:
        logger.warning("No news sources are enabled. Check your configuration.")
        return [], [], [], [], [], [], [], []
    
    # Process tiers in priority order
    successful_sources = []
    failed_sources = []
    total_articles = 0
    
    try:
        # Process Tier 1 APIs first (fastest/most reliable)
        tier1_names = [name for _, name, _ in tier1_apis if name in api_names]
        if tier1_names:
            logger.info(f"Awaiting Tier 1 APIs: {', '.join(tier1_names)}")
            tier1_tasks = [task for task, (name, _) in api_tasks.items() if name in tier1_names]
            tier1_results = await asyncio.gather(*tier1_tasks, return_exceptions=True)
            
            # Process Tier 1 results
            for task, result in zip(tier1_tasks, tier1_results):
                name, index = api_tasks[task]
                
                if isinstance(result, Exception):
                    logger.error(f"Error in {name} fetcher: {result}")
                    failed_sources.append(name)
                    all_results[index] = []
                else:
                    all_results[index] = result
                    if not result:  # Empty result list
                        logger.warning(f"No articles found from {name} for '{event}'")
                        failed_sources.append(name)
                    else:
                        logger.info(f"{name}: Fetched {len(result)} articles for '{event}'")
                        successful_sources.append(name)
                        total_articles += len(result)
            
            # Early return if we have enough articles from Tier 1
            if total_articles >= min_articles:
                logger.info(f"Early return with {total_articles} articles from Tier 1 sources")
                # Cancel remaining tasks
                for task in list(api_tasks.keys()):
                    if task not in tier1_tasks and not task.done():
                        task.cancel()
                        logger.info(f"Cancelled task for {api_tasks[task][0]} due to early return")
                
                return tuple(all_results)
        
        # Process Tier 2 APIs next
        tier2_names = [name for _, name, _ in tier2_apis if name in api_names]
        if tier2_names:
            logger.info(f"Awaiting Tier 2 APIs: {', '.join(tier2_names)}")
            tier2_tasks = [task for task, (name, _) in api_tasks.items() if name in tier2_names]
            tier2_results = await asyncio.gather(*tier2_tasks, return_exceptions=True)
            
            # Process Tier 2 results
            for task, result in zip(tier2_tasks, tier2_results):
                name, index = api_tasks[task]
                
                if isinstance(result, Exception):
                    logger.error(f"Error in {name} fetcher: {result}")
                    failed_sources.append(name)
                    all_results[index] = []
                else:
                    all_results[index] = result
                    if not result:  # Empty result list
                        logger.warning(f"No articles found from {name} for '{event}'")
                        failed_sources.append(name)
                    else:
                        logger.info(f"{name}: Fetched {len(result)} articles for '{event}'")
                        successful_sources.append(name)
                        total_articles += len(result)
            
            # Early return if we have enough articles from Tiers 1-2
            if total_articles >= min_articles:
                logger.info(f"Early return with {total_articles} articles from Tier 1-2 sources")
                # Cancel remaining tasks
                for task in list(api_tasks.keys()):
                    if task not in tier1_tasks and task not in tier2_tasks and not task.done():
                        task.cancel()
                        logger.info(f"Cancelled task for {api_tasks[task][0]} due to early return")
                
                return tuple(all_results)
        
        # Process Tier 3 APIs last (slowest/least reliable)
        tier3_names = [name for _, name, _ in tier3_apis if name in api_names]
        if tier3_names:
            logger.info(f"Awaiting Tier 3 APIs: {', '.join(tier3_names)}")
            tier3_tasks = [task for task, (name, _) in api_tasks.items() if name in tier3_names]
            tier3_results = await asyncio.gather(*tier3_tasks, return_exceptions=True)
            
            # Process Tier 3 results
            for task, result in zip(tier3_tasks, tier3_results):
                name, index = api_tasks[task]
                
                if isinstance(result, Exception):
                    logger.error(f"Error in {name} fetcher: {result}")
                    failed_sources.append(name)
                    all_results[index] = []
                else:
                    all_results[index] = result
                    if not result:  # Empty result list
                        logger.warning(f"No articles found from {name} for '{event}'")
                        failed_sources.append(name)
                    else:
                        logger.info(f"{name}: Fetched {len(result)} articles for '{event}'")
                        successful_sources.append(name)
                        total_articles += len(result)
        
        success_rate = len(successful_sources) / len(api_names) if api_names else 0
        logger.info(f"Priority-based parallel fetching complete for '{event}' - Success rate: {success_rate:.2%}")
        logger.info(f"Total articles fetched: {total_articles}")
        
        if successful_sources:
            logger.info(f"Successful sources ({len(successful_sources)}): {', '.join(successful_sources)}")
        if failed_sources:
            logger.warning(f"Failed sources ({len(failed_sources)}): {', '.join(failed_sources)}")
        
        # Check if we have at least some minimum success rate
        if success_rate < 0.3 and len(api_names) > 2:
            logger.error(f"Critical failure rate in news fetching for '{event}' - Only {len(successful_sources)}/{len(api_names)} sources succeeded")
            
        return tuple(all_results)
        
    except Exception as e:
        logger.error(f"Error in priority-based parallel fetching: {e}")
        # Return empty lists for all fetchers
        return [], [], [], [], [], [], [], []

def fetch_articles(event, days_back=DEFAULT_DAYS_BACK):
    """
    Fetch articles from all configured APIs for a given event.
    
    Args:
        event (str): The event or query to search for.
        days_back (int): Time window in days (default from config).
    
    Returns:
        list: Combined list of articles from all sources.
    """
    # Log the current timeout settings
    log_request_timeout_settings()
    
    try:
        # Define functions with their proper API keys and feature flags
        fetch_functions = [
            (lambda e, d: fetch_newsapi_org_diversified(e, d), USE_NEWSAPI_ORG),
            (lambda e, d: fetch_mediastack_articles(e, MEDIASTACK_API_KEY, d), USE_MEDIASTACK),
            (lambda e, d: fetch_gnews_articles(e, GNEWS_API_KEY, d), USE_GNEWS),
            (lambda e, d: fetch_nyt_articles(e, NYT_API_KEY, d), USE_NYT),
            (lambda e, d: fetch_aylien_articles(e, AYLIEN_APP_ID, AYLIEN_API_KEY, d), USE_AYLIEN),
            (lambda e, d: fetch_newsapi_ai_articles(e, NEWSAPI_AI_KEY, d), USE_NEWSAPI_AI),
            (lambda e, d: fetch_newsdata_io_articles(e, NEWSDATAIO_API_KEY, d), USE_NEWSDATAIO),
            (lambda e, d: fetch_guardian(e, d), USE_GUARDIAN)
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
    """Check if domain exists and get its IP address"""
    try:
        ip_address = socket.gethostbyname(domain)
        logger.info(f"Domain {domain} resolves to {ip_address}")
        return ip_address
    except socket.gaierror:
        logger.error(f"Domain {domain} could not be resolved")
        return None

# Test domains
check_domain("api.xai.com")
check_domain("api.x.ai")
check_domain("x.ai")

def verify_key_format(key):
    """Check if key follows expected pattern and log securely"""
    import re
    # Check if key has expected format
    if re.match(r'^xai-[a-zA-Z0-9]{64,}$', key):
        logger.info("Key format appears valid")
    else:
        logger.info("Key format may be incorrect")
    
    # No need to log key length as it could provide partial information about the key
    
    # Log securely with no visible characters
    masked_key = secure_log_key(key, visible_chars=0)
    logger.debug("Key format check complete")

# Verify the key removed as it's no longer needed