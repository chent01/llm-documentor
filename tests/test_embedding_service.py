"""
Unit tests for embedding service with FAISS vector store.

Tests embedding generation, similarity search, and vector store operations
for the local LLM integration layer.
"""

import pytest
import tempfile
import os
import shutil
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from medical_analyzer.llm.embedding_service import EmbeddingService, EmbeddingResult
from medical_analyzer.models.core import CodeChunk
from medical_analyzer.models.enums import ChunkType


class TestEmbeddingService:
    """Test cases for EmbeddingService class."""
    
    def test_initialization_no_sentence_transformers(self):
        """Test initialization when sentence-transformers is not available."""
        with patch('medical_analyzer.llm.embedding_service.logger') as mock_logger:
            with patch('sentence_transformers.SentenceTransformer', side_effect=ImportError("No module")):
                service = EmbeddingService()
                
                assert not service.is_available()
                assert service._model is None
    
    def test_initialization_with_cache_dir(self):
        """Test initialization with custom cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, "embeddings")
            
            service = EmbeddingService(cache_dir=cache_dir)
            
            assert service.cache_dir == cache_dir
            assert os.path.exists(cache_dir)
    
    def test_embed_text_not_available(self):
        """Test text embedding when service is not available."""
        with patch('sentence_transformers.SentenceTransformer', side_effect=ImportError("No module")):
            service = EmbeddingService()
            
            result = service.embed_text("test text")
            assert result is None
    
    def test_embed_chunks_not_available(self):
        """Test chunk embedding when service is not available."""
        with patch('sentence_transformers.SentenceTransformer', side_effect=ImportError("No module")):
            service = EmbeddingService()
            
            chunks = [
                CodeChunk(
                    file_path="test.c",
                    start_line=1,
                    end_line=5,
                    content="int main() { return 0; }",
                    function_name="main",
                    chunk_type=ChunkType.FUNCTION
                )
            ]
            
            result = service.embed_chunks(chunks)
            assert result == []
    
    def test_build_index_not_available(self):
        """Test index building when service is not available."""
        with patch('sentence_transformers.SentenceTransformer', side_effect=ImportError("No module")):
            service = EmbeddingService()
            
            chunks = [
                CodeChunk(
                    file_path="test.c",
                    start_line=1,
                    end_line=5,
                    content="int main() { return 0; }",
                    function_name="main",
                    chunk_type=ChunkType.FUNCTION
                )
            ]
            
            result = service.build_index(chunks)
            assert result is False
    
    def test_search_not_available(self):
        """Test search when service is not available."""
        service = EmbeddingService()
        
        results = service.search("test query")
        assert results == []
    
    def test_get_stats(self):
        """Test getting service statistics."""
        service = EmbeddingService(model_name="test-model")
        
        stats = service.get_stats()
        
        assert stats['model_name'] == "test-model"
        assert stats['is_available'] is False
        assert stats['index_built'] is False
        assert stats['num_chunks'] == 0
        assert stats['embedding_dimension'] is None
    
    def test_clear_index(self):
        """Test clearing the index."""
        service = EmbeddingService()
        
        # Simulate having some data
        service._chunks = [Mock()]
        service._index = Mock()
        service._embeddings = np.array([[1, 2, 3]])
        
        service.clear_index()
        
        assert service._chunks == []
        assert service._index is None
        assert service._embeddings is None
    
    def test_get_chunk_by_index(self):
        """Test getting chunk by index."""
        service = EmbeddingService()
        
        chunk = CodeChunk(
            file_path="test.c",
            start_line=1,
            end_line=5,
            content="int main() { return 0; }",
            function_name="main",
            chunk_type=ChunkType.FUNCTION
        )
        
        service._chunks = [chunk]
        
        # Valid index
        result = service.get_chunk_by_index(0)
        assert result == chunk
        
        # Invalid indices
        assert service.get_chunk_by_index(-1) is None
        assert service.get_chunk_by_index(1) is None
    
    def test_save_index_no_index(self):
        """Test saving index when no index exists."""
        service = EmbeddingService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_index")
            
            result = service.save_index(filepath)
            assert result is False
    
    def test_load_index_files_not_exist(self):
        """Test loading index when files don't exist."""
        service = EmbeddingService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "nonexistent_index")
            
            result = service.load_index(filepath)
            assert result is False


class TestEmbeddingServiceWithMocks:
    """Test cases for EmbeddingService with mocked dependencies."""
    
    def test_initialization_success(self):
        """Test successful initialization when dependencies are available."""
        service = EmbeddingService(model_name="all-MiniLM-L6-v2")
        # In our test environment, dependencies are available
        assert service.is_available()
        assert service._model is not None
    
    def test_embed_text_success(self):
        """Test successful text embedding."""
        service = EmbeddingService()
        result = service.embed_text("test text")
        
        # Should return a numpy array with embeddings
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 1  # 1D array
        assert result.shape[0] > 0  # Has dimensions
    
    def test_embed_text_error(self):
        """Test text embedding error handling."""
        service = EmbeddingService()
        
        # Mock the model to raise an exception
        with patch.object(service, '_model') as mock_model:
            mock_model.encode.side_effect = Exception("Model error")
            
            result = service.embed_text("test text")
            assert result is None
    
    def test_embed_chunks_success(self):
        """Test successful chunk embedding."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            ),
            CodeChunk(
                file_path="test2.c",
                start_line=10,
                end_line=15,
                content="void helper() { printf(\"hello\"); }",
                function_name="helper",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        results = service.embed_chunks(chunks)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, np.ndarray)
            assert len(result.shape) == 1
            assert result.shape[0] > 0
    
    def test_build_index_success(self):
        """Test successful index building."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            ),
            CodeChunk(
                file_path="test2.c",
                start_line=10,
                end_line=15,
                content="void helper() { printf(\"hello\"); }",
                function_name="helper",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        result = service.build_index(chunks)
        
        assert result is True
        assert service._index is not None
        assert len(service._chunks) == 2
        assert service._embeddings is not None
    
    def test_build_index_no_embeddings(self):
        """Test index building when no embeddings are generated."""
        chunks = [
            CodeChunk(
                file_path="test.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        
        # Mock embed_chunks to return empty list
        with patch.object(service, 'embed_chunks', return_value=[]):
            result = service.build_index(chunks)
            assert result is False
            assert service._index is None
    
    def test_search_success(self):
        """Test successful search functionality."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            ),
            CodeChunk(
                file_path="test2.c",
                start_line=10,
                end_line=15,
                content="void helper() { printf(\"hello\"); }",
                function_name="helper",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        service.build_index(chunks)
        
        results = service.search("main function", k=2)
        
        assert len(results) <= 2
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert isinstance(result.chunk, CodeChunk)
            assert isinstance(result.similarity, float)
            assert isinstance(result.index, int)
    
    def test_search_with_min_similarity(self):
        """Test search with minimum similarity threshold."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            ),
            CodeChunk(
                file_path="test2.c",
                start_line=10,
                end_line=15,
                content="void helper() { printf(\"hello\"); }",
                function_name="helper",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        service.build_index(chunks)
        
        # Use high similarity threshold to potentially filter results
        results = service.search("main function", k=2, min_similarity=0.9)
        
        # All results should meet the minimum similarity threshold
        for result in results:
            assert result.similarity >= 0.9
    
    def test_save_index_success(self):
        """Test successful index saving."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        service = EmbeddingService()
        service.build_index(chunks)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_index")
            result = service.save_index(filepath)
            
            assert result is True
            assert os.path.exists(f"{filepath}.faiss")
            assert os.path.exists(f"{filepath}.pkl")
    
    def test_load_index_success(self):
        """Test successful index loading."""
        chunks = [
            CodeChunk(
                file_path="test1.c",
                start_line=1,
                end_line=5,
                content="int main() { return 0; }",
                function_name="main",
                chunk_type=ChunkType.FUNCTION
            )
        ]
        
        # Create and save an index
        service1 = EmbeddingService(model_name="all-MiniLM-L6-v2")
        service1.build_index(chunks)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_index")
            save_result = service1.save_index(filepath)
            assert save_result is True
            
            # Load the index in a new service
            service2 = EmbeddingService(model_name="all-MiniLM-L6-v2")
            load_result = service2.load_index(filepath)
            
            assert load_result is True
            assert len(service2._chunks) == 1
            assert service2._index is not None
    
    def test_get_similar_chunks(self):
        """Test finding similar chunks when service is not available."""
        service = EmbeddingService()
        
        reference_chunk = CodeChunk(
            file_path="test.c",
            start_line=1,
            end_line=5,
            content="int main() { return 0; }",
            function_name="main",
            chunk_type=ChunkType.FUNCTION
        )
        
        results = service.get_similar_chunks(reference_chunk, k=5, exclude_self=True)
        assert results == []


class TestEmbeddingResult:
    """Test cases for EmbeddingResult dataclass."""
    
    def test_embedding_result_creation(self):
        """Test EmbeddingResult creation."""
        chunk = CodeChunk(
            file_path="test.c",
            start_line=1,
            end_line=5,
            content="int main() { return 0; }",
            function_name="main",
            chunk_type=ChunkType.FUNCTION
        )
        
        result = EmbeddingResult(
            chunk=chunk,
            similarity=0.85,
            index=42
        )
        
        assert result.chunk == chunk
        assert result.similarity == 0.85
        assert result.index == 42


if __name__ == "__main__":
    pytest.main([__file__])