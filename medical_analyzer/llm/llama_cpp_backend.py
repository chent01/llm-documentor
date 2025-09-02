"""
LlamaCpp backend implementation for local LLM integration.

This module provides integration with llama.cpp for running local language models
without cloud dependencies, suitable for medical device software analysis.
"""

import os
from typing import List, Optional, Dict, Any
import logging
import time
import traceback
import threading
from datetime import datetime

from .backend import LLMBackend, LLMError, ModelInfo, ModelType

logger = logging.getLogger(__name__)

# Create specialized loggers for different aspects
debug_logger = logging.getLogger(f"{__name__}.debug")
model_logger = logging.getLogger(f"{__name__}.model")
performance_logger = logging.getLogger(f"{__name__}.performance")
generation_logger = logging.getLogger(f"{__name__}.generation")
error_logger = logging.getLogger(f"{__name__}.errors")


class LlamaCppBackend(LLMBackend):
    """
    LLM backend implementation using llama.cpp.
    
    This backend integrates with llama.cpp to run local language models
    for medical software analysis without external dependencies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LlamaCpp backend.
        
        Args:
            config: Configuration dictionary with llama.cpp settings
        """
        super().__init__(config)
        self._llama = None
        self._model_info = None
        self._lock = threading.Lock()
        
        # Performance tracking
        self._generation_stats = {
            'total_generations': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'total_tokens_generated': 0,
            'total_generation_time': 0.0,
            'avg_tokens_per_second': 0.0,
            'model_load_time': None,
            'model_loaded_at': None
        }
        
        # Debug configuration
        self._debug_enabled = config.get('debug_enabled', False)
        self._log_generations = config.get('log_generations', self._debug_enabled)
        self._log_model_loading = config.get('log_model_loading', True)
        
        logger.info(f"Initializing LlamaCpp backend with config: {self._sanitize_config_for_logging(config)}")
        
        # Validate configuration
        try:
            self.validate_config()
            logger.debug("LlamaCpp configuration validation passed")
        except Exception as e:
            error_logger.error(f"LlamaCpp configuration validation failed: {e}")
            raise
        
        # Initialize llama.cpp if available
        self._initialize_llama()
    
    def _sanitize_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration for safe logging."""
        safe_config = config.copy()
        # No sensitive data to sanitize in llama.cpp config typically
        return safe_config
    
    def _initialize_llama(self) -> None:
        """Initialize llama.cpp model if available."""
        model_path = self.config.get("model_path", "")
        
        if self._log_model_loading:
            model_logger.info(f"Attempting to initialize llama.cpp model: {model_path}")
        
        load_start_time = time.time()
        
        try:
            # Try to import llama-cpp-python
            try:
                from llama_cpp import Llama
                model_logger.debug("llama-cpp-python import successful")
            except ImportError as e:
                error_msg = "llama-cpp-python not available. Install with: pip install llama-cpp-python"
                error_logger.error(error_msg)
                model_logger.error(f"Import error: {e}")
                return
            
            # Validate model path
            if not model_path:
                error_logger.error("Model path not specified in configuration")
                return
            
            if not os.path.exists(model_path):
                error_logger.error(f"Model file not found: {model_path}")
                model_logger.info("Check that the model file exists and is accessible")
                return
            
            # Log model file info
            try:
                model_size = os.path.getsize(model_path)
                model_logger.info(f"Model file size: {model_size / (1024**3):.2f} GB")
            except Exception as e:
                model_logger.warning(f"Could not get model file size: {e}")
            
            # Prepare initialization parameters
            init_params = {
                'model_path': model_path,
                'n_ctx': self.config.get("n_ctx", 4096),
                'n_threads': self.config.get("n_threads", -1),
                'verbose': self.config.get("verbose", False),
                'n_gpu_layers': self.config.get("n_gpu_layers", 0),
                'use_mmap': self.config.get("use_mmap", True),
                'use_mlock': self.config.get("use_mlock", False)
            }
            
            model_logger.debug(f"Initializing with parameters: {init_params}")
            
            # Initialize Llama model
            model_logger.info("Loading model... this may take a while for large models")
            self._llama = Llama(**init_params)
            
            load_time = time.time() - load_start_time
            self._generation_stats['model_load_time'] = load_time
            self._generation_stats['model_loaded_at'] = datetime.now()
            
            # Create model info
            self._model_info = ModelInfo(
                name=os.path.basename(model_path),
                type=ModelType.CHAT if self.config.get("chat_format") else ModelType.COMPLETION,
                context_length=self.config.get("n_ctx", 4096),
                supports_system_prompt=self.config.get("chat_format", False),
                backend_name="LlamaCppBackend"
            )
            
            model_logger.info(f"Model loaded successfully in {load_time:.2f}s: {os.path.basename(model_path)}")
            model_logger.info(f"Model type: {self._model_info.type.value}, Context length: {self._model_info.context_length}")
            
            # Log GPU usage if enabled
            if init_params['n_gpu_layers'] > 0:
                model_logger.info(f"GPU acceleration enabled with {init_params['n_gpu_layers']} layers")
            else:
                model_logger.debug("Running on CPU only")
            
        except Exception as e:
            load_time = time.time() - load_start_time
            error_logger.error(f"Failed to initialize LlamaCpp backend after {load_time:.2f}s: {e}")
            model_logger.debug(f"Full initialization error: {traceback.format_exc()}")
            self._llama = None
            
            # Provide helpful error messages
            if "CUDA" in str(e):
                model_logger.error("CUDA-related error - check GPU drivers and CUDA installation")
            elif "memory" in str(e).lower():
                model_logger.error("Memory error - model may be too large for available RAM")
            elif "file" in str(e).lower():
                model_logger.error("File access error - check model file permissions and path")
    
    def generate(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using llama.cpp model.
        
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
            error_msg = "LlamaCpp backend not available. Check model path and installation."
            error_logger.error(error_msg)
            raise LLMError(error_msg, recoverable=False, backend="LlamaCppBackend")
        
        # Update stats
        with self._lock:
            self._generation_stats['total_generations'] += 1
            generation_id = self._generation_stats['total_generations']
        
        start_time = time.time()
        
        if self._log_generations:
            generation_logger.info(f"[GEN-{generation_id:04d}] Starting generation")
            generation_logger.debug(f"[GEN-{generation_id:04d}] Prompt length: {len(prompt)} chars")
            generation_logger.debug(f"[GEN-{generation_id:04d}] Context chunks: {len(context_chunks) if context_chunks else 0}")
            generation_logger.debug(f"[GEN-{generation_id:04d}] Temperature: {temperature}, Max tokens: {max_tokens}")
        
        try:
            # Validate input length and handle token limits
            if not self.validate_input_length(prompt, context_chunks):
                generation_logger.warning(f"[GEN-{generation_id:04d}] Input exceeds token limits, applying truncation")
                # Handle token limit by reducing context
                if context_chunks:
                    original_count = len(context_chunks)
                    context_chunks = self._reduce_context_for_limits(prompt, context_chunks)
                    generation_logger.info(f"[GEN-{generation_id:04d}] Reduced context from {original_count} to {len(context_chunks)} chunks")
            
            # Prepare the full prompt
            full_prompt = self._prepare_prompt(prompt, context_chunks, system_prompt)
            
            # Set generation parameters
            if max_tokens is None:
                max_tokens = self.config.get("max_tokens", 512)
            
            # Ensure max_tokens doesn't exceed model limits
            model_info = self.get_model_info()
            input_tokens = self.estimate_tokens(full_prompt)
            available_tokens = model_info.context_length - input_tokens - 50  # Safety margin
            max_tokens = min(max_tokens, available_tokens)
            
            if max_tokens <= 0:
                error_msg = f"Input too long for model context window (input: {input_tokens}, context: {model_info.context_length})"
                error_logger.error(f"[GEN-{generation_id:04d}] {error_msg}")
                raise LLMError(error_msg, recoverable=True, backend="LlamaCppBackend")
            
            generation_logger.debug(f"[GEN-{generation_id:04d}] Input tokens: {input_tokens}, Available for generation: {max_tokens}")
            
            # Generate response
            generation_start = time.time()
            
            if self._model_info.type == ModelType.CHAT and self.config.get("chat_format"):
                generation_logger.debug(f"[GEN-{generation_id:04d}] Using chat completion format")
                
                # Use chat completion format
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": full_prompt})
                
                response = self._llama.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=self.config.get("stop_sequences", [])
                )
                
                generated_text = response["choices"][0]["message"]["content"].strip()
            else:
                generation_logger.debug(f"[GEN-{generation_id:04d}] Using completion format")
                
                # Use completion format
                response = self._llama(
                    full_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=self.config.get("stop_sequences", []),
                    echo=False
                )
                
                generated_text = response["choices"][0]["text"].strip()
            
            generation_time = time.time() - generation_start
            total_time = time.time() - start_time
            
            # Update statistics
            with self._lock:
                self._generation_stats['successful_generations'] += 1
                self._generation_stats['total_generation_time'] += generation_time
                
                # Estimate tokens generated
                generated_tokens = self.estimate_tokens(generated_text)
                self._generation_stats['total_tokens_generated'] += generated_tokens
                
                # Calculate tokens per second
                if generation_time > 0:
                    tokens_per_second = generated_tokens / generation_time
                    # Update running average
                    total_successful = self._generation_stats['successful_generations']
                    current_avg = self._generation_stats['avg_tokens_per_second']
                    self._generation_stats['avg_tokens_per_second'] = (
                        (current_avg * (total_successful - 1) + tokens_per_second) / total_successful
                    )
            
            if self._log_generations:
                generation_logger.info(f"[GEN-{generation_id:04d}] Generation completed in {generation_time:.2f}s")
                generation_logger.info(f"[GEN-{generation_id:04d}] Generated {len(generated_text)} characters (~{generated_tokens} tokens)")
                
                if generation_time > 0:
                    tokens_per_second = generated_tokens / generation_time
                    performance_logger.info(f"[GEN-{generation_id:04d}] Performance: {tokens_per_second:.1f} tokens/second")
            
            # Log performance warnings
            if generation_time > 30:
                performance_logger.warning(f"[GEN-{generation_id:04d}] Slow generation: {generation_time:.2f}s")
            elif generation_time < 1:
                performance_logger.debug(f"[GEN-{generation_id:04d}] Fast generation: {generation_time:.2f}s")
            
            # Log periodic performance summary
            if generation_id % 10 == 0:
                self._log_performance_summary()
            
            return generated_text
                
        except Exception as e:
            generation_time = time.time() - start_time
            
            with self._lock:
                self._generation_stats['failed_generations'] += 1
            
            error_logger.error(f"[GEN-{generation_id:04d}] Generation failed after {generation_time:.2f}s: {e}")
            generation_logger.debug(f"[GEN-{generation_id:04d}] Full error traceback:\n{traceback.format_exc()}")
            
            # Provide specific error guidance
            if "out of memory" in str(e).lower():
                error_logger.error("Out of memory - try reducing max_tokens or context length")
            elif "cuda" in str(e).lower():
                error_logger.error("CUDA error - check GPU memory and drivers")
            
            raise LLMError(
                f"Text generation failed: {str(e)}",
                recoverable=True,
                backend="LlamaCppBackend"
            )
    
    def _log_performance_summary(self):
        """Log performance summary statistics."""
        stats = self._generation_stats
        
        if stats['total_generations'] > 0:
            success_rate = (stats['successful_generations'] / stats['total_generations']) * 100
            avg_generation_time = stats['total_generation_time'] / max(stats['successful_generations'], 1)
            
            performance_logger.info(
                f"LlamaCpp Performance Summary - "
                f"Generations: {stats['total_generations']} "
                f"(✅ {stats['successful_generations']}, ❌ {stats['failed_generations']}), "
                f"Success Rate: {success_rate:.1f}%, "
                f"Avg Generation Time: {avg_generation_time:.2f}s, "
                f"Avg Speed: {stats['avg_tokens_per_second']:.1f} tokens/s"
            )
            
            if stats['model_load_time']:
                performance_logger.debug(f"Model loaded in {stats['model_load_time']:.2f}s")
            
            if stats['total_tokens_generated'] > 0:
                performance_logger.debug(f"Total tokens generated: {stats['total_tokens_generated']}")
    
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
        
        # Add system prompt if not using chat format
        if system_prompt and not self.config.get("chat_format"):
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
        Check if LlamaCpp backend is available.
        
        Returns:
            True if backend is available, False otherwise
        """
        return self._llama is not None
    
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
                "LlamaCpp backend not available",
                recoverable=False,
                backend="LlamaCppBackend"
            )
        
        return self._model_info
    
    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys.
        
        Returns:
            List of required configuration key names
        """
        return ["model_path"]
    
    def chunk_content(self, content: str, max_chunk_size: Optional[int] = None) -> List[str]:
        """
        Chunk content to fit within model token limits.
        
        Uses llama.cpp tokenizer for accurate token counting if available.
        
        Args:
            content: Content to chunk
            max_chunk_size: Maximum chunk size in tokens
            
        Returns:
            List of content chunks
        """
        if max_chunk_size is None:
            model_info = self.get_model_info()
            # Use 60% of context length for content, leaving room for prompt
            max_chunk_size = int(model_info.context_length * 0.6)
        
        if not self.is_available():
            # Fallback to character-based chunking
            return super().chunk_content(content, max_chunk_size * 4)  # Rough estimate
        
        try:
            # Use llama.cpp tokenizer for accurate chunking
            tokens = self._llama.tokenize(content.encode('utf-8'))
            
            if len(tokens) <= max_chunk_size:
                return [content]
            
            chunks = []
            current_pos = 0
            overlap_tokens = self.config.get("chunk_overlap_tokens", 50)  # Token overlap between chunks
            
            while current_pos < len(tokens):
                end_pos = min(current_pos + max_chunk_size, len(tokens))
                
                # Try to break at natural boundaries
                if end_pos < len(tokens):
                    # Look for sentence or paragraph breaks in the last 20% of chunk
                    search_start = max(current_pos, end_pos - int(max_chunk_size * 0.2))
                    
                    # Decode tokens to find natural breaks
                    chunk_tokens = tokens[search_start:end_pos]
                    chunk_text = self._llama.detokenize(chunk_tokens).decode('utf-8', errors='ignore')
                    
                    # Look for natural breaks
                    for break_char in ['\n\n', '\n', '.', ';', ',']:
                        break_pos = chunk_text.rfind(break_char)
                        if break_pos > len(chunk_text) * 0.5:  # At least halfway through
                            # Adjust end_pos based on break position
                            break_tokens = self._llama.tokenize(chunk_text[:break_pos + 1].encode('utf-8'))
                            end_pos = search_start + len(break_tokens)
                            break
                
                # Extract chunk
                chunk_tokens = tokens[current_pos:end_pos]
                chunk_text = self._llama.detokenize(chunk_tokens).decode('utf-8', errors='ignore')
                chunks.append(chunk_text)
                
                # Move position with overlap for better context continuity
                current_pos = max(end_pos - overlap_tokens, current_pos + 1)
                if current_pos >= len(tokens):
                    break
            
            return chunks
            
        except Exception as e:
            logger.warning(f"Token-based chunking failed, falling back to character-based: {e}")
            return super().chunk_content(content, max_chunk_size * 4)  # Rough estimate
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not self.is_available():
            # Rough estimate: 4 characters per token
            return len(text) // 4
        
        try:
            tokens = self._llama.tokenize(text.encode('utf-8'))
            return len(tokens)
        except Exception as e:
            logger.warning(f"Token estimation failed: {e}")
            return len(text) // 4
    
    def validate_input_length(self, prompt: str, context_chunks: Optional[List[str]] = None) -> bool:
        """
        Validate that input fits within model context limits.
        
        Args:
            prompt: Main prompt
            context_chunks: Optional context chunks
            
        Returns:
            True if input fits, False otherwise
        """
        if not self.is_available():
            return True  # Can't validate without model
        
        try:
            model_info = self.get_model_info()
            max_input_tokens = int(model_info.context_length * 0.8)  # Leave room for generation
            
            total_tokens = self.estimate_tokens(prompt)
            
            if context_chunks:
                for chunk in context_chunks:
                    total_tokens += self.estimate_tokens(chunk)
            
            return total_tokens <= max_input_tokens
            
        except Exception as e:
            logger.warning(f"Input validation failed: {e}")
            return True  # Assume valid if validation fails
    
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
                # Try to fit a truncated version using accurate tokenization
                remaining_tokens = available_for_context - used_tokens
                if remaining_tokens > 100:  # Only if reasonable space left
                    try:
                        # Use tokenizer to get exact truncation
                        chunk_tokens_list = self._llama.tokenize(chunk.encode('utf-8'))
                        if len(chunk_tokens_list) > remaining_tokens:
                            truncated_tokens = chunk_tokens_list[:remaining_tokens-10]  # Leave room for truncation marker
                            truncated_text = self._llama.detokenize(truncated_tokens).decode('utf-8', errors='ignore')
                            truncated_chunk = truncated_text + "... [truncated]"
                            selected_chunks.append(truncated_chunk)
                    except Exception as e:
                        logger.warning(f"Token-based truncation failed: {e}")
                        # Fallback to character-based truncation
                        chars_to_keep = remaining_tokens * 4
                        truncated_chunk = chunk[:chars_to_keep] + "... [truncated]"
                        selected_chunks.append(truncated_chunk)
                break
        
        if len(selected_chunks) < len(context_chunks):
            logger.info(f"Reduced context from {len(context_chunks)} to {len(selected_chunks)} chunks")
        
        return selected_chunks