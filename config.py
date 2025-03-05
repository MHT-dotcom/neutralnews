"""
Configuration module for Neutral News application.
Handles both development and production environments.
"""

import os
from signal import getitimer
from flask_caching import Cache
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Cache configuration
    CACHE_CONFIG = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 1800  # 30 minutes
    }
    
    # API Keys (loaded from environment variables)
    NEWSAPI_ORG_KEY = os.getenv("NEWSAPI_ORG_KEY", "")
    GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "")
    AYLIEN_APP_ID = os.getenv("AYLIEN_APP_ID", "")
    AYLIEN_API_KEY = os.getenv("AYLIEN_API_KEY", "")
    GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
    NEWSAPI_AI_KEY = os.getenv("NEWSAPI_AI_KEY", "")
    MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    NYT_API_KEY = os.getenv("NYT_API_KEY", "")
    
    # Feature flags based on API key availability
    USE_NEWSAPI_ORG = bool(NEWSAPI_ORG_KEY)
    USE_GUARDIAN = bool(GUARDIAN_API_KEY)
    USE_GNEWS = bool(GNEWS_API_KEY)
    USE_NYT = bool(NYT_API_KEY)
    USE_MEDIASTACK = bool(MEDIASTACK_API_KEY)
    USE_NEWSAPI_AI = bool(NEWSAPI_AI_KEY)
    USE_AYLIEN = bool(AYLIEN_APP_ID and AYLIEN_API_KEY)
    USE_OPENAI = bool(OPENAI_API_KEY)
    
    # API Endpoints
    NEWSAPI_URL = "https://newsapi.org/v2/everything"
    GUARDIAN_URL = "https://content.guardianapis.com/search"
    GNEWS_URL = "https://gnews.io/api/v4/search"
    
    # Model Configuration
    SUMMARIZER_MODEL = "facebook/bart-large-cnn"
    
    # Default Settings
    MAX_ARTICLES_PER_API = 10
    DEFAULT_TOP_N = 20
    RELEVANCE_THRESHOLD = 0.05
    SUMMARIZER_MAX_LENGTH = 300
    SUMMARIZER_MIN_LENGTH = 100
    AYLIEN_PER_PAGE = MAX_ARTICLES_PER_API
    GNEWS_MAX_ARTICLES = MAX_ARTICLES_PER_API
    REQUEST_TIMEOUT = 10
    DEFAULT_DAYS_BACK = 7
    MAX_ARTICLES_PER_SOURCE = 10
    SUMMARIZER_BY_GPT = 1
    WEIGHT_RELEVANCE = 0.7
    WEIGHT_POPULARITY = 0.3

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Override cache config for development
    CACHE_CONFIG = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes for faster testing
    }

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Use memory cache for testing
    CACHE_CONFIG = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 60
    }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    MAX_ARTICLES_PER_API = 8
    DEFAULT_TOP_N = 7
    SUMMARIZER_MAX_LENGTH = 250
    MAX_ARTICLES_PER_SOURCE = 4
    WEIGHT_RELEVANCE = 0.8
    WEIGHT_POPULARITY = 0.2
    
    # Production cache config
    CACHE_CONFIG = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 1800
    }

# cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})  # Temporarily disabled for faster builds


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
MAX_ARTICLES_PER_SOURCE = 10  # Increased from 5 to allow more articles per source
SUMMARIZER_BY_GPT = 1
WEIGHT_RELEVANCE = 0.7
WEIGHT_POPULARITY = 0.3

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 1800  # 30 minutes
}
