"""
Local server backend implementation for LLM integration.

This module provides integration with local LLM servers via REST API,
supporting various local model servers for medical device software analysis.
"""

import json
import requests
import time
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import urljoin
import traceback
import sys
import threading
from datetime import datetime, timedelta

from .backend import LLMBackend, LLMError, ModelInfo, ModelType
from .api_response_validator import APIResponseValidator, ValidationResult, RecoveryAction
from ..utils.http_client import get_shared_http_client

logger = logging.getLogger(__name__)

# Create a dedicated debug logger for LLM operations
debug_logger = logging.getLogger(f"{__name__}.debug")

# Create specialized loggers for different aspects
connection_logger = logging.getLogger(f"{__name__}.connection")
performance_logger = logging.getLogger(f"{__name__}.performance")
request_logger = logging.getLogger(f"{__name__}.requests")
response_logger = logging.getLogger(f"{__name__}.responses")
error_logger = logging.getLogger(f"{__name__}.errors")

class LLMDebugLogger:
    """Enhanced debugging logger for LLM operations."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.request_counter = 0
        self.active_requests = {}  # Track active requests
        self.request_history = []  # Keep history of recent requests
        self.max_history = 100
        self._lock = threading.Lock()
        
    def log_request_start(self, operation: str, **kwargs) -> int:
        """Log the start of an LLM request."""
        with self._lock:
            self.request_counter += 1
            request_id = self.request_counter
            
            start_time = time.time()
            request_info = {
                'id': request_id,
                'operation': operation,
                'start_time': start_time,
                'parameters': kwargs,
                'status': 'started'
            }
            
            self.active_requests[request_id] = request_info
            
            # Log with different levels based on debug settings
            self.logger.info(f"[REQ-{request_id:04d}] Starting {operation}")
            request_logger.debug(f"[REQ-{request_id:04d}] Request parameters: {kwargs}")
            
            # Log system state
            active_count = len(self.active_requests)
            if active_count > 1:
                self.logger.debug(f"[REQ-{request_id:04d}] Active requests: {active_count}")
            
            return request_id
    
    def log_request_details(self, request_id: int, url: str, headers: Dict, data: Dict):
        """Log detailed request information."""
        # Sanitize headers (remove sensitive info)
        safe_headers = {k: v if k.lower() != 'authorization' else '***' for k, v in headers.items()}
        
        # Update active request info
        with self._lock:
            if request_id in self.active_requests:
                self.active_requests[request_id]['url'] = url
                self.active_requests[request_id]['headers'] = safe_headers
                self.active_requests[request_id]['data_size'] = len(json.dumps(data))
        
        connection_logger.debug(f"[REQ-{request_id:04d}] URL: {url}")
        connection_logger.debug(f"[REQ-{request_id:04d}] Headers: {safe_headers}")
        
        # Log request data with truncation for large prompts
        if 'prompt' in data:
            prompt = data['prompt']
            prompt_length = len(prompt)
            if prompt_length > 500:
                request_logger.debug(f"[REQ-{request_id:04d}] Prompt ({prompt_length} chars, truncated): {prompt[:500]}...")
            else:
                request_logger.debug(f"[REQ-{request_id:04d}] Prompt ({prompt_length} chars): {prompt}")
        
        if 'messages' in data:
            messages = data['messages']
            total_content_length = sum(len(msg.get('content', '')) for msg in messages)
            request_logger.debug(f"[REQ-{request_id:04d}] Messages: {len(messages)} messages, {total_content_length} total chars")
            
            for i, msg in enumerate(messages):
                content = msg.get('content', '')
                role = msg.get('role', 'unknown')
                if len(content) > 200:
                    request_logger.debug(f"[REQ-{request_id:04d}] Message {i} ({role}, {len(content)} chars): {content[:200]}...")
                else:
                    request_logger.debug(f"[REQ-{request_id:04d}] Message {i} ({role}, {len(content)} chars): {content}")
        
        # Log other important parameters with more detail
        for key in ['temperature', 'max_tokens', 'model', 'stop', 'stream', 'top_p', 'frequency_penalty', 'presence_penalty']:
            if key in data:
                request_logger.debug(f"[REQ-{request_id:04d}] {key}: {data[key]}")
        
        # Log request size and complexity metrics
        data_size = len(json.dumps(data))
        request_logger.debug(f"[REQ-{request_id:04d}] Request size: {data_size} bytes")
    
    def log_response_details(self, request_id: int, response: requests.Response, response_time: float):
        """Log detailed response information."""
        # Update active request info
        with self._lock:
            if request_id in self.active_requests:
                self.active_requests[request_id]['response_time'] = response_time
                self.active_requests[request_id]['status_code'] = response.status_code
                self.active_requests[request_id]['response_size'] = len(response.content)
        
        # Log performance metrics
        performance_logger.info(f"[REQ-{request_id:04d}] Response received in {response_time:.2f}s - Status: {response.status_code}")
        
        # Log response headers with useful metrics
        response_headers = dict(response.headers)
        content_length = response_headers.get('content-length', 'unknown')
        content_type = response_headers.get('content-type', 'unknown')
        
        connection_logger.debug(f"[REQ-{request_id:04d}] Response headers: Content-Length: {content_length}, Content-Type: {content_type}")
        connection_logger.debug(f"[REQ-{request_id:04d}] All response headers: {response_headers}")
        
        # Log response content with better analysis
        try:
            response_size = len(response.content)
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                response_str = json.dumps(response_data, indent=2)
                
                # Extract useful metrics from response
                if 'choices' in response_data:
                    choices_count = len(response_data['choices'])
                    if choices_count > 0:
                        first_choice = response_data['choices'][0]
                        if 'message' in first_choice:
                            content = first_choice['message'].get('content', '')
                            response_logger.info(f"[REQ-{request_id:04d}] Generated {len(content)} characters in {choices_count} choices")
                        elif 'text' in first_choice:
                            content = first_choice.get('text', '')
                            response_logger.info(f"[REQ-{request_id:04d}] Generated {len(content)} characters in {choices_count} choices")
                
                # Log usage statistics if available
                if 'usage' in response_data:
                    usage = response_data['usage']
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)
                    performance_logger.info(f"[REQ-{request_id:04d}] Token usage: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total")
                
                # Log full response at debug level
                if len(response_str) > 1000:
                    response_logger.debug(f"[REQ-{request_id:04d}] Response ({response_size} bytes, truncated): {response_str[:1000]}...")
                else:
                    response_logger.debug(f"[REQ-{request_id:04d}] Response ({response_size} bytes): {response_str}")
            else:
                content = response.text
                response_logger.info(f"[REQ-{request_id:04d}] Non-JSON response: {response_size} bytes")
                if len(content) > 500:
                    response_logger.debug(f"[REQ-{request_id:04d}] Response text (truncated): {content[:500]}...")
                else:
                    response_logger.debug(f"[REQ-{request_id:04d}] Response text: {content}")
        except Exception as e:
            error_logger.warning(f"[REQ-{request_id:04d}] Could not parse response content: {e}")
            response_logger.debug(f"[REQ-{request_id:04d}] Raw response: {response.content[:500]}...")
    
    def log_error(self, request_id: int, error: Exception, context: Dict[str, Any] = None):
        """Log error information with context."""
        # Update active request info
        with self._lock:
            if request_id in self.active_requests:
                self.active_requests[request_id]['error'] = str(error)
                self.active_requests[request_id]['error_type'] = type(error).__name__
                self.active_requests[request_id]['status'] = 'error'
        
        error_type = type(error).__name__
        error_logger.error(f"[REQ-{request_id:04d}] Error: {error_type}: {error}")
        
        if context:
            error_logger.error(f"[REQ-{request_id:04d}] Error context: {context}")
            
            # Log specific error patterns for common issues
            if isinstance(error, requests.exceptions.ConnectionError):
                connection_logger.error(f"[REQ-{request_id:04d}] Connection failed - check if LLM server is running")
            elif isinstance(error, requests.exceptions.Timeout):
                performance_logger.error(f"[REQ-{request_id:04d}] Request timeout - server may be overloaded")
            elif isinstance(error, requests.exceptions.HTTPError):
                connection_logger.error(f"[REQ-{request_id:04d}] HTTP error - check server configuration")
        
        # Log full traceback at debug level
        error_logger.debug(f"[REQ-{request_id:04d}] Full traceback:\n{traceback.format_exc()}")
    
    def log_retry_attempt(self, request_id: int, attempt: int, max_attempts: int, delay: float, reason: str):
        """Log retry attempt information."""
        # Update active request info
        with self._lock:
            if request_id in self.active_requests:
                retries = self.active_requests[request_id].get('retries', [])
                retries.append({'attempt': attempt, 'reason': reason, 'delay': delay})
                self.active_requests[request_id]['retries'] = retries
        
        performance_logger.warning(f"[REQ-{request_id:04d}] Retry {attempt}/{max_attempts} in {delay:.2f}s - Reason: {reason}")
        
        # Log retry patterns for analysis
        if attempt == 1:
            error_logger.info(f"[REQ-{request_id:04d}] First retry due to: {reason}")
        elif attempt >= max_attempts - 1:
            error_logger.warning(f"[REQ-{request_id:04d}] Final retry attempt - {reason}")
    
    def log_success(self, request_id: int, content_length: int, processing_time: float):
        """Log successful completion."""
        # Update active request info and move to history
        with self._lock:
            if request_id in self.active_requests:
                request_info = self.active_requests[request_id]
                request_info['status'] = 'completed'
                request_info['content_length'] = content_length
                request_info['total_time'] = processing_time
                request_info['end_time'] = time.time()
                
                # Move to history
                self.request_history.append(request_info)
                if len(self.request_history) > self.max_history:
                    self.request_history.pop(0)
                
                del self.active_requests[request_id]
        
        performance_logger.info(f"[REQ-{request_id:04d}] Success - Generated {content_length} characters in {processing_time:.2f}s")
        
        # Log performance metrics
        if processing_time > 10:
            performance_logger.warning(f"[REQ-{request_id:04d}] Slow response: {processing_time:.2f}s")
        elif processing_time < 1:
            performance_logger.debug(f"[REQ-{request_id:04d}] Fast response: {processing_time:.2f}s")
    
    def log_connection_test(self, url: str, success: bool, response_time: float = None, error: str = None):
        """Log connection test results."""
        if success:
            connection_logger.info(f"Connection test SUCCESS: {url} ({response_time:.2f}s)")
        else:
            connection_logger.error(f"Connection test FAILED: {url} - {error}")
    
    def log_model_info(self, model_info: Dict[str, Any]):
        """Log model information."""
        connection_logger.info(f"Model info retrieved: {json.dumps(model_info, indent=2)}")
    
    def get_active_requests_summary(self) -> Dict[str, Any]:
        """Get summary of currently active requests."""
        with self._lock:
            return {
                'active_count': len(self.active_requests),
                'requests': list(self.active_requests.values())
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from recent requests."""
        with self._lock:
            if not self.request_history:
                return {'message': 'No completed requests'}
            
            recent_requests = self.request_history[-20:]  # Last 20 requests
            
            response_times = [r.get('response_time', 0) for r in recent_requests if r.get('response_time')]
            total_times = [r.get('total_time', 0) for r in recent_requests if r.get('total_time')]
            content_lengths = [r.get('content_length', 0) for r in recent_requests if r.get('content_length')]
            
            return {
                'recent_requests': len(recent_requests),
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'avg_total_time': sum(total_times) / len(total_times) if total_times else 0,
                'avg_content_length': sum(content_lengths) / len(content_lengths) if content_lengths else 0,
                'success_rate': len([r for r in recent_requests if r.get('status') == 'completed']) / len(recent_requests) * 100
            }

# Global debug logger instance
llm_debug = LLMDebugLogger(f"{__name__}.debug")


class LocalServerBackend(LLMBackend):
    """
    LLM backend implementation for local REST API servers.
    
    This backend integrates with local LLM servers (like text-generation-webui,
    LocalAI, or custom servers) via REST API for medical software analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LocalServer backend.
        
        Args:
            config: Configuration dictionary with server settings
        """
        super().__init__(config)
        self._model_info = None
        
        # Enhanced logging for initialization
        sanitized_config = self._sanitize_config_for_logging(config)
        logger.info(f"Initializing LocalServerBackend with config: {sanitized_config}")
        connection_logger.debug(f"Full initialization config: {sanitized_config}")
        
        # Use shared HTTP client for better connection pooling and caching
        self._http_client = get_shared_http_client()
        connection_logger.debug("Shared HTTP client initialized")
        
        # Legacy session attribute for backward compatibility with tests
        self._session = requests.Session()
        
        # Configure session for better connection handling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=3,
            pool_block=False
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        connection_logger.debug("HTTP session configured with connection pooling")
        
        # Set connection keep-alive headers
        self._session.headers.update({
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=30, max=100'
        })
        connection_logger.debug("Keep-alive headers configured")
        
        # Initialize API response validator
        self._validator = APIResponseValidator()
        
        # Caching for availability and model info
        self._availability_cache = None
        self._availability_cache_time = 0
        self._availability_cache_ttl = 30  # Cache availability for 30 seconds
        
        self._model_info_cache = None
        self._model_info_cache_time = 0
        self._model_info_cache_ttl = 300  # Cache model info for 5 minutes
        
        # Response caching for improved performance
        self._response_cache: Dict[str, Any] = {}
        self._response_cache_ttl = 300  # 5 minutes
        
        # Retry configuration
        self._max_retries = config.get('max_retries', 3)
        self._base_retry_delay = config.get('base_retry_delay', 1.0)
        
        # Debug configuration with enhanced options
        self._debug_enabled = config.get('debug_enabled', False)
        self._log_requests = config.get('log_requests', self._debug_enabled)
        self._log_responses = config.get('log_responses', self._debug_enabled)
        self._log_connections = config.get('log_connections', self._debug_enabled)
        self._log_performance = config.get('log_performance', True)  # Always enabled for performance monitoring
        
        # Performance tracking with more detailed metrics
        self._request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'cache_hits': 0,
            'connection_errors': 0,
            'timeout_errors': 0,
            'http_errors': 0,
            'retry_attempts': 0,
            'avg_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0,
            'last_request_time': None,
            'first_request_time': None
        }
        
        # Connection health tracking
        self._connection_health = {
            'last_successful_connection': None,
            'consecutive_failures': 0,
            'total_connection_attempts': 0,
            'successful_connections': 0,
            'last_error': None,
            'server_info': None
        }
        
        # Prepare headers for API requests
        self._headers = {"Content-Type": "application/json"}
        api_key = self.config.get("api_key")
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
            self._session.headers["Authorization"] = f"Bearer {api_key}"
            logger.debug("API key configured for authentication")
        
        # Log connection configuration with detailed info
        base_url = config.get('base_url', 'Not configured')
        timeout = config.get('timeout', 30)
        connection_logger.info(f"LocalServer backend configured - URL: {base_url}, Timeout: {timeout}s, Max retries: {self._max_retries}")
        
        # Log debug settings
        debug_settings = {
            'debug_enabled': self._debug_enabled,
            'log_requests': self._log_requests,
            'log_responses': self._log_responses,
            'log_connections': self._log_connections,
            'log_performance': self._log_performance
        }
        logger.debug(f"Debug settings: {debug_settings}")
        
        # Validate configuration
        try:
            self.validate_config()
            logger.debug("Configuration validation passed")
        except Exception as e:
            error_logger.error(f"Configuration validation failed: {e}")
            raise
        
        # Test initial connection if URL is configured
        if base_url and base_url != 'Not configured':
            self._test_initial_connection()
        
        # Initialize model info
        self._initialize_model_info()
    
    def _sanitize_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration for safe logging (remove sensitive data)."""
        safe_config = config.copy()
        if 'api_key' in safe_config and safe_config['api_key']:
            safe_config['api_key'] = '***'
        return safe_config
    
    def _test_initial_connection(self) -> None:
        """Test initial connection to the LLM server."""
        base_url = self.config.get('base_url')
        if not base_url:
            return
        
        connection_logger.info(f"Testing initial connection to {base_url}")
        start_time = time.time()
        
        try:
            # Test basic connectivity
            test_url = urljoin(base_url, "/v1/models")
            response = self._session.get(test_url, timeout=5)
            response_time = time.time() - start_time
            
            self._connection_health['total_connection_attempts'] += 1
            
            if response.status_code < 500:
                self._connection_health['successful_connections'] += 1
                self._connection_health['last_successful_connection'] = datetime.now()
                self._connection_health['consecutive_failures'] = 0
                
                llm_debug.log_connection_test(test_url, True, response_time)
                connection_logger.info(f"Initial connection successful ({response_time:.2f}s)")
                
                # Try to get server info
                try:
                    if response.status_code == 200:
                        server_info = response.json()
                        self._connection_health['server_info'] = server_info
                        connection_logger.debug(f"Server info: {json.dumps(server_info, indent=2)}")
                except:
                    pass
            else:
                self._handle_connection_failure(f"HTTP {response.status_code}", test_url)
                
        except Exception as e:
            self._handle_connection_failure(str(e), base_url)
    
    def _handle_connection_failure(self, error: str, url: str) -> None:
        """Handle connection failure and update health tracking."""
        self._connection_health['consecutive_failures'] += 1
        self._connection_health['last_error'] = error
        
        llm_debug.log_connection_test(url, False, error=error)
        connection_logger.warning(f"Initial connection failed: {error}")
        
        # Provide helpful diagnostics
        if "Connection refused" in error:
            connection_logger.error("Connection refused - is the LLM server running?")
            connection_logger.info("Try running: python diagnose_lm_studio.py")
        elif "timeout" in error.lower():
            connection_logger.error("Connection timeout - server may be starting up or overloaded")
        elif "Name or service not known" in error:
            connection_logger.error("DNS resolution failed - check the server URL")
    
    def _initialize_model_info(self) -> None:
        """Initialize model information from server."""
        connection_logger.debug("Initializing model information from server")
        
        try:
            # Try to get model info from server
            model_info = self._get_server_model_info()
            if model_info:
                self._model_info = model_info
                logger.info(f"Initialized LocalServer backend with model: {model_info.name}")
                llm_debug.log_model_info(model_info.__dict__)
            else:
                # Use default model info if server doesn't provide it
                self._model_info = ModelInfo(
                    name="local-server-model",
                    type=ModelType.CHAT,
                    context_length=self.config.get("context_length", 4096),
                    supports_system_prompt=True,
                    backend_name="LocalServerBackend"
                )
                logger.info("Initialized LocalServer backend with default model info")
                connection_logger.debug("Using default model info - server didn't provide model details")
                
        except Exception as e:
            error_logger.warning(f"Failed to get model info from server: {e}")
            connection_logger.debug(f"Model info initialization error: {traceback.format_exc()}")
            self._model_info = None
    
    def _get_server_model_info(self) -> Optional[ModelInfo]:
        """
        Get model information from the server.
        
        Returns:
            ModelInfo if available, None otherwise
        """
        try:
            base_url = self.config["base_url"]
            timeout = self.config.get("timeout", 30)
            
            # Try only LM Studio compatible endpoints for model info
            endpoints = [
                "/v1/models"  # LM Studio only supports OpenAI-compatible endpoints
            ]
            
            for endpoint in endpoints:
                try:
                    url = urljoin(base_url, endpoint)
                    # Try with session first for test compatibility
                    try:
                        response = self._session.get(url, headers=self._headers, timeout=timeout)
                        if response and response.status_code == 200:
                            data = response.json()
                            return self._parse_model_info(data)
                    except Exception:
                        # Fall back to shared HTTP client
                        response = self._http_client.get(url, headers=self._headers)
                        if response and response.status_code == 200:
                            data = response.json()
                            return self._parse_model_info(data)
                        
                except Exception as e:
                    logger.debug(f"Failed to get model info from {endpoint}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting server model info: {e}")
            return None
    
    def _parse_model_info(self, data: Dict[str, Any]) -> Optional[ModelInfo]:
        """
        Parse model information from server response.
        
        Args:
            data: Server response data
            
        Returns:
            ModelInfo if parseable, None otherwise
        """
        try:
            # Handle OpenAI-compatible format
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                model_data = data["data"][0]
                return ModelInfo(
                    name=model_data.get("id", "unknown"),
                    type=ModelType.CHAT,
                    context_length=model_data.get("context_length", 4096),
                    supports_system_prompt=True,
                    backend_name="LocalServerBackend"
                )
            
            # Handle direct model info format
            if "model" in data or "name" in data:
                return ModelInfo(
                    name=data.get("model", data.get("name", "unknown")),
                    type=ModelType.CHAT,
                    context_length=data.get("context_length", data.get("max_context", 4096)),
                    supports_system_prompt=data.get("supports_system", True),
                    backend_name="LocalServerBackend"
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing model info: {e}")
            return None
    
    def generate(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using local server API with comprehensive response validation.
        
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
        
        # Start debug logging
        request_id = llm_debug.log_request_start(
            "text_generation",
            prompt_length=len(prompt),
            context_chunks_count=len(context_chunks) if context_chunks else 0,
            temperature=temperature,
            max_tokens=max_tokens,
            has_system_prompt=system_prompt is not None
        )
        
        # Update stats
        self._request_stats['total_requests'] += 1
        
        if not self.is_available():
            error_msg = "LocalServer backend not available. Check server URL and connectivity."
            llm_debug.log_error(request_id, LLMError(error_msg), {
                'base_url': self.config.get('base_url'),
                'availability_check': 'failed'
            })
            self._request_stats['failed_requests'] += 1
            raise LLMError(
                error_msg,
                recoverable=True,
                backend="LocalServerBackend"
            )
        
        # Check cache first
        cache_key = self._generate_cache_key(prompt, context_chunks, temperature, max_tokens, system_prompt)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            self._request_stats['cache_hits'] += 1
            processing_time = time.time() - start_time
            llm_debug.log_success(request_id, len(cached_response), processing_time)
            logger.debug(f"[REQ-{request_id:04d}] Returning cached response")
            return cached_response
        
        try:
            # Validate input length and handle token limits
            if not self.validate_input_length(prompt, context_chunks):
                logger.warning(f"[REQ-{request_id:04d}] Input exceeds token limits, applying truncation")
                # Handle token limit by reducing context
                if context_chunks:
                    original_count = len(context_chunks)
                    context_chunks = self._reduce_context_for_limits(prompt, context_chunks)
                    logger.info(f"[REQ-{request_id:04d}] Reduced context chunks from {original_count} to {len(context_chunks)}")
            
            # Prepare the request
            if max_tokens is None:
                max_tokens = self.config.get("max_tokens", 512)
            
            logger.info(f"[REQ-{request_id:04d}] Starting generation with max_tokens={max_tokens}, temperature={temperature}")
            
            # Try different API formats with validation and retry
            response_text = None
            last_error = None
            
            # Try OpenAI-compatible chat completions first
            if self._model_info and self._model_info.supports_system_prompt:
                logger.debug(f"[REQ-{request_id:04d}] Attempting chat completion API")
                response_text, last_error = self._try_chat_completion_with_validation(
                    request_id, prompt, context_chunks, system_prompt, temperature, max_tokens
                )
            
            # Fall back to completion API
            if response_text is None:
                logger.debug(f"[REQ-{request_id:04d}] Falling back to completion API")
                full_prompt = self._prepare_prompt(prompt, context_chunks, system_prompt)
                response_text, last_error = self._try_completion_with_validation(
                    request_id, full_prompt, temperature, max_tokens
                )
            
            if response_text is None:
                error_msg = "All API formats failed"
                if last_error:
                    error_msg += f". Last error: {last_error}"
                
                llm_debug.log_error(request_id, LLMError(error_msg), {
                    'last_error': last_error,
                    'tried_chat_completion': self._model_info and self._model_info.supports_system_prompt,
                    'tried_completion': True
                })
                self._request_stats['failed_requests'] += 1
                
                raise LLMError(
                    error_msg,
                    recoverable=True,
                    backend="LocalServerBackend"
                )
            
            # Cache successful response
            self._cache_response(cache_key, response_text)
            
            # Update stats and log success
            self._request_stats['successful_requests'] += 1
            processing_time = time.time() - start_time
            self._request_stats['total_response_time'] += processing_time
            
            llm_debug.log_success(request_id, len(response_text), processing_time)
            
            # Log performance stats periodically
            if self._request_stats['total_requests'] % 10 == 0:
                self._log_performance_stats()
            
            return response_text.strip()
            
        except LLMError:
            self._request_stats['failed_requests'] += 1
            raise
        except Exception as e:
            self._request_stats['failed_requests'] += 1
            processing_time = time.time() - start_time
            
            llm_debug.log_error(request_id, e, {
                'processing_time': processing_time,
                'prompt_length': len(prompt),
                'context_chunks': len(context_chunks) if context_chunks else 0
            })
            
            logger.error(f"[REQ-{request_id:04d}] LocalServer generation failed after {processing_time:.2f}s: {e}")
            raise LLMError(
                f"Text generation failed: {str(e)}",
                recoverable=True,
                backend="LocalServerBackend"
            )
    
    def _log_performance_stats(self):
        """Log comprehensive performance statistics."""
        stats = self._request_stats
        if stats['total_requests'] > 0:
            success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            failure_rate = (stats['failed_requests'] / stats['total_requests']) * 100
            avg_response_time = stats['total_response_time'] / max(stats['successful_requests'], 1)
            cache_hit_rate = (stats['cache_hits'] / stats['total_requests']) * 100
            
            # Update average response time
            stats['avg_response_time'] = avg_response_time
            
            # Log main performance summary
            performance_logger.info(
                f"Performance Summary - "
                f"Requests: {stats['total_requests']} "
                f"(✅ {stats['successful_requests']}, ❌ {stats['failed_requests']}), "
                f"Success Rate: {success_rate:.1f}%, "
                f"Avg Response Time: {avg_response_time:.2f}s, "
                f"Cache Hit Rate: {cache_hit_rate:.1f}%"
            )
            
            # Log detailed error breakdown
            if stats['failed_requests'] > 0:
                error_breakdown = []
                if stats['connection_errors'] > 0:
                    error_breakdown.append(f"Connection: {stats['connection_errors']}")
                if stats['timeout_errors'] > 0:
                    error_breakdown.append(f"Timeout: {stats['timeout_errors']}")
                if stats['http_errors'] > 0:
                    error_breakdown.append(f"HTTP: {stats['http_errors']}")
                
                if error_breakdown:
                    performance_logger.warning(f"Error breakdown - {', '.join(error_breakdown)}")
            
            # Log response time statistics
            if stats['min_response_time'] != float('inf'):
                performance_logger.debug(
                    f"Response time stats - "
                    f"Min: {stats['min_response_time']:.2f}s, "
                    f"Max: {stats['max_response_time']:.2f}s, "
                    f"Avg: {avg_response_time:.2f}s"
                )
            
            # Log retry statistics
            if stats['retry_attempts'] > 0:
                retry_rate = (stats['retry_attempts'] / stats['total_requests']) * 100
                performance_logger.info(f"Retry rate: {retry_rate:.1f}% ({stats['retry_attempts']} retries)")
            
            # Log connection health
            health = self._connection_health
            if health['total_connection_attempts'] > 0:
                connection_success_rate = (health['successful_connections'] / health['total_connection_attempts']) * 100
                connection_logger.debug(f"Connection health: {connection_success_rate:.1f}% success rate")
                
                if health['consecutive_failures'] > 0:
                    connection_logger.warning(f"Consecutive failures: {health['consecutive_failures']}")
                
                if health['last_successful_connection']:
                    time_since_success = datetime.now() - health['last_successful_connection']
                    if time_since_success > timedelta(minutes=5):
                        connection_logger.warning(f"Last successful connection: {time_since_success} ago")
    
    def _try_chat_completion_with_validation(
        self,
        request_id: int,
        prompt: str,
        context_chunks: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> tuple[Optional[str], Optional[str]]:
        """Try OpenAI-compatible chat completion API with validation and retry."""
        base_url = self.config["base_url"]
        timeout = self.config.get("timeout", 30)
        
        # Prepare messages
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add context if provided
        if context_chunks:
            context_text = "\n\n".join(context_chunks)
            messages.append({"role": "user", "content": f"Context:\n{context_text}"})
        
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request data
        data = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Add model if specified
        model = self.config.get("model")
        if model:
            data["model"] = model
        
        # Add stop sequences if specified
        stop = self.config.get("stop_sequences")
        if stop:
            data["stop"] = stop
        
        # Try chat completions endpoint with retry logic
        url = urljoin(base_url, "/v1/chat/completions")
        
        for attempt in range(1, self._max_retries + 1):
            request_start_time = time.time()
            
            try:
                logger.debug(f"[REQ-{request_id:04d}] Chat completion attempt {attempt}/{self._max_retries}")
                
                # Log detailed request information
                if self._log_requests:
                    llm_debug.log_request_details(request_id, url, self._headers, data)
                
                # Make request with proper connection handling
                try:
                    response = self._session.post(url, json=data, headers=self._headers, timeout=timeout)
                except Exception as session_error:
                    logger.debug(f"[REQ-{request_id:04d}] Session request failed, trying HTTP client: {session_error}")
                    # Fall back to shared HTTP client
                    response = self._http_client.post(url, json=data, headers=self._headers)
                
                response_time = time.time() - request_start_time
                
                # Log detailed response information
                if self._log_responses:
                    llm_debug.log_response_details(request_id, response, response_time)
                
                # Validate response
                validation_result = self._validator.validate_response(
                    response, 
                    operation="text_generation"
                )
                
                # Log validation details
                if validation_result.errors:
                    logger.warning(f"[REQ-{request_id:04d}] Validation errors: {[e.error_message for e in validation_result.errors]}")
                if validation_result.warnings:
                    logger.info(f"[REQ-{request_id:04d}] Validation warnings: {validation_result.warnings}")
                
                # Check if response is valid
                if validation_result.is_valid and validation_result.extracted_data:
                    content = validation_result.extracted_data.get('content')
                    if content:
                        logger.debug(f"[REQ-{request_id:04d}] Chat completion successful on attempt {attempt} ({response_time:.2f}s)")
                        return content, None
                
                # Check if we should retry
                if not validation_result.should_retry() or attempt >= self._max_retries:
                    error_msg = f"Chat completion validation failed: {validation_result.errors[0].error_message if validation_result.errors else 'Unknown error'}"
                    logger.debug(f"[REQ-{request_id:04d}] {error_msg}")
                    return None, error_msg
                
                # Wait before retry
                if attempt < self._max_retries:
                    delay = self._validator.calculate_retry_delay(attempt, self._base_retry_delay)
                    retry_reason = f"Validation failed: {validation_result.errors[0].error_message if validation_result.errors else 'Unknown'}"
                    llm_debug.log_retry_attempt(request_id, attempt, self._max_retries, delay, retry_reason)
                    time.sleep(delay)
                    
            except Exception as e:
                response_time = time.time() - request_start_time
                error_msg = f"Chat completion API failed: {e}"
                
                llm_debug.log_error(request_id, e, {
                    'attempt': attempt,
                    'response_time': response_time,
                    'url': url,
                    'timeout': timeout
                })
                
                logger.debug(f"[REQ-{request_id:04d}] {error_msg}")
                
                if attempt >= self._max_retries:
                    return None, error_msg
                
                # Wait before retry
                delay = self._validator.calculate_retry_delay(attempt, self._base_retry_delay)
                llm_debug.log_retry_attempt(request_id, attempt, self._max_retries, delay, f"Exception: {type(e).__name__}")
                time.sleep(delay)
        
        return None, "Chat completion failed after all retries"
    
    def _try_completion_with_validation(
        self,
        request_id: int,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> tuple[Optional[str], Optional[str]]:
        """Try completion API with validation and retry."""
        base_url = self.config["base_url"]
        timeout = self.config.get("timeout", 30)
        
        # Prepare request data
        data = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Add model if specified
        model = self.config.get("model")
        if model:
            data["model"] = model
        
        # Add stop sequences if specified
        stop = self.config.get("stop_sequences")
        if stop:
            data["stop"] = stop
        
        # Try only LM Studio compatible completion endpoints
        endpoints = [
            "/v1/completions"  # LM Studio only supports OpenAI-compatible endpoints
        ]
        
        last_error = None
        
        for endpoint in endpoints:
            logger.debug(f"[REQ-{request_id:04d}] Trying completion endpoint: {endpoint}")
            
            for attempt in range(1, self._max_retries + 1):
                request_start_time = time.time()
                
                try:
                    url = urljoin(base_url, endpoint)
                    
                    # Log detailed request information
                    if self._log_requests:
                        llm_debug.log_request_details(request_id, url, self._headers, data)
                    
                    # Use session first for better connection handling
                    try:
                        response = self._session.post(url, json=data, headers=self._headers, timeout=timeout)
                    except Exception as session_error:
                        logger.debug(f"[REQ-{request_id:04d}] Session request failed for {endpoint}, trying HTTP client: {session_error}")
                        # Fall back to shared HTTP client
                        response = self._http_client.post(url, json=data, headers=self._headers)
                    
                    response_time = time.time() - request_start_time
                    
                    # Log detailed response information
                    if self._log_responses:
                        llm_debug.log_response_details(request_id, response, response_time)
                    
                    # Validate response
                    validation_result = self._validator.validate_response(
                        response, 
                        operation="text_generation"
                    )
                    
                    # Log validation details
                    if validation_result.errors:
                        logger.debug(f"[REQ-{request_id:04d}] Validation errors for {endpoint}: {[e.error_message for e in validation_result.errors]}")
                    if validation_result.warnings:
                        logger.debug(f"[REQ-{request_id:04d}] Validation warnings for {endpoint}: {validation_result.warnings}")
                    
                    # Check if response is valid
                    if validation_result.is_valid and validation_result.extracted_data:
                        content = validation_result.extracted_data.get('content')
                        if content:
                            logger.debug(f"[REQ-{request_id:04d}] Completion successful with {endpoint} on attempt {attempt} ({response_time:.2f}s)")
                            return content, None
                    
                    # For completion API, also try alternative response parsing
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            
                            # Handle different response formats
                            content = None
                            if "choices" in result and result["choices"]:
                                content = result["choices"][0].get("text", "")
                            elif "text" in result:
                                content = result["text"]
                            elif "response" in result:
                                content = result["response"]
                            
                            if content and content.strip():
                                logger.debug(f"[REQ-{request_id:04d}] Completion successful with alternative parsing for {endpoint} ({response_time:.2f}s)")
                                return content.strip(), None
                                
                        except Exception as parse_error:
                            logger.debug(f"[REQ-{request_id:04d}] Alternative parsing failed for {endpoint}: {parse_error}")
                    
                    # Check if we should retry this endpoint
                    if not validation_result.should_retry() or attempt >= self._max_retries:
                        last_error = f"Endpoint {endpoint} validation failed: {validation_result.errors[0].error_message if validation_result.errors else 'Unknown error'}"
                        break
                    
                    # Wait before retry
                    if attempt < self._max_retries:
                        delay = self._validator.calculate_retry_delay(attempt, self._base_retry_delay)
                        retry_reason = f"Validation failed for {endpoint}"
                        llm_debug.log_retry_attempt(request_id, attempt, self._max_retries, delay, retry_reason)
                        time.sleep(delay)
                        
                except Exception as e:
                    response_time = time.time() - request_start_time
                    last_error = f"Completion endpoint {endpoint} failed: {e}"
                    
                    llm_debug.log_error(request_id, e, {
                        'endpoint': endpoint,
                        'attempt': attempt,
                        'response_time': response_time,
                        'url': url
                    })
                    
                    logger.debug(f"[REQ-{request_id:04d}] {last_error}")
                    
                    if attempt >= self._max_retries:
                        break
                    
                    # Wait before retry
                    delay = self._validator.calculate_retry_delay(attempt, self._base_retry_delay)
                    llm_debug.log_retry_attempt(request_id, attempt, self._max_retries, delay, f"Exception on {endpoint}: {type(e).__name__}")
                    time.sleep(delay)
        
        return None, last_error or "All completion endpoints failed"
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information about the backend state."""
        debug_info = {
            'backend_type': 'LocalServerBackend',
            'config': self._sanitize_config_for_logging(self.config),
            'availability': {
                'is_available': self.is_available(),
                'cache_status': {
                    'availability_cached': self._availability_cache,
                    'availability_cache_age': time.time() - self._availability_cache_time if self._availability_cache_time else None,
                    'model_info_cached': self._model_info_cache is not None,
                    'model_info_cache_age': time.time() - self._model_info_cache_time if self._model_info_cache_time else None
                }
            },
            'performance_stats': self._request_stats.copy(),
            'configuration': {
                'max_retries': self._max_retries,
                'base_retry_delay': self._base_retry_delay,
                'debug_enabled': self._debug_enabled,
                'log_requests': self._log_requests,
                'log_responses': self._log_responses,
                'cache_ttl': {
                    'availability': self._availability_cache_ttl,
                    'model_info': self._model_info_cache_ttl,
                    'response': self._response_cache_ttl
                }
            },
            'model_info': self._model_info.__dict__ if self._model_info else None,
            'cache_stats': {
                'response_cache_size': len(self._response_cache),
                'cache_hit_rate': (self._request_stats['cache_hits'] / max(self._request_stats['total_requests'], 1)) * 100
            }
        }
        
        # Add health check information
        try:
            health_info = self.health_check()
            debug_info['health_check'] = health_info
        except Exception as e:
            debug_info['health_check'] = {'error': str(e)}
        
        return debug_info
    
    def enable_debug_logging(self, enable_requests: bool = True, enable_responses: bool = True):
        """Enable detailed debug logging for requests and responses."""
        self._debug_enabled = True
        self._log_requests = enable_requests
        self._log_responses = enable_responses
        
        # Set debug level for LLM loggers
        logging.getLogger(f"{__name__}.debug").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        
        logger.info("Debug logging enabled for LocalServer backend")
    
    def disable_debug_logging(self):
        """Disable detailed debug logging."""
        self._debug_enabled = False
        self._log_requests = False
        self._log_responses = False
        
        logger.info("Debug logging disabled for LocalServer backend")
    
    def reset_stats(self):
        """Reset performance statistics."""
        self._request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'cache_hits': 0
        }
        logger.info("Performance statistics reset")
    
    def _prepare_prompt(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Prepare the full prompt with context and system instructions.
        
        Args:
            prompt: Main prompt
            context_chunks: Optional context chunks
            system_prompt: Optional system prompt
            
        Returns:
            Formatted prompt string
        """
        parts = []
        
        # Add system prompt
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        
        # Add context chunks if provided
        if context_chunks:
            context_text = "\n\n".join(context_chunks)
            parts.append(f"Context:\n{context_text}")
        
        # Add main prompt
        parts.append(f"Query: {prompt}")
        
        return "\n\n".join(parts)
    
    def is_available(self) -> bool:
        """
        Check if LocalServer backend is available with caching.
        
        Returns:
            True if backend is available, False otherwise
        """
        import time
        
        # Check cache first
        current_time = time.time()
        if (self._availability_cache is not None and 
            current_time - self._availability_cache_time < self._availability_cache_ttl):
            logger.debug(f"Returning cached availability status: {self._availability_cache}")
            return self._availability_cache
        
        check_start_time = time.time()
        
        try:
            base_url = self.config.get("base_url")
            if not base_url:
                logger.warning("No base_url configured for LocalServer backend")
                self._availability_cache = False
                self._availability_cache_time = current_time
                return False
            
            timeout = self.config.get("timeout", 5)  # Short timeout for availability check
            logger.debug(f"Checking availability for {base_url} with timeout {timeout}s")
            
            # Try health endpoints in order of preference (LM Studio compatible)
            health_endpoints = ["/v1/models", "/health"]
            
            for endpoint in health_endpoints:
                endpoint_start_time = time.time()
                
                try:
                    url = urljoin(base_url, endpoint)
                    logger.debug(f"Trying availability endpoint: {url}")
                    
                    # Try with session first for test compatibility
                    try:
                        response = self._session.get(url, headers=self._headers, timeout=timeout)
                        endpoint_time = time.time() - endpoint_start_time
                        
                        logger.debug(f"Availability check response from {endpoint}: "
                                   f"status={response.status_code}, time={endpoint_time:.2f}s")
                        
                        if response and response.status_code < 500:  # Any non-server-error response
                            logger.info(f"LocalServer backend available at {base_url} "
                                      f"(endpoint: {endpoint}, status: {response.status_code})")
                            self._availability_cache = True
                            self._availability_cache_time = current_time
                            return True
                            
                    except Exception as session_error:
                        logger.debug(f"Session availability check failed for {endpoint}: {session_error}")
                        # Fall back to shared HTTP client
                        response = self._http_client.get(url, headers=self._headers, use_cache=True)
                        endpoint_time = time.time() - endpoint_start_time
                        
                        if response:
                            logger.debug(f"HTTP client availability check response from {endpoint}: "
                                       f"status={response.status_code}, time={endpoint_time:.2f}s")
                            
                            if response.status_code < 500:  # Any non-server-error response
                                logger.info(f"LocalServer backend available at {base_url} "
                                          f"(endpoint: {endpoint}, status: {response.status_code})")
                                self._availability_cache = True
                                self._availability_cache_time = current_time
                                return True
                        
                except Exception as e:
                    endpoint_time = time.time() - endpoint_start_time
                    logger.debug(f"Availability check failed for {endpoint} after {endpoint_time:.2f}s: {e}")
                    continue
            
            total_check_time = time.time() - check_start_time
            logger.warning(f"LocalServer backend not available at {base_url} "
                         f"(checked {len(health_endpoints)} endpoints in {total_check_time:.2f}s)")
            
            self._availability_cache = False
            self._availability_cache_time = current_time
            return False
            
        except Exception as e:
            total_check_time = time.time() - check_start_time
            logger.error(f"Availability check failed after {total_check_time:.2f}s: {e}")
            debug_logger.debug(f"Availability check exception details:\n{traceback.format_exc()}")
            
            self._availability_cache = False
            self._availability_cache_time = current_time
            return False
    
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the loaded model with caching.
        
        Returns:
            ModelInfo object with model details
            
        Raises:
            LLMError: If model info cannot be retrieved
        """
        import time
        
        # Check cache first
        current_time = time.time()
        if (self._model_info_cache is not None and 
            current_time - self._model_info_cache_time < self._model_info_cache_ttl):
            return self._model_info_cache
        
        if not self.is_available():
            raise LLMError(
                "LocalServer backend not available",
                recoverable=True,
                backend="LocalServerBackend"
            )
        
        if self._model_info is None:
            # Try to refresh model info
            self._initialize_model_info()
            
            if self._model_info is None:
                raise LLMError(
                    "Model information not available",
                    recoverable=True,
                    backend="LocalServerBackend"
                )
        
        # Cache the result
        self._model_info_cache = self._model_info
        self._model_info_cache_time = current_time
        
        return self._model_info
    
    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys.
        
        Returns:
            List of required configuration key names
        """
        return ["base_url"]
    
    def chunk_content(self, content: str, max_chunk_size: Optional[int] = None) -> List[str]:
        """
        Chunk content to fit within model token limits.
        
        Uses character-based estimation for token counting.
        
        Args:
            content: Content to chunk
            max_chunk_size: Maximum chunk size in estimated tokens
            
        Returns:
            List of content chunks
        """
        if max_chunk_size is None:
            try:
                model_info = self.get_model_info()
                # Use 60% of context length for content, leaving room for prompt
                max_chunk_size = int(model_info.context_length * 0.6)
            except LLMError:
                max_chunk_size = 2048  # Default fallback
        
        # Convert token estimate to characters (rough estimate: 4 chars per token)
        max_chars = max_chunk_size * 4
        
        if len(content) <= max_chars:
            return [content]
        
        chunks = []
        current_pos = 0
        overlap_chars = self.config.get("chunk_overlap_chars", 200)  # Character overlap
        
        while current_pos < len(content):
            end_pos = min(current_pos + max_chars, len(content))
            
            # Try to break at natural boundaries
            if end_pos < len(content):
                # Look for natural breaks in the last 20% of chunk
                search_start = max(current_pos, end_pos - int(max_chars * 0.2))
                chunk_text = content[search_start:end_pos]
                
                # Look for natural breaks
                for break_char in ['\n\n', '\n', '.', ';', ',', ' ']:
                    break_pos = chunk_text.rfind(break_char)
                    if break_pos > len(chunk_text) * 0.5:  # At least halfway through
                        end_pos = search_start + break_pos + 1
                        break
            
            # Extract chunk
            chunk = content[current_pos:end_pos]
            chunks.append(chunk)
            
            # Move position with overlap for better context continuity
            current_pos = max(end_pos - overlap_chars, current_pos + 1)
            if current_pos >= len(content):
                break
        
        return chunks
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.
        
        Uses character-based estimation since we don't have direct tokenizer access.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 4 characters per token for English text
        # This can be adjusted based on the specific model being used
        chars_per_token = self.config.get("chars_per_token", 4)
        return max(1, len(text) // chars_per_token)
    
    def validate_input_length(self, prompt: str, context_chunks: Optional[List[str]] = None) -> bool:
        """
        Validate that input fits within model context limits.
        
        Args:
            prompt: Main prompt
            context_chunks: Optional context chunks
            
        Returns:
            True if input fits, False otherwise
        """
        try:
            model_info = self.get_model_info()
            max_input_tokens = int(model_info.context_length * 0.8)  # Leave room for generation
            
            total_tokens = self.estimate_tokens(prompt)
            
            if context_chunks:
                for chunk in context_chunks:
                    total_tokens += self.estimate_tokens(chunk)
            
            return total_tokens <= max_input_tokens
            
        except LLMError:
            logger.warning("Could not validate input length - model info unavailable")
            return True  # Assume valid if validation fails
    
    def _handle_token_limit_error(self, prompt: str, context_chunks: Optional[List[str]] = None) -> str:
        """
        Handle cases where input exceeds token limits by chunking content.
        
        Args:
            prompt: Main prompt
            context_chunks: Optional context chunks
            
        Returns:
            Truncated or chunked content that fits within limits
        """
        if not context_chunks:
            # If no context chunks, just truncate the prompt
            max_prompt_tokens = 1000  # Conservative limit for prompt only
            estimated_tokens = self.estimate_tokens(prompt)
            
            if estimated_tokens > max_prompt_tokens:
                # Truncate prompt to fit
                chars_to_keep = max_prompt_tokens * 4  # Rough conversion
                return prompt[:chars_to_keep] + "... [truncated]"
            
            return prompt
        
        # If we have context chunks, reduce them first
        try:
            model_info = self.get_model_info()
            max_total_tokens = int(model_info.context_length * 0.7)  # Conservative limit
        except LLMError:
            max_total_tokens = 2000  # Fallback limit
        
        prompt_tokens = self.estimate_tokens(prompt)
        available_for_context = max_total_tokens - prompt_tokens
        
        if available_for_context <= 0:
            # Prompt itself is too long
            return self._handle_token_limit_error(prompt, None)
        
        # Select most relevant context chunks that fit
        selected_chunks = []
        used_tokens = 0
        
        for chunk in context_chunks:
            chunk_tokens = self.estimate_tokens(chunk)
            if used_tokens + chunk_tokens <= available_for_context:
                selected_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                # Try to fit a truncated version of this chunk
                remaining_tokens = available_for_context - used_tokens
                if remaining_tokens > 100:  # Only if we have reasonable space left
                    chars_to_keep = remaining_tokens * 4
                    truncated_chunk = chunk[:chars_to_keep] + "... [truncated]"
                    selected_chunks.append(truncated_chunk)
                break
        
        return prompt  # Return original prompt, context will be handled separately
    
    def _reduce_context_for_limits(self, prompt: str, context_chunks: List[str]) -> List[str]:
        """
        Reduce context chunks to fit within token limits.
        
        Args:
            prompt: Main prompt
            context_chunks: Original context chunks
            
        Returns:
            Reduced list of context chunks that fit within limits
        """
        try:
            model_info = self.get_model_info()
            max_total_tokens = int(model_info.context_length * 0.7)  # Conservative limit
        except LLMError:
            max_total_tokens = 2000  # Fallback limit
        
        prompt_tokens = self.estimate_tokens(prompt)
        available_for_context = max_total_tokens - prompt_tokens
        
        if available_for_context <= 0:
            logger.warning("Prompt too long, removing all context")
            return []
        
        # Select chunks that fit, prioritizing earlier chunks (usually more relevant)
        selected_chunks = []
        used_tokens = 0
        
        for chunk in context_chunks:
            chunk_tokens = self.estimate_tokens(chunk)
            if used_tokens + chunk_tokens <= available_for_context:
                selected_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = available_for_context - used_tokens
                if remaining_tokens > 100:  # Only if reasonable space left
                    chars_to_keep = remaining_tokens * 4
                    truncated_chunk = chunk[:chars_to_keep] + "... [truncated]"
                    selected_chunks.append(truncated_chunk)
                break
        
        if len(selected_chunks) < len(context_chunks):
            logger.info(f"Reduced context from {len(context_chunks)} to {len(selected_chunks)} chunks")
        
        return selected_chunks
    
    def invalidate_availability_cache(self) -> None:
        """Invalidate the availability cache to force a fresh check."""
        self._availability_cache = None
        self._availability_cache_time = 0
    
    def invalidate_model_info_cache(self) -> None:
        """Invalidate the model info cache to force a fresh fetch."""
        self._model_info_cache = None
        self._model_info_cache_time = 0
    
    def invalidate_all_caches(self) -> None:
        """Invalidate all caches."""
        self.invalidate_availability_cache()
        self.invalidate_model_info_cache()
        self._response_cache.clear()
    
    def _generate_cache_key(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]], 
        temperature: float, 
        max_tokens: Optional[int], 
        system_prompt: Optional[str]
    ) -> str:
        """Generate cache key for response caching."""
        import hashlib
        
        # Create a hash of the request parameters
        cache_data = {
            'prompt': prompt,
            'context_chunks': context_chunks or [],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'system_prompt': system_prompt or '',
            'model': self.config.get('model', ''),
            'base_url': self.config.get('base_url', '')
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        if cache_key not in self._response_cache:
            return None
        
        cached_data = self._response_cache[cache_key]
        current_time = time.time()
        
        if current_time - cached_data['timestamp'] > self._response_cache_ttl:
            # Cache expired
            del self._response_cache[cache_key]
            return None
        
        return cached_data['response']
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a successful response."""
        self._response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Clean up old cache entries (simple LRU-like cleanup)
        if len(self._response_cache) > 100:  # Limit cache size
            # Remove oldest entries
            sorted_items = sorted(
                self._response_cache.items(), 
                key=lambda x: x[1]['timestamp']
            )
            
            # Keep only the 50 most recent entries
            self._response_cache = dict(sorted_items[-50:])
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get statistics about API response validation."""
        return {
            'cache_size': len(self._response_cache),
            'cache_ttl': self._response_cache_ttl,
            'max_retries': self._max_retries,
            'base_retry_delay': self._base_retry_delay,
            'validator_schemas': list(self._validator.expected_schemas.keys())
        }
    
    def clear_response_cache(self) -> None:
        """Clear the response cache."""
        self._response_cache.clear()
        logger.info("Response cache cleared")