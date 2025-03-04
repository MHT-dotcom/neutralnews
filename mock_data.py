"""
This module provides mock data for testing purposes.
It includes sample responses from various news APIs and mock implementations
of key functions to avoid making real API calls during testing.
"""

# Mock news articles for testing
MOCK_ARTICLES = [
    {
        "title": "Test Article 1",
        "description": "This is a test article with positive sentiment.",
        "url": "https://example.com/article1",
        "source": {"name": "Test Source 1"},
        "publishedAt": "2023-01-01T12:00:00Z",
        "content": "This is a positive test article content. It discusses advancements and improvements.",
        "urlToImage": "https://example.com/image1.jpg",
        "sentiment_score": 0.8,
        "relevance_score": 0.9,
        "popularity_score": 0.7,
        "combined_score": 0.85,
        "summary": "This is a summary of the positive test article."
    },
    {
        "title": "Test Article 2",
        "description": "This is a test article with negative sentiment.",
        "url": "https://example.com/article2",
        "source": {"name": "Test Source 2"},
        "publishedAt": "2023-01-02T12:00:00Z",
        "content": "This is a negative test article content. It discusses problems and challenges.",
        "urlToImage": "https://example.com/image2.jpg",
        "sentiment_score": -0.7,
        "relevance_score": 0.8,
        "popularity_score": 0.6,
        "combined_score": 0.75,
        "summary": "This is a summary of the negative test article."
    },
    {
        "title": "Test Article 3",
        "description": "This is a test article with neutral sentiment.",
        "url": "https://example.com/article3",
        "source": {"name": "Test Source 3"},
        "publishedAt": "2023-01-03T12:00:00Z",
        "content": "This is a neutral test article content. It discusses facts and information.",
        "urlToImage": "https://example.com/image3.jpg",
        "sentiment_score": 0.1,
        "relevance_score": 0.95,
        "popularity_score": 0.8,
        "combined_score": 0.9,
        "summary": "This is a summary of the neutral test article."
    }
]

# Mock response from NewsAPI
MOCK_NEWSAPI_RESPONSE = {
    "status": "ok",
    "totalResults": 3,
    "articles": MOCK_ARTICLES
}

# Mock response from Guardian API
MOCK_GUARDIAN_RESPONSE = {
    "response": {
        "status": "ok",
        "total": 3,
        "results": [
            {
                "id": "test/article1",
                "type": "article",
                "sectionId": "test",
                "webTitle": "Test Article 1",
                "webUrl": "https://example.com/article1",
                "apiUrl": "https://example.com/api/article1",
                "fields": {
                    "headline": "Test Article 1",
                    "trailText": "This is a test article with positive sentiment.",
                    "body": "This is a positive test article content. It discusses advancements and improvements."
                }
            },
            {
                "id": "test/article2",
                "type": "article",
                "sectionId": "test",
                "webTitle": "Test Article 2",
                "webUrl": "https://example.com/article2",
                "apiUrl": "https://example.com/api/article2",
                "fields": {
                    "headline": "Test Article 2",
                    "trailText": "This is a test article with negative sentiment.",
                    "body": "This is a negative test article content. It discusses problems and challenges."
                }
            },
            {
                "id": "test/article3",
                "type": "article",
                "sectionId": "test",
                "webTitle": "Test Article 3",
                "webUrl": "https://example.com/article3",
                "apiUrl": "https://example.com/api/article3",
                "fields": {
                    "headline": "Test Article 3",
                    "trailText": "This is a test article with neutral sentiment.",
                    "body": "This is a neutral test article content. It discusses facts and information."
                }
            }
        ]
    }
}

# Mock response from GNews API
MOCK_GNEWS_RESPONSE = {
    "totalArticles": 3,
    "articles": [
        {
            "title": "Test Article 1",
            "description": "This is a test article with positive sentiment.",
            "content": "This is a positive test article content. It discusses advancements and improvements.",
            "url": "https://example.com/article1",
            "image": "https://example.com/image1.jpg",
            "publishedAt": "2023-01-01T12:00:00Z",
            "source": {"name": "Test Source 1"}
        },
        {
            "title": "Test Article 2",
            "description": "This is a test article with negative sentiment.",
            "content": "This is a negative test article content. It discusses problems and challenges.",
            "url": "https://example.com/article2",
            "image": "https://example.com/image2.jpg",
            "publishedAt": "2023-01-02T12:00:00Z",
            "source": {"name": "Test Source 2"}
        },
        {
            "title": "Test Article 3",
            "description": "This is a test article with neutral sentiment.",
            "content": "This is a neutral test article content. It discusses facts and information.",
            "url": "https://example.com/article3",
            "image": "https://example.com/image3.jpg",
            "publishedAt": "2023-01-03T12:00:00Z",
            "source": {"name": "Test Source 3"}
        }
    ]
}

# Mock sentiment analysis results
MOCK_SENTIMENT_RESULTS = {
    "This is a positive test article content. It discusses advancements and improvements.": 0.8,
    "This is a negative test article content. It discusses problems and challenges.": -0.7,
    "This is a neutral test article content. It discusses facts and information.": 0.1
}

# Mock summarization results
MOCK_SUMMARY_RESULTS = {
    "This is a positive test article content. It discusses advancements and improvements.": 
        "This is a summary of the positive test article.",
    "This is a negative test article content. It discusses problems and challenges.": 
        "This is a summary of the negative test article.",
    "This is a neutral test article content. It discusses facts and information.": 
        "This is a summary of the neutral test article."
}

# Mock search queries and results
MOCK_SEARCH_QUERIES = {
    "climate change": MOCK_ARTICLES,
    "politics": MOCK_ARTICLES,
    "technology": MOCK_ARTICLES,
    "health": MOCK_ARTICLES,
    "economy": MOCK_ARTICLES
}

# Function to get mock articles based on query
def get_mock_articles(query):
    """Return mock articles for a given query"""
    return MOCK_SEARCH_QUERIES.get(query.lower(), MOCK_ARTICLES) 