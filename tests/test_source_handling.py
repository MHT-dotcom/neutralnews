import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from mock_services import MOCK_ARTICLES

class TestSourceHandling(unittest.TestCase):
    def setUp(self):
        # Set up Flask test client
        self.client = app.test_client()
        self.client.testing = True
        
    @patch('routes._fetch_and_process_data')
    def test_dictionary_source_handling(self, mock_fetch_process):
        """Test that dictionary sources are properly handled"""
        # Create test articles with dictionary sources
        test_articles = [
            {
                'title': 'Test Article 1',
                'description': 'Test description 1',
                'url': 'https://example.com/1',
                'source': {'name': 'Source A'},
                'publishedAt': '2023-01-01T12:00:00Z',
                'content': 'Test content 1',
                'urlToImage': 'https://example.com/image1.jpg',
                'sentiment_score': 0.5,
                'relevance_score': 0.8,
                'popularity_score': 0.7,
                'combined_score': 0.75
            },
            {
                'title': 'Test Article 2',
                'description': 'Test description 2',
                'url': 'https://example.com/2',
                'source': {'name': 'Source B'},
                'publishedAt': '2023-01-02T12:00:00Z',
                'content': 'Test content 2',
                'urlToImage': 'https://example.com/image2.jpg',
                'sentiment_score': -0.3,
                'relevance_score': 0.6,
                'popularity_score': 0.5,
                'combined_score': 0.65
            }
        ]
        
        # Configure the mock to return our test data
        def side_effect(query):
            if query == 'test query':
                return {
                    'articles': test_articles,
                    'summary': 'Test summary',
                    'sentiment': {'score': 0.1, 'label': 'neutral'}
                }
            else:
                # Return default mock data for trending topics
                return {
                    'articles': MOCK_ARTICLES,
                    'summary': f'Summary for {query}',
                    'sentiment': {'score': 0.0, 'label': 'neutral'}
                }
                
        mock_fetch_process.side_effect = side_effect
        
        # Make a request to the data endpoint
        response = self.client.post('/data', data={'event': 'test query'})
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Parse the response data
        data = json.loads(response.data)
        
        # Check that the articles are included in the response
        self.assertIn('articles', data)
        
        # Verify that the mock was called with the expected arguments
        mock_fetch_process.assert_any_call('test query')
        
        # Check that the source field is properly handled in the response
        # The source should be normalized in the routes.py file
        for article in data['articles']:
            self.assertIn('source', article)
            # Source should be a string (the name extracted from the dictionary)
            self.assertIsInstance(article['source'], str)
        
        # Check that the metadata includes source distribution
        self.assertIn('metadata', data)
        self.assertIn('source_distribution', data['metadata'])
        
        # Source distribution should have keys that are strings
        for source in data['metadata']['source_distribution'].keys():
            self.assertIsInstance(source, str)

if __name__ == '__main__':
    unittest.main() 