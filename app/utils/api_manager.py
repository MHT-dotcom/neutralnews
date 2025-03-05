import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..config.api_config import API_QUOTAS, API_CONFIGS, RETRY_CONFIG

@dataclass
class APIQuota:
    requests_per_second: int
    requests_per_minute: int
    requests_per_day: int
    current_second: int = 0
    current_minute: int = 0
    current_day: int = 0
    last_second_reset: float = time.time()
    last_minute_reset: float = time.time()
    last_day_reset: float = time.time()

class APIManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.quotas: Dict[str, APIQuota] = {}
        for api_name, quota_config in API_QUOTAS.items():
            self.quotas[api_name] = APIQuota(
                requests_per_second=quota_config['requests_per_second'],
                requests_per_minute=quota_config['requests_per_minute'],
                requests_per_day=quota_config['requests_per_day']
            )
        
        self.api_keys: Dict[str, Dict[str, str]] = {}
        self.last_key_rotation: Dict[str, float] = {}
        self.configs = API_CONFIGS
        self.retry_config = RETRY_CONFIG
        self._initialized = True
        logging.info("APIManager initialized with configurations from api_config.py")

    def can_make_request(self, api_name: str) -> bool:
        if api_name not in self.quotas:
            logging.error(f"No quota configuration found for API: {api_name}")
            return False

        quota = self.quotas[api_name]
        current_time = time.time()

        # Reset counters if needed
        if current_time - quota.last_second_reset >= 1:
            quota.current_second = 0
            quota.last_second_reset = current_time
            
        if current_time - quota.last_minute_reset >= 60:
            quota.current_minute = 0
            quota.last_minute_reset = current_time
            
        if current_time - quota.last_day_reset >= 86400:
            quota.current_day = 0
            quota.last_day_reset = current_time

        # Check if we're within limits
        if (quota.current_second < quota.requests_per_second and
            quota.current_minute < quota.requests_per_minute and
            quota.current_day < quota.requests_per_day):
            
            quota.current_second += 1
            quota.current_minute += 1
            quota.current_day += 1
            logging.debug(f"{api_name} request allowed. Second: {quota.current_second}/{quota.requests_per_second}, "
                         f"Minute: {quota.current_minute}/{quota.requests_per_minute}, "
                         f"Day: {quota.current_day}/{quota.requests_per_day}")
            return True
            
        logging.warning(f"{api_name} rate limit reached. Second: {quota.current_second}/{quota.requests_per_second}, "
                       f"Minute: {quota.current_minute}/{quota.requests_per_minute}, "
                       f"Day: {quota.current_day}/{quota.requests_per_day}")
        return False

    def get_api_key(self, api_name: str) -> Optional[str]:
        if not self.configs.get(api_name, {}).get('requires_key', False):
            return None
            
        if api_name not in self.api_keys:
            logging.error(f"No API keys configured for: {api_name}")
            return None
            
        keys = self.api_keys[api_name]
        if not keys:
            logging.error(f"No valid API keys available for: {api_name}")
            return None
            
        # Simple round-robin key rotation
        current_time = time.time()
        if api_name not in self.last_key_rotation or current_time - self.last_key_rotation[api_name] >= 3600:
            self.last_key_rotation[api_name] = current_time
            # Rotate to next key if available
            current_key = list(keys.keys())[0]
            rotated_keys = {k: keys[k] for k in list(keys.keys())[1:] + [current_key]}
            self.api_keys[api_name] = rotated_keys
            logging.info(f"Rotated API key for {api_name}")
            
        return list(self.api_keys[api_name].values())[0]

    def register_api_key(self, api_name: str, key_id: str, key_value: str) -> None:
        if api_name not in self.api_keys:
            self.api_keys[api_name] = {}
        self.api_keys[api_name][key_id] = key_value
        logging.info(f"Registered new API key for {api_name} with ID: {key_id}")

    def handle_rate_limit_error(self, api_name: str) -> None:
        """Record rate limit errors and adjust quotas if needed"""
        if api_name in self.quotas:
            quota = self.quotas[api_name]
            # Temporarily reduce quotas by 25% if we hit rate limits
            quota.requests_per_minute = max(1, int(quota.requests_per_minute * 0.75))
            quota.requests_per_day = max(10, int(quota.requests_per_day * 0.75))
            logging.warning(f"Adjusted quotas for {api_name} due to rate limit error. "
                          f"New limits - Minute: {quota.requests_per_minute}, Day: {quota.requests_per_day}")

    def handle_auth_error(self, api_name: str, key_id: str) -> None:
        """Handle authentication errors by removing invalid keys"""
        if api_name in self.api_keys and key_id in self.api_keys[api_name]:
            del self.api_keys[api_name][key_id]
            logging.error(f"Removed invalid API key for {api_name} with ID: {key_id}")

    def get_retry_config(self, api_name: str) -> dict:
        """Get retry configuration for specific API"""
        return self.retry_config 