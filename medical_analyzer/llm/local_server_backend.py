"""
Local server backend implementation for LLM integration.

This module provides integration with local LLM servers via REST API,
supporting various local model servers for medical device software analysis.
"""

import json
import requests
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import urljoin

from .backend import LLMBackend, LLMError, ModelInfo, ModelType

logger = logging.getLogger(__name__)


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
        self._session = requests.Session()
        
        # Set up session with API key if provided
        api_key = self.config.get("api_key")
        if api_key:
            self._session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        # Validate configuration
        self.validate_config()
        
        # Initialize model info
        self._initialize_model_info()
    
    def _initialize_model_info(self) -> None:
        """Initialize model information from server."""
        try:
            # Try to get model info from server
            model_info = self._get_server_model_info()
            if model_info:
                self._model_info = model_info
                logger.info(f"Initialized LocalServer backend with model: {model_info.name}")
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
                
        except Exception as e:
            logger.warning(f"Failed to get model info from server: {e}")
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
            
            # Try different endpoints for model info
            endpoints = [
                "/v1/models",  # OpenAI-compatible
                "/api/v1/models",  # Alternative
                "/models",  # Simple endpoint
                "/info"  # Generic info endpoint
            ]
            
            for endpoint in endpoints:
                try:
                    url = urljoin(base_url, endpoint)
                    response = self._session.get(url, timeout=timeout)
                    
                    if response.status_code == 200:
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
        Generate text using local server API.
        
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
        if not self.is_available():
            raise LLMError(
                "LocalServer backend not available. Check server URL and connectivity.",
                recoverable=True,
                backend="LocalServerBackend"
            )
        
        try:
            # Validate input length and handle token limits
            if not self.validate_input_length(prompt, context_chunks):
                logger.warning("Input exceeds token limits, applying truncation")
                # Handle token limit by reducing context
                if context_chunks:
                    # Reduce context chunks to fit
                    context_chunks = self._reduce_context_for_limits(prompt, context_chunks)
            
            # Prepare the request
            full_prompt = self._prepare_prompt(prompt, context_chunks, system_prompt)
            
            if max_tokens is None:
                max_tokens = self.config.get("max_tokens", 512)
            
            # Try different API formats
            response_text = None
            
            # Try OpenAI-compatible chat completions first
            if self._model_info and self._model_info.supports_system_prompt:
                response_text = self._try_chat_completion(
                    prompt, context_chunks, system_prompt, temperature, max_tokens
                )
            
            # Fall back to completion API
            if response_text is None:
                response_text = self._try_completion(
                    full_prompt, temperature, max_tokens
                )
            
            if response_text is None:
                raise LLMError(
                    "All API formats failed",
                    recoverable=True,
                    backend="LocalServerBackend"
                )
            
            return response_text.strip()
            
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"LocalServer generation failed: {e}")
            raise LLMError(
                f"Text generation failed: {str(e)}",
                recoverable=True,
                backend="LocalServerBackend"
            )
    
    def _try_chat_completion(
        self,
        prompt: str,
        context_chunks: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """Try OpenAI-compatible chat completion API."""
        try:
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
            
            # Try chat completions endpoint
            url = urljoin(base_url, "/v1/chat/completions")
            response = self._session.post(url, json=data, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"]
            
            return None
            
        except Exception as e:
            logger.debug(f"Chat completion API failed: {e}")
            return None
    
    def _try_completion(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """Try completion API."""
        try:
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
            
            # Try different completion endpoints
            endpoints = [
                "/v1/completions",
                "/api/v1/completions",
                "/completions",
                "/generate"
            ]
            
            for endpoint in endpoints:
                try:
                    url = urljoin(base_url, endpoint)
                    response = self._session.post(url, json=data, timeout=timeout)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Handle different response formats
                        if "choices" in result and result["choices"]:
                            return result["choices"][0].get("text", "")
                        elif "text" in result:
                            return result["text"]
                        elif "response" in result:
                            return result["response"]
                        
                except Exception as e:
                    logger.debug(f"Completion endpoint {endpoint} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Completion API failed: {e}")
            return None
    
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
        Check if LocalServer backend is available.
        
        Returns:
            True if backend is available, False otherwise
        """
        try:
            base_url = self.config.get("base_url")
            if not base_url:
                return False
            
            timeout = self.config.get("timeout", 5)  # Short timeout for availability check
            
            # Try to ping the server
            health_endpoints = ["/health", "/v1/models", "/", "/api/health"]
            
            for endpoint in health_endpoints:
                try:
                    url = urljoin(base_url, endpoint)
                    response = self._session.get(url, timeout=timeout)
                    
                    if response.status_code < 500:  # Any non-server-error response
                        return True
                        
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Availability check failed: {e}")
            return False
    
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the loaded model.
        
        Returns:
            ModelInfo object with model details
            
        Raises:
            LLMError: If model info cannot be retrieved
        """
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