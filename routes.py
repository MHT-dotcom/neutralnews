from flask import render_template, request, Blueprint, jsonify
import logging
import time
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
from config import MAX_ARTICLES_PER_SOURCE, cache

# Set up logging
logger = logging.getLogger(__name__)

logger.info("Initializing routes Blueprint")
routes = Blueprint('routes', __name__, template_folder='templates')
logger.info("Routes Blueprint initialized")

@cache.cached(timeout=3600, key_prefix='summary')
def fetch_and_process_data(event):
    start_time = time.time()
    logger.info(f"Starting fetch_and_process_data for event '{event}', total start time: {start_time}")
    try:
        # Fetch articles from multiple APIs
        fetch_start = time.time()
        logger.info(f"Beginning API fetch for event '{event}' at {fetch_start}")
        newsapi_org_articles = fetch_newsapi_org(event)
        guardian_articles = fetch_guardian(event)
        aylien_articles = fetch_aylien_articles(event)
        gnews_articles = fetch_gnews_articles(event)
        nyt_articles = fetch_nyt_articles(event)
        mediastack_articles = fetch_mediastack_articles(event)
        newsapi_ai_articles = fetch_newsapi_ai_articles(event)
        fetch_time = time.time() - fetch_start
        logger.info(f"Fetching articles took {fetch_time:.2f} seconds for event '{event}', end time: {time.time()}")

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
            logger.info(f"Total time for failed fetch: {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No articles found for '{event}' in the past 7 days. Try a broader topic."

        # Standardize articles based on source
        standardize_start = time.time()
        logger.info(f"Starting standardization for event '{event}' at {standardize_start}")
        std_newsapi = process_articles(newsapi_org_articles, "NewsAPI")
        std_guardian = process_articles(guardian_articles, "Guardian")
        std_aylien = process_articles(aylien_articles, "Aylien")
        std_gnews = process_articles(gnews_articles, "GNews")
        std_nyt = process_articles(nyt_articles, "NYT")
        std_mediastack = process_articles(mediastack_articles, "Mediastack")
        std_newsapi_ai = process_articles(newsapi_ai_articles, "NewsAPI.ai")
        standardize_time = time.time() - standardize_start
        logger.info(f"Standardizing articles took {standardize_time:.2f} seconds for event '{event}', end time: {time.time()}")

        # Combine all standardized articles
        all_articles = (std_newsapi + std_guardian + std_aylien + std_gnews +
                       std_nyt + std_mediastack + std_newsapi_ai)
        logger.info(f"Combined articles count for event '{event}': {len(all_articles)}")

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
        logger.info(f"Grouping and capping articles took {group_and_cap_time:.2f} seconds for event '{event}', end time: {time.time()}")

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
            logger.info(f"Total time for partial failure: {total_time:.2f} seconds, ending at {time.time()}")
            
            # Process articles even with partial failure
            process_start = time.time()
            logger.info(f"Starting processing with partial results for event '{event}' at {process_start}")
            unique_articles = remove_duplicates(articles)
            relevant_articles = filter_relevant_articles(unique_articles, event)
            process_time = time.time() - process_start
            logger.info(f"Processing articles took {process_time:.2f} seconds for event '{event}', end time: {time.time()}")

            if not relevant_articles:
                return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

            # Generate summary from available articles
            summarize_start = time.time()
            logger.info(f"Starting summarization with partial results for event '{event}' at {summarize_start}")
            summary = summarize_articles(relevant_articles, event)
            summarize_time = time.time() - summarize_start
            logger.info(f"Summarizing articles took {summarize_time:.2f} seconds for event '{event}', end time: {time.time()}")
            
            return summary, relevant_articles, error_message

        # Log source distribution after capping
        source_counts = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        logger.info(f"Source distribution for event '{event}' after capping: {source_counts}")

        # Process articles: remove duplicates, filter, and summarize
        process_start = time.time()
        logger.info(f"Starting processing (remove duplicates and filter) for event '{event}' at {process_start}")
        unique_articles = remove_duplicates(articles)
        relevant_articles = filter_relevant_articles(unique_articles, event)
        process_time = time.time() - process_start
        logger.info(f"Processing articles (remove duplicates and filter) took {process_time:.2f} seconds for event '{event}', end time: {time.time()}")

        if not relevant_articles:
            total_time = time.time() - start_time
            logger.info(f"Total time for no relevant articles: {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No relevant articles found for '{event}' after filtering. Try a broader topic."

        # Summarize articles
        summarize_start = time.time()
        logger.info(f"Starting summarization for event '{event}' at {summarize_start}")
        summary = summarize_articles(relevant_articles, event)
        summarize_time = time.time() - summarize_start
        logger.info(f"Summarizing articles took {summarize_time:.2f} seconds for event '{event}', end time: {time.time()}")

        if summary.startswith("Error"):
            total_time = time.time() - start_time
            logger.info(f"Total time for summarization error: {total_time:.2f} seconds, ending at {time.time()}")
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
        logger.info(f"Total time for fetch_and_process_data: {total_time:.2f} seconds, ending at {time.time()}")

        # Ensure models are cleared after processing
        try:
            ModelManager.get_instance().clear_models()
        except Exception as e:
            logger.warning(f"Failed to clear models: {e}")

        return response
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Exception occurred, total time: {total_time:.2f} seconds, error: {str(e)}, ending at {time.time()}")
        
        # Ensure models are cleared even if an error occurs
        try:
            ModelManager.get_instance().clear_models()
        except Exception as clear_error:
            logger.warning(f"Failed to clear models after error: {clear_error}")
            
        return None, None, f"An unexpected error occurred while processing '{event}'. Please try again later."

@routes.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main route for fetching and summarizing articles."""
    logger.info("Route / accessed")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {request.form}")
    summary = None
    articles = []
    event = None
    error = None

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
                error = error

    logger.info(f"Rendering template with summary: {summary is not None}, articles: {len(articles) if articles else 0}, event: {event}, error: {error}")
    return render_template('index.html', summary=summary, articles=articles, event=event, error=error)

@routes.route('/data', methods=['POST'])
def get_news_data():
    """Handle the AJAX request for fetching news data."""
    try:
        # Log the entire request for debugging
        logger.info("Route /data accessed")
        logger.info(f"Request method: {request.method}")
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
        result = fetch_and_process_data(event)
        
        # Check if result is a tuple (old format) or a dictionary (new format)
        if isinstance(result, tuple):
            summary, articles, error = result
            # Create metadata if it's not available
            if articles:
                # Calculate average sentiment
                total_sentiment = sum(article.get('sentiment_score', 0) for article in articles)
                avg_sentiment = total_sentiment / len(articles) if articles else 0
                
                # Count sources
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
            # Result is already in the correct format
            summary = result.get('summary')
            articles = result.get('articles', [])
            metadata = result.get('metadata', {
                'total_articles': len(articles),
                'average_sentiment': 0,
                'source_distribution': {}
            })
            error = None
            
        logger.info(f"AJAX response - summary: {summary is not None}, articles: {len(articles) if articles else 0}, error: {error}")
        
        # Even if there's a partial error, return success if we have articles
        if articles:
            response_data = {
                'summary': summary if summary else "Summary not available.",
                'articles': articles,
                'metadata': metadata
            }
            if error:  # Add warning if there was a partial failure
                response_data['warning'] = error
            return jsonify(response_data), 200
        elif error:  # Only return error status if we have no articles
            return jsonify({'error': error}), 400
        else:
            return jsonify({'error': 'No articles found.'}), 404
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@routes.route('/test', methods=['GET'])
def test():
    """Test route to verify routing is working."""
    logger.info("Test route accessed")
    return jsonify({"status": "ok"})