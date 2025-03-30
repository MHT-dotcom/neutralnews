from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from concurrent.futures import ThreadPoolExecutor
import time
import logging
import sqlite3
import json
import os
import asyncio
from datetime import datetime, timedelta
from fetchers import (fetch_newsapi_org, fetch_guardian, fetch_aylien_articles,
                     fetch_gnews_articles, fetch_nyt_articles, fetch_mediastack_articles,
                     fetch_newsapi_ai_articles, async_fetch_articles)
from processors import (process_articles, remove_duplicates, filter_relevant_articles,
                       summarize_articles)
from config_prod import (MAX_ARTICLES_PER_SOURCE, cache, NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, 
                        GNEWS_API_KEY, NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
                        NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY, DEFAULT_TOP_N, CACHE_CONFIG, DEBUG)
from get_img import generate_and_save_image, get_image_cache_stats, optimize_image_storage
from topics import get_trending_topics

# Align blueprint name with app.py registration
routes = Blueprint('news_routes', __name__)
logger = logging.getLogger(__name__)

_is_first_request = True

def get_db_path():
    """Helper function to find DB_PATH from multiple sources with fallback."""
    db_path = None
    
    # 1. Try Flask app config
    if hasattr(current_app, 'config'):
        db_path = current_app.config.get("DB_PATH")
        logger.debug(f"DB_PATH from current_app.config: {db_path}")
    
    # 2. Try environment variable
    if not db_path:
        db_path = os.environ.get("DB_PATH")
        logger.debug(f"DB_PATH from environment: {db_path}")
    
    # 3. Use fallback path as last resort
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "search_db.sqlite")
        logger.warning(f"Using fallback DB_PATH: {db_path}")
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    
    logger.debug(f"Using DB_PATH: {db_path}")
    return db_path

@routes.before_app_request
def before_first_request():
    global _is_first_request
    if _is_first_request:
        _is_first_request = False
        init_db()  # Initialize DB on first request

def fetch_and_process_data(event):
    """Fetch data from multiple APIs, process it, and return articles and a summary."""
    start_time = time.time()
    logger.info(f"UNCACHED: Starting fetch_and_process_data for event '{event}', total start time: {start_time}")
    
    if 'election' in event.lower():
        logger.info(f"ELECTIONS TOPIC DETECTED in search: '{event}'")
    
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
        fetch_start = time.time()
        logger.info(f"Beginning API fetch for event '{event}' at {fetch_start}")
        
        # Run async fetch in an executor to avoid blocking Flask
        loop = asyncio.new_event_loop()
        
        def run_async_fetch():
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(async_fetch_articles(event))
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            results = executor.submit(run_async_fetch).result()
        
        newsapi_org_articles, guardian_articles, aylien_articles, gnews_articles, nyt_articles, mediastack_articles, newsapi_ai_articles = results
        
        fetch_time = time.time() - fetch_start
        logger.info(f"API Fetching took {fetch_time:.2f} seconds for event '{event}'")

        logger.info(f"Articles retrieved for event '{event}': "
                   f"NewsAPI.org: {len(newsapi_org_articles)}, "
                   f"Guardian: {len(guardian_articles)}, "
                   f"Aylien: {len(aylien_articles)}, "
                   f"GNews: {len(gnews_articles)}, "
                   f"NYT: {len(nyt_articles)}, "
                   f"Mediastack: {len(mediastack_articles)}, "
                   f"NewsAPI.ai: {len(newsapi_ai_articles)}")

        total_fetched = (len(newsapi_org_articles) + len(guardian_articles) + 
                        len(aylien_articles) + len(gnews_articles) +
                        len(nyt_articles) + len(mediastack_articles) + 
                        len(newsapi_ai_articles))
        logger.info(f"Total articles fetched for event '{event}': {total_fetched}")
        if total_fetched == 0:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no articles): {total_time:.2f} seconds, ending at {time.time()}")
            return None, None, f"No articles found for '{event}' in the past 7 days. Try a broader topic."

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
        
        # Skip sentiment analysis, just set sentiment_score to 0 for all articles
        logger.info(f"Skipping sentiment analysis for {len(all_articles)} articles")
        sentiment_start = time.time()
        for article in all_articles:
            article['sentiment_score'] = 0
        sentiment_time = time.time() - sentiment_start
        logger.info(f"Sentiment processing (removed) took {sentiment_time:.2f} seconds")
        
        standardize_time = time.time() - standardize_start
        logger.info(f"Standardization took {standardize_time:.2f} seconds for event '{event}'")

        initial_source_counts = {}
        for article in all_articles:
            source = article.get('source', 'Unknown')
            initial_source_counts[source] = initial_source_counts.get(source, 0) + 1
        logger.info(f"Initial source distribution before processing for '{event}': {initial_source_counts}")
        logger.info(f"Initial total articles: {len(all_articles)}")

        duplicate_start = time.time()
        logger.info(f"Starting duplicate removal for event '{event}' at {duplicate_start}")
        unique_articles = remove_duplicates(all_articles)
        
        after_dedup_counts = {}
        for article in unique_articles:
            source = article.get('source', 'Unknown')
            after_dedup_counts[source] = after_dedup_counts.get(source, 0) + 1
        logger.info(f"Source distribution after duplicate removal for '{event}': {after_dedup_counts}")
        logger.info(f"Articles removed by deduplication: {len(all_articles) - len(unique_articles)}")
        duplicate_time = time.time() - duplicate_start
        logger.info(f"Duplicate removal took {duplicate_time:.2f} seconds for event '{event}'")

        filter_start = time.time()
        logger.info(f"Starting filtering for event '{event}' at {filter_start}")
        relevant_articles = filter_relevant_articles(unique_articles, event)
        
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

        group_and_cap_start = time.time()
        logger.info(f"Starting grouping and capping for event '{event}' at {group_and_cap_start}")
        source_groups = {}
        for article in relevant_articles:
            source = article.get('source', 'Unknown')
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(article)
        
        logger.info(f"Articles per source before capping for '{event}':")
        for source, articles_list in source_groups.items():
            logger.info(f"- {source}: {len(articles_list)} articles")
        
        num_sources = len(source_groups)
        
        # Use increased_top_n if available (for problematic queries)
        top_n_value = increased_top_n if 'increased_top_n' in locals() else DEFAULT_TOP_N
        
        # Modified dynamic cap formula to allow more articles per source when there are fewer sources
        # Using formula: min(MAX_ARTICLES_PER_SOURCE, max(3, top_n_value // max(1, num_sources - 1)))
        dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(3, top_n_value // max(1, num_sources - 1)))
        logger.info(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
        logger.info(f"Total slots available: {top_n_value}")
        logger.info(f"DIAGNOSTIC: MAX_ARTICLES_PER_SOURCE={MAX_ARTICLES_PER_SOURCE}, DEFAULT_TOP_N={top_n_value}")
        logger.info(f"DIAGNOSTIC: Modified formula: min({MAX_ARTICLES_PER_SOURCE}, max(3, {top_n_value} // max(1, {num_sources} - 1))) = {dynamic_cap}")
        
        final_articles = []
        remaining_slots = top_n_value
        
        first_round_sources = []
        for source, articles_list in source_groups.items():
            if articles_list and remaining_slots > 0:
                final_articles.append(articles_list[0])
                articles_list.pop(0)
                remaining_slots -= 1
                first_round_sources.append(source)
        logger.info(f"First round distribution - Added one article from each of these sources: {first_round_sources}")
        logger.info(f"Remaining slots after first round: {remaining_slots}")
        
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
                return None, None, error_message

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

        source_counts = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        logger.info(f"Source distribution for event '{event}' after capping: {source_counts}")

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
        
        # Add diagnostic logging to trace article count
        logger.info(f"DIAGNOSTIC: Final article count before response creation: {len(articles)}")
        for i, article in enumerate(articles[:10]):  # Log up to 10 articles
            logger.info(f"DIAGNOSTIC: Article {i+1}: '{article.get('title', 'No title')[:40]}...' - Source: {article.get('source', 'Unknown')}")
        
        return summary, relevant_articles, None
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Exception occurred, total time: {total_time:.2f} seconds, error: {str(e)}, ending at {time.time()}", exc_info=True)
        return None, None, f"An unexpected error occurred while processing '{event}'. Please try again later."

@routes.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main route for displaying trending topics and fetching custom summaries."""
    logger.info("=== Template Debug Info ===")
    logger.info(f"Current working directory: {os.getcwd()}")
    template_folder = current_app.template_folder
    template_path = os.path.join(template_folder, 'index.html')
    logger.info(f"Template folder path: {template_folder}")
    logger.info(f"Full template path: {template_path}")
    logger.info(f"Template exists: {os.path.exists(template_path)}")
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
            logger.info(f"Template file size: {len(content)} bytes")
            logger.info("Template content preview:")
            for i, line in enumerate(content.split('\n')[:20]):
                logger.info(f"Line {i+1}: {line}")
    except Exception as e:
        logger.error(f"Error reading template: {e}")
    logger.info("========================")

    logger.info("Route / accessed")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {request.form}")

    today = datetime.now().strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    last_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    today_topics = get_trending_topics("today")
    logger.info(f"Today topics sample: {today_topics[0] if today_topics else 'None'}")
    
    last_week_topics = get_trending_topics("last_week")
    logger.info(f"Last week topics sample: {last_week_topics[0] if last_week_topics else 'None'}")
    
    last_month_topics = get_trending_topics("last_month")
    logger.info(f"Last month topics sample: {last_month_topics[0] if last_month_topics else 'None'}")
    
    are_same = today_topics[0][0] == last_week_topics[0][0] if today_topics and last_week_topics else False
    logger.info(f"Today and last week topics are the same: {are_same}")
    
    summary = None
    articles = []
    event = None
    error = None
    image_path = None

    if request.method == 'POST':
        event = request.form.get('event')
        logger.info(f"POST request received with event: '{event}'")
        if not event:
            error = "Please enter a news event to search for."
            logger.warning("No event provided")
        else:
            logger.info(f"Processing event: '{event}'")
            conn = sqlite3.connect(get_db_path())
            c = conn.cursor()
            c.execute("""SELECT * FROM search_history 
                        WHERE query = ? AND timestamp > ?""", 
                     (event, (datetime.now() - timedelta(hours=24)).isoformat()))
            result = c.fetchone()
            
            if result:
                logger.info(f"Cache hit for '{event}' - Summary: {result[3][:50]}..., Image Path: {result[7]}")
                summary = result[3]
                articles = json.loads(result[5])
                image_path = result[7]
                if image_path and os.path.exists(image_path):
                    logger.info(f"Using cached image: {image_path}")
                else:
                    logger.warning(f"Cached image not found: {image_path}")
                    image_path = None
            else:
                logger.info(f"No cache hit for '{event}', processing request")
                summary, articles, error = process_news_request(event)
                
                if error:
                    logger.error(f"Error processing '{event}': {error}")
                else:
                    logger.info(f"Success processing '{event}': {summary[:50]}..., {len(articles)} articles")
                    
                    # Generate or fetch image for the topic
                    try:
                        image_path = generate_and_save_image("", event, True)
                        logger.info(f"Generated image: {image_path}")
                    except Exception as img_error:
                        logger.error(f"Failed to generate image: {img_error}")
                        image_path = None
                        
            conn.close()

    # Get trending topics for different time periods
    today_topics = get_trending_topics("today")
    last_week_topics = get_trending_topics("last_week")
    last_month_topics = get_trending_topics("last_month")
    
    # Log the lengths of trending topics
    logger.info(f"Rendering template with trending topics - Today: {len(today_topics)}, Last Week: {len(last_week_topics)}, Last Month: {len(last_month_topics)}")
    
    return render_template('index.html', 
                          summary=summary, 
                          articles=articles, 
                          event=event,
                          error=error,
                          image_path=image_path,
                          today_topics=today_topics,
                          last_week_topics=last_week_topics,
                          last_month_topics=last_month_topics)

def process_news_request(event, include_images=True):
    """Process a news data request."""
    try:
        logger.info(f"Starting process_news_request for '{event}' with include_images={include_images} (type: {type(include_images)})")
        
        # Additional checks
        if not event:
            logger.warning("Empty event query received")
            return [], "", "Please enter a search query."

        logger.info(f"Checking cache for '{event}'")
        
        # Get DB_PATH from multiple sources
        db_path = get_db_path()
        
        logger.info(f"Using DB_PATH: {db_path}")
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""SELECT * FROM search_history 
                    WHERE query = ? AND timestamp > ?""", 
                 (event, (datetime.now() - timedelta(hours=24)).isoformat()))
        result = c.fetchone()
        
        if result:
            logger.info(f"Cache hit for '{event}' - Summary: {result[3][:50]}..., Image Path: {result[7]}")
            image_path = result[7] if include_images else None
            logger.info(f"Initial image_path after cache hit: {image_path} (include_images={include_images})")
            
            if image_path and os.path.exists(image_path):
                logger.info(f"Existing image found at {image_path}")
                image_filename = os.path.basename(image_path)
                image_path = f"/images/{image_filename}"  # Convert to relative URL
                logger.info(f"Converted to relative URL: {image_path}")
            else:
                if include_images:
                    logger.info(f"No valid image in cache or on disk, generating for '{event}'")
                    image_path, image_status = generate_and_save_image(result[3], event, include_images)
                    logger.info(f"Image generation returned: path={image_path}, status={image_status}")
                    
                    if image_status:
                        logger.info(f"Generated new image: {image_path}")
                        image_filename = os.path.basename(image_path)
                        image_path = f"/images/{image_filename}"  # Convert to relative URL
                        logger.info(f"Converted to relative URL: {image_path}")
                        c.execute("UPDATE search_history SET image_path = ? WHERE query = ?", (image_path, event))
                        conn.commit()
                    else:
                        logger.warning(f"Image generation failed for cached entry '{event}'")
                        image_path = None
                else:
                    logger.info("Image generation skipped because include_images=False")
                    image_path = None
            
            data = {
                'success': True,
                'summary': result[3],
                'articles': json.loads(result[5]),
                'metadata': {
                    'average_sentiment': result[4],
                    'source_distribution': json.loads(result[6]),
                    'image': {
                        'path': image_path if include_images else None,
                        'generated': bool(image_path)
                    } if include_images else None
                }
            }
            conn.close()
            return data, 200
        
        # Not in cache, need to fetch from APIs
        start_time = time.time()
        logger.info(f"Starting request processing for '{event}' at {start_time}")
        
        logger.info(f"NEWSAPI_ORG_KEY: {'Available' if NEWSAPI_ORG_KEY else 'Missing'}")
        logger.info(f"GUARDIAN_API_KEY: {'Available' if GUARDIAN_API_KEY else 'Missing'}")
        logger.info(f"GNEWS_API_KEY: {'Available' if GNEWS_API_KEY else 'Missing'}")
        logger.info(f"NYT_API_KEY: {'Available' if NYT_API_KEY else 'Missing'}")
        logger.info(f"OPENAI_API_KEY: {'Available' if OPENAI_API_KEY else 'Missing'}")
        logger.info(f"MEDIASTACK_API_KEY: {'Available' if MEDIASTACK_API_KEY else 'Missing'}")
        logger.info(f"NEWSDATA_API_KEY: {'Available' if NEWSDATA_API_KEY else 'Missing'}")
        logger.info(f"AYLIEN keys: {'Available' if AYLIEN_APP_ID and AYLIEN_API_KEY else 'Missing'}")
        
        try:
            fetch_start = time.time()
            logger.info(f"Beginning API fetch for event '{event}' at {fetch_start}")
            
            # Run async fetch in an executor to avoid blocking Flask
            loop = asyncio.new_event_loop()
            
            def run_async_fetch():
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(async_fetch_articles(event))
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                results = executor.submit(run_async_fetch).result()
            
            newsapi_org_articles, guardian_articles, aylien_articles, gnews_articles, nyt_articles, mediastack_articles, newsapi_ai_articles = results
            
            fetch_time = time.time() - fetch_start
            logger.info(f"API Fetching took {fetch_time:.2f} seconds for event '{event}'")

            logger.info(f"Articles retrieved for event '{event}': "
                      f"NewsAPI.org: {len(newsapi_org_articles)}, "
                      f"Guardian: {len(guardian_articles)}, "
                      f"Aylien: {len(aylien_articles)}, "
                      f"GNews: {len(gnews_articles)}, "
                      f"NYT: {len(nyt_articles)}, "
                      f"Mediastack: {len(mediastack_articles)}, "
                      f"NewsAPI.ai: {len(newsapi_ai_articles)}")

            # Add debug logging for USE_* variables
            try:
                logger.info("Checking availability of API configuration flags:")
                logger.info(f"USE_NEWSAPI_ORG defined: {'Yes' if 'USE_NEWSAPI_ORG' in globals() else 'No'}")
                logger.info(f"USE_GUARDIAN defined: {'Yes' if 'USE_GUARDIAN' in globals() else 'No'}")
                logger.info(f"USE_AYLIEN defined: {'Yes' if 'USE_AYLIEN' in globals() else 'No'}")
                logger.info(f"USE_GNEWS defined: {'Yes' if 'USE_GNEWS' in globals() else 'No'}")
                logger.info(f"USE_NYT defined: {'Yes' if 'USE_NYT' in globals() else 'No'}")
                logger.info(f"USE_MEDIASTACK defined: {'Yes' if 'USE_MEDIASTACK' in globals() else 'No'}")
                logger.info(f"USE_NEWSDATA defined: {'Yes' if 'USE_NEWSDATA' in globals() else 'No'}")
                
                # Try importing directly from config
                from config_prod import USE_NEWSAPI_ORG, USE_GUARDIAN, USE_AYLIEN, USE_GNEWS, USE_NYT, USE_MEDIASTACK, USE_NEWSDATA
                logger.info("Successfully imported USE_* flags from config_prod")
            except Exception as e:
                logger.error(f"Error importing USE_* flags: {str(e)}")
                # Define fallback values if imports fail
                USE_NEWSAPI_ORG = NEWSAPI_ORG_KEY is not None
                USE_GUARDIAN = GUARDIAN_API_KEY is not None
                USE_AYLIEN = AYLIEN_APP_ID is not None and AYLIEN_API_KEY is not None
                USE_GNEWS = GNEWS_API_KEY is not None
                USE_NYT = NYT_API_KEY is not None
                USE_MEDIASTACK = MEDIASTACK_API_KEY is not None
                USE_NEWSDATA = NEWSDATA_API_KEY is not None
                logger.info("Using fallback values for USE_* flags based on API key availability")
                
            # Identify failed sources
            failed_sources = []
            if not newsapi_org_articles and USE_NEWSAPI_ORG:
                failed_sources.append("NewsAPI.org")
            if not guardian_articles and USE_GUARDIAN:
                failed_sources.append("Guardian")
            if not aylien_articles and USE_AYLIEN:
                failed_sources.append("Aylien")
            if not gnews_articles and USE_GNEWS:
                failed_sources.append("GNews")
            if not nyt_articles and USE_NYT:
                failed_sources.append("NYT")
            if not mediastack_articles and USE_MEDIASTACK:
                failed_sources.append("Mediastack")
            if not newsapi_ai_articles and USE_NEWSDATA:
                failed_sources.append("NewsAPI.ai")
            
            # Calculate success rate
            enabled_sources = sum([USE_NEWSAPI_ORG, USE_GUARDIAN, USE_AYLIEN, USE_GNEWS, 
                                  USE_NYT, USE_MEDIASTACK, USE_NEWSDATA])
            successful_sources = enabled_sources - len(failed_sources)
            success_rate = successful_sources / enabled_sources if enabled_sources > 0 else 0
            
            if failed_sources:
                logger.warning(f"The following sources failed to return results: {', '.join(failed_sources)}")
                logger.warning(f"Source success rate: {success_rate:.2%}")
            
            # Handle critical failure scenario - almost all sources failed
            if success_rate < 0.25 and enabled_sources > 2:
                logger.error(f"Critical failure rate: {success_rate:.2%}")
                # If we have an extremely low success rate, we should inform the user
                # But we'll still try to proceed with what we have
                if success_rate == 0:
                    logger.error("All news sources failed to return results")
                    # Create a more user-friendly response
                    fallback_data = {
                        'success': False,
                        'error': "We're experiencing technical difficulties reaching our news sources. Please try again later.",
                        'articles': [],
                        'summary': "Due to technical issues, we couldn't fetch the latest news at this time. Please try again in a few minutes.",
                        'metadata': {
                            'average_sentiment': 0,
                            'source_distribution': {},
                            'image': None
                        },
                        'technical_details': {
                            'failed_sources': failed_sources,
                            'enabled_sources': enabled_sources,
                            'success_rate': success_rate
                        }
                    }
                    conn.close()
                    return fallback_data, 503  # Service Unavailable

            total_fetched = (len(newsapi_org_articles) + len(guardian_articles) + 
                            len(aylien_articles) + len(gnews_articles) +
                            len(nyt_articles) + len(mediastack_articles) + 
                            len(newsapi_ai_articles))
            logger.info(f"Total articles fetched for event '{event}': {total_fetched}")
            if total_fetched == 0:
                total_time = time.time() - start_time
                logger.info(f"Total request time (no articles): {total_time:.2f} seconds, ending at {time.time()}")
                # Create a more user-friendly response
                fallback_data = {
                    'success': False,
                    'warning': f"No articles found for '{event}' in the past 7 days. Try a broader topic.",
                    'articles': [],
                    'summary': f"We couldn't find any recent news articles about '{event}'. Try a different search term or check back later.",
                    'metadata': {
                        'average_sentiment': 0,
                        'source_distribution': {},
                        'image': None
                    }
                }
                conn.close()
                return fallback_data, 200

            # Continue with existing processing code
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
            
            # If we got this far but have some failed sources, add a note to the response
            warning_message = None
            if failed_sources:
                warning_message = "Some news sources were unavailable. Showing results from available sources."
                if success_rate < 0.5:
                    warning_message = "Several news sources were unavailable. Results may be limited."
            
            # Skip sentiment analysis, just set sentiment_score to 0 for all articles
            logger.info(f"Skipping sentiment analysis for {len(all_articles)} articles")
            sentiment_start = time.time()
            for article in all_articles:
                article['sentiment_score'] = 0
            sentiment_time = time.time() - sentiment_start
            logger.info(f"Sentiment processing (removed) took {sentiment_time:.2f} seconds")
            
            standardize_time = time.time() - standardize_start
            logger.info(f"Standardization took {standardize_time:.2f} seconds for event '{event}'")

            initial_source_counts = {}
            for article in all_articles:
                source = article.get('source', 'Unknown')
                initial_source_counts[source] = initial_source_counts.get(source, 0) + 1
            logger.info(f"Initial source distribution before processing for '{event}': {initial_source_counts}")
            logger.info(f"Initial total articles: {len(all_articles)}")

            duplicate_start = time.time()
            logger.info(f"Starting duplicate removal for event '{event}' at {duplicate_start}")
            unique_articles = remove_duplicates(all_articles)
            
            after_dedup_counts = {}
            for article in unique_articles:
                source = article.get('source', 'Unknown')
                after_dedup_counts[source] = after_dedup_counts.get(source, 0) + 1
            logger.info(f"Source distribution after duplicate removal for '{event}': {after_dedup_counts}")
            logger.info(f"Articles removed by deduplication: {len(all_articles) - len(unique_articles)}")
            duplicate_time = time.time() - duplicate_start
            logger.info(f"Duplicate removal took {duplicate_time:.2f} seconds for event '{event}'")

            filter_start = time.time()
            logger.info(f"Starting filtering for event '{event}' at {filter_start}")
            relevant_articles = filter_relevant_articles(unique_articles, event)
            
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
                return {'warning': f"No relevant articles found for '{event}' after filtering. Try a broader topic."}, 200

            group_and_cap_start = time.time()
            logger.info(f"Starting grouping and capping for event '{event}' at {group_and_cap_start}")
            source_groups = {}
            for article in relevant_articles:
                source = article.get('source', 'Unknown')
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(article)
            
            logger.info(f"Articles per source before capping for '{event}':")
            for source, articles_list in source_groups.items():
                logger.info(f"- {source}: {len(articles_list)} articles")
            
            num_sources = len(source_groups)
            
            # Use increased_top_n if available (for problematic queries)
            top_n_value = increased_top_n if 'increased_top_n' in locals() else DEFAULT_TOP_N
            
            # Modified dynamic cap formula to allow more articles per source when there are fewer sources
            # Using formula: min(MAX_ARTICLES_PER_SOURCE, max(3, top_n_value // max(1, num_sources - 1)))
            dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(3, top_n_value // max(1, num_sources - 1)))
            logger.info(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
            logger.info(f"Total slots available: {top_n_value}")
            logger.info(f"DIAGNOSTIC: MAX_ARTICLES_PER_SOURCE={MAX_ARTICLES_PER_SOURCE}, DEFAULT_TOP_N={top_n_value}")
            logger.info(f"DIAGNOSTIC: Modified formula: min({MAX_ARTICLES_PER_SOURCE}, max(3, {top_n_value} // max(1, {num_sources} - 1))) = {dynamic_cap}")
            
            final_articles = []
            remaining_slots = top_n_value
            
            first_round_sources = []
            for source, articles_list in source_groups.items():
                if articles_list and remaining_slots > 0:
                    final_articles.append(articles_list[0])
                    articles_list.pop(0)
                    remaining_slots -= 1
                    first_round_sources.append(source)
            logger.info(f"First round distribution - Added one article from each of these sources: {first_round_sources}")
            logger.info(f"Remaining slots after first round: {remaining_slots}")
            
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
            
            # Generate image for the event
            logger.info(f"Generating image for event '{event}'")
            image_path, image_status = generate_and_save_image(summary, event, include_images)
            if image_status:
                logger.info(f"Image generation successful: {image_path}")
                image_filename = os.path.basename(image_path)
                image_path = f"/images/{image_filename}"  # Convert to relative URL
            else:
                logger.warning(f"Image generation failed for event '{event}'")
                image_path = None
            
            # Store in database for caching
            try:
                # Set sentiment score to 0 as we've removed sentiment analysis
                avg_sentiment = 0
                logger.info(f"Storing result in database for '{event}'")
                c.execute("""INSERT INTO search_history 
                             (query, timestamp, summary, average_sentiment, 
                              articles, source_distribution, image_path) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                          (event, datetime.now().isoformat(), summary, 
                           avg_sentiment, json.dumps(articles), 
                           json.dumps(final_source_counts), image_path))
                conn.commit()
            except Exception as db_error:
                logger.error(f"Error storing results in database: {db_error}")
            finally:
                conn.close()
            
            # Return response with appropriate warning if sources failed
            total_time = time.time() - start_time
            logger.info(f"Total request time: {total_time:.2f} seconds, ending at {time.time()}")
            
            # Add diagnostic logging to trace article count
            logger.info(f"DIAGNOSTIC: Final article count before response creation: {len(articles)}")
            for i, article in enumerate(articles[:10]):  # Log up to 10 articles
                logger.info(f"DIAGNOSTIC: Article {i+1}: '{article.get('title', 'No title')[:40]}...' - Source: {article.get('source', 'Unknown')}")
            
            # Build image metadata structure based on include_images flag
            image_metadata = None
            if include_images:
                image_metadata = {
                    'path': image_path,
                    'generated': bool(image_path)
                }
            
            if warning_message:
                return {
                    'success': True, 
                    'summary': summary, 
                    'articles': articles,
                    'warning': warning_message,
                    'metadata': {
                        'average_sentiment': avg_sentiment,
                        'source_distribution': final_source_counts,
                        'image': image_metadata,
                        'source_health': {
                            'success_rate': success_rate,
                            'failed_sources': failed_sources,
                            'successful_sources': successful_sources
                        }
                    }
                }, 200
            else:
                return {'success': True, 'summary': summary, 'articles': articles, 'metadata': {
                    'average_sentiment': avg_sentiment,
                    'source_distribution': final_source_counts,
                    'image': image_metadata
                }}, 200
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                'error': f"An error occurred while processing your request.",
                'details': str(e) if current_app.config.get("DEBUG", False) else "Please try again later."
            }, 500
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            'error': f"An error occurred while processing your request.",
            'details': str(e) if current_app.config.get("DEBUG", False) else "Please try again later."
        }, 500

@routes.route('/data', methods=['POST'])
def get_news_data():
    """Handle news data requests"""
    try:
        # Get the search query and image toggle state
        event = request.form.get('event') or request.json.get('event')
        
        # More robust handling of include_images parameter with extensive error handling
        try:
            raw_include_images = request.form.get('include_images')
            logger.info(f"Received include_images raw value: '{raw_include_images}' (type: {type(raw_include_images).__name__})")
            
            # Parse include_images in a more robust way with clear error handling
            try:
                if raw_include_images is None:
                    include_images = request.json.get('include_images', True)
                    logger.info(f"Using JSON parameter or default: {include_images}")
                else:
                    # Convert various true values to boolean True
                    if isinstance(raw_include_images, bool):
                        include_images = raw_include_images
                        logger.info(f"Using boolean value directly: {include_images}")
                    else:
                        # Handle string values safely
                        try:
                            include_images = str(raw_include_images).lower() in ('true', 't', 'yes', 'y', '1')
                            logger.info(f"Parsed string value to boolean: {include_images}")
                        except Exception as str_error:
                            logger.error(f"Error parsing string value: {str_error}")
                            include_images = True  # Default to True on error
                            logger.info(f"Using default value after string parsing error: {include_images}")
            except Exception as parse_error:
                logger.error(f"Error in include_images parsing: {parse_error}")
                include_images = True  # Default to True on error
                logger.info(f"Using default value after parsing error: {include_images}")
        except Exception as param_error:
            logger.error(f"Error extracting include_images parameter: {param_error}")
            include_images = True  # Default to True on error
            logger.info(f"Using default value after parameter error: {include_images}")
        
        logger.info(f"Final include_images value: {include_images} (type: {type(include_images).__name__})")
        logger.info(f"Received request for event '{event}' with include_images={include_images}")
        
        if not event:
            logger.error("No event provided in request")
            return jsonify({"error": "Please provide an event to search for."}), 400
        
        # Process the request
        try:
            result = process_news_request(event, include_images)
            
            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
                if 'error' in data:
                    logger.error(f"Error in process_news_request: {data['error']}")
                    return jsonify(data), status_code
                articles = data.get('articles', [])
                summary = data.get('summary', '')
                logger.info(f"process_news_request returned: articles={len(articles) if articles else 0}, summary={'present' if summary else 'none'}")
                
                # Ensure metadata is properly set
                if 'metadata' not in data:
                    data['metadata'] = {
                        'average_sentiment': 0,
                        'source_distribution': {},
                        'image': None
                    }
                    logger.warning(f"Added missing metadata to response")
            else:
                articles, summary, error = result
                logger.info(f"process_news_request returned: articles={len(articles) if articles else 0}, summary={'present' if summary else 'none'}, error={error}")
                if error:
                    logger.error(f"Error processing request: {error}")
                    return jsonify({'error': error}), 400
                
                # Create a proper response structure
                data = {
                    'articles': articles,
                    'summary': summary,
                    'metadata': {
                        'average_sentiment': 0,
                        'source_distribution': {},
                        'image': None
                    }
                }
                logger.info(f"Created fallback response structure")
                
        except Exception as process_error:
            logger.error(f"Error in process_news_request: {str(process_error)}", exc_info=True)
            # Create a safe fallback response
            return jsonify({
                'error': f"Internal processing error: {str(process_error)}",
                'articles': [],
                'summary': f"Error retrieving news for '{event}'. Please try again later.",
                'metadata': {
                    'average_sentiment': 0,
                    'source_distribution': {},
                    'image': None
                }
            }), 500
        
        # Log the response data
        logger.info(f"Returning response with {len(data.get('articles', [])) if 'articles' in data and isinstance(data['articles'], list) else 0} articles")
        if 'metadata' in data and 'image' in data['metadata'] and data['metadata']['image']:
            logger.info(f"Image in response: {data['metadata']['image']}")
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Unexpected error in get_news_data: {str(e)}", exc_info=True)
        # Create a safe fallback response
        return jsonify({
            'error': f"An unexpected error occurred: {str(e)}",
            'articles': [],
            'summary': "",
            'metadata': {
                'average_sentiment': 0,
                'source_distribution': {},
                'image': None
            }
        }), 500

@routes.route('/images/<filename>')
def serve_image(filename):
    """Serve an image file from the image directory."""
    try:
        logger.info(f"Serving image: {filename} from {current_app.config['IMAGE_DIRECTORY']}")
        return send_from_directory(current_app.config["IMAGE_DIRECTORY"], filename)
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        return jsonify({"error": "Image not found"}), 404

@routes.route('/health', methods=['GET'])
def health_check():
    """
    Enhanced health check endpoint for monitoring application health in production.
    Tests database connectivity, API access, and returns version and uptime information.
    """
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': os.environ.get('APP_VERSION', 'dev'),
        'checks': {},
        'uptime': time.time() - current_app.start_time if hasattr(current_app, 'start_time') else None
    }
    
    # Check database connectivity
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM search_history")
            search_count = cursor.fetchone()[0]
            health_status['checks']['database'] = {
                'status': 'pass',
                'message': f"Connected to database, {search_count} searches"
            }
        except sqlite3.OperationalError as db_error:
            health_status['checks']['database'] = {
                'status': 'warn',
                'message': f"Connected but {str(db_error)}"
            }
            # Create the required tables if they don't exist
            cursor.execute('''CREATE TABLE IF NOT EXISTS search_history
                          (id INTEGER PRIMARY KEY, query TEXT NOT NULL, timestamp DATETIME NOT NULL,
                          summary TEXT, average_sentiment REAL, articles TEXT, source_distribution TEXT, 
                          image_path TEXT, search_count INTEGER DEFAULT 1)''')
            conn.commit()
        conn.close()
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'fail',
            'message': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check image directory
    try:
        img_dir = os.path.join(os.path.dirname(get_db_path()), "images")
        if os.path.exists(img_dir) and os.access(img_dir, os.W_OK):
            try:
                stats = get_image_cache_stats()
                if 'count' in stats:
                    health_status['checks']['image_cache'] = {
                        'status': 'pass',
                        'message': f"{stats['count']} images, {stats['size_mb']:.1f}MB"
                    }
                else:
                    # Fallback to directory count
                    count = len([f for f in os.listdir(img_dir) if f.endswith('.webp')])
                    size_mb = sum(os.path.getsize(os.path.join(img_dir, f)) for f in os.listdir(img_dir) if f.endswith('.webp')) / (1024 * 1024)
                    health_status['checks']['image_cache'] = {
                        'status': 'pass',
                        'message': f"{count} images, {size_mb:.1f}MB (from directory)"
                    }
            except Exception as cache_error:
                # Fallback to directory count on error
                count = len([f for f in os.listdir(img_dir) if f.endswith('.webp')])
                size_mb = sum(os.path.getsize(os.path.join(img_dir, f)) for f in os.listdir(img_dir) if f.endswith('.webp')) / (1024 * 1024)
                health_status['checks']['image_cache'] = {
                    'status': 'warn',
                    'message': f"{count} images, {size_mb:.1f}MB (fallback: {str(cache_error)})"
                }
        else:
            health_status['checks']['image_cache'] = {
                'status': 'fail',
                'message': "Image directory missing or not writable"
            }
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['image_cache'] = {
            'status': 'fail',
            'message': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check API keys
    api_keys = {
        'NEWSAPI_ORG_KEY': NEWSAPI_ORG_KEY,
        'GUARDIAN_API_KEY': GUARDIAN_API_KEY,
        'GNEWS_API_KEY': GNEWS_API_KEY,
        'NYT_API_KEY': NYT_API_KEY,
        'MEDIASTACK_API_KEY': MEDIASTACK_API_KEY,
        'NEWSDATA_API_KEY': NEWSDATA_API_KEY
    }
    
    missing_keys = [name for name, key in api_keys.items() if not key]
    if missing_keys:
        health_status['checks']['api_keys'] = {
            'status': 'warn',
            'message': f"Missing keys: {', '.join(missing_keys)}"
        }
        if len(missing_keys) > 3:  # If more than half of the keys are missing
            health_status['status'] = 'degraded'
    else:
        health_status['checks']['api_keys'] = {
            'status': 'pass',
            'message': "All API keys present"
        }
    
    # Check memory usage (if psutil is available)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        health_status['checks']['memory'] = {
            'status': 'pass',
            'message': f"{memory_mb:.1f}MB in use"
        }
    except ImportError:
        # psutil not installed, skip this check
        pass
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'warn',
            'message': str(e)
        }
    
    # Add response time
    health_status['response_time_ms'] = (time.time() - start_time) * 1000
    
    # Set appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 207  # 207 Multi-Status
    
    # Log health check
    logger.info(f"Health check: {health_status['status']} in {health_status['response_time_ms']:.1f}ms")
    
    return jsonify(health_status), status_code

@routes.route('/admin/image-cache', methods=['GET', 'POST'])
def image_cache_admin():
    """Admin endpoint for image cache management"""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'optimize':
            # Get the image cache instance
            from image_cache import get_instance
            cache = get_instance(
                db_path=get_db_path(),
                image_dir=current_app.config["IMAGE_DIRECTORY"]
            )
            # Run optimization with parameters from form
            max_age = int(request.form.get('max_age', 30))
            target_size = int(request.form.get('target_size', 500))
            optimize_image_storage(max_age_days=max_age, target_size_mb=target_size)
            return jsonify({
                'status': 'success',
                'message': f'Optimization started with max_age={max_age}, target_size={target_size}MB'
            })
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
    
    # Get current stats
    stats = get_image_cache_stats()
    
    # Calculate directory size
    image_dir = current_app.config["IMAGE_DIRECTORY"]
    dir_size = 0
    file_count = 0
    
    for path, dirs, files in os.walk(image_dir):
        for f in files:
            if f.endswith('.png'):
                fp = os.path.join(path, f)
                file_count += 1
                dir_size += os.path.getsize(fp)
    
    stats['directory_size_mb'] = dir_size / (1024 * 1024)
    stats['file_count'] = file_count
    
    # Get some sample entries from cache sorted by search count
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("""
        SELECT query, image_path, search_count FROM search_history 
        WHERE image_path IS NOT NULL
        ORDER BY search_count DESC
        LIMIT 10
    """)
    top_searches = [{'query': row[0], 'path': row[1], 'count': row[2]} for row in c.fetchall()]
    conn.close()
    
    return jsonify({
        'stats': stats,
        'top_searches': top_searches,
        'timestamp': datetime.now().isoformat()
    })

def init_db():
    """Initialize the SQLite database with image_path column."""
    logger.info("Starting init_db function in routes.py")
    
    try:
        # Try multiple sources for DB_PATH, in order of preference
        db_path = get_db_path()
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        try:
            c.execute('''CREATE TABLE IF NOT EXISTS search_history
                         (query TEXT, timestamp TEXT, summary TEXT, average_sentiment REAL,
                          articles TEXT, source_distribution TEXT, image_path TEXT)''')
            logger.info("Created search_history table if it didn't exist")
        except sqlite3.OperationalError:
            logger.info("search_history table already exists")
        try:
            c.execute('''ALTER TABLE search_history 
                         ADD COLUMN image_path TEXT''')
            logger.info("Added image_path column to search_history")
        except sqlite3.OperationalError:
            logger.info("image_path column already exists")
        try:
            c.execute('''ALTER TABLE search_history 
                         ADD COLUMN search_count INTEGER DEFAULT 1''')
            logger.info("Added search_count column to search_history")
        except sqlite3.OperationalError:
            logger.info("search_count column already exists")
            
        conn.commit()
        conn.close()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error in init_db: {str(e)}")
        raise

@routes.route('/analytics', methods=['POST'])
def log_analytics():
    try:
        data = request.get_json()
        
        # Get DB path
        db_path = current_app.config.get('DB_PATH')
        if not db_path:
            db_path = os.environ.get('DB_PATH', 'search_db.sqlite')
            
        # Connect to database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create analytics table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS analytics
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     event_type TEXT NOT NULL,
                     event_data TEXT NOT NULL,
                     timestamp TEXT NOT NULL)''')
        
        # Insert analytics data
        c.execute('INSERT INTO analytics (event_type, event_data, timestamp) VALUES (?, ?, ?)',
                 (data['event_type'], 
                  json.dumps(data['data']), 
                  datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        current_app.logger.error(f"Error logging analytics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@routes.route('/analytics-dashboard')
def analytics_dashboard():
    """Display analytics data in a dashboard format."""
    try:
        # Get DB path
        db_path = current_app.config.get('DB_PATH')
        if not db_path:
            db_path = os.environ.get('DB_PATH', 'search_db.sqlite')
            
        # Connect to database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get top searches (only manual searches)
        c.execute('''
            SELECT json_extract(event_data, '$.query') as search_query, COUNT(*) as count 
            FROM analytics 
            WHERE event_type = 'search'
            GROUP BY search_query 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_searches = c.fetchall()
        
        # Get top hot topics clicked
        c.execute('''
            SELECT json_extract(event_data, '$.topic') as topic, 
                   json_extract(event_data, '$.category') as category,
                   COUNT(*) as count 
            FROM analytics 
            WHERE event_type = 'hot_topic_click'
            GROUP BY topic, category
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_hot_topics = c.fetchall()
        
        # Get most clicked articles
        c.execute('''
            SELECT json_extract(event_data, '$.title') as article_title, 
                   json_extract(event_data, '$.source') as source,
                   COUNT(*) as clicks 
            FROM analytics 
            WHERE event_type = 'article_click'
            GROUP BY article_title, source
            ORDER BY clicks DESC 
            LIMIT 10
        ''')
        top_articles = c.fetchall()
        
        # Get average session duration
        c.execute('''
            SELECT AVG(CAST(json_extract(event_data, '$.duration_ms') AS INTEGER))/1000.0 as avg_session_seconds 
            FROM analytics 
            WHERE event_type = 'session_end'
        ''')
        avg_session_duration = c.fetchone()[0]
        
        # Get feature usage
        c.execute('''
            SELECT json_extract(event_data, '$.feature') as feature, COUNT(*) as views 
            FROM analytics 
            WHERE event_type = 'feature_view'
            GROUP BY feature
        ''')
        feature_usage = c.fetchall()
        
        # Get API performance
        c.execute('''
            SELECT 
                json_extract(event_data, '$.endpoint') as endpoint,
                AVG(CAST(json_extract(event_data, '$.response_time_ms') AS INTEGER)) as avg_response_time,
                COUNT(*) as calls,
                SUM(CASE WHEN json_extract(event_data, '$.success') = 'true' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM analytics 
            WHERE event_type = 'api_response'
            GROUP BY endpoint
        ''')
        api_stats = c.fetchall()
        
        conn.close()
        
        return render_template('analytics_dashboard.html',
                             top_searches=top_searches or [],
                             top_hot_topics=top_hot_topics or [],
                             top_articles=top_articles or [],
                             avg_session_duration=avg_session_duration or 0,
                             feature_usage=feature_usage or [],
                             api_stats=api_stats or [])
                             
    except Exception as e:
        current_app.logger.error(f"Error in analytics dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@routes.route('/favicon.ico')
def favicon():
    """Serve the favicon from the static folder."""
    return current_app.send_static_file('favicon/favicon.svg')

@routes.route('/admin/budget-status')
def budget_status():
    """Admin endpoint to view budget status for Stability AI."""
    from budget_control import get_budget_summary, MONTHLY_BUDGET_USD, COST_PER_IMAGE_USD, MAX_MONTHLY_GENERATIONS
    import json
    from flask import jsonify
    from datetime import datetime
    
    # Get budget info
    budget_info = get_budget_summary()
    
    # Add more helpful data
    days_in_current_month = (datetime.now().replace(day=28) + timedelta(days=4)).replace(day=1).replace(day=1) - timedelta(days=1)
    days_in_current_month = days_in_current_month.day
    days_passed = datetime.now().day
    days_remaining = days_in_current_month - days_passed
    
    # Calculate run rate and estimates
    if days_passed > 0:
        run_rate_per_day = budget_info['used'] / days_passed
        estimated_monthly_total = run_rate_per_day * days_in_current_month
    else:
        run_rate_per_day = 0
        estimated_monthly_total = 0
    
    # Format for display
    return jsonify({
        'status': 'ok',
        'budget_info': budget_info,
        'configuration': {
            'monthly_budget_usd': MONTHLY_BUDGET_USD,
            'cost_per_image_usd': COST_PER_IMAGE_USD,
            'max_monthly_generations': MAX_MONTHLY_GENERATIONS
        },
        'current_month': {
            'name': datetime.now().strftime('%B %Y'),
            'days_total': days_in_current_month,
            'days_passed': days_passed,
            'days_remaining': days_remaining,
            'percentage_of_month_passed': (days_passed / days_in_current_month) * 100
        },
        'usage': {
            'total_images': budget_info['used'],
            'remaining_images': budget_info['remaining'],
            'total_cost': f"${budget_info['total_cost']:.2f}",
            'remaining_budget': f"${budget_info['remaining_cost']:.2f}",
            'usage_percentage': f"{budget_info['percentage_used']:.1f}%",
            'run_rate_per_day': run_rate_per_day,
            'estimated_monthly_total': estimated_monthly_total,
            'on_budget': estimated_monthly_total <= MAX_MONTHLY_GENERATIONS
        },
        'message': f"Used {budget_info['used']}/{budget_info['limit']} images (${budget_info['total_cost']:.2f}/${budget_info['budget']:.2f})",
        'remaining': f"{budget_info['remaining']} images (${budget_info['remaining_cost']:.2f})",
        'budget_status': "Available" if budget_info['remaining'] > 0 else "Exhausted"
    })