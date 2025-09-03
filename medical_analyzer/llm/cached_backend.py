"""
Cached LLM backend wrapper that adds query-level caching to any LLM backend.

This module provides a transparent caching layer that can wrap any LLM backend
to avoid redundant API calls and improve performance.
"""

import time
import logging
from typing import List, Optional, Dict, Any

from .backend import LLMBackend, LLMError, ModelInfo
from .query_cache import LLMQueryCache, get_global_cache


logger = logging.getLogger(__name__)


class CachedLLMBackend(LLMBackend):
    """
    Cached wrapper for LLM backends that adds intelligent query-level caching.
    
    This wrapper transparently adds caching to any LLM backend without changing
    the interface. It caches responses based on query content and parameters.
    """
    
    def __init__(self, 
                 backend: LLMBackend, 
                 cache: Optional[LLMQueryCache] = None,
                 cache_enabled: bool = True):
        """
        Initialize cached backend wrapper.
        
        Args:
            backend: The underlying LLM backend to wrap
            cache: Optional cache instance (uses global cache if None)
            cache_enabled: Whether caching is enabled
        """
        # Initialize with the wrapped backend's config
        super().__init__(backend.config)
        
        self.backend = backend
        self.cache = cache or get_global_cache()
        self.cache_enabled = cache_enabled
        
        # Copy circuit breaker state from wrapped backend
        self._failure_count = backend._failure_count
        self._last_failure_time = backend._last_failure_time
        self._circuit_open = backend._circuit_open
        
        logger.info(f"Initialized CachedLLMBackend wrapping {backend.__class__.__name__}")
        logger.info(f"Cache enabled: {cache_enabled}")
    
    def generate(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text with caching support.
        
        First checks cache for existing response, then falls back to backend
        if not found. Stores successful responses in cache.
        
        Args:
            prompt: The main prompt for generation
            context_chunks: Optional list of context chunks for RAG
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt for instruction
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If generation fails
        """
        start_time = time.time()
        
        # Get model info for cache key
        try:
            model_info = self.get_model_info()
            backend_name = self.backend.__class__.__name__
            model_name = model_info.name if model_info else "unknown"
        except:
            backend_name = self.backend.__class__.__name__
            model_name = "unknown"
        
        # Check cache first if enabled
        if self.cache_enabled:
            try:
                cached_response = self.cache.get(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context_chunks=context_chunks,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    backend_name=backend_name,
                    model_name=model_name
                )
                
                if cached_response is not None:
                    cache_time = time.time() - start_time
                    logger.debug(f"Cache hit - returned response in {cache_time:.3f}s")
                    return cached_response
                    
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")
                # Continue with backend call
        
        # Cache miss or caching disabled - call backend
        try:
            logger.debug("Cache miss - calling backend")
            backend_start = time.time()
            
            response = self.backend.generate(
                prompt=prompt,
                context_chunks=context_chunks,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
            
            backend_time = time.time() - backend_start
            
            # Store in cache if enabled and response is valid
            if self.cache_enabled and response and len(response.strip()) > 0:
                try:
                    # Estimate token count (rough approximation)
                    token_count = len(response.split()) * 1.3  # Rough estimate
                    
                    self.cache.put(
                        prompt=prompt,
                        response=response,
                        response_time=backend_time,
                        system_prompt=system_prompt,
                        context_chunks=context_chunks,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        backend_name=backend_name,
                        model_name=model_name,
                        token_count=int(token_count)
                    )
                    
                    logger.debug(f"Stored response in cache (backend time: {backend_time:.3f}s)")
                    
                except Exception as e:
                    logger.warning(f"Failed to store response in cache: {e}")
            
            total_time = time.time() - start_time
            logger.debug(f"Generated response in {total_time:.3f}s (backend: {backend_time:.3f}s)")
            
            return response
            
        except Exception as e:
            # Update circuit breaker state
            self._record_failure()
            raise
    
    def is_available(self) -> bool:
        """Check if the wrapped backend is available."""
        return self.backend.is_available()
    
    def get_model_info(self) -> ModelInfo:
        """Get model info from wrapped backend."""
        return self.backend.get_model_info()
    
    def get_required_config_keys(self) -> List[str]:
        """Get required config keys from wrapped backend."""
        return self.backend.get_required_config_keys()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check including cache statistics."""
        backend_health = self.backend.health_check()
        
        # Add cache statistics
        cache_stats = {}
        if self.cache_enabled:
            try:
                cache_stats = self.cache.get_statistics()
            except Exception as e:
                cache_stats = {'error': str(e)}
        
        return {
            **backend_health,
            'cache_enabled': self.cache_enabled,
            'cache_stats': cache_stats,
            'wrapper': 'CachedLLMBackend'
        }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        if not self.cache_enabled:
            return {'cache_enabled': False}
        
        try:
            return self.cache.get_statistics()
        except Exception as e:
            return {'error': str(e)}
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """
        Clear the cache.
        
        Args:
            older_than_hours: If specified, only clear entries older than this many hours
        """
        if self.cache_enabled:
            try:
                self.cache.clear(older_than_hours)
                logger.info(f"Cache cleared (older_than_hours={older_than_hours})")
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
        else:
            logger.warning("Cache is disabled - cannot clear")
    
    def enable_cache(self):
        """Enable caching."""
        self.cache_enabled = True
        logger.info("Cache enabled")
    
    def disable_cache(self):
        """Disable caching."""
        self.cache_enabled = False
        logger.info("Cache disabled")
    
    def __getattr__(self, name):
        """Delegate unknown attributes to the wrapped backend."""
        return getattr(self.backend, name)


def create_cached_backend(backend: LLMBackend, 
                         cache_config: Optional[Dict[str, Any]] = None) -> CachedLLMBackend:
    """
    Create a cached wrapper for an LLM backend.
    
    Args:
        backend: The backend to wrap
        cache_config: Optional cache configuration
        
    Returns:
        CachedLLMBackend instance
    """
    cache = None
    cache_enabled = True
    
    if cache_config:
        cache_enabled = cache_config.get('enabled', True)
        
        if cache_enabled:
            cache = LLMQueryCache(
                cache_dir=cache_config.get('cache_dir', 'llm_cache'),
                max_entries=cache_config.get('max_entries', 1000),
                default_ttl=cache_config.get('default_ttl', 3600),
                max_cache_size_mb=cache_config.get('max_cache_size_mb', 100)
            )
    
    return CachedLLMBackend(backend, cache, cache_enabled)