"""
This script sets up the test environment for the Neutral News application.
It creates necessary directories, environment files, and prepares the application for testing.
"""

import os
import sys
import shutil
import argparse
from dotenv import load_dotenv

def create_test_env_file(use_real_apis=False):
    """Create a .env.test file for testing"""
    env_content = """# Test environment variables
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_CONFIG=config_test
TEST_PORT=10001

# Set to 1 to use mock models instead of real models
MOCK_MODELS=1

# Set to 1 to enable specific APIs for testing
TEST_USE_NEWSAPI_ORG=0
TEST_USE_GUARDIAN=0
TEST_USE_GNEWS=0
TEST_USE_NYT=0
TEST_USE_OPENAI=0
TEST_USE_MEDIASTACK=0
TEST_USE_NEWSDATA=0
TEST_USE_AYLIEN=0
"""

    # If using real APIs, add placeholders for API keys
    if use_real_apis:
        env_content += """
# Add your test API keys here if you want to use real APIs
# TEST_NEWSAPI_ORG_KEY=your_test_key
# TEST_GUARDIAN_API_KEY=your_test_key
# TEST_AYLIEN_APP_ID=your_test_id
# TEST_AYLIEN_API_KEY=your_test_key
# TEST_GNEWS_API_KEY=your_test_key
# TEST_NEWSAPI_AI_KEY=your_test_key
# TEST_MEDIASTACK_API_KEY=your_test_key
# TEST_OPENAI_API_KEY=your_test_key
# TEST_SHARECOUNT_API_KEY=your_test_key
# TEST_NYT_API_KEY=your_test_key
"""

    with open('.env.test', 'w') as f:
        f.write(env_content)
    
    print("Created .env.test file")

def create_test_script():
    """Create a test.sh script to run the test environment"""
    script_content = """#!/bin/bash
# Script to run the test environment

# Export test environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export FLASK_CONFIG=config_test
export TEST_PORT=10001

# Run the test application
python app_test.py
"""

    with open('test.sh', 'w') as f:
        f.write(script_content)
    
    # Make the script executable
    os.chmod('test.sh', 0o755)
    
    print("Created test.sh script")

def create_test_directory():
    """Create a test directory for test artifacts"""
    if not os.path.exists('tests'):
        os.makedirs('tests')
        print("Created tests directory")
    
    if not os.path.exists('tests/fixtures'):
        os.makedirs('tests/fixtures')
        print("Created tests/fixtures directory")

def update_gitignore():
    """Update .gitignore to exclude test-specific files"""
    gitignore_additions = """
# Test-specific files
.env.test
__pycache__/
.pytest_cache/
tests/fixtures/
"""

    with open('.gitignore', 'a') as f:
        f.write(gitignore_additions)
    
    print("Updated .gitignore with test-specific exclusions")

def create_pytest_config():
    """Create a pytest.ini file for pytest configuration"""
    pytest_content = """[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
# Don't use pytest-flask plugin
addopts = -v
"""

    with open('pytest.ini', 'w') as f:
        f.write(pytest_content)
    
    print("Created pytest.ini file")

def create_comprehensive_test_file():
    """Create a comprehensive test file with examples of different test types"""
    # Break up the large string into smaller parts to avoid linter issues
    test_content_imports = """import unittest
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import mock modules for testing
from mock_services import patch_modules
from mock_data import MOCK_ARTICLES, get_mock_articles

# Import application modules
# Note: These imports will use the mocked versions if patch_modules() is called
import app_test
from app_test import app
"""

    test_content_class = """
class TestNeutralNewsApp(unittest.TestCase):
    def setUp(self):
        # Patch modules with mock implementations
        self.mock_modules = patch_modules()
        
        # Set up Flask test client
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def tearDown(self):
        # Clean up any resources if needed
        pass
    
    def test_index_route(self):
        \"\"\"Test that the index route returns 200 OK\"\"\"
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_search_with_valid_query(self):
        \"\"\"Test search with a valid query\"\"\"
        response = self.client.post('/data', data={'event': 'climate change'})
        self.assertEqual(response.status_code, 200)
        
        # Check if response contains expected data
        data = json.loads(response.data)
        self.assertIn('articles', data)
        self.assertIn('summary', data)
    
    def test_search_with_empty_query(self):
        \"\"\"Test search with an empty query\"\"\"
        response = self.client.post('/data', data={'event': ''})
        self.assertEqual(response.status_code, 400)
"""

    test_content_more_tests = """    
    @patch('fetchers.fetch_newsapi')
    def test_newsapi_integration(self, mock_fetch):
        \"\"\"Test NewsAPI integration with mocked response\"\"\"
        # Configure the mock to return a specific result
        mock_fetch.return_value = MOCK_ARTICLES[:2]
        
        # Make the request
        response = self.client.post('/data', data={'event': 'test query'})
        self.assertEqual(response.status_code, 200)
        
        # Verify the mock was called with expected arguments
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        self.assertEqual(args[0], 'test query')
    
    def test_api_error_handling(self):
        \"\"\"Test error handling when APIs fail\"\"\"
        # This would need to be implemented based on how your application handles API errors
        pass
"""

    test_content_pytest = """
# Pytest-style tests
@pytest.fixture
def client():
    \"\"\"Flask test client fixture\"\"\"
    # Patch modules with mock implementations
    patch_modules()
    
    # Create a test client without using pytest-flask
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Establish an application context
        with app.app_context():
            yield client

def test_index_page_pytest(client):
    \"\"\"Test index page using pytest style\"\"\"
    response = client.get('/')
    assert response.status_code == 200

def test_search_functionality_pytest(client):
    \"\"\"Test search functionality using pytest style\"\"\"
    response = client.post('/data', data={'event': 'technology'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'articles' in data
    assert len(data['articles']) > 0

if __name__ == '__main__':
    unittest.main()
"""

    # Combine all parts
    test_content = test_content_imports + test_content_class + test_content_more_tests + test_content_pytest

    with open('tests/test_comprehensive.py', 'w') as f:
        f.write(test_content)
    
    print("Created comprehensive test file at tests/test_comprehensive.py")

def main():
    parser = argparse.ArgumentParser(description='Set up test environment for Neutral News')
    parser.add_argument('--use-real-apis', action='store_true', help='Include placeholders for real API keys')
    args = parser.parse_args()
    
    print("Setting up test environment for Neutral News...")
    
    # Create test environment file
    create_test_env_file(args.use_real_apis)
    
    # Create test script
    create_test_script()
    
    # Create test directory
    create_test_directory()
    
    # Update .gitignore
    update_gitignore()
    
    # Create pytest configuration
    create_pytest_config()
    
    # Create comprehensive test file
    create_comprehensive_test_file()
    
    print("\nTest environment setup complete!")
    print("\nTo run the test environment:")
    print("1. Modify .env.test if needed")
    print("2. Run './test.sh' to start the test server")
    print("3. Run 'pytest' to run the tests")

if __name__ == '__main__':
    main() 