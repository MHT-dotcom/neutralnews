# Production configuration using environment variables
import os
# type: ignore
from flask_caching import Cache
from dotenv import load_dotenv
import random
from datetime import datetime
from utils import secure_log_key

# Basic in-memory cache with init_app pattern
cache = Cache()
CACHE_CONFIG = {'CACHE_TYPE': 'simple'}

# News API keys
NEWSAPI_ORG_KEY = os.environ.get("NEWSAPI_ORG_KEY", "")
NEWSAPI_AI_KEY = os.environ.get("NEWSAPI_AI_KEY", "")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")
GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "")
NYT_API_KEY = os.environ.get("NYT_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MEDIASTACK_API_KEY = os.environ.get("MEDIASTACK_API_KEY", "")
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "")
AYLIEN_APP_ID = os.environ.get("AYLIEN_APP_ID", "")
AYLIEN_API_KEY = os.environ.get("AYLIEN_API_KEY", "")
GROK_API_KEY = os.environ.get("GROK_API_KEY", "").replace("xai-", "")
STABILITY_API_KEY = os.environ.get('STABILITY_API_KEY')
GETIMG_API_KEY = os.environ.get('GETIMG_API_KEY')

# Helper function to check API key status without exposing the actual key
def get_api_key_status(key_name, key_value):
    """Return the status of an API key for logging purposes without exposing the actual key"""
    if not key_value:
        return "Missing"
    
    if len(key_value) < 8:
        return "Invalid (too short)"
        
    masked_key = secure_log_key(key_value, visible_chars=2)
    return f"Available ({masked_key})"

# api endpoints
# NEWSAPI_URL = "https://newsapi.org/v2/everything"
GUARDIAN_URL = "https://content.guardianapis.com/search"
GNEWS_URL = "https://gnews.io/api/v4/search"
# Default Settings
DEFAULT_DAYS_BACK = 7

# Feature flags
USE_NEWSAPI_ORG = bool(NEWSAPI_ORG_KEY)
USE_GUARDIAN = bool(GUARDIAN_API_KEY)
USE_GNEWS = bool(GNEWS_API_KEY)
USE_NYT = bool(NYT_API_KEY)
USE_OPENAI = bool(OPENAI_API_KEY)
USE_MEDIASTACK = bool(MEDIASTACK_API_KEY)
USE_NEWSDATA = bool(NEWSDATA_API_KEY)
USE_AYLIEN = bool(AYLIEN_APP_ID and AYLIEN_API_KEY)
USE_GROK = bool(GROK_API_KEY)

# Cache configuration
CACHE_TYPE = "FileSystemCache"
CACHE_DIR = "cache"
CACHE_DEFAULT_TIMEOUT = 1800  # 30 minutes

# App configuration
DEBUG = False


NEWSAPI_URL = "https://newsapi.org/v2/everything"
GUARDIAN_URL = "https://content.guardianapis.com/search"
GNEWS_URL = "https://gnews.io/api/v4/search"

# Model Configuration
SUMMARIZER_MODEL = "facebook/bart-large-cnn"

# Default Settings
MAX_ARTICLES_PER_API = 15  # Increased from 8 to get more articles per API
DEFAULT_TOP_N = 15  # Increased from 10 to 15 to allow more articles in the response
RELEVANCE_THRESHOLD = 0.02  # Lowered from 0.05 to allow more articles through
MAX_ARTICLES_PER_SOURCE = 5  # Adjusted to allow up to 4 articles per source for better distribution
SUMMARIZER_MAX_LENGTH = 250
SUMMARIZER_MIN_LENGTH = 100
AYLIEN_PER_PAGE = MAX_ARTICLES_PER_API
GNEWS_MAX_ARTICLES = MAX_ARTICLES_PER_API
REQUEST_TIMEOUT = 10
DEFAULT_DAYS_BACK = 7
SUMMARIZER_BY_GPT = 1
WEIGHT_RELEVANCE = 0.6
WEIGHT_POPULARITY = 0.4


# Use secure logging to protect API key before .env load
grok_key_before = secure_log_key(os.environ.get("GROK_API_KEY", "NOT SET"), visible_chars=2)
print(f"Before .env load: GROK_API_KEY status: {grok_key_before}")

load_dotenv()
