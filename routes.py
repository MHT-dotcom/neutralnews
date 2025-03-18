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
                       summarize_articles, ModelManager)
from config_prod import (MAX_ARTICLES_PER_SOURCE, cache, NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, 
                        GNEWS_API_KEY, NYT_API_KEY, OPENAI_API_KEY, MEDIASTACK_API_KEY, 
                        NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY, DEFAULT_TOP_N)
from get_img import generate_and_save_image, get_image_cache_stats, optimize_image_storage

# Align blueprint name with app.py registration
routes = Blueprint('news_routes', __name__)
logger = logging.getLogger(__name__)

_is_first_request = True

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
        
        logger.info(f"Skipping sentiment analysis for {len(all_articles)} articles to avoid crashes")
        sentiment_start = time.time()
        for article in all_articles:
            article['sentiment_score'] = 0
        sentiment_time = time.time() - sentiment_start
        logger.info(f"Sentiment processing (disabled) took {sentiment_time:.2f} seconds")
        
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
        dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(2, DEFAULT_TOP_N // num_sources))
        logger.info(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
        logger.info(f"Total slots available: {DEFAULT_TOP_N}")
        
        final_articles = []
        remaining_slots = DEFAULT_TOP_N
        
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
        return summary, relevant_articles, None
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Exception occurred, total time: {total_time:.2f} seconds, error: {str(e)}, ending at {time.time()}", exc_info=True)
        try:
            ModelManager.get_instance().clear_models()
        except Exception as clear_error:
            logger.warning(f"Failed to clear models after error: {clear_error}")
        return None, None, f"An unexpected error occurred while processing '{event}'. Please try again later."

def get_trending_topics(date_str, force_refresh=False, time_period="current"):
    """Get trending topics for a given date"""
    logger.info("Returning static trending topics")
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
    if time_period == "last_week":
        return last_week_fallback_topics[:8]
    else:
        return current_fallback_topics[:8]

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
    
    today_topics = get_trending_topics(today, force_refresh=False, time_period="current")
    logger.info(f"Today topics sample: {today_topics[0] if today_topics else 'None'}")
    
    last_week_topics = get_trending_topics(last_week, force_refresh=False, time_period="last_week")
    logger.info(f"Last week topics sample: {last_week_topics[0] if last_week_topics else 'None'}")
    
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
            conn = sqlite3.connect(current_app.config["DB_PATH"])
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
                    logger.info(f"Existing image found at {image_path}")
                    image_filename = os.path.basename(image_path)
                    image_path = f"/images/{image_filename}"  # Convert to relative URL
                else:
                    logger.info(f"No valid image in cache or on disk, generating for '{event}'")
                    image_path, image_status = generate_and_save_image(event, summary)
                    if image_status:
                        logger.info(f"Generated new image: {image_path}")
                        image_filename = os.path.basename(image_path)
                        image_path = f"/images/{image_filename}"  # Convert to relative URL
                        c.execute("UPDATE search_history SET image_path = ? WHERE query = ?", (image_path, event))
                        conn.commit()
                    else:
                        logger.warning(f"Image generation failed")
                        image_path = None
                conn.close()
            else:
                result = fetch_and_process_data(event)
                if isinstance(result, tuple):
                    summary, articles, error = result
                else:
                    summary = result.get('summary')
                    articles = result.get('articles', [])
                if summary and not error:
                    image_path, image_status = generate_and_save_image(event, summary)
                    logger.info(f"Image generation result - Path: {image_path}, Status: {image_status}")
                    if image_status:
                        image_filename = os.path.basename(image_path)
                        image_path = f"/images/{image_filename}"  # Convert to relative URL
                conn.close()

    logger.info(f"Rendering template with: summary={summary is not None}, articles={len(articles)}, event='{event}', error='{error}', image_path='{image_path}'")
    return render_template(
        'index.html',
        today_topics=today_topics,
        last_week_topics=last_week_topics,
        summary=summary,
        articles=articles,
        event=event,
        error=error,
        image_path=image_path if image_path else None
    )

def process_news_request(event):
    """Process a news request for the given event, handling API calls and data formatting."""
    if not event:
        logger.warning("No event provided")
        return {'error': 'Please provide an event to search for.'}, 400

    logger.info(f"Checking cache for '{event}'")
    conn = sqlite3.connect(current_app.config["DB_PATH"])
    c = conn.cursor()
    c.execute("""SELECT * FROM search_history 
                WHERE query = ? AND timestamp > ?""", 
             (event, (datetime.now() - timedelta(hours=24)).isoformat()))
    result = c.fetchone()
    
    if result:
        logger.info(f"Cache hit for '{event}' - Summary: {result[3][:50]}..., Image Path: {result[7]}")
        image_path = result[7]
        if image_path and os.path.exists(image_path):
            logger.info(f"Existing image found at {image_path}")
            image_filename = os.path.basename(image_path)
            image_path = f"/images/{image_filename}"  # Convert to relative URL
        else:
            logger.info(f"No valid image in cache or on disk, generating for '{event}'")
            image_path, image_status = generate_and_save_image(event, result[3])
            if image_status:
                logger.info(f"Generated new image: {image_path}")
                image_filename = os.path.basename(image_path)
                image_path = f"/images/{image_filename}"  # Convert to relative URL
                c.execute("UPDATE search_history SET image_path = ? WHERE query = ?", (image_path, event))
                conn.commit()
            else:
                logger.warning(f"Image generation failed for cached entry '{event}'")
                image_path = None
        
        data = {
            'success': True,
            'summary': result[3],
            'articles': json.loads(result[5]),
            'metadata': {
                'average_sentiment': result[4],
                'source_distribution': json.loads(result[6]),
                'image': {
                    'path': image_path if image_path else None,
                    'generated': bool(image_path)
                }
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

        total_fetched = (len(newsapi_org_articles) + len(guardian_articles) + 
                        len(aylien_articles) + len(gnews_articles) +
                        len(nyt_articles) + len(mediastack_articles) + 
                        len(newsapi_ai_articles))
        logger.info(f"Total articles fetched for event '{event}': {total_fetched}")
        if total_fetched == 0:
            total_time = time.time() - start_time
            logger.info(f"Total request time (no articles): {total_time:.2f} seconds, ending at {time.time()}")
            return {'warning': f"No articles found for '{event}' in the past 7 days. Try a broader topic."}, 200

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
        
        logger.info(f"Skipping sentiment analysis for {len(all_articles)} articles to avoid crashes")
        sentiment_start = time.time()
        for article in all_articles:
            article['sentiment_score'] = 0
        sentiment_time = time.time() - sentiment_start
        logger.info(f"Sentiment processing (disabled) took {sentiment_time:.2f} seconds")
        
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
        dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(2, DEFAULT_TOP_N // num_sources))
        logger.info(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
        logger.info(f"Total slots available: {DEFAULT_TOP_N}")
        
        final_articles = []
        remaining_slots = DEFAULT_TOP_N
        
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
                return {'warning': error_message}, 200

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
            return {'warning': error_message}, 200

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
            return {'warning': f"No relevant articles found for '{event}' after filtering. Try a broader topic."}, 200
        
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
        return {'success': True, 'summary': summary, 'articles': articles, 'metadata': {
            'average_sentiment': sum(article.get('sentiment_score', 0) for article in articles) / len(articles),
            'source_distribution': source_counts,
            'image': {
                'path': image_path,
                'generated': True
            }
        }}, 200
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {'error': f"An error occurred: {str(e)}"}, 500

@routes.route('/data', methods=['POST'])
def get_news_data():
    """Handle AJAX requests with detailed logging and image handling."""
    logger.info("=== Entering get_news_data() ===")
    try:
        event = request.form.get('event')
        logger.info(f"Received event: '{event}'")
        
        result, status_code = process_news_request(event)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Unexpected error in get_news_data: {str(e)}")
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

@routes.route('/images/<filename>')
def serve_image(filename):
    """Serve images from the IMAGE_DIR directory."""
    # Security checks to prevent path traversal and restrict to PNG files
    if not filename.endswith('.png') or '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Blocked suspicious image request: {filename}")
        return jsonify({'error': 'Invalid image filename'}), 403
    
    logger.info(f"Serving image: {filename} from {current_app.config['IMAGE_DIR']}")
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)

@routes.route('/health', methods=['GET'])
def health_check():
    """Return a simple health status for Render's health check."""
    logger.info("Health check accessed")
    return jsonify({'status': 'healthy'}), 200

@routes.route('/admin/image-cache', methods=['GET', 'POST'])
def image_cache_admin():
    """Admin route for image cache statistics and management."""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'optimize':
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
    image_dir = current_app.config["IMAGE_DIR"]
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
    conn = sqlite3.connect(current_app.config["DB_PATH"])
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
    conn = sqlite3.connect(current_app.config["DB_PATH"])
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
    conn.commit()
    conn.close()