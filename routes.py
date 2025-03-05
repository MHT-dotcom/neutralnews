"""
This file defines the web routes for the Neutral News application.
It handles HTTP requests for the main page, news fetching, and API endpoints.
"""

from flask import Blueprint, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import logging
from fetchers import (fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
                     fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
                     fetch_newsapi_ai_articles)
from processors import (process_articles, remove_duplicates, filter_relevant_articles,
                       summarize_articles, ModelManager)
from trends import get_trending_topics

routes = Blueprint('routes', __name__)
logger = logging.getLogger(__name__)

def fetch_and_process_data(event):
    """Main function to fetch and process news data"""
    logger.info(f"Starting fetch_and_process_data for event '{event}'")
    
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
        
        if not all_articles:
            return None, None, f"No articles found for '{event}'"
            
        # Process sentiment
        if all_articles:  # Safety check before processing
            model_manager = ModelManager.get_instance()
            sentiment_analyzer = model_manager.get_sentiment_analyzer()
            titles = [article['title'][:200] for article in all_articles]
            contents = [article['content'][:200] for article in all_articles]
            
            title_results = sentiment_analyzer(titles)
            content_results = sentiment_analyzer(contents)
            
            for article, title_result, content_result in zip(all_articles, title_results, content_results):
                title_score = title_result['score'] if title_result['label'] == 'POSITIVE' else -title_result['score']
                content_score = content_result['score'] if content_result['label'] == 'POSITIVE' else -content_result['score']
                article['sentiment_score'] = 0.3 * title_score + 0.7 * content_score
        
        # Remove duplicates and filter relevant articles
        unique_articles = remove_duplicates(all_articles)
        relevant_articles = filter_relevant_articles(unique_articles, event)
        
        if not relevant_articles:
            return None, None, f"No relevant articles found for '{event}'"
            
        # Generate summary
        summary = summarize_articles(relevant_articles, event)
        
        return summary, relevant_articles, None
        
    except Exception as e:
        logger.error(f"Error in fetch_and_process_data: {str(e)}")
        return None, None, f"Error processing request: {str(e)}"

def get_trending_summaries():
    """Fetch and process summaries for trending topics"""
    topics = get_trending_topics(limit=4)
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

@routes.route('/', methods=['GET', 'POST'])
def index():
    """Main route that displays trending topics and handles search"""
    try:
        # Get trending summaries
        trending_summaries = get_trending_summaries()
        
        # Handle POST request (search form submission)
        if request.method == 'POST':
            event = request.form.get('event')
            if event:
                summary, articles, error = fetch_and_process_data(event)
                return render_template('index.html', 
                                    summary=summary,
                                    articles=articles,
                                    event=event,
                                    error=error,
                                    trending_summaries=trending_summaries)
        
        # Handle GET request (initial page load)
        return render_template('index.html',
                            summary=None,
                            articles=[],
                            event=None,
                            error=None,
                            trending_summaries=trending_summaries)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
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
        return jsonify({"error": "No query provided"}), 400

    try:
        summary, articles, error_message = fetch_and_process_data(event)
        if error_message and not articles:
            return jsonify({"error": error_message}), 404
        
        response_data = {
            "status": "success",
            "summary": summary,
            "articles": articles,
            "error": error_message if error_message else None
        }
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error processing request for event '{event}': {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@routes.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "API is operational"})