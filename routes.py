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
from config_prod import MAX_ARTICLES_PER_SOURCE  # Get from config_prod instead of app

routes = Blueprint('routes', __name__)
logger = logging.getLogger(__name__)
logger.info(f"Routes module initialized")

# We'll get the cache instance when the blueprint is registered
cache = None

@routes.record
def record_params(setup_state):
    global cache
    app = setup_state.app
    cache = app.extensions['cache'].get(app)
    logger.info(f"Cache set in routes: {cache}")

_is_first_request = True

# Create a function to safely access the cache
def get_cache():
    if cache is None:
        logger.warning("Cache not initialized yet, using dummy cache")
        # Return a dummy cache object that does nothing
        class DummyCache:
            def cached(self, *args, **kwargs):
                def decorator(f):
                    return f
                return decorator
        return DummyCache()
    return cache

@routes.before_app_request
def before_first_request():
    global _is_first_request
    if _is_first_request:
        # Your initialization code here (unchanged from original)
        _is_first_request = False

# Use a function to create the decorator
def cached_fetch_and_process_data(event):
    """Wrapper function to apply caching when cache is available"""
    cache_obj = get_cache()
    if hasattr(cache_obj, 'cached'):
        return cache_obj.cached(timeout=3600, key_prefix=lambda: f"summary_{event}")(lambda: _fetch_and_process_data(event))()
    else:
        return _fetch_and_process_data(event)

# Rename the original function
def _fetch_and_process_data(event):
    start_time = time.time()
    cache_key = f"summary_{event}"
    logger.info(f"Starting fetch_and_process_data for event '{event}', total start time: {start_time}, cache key: {cache_key}")
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
        if all_articles:
            model_manager = ModelManager.get_instance()
            sentiment_analyzer = model_manager.get_sentiment_analyzer()
            logger.info(f"Batching sentiment for {len(all_articles)} articles")
            sentiment_start = time.time()
            titles = [article['title'][:200] for article in all_articles]
            contents = [article['content'][:200] for article in all_articles]
            title_results = sentiment_analyzer(titles)  # Single batch for all titles
            content_results = sentiment_analyzer(contents)  # Single batch for all contents
            sentiment_time = time.time() - sentiment_start
            logger.info(f"Sentiment batching took {sentiment_time:.2f} seconds")
            for article, title_result, content_result in zip(all_articles, title_results, content_results):
                title_score = title_result['score'] if title_result['label'] == 'POSITIVE' else -title_result['score']
                content_score = content_result['score'] if content_result['label'] == 'POSITIVE' else -content_result['score']
                article['sentiment_score'] = 0.3 * title_score + 0.7 * content_score
        
        standardize_time = time.time() - standardize_start
        logger.info(f"Standardization took {standardize_time:.2f} seconds for event '{event}'")

        # Group by true source and cap at MAX_ARTICLES_PER_SOURCE
        group_and_cap_start = time.time()
        logger.info(f"Starting grouping and capping for event '{event}' at {group_and_cap_start}")
        source_groups = {}
        for article in all_articles:
            source = article.get('source', 'Unknown')
            logger.debug(f"Processing article with source '{source}' for event '{event}'")
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(article)
        
        capped_articles = []
        for source, articles_list in source_groups.items():
            logger.debug(f"Before capping, source '{source}' has {len(articles_list)} articles for event '{event}'")
            capped_articles.extend(articles_list[:MAX_ARTICLES_PER_SOURCE])
            logger.debug(f"After capping, source '{source}' has {min(len(articles_list), MAX_ARTICLES_PER_SOURCE)} articles for event '{event}'")
        group_and_cap_time = time.time() - group_and_cap_start
        logger.info(f"Grouping and capping took {group_and_cap_time:.2f} seconds for event '{event}'")

        articles = capped_articles
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

            if not relevant_articles:
                total_time = time.time() - start_time
                logger.info(f"Total request time (no relevant articles): {total_time:.2f} seconds, ending at {time.time()}")
                return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

            summarize_start = time.time()
            logger.info(f"Starting summarization for event '{event}' at {summarize_start}")
            summary = summarize_articles(relevant_articles, event)
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

        if not relevant_articles:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no relevant articles): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

        # Summarize articles
        summarize_start = time.time()
        logger.info(f"Starting summarization for event '{event}' at {summarize_start}")
        summary = summarize_articles(relevant_articles, event)
        summarize_time = time.time() - summarize_start
        logger.info(f"Summarization took {summarize_time:.2f} seconds for event '{event}'")

        if summary.startswith("Error"):
            total_time = time.time() - start_time
            logger.info(f"Total request time (summarization error): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"Failed to generate a summary for '{event}' due to processing issues."

        # Log the final number of articles
        logger.info(f"Final number of articles for event '{event}': {len(relevant_articles)}")

        # Calculate average sentiment and prepare article data
        total_sentiment = 0
        article_data = []
        
        for article in relevant_articles:
            sentiment_score = article.get('sentiment_score', 0)
            total_sentiment += sentiment_score
            article_data.append({
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'content': article.get('content', ''),
                'source': article.get('source', 'Unknown'),
                'sentiment_score': sentiment_score
            })
        
        avg_sentiment = total_sentiment / len(relevant_articles) if relevant_articles else 0
        
        response = {
            'articles': article_data,
            'summary': summary,
            'metadata': {
                'total_articles': len(relevant_articles),
                'average_sentiment': avg_sentiment,
                'source_distribution': source_counts
            }
        }

        total_time = time.time() - start_time
        logger.info(f"Total request time: {total_time:.2f} seconds, ending at {time.time()}")

        # Ensure models are cleared after processing
        try:
            ModelManager.get_instance().clear_models()
        except Exception as e:
            logger.warning(f"Failed to clear models: {e}")

        return response
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Exception occurred, total time: {total_time:.2f} seconds, error: {str(e)}, ending at {time.time()}", exc_info=True)
        
        # Ensure models are cleared even if an error occurs
        try:
            ModelManager.get_instance().clear_models()
        except Exception as clear_error:
            logger.warning(f"Failed to clear models after error: {clear_error}")
            
        return None, None, f"An unexpected error occurred while processing '{event}'. Please try again later."

# Cache trending topics and summaries with dynamic hot topics
def cached_get_trending_summaries():
    """Wrapper function to apply caching when cache is available"""
    cache_obj = get_cache()
    if hasattr(cache_obj, 'cached'):
        return cache_obj.cached(timeout=3600, key_prefix="trending_summaries")(_get_trending_summaries)()
    else:
        return _get_trending_summaries()

def _get_trending_summaries():
    """
    Fetch and process summaries for trending topics (4 topics, 3 articles each).
    Uses dynamic topics from trends.py instead of hardcoded ones.
    """
    topics = get_trending_topics(limit=4)  # Fetch dynamic topics
    summaries = {}
    logger.info(f"Fetching trending summaries for topics: {topics}")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_topic = {executor.submit(cached_fetch_and_process_data, topic): topic for topic in topics}
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
    """Preload trending summaries at startup"""
    logger.info("Preloading trending summaries at startup")
    cached_get_trending_summaries()

@routes.route('/', methods=['GET', 'POST'])
def index():
    """Main route for the application."""
    logger.info("Route / accessed")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {request.form}")
    
    # Get trending summaries
    trending_summaries = cached_get_trending_summaries()  # Fetch dynamic trending summaries
    
    # Handle POST request (search form submission)
    if request.method == 'POST':
        event = request.form.get('event')
        if event:
            logger.info(f"Calling cached_fetch_and_process_data for event: {event}")
            result = cached_fetch_and_process_data(event)
            if isinstance(result, tuple) and len(result) == 3:
                summary, articles, error = result
                logger.info(f"After cached_fetch_and_process_data, summary: {summary is not None}, articles: {len(articles) if articles else 0}, error: {error}")
                return render_template('index.html', 
                                      summary=summary, 
                                      articles=articles, 
                                      event=event, 
                                      error=error,
                                      trending_summaries=trending_summaries)
    
    # Handle GET request (initial page load)
    return render_template('index.html', 
                          summary=False, 
                          articles=[], 
                          event=None, 
                          error=None,
                          trending_summaries=trending_summaries)

@routes.route('/data', methods=['POST'])
def get_news_data():
    """API endpoint to fetch news data."""
    try:
        logger.info("Route /data accessed")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")  # Log headers for more context
        logger.info(f"Request form data: {request.form}")
        logger.info(f"Request JSON data: {request.get_json(silent=True)}")
        logger.info(f"Request args: {request.args}")
        logger.info(f"Raw data: {request.data}")
        
        # Try to get the event from various sources
        event = (request.form.get('event') or 
                 (request.get_json(silent=True) or {}).get('event') or 
                 request.args.get('event'))
        
        if not event:
            logger.error("No event provided in request")
            return jsonify({'error': "Please enter a news event to search for."}), 400
        
        logger.info(f"Processing event: {event}")
        result = cached_fetch_and_process_data(event)
        
        # Log detailed result info
        if isinstance(result, tuple) and len(result) == 3:
            summary, articles, error = result
            logger.info(f"cached_fetch_and_process_data returned tuple - summary: {summary is not None}, "
                       f"articles: {len(articles) if articles else 0}, error: {error}")
            # Create metadata if it's not available
            if articles:
                total_sentiment = sum(article.get('sentiment_score', 0) for article in articles)
                avg_sentiment = total_sentiment / len(articles) if articles else 0
                source_counts = {}
                for article in articles:
                    source = article.get('source', 'Unknown')
                    source_counts[source] = source_counts.get(source, 0) + 1
                metadata = {
                    'total_articles': len(articles),
                    'average_sentiment': avg_sentiment,
                    'source_distribution': source_counts
                }
            else:
                metadata = {
                    'total_articles': 0,
                    'average_sentiment': 0,
                    'source_distribution': {}
                }
        else:
            summary = result.get('summary')
            articles = result.get('articles', [])
            metadata = result.get('metadata', {
                'total_articles': len(articles),
                'average_sentiment': 0,
                'source_distribution': {}
            })
            error = None
            logger.info(f"cached_fetch_and_process_data returned dict - summary: {summary is not None}, "
                        f"articles: {len(articles)}, metadata: {metadata}, error: {error}")

        # Prepare and log the response
        if articles:
            response_data = {
                'summary': summary if summary else "Summary not available.",
                'articles': articles,
                'metadata': metadata
            }
            if error:  # Add warning if there was a partial failure
                response_data['warning'] = error
                logger.warning(f"Partial failure warning: {error}")
            logger.info(f"Returning success response - articles: {len(articles)}, summary: {summary is not None}")
            return jsonify(response_data), 200
        elif error:
            logger.error(f"Returning error response: {error}")
            return jsonify({'error': error}), 400
        else:
            logger.error("No articles found and no specific error provided")
            return jsonify({'error': 'No articles found.'}), 404

    except Exception as e:
        logger.error(f"Unexpected error in get_news_data: {str(e)}", exc_info=True)  # Include stack trace
        return jsonify({'error': f"An internal server error occurred: {str(e)}"}), 500

@routes.route('/test', methods=['GET'])
def test():
    """Test route to verify routing is working."""
    logger.info("Test route accessed")
    return jsonify({"status": "ok"})