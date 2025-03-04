import unittest
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import mock modules for testing
from mock_services import (
    mock_fetch_newsapi,
    fetch_newsapi_org,
    fetch_guardian,
    fetch_aylien_articles,
    fetch_gnews_articles,
    fetch_nyt_articles,
    fetch_mediastack_articles,
    fetch_newsapi_ai_articles,
    MockModelManager
)

class TestMockServices(unittest.TestCase):
    def test_mock_fetch_newsapi(self):
        """Test that mock_fetch_newsapi returns properly structured articles"""
        articles = mock_fetch_newsapi("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_fetch_newsapi_org(self):
        """Test that fetch_newsapi_org returns properly structured articles"""
        articles = fetch_newsapi_org("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_fetch_guardian(self):
        """Test that fetch_guardian returns properly structured articles"""
        articles = fetch_guardian("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
            self.assertEqual(article['source']['name'], "The Guardian")
    
    def test_fetch_aylien_articles(self):
        """Test that fetch_aylien_articles returns properly structured articles"""
        articles = fetch_aylien_articles("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_fetch_gnews_articles(self):
        """Test that fetch_gnews_articles returns properly structured articles"""
        articles = fetch_gnews_articles("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_fetch_nyt_articles(self):
        """Test that fetch_nyt_articles returns properly structured articles"""
        articles = fetch_nyt_articles("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
            self.assertEqual(article['source']['name'], "The New York Times")
    
    def test_fetch_mediastack_articles(self):
        """Test that fetch_mediastack_articles returns properly structured articles"""
        articles = fetch_mediastack_articles("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_fetch_newsapi_ai_articles(self):
        """Test that fetch_newsapi_ai_articles returns properly structured articles"""
        articles = fetch_newsapi_ai_articles("test query")
        self.assertTrue(len(articles) > 0)
        for article in articles:
            self.assertIn('title', article)
            self.assertIn('source', article)
            self.assertIsInstance(article['source'], dict)
            self.assertIn('name', article['source'])
    
    def test_mock_model_manager(self):
        """Test that MockModelManager works correctly"""
        model_manager = MockModelManager.get_instance()
        self.assertIsInstance(model_manager, MockModelManager)
        
        # Test get_sentiment_analyzer
        sentiment_analyzer = model_manager.get_sentiment_analyzer()
        self.assertEqual(sentiment_analyzer, model_manager)
        
        # Test get_summarizer
        summarizer = model_manager.get_summarizer()
        self.assertEqual(summarizer, model_manager)
        
        # Test clear_models
        model_manager.clear_models()  # Should not raise an exception
        
        # Test __call__
        result = model_manager(["Test text 1", "Test text 2"])
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIsInstance(item, dict)
            self.assertIn('score', item)
            self.assertIn('label', item)

if __name__ == '__main__':
    unittest.main() 