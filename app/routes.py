"""
Route definitions for the Neutral News API
"""

from quart import Blueprint, jsonify, request
from .fetchers.base import BaseFetcher
import logging

# Create blueprint
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is operational"}

@api_bp.route('/news', methods=['GET'])
async def get_news():
    """
    Fetch news articles from configured sources
    Query parameters:
    - q: search query
    - sources: comma-separated list of sources (optional)
    """
    try:
        query = request.args.get('q', '')
        if not query:
            return {"error": "Query parameter 'q' is required"}, 400
            
        # Initialize fetcher for Guardian (we can add more sources later)
        fetcher = BaseFetcher("guardian", verify_ssl=True)
        try:
            url = f"{fetcher.api_manager.get_base_url('guardian')}/search?q={query}&api-key={fetcher.api_manager.get_api_key('guardian')}&show-fields=all"
            response = await fetcher.fetch_with_retry(url)
            
            if response and 'response' in response:
                articles = response['response'].get('results', [])
                return {
                    "status": "success",
                    "count": len(articles),
                    "articles": articles
                }
            else:
                return {"error": "No results found"}, 404
                
        finally:
            await fetcher.close()
            
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        return {"error": "Internal server error", "details": str(e)}, 500

# Add more routes as needed 