"""
Basic test file to verify the testing setup works without pytest-flask.
"""

import pytest
import json
import os
import sys

# Add the parent directory to sys.path to import application modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import mock modules for testing
from mock_data import MOCK_ARTICLES

def test_mock_data_exists():
    """Test that mock data is available"""
    assert len(MOCK_ARTICLES) > 0
    assert "title" in MOCK_ARTICLES[0]
    assert "content" in MOCK_ARTICLES[0]

def test_basic_functionality():
    """A simple test that always passes"""
    assert True

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 