# routes.py
# This file defines the web routes for the application using a Flask Blueprint named 'routes'.
# It handles HTTP requests: '/' for the main page (GET/POST) displaying trending topics and custom searches,
# '/data' for AJAX news fetching (POST), and '/test' for a simple status check (GET).
# The core function 'fetch_and_process_data' fetches articles from multiple APIs in parallel, processes them,
# and generates summaries, with detailed timing logs for performance tracking.
# New feature: Retrieves dynamic hot topics for the main page using trends.py.

from flask import Blueprint, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from fetchers import (fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
                     fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
                     fetch_newsapi_ai_articles)
from processors import (process_articles, remove_duplicates, filter_relevant_articles,
                       summarize_articles, ModelManager)
from trends import get_trending_topics  # Absolute import for Render compatibility
from config_prod import (MAX_ARTICLES_PER_SOURCE, cache, NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, 
                        GNEWS_API_KEY, NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
                        NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY, DEFAULT_TOP_N)
import os
from datetime import datetime

routes = Blueprint('routes', __name__)
logger = logging.getLogger(__name__)

_is_first_request = True

@routes.before_app_request
def before_first_request():
    global _is_first_request
    if _is_first_request:
        # Your initialization code here (unchanged from original)
        _is_first_request = False

# Completely remove caching for the search function to fix the issue
# @cache.cached(timeout=3600, key_prefix=lambda: f"summary_{request.form.get('event', 'default')}")
def fetch_and_process_data(event):
    """Fetch data from multiple APIs, process it, and return articles and a summary."""
    start_time = time.time()
    logger.info(f"UNCACHED: Starting fetch_and_process_data for event '{event}', total start time: {start_time}")
    
    # Special logging for Elections-related topics
    if 'election' in event.lower():
        logger.info(f"ELECTIONS TOPIC DETECTED in search: '{event}'")
    
    # Log API key availability for debugging
    logger.info(f"[Debug] API Keys for '{event}' search:")
    logger.info(f"NEWSAPI_ORG_KEY: {'Available' if NEWSAPI_ORG_KEY else 'Missing'}")
    logger.info(f"GUARDIAN_API_KEY: {'Available' if GUARDIAN_API_KEY else 'Missing'}")
    logger.info(f"GNEWS_API_KEY: {'Available' if GNEWS_API_KEY else 'Missing'}")
    logger.info(f"NYT_API_KEY: {'Available' if NYT_API_KEY else 'Missing'}")
    logger.info(f"OPENAI_API_KEY: {'Available' if OPENAI_API_KEY else 'Missing'}")
    logger.info(f"MEDIASTACK_API_KEY: {'Available' if MEDIASTACK_API_KEY else 'Missing'}")
    logger.info(f"NEWSDATA_API_KEY: {'Available' if NEWSDATA_API_KEY else 'Missing'}")
    logger.info(f"AYLIEN keys: {'Available' if AYLIEN_APP_ID and AYLIEN_API_KEY else 'Missing'}")
    
    try:
        # Fetch articles from multiple APIs in parallel
        fetch_start = time.time()
        logger.info(f"Beginning API fetch for event '{event}' at {fetch_start}")
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = [
                executor.submit(fetch_newsapi_org, event),
                executor.submit(fetch_guardian, event),
                executor.submit(fetch_aylien_articles, event),
                executor.submit(fetch_gnews_articles, event),
                executor.submit(fetch_nyt_articles, event),
                executor.submit(fetch_mediastack_articles, event),
                executor.submit(fetch_newsapi_ai_articles, event)
            ]
            results = [future.result() for future in futures]
        newsapi_org_articles, guardian_articles, aylien_articles, gnews_articles, nyt_articles, mediastack_articles, newsapi_ai_articles = results
        fetch_time = time.time() - fetch_start
        logger.info(f"API Fetching took {fetch_time:.2f} seconds for event '{event}'")

        # Log the number of articles retrieved per API
        logger.info(f"Articles retrieved for event '{event}': "
                   f"NewsAPI.org: {len(newsapi_org_articles)}, "
                   f"Guardian: {len(guardian_articles)}, "
                   f"Aylien: {len(aylien_articles)}, "
                   f"GNews: {len(gnews_articles)}, "
                   f"NYT: {len(nyt_articles)}, "
                   f"Mediastack: {len(mediastack_articles)}, "
                   f"NewsAPI.ai: {len(newsapi_ai_articles)}")

        # Check for partial API failures
        total_fetched = (len(newsapi_org_articles) + len(guardian_articles) + 
                        len(aylien_articles) + len(gnews_articles) +
                        len(nyt_articles) + len(mediastack_articles) + 
                        len(newsapi_ai_articles))
        logger.info(f"Total articles fetched for event '{event}': {total_fetched}")
        if total_fetched == 0:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no articles): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No articles found for '{event}' in the past 7 days. Try a broader topic."

        # Standardize articles and batch sentiment analysis once
        standardize_start = time.time()
        logger.info(f"Starting standardization for event '{event}' at {standardize_start}")
        std_newsapi = process_articles(newsapi_org_articles, "NewsAPI")
        std_guardian = process_articles(guardian_articles, "Guardian")
        std_aylien = process_articles(aylien_articles, "Aylien")
        std_gnews = process_articles(gnews_articles, "GNews")
        std_nyt = process_articles(nyt_articles, "NYT")
        std_mediastack = process_articles(mediastack_articles, "Mediastack")
        std_newsapi_ai = process_articles(newsapi_ai_articles, "NewsAPI.ai")
        
        all_articles = (std_newsapi + std_guardian + std_aylien + std_gnews +
                        std_nyt + std_mediastack + std_newsapi_ai)
        
        # TEMPORARILY DISABLE SENTIMENT ANALYSIS TO AVOID CRASHES
        logger.info(f"Skipping sentiment analysis for {len(all_articles)} articles to avoid crashes")
        sentiment_start = time.time()
        
        # Just set a default neutral sentiment for all articles
        for article in all_articles:
            article['sentiment_score'] = 0
            
        sentiment_time = time.time() - sentiment_start
        logger.info(f"Sentiment processing (disabled) took {sentiment_time:.2f} seconds")
        
        standardize_time = time.time() - standardize_start
        logger.info(f"Standardization took {standardize_time:.2f} seconds for event '{event}'")

        # Log initial article counts and distribution
        initial_source_counts = {}
        for article in all_articles:
            source = article.get('source', 'Unknown')
            initial_source_counts[source] = initial_source_counts.get(source, 0) + 1
        logger.info(f"Initial source distribution before processing for '{event}': {initial_source_counts}")
        logger.info(f"Initial total articles: {len(all_articles)}")

        # First, remove duplicates
        duplicate_start = time.time()
        logger.info(f"Starting duplicate removal for event '{event}' at {duplicate_start}")
        unique_articles = remove_duplicates(all_articles)
        
        # Log distribution after duplicate removal
        after_dedup_counts = {}
        for article in unique_articles:
            source = article.get('source', 'Unknown')
            after_dedup_counts[source] = after_dedup_counts.get(source, 0) + 1
        logger.info(f"Source distribution after duplicate removal for '{event}': {after_dedup_counts}")
        logger.info(f"Articles removed by deduplication: {len(all_articles) - len(unique_articles)}")
        duplicate_time = time.time() - duplicate_start
        logger.info(f"Duplicate removal took {duplicate_time:.2f} seconds for event '{event}'")

        # Then apply relevance filtering
        filter_start = time.time()
        logger.info(f"Starting filtering for event '{event}' at {filter_start}")
        relevant_articles = filter_relevant_articles(unique_articles, event)
        
        # Log distribution after relevance filtering
        after_relevance_counts = {}
        for article in relevant_articles:
            source = article.get('source', 'Unknown')
            after_relevance_counts[source] = after_relevance_counts.get(source, 0) + 1
        logger.info(f"Source distribution after relevance filtering for '{event}': {after_relevance_counts}")
        logger.info(f"Articles removed by relevance filtering: {len(unique_articles) - len(relevant_articles)}")
        filter_time = time.time() - filter_start
        logger.info(f"Filtering took {filter_time:.2f} seconds for event '{event}'")

        if not relevant_articles:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no relevant articles): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

        # Finally, group by source and cap to ensure balanced distribution
        group_and_cap_start = time.time()
        logger.info(f"Starting grouping and capping for event '{event}' at {group_and_cap_start}")
        source_groups = {}
        for article in relevant_articles:
            source = article.get('source', 'Unknown')
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(article)
        
        # Log article counts per source before capping
        logger.info(f"Articles per source before capping for '{event}':")
        for source, articles_list in source_groups.items():
            logger.info(f"- {source}: {len(articles_list)} articles")
        
        # Calculate dynamic cap based on number of sources
        num_sources = len(source_groups)
        dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(2, DEFAULT_TOP_N // num_sources))
        logger.info(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
        logger.info(f"Total slots available: {DEFAULT_TOP_N}")
        
        # Apply balanced distribution
        final_articles = []
        remaining_slots = DEFAULT_TOP_N
        
        # First round: Take at least one from each source
        first_round_sources = []
        for source, articles_list in source_groups.items():
            if articles_list and remaining_slots > 0:
                final_articles.append(articles_list[0])
                articles_list.pop(0)
                remaining_slots -= 1
                first_round_sources.append(source)
        logger.info(f"First round distribution - Added one article from each of these sources: {first_round_sources}")
        logger.info(f"Remaining slots after first round: {remaining_slots}")
        
        # Second round: Fill remaining slots evenly
        second_round_additions = {}
        while remaining_slots > 0:
            added_article = False
            for source, articles_list in source_groups.items():
                current_source_count = len([a for a in final_articles if a.get('source') == source])
                if articles_list and current_source_count < dynamic_cap:
                    final_articles.append(articles_list[0])
                    articles_list.pop(0)
                    remaining_slots -= 1
                    second_round_additions[source] = second_round_additions.get(source, 0) + 1
                    added_article = True
                    if remaining_slots <= 0:
                        break
            if not added_article:
                break
        logger.info(f"Second round distribution - Additional articles per source: {second_round_additions}")
        logger.info(f"Remaining slots after second round: {remaining_slots}")
        
        group_and_cap_time = time.time() - group_and_cap_start
        logger.info(f"Grouping and capping took {group_and_cap_time:.2f} seconds for event '{event}'")

        # Log final source distribution with detailed stats
        final_source_counts = {}
        for article in final_articles:
            source = article.get('source', 'Unknown')
            final_source_counts[source] = final_source_counts.get(source, 0) + 1
        
        logger.info(f"=== Final Distribution Summary for '{event}' ===")
        logger.info(f"Initial article count: {len(all_articles)}")
        logger.info(f"After deduplication: {len(unique_articles)}")
        logger.info(f"After relevance filtering: {len(relevant_articles)}")
        logger.info(f"Final article count: {len(final_articles)}")
        logger.info(f"Source distribution progression:")
        logger.info(f"1. Initial: {initial_source_counts}")
        logger.info(f"2. After dedup: {after_dedup_counts}")
        logger.info(f"3. After relevance: {after_relevance_counts}")
        logger.info(f"4. Final: {final_source_counts}")
        logger.info(f"=== End Distribution Summary ===")

        articles = final_articles
        logger.info(f"Capped articles count for event '{event}': {len(articles)}")

        # Check for partial failure and set a warning
        failed_sources = []
        if not newsapi_org_articles:
            failed_sources.append("NewsAPI")
        if not guardian_articles:
            failed_sources.append("Guardian")
        if not aylien_articles:
            failed_sources.append("Aylien")
        if not gnews_articles:
            failed_sources.append("GNews")
        if not nyt_articles:
            failed_sources.append("NYT")
        if not mediastack_articles:
            failed_sources.append("Mediastack")
        if not newsapi_ai_articles:
            failed_sources.append("NewsAPI.ai")
        
        if failed_sources:
            error_message = "Showing results from available sources"
            logger.warning(f"Partial API failure for event '{event}': {failed_sources}")
            total_time = time.time() - start_time

            filter_start = time.time()
            logger.info(f"Starting filtering for event '{event}' at {filter_start}")
            relevant_articles = filter_relevant_articles(articles, event)
            filter_time = time.time() - filter_start
            logger.info(f"Filtering took {filter_time:.2f} seconds for event '{event}'")

            if not relevant_articles:
                total_time = time.time() - start_time
                logger.info(f"Total request time (no relevant articles): {total_time:.2f} seconds, ending at {time.time()}")
                return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

            # Re-enable summarization with proper error handling
            logger.info(f"Starting summarization for event '{event}'")
            summarize_start = time.time()
            try:
                summary = summarize_articles(relevant_articles, event)
                if not summary or "Error generating summary" in summary:
                    summary = f"Found {len(relevant_articles)} articles about '{event}'. View them below for the latest news on this topic."
            except Exception as e:
                logger.error(f"Error during summarization: {e}")
                summary = f"Found {len(relevant_articles)} articles about '{event}'. View them below for the latest news on this topic."
            summarize_time = time.time() - summarize_start
            logger.info(f"Summarization took {summarize_time:.2f} seconds for event '{event}'")
            
            total_time = time.time() - start_time
            logger.info(f"Total request time (partial failure): {total_time:.2f} seconds, ending at {time.time()}")
            return summary, relevant_articles, error_message

        # Log source distribution after capping
        source_counts = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        logger.info(f"Source distribution for event '{event}' after capping: {source_counts}")

        # Process articles: remove duplicates, filter, and summarize
        duplicate_start = time.time()
        logger.info(f"Starting duplicate removal for event '{event}' at {duplicate_start}")
        unique_articles = remove_duplicates(articles)
        duplicate_time = time.time() - duplicate_start
        logger.info(f"Duplicate removal took {duplicate_time:.2f} seconds for event '{event}'")

        filter_start = time.time()
        logger.info(f"Starting filtering for event '{event}' at {filter_start}")
        relevant_articles = filter_relevant_articles(unique_articles, event)
        filter_time = time.time() - filter_start
        logger.info(f"Filtering took {filter_time:.2f} seconds for event '{event}'")
        
        # Check if we have relevant articles after filtering
        if not relevant_articles:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no relevant articles): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."
        
        # Re-enable summarization with proper error handling
        logger.info(f"Starting summarization for event '{event}'")
        summarize_start = time.time()
        try:
            summary = summarize_articles(relevant_articles, event)
            if not summary or "Error generating summary" in summary:
                summary = f"Found {len(relevant_articles)} articles about '{event}'. View them below for the latest news on this topic."
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            summary = f"Found {len(relevant_articles)} articles about '{event}'. View them below for the latest news on this topic."
        summarize_time = time.time() - summarize_start
        logger.info(f"Summarization took {summarize_time:.2f} seconds for event '{event}'")
        
        total_time = time.time() - start_time
        logger.info(f"Total request time: {total_time:.2f} seconds, ending at {time.time()}")
        return summary, relevant_articles, None
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Exception occurred, total time: {total_time:.2f} seconds, error: {str(e)}, ending at {time.time()}", exc_info=True)
        
        # Ensure models are cleared even if an error occurs
        try:
            ModelManager.get_instance().clear_models()
        except Exception as clear_error:
            logger.warning(f"Failed to clear models after error: {clear_error}")
            
        return None, None, f"An unexpected error occurred while processing '{event}'. Please try again later."

# Fix for the request context issue with a safer approach for the lambda
def trending_cache_key():
    try:
        # Try to get from request context if available
        return f"trending_summaries_{int(time.time() / 3600)}"
    except Exception:
        # Fall back to hourly key when outside request context
        return f"trending_summaries_{int(time.time() / 3600)}"

@cache.cached(timeout=3600, key_prefix=trending_cache_key)
def get_trending_summaries():
    """
    Fetch and process summaries for trending topics (4 topics, 3 articles each).
    Uses dynamic topics from trends.py instead of hardcoded ones.
    """
    topics = get_trending_topics(limit=4)  # Fetch dynamic topics
    summaries = {}
    logger.info(f"Fetching trending summaries for topics: {topics}")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_topic = {executor.submit(fetch_and_process_data, topic): topic for topic in topics}
        for future in future_to_topic:
            topic = future_to_topic[future]
            try:
                result = future.result()
                if isinstance(result, tuple) and result[0]:
                    summaries[topic] = {
                        'summary': result[0],
                        'articles': result[1][:3]  # Limit to 3 articles per topic
                    }
                else:
                    summaries[topic] = {
                        'summary': "No summary available",
                        'articles': []
                    }
            except Exception as e:
                logger.error(f"Error processing trending topic '{topic}': {e}")
                summaries[topic] = {
                    'summary': "Error generating summary",
                    'articles': []
                }
    
    logger.info(f"Generated trending summaries for {list(summaries.keys())}")
    return summaries

# Precompute trending summaries at startup
@routes.before_app_request
def preload_trending_summaries():
    """Precompute trending summaries at startup."""
    logger.info("Preloading trending summaries at startup")
    try:
        get_trending_summaries()
    except Exception as e:
        logger.error(f"Error preloading trending summaries: {e}")
        # Continue with request even if preloading fails

@routes.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main route for displaying trending topics and fetching custom summaries."""
    logger.info("Route / accessed")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {request.form}")
    summary = None
    articles = []
    event = None
    error = None
    trending_summaries = get_trending_summaries()  # Fetch dynamic trending summaries

    if request.method == 'POST':
        event = request.form.get('event')
        logger.info(f"Received POST request with event: {event}")
        if not event:
            error = "Please enter a news event to search for."
            logger.warning("No event provided in POST request")
        else:
            logger.info(f"Calling fetch_and_process_data for event: {event}")
            result = fetch_and_process_data(event)
            if isinstance(result, tuple):
                summary, articles, error = result
            else:
                summary = result.get('summary')
                articles = result.get('articles', [])
                error = None
            logger.info(f"After fetch_and_process_data, summary: {summary is not None}, articles: {len(articles) if articles else 0}, error: {error}")
            if error:
                logger.error(f"Error in processing event '{event}': {error}")

    logger.info(f"Rendering template with summary: {summary is not None}, articles: {len(articles) if articles else 0}, event: {event}, error: {error}")
    return render_template('index.html', summary=summary, articles=articles, event=event, error=error, trending_summaries=trending_summaries)

@routes.route('/data', methods=['POST'])
def get_news_data():
    """Handle the AJAX request for fetching news data with detailed error logging."""
    try:
        event = request.form.get('event')
        if not event:
            logger.error("No event provided in request")
            return jsonify({'error': 'Please provide an event to search for.'}), 400

        logger.info(f"Processing request for event: '{event}'")
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Fetch and process data
        summary, articles, error = fetch_and_process_data(event)
        
        # Log the results
        logger.info(f"fetch_and_process_data results for '{event}':")
        logger.info(f"- Summary: {summary if summary else 'None'}")
        logger.info(f"- Articles count: {len(articles) if articles else 0}")
        logger.info(f"- Error: {error if error else 'None'}")
        
        if not articles:
            logger.warning(f"No articles found for event '{event}'")
            return jsonify({'error': error or f"No articles found for '{event}'"}), 404

        # Calculate average sentiment
        sentiments = [article.get('sentiment_score', 0) for article in articles]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Count articles by source
        source_counts = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        metadata = {
            'total_articles': len(articles),
            'average_sentiment': avg_sentiment,
            'source_distribution': source_counts
        }
        
        # Add timestamp to summary to show it's a fresh result
        if summary:
            summary_with_time = f"{summary} (searched at {current_time})"
            logger.info(f"Final summary for '{event}': {summary_with_time}")
        else:
            # Provide a fallback summary if none was generated
            summary_with_time = f"Found {len(articles)} articles about '{event}'. (searched at {current_time})"
            logger.warning(f"Using fallback summary for '{event}': {summary_with_time}")
        
        # Structure response in format expected by frontend
        response = {
            'success': True,
            'summary': summary_with_time,
            'articles': articles,
            'metadata': metadata,
        }
        
        # Add warning if there was a partial failure
        if error:
            logger.warning(f"Partial failure warning for '{event}': {error}")
            response['warning'] = error
        
        logger.info(f"Returning success response for '{event}' with metadata: {metadata}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error processing request for '{event}': {str(e)}", exc_info=True)
        return jsonify({'error': f"An error occurred: {str(e)}"}), 500

@routes.route('/test', methods=['GET'])
def test():
    """Test route to verify routing is working."""
    logger.info("Test route accessed")
    return jsonify({"status": "ok"})