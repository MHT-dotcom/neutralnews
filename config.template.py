# Template for config.py - DO NOT add actual API keys here
# Copy this file to config.py and fill in your actual keys

import os
from signal import getitimer
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})  # Use 'SimpleCache' for in-memory caching

# API Keys (loaded from environment variables for security)
NEWSAPI_ORG_KEY = os.getenv("NEWSAPI_ORG_KEY", "your_newsapi_org_key_here")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "your_guardian_api_key_here")
AYLIEN_APP_ID = os.getenv("AYLIEN_APP_ID", "your_aylien_app_id_here")
AYLIEN_API_KEY = os.getenv("AYLIEN_API_KEY", "your_aylien_api_key_here")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "your_gnews_api_key_here")
NEWSAPI_AI_KEY = os.getenv("NEWSAPI_AI_KEY", "your_newsapi_ai_key_here")
MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY", "your_mediastack_api_key_here")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
SHARECOUNT_API_KEY = os.getenv("SHARECOUNT_API_KEY", "your_sharecount_api_key_here")
NYT_API_KEY = os.getenv("NYT_API_KEY", "your_nyt_api_key_here")

# API Endpoints
NEWSAPI_URL = "https://newsapi.org/v2/everything"
GUARDIAN_URL = "https://content.guardianapis.com/search"
GNEWS_URL = "https://gnews.io/api/v4/search"

# Model Configuration
SUMMARIZER_MODEL = "facebook/bart-large-cnn"

# Default Settings
MAX_ARTICLES_PER_API = 10  # Maximum number of articles to request from each API source
DEFAULT_TOP_N = 20  # Number of articles to return after filtering
RELEVANCE_THRESHOLD = 0.05  # Lowered from 0.1 to allow more articles through
SUMMARIZER_MAX_LENGTH = 300
SUMMARIZER_MIN_LENGTH = 100
AYLIEN_PER_PAGE = MAX_ARTICLES_PER_API
GNEWS_MAX_ARTICLES = MAX_ARTICLES_PER_API
REQUEST_TIMEOUT = 10
DEFAULT_DAYS_BACK = 7
MAX_ARTICLES_PER_SOURCE = 10  # Maximum articles per true source for balanced summary
SUMMARIZER_BY_GPT = 1
WEIGHT_RELEVANCE = 0.7
WEIGHT_POPULARITY = 0.3
