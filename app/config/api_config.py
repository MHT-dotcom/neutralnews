"""
API Configuration

This module contains configuration settings for various APIs used in the application.
"""

# API Quota configurations
API_QUOTAS = {
    'newsapi': {
        'requests_per_second': 1,
        'requests_per_minute': 30,
        'requests_per_day': 1000
    },
    'nyt': {
        'requests_per_second': 1,
        'requests_per_minute': 30,
        'requests_per_day': 4000
    },
    'mediastack': {
        'requests_per_second': 1,
        'requests_per_minute': 60,
        'requests_per_day': 1000
    },
    'gnews': {
        'requests_per_second': 1,
        'requests_per_minute': 60,
        'requests_per_day': 1000
    },
    'guardian': {
        'requests_per_second': 1,
        'requests_per_minute': 30,
        'requests_per_day': 500
    },
    'jsonplaceholder': {
        'requests_per_second': 5,  # JSONPlaceholder is quite permissive
        'requests_per_minute': 100,
        'requests_per_day': 1000
    }
}

# Default retry configurations
RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 5,  # seconds
    'max_delay': 300,  # 5 minutes
    'exponential_base': 2
}

# API specific configurations
API_CONFIGS = {
    'newsapi': {
        'base_url': 'https://newsapi.org/v2',
        'timeout': 30,
        'requires_key': True
    },
    'nyt': {
        'base_url': 'https://api.nytimes.com/svc',
        'timeout': 30,
        'requires_key': True
    },
    'mediastack': {
        'base_url': 'http://api.mediastack.com/v1',
        'timeout': 30,
        'requires_key': True
    },
    'gnews': {
        'base_url': 'https://gnews.io/api/v4',
        'timeout': 30,
        'requires_key': True
    },
    'guardian': {
        'base_url': 'https://content.guardianapis.com',
        'timeout': 30,
        'requires_key': True
    }
}

API_RETRY_CONFIG = {
    'default': {
        'max_retries': 3,
        'base_delay': 5,
        'max_delay': 300,
        'exponential_base': 2
    }
} 