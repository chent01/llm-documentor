"""
Feature extraction service.

This module handles the extraction of software features from code chunks
using both LLM-based analysis and heuristic fallback methods.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.core import CodeChunk, Feature, CodeReference
from ..models.enums import FeatureCategory
from ..llm.backend import LLMBackend, LLMError
from ..models.result_models import FeatureExtractionResult
from .llm_response_parser import LLMResponseParser


class FeatureExtractor:
    """Service for extracting software features from code chunks."""
    
    def __init__(self, llm_backend: LLMBackend, min_confidence: float = 0.3):
        """
        Initialize the feature extractor.
        
        Args:
            llm_backend: LLM backend for analysis
            min_confidence: Minimum confidence threshold for features
        """
        self.llm_backend = llm_backend
        self.min_confidence = min_confidence
        self.feature_counter = 0
        
        # Feature extraction prompts
        self.system_prompt = """You are an expert software analyst specializing in medical device software. Your task is to analyze code chunks and identify implemented software features. Focus on functional capabilities that would be relevant for medical device documentation and requirements traceability.

For each feature you identify, provide:
1. A clear, concise description of what the feature does
2. The category it belongs to (data_processing, user_interface, communication, safety, device_control, algorithm, storage, validation, monitoring, or configuration)
3. A confidence score (0.0 to 1.0) based on how certain you are about the feature
4. Evidence from the code that supports your identification

Respond in JSON format with an array of features."""
        
        self.prompt_template = """Analyze the following code chunk and identify software features implemented in it:

File: {file_path}
Lines: {start_line}-{end_line}
Function: {function_name}
Language: {language}

Code:
```{language}
{code_content}
```

Context: This is part of a medical device software project. Look for features related to:
- Data processing and validation
- User interface components
- Device communication
- Safety mechanisms
- Control algorithms
- Data storage and retrieval
- Configuration management
- Monitoring and logging

Respond with a JSON array of features in this format:
[
  {{
    "description": "Clear description of the feature",
    "category": "data_processing|user_interface|communication|safety|device_control|algorithm|storage|validation|monitoring|configuration",
    "confidence": 0.85,
    "evidence": ["Specific code elements that indicate this feature", "Function calls, variable names, etc."]
  }}
]

Only include features you can clearly identify from the code. If no clear features are present, return an empty array."""
    
    def extract_features(self, chunks: List[CodeChunk]) -> FeatureExtractionResult:
        """
        Extract features from a list of code chunks.
        
        Args:
            chunks: List of code chunks to analyze
            
        Returns:
            FeatureExtractionResult with extracted features and metadata
        """
        start_time = datetime.now()
        all_features = []
        errors = []
        chunks_processed = 0
        
        for chunk in chunks:
            try:
                features = self._extract_features_from_chunk(chunk)
                all_features.extend(features)
                chunks_processed += 1
            except Exception as e:
                error_msg = f"Error processing chunk {chunk.file_path}:{chunk.start_line}: {str(e)}"
                errors.append(error_msg)
                continue
        
        # Calculate overall confidence score
        if all_features:
            overall_confidence = sum(f.confidence for f in all_features) / len(all_features)
        else:
            overall_confidence = 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return FeatureExtractionResult(
            features=all_features,
            confidence_score=overall_confidence,
            processing_time=processing_time,
            chunks_processed=chunks_processed,
            errors=errors,
            metadata={
                'total_chunks': len(chunks),
                'successful_chunks': chunks_processed,
                'failed_chunks': len(chunks) - chunks_processed,
                'features_per_chunk': len(all_features) / max(chunks_processed, 1),
                'llm_backend': self.llm_backend.__class__.__name__
            }
        )
    
    def _extract_features_from_chunk(self, chunk: CodeChunk) -> List[Feature]:
        """
        Extract features from a single code chunk.
        
        Args:
            chunk: Code chunk to analyze
            
        Returns:
            List of extracted features
        """
        # Prepare prompt with chunk information
        language = chunk.metadata.get('language', 'unknown')
        function_name = chunk.function_name or 'global'
        
        prompt = self.prompt_template.format(
            file_path=chunk.file_path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            function_name=function_name,
            language=language,
            code_content=chunk.content
        )
        
        try:
            # Generate response using LLM
            response = self.llm_backend.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse JSON response
            features_data = LLMResponseParser.parse_json_response(response)
            
            # Convert to Feature objects
            features = []
            for feature_data in features_data:
                feature = self._create_feature_from_data(feature_data, chunk)
                if feature and feature.confidence >= self.min_confidence:
                    features.append(feature)
            
            return features
            
        except LLMError as e:
            if not e.recoverable:
                raise
            # Try fallback analysis for recoverable errors
            return self._fallback_feature_extraction(chunk)
        except Exception as e:
            raise Exception(f"Feature extraction failed: {str(e)}")
    
    def _create_feature_from_data(self, feature_data: Dict[str, Any], chunk: CodeChunk) -> Optional[Feature]:
        """
        Create a Feature object from parsed data.
        
        Args:
            feature_data: Dictionary with feature information
            chunk: Source code chunk
            
        Returns:
            Feature object or None if invalid
        """
        try:
            # Validate required fields
            if not LLMResponseParser.validate_required_fields(feature_data, ['description']):
                return None
            
            description = feature_data['description'].strip()
            
            # Parse confidence
            confidence = LLMResponseParser.clamp_confidence(feature_data.get('confidence', 0.5))
            
            # Parse category
            category_str = feature_data.get('category', 'data_processing').lower()
            category = self._parse_feature_category(category_str)
            
            # Create evidence from code references
            evidence_list = feature_data.get('evidence', [])
            if not isinstance(evidence_list, list):
                evidence_list = [str(evidence_list)] if evidence_list else []
            
            # Create code reference for this chunk
            code_ref = CodeReference(
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                function_name=chunk.function_name,
                context=f"Evidence: {'; '.join(evidence_list[:3])}"  # Limit context length
            )
            
            # Generate unique feature ID
            self.feature_counter += 1
            feature_id = f"FEAT_{self.feature_counter:04d}"
            
            return Feature(
                id=feature_id,
                description=description,
                confidence=confidence,
                evidence=[code_ref],
                category=category,
                metadata={
                    'source_chunk': {
                        'file_path': chunk.file_path,
                        'start_line': chunk.start_line,
                        'end_line': chunk.end_line,
                        'function_name': chunk.function_name
                    },
                    'evidence_details': evidence_list,
                    'extraction_method': 'llm',
                    'chunk_type': chunk.chunk_type.name,
                    'language': chunk.metadata.get('language', 'unknown')
                }
            )
            
        except (ValueError, KeyError, TypeError):
            return None
    
    def _parse_feature_category(self, category_str: str) -> FeatureCategory:
        """
        Parse feature category from string.
        
        Args:
            category_str: Category string from LLM
            
        Returns:
            FeatureCategory enum value
        """
        category_mapping = {
            'data_processing': FeatureCategory.DATA_PROCESSING,
            'user_interface': FeatureCategory.USER_INTERFACE,
            'communication': FeatureCategory.COMMUNICATION,
            'safety': FeatureCategory.SAFETY,
            'device_control': FeatureCategory.DEVICE_CONTROL,
            'algorithm': FeatureCategory.ALGORITHM,
            'storage': FeatureCategory.STORAGE,
            'validation': FeatureCategory.VALIDATION,
            'monitoring': FeatureCategory.MONITORING,
            'configuration': FeatureCategory.CONFIGURATION
        }
        
        return category_mapping.get(category_str, FeatureCategory.DATA_PROCESSING)
    
    def _fallback_feature_extraction(self, chunk: CodeChunk) -> List[Feature]:
        """
        Fallback feature extraction using heuristics when LLM fails.
        
        Args:
            chunk: Code chunk to analyze
            
        Returns:
            List of features extracted using heuristics
        """
        features = []
        content = chunk.content.lower()
        
        # Simple heuristic-based feature detection
        heuristics = [
            {
                'keywords': ['printf', 'cout', 'console.log', 'alert', 'display'],
                'category': FeatureCategory.USER_INTERFACE,
                'description': 'User output/display functionality',
                'confidence': 0.4
            },
            {
                'keywords': ['scanf', 'cin', 'input', 'readline', 'prompt'],
                'category': FeatureCategory.USER_INTERFACE,
                'description': 'User input functionality',
                'confidence': 0.4
            },
            {
                'keywords': ['malloc', 'free', 'new', 'delete', 'alloc'],
                'category': FeatureCategory.DATA_PROCESSING,
                'description': 'Memory management functionality',
                'confidence': 0.3
            },
            {
                'keywords': ['file', 'fopen', 'fclose', 'read', 'write', 'save', 'load'],
                'category': FeatureCategory.STORAGE,
                'description': 'File I/O functionality',
                'confidence': 0.4
            },
            {
                'keywords': ['validate', 'check', 'verify', 'assert', 'test'],
                'category': FeatureCategory.VALIDATION,
                'description': 'Data validation functionality',
                'confidence': 0.3
            },
            {
                'keywords': ['error', 'exception', 'try', 'catch', 'handle'],
                'category': FeatureCategory.SAFETY,
                'description': 'Error handling functionality',
                'confidence': 0.4
            }
        ]
        
        for heuristic in heuristics:
            if any(keyword in content for keyword in heuristic['keywords']):
                self.feature_counter += 1
                feature_id = f"FEAT_{self.feature_counter:04d}"
                
                code_ref = CodeReference(
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    function_name=chunk.function_name,
                    context="Heuristic-based detection"
                )
                
                feature = Feature(
                    id=feature_id,
                    description=heuristic['description'],
                    confidence=heuristic['confidence'],
                    evidence=[code_ref],
                    category=heuristic['category'],
                    metadata={
                        'source_chunk': {
                            'file_path': chunk.file_path,
                            'start_line': chunk.start_line,
                            'end_line': chunk.end_line,
                            'function_name': chunk.function_name
                        },
                        'extraction_method': 'heuristic',
                        'matched_keywords': [kw for kw in heuristic['keywords'] if kw in content],
                        'chunk_type': chunk.chunk_type.name,
                        'language': chunk.metadata.get('language', 'unknown')
                    }
                )
                features.append(feature)
        
        return features
    
    def get_statistics(self, features: List[Feature]) -> Dict[str, Any]:
        """
        Get statistics about extracted features.
        
        Args:
            features: List of extracted features
            
        Returns:
            Dictionary with feature statistics
        """
        if not features:
            return {
                'total_features': 0,
                'average_confidence': 0.0,
                'categories': {},
                'high_confidence_features': 0,
                'medium_confidence_features': 0,
                'low_confidence_features': 0
            }
        
        # Calculate confidence statistics
        confidences = [f.confidence for f in features]
        avg_confidence = sum(confidences) / len(confidences)
        
        high_conf = sum(1 for c in confidences if c >= 0.7)
        medium_conf = sum(1 for c in confidences if 0.4 <= c < 0.7)
        low_conf = sum(1 for c in confidences if c < 0.4)
        
        # Count by category
        categories = {}
        for feature in features:
            cat_name = feature.category.name
            categories[cat_name] = categories.get(cat_name, 0) + 1
        
        return {
            'total_features': len(features),
            'average_confidence': avg_confidence,
            'max_confidence': max(confidences),
            'min_confidence': min(confidences),
            'categories': categories,
            'high_confidence_features': high_conf,
            'medium_confidence_features': medium_conf,
            'low_confidence_features': low_conf,
            'extraction_methods': self._count_extraction_methods(features)
        }
    
    def _count_extraction_methods(self, features: List[Feature]) -> Dict[str, int]:
        """Count features by extraction method."""
        methods = {}
        for feature in features:
            method = feature.metadata.get('extraction_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        return methods
    
    def filter_by_confidence(self, features: List[Feature], min_confidence: float) -> List[Feature]:
        """
        Filter features by minimum confidence threshold.
        
        Args:
            features: List of features to filter
            min_confidence: Minimum confidence threshold
            
        Returns:
            Filtered list of features
        """
        return [f for f in features if f.confidence >= min_confidence]
    
    def group_by_file(self, features: List[Feature]) -> Dict[str, List[Feature]]:
        """
        Group features by source file.
        
        Args:
            features: List of features to group
            
        Returns:
            Dictionary mapping file paths to feature lists
        """
        grouped = {}
        for feature in features:
            if feature.evidence:
                file_path = feature.evidence[0].file_path
                if file_path not in grouped:
                    grouped[file_path] = []
                grouped[file_path].append(feature)
        return grouped