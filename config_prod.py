# Production configuration using environment variables
import os

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
MAX_ARTICLES_PER_API = 10  # Maximum number of articles to request from each API source
DEFAULT_TOP_N = 20  # Number of articles to return after filtering
RELEVANCE_THRESHOLD = 0.05  # Lowered from 0.1 to allow more articles through
SUMMARIZER_MAX_LENGTH = 300
SUMMARIZER_MIN_LENGTH = 100
AYLIEN_PER_PAGE = MAX_ARTICLES_PER_API
GNEWS_MAX_ARTICLES = MAX_ARTICLES_PER_API
REQUEST_TIMEOUT = 10
DEFAULT_DAYS_BACK = 7
MAX_ARTICLES_PER_SOURCE = 10  # Increased from 5 to allow more articles per source
SUMMARIZER_BY_GPT = 1
WEIGHT_RELEVANCE = 0.7
WEIGHT_POPULARITY = 0.3
