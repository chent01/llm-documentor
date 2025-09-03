"""
Query-level caching system for LLM backends.

This module provides intelligent caching of LLM queries and responses to avoid
redundant API calls and improve performance.
"""

import hashlib
import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached LLM query and response."""
    query_hash: str
    prompt: str
    system_prompt: Optional[str]
    context_chunks: Optional[List[str]]
    temperature: float
    max_tokens: Optional[int]
    response: str
    backend_name: str
    model_name: str
    created_at: datetime
    accessed_at: datetime
    access_count: int
    response_time: float
    token_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['accessed_at'] = self.accessed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['accessed_at'] = datetime.fromisoformat(data['accessed_at'])
        return cls(**data)


class LLMQueryCache:
    """
    Intelligent caching system for LLM queries and responses.
    
    Features:
    - Content-based cache keys (hash of prompt + parameters)
    - TTL-based expiration
    - LRU eviction policy
    - Statistics tracking
    - Configurable cache size limits
    """
    
    def __init__(self, 
                 cache_dir: str = "llm_cache",
                 max_entries: int = 1000,
                 default_ttl: int = 3600,  # 1 hour
                 max_cache_size_mb: int = 100):
        """
        Initialize the query cache.
        
        Args:
            cache_dir: Directory to store cache database
            max_entries: Maximum number of cache entries
            default_ttl: Default TTL in seconds
            max_cache_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.db_path = self.cache_dir / "query_cache.db"
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.max_cache_size_mb = max_cache_size_mb
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_queries': 0,
            'cache_size_bytes': 0,
            'avg_response_time_saved': 0.0
        }
        
        # Initialize database
        self._init_database()
        
        # Load statistics
        self._load_stats()
        
        logger.info(f"LLM Query Cache initialized: {self.db_path}")
        logger.info(f"Cache config: max_entries={max_entries}, ttl={default_ttl}s, max_size={max_cache_size_mb}MB")
    
    def _init_database(self):
        """Initialize the cache database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Cache entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    query_hash TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    system_prompt TEXT,
                    context_chunks TEXT,  -- JSON array
                    temperature REAL NOT NULL,
                    max_tokens INTEGER,
                    response TEXT NOT NULL,
                    backend_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    accessed_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    response_time REAL NOT NULL,
                    token_count INTEGER,
                    response_size INTEGER NOT NULL
                )
            """)
            
            # Cache statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_accessed_at 
                ON cache_entries(accessed_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created_at 
                ON cache_entries(created_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_backend_model 
                ON cache_entries(backend_name, model_name)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _generate_cache_key(self, 
                           prompt: str,
                           system_prompt: Optional[str] = None,
                           context_chunks: Optional[List[str]] = None,
                           temperature: float = 0.1,
                           max_tokens: Optional[int] = None) -> str:
        """
        Generate a cache key based on query parameters.
        
        Args:
            prompt: Main prompt
            system_prompt: System prompt
            context_chunks: Context chunks
            temperature: Temperature setting
            max_tokens: Max tokens setting
            
        Returns:
            SHA-256 hash as cache key
        """
        # Create a deterministic representation of the query
        cache_data = {
            'prompt': prompt,
            'system_prompt': system_prompt,
            'context_chunks': context_chunks or [],
            'temperature': round(temperature, 3),  # Round to avoid float precision issues
            'max_tokens': max_tokens
        }
        
        # Convert to JSON with sorted keys for consistency
        cache_json = json.dumps(cache_data, sort_keys=True, ensure_ascii=True)
        
        # Generate SHA-256 hash
        return hashlib.sha256(cache_json.encode('utf-8')).hexdigest()
    
    def get(self, 
            prompt: str,
            system_prompt: Optional[str] = None,
            context_chunks: Optional[List[str]] = None,
            temperature: float = 0.1,
            max_tokens: Optional[int] = None,
            backend_name: str = "unknown",
            model_name: str = "unknown") -> Optional[str]:
        """
        Get cached response for a query.
        
        Args:
            prompt: Main prompt
            system_prompt: System prompt
            context_chunks: Context chunks
            temperature: Temperature setting
            max_tokens: Max tokens setting
            backend_name: Name of the backend
            model_name: Name of the model
            
        Returns:
            Cached response if found and valid, None otherwise
        """
        query_hash = self._generate_cache_key(prompt, system_prompt, context_chunks, temperature, max_tokens)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get cache entry
                cursor.execute("""
                    SELECT * FROM cache_entries 
                    WHERE query_hash = ?
                """, (query_hash,))
                
                row = cursor.fetchone()
                if not row:
                    self.stats['misses'] += 1
                    self.stats['total_queries'] += 1
                    logger.debug(f"Cache MISS for query hash: {query_hash[:16]}...")
                    return None
                
                # Check if entry is expired
                created_at = datetime.fromisoformat(row['created_at'])
                if datetime.now() - created_at > timedelta(seconds=self.default_ttl):
                    # Entry expired, remove it
                    cursor.execute("DELETE FROM cache_entries WHERE query_hash = ?", (query_hash,))
                    conn.commit()
                    
                    self.stats['misses'] += 1
                    self.stats['total_queries'] += 1
                    logger.debug(f"Cache EXPIRED for query hash: {query_hash[:16]}...")
                    return None
                
                # Update access statistics
                cursor.execute("""
                    UPDATE cache_entries 
                    SET accessed_at = ?, access_count = access_count + 1
                    WHERE query_hash = ?
                """, (datetime.now().isoformat(), query_hash))
                conn.commit()
                
                # Update statistics
                self.stats['hits'] += 1
                self.stats['total_queries'] += 1
                
                response = row['response']
                response_time_saved = row['response_time']
                
                # Update average response time saved
                if self.stats['hits'] > 1:
                    self.stats['avg_response_time_saved'] = (
                        (self.stats['avg_response_time_saved'] * (self.stats['hits'] - 1) + response_time_saved) / 
                        self.stats['hits']
                    )
                else:
                    self.stats['avg_response_time_saved'] = response_time_saved
                
                logger.info(f"Cache HIT for query hash: {query_hash[:16]}... (saved {response_time_saved:.2f}s)")
                return response
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            self.stats['misses'] += 1
            self.stats['total_queries'] += 1
            return None
    
    def put(self,
            prompt: str,
            response: str,
            response_time: float,
            system_prompt: Optional[str] = None,
            context_chunks: Optional[List[str]] = None,
            temperature: float = 0.1,
            max_tokens: Optional[int] = None,
            backend_name: str = "unknown",
            model_name: str = "unknown",
            token_count: Optional[int] = None):
        """
        Store a query and response in the cache.
        
        Args:
            prompt: Main prompt
            response: Generated response
            response_time: Time taken to generate response
            system_prompt: System prompt
            context_chunks: Context chunks
            temperature: Temperature setting
            max_tokens: Max tokens setting
            backend_name: Name of the backend
            model_name: Name of the model
            token_count: Number of tokens in response
        """
        query_hash = self._generate_cache_key(prompt, system_prompt, context_chunks, temperature, max_tokens)
        
        try:
            # Check cache size limits before adding
            self._enforce_cache_limits()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now()
                response_size = len(response.encode('utf-8'))
                
                # Insert or replace cache entry
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_entries (
                        query_hash, prompt, system_prompt, context_chunks,
                        temperature, max_tokens, response, backend_name, model_name,
                        created_at, accessed_at, access_count, response_time,
                        token_count, response_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query_hash, prompt, system_prompt,
                    json.dumps(context_chunks) if context_chunks else None,
                    temperature, max_tokens, response, backend_name, model_name,
                    now.isoformat(), now.isoformat(), 1, response_time,
                    token_count, response_size
                ))
                
                conn.commit()
                
                # Update cache size statistics
                self.stats['cache_size_bytes'] += response_size
                
                logger.debug(f"Cache STORE for query hash: {query_hash[:16]}... ({response_size} bytes)")
                
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
    
    def _enforce_cache_limits(self):
        """Enforce cache size and entry count limits."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check entry count limit
                cursor.execute("SELECT COUNT(*) as count FROM cache_entries")
                entry_count = cursor.fetchone()['count']
                
                if entry_count >= self.max_entries:
                    # Remove oldest entries (LRU eviction)
                    entries_to_remove = entry_count - self.max_entries + 100  # Remove extra for efficiency
                    
                    cursor.execute("""
                        DELETE FROM cache_entries 
                        WHERE query_hash IN (
                            SELECT query_hash FROM cache_entries 
                            ORDER BY accessed_at ASC 
                            LIMIT ?
                        )
                    """, (entries_to_remove,))
                    
                    removed_count = cursor.rowcount
                    self.stats['evictions'] += removed_count
                    
                    logger.info(f"Cache eviction: removed {removed_count} old entries")
                
                # Check size limit
                cursor.execute("SELECT SUM(response_size) as total_size FROM cache_entries")
                total_size = cursor.fetchone()['total_size'] or 0
                max_size_bytes = self.max_cache_size_mb * 1024 * 1024
                
                if total_size > max_size_bytes:
                    # Remove entries until under size limit
                    cursor.execute("""
                        DELETE FROM cache_entries 
                        WHERE query_hash IN (
                            SELECT query_hash FROM cache_entries 
                            ORDER BY accessed_at ASC 
                            LIMIT (
                                SELECT COUNT(*) / 4 FROM cache_entries
                            )
                        )
                    """)
                    
                    removed_count = cursor.rowcount
                    self.stats['evictions'] += removed_count
                    
                    logger.info(f"Cache size eviction: removed {removed_count} entries")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error enforcing cache limits: {e}")
    
    def clear(self, older_than_hours: Optional[int] = None):
        """
        Clear cache entries.
        
        Args:
            older_than_hours: If specified, only clear entries older than this many hours
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if older_than_hours:
                    cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                    cursor.execute("""
                        DELETE FROM cache_entries 
                        WHERE created_at < ?
                    """, (cutoff_time.isoformat(),))
                    
                    removed_count = cursor.rowcount
                    logger.info(f"Cleared {removed_count} cache entries older than {older_than_hours} hours")
                else:
                    cursor.execute("DELETE FROM cache_entries")
                    removed_count = cursor.rowcount
                    logger.info(f"Cleared all {removed_count} cache entries")
                
                conn.commit()
                
                # Reset statistics
                if not older_than_hours:
                    self.stats['cache_size_bytes'] = 0
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current cache info
                cursor.execute("""
                    SELECT 
                        COUNT(*) as entry_count,
                        SUM(response_size) as total_size,
                        AVG(response_time) as avg_response_time,
                        SUM(access_count) as total_accesses,
                        MIN(created_at) as oldest_entry,
                        MAX(accessed_at) as newest_access
                    FROM cache_entries
                """)
                
                cache_info = cursor.fetchone()
                
                # Calculate hit rate
                hit_rate = (self.stats['hits'] / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0
                
                return {
                    'hit_rate_percent': round(hit_rate, 2),
                    'total_queries': self.stats['total_queries'],
                    'cache_hits': self.stats['hits'],
                    'cache_misses': self.stats['misses'],
                    'evictions': self.stats['evictions'],
                    'entry_count': cache_info['entry_count'] or 0,
                    'total_size_bytes': cache_info['total_size'] or 0,
                    'total_size_mb': round((cache_info['total_size'] or 0) / (1024 * 1024), 2),
                    'avg_response_time': round(cache_info['avg_response_time'] or 0, 3),
                    'avg_response_time_saved': round(self.stats['avg_response_time_saved'], 3),
                    'total_accesses': cache_info['total_accesses'] or 0,
                    'oldest_entry': cache_info['oldest_entry'],
                    'newest_access': cache_info['newest_access'],
                    'max_entries': self.max_entries,
                    'max_size_mb': self.max_cache_size_mb,
                    'default_ttl_seconds': self.default_ttl
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def _load_stats(self):
        """Load statistics from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM cache_stats")
                
                for row in cursor.fetchall():
                    key = row['key']
                    if key in self.stats:
                        try:
                            if key in ['hits', 'misses', 'evictions', 'total_queries']:
                                self.stats[key] = int(row['value'])
                            elif key in ['avg_response_time_saved', 'cache_size_bytes']:
                                self.stats[key] = float(row['value'])
                        except (ValueError, TypeError):
                            pass
                            
        except Exception as e:
            logger.debug(f"Could not load cache statistics: {e}")
    
    def _save_stats(self):
        """Save statistics to database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for key, value in self.stats.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO cache_stats (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, str(value), datetime.now().isoformat()))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving cache statistics: {e}")
    
    def __del__(self):
        """Save statistics when cache is destroyed."""
        try:
            self._save_stats()
        except:
            pass


# Global cache instance
_global_cache: Optional[LLMQueryCache] = None


def get_global_cache() -> LLMQueryCache:
    """Get or create the global LLM query cache instance."""
    global _global_cache
    
    if _global_cache is None:
        _global_cache = LLMQueryCache()
    
    return _global_cache


def clear_global_cache():
    """Clear the global cache."""
    global _global_cache
    
    if _global_cache:
        _global_cache.clear()
        _global_cache = None