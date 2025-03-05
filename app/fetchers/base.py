import logging
import aiohttp
import asyncio
import ssl
from urllib.parse import urlparse
from typing import Any, Optional
from ..utils.api_manager import APIManager

class BaseFetcher:
    def __init__(self, api_name: str, verify_ssl: bool = True):
        self.api_name = api_name
        self.api_manager = APIManager()
        self._session = None
        self.verify_ssl = verify_ssl
        logging.info(f"Initialized {self.__class__.__name__} with API name: {api_name}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession"""
        if self._session is None:
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self._session = aiohttp.ClientSession(connector=connector)
            else:
                self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session if it exists"""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def make_request(self, url: str, **kwargs) -> Any:
        if not self.api_manager.can_make_request(self.api_name):
            logging.warning(f"{self.api_name}: Rate limit would be exceeded, waiting...")
            await asyncio.sleep(60)  # Wait for a minute before retrying
            if not self.api_manager.can_make_request(self.api_name):
                raise Exception(f"{self.api_name}: Rate limit exceeded even after waiting")

        try:
            logging.info(f"{self.__class__.__name__}: DNS pre-request check for {urlparse(url).netloc}")
            # Try DNS resolution before making request
            try:
                import socket
                socket.gethostbyname(urlparse(url).netloc)
                logging.info(f"{self.__class__.__name__}: DNS resolution successful for {urlparse(url).netloc}")
            except socket.gaierror as e:
                logging.error(f"{self.__class__.__name__}: DNS resolution failed for {urlparse(url).netloc}: {str(e)}")
                
            # Get API key if needed
            api_key = self.api_manager.get_api_key(self.api_name)
            if api_key:
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Authorization'] = f'Bearer {api_key}'

            # Log request details
            logging.info(f"{self.__class__.__name__}: Making request to {url} with headers: {kwargs.get('headers', {})}")
            
            session = await self._get_session()
            async with session.get(url, **kwargs) as response:
                logging.info(f"{self.__class__.__name__}: Response status {response.status} for {url}")
                
                if response.status == 403:
                    logging.error(f"{self.__class__.__name__}: Authentication failed with headers: {kwargs.get('headers', {})}")
                    self.api_manager.handle_auth_error(self.api_name, "current")  # We'll need to implement key tracking
                    raise Exception(f"{self.api_name}: Authentication failed")
                
                if response.status == 429:
                    logging.error(f"{self.__class__.__name__}: Rate limit exceeded")
                    self.api_manager.handle_rate_limit_error(self.api_name)
                    raise Exception(f"{self.api_name}: Rate limit exceeded")
                
                return await response.json()
        except Exception as e:
            logging.error(f"{self.__class__.__name__}: Request failed for {url}: {str(e)}")
            raise 

    async def fetch_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> Optional[Any]:
        """Fetch with automatic retry on failure"""
        for attempt in range(max_retries):
            try:
                return await self.make_request(url, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"{self.__class__.__name__}: All retry attempts failed for {url}")
                    return None
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logging.warning(f"{self.__class__.__name__}: Retry attempt {attempt + 1} for {url} in {wait_time}s")
                await asyncio.sleep(wait_time) 