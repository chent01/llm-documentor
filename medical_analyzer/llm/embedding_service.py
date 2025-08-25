"""
Embedding service with FAISS vector store for local LLM integration.

This module provides embedding generation and similarity search capabilities
using sentence-transformers and FAISS for medical device software analysis.
"""

import os
import pickle
import logging
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass

from ..models.core import CodeChunk

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding search with similarity score."""
    chunk: CodeChunk
    similarity: float
    index: int


class EmbeddingService:
    """
    Service for generating embeddings and performing similarity search.
    
    Uses sentence-transformers for local embedding generation and FAISS
    for efficient vector storage and retrieval without cloud dependencies.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            cache_dir: Directory to cache embeddings and model files
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or os.path.expanduser("~/.medical_analyzer/embeddings")
        self._model = None
        self._index = None
        self._chunks: List[CodeChunk] = []
        self._embeddings: Optional[np.ndarray] = None
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=os.path.join(self.cache_dir, "models")
            )
            logger.info("Embedding model loaded successfully")
            
        except ImportError:
            logger.warning(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
            self._model = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._model = None
    
    def is_available(self) -> bool:
        """
        Check if the embedding service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        return self._model is not None
    
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array, None if service unavailable
        """
        if not self.is_available():
            logger.warning("Embedding service not available")
            return None
        
        try:
            embedding = self._model.encode([text], convert_to_numpy=True)
            return embedding[0]
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def embed_chunks(self, chunks: List[CodeChunk]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple code chunks.
        
        Args:
            chunks: List of code chunks to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.is_available():
            logger.warning("Embedding service not available")
            return []
        
        try:
            # Prepare texts for embedding
            texts = []
            for chunk in chunks:
                # Combine file path, function name, and content for better context
                text_parts = []
                
                if chunk.file_path:
                    text_parts.append(f"File: {chunk.file_path}")
                
                if chunk.function_name:
                    text_parts.append(f"Function: {chunk.function_name}")
                
                text_parts.append(f"Code: {chunk.content}")
                
                texts.append(" | ".join(text_parts))
            
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            
            return [embedding for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []
    
    def build_index(self, chunks: List[CodeChunk]) -> bool:
        """
        Build FAISS index from code chunks.
        
        Args:
            chunks: List of code chunks to index
            
        Returns:
            True if index built successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Embedding service not available")
            return False
        
        try:
            import faiss
            
            # Generate embeddings
            embeddings = self.embed_chunks(chunks)
            if not embeddings:
                logger.error("No embeddings generated")
                return False
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings).astype('float32')
            
            # Create FAISS index
            dimension = embeddings_array.shape[1]
            logger.info(f"Creating FAISS index with dimension {dimension}")
            
            # Use IndexFlatIP for cosine similarity (after normalization)
            index = faiss.IndexFlatIP(dimension)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_array)
            
            # Add embeddings to index
            index.add(embeddings_array)
            
            # Store index and chunks
            self._index = index
            self._chunks = chunks.copy()
            self._embeddings = embeddings_array
            
            logger.info(f"Built FAISS index with {len(chunks)} chunks")
            return True
            
        except ImportError:
            logger.warning("FAISS not available. Install with: pip install faiss-cpu")
            return False
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            return False
    
    def search(self, query: str, k: int = 5, min_similarity: float = 0.0) -> List[EmbeddingResult]:
        """
        Search for similar code chunks using embedding similarity.
        
        Args:
            query: Search query text
            k: Number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of embedding results sorted by similarity
        """
        if not self.is_available() or self._index is None:
            logger.warning("Embedding service or index not available")
            return []
        
        try:
            import faiss
            
            # Generate query embedding
            query_embedding = self.embed_text(query)
            if query_embedding is None:
                return []
            
            # Normalize query embedding
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search index
            similarities, indices = self._index.search(query_embedding, min(k, len(self._chunks)))
            
            # Prepare results
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx >= 0 and similarity >= min_similarity:
                    results.append(EmbeddingResult(
                        chunk=self._chunks[idx],
                        similarity=float(similarity),
                        index=int(idx)
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            return []
    
    def save_index(self, filepath: str) -> bool:
        """
        Save the FAISS index and associated data to disk.
        
        Args:
            filepath: Path to save the index
            
        Returns:
            True if saved successfully, False otherwise
        """
        if self._index is None:
            logger.warning("No index to save")
            return False
        
        try:
            import faiss
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self._index, f"{filepath}.faiss")
            
            # Save chunks and metadata
            metadata = {
                'chunks': self._chunks,
                'model_name': self.model_name,
                'embeddings_shape': self._embeddings.shape if self._embeddings is not None else None
            }
            
            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved index to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def load_index(self, filepath: str) -> bool:
        """
        Load FAISS index and associated data from disk.
        
        Args:
            filepath: Path to load the index from
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            import faiss
            
            # Check if files exist
            if not os.path.exists(f"{filepath}.faiss") or not os.path.exists(f"{filepath}.pkl"):
                logger.warning(f"Index files not found at {filepath}")
                return False
            
            # Load FAISS index
            self._index = faiss.read_index(f"{filepath}.faiss")
            
            # Load metadata
            with open(f"{filepath}.pkl", 'rb') as f:
                metadata = pickle.load(f)
            
            self._chunks = metadata['chunks']
            
            # Verify model compatibility
            if metadata['model_name'] != self.model_name:
                logger.warning(
                    f"Model mismatch: saved with {metadata['model_name']}, "
                    f"current is {self.model_name}"
                )
            
            logger.info(f"Loaded index from {filepath} with {len(self._chunks)} chunks")
            return True
            
        except ImportError:
            logger.warning("FAISS not available for loading index")
            return False
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def get_chunk_by_index(self, index: int) -> Optional[CodeChunk]:
        """
        Get code chunk by its index in the vector store.
        
        Args:
            index: Index of the chunk
            
        Returns:
            CodeChunk if found, None otherwise
        """
        if 0 <= index < len(self._chunks):
            return self._chunks[index]
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embedding service and index.
        
        Returns:
            Dictionary with service statistics
        """
        stats = {
            'model_name': self.model_name,
            'is_available': self.is_available(),
            'cache_dir': self.cache_dir,
            'index_built': self._index is not None,
            'num_chunks': len(self._chunks),
            'embedding_dimension': None
        }
        
        if self._embeddings is not None:
            stats['embedding_dimension'] = self._embeddings.shape[1]
        
        return stats
    
    def clear_index(self) -> None:
        """Clear the current index and associated data."""
        self._index = None
        self._chunks = []
        self._embeddings = None
        logger.info("Cleared embedding index")
    
    def update_chunks(self, chunks: List[CodeChunk]) -> bool:
        """
        Update the index with new chunks (rebuilds the entire index).
        
        Args:
            chunks: New list of code chunks
            
        Returns:
            True if updated successfully, False otherwise
        """
        logger.info("Updating embedding index with new chunks")
        self.clear_index()
        return self.build_index(chunks)
    
    def get_similar_chunks(
        self, 
        chunk: CodeChunk, 
        k: int = 5, 
        exclude_self: bool = True
    ) -> List[EmbeddingResult]:
        """
        Find chunks similar to the given chunk.
        
        Args:
            chunk: Reference chunk to find similar chunks for
            k: Number of similar chunks to return
            exclude_self: Whether to exclude the reference chunk from results
            
        Returns:
            List of similar chunks
        """
        # Use the chunk content as query
        query_text = f"File: {chunk.file_path} | Function: {chunk.function_name} | Code: {chunk.content}"
        results = self.search(query_text, k + (1 if exclude_self else 0))
        
        if exclude_self:
            # Filter out the exact same chunk
            results = [
                result for result in results 
                if not (result.chunk.file_path == chunk.file_path and 
                       result.chunk.start_line == chunk.start_line and
                       result.chunk.end_line == chunk.end_line)
            ][:k]
        
        return results