import pytest
import aiohttp
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from app.fetchers.base import BaseFetcher
from app.utils.api_manager import APIManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
async def base_fetcher():
    """Create a BaseFetcher instance with mocked APIManager"""
    logger.debug("Setting up base_fetcher fixture")
    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        # Create mock instance
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        
        fetcher = BaseFetcher("test_api")
        logger.debug(f"Created BaseFetcher instance: {fetcher}")
        try:
            yield fetcher
            logger.debug("Yielded fetcher instance")
        finally:
            logger.debug("Cleaning up fetcher instance")
            if hasattr(fetcher, '_session') and fetcher._session:
                logger.debug("Closing fetcher session")
                await fetcher.close()

@pytest.fixture
async def mock_session():
    """Create a mock session that behaves like aiohttp.ClientSession"""
    session = AsyncMock(spec=aiohttp.ClientSession)
    async def async_close():
        pass
    session.close = async_close
    return session

@pytest.mark.asyncio
async def test_make_request_success():
    """Test successful request"""
    logger.debug("Starting test_make_request_success")
    test_url = "http://test.api/endpoint"
    test_response = {"data": "test"}

    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = test_response
    mock_response.__aenter__.return_value = mock_response
    logger.debug(f"Created mock response: {mock_response}")

    # Create mock session with explicit async context methods
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    logger.debug(f"Created mock session with async context methods: {mock_session}")

    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        # Create mock instance
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        
        fetcher = BaseFetcher("test_api")
        logger.debug("Created test fetcher instance")
        fetcher._session = mock_session

        with patch('socket.gethostbyname', return_value="127.0.0.1"):
            logger.debug("Making test request")
            response = await fetcher.make_request(test_url)
            logger.debug(f"Got response: {response}")
            assert response == test_response
            mock_session.get.assert_called_once_with(test_url)

@pytest.mark.asyncio
async def test_make_request_rate_limit():
    """Test rate limit handling"""
    logger.debug("Starting test_make_request_rate_limit")
    test_url = "http://test.api/endpoint"

    # Mock 429 response
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.__aenter__.return_value = mock_response
    logger.debug("Created mock response with status 429")

    # Create mock session with explicit async context methods
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    logger.debug("Created mock session with async context methods")

    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        logger.debug("Configured mock APIManager")
        
        fetcher = BaseFetcher("test_api")
        fetcher._session = mock_session
        logger.debug("Created and configured test fetcher")

        with patch('socket.gethostbyname', return_value="127.0.0.1"):
            with pytest.raises(Exception) as exc_info:
                logger.debug("Making request expected to hit rate limit")
                await fetcher.make_request(test_url)
            assert "Rate limit exceeded" in str(exc_info.value)
            logger.debug("Verified rate limit error")

@pytest.mark.asyncio
async def test_make_request_auth_error():
    """Test authentication error handling"""
    logger.debug("Starting test_make_request_auth_error")
    test_url = "http://test.api/endpoint"

    # Mock 403 response
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.__aenter__.return_value = mock_response
    logger.debug("Created mock response with status 403")

    # Create mock session with explicit async context methods
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    logger.debug("Created mock session with async context methods")

    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        logger.debug("Configured mock APIManager")
        
        fetcher = BaseFetcher("test_api")
        fetcher._session = mock_session
        logger.debug("Created and configured test fetcher")

        with patch('socket.gethostbyname', return_value="127.0.0.1"):
            with pytest.raises(Exception) as exc_info:
                logger.debug("Making request expected to fail auth")
                await fetcher.make_request(test_url)
            assert "Authentication failed" in str(exc_info.value)
            logger.debug("Verified auth error")

@pytest.mark.asyncio
async def test_fetch_with_retry_success():
    """Test successful retry after failure"""
    logger.debug("Starting test_fetch_with_retry_success")
    test_url = "http://test.api/endpoint"
    test_response = {"data": "test"}

    # Mock responses: first fails, second succeeds
    mock_fail_response = AsyncMock()
    mock_fail_response.status = 500
    mock_fail_response.json.side_effect = Exception("Server error")
    mock_fail_response.__aenter__.return_value = mock_fail_response
    logger.debug("Created mock fail response")

    mock_success_response = AsyncMock()
    mock_success_response.status = 200
    mock_success_response.json.return_value = test_response
    mock_success_response.__aenter__.return_value = mock_success_response
    logger.debug("Created mock success response")

    # Create mock session with explicit async context methods
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.side_effect = [mock_fail_response, mock_success_response]
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    logger.debug("Created mock session with async context methods")

    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        logger.debug("Configured mock APIManager")
        
        fetcher = BaseFetcher("test_api")
        fetcher._session = mock_session
        logger.debug("Created and configured test fetcher")

        with patch('socket.gethostbyname', return_value="127.0.0.1"):
            with patch('asyncio.sleep', return_value=None):
                logger.debug("Making request with retry")
                response = await fetcher.fetch_with_retry(test_url, max_retries=2)
                assert response == test_response
                assert mock_session.get.call_count == 2
                logger.debug("Verified retry success")

@pytest.mark.asyncio
async def test_fetch_with_retry_max_attempts():
    """Test retry exhaustion"""
    logger.debug("Starting test_fetch_with_retry_max_attempts")
    test_url = "http://test.api/endpoint"

    # Mock failed response
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.json.side_effect = Exception("Server error")
    mock_response.__aenter__.return_value = mock_response
    logger.debug("Created mock error response")

    # Create mock session with explicit async context methods
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    logger.debug("Created mock session with async context methods")

    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        logger.debug("Configured mock APIManager")
        
        fetcher = BaseFetcher("test_api")
        fetcher._session = mock_session
        logger.debug("Created and configured test fetcher")

        with patch('socket.gethostbyname', return_value="127.0.0.1"):
            with patch('asyncio.sleep', return_value=None):
                logger.debug("Making request expected to exhaust retries")
                response = await fetcher.fetch_with_retry(test_url, max_retries=3)
                assert response is None
                assert mock_session.get.call_count == 3
                logger.debug("Verified retry exhaustion")

@pytest.mark.asyncio
async def test_session_management():
    """Test session creation and cleanup"""
    logger.debug("Starting test_session_management")
    
    with patch('app.fetchers.base.APIManager') as mock_api_manager_class:
        logger.debug("Patched APIManager")
        mock_api_manager = MagicMock()
        mock_api_manager.can_make_request.return_value = True
        mock_api_manager.get_api_key.return_value = None
        mock_api_manager_class.return_value = mock_api_manager
        
        fetcher = BaseFetcher("test_api")
        logger.debug("Created test fetcher instance")
        
        # Initially no session
        assert fetcher._session is None
        logger.debug("Verified initial session is None")

        # Get session should create one
        session = await fetcher._get_session()
        logger.debug(f"Created new session: {session}")
        assert isinstance(session, aiohttp.ClientSession)
        assert fetcher._session is session

        # Close should clean up
        await fetcher.close()
        logger.debug("Closed session")
        assert fetcher._session is None 