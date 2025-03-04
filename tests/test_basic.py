import unittest
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import mock modules for testing
from mock_services import patch_modules
from mock_data import MOCK_ARTICLES

# Patch modules before importing app
patch_modules()

# Import application modules after patching
import app_test
from app_test import app

class TestBasicFunctionality(unittest.TestCase):
    def setUp(self):
        # Set up Flask test client
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_index_route(self):
        """Test that the index route returns 200 OK"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_search_with_empty_query(self):
        """Test search with an empty query"""
        response = self.client.post('/data', data={'event': ''})
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main() 