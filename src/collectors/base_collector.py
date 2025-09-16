"""
Base collector class with common functionality for all data collectors.
"""
import asyncio
import aiohttp
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from ratelimit import limits, sleep_and_retry
import structlog

logger = structlog.get_logger()

class BaseCollector(ABC):
    """Base class for all data collectors."""
    
    def __init__(self, timeout: int = 30, rate_limit_calls: int = 10, rate_limit_period: int = 60):
        self.timeout = timeout
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @sleep_and_retry
    @limits(calls=10, period=60)
    async def make_request(self, url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make rate-limited HTTP request."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
                
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Request failed with status {response.status} for URL: {url}")
                    return None
        except Exception as e:
            logger.error(f"Request error for URL {url}: {str(e)}")
            return None
    
    @abstractmethod
    async def collect_data(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Abstract method for collecting data. Must be implemented by subclasses."""
        pass
    
    def normalize_data(self, raw_data: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize raw data to a standard format."""
        normalized = []
        for item in raw_data:
            try:
                normalized_item = self._normalize_item(item)
                if normalized_item:
                    normalized.append(normalized_item)
            except Exception as e:
                logger.warning(f"Failed to normalize item: {str(e)}")
                continue
        return normalized
    
    @abstractmethod
    def _normalize_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """Normalize a single data item. Must be implemented by subclasses."""
        pass
    
    def handle_unavailable_source(self, source_name: str) -> Dict[str, Any]:
        """Return standard response when a source is unavailable."""
        return {
            "notes": [f"{source_name} source unavailable"],
            "data": [],
            "timestamp": time.time()
        }

