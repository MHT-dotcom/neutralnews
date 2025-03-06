"""
This file defines the web routes for the Neutral News application.
It handles HTTP requests for the main page, news fetching, and API endpoints.
"""

from flask import Blueprint, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import logging
import time
<<<<<<< HEAD
import inspect
from fetchers import (fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
                     fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
                     fetch_newsapi_ai_articles)
from processors import (process_articles, remove_duplicates, filter_relevant_articles,
                       summarize_articles, ModelManager)
from trends import get_trending_topics
=======
from fetchers import (
    fetch_newsapi_org,
    fetch_guardian,
    fetch_aylien_articles,
    fetch_gnews_articles,
    fetch_nyt_articles,
    fetch_mediastack_articles,
    fetch_newsapi_ai_articles
)
from processors import (
    process_articles,
    remove_duplicates,
    filter_relevant_articles,
    summarize_articles,
    ModelManager
)
from config_prod import MAX_ARTICLES_PER_SOURCE, cache
from .trends import get_trending_topics
from .fetchers import fetch_trending_articles
from .processors import process_trending_articles
>>>>>>> dbcc478 (added logging)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Log when this module is imported
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Routes module is being imported")
=======
logger.info("Initializing routes Blueprint")
routes = Blueprint('news_routes', __name__, template_folder='templates')  # Match app.py's unique name
logger.info("Routes Blueprint initialized with routes to be registered")
>>>>>>> dbcc478 (added logging)

# Log the call stack to see who's importing this module
current_frame = inspect.currentframe()
try:
    call_stack = inspect.getouterframes(current_frame)
    caller_info = ", ".join([f"{frame.filename}:{frame.lineno}" for frame in call_stack[1:4]])
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Routes module imported by: {caller_info}")
except Exception as e:
    logger.error(f"[IMPORT_SEQUENCE] Error getting call stack: {e}")
finally:
    del current_frame  # Prevent reference cycles

# Create the Blueprint
routes = Blueprint('routes', __name__)
logger.info(f"[BLUEPRINT] {time.time()} - Routes blueprint created")

def fetch_and_process_data(event):
    """Main function to fetch and process news data"""
    start_time = time.time()
    logger.info(f"[FETCH_PROCESS] Starting fetch_and_process_data for event '{event}'")
    
    try:
        # Fetch articles from multiple APIs in parallel
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
            logger.info(f"[FETCH_PROCESS] Fetched articles from all APIs in {time.time() - start_time:.2f}s")
        
        newsapi_org_articles, guardian_articles, aylien_articles, gnews_articles, nyt_articles, mediastack_articles, newsapi_ai_articles = results
        
        # Process and standardize articles
        all_articles = (
            process_articles(newsapi_org_articles, "NewsAPI") +
            process_articles(guardian_articles, "Guardian") +
            process_articles(aylien_articles, "Aylien") +
            process_articles(gnews_articles, "GNews") +
            process_articles(nyt_articles, "NYT") +
            process_articles(mediastack_articles, "Mediastack") +
            process_articles(newsapi_ai_articles, "NewsAPI.ai")
        )
        logger.info(f"[FETCH_PROCESS] Standardized {len(all_articles)} articles in {time.time() - start_time:.2f}s")
        
        if not all_articles:
            logger.warning(f"[FETCH_PROCESS] No articles found for '{event}'")
            return None, None, f"No articles found for '{event}'"
            
        # Process sentiment
        if all_articles:  # Safety check before processing
            model_manager = ModelManager.get_instance()
            sentiment_analyzer = model_manager.get_sentiment_analyzer()
            titles = [article['title'][:200] for article in all_articles]
            contents = [article['content'][:200] for article in all_articles]
            
            logger.info(f"[FETCH_PROCESS] Starting sentiment analysis for {len(all_articles)} articles")
            sentiment_start = time.time()
            title_results = sentiment_analyzer(titles)
            content_results = sentiment_analyzer(contents)
            logger.info(f"[FETCH_PROCESS] Completed sentiment analysis in {time.time() - sentiment_start:.2f}s")
            
            for article, title_result, content_result in zip(all_articles, title_results, content_results):
                title_score = title_result['score'] if title_result['label'] == 'POSITIVE' else -title_result['score']
                content_score = content_result['score'] if content_result['label'] == 'POSITIVE' else -content_result['score']
                article['sentiment_score'] = 0.3 * title_score + 0.7 * content_score
        
        # Remove duplicates and filter relevant articles
        unique_articles = remove_duplicates(all_articles)
        relevant_articles = filter_relevant_articles(unique_articles, event)
        logger.info(f"[FETCH_PROCESS] Filtered to {len(relevant_articles)} relevant articles in {time.time() - start_time:.2f}s")
        
        if not relevant_articles:
            logger.warning(f"[FETCH_PROCESS] No relevant articles found for '{event}'")
            return None, None, f"No relevant articles found for '{event}'"
            
        # Generate summary
        summary_start = time.time()
        summary = summarize_articles(relevant_articles, event)
        logger.info(f"[FETCH_PROCESS] Generated summary in {time.time() - summary_start:.2f}s")
        
        total_time = time.time() - start_time
        logger.info(f"[FETCH_PROCESS] Completed fetch_and_process_data for '{event}' in {total_time:.2f}s")
        return summary, relevant_articles, None
        
    except Exception as e:
        logger.error(f"[FETCH_PROCESS] Error in fetch_and_process_data: {str(e)}", exc_info=True)
        return None, None, f"Error processing request: {str(e)}"

def get_trending_summaries():
    """Fetch and process summaries for trending topics"""
    start_time = time.time()
    topics = get_trending_topics(limit=4)
    summaries = {}
    logger.info(f"[TRENDING] Fetching trending summaries for topics: {topics}")
    
    # with ThreadPoolExecutor(max_workers=4) as executor:
    #     future_to_topic = {executor.submit(fetch_and_process_data, topic): topic for topic in topics}
    #     for future in future_to_topic:
    #         topic = future_to_topic[future]
    #         try:
    #             result = future.result()
    #             if isinstance(result, tuple) and result[0]:
    #                 summaries[topic] = {
    #                     'summary': result[0],
    #                     'articles': result[1][:3]  # Limit to 3 articles per topic
    #                 }
    #             else:
    #                 summaries[topic] = {
    #                     'summary': result[2] if result[2] else "No summary available",
    #                     'articles': []
    #                 }
    #         except Exception as e:
    #             logger.error(f"[TRENDING] Error processing trending topic '{topic}': {e}", exc_info=True)
    #             summaries[topic] = {
    #                 'summary': "Error generating summary",
    #                 'articles': []
    #             }
    
    logger.info(f"[TRENDING] Generated trending summaries for {list(summaries.keys())} in {time.time() - start_time:.2f}s")
    return summaries

@routes.route('/', methods=['GET', 'POST'])
def index():
<<<<<<< HEAD
    """Main route that displays trending topics and handles search"""
    try:
        # Get trending summaries
        trending_start = time.time()
        trending_summaries = get_trending_summaries()
        logger.info(f"[ROUTE] Loaded trending summaries in {time.time() - trending_start:.2f}s")
        
        # Handle POST request (search form submission)
        if request.method == 'POST':
            event = request.form.get('event')
            if event:
                logger.info(f"[ROUTE] Processing search for event '{event}'")
                summary, articles, error = fetch_and_process_data(event)
                return render_template('index.html', 
                                    summary=summary,
                                    articles=articles,
                                    event=event,
                                    error=error,
                                    trending_summaries=trending_summaries)
        
        # Handle GET request (initial page load)
        logger.info("[ROUTE] Rendering index page with trending summaries")
        return render_template('index.html',
                            summary=None,
                            articles=[],
                            event=None,
                            error=None,
                            trending_summaries=trending_summaries)
    except Exception as e:
        logger.error(f"[ROUTE] Error in index route: {str(e)}", exc_info=True)
        return render_template('index.html',
                            summary=None,
                            articles=[],
                            event=None,
                            error=str(e),
                            trending_summaries={})

@routes.route('/api/news', methods=['GET', 'POST'])
def get_news():
    """
    API endpoint for fetching news data
    Supports both GET (query params) and POST (form data)
    """
    # Get query from either POST form data or GET query params
    event = request.form.get('event') if request.method == 'POST' else request.args.get('q')
    if not event:
        logger.warning("[API] No query provided in request")
        return jsonify({"error": "No query provided"}), 400
=======
    """Handle the main route for displaying trending topics and fetching custom summaries."""
    logger.info("[INDEX] Route / accessed")
    logger.info(f"[INDEX] Request method: {request.method}")
    logger.info(f"[INDEX] Request form data: {request.form}")
    summary = None
    articles = []
    event = None
    error = None
    trending_summaries = get_trending_summaries()  # Fetch from cache

    if request.method == 'POST':
        event = request.form.get('event')
        logger.info(f"[INDEX] Received POST request with event: {event}")
        if not event:
            error = "Please enter a news event to search for."
            logger.warning("[INDEX] No event provided in POST request")
        else:
            logger.info(f"[INDEX] Calling fetch_and_process_data for event: {event}")
            result = fetch_and_process_data(event)
            if isinstance(result, tuple):
                summary, articles, error = result
            else:
                summary = result.get('summary')
                articles = result.get('articles', [])
                error = None
            logger.info(f"[INDEX] After fetch_and_process_data, summary: {summary is not None}, articles: {len(articles) if articles else 0}, error: {error}")
            if error:
                logger.error(f"[INDEX] Error in processing event '{event}': {error}")

    logger.info(f"[INDEX] Rendering template with summary: {summary is not None}, articles: {len(articles) if articles else 0}, event: {event}, error: {error}")
    return render_template('index.html', summary=summary, articles=articles, event=event, error=error, trending_summaries=trending_summaries)

@routes.route('/data', methods=['POST'])
def get_news_data():
    """Handle the AJAX request for fetching news data with detailed error logging."""
    logger.info("[DATA] Route /data accessed")
    logger.info(f"[DATA] Received POST request with data: {request.get_json(silent=True)}")
    logger.info(f"[DATA] Request headers: {dict(request.headers)}")
    logger.info(f"[DATA] Request form data: {request.form}")
    logger.info(f"[DATA] Request args: {request.args}")
    logger.info(f"[DATA] Raw request data: {request.data}")
>>>>>>> dbcc478 (added logging)

    try:
        logger.info(f"[API] Processing news request for event '{event}'")
        summary, articles, error_message = fetch_and_process_data(event)
        if error_message and not articles:
            logger.warning(f"[API] No articles found for '{event}': {error_message}")
            return jsonify({"error": error_message}), 404
        
<<<<<<< HEAD
        response_data = {
            "status": "success",
            "summary": summary,
            "articles": articles,
            "error": error_message if error_message else None
        }
        logger.info(f"[API] Successfully processed request for '{event}'")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"[API] Error processing request for event '{event}': {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@routes.route('/health')
def health_check():
    logger.info("[HEALTH] Health check requested")
    return jsonify({"status": "healthy", "message": "API is operational"})
=======
        if not event:
            logger.error("[DATA] No event provided in request")
            return jsonify({'error': "Please enter a news event to search for."}), 400
        
        logger.info(f"[DATA] Processing event: {event}")
        result = fetch_and_process_data(event)
        
        # Log detailed result info
        if isinstance(result, tuple):
            summary, articles, error = result
            logger.info(f"[DATA] fetch_and_process_data returned tuple - summary: {summary is not None}, "
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
            logger.info(f"[DATA] fetch_and_process_data returned dict - summary: {summary is not None}, "
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
                logger.warning(f"[DATA] Partial failure warning: {error}")
            logger.info(f"[DATA] Returning success response - articles: {len(articles)}, summary: {summary is not None}")
            logger.info(f"[DATA] Response data: {response_data}")
            return jsonify(response_data), 200
        elif error:
            logger.error(f"[DATA] Returning error response: {error}")
            logger.info(f"[DATA] Response data: {{'error': '{error}'}}")
            return jsonify({'error': error}), 400
        else:
            logger.error("[DATA] No articles found and no specific error provided")
            logger.info("[DATA] Response data: {'error': 'No articles found.'}")
            return jsonify({'error': 'No articles found.'}), 404

    except Exception as e:
        logger.error(f"[DATA] Unexpected error in get_news_data: {str(e)}", exc_info=True)
        logger.info(f"[DATA] Response data: {{'error': 'An internal server error occurred: {str(e)}'}}")
        return jsonify({'error': f"An internal server error occurred: {str(e)}"}), 500

@routes.route('/test', methods=['GET'])
def test():
    """Test route to verify routing is working."""
    logger.info("[TEST] Test route accessed")
    logger.info("[TEST] Returning status: ok")
    return jsonify({"status": "ok"})
>>>>>>> dbcc478 (added logging)
