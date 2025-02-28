# Production configuration using environment variables
import os

# News API keys
NEWSAPI_ORG_KEY = os.environ.get("NEWSAPI_ORG_KEY", "")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")
GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "")
NYT_API_KEY = os.environ.get("NYT_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MEDIASTACK_API_KEY = os.environ.get("MEDIASTACK_API_KEY", "")
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "")
AYLIEN_APP_ID = os.environ.get("AYLIEN_APP_ID", "")
AYLIEN_API_KEY = os.environ.get("AYLIEN_API_KEY", "")

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
