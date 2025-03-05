import logging
import aiohttp
from urllib.parse import urlparse
from typing import Any

class BaseFetcher:
    async def make_request(self, url: str, **kwargs) -> Any:
        try:
            logging.info(f"{self.__class__.__name__}: DNS pre-request check for {urlparse(url).netloc}")
            # Try DNS resolution before making request
            try:
                import socket
                socket.gethostbyname(urlparse(url).netloc)
                logging.info(f"{self.__class__.__name__}: DNS resolution successful for {urlparse(url).netloc}")
            except socket.gaierror as e:
                logging.error(f"{self.__class__.__name__}: DNS resolution failed for {urlparse(url).netloc}: {str(e)}")
                
            # Log request details
            logging.info(f"{self.__class__.__name__}: Making request to {url} with headers: {kwargs.get('headers', {})}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, **kwargs) as response:
                    logging.info(f"{self.__class__.__name__}: Response status {response.status} for {url}")
                    if response.status == 403:
                        logging.error(f"{self.__class__.__name__}: Authentication failed with headers: {kwargs.get('headers', {})}")
                    return await response.json()
        except Exception as e:
            logging.error(f"{self.__class__.__name__}: Request failed for {url}: {str(e)}")
            raise 