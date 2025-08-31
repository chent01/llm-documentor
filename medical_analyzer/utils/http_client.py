"""
HTTP client utility with caching and connection pooling to reduce redundant requests.
"""

import time
import requests
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class CachedHTTPClient:
    """
    HTTP client with response caching and connection pooling.
    
    This client reduces redundant requests by:
    - Caching GET responses for a configurable TTL
    - Reusing HTTP connections via session pooling
    - Providing circuit breaker functionality for failed endpoints
    """
    
    def __init__(self, 
                 cache_ttl: int = 30,
                 max_cache_size: int = 100,
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        Initialize the cached HTTP client.
        
        Args:
            cache_ttl: Time-to-live for cached responses in seconds
            max_cache_size: Maximum number of cached responses
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Response cache: {cache_key: (response_data, timestamp)}
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = Lock()
        
        # Session pool for connection reuse
        self._sessions: Dict[str, requests.Session] = {}
        self._session_lock = Lock()
        
        # Circuit breaker for failed endpoints
        self._failed_endpoints: Dict[str, float] = {}
        self._failure_threshold = 5  # Number of failures before circuit opens
        self._circuit_reset_time = 300  # 5 minutes
    
    def _get_cache_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key for the request."""
        key_parts = [method.upper(), url]
        if params:
            # Sort params for consistent cache keys
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))
        return "|".join(key_parts)
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if still valid."""
        with self._cache_lock:
            if cache_key in self._cache:
                response_data, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return response_data
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
                    logger.debug(f"Cache expired for key: {cache_key}")
        return None
    
    def _cache_response(self, cache_key: str, response_data: Any) -> None:
        """Cache a response."""
        with self._cache_lock:
            # Implement LRU eviction if cache is full
            if len(self._cache) >= self.max_cache_size:
                # Remove oldest entry
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")
            
            self._cache[cache_key] = (response_data, time.time())
            logger.debug(f"Cached response for key: {cache_key}")
    
    def _get_session(self, base_url: str) -> requests.Session:
        """Get or create a session for the base URL."""
        with self._session_lock:
            if base_url not in self._sessions:
                session = requests.Session()
                # Configure session for better performance
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=self.max_retries
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                self._sessions[base_url] = session
                logger.debug(f"Created new session for: {base_url}")
            
            return self._sessions[base_url]
    
    def _is_endpoint_failed(self, url: str) -> bool:
        """Check if endpoint is in circuit breaker state."""
        if url in self._failed_endpoints:
            failure_time = self._failed_endpoints[url]
            if time.time() - failure_time < self._circuit_reset_time:
                return True
            else:
                # Reset circuit breaker
                del self._failed_endpoints[url]
        return False
    
    def _mark_endpoint_failed(self, url: str) -> None:
        """Mark endpoint as failed for circuit breaker."""
        self._failed_endpoints[url] = time.time()
        logger.warning(f"Marked endpoint as failed: {url}")
    
    def get(self, url: str, 
            params: Optional[Dict] = None,
            headers: Optional[Dict] = None,
            use_cache: bool = True) -> Optional[requests.Response]:
        """
        Perform GET request with caching.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            use_cache: Whether to use response caching
            
        Returns:
            Response object or None if request failed
        """
        # Check circuit breaker
        if self._is_endpoint_failed(url):
            logger.warning(f"Endpoint in circuit breaker state: {url}")
            return None
        
        # Check cache for GET requests
        if use_cache:
            cache_key = self._get_cache_key("GET", url, params)
            cached_response = self._get_cached_response(cache_key)
            if cached_response is not None:
                return cached_response
        
        try:
            # Extract base URL for session pooling
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            session = self._get_session(base_url)
            
            response = session.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            
            # Cache successful GET responses
            if use_cache and response.status_code == 200:
                cache_key = self._get_cache_key("GET", url, params)
                self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"GET request failed for {url}: {e}")
            self._mark_endpoint_failed(url)
            return None
    
    def post(self, url: str,
             json: Optional[Dict] = None,
             data: Optional[Dict] = None,
             headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Perform POST request (no caching).
        
        Args:
            url: Request URL
            json: JSON payload
            data: Form data
            headers: Request headers
            
        Returns:
            Response object or None if request failed
        """
        # Check circuit breaker
        if self._is_endpoint_failed(url):
            logger.warning(f"Endpoint in circuit breaker state: {url}")
            return None
        
        try:
            # Extract base URL for session pooling
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            session = self._get_session(base_url)
            
            response = session.post(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            
            return response
            
        except Exception as e:
            logger.error(f"POST request failed for {url}: {e}")
            self._mark_endpoint_failed(url)
            return None
    
    def clear_cache(self) -> None:
        """Clear all cached responses."""
        with self._cache_lock:
            self._cache.clear()
            logger.info("Cleared HTTP response cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                'cache_size': len(self._cache),
                'max_cache_size': self.max_cache_size,
                'cache_ttl': self.cache_ttl,
                'failed_endpoints': len(self._failed_endpoints)
            }
    
    def close(self) -> None:
        """Close all sessions and clear resources."""
        with self._session_lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
        
        self.clear_cache()
        logger.info("Closed HTTP client and cleared resources")


# Global shared client instance
_shared_client: Optional[CachedHTTPClient] = None
_client_lock = Lock()


def get_shared_http_client() -> CachedHTTPClient:
    """
    Get the shared HTTP client instance.
    
    Returns:
        Shared CachedHTTPClient instance
    """
    global _shared_client
    
    with _client_lock:
        if _shared_client is None:
            _shared_client = CachedHTTPClient()
            logger.info("Created shared HTTP client")
        
        return _shared_client


def reset_shared_http_client() -> None:
    """Reset the shared HTTP client (useful for testing)."""
    global _shared_client
    
    with _client_lock:
        if _shared_client is not None:
            _shared_client.close()
            _shared_client = None
            logger.info("Reset shared HTTP client")