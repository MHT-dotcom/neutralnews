import pytest
import time
from unittest.mock import patch, MagicMock
from app.utils.api_manager import APIManager, APIQuota

@pytest.fixture
def api_manager():
    manager = APIManager()
    # Register some test API keys
    manager.register_api_key('newsapi', 'test_key_1', 'test_value_1')
    manager.register_api_key('newsapi', 'test_key_2', 'test_value_2')
    return manager

def test_singleton_pattern():
    """Test that APIManager is a singleton"""
    manager1 = APIManager()
    manager2 = APIManager()
    assert manager1 is manager2

def test_api_key_registration(api_manager):
    """Test API key registration and retrieval"""
    api_manager.register_api_key('test_api', 'key1', 'value1')
    assert 'test_api' in api_manager.api_keys
    assert api_manager.api_keys['test_api']['key1'] == 'value1'

def test_api_key_rotation(api_manager):
    """Test API key rotation"""
    # Get initial key
    initial_key = api_manager.get_api_key('newsapi')
    assert initial_key is not None
    
    # Force key rotation by setting last rotation time to past
    api_manager.last_key_rotation['newsapi'] = time.time() - 3601
    
    # Get key again, should be different
    rotated_key = api_manager.get_api_key('newsapi')
    assert rotated_key is not None
    assert rotated_key != initial_key

def test_rate_limiting(api_manager):
    """Test rate limiting functionality"""
    api_name = 'test_api'
    api_manager.quotas[api_name] = APIQuota(
        requests_per_second=1,
        requests_per_minute=2,
        requests_per_day=5
    )
    
    # First request should be allowed
    assert api_manager.can_make_request(api_name) is True
    
    # Second request in same second should be denied
    assert api_manager.can_make_request(api_name) is False
    
    # Wait for 1 second and try again
    time.sleep(1.1)
    assert api_manager.can_make_request(api_name) is True

def test_handle_rate_limit_error(api_manager):
    """Test rate limit error handling"""
    api_name = 'test_api'
    api_manager.quotas[api_name] = APIQuota(
        requests_per_second=1,
        requests_per_minute=60,
        requests_per_day=1000
    )
    
    initial_minute_limit = api_manager.quotas[api_name].requests_per_minute
    api_manager.handle_rate_limit_error(api_name)
    
    # Check that limits were reduced by 25%
    assert api_manager.quotas[api_name].requests_per_minute == int(initial_minute_limit * 0.75)

def test_handle_auth_error(api_manager):
    """Test authentication error handling"""
    api_name = 'test_api'
    key_id = 'test_key'
    api_manager.register_api_key(api_name, key_id, 'test_value')
    
    # Verify key exists
    assert key_id in api_manager.api_keys[api_name]
    
    # Handle auth error
    api_manager.handle_auth_error(api_name, key_id)
    
    # Verify key was removed
    assert key_id not in api_manager.api_keys[api_name]

@pytest.mark.asyncio
async def test_retry_configuration(api_manager):
    """Test retry configuration"""
    retry_config = api_manager.get_retry_config('test_api')
    assert retry_config['max_retries'] == 3
    assert retry_config['base_delay'] == 5
    assert retry_config['max_delay'] == 300
    assert retry_config['exponential_base'] == 2 