import os
from flask_caching import Cache

# Cache configuration for testing
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',  # Use in-memory cache for testing
    'CACHE_DEFAULT_TIMEOUT': 60  # Short timeout for testing
}

# Mock API Keys for testing or load from environment if available
NEWSAPI_ORG_KEY = os.getenv("TEST_NEWSAPI_ORG_KEY", "test_key")
GUARDIAN_API_KEY = os.getenv("TEST_GUARDIAN_API_KEY", "test_key")
AYLIEN_APP_ID = os.getenv("TEST_AYLIEN_APP_ID", "test_id")
AYLIEN_API_KEY = os.getenv("TEST_AYLIEN_API_KEY", "test_key")
GNEWS_API_KEY = os.getenv("TEST_GNEWS_API_KEY", "test_key")
NEWSAPI_AI_KEY = os.getenv("TEST_NEWSAPI_AI_KEY", "test_key")
MEDIASTACK_API_KEY = os.getenv("TEST_MEDIASTACK_API_KEY", "test_key")
OPENAI_API_KEY = os.getenv("TEST_OPENAI_API_KEY", "test_key")
SHARECOUNT_API_KEY = os.getenv("TEST_SHARECOUNT_API_KEY", "test_key")
NYT_API_KEY = os.getenv("TEST_NYT_API_KEY", "test_key")

# API Endpoints - could be mocked for testing
NEWSAPI_URL = "https://newsapi.org/v2/everything"
GUARDIAN_URL = "https://content.guardianapis.com/search"
GNEWS_URL = "https://gnews.io/api/v4/search"

# Model Configuration
SUMMARIZER_MODEL = "facebook/bart-large-cnn"

# Testing Settings - reduced values for faster testing
MAX_ARTICLES_PER_API = 3  # Reduced for testing
DEFAULT_TOP_N = 5  # Reduced for testing
RELEVANCE_THRESHOLD = 0.05
SUMMARIZER_MAX_LENGTH = 100  # Shorter summaries for testing
SUMMARIZER_MIN_LENGTH = 50
AYLIEN_PER_PAGE = MAX_ARTICLES_PER_API
GNEWS_MAX_ARTICLES = MAX_ARTICLES_PER_API
REQUEST_TIMEOUT = 5  # Shorter timeout for testing
DEFAULT_DAYS_BACK = 3  # Fewer days for testing
MAX_ARTICLES_PER_SOURCE = 2  # Fewer articles for testing
SUMMARIZER_BY_GPT = 1
WEIGHT_RELEVANCE = 0.7
WEIGHT_POPULARITY = 0.3

# Testing specific settings
TESTING = True
DEBUG = True

# Feature flags - all disabled by default for testing
USE_NEWSAPI_ORG = False
USE_GUARDIAN = False
USE_GNEWS = False
USE_NYT = False
USE_OPENAI = False
USE_MEDIASTACK = False
USE_NEWSDATA = False
USE_AYLIEN = False

# You can selectively enable specific APIs for testing
# by setting the corresponding environment variables
if os.getenv("TEST_USE_NEWSAPI_ORG"):
    USE_NEWSAPI_ORG = True
if os.getenv("TEST_USE_GUARDIAN"):
    USE_GUARDIAN = True
# ... and so on for other APIs 