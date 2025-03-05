import logging
from typing import Any, Optional

class Cache:
    def __init__(self):
        self._cache = {}
        self._initialized = False
        logging.info("Cache instance created")

    def initialize(self):
        if not self._initialized:
            logging.info("Initializing cache")
            try:
                self._cache = {}
                self._initialized = True
                logging.info("Cache successfully initialized")
            except Exception as e:
                logging.error(f"Cache initialization failed: {str(e)}")
                raise
        else:
            logging.info("Cache already initialized")

    @property
    def is_initialized(self):
        logging.debug(f"Cache initialization status checked: {self._initialized}")
        return self._initialized

    def get(self, key: str) -> Optional[Any]:
        if not self._initialized:
            logging.warning("Attempted to get from uninitialized cache")
            return None
        
        value = self._cache.get(key)
        logging.debug(f"Cache get for key '{key}': {'hit' if value is not None else 'miss'}")
        return value

    def set(self, key: str, value: Any) -> None:
        if not self._initialized:
            logging.warning("Attempted to set in uninitialized cache")
            return
            
        self._cache[key] = value
        logging.debug(f"Cache set for key '{key}'") 