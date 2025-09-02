"""
Requirements generation service.

This module handles the generation of user requirements and software requirements
from extracted features, following the proper requirements engineering flow:
Code → Features → User Requirements → Software Requirements → Risks
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models.core import Feature, Requirement, CodeReference
from ..models.enums import RequirementType, FeatureCategory
from ..llm.backend import LLMBackend, LLMError
from ..llm.api_response_validator import APIResponseValidator, ValidationResult
from ..models.result_models import RequirementsGenerationResult
from .llm_response_parser import LLMResponseParser

logger = logging.getLogger(__name__)


class RequirementsGenerator:
    """Service for generating requirements from extracted features."""
    
    def __init__(self, llm_backend: LLMBackend):
        """
        Initialize the requirements generator.
        
        Args:
            llm_backend: LLM backend for analysis
        """
        self.llm_backend = llm_backend
        self.ur_counter = 0
        self.sr_counter = 0
        
        # Initialize API response validator for requirements generation
        self._validator = APIResponseValidator()
        self._setup_requirements_validation_schemas()
        
        # Generation statistics
        self._generation_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'validation_failures': 0,
            'fallback_generations': 0,
            'retry_attempts': 0
        }
    
    def set_api_validator(self, validator: APIResponseValidator):
        """Set a custom API response validator."""
        self._validator = validator
        self._setup_requirements_validation_schemas()
    
    def _setup_requirements_validation_schemas(self) -> None:
        """Setup validation schemas specific to requirements generation."""
        
        # Schema for user requirements generation response
        user_requirements_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "minLength": 10},
                    "rationale": {"type": "string"},
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    },
                    "related_features": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["description", "acceptance_criteria"]
            },
            "minItems": 1,
            "maxItems": 10
        }
        
        # Schema for software requirements generation response
        software_requirements_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "minLength": 10},
                    "type": {
                        "type": "string",
                        "enum": ["functional", "performance", "security", "safety", "interface", "data"]
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    },
                    "implementation_notes": {"type": "string"}
                },
                "required": ["description", "acceptance_criteria"]
            },
            "minItems": 1,
            "maxItems": 8
        }
        
        # Add schemas to validator
        self._validator.add_schema('user_requirements_generation', {
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"}
                                },
                                "required": ["content"]
                            }
                        },
                        "required": ["message"]
                    },
                    "minItems": 1
                }
            },
            "required": ["choices"]
        })
        
        self._validator.add_schema('software_requirements_generation', {
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"}
                                },
                                "required": ["content"]
                            }
                        },
                        "required": ["message"]
                    },
                    "minItems": 1
                }
            },
            "required": ["choices"]
        })
        
        # User requirements generation prompts
        self.ur_system_prompt = """You are an expert requirements engineer specializing in medical device software. Your task is to analyze extracted software features and generate high-level user requirements that describe what users need from the system.

User requirements should be:
- Written from the user's perspective
- High-level and goal-oriented
- Independent of implementation details
- Focused on what the system should accomplish for users
- Traceable to the features that implement them

Respond in JSON format with an array of user requirements."""
        
        self.ur_prompt_template = """Analyze the following software features and generate user requirements that these features would satisfy:

Features:
{features_text}

Context: This is part of a medical device software project. Generate user requirements that:
- Describe what users need to accomplish with the system
- Are written from the user's perspective (not technical implementation)
- Group related features under common user goals
- Focus on clinical workflows and user outcomes

Respond with a JSON array of user requirements in this format:
[
  {{
    "description": "Clear user-focused requirement description",
    "rationale": "Why this requirement is important for users",
    "acceptance_criteria": ["Specific criteria to verify the requirement is met"],
    "priority": "high|medium|low",
    "related_features": ["FEAT_0001", "FEAT_0002"]
  }}
]

Generate 3-8 user requirements that cover the provided features."""
        
        # Software requirements generation prompts
        self.sr_system_prompt = """You are an expert software engineer specializing in medical device software. Your task is to analyze user requirements and generate detailed software requirements that specify how the system will implement the user needs.

Software requirements should be:
- Technical and implementation-focused
- Specific and measurable
- Derived from user requirements
- Include functional and non-functional aspects
- Suitable for software developers to implement

Respond in JSON format with an array of software requirements."""
        
        self.sr_prompt_template = """Analyze the following user requirement and generate software requirements that will implement it:

User Requirement:
ID: {ur_id}
Description: {ur_description}
Rationale: {ur_rationale}
Acceptance Criteria: {ur_criteria}

Related Features:
{related_features_text}

Context: This is part of a medical device software project. Generate software requirements that:
- Specify technical implementation details
- Include functional and non-functional requirements
- Are specific enough for developers to implement
- Include error handling and validation requirements
- Consider medical device safety and regulatory requirements

Respond with a JSON array of software requirements in this format:
[
  {{
    "description": "Specific technical requirement description",
    "type": "functional|performance|security|safety|interface|data",
    "acceptance_criteria": ["Technical criteria to verify implementation"],
    "priority": "high|medium|low",
    "implementation_notes": "Additional technical guidance"
  }}
]

Generate 2-5 software requirements for this user requirement."""
    
    def generate_requirements_from_features(
        self, 
        features: List[Feature],
        project_description: str = ""
    ) -> RequirementsGenerationResult:
        """
        Generate user and software requirements from extracted features.
        
        Args:
            features: List of extracted features
            project_description: Description of the project context
            
        Returns:
            RequirementsGenerationResult with generated requirements and metadata
        """
        start_time = datetime.now()
        
        # Step 1: Generate user requirements from features
        user_requirements = self._generate_user_requirements(features, project_description)
        
        # Step 2: Generate software requirements from user requirements
        software_requirements = self._generate_software_requirements(user_requirements, features)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return RequirementsGenerationResult(
            user_requirements=user_requirements,
            software_requirements=software_requirements,
            processing_time=processing_time,
            metadata={
                'total_features_analyzed': len(features),
                'user_requirements_generated': len(user_requirements),
                'software_requirements_generated': len(software_requirements),
                'generation_method': 'llm_based',
                'llm_backend': self.llm_backend.__class__.__name__,
                'project_description_provided': bool(project_description)
            }
        )
    
    def _generate_user_requirements(
        self, 
        features: List[Feature], 
        project_description: str
    ) -> List[Requirement]:
        """Generate user requirements from features."""
        
        # Group features by category for better requirement generation
        feature_groups = self._group_features_by_category(features)
        user_requirements = []
        
        for category, category_features in feature_groups.items():
            if not category_features:
                continue
                
            # Prepare features text for prompt
            features_text = self._format_features_for_prompt(category_features)
            
            prompt = self.ur_prompt_template.format(
                features_text=features_text
            )
            
            try:
                self._generation_stats['total_requests'] += 1
                
                # Generate user requirements using LLM with validation
                response_text, validation_result = self._generate_with_validation(
                    prompt=prompt,
                    system_prompt=self.ur_system_prompt,
                    operation="user_requirements_generation",
                    temperature=0.7,
                    max_tokens=4000
                )
                
                if response_text and validation_result and validation_result.is_valid:
                    self._generation_stats['successful_requests'] += 1
                    
                    # Parse JSON response
                    ur_data_list = LLMResponseParser.parse_json_response(response_text)
                    
                    # Validate parsed requirements data
                    if self._validate_requirements_data(ur_data_list, 'user'):
                        # Convert to Requirement objects
                        for ur_data in ur_data_list:
                            ur = self._create_user_requirement_from_data(ur_data, category_features)
                            if ur:
                                user_requirements.append(ur)
                        
                        logger.info(f"Generated {len(ur_data_list)} user requirements for category {category}")
                    else:
                        logger.warning(f"Generated requirements data failed validation for category {category}")
                        raise ValueError("Requirements data validation failed")
                else:
                    # Log validation issues
                    if validation_result:
                        logger.warning(f"User requirements generation validation failed: {[e.error_message for e in validation_result.errors]}")
                        self._generation_stats['validation_failures'] += 1
                    
                    raise LLMError("Requirements generation validation failed")
                        
            except (LLMError, Exception) as e:
                self._generation_stats['failed_requests'] += 1
                self._generation_stats['fallback_generations'] += 1
                
                logger.warning(f"User requirements generation failed for category {category}: {e}")
                
                # Fallback to heuristic generation for this category
                fallback_ur = self._generate_fallback_user_requirement(category, category_features)
                if fallback_ur:
                    user_requirements.append(fallback_ur)
                    logger.info(f"Generated fallback user requirement for category {category}")
        
        return user_requirements
    
    def _generate_software_requirements(
        self, 
        user_requirements: List[Requirement], 
        features: List[Feature]
    ) -> List[Requirement]:
        """Generate software requirements from user requirements."""
        
        software_requirements = []
        feature_lookup = {f.id: f for f in features}
        
        for ur in user_requirements:
            # Get related features for this user requirement
            related_features = []
            for feature_id in ur.derived_from:
                if feature_id in feature_lookup:
                    related_features.append(feature_lookup[feature_id])
            
            if not related_features:
                continue
            
            # Format related features for prompt
            related_features_text = self._format_features_for_prompt(related_features)
            
            prompt = self.sr_prompt_template.format(
                ur_id=ur.id,
                ur_description=ur.text,
                ur_rationale=ur.metadata.get('rationale', 'Not specified'),
                ur_criteria='; '.join(ur.acceptance_criteria),
                related_features_text=related_features_text
            )
            
            try:
                self._generation_stats['total_requests'] += 1
                
                # Generate software requirements using LLM with validation
                response_text, validation_result = self._generate_with_validation(
                    prompt=prompt,
                    system_prompt=self.sr_system_prompt,
                    operation="software_requirements_generation",
                    temperature=0.6,
                    max_tokens=4000
                )
                
                if response_text and validation_result and validation_result.is_valid:
                    self._generation_stats['successful_requests'] += 1
                    
                    # Parse JSON response
                    sr_data_list = LLMResponseParser.parse_json_response(response_text)
                    
                    # Validate parsed requirements data
                    if self._validate_requirements_data(sr_data_list, 'software'):
                        # Convert to Requirement objects
                        for sr_data in sr_data_list:
                            sr = self._create_software_requirement_from_data(sr_data, ur, related_features)
                            if sr:
                                software_requirements.append(sr)
                        
                        logger.info(f"Generated {len(sr_data_list)} software requirements for UR {ur.id}")
                    else:
                        logger.warning(f"Generated software requirements data failed validation for UR {ur.id}")
                        raise ValueError("Software requirements data validation failed")
                else:
                    # Log validation issues
                    if validation_result:
                        logger.warning(f"Software requirements generation validation failed: {[e.error_message for e in validation_result.errors]}")
                        self._generation_stats['validation_failures'] += 1
                    
                    raise LLMError("Software requirements generation validation failed")
                        
            except (LLMError, Exception) as e:
                self._generation_stats['failed_requests'] += 1
                self._generation_stats['fallback_generations'] += 1
                
                logger.warning(f"Software requirements generation failed for UR {ur.id}: {e}")
                
                # Fallback to heuristic generation
                fallback_srs = self._generate_fallback_software_requirements(ur, related_features)
                software_requirements.extend(fallback_srs)
                logger.info(f"Generated {len(fallback_srs)} fallback software requirements for UR {ur.id}")
        
        return software_requirements
    
    def _group_features_by_category(self, features: List[Feature]) -> Dict[str, List[Feature]]:
        """Group features by their category."""
        groups = {}
        
        for feature in features:
            category = feature.category.name if hasattr(feature.category, 'name') else str(feature.category)
            if category not in groups:
                groups[category] = []
            groups[category].append(feature)
        
        return groups
    
    def _format_features_for_prompt(self, features: List[Feature]) -> str:
        """Format features for inclusion in prompts."""
        formatted = []
        
        for feature in features:
            feature_text = f"- {feature.id}: {feature.description}"
            if feature.evidence:
                # Add code context
                code_ref = feature.evidence[0]
                feature_text += f" (from {code_ref.file_path}:{code_ref.start_line})"
            formatted.append(feature_text)
        
        return '\n'.join(formatted)
    
    def _create_user_requirement_from_data(
        self, 
        ur_data: Dict[str, Any], 
        related_features: List[Feature]
    ) -> Optional[Requirement]:
        """Create a user requirement from parsed LLM data."""
        
        try:
            if not LLMResponseParser.validate_required_fields(ur_data, ['description']):
                return None
            
            self.ur_counter += 1
            ur_id = f"UR_{self.ur_counter:04d}"
            
            description = ur_data['description'].strip()
            rationale = ur_data.get('rationale', 'Generated from code analysis')
            acceptance_criteria = ur_data.get('acceptance_criteria', [])
            priority = ur_data.get('priority', 'medium')
            
            # Ensure acceptance_criteria is a list
            if isinstance(acceptance_criteria, str):
                acceptance_criteria = [acceptance_criteria]
            elif not isinstance(acceptance_criteria, list):
                acceptance_criteria = []
            
            # Get related feature IDs
            related_feature_ids = ur_data.get('related_features', [])
            if not related_feature_ids:
                related_feature_ids = [f.id for f in related_features]
            
            return Requirement(
                id=ur_id,
                text=description,
                type=RequirementType.USER,
                acceptance_criteria=acceptance_criteria,
                derived_from=related_feature_ids,
                metadata={
                    'rationale': rationale,
                    'priority': priority,
                    'generation_method': 'llm',
                    'related_features_count': len(related_features),
                    'category': related_features[0].category.name if related_features else 'general'
                }
            )
            
        except (ValueError, KeyError, TypeError):
            return None
    
    def _create_software_requirement_from_data(
        self, 
        sr_data: Dict[str, Any], 
        user_requirement: Requirement,
        related_features: List[Feature]
    ) -> Optional[Requirement]:
        """Create a software requirement from parsed LLM data."""
        
        try:
            if not LLMResponseParser.validate_required_fields(sr_data, ['description']):
                return None
            
            self.sr_counter += 1
            sr_id = f"SR_{self.sr_counter:04d}"
            
            description = sr_data['description'].strip()
            req_type = sr_data.get('type', 'functional')
            acceptance_criteria = sr_data.get('acceptance_criteria', [])
            priority = sr_data.get('priority', user_requirement.priority)
            implementation_notes = sr_data.get('implementation_notes', '')
            
            # Ensure acceptance_criteria is a list
            if isinstance(acceptance_criteria, str):
                acceptance_criteria = [acceptance_criteria]
            elif not isinstance(acceptance_criteria, list):
                acceptance_criteria = []
            
            return Requirement(
                id=sr_id,
                text=description,
                type=RequirementType.SOFTWARE,
                acceptance_criteria=acceptance_criteria,
                derived_from=[user_requirement.id],
                metadata={
                    'requirement_type': req_type,
                    'priority': priority,
                    'implementation_notes': implementation_notes,
                    'generation_method': 'llm',
                    'parent_user_requirement': user_requirement.id,
                    'related_features': [f.id for f in related_features]
                }
            )
            
        except (ValueError, KeyError, TypeError):
            return None
    
    def _generate_fallback_user_requirement(
        self, 
        category: str, 
        features: List[Feature]
    ) -> Optional[Requirement]:
        """Generate fallback user requirement using heuristics."""
        
        if not features:
            return None
        
        self.ur_counter += 1
        ur_id = f"UR_{self.ur_counter:04d}"
        
        # Category-based descriptions
        category_descriptions = {
            'DATA_PROCESSING': 'The system shall provide reliable data processing capabilities',
            'USER_INTERFACE': 'The system shall provide an intuitive user interface',
            'COMMUNICATION': 'The system shall provide reliable communication features',
            'SAFETY': 'The system shall implement safety mechanisms',
            'DEVICE_CONTROL': 'The system shall provide device control functionality',
            'ALGORITHM': 'The system shall implement required algorithms',
            'STORAGE': 'The system shall provide data storage capabilities',
            'VALIDATION': 'The system shall provide data validation features',
            'MONITORING': 'The system shall provide monitoring capabilities',
            'CONFIGURATION': 'The system shall provide configuration options'
        }
        
        description = category_descriptions.get(category, f'The system shall provide {category.lower()} functionality')
        
        return Requirement(
            id=ur_id,
            text=description,
            type=RequirementType.USER,
            acceptance_criteria=[
                f'System shall implement all {category.lower()} features reliably',
                f'System shall handle {category.lower()} errors appropriately',
                f'System shall meet performance requirements for {category.lower()}'
            ],
            derived_from=[f.id for f in features],
            metadata={
                'rationale': f'Generated from {len(features)} {category.lower()} features',
                'priority': 'medium',
                'generation_method': 'heuristic',
                'category': category
            }
        )
    
    def _generate_fallback_software_requirements(
        self, 
        user_requirement: Requirement, 
        features: List[Feature]
    ) -> List[Requirement]:
        """Generate fallback software requirements using heuristics."""
        
        software_requirements = []
        
        # Generate 2-3 software requirements per user requirement
        for i, feature in enumerate(features[:3]):  # Limit to first 3 features
            self.sr_counter += 1
            sr_id = f"SR_{self.sr_counter:04d}"
            
            description = f"Software shall implement {feature.description}"
            
            sr = Requirement(
                id=sr_id,
                text=description,
                type=RequirementType.SOFTWARE,
                acceptance_criteria=[
                    f'Implementation shall match feature specification',
                    f'Implementation shall include error handling',
                    f'Implementation shall be testable and verifiable'
                ],
                derived_from=[user_requirement.id],
                metadata={
                    'requirement_type': 'functional',
                    'priority': user_requirement.metadata.get('priority', 'medium'),
                    'generation_method': 'heuristic',
                    'parent_user_requirement': user_requirement.id,
                    'related_feature': feature.id
                }
            )
            
            software_requirements.append(sr)
        
        return software_requirements
    
    def get_statistics(
        self, 
        user_requirements: List[Requirement], 
        software_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """Get statistics about generated requirements."""
        
        ur_priorities = {}
        sr_priorities = {}
        sr_types = {}
        
        for ur in user_requirements:
            priority = ur.metadata.get('priority', 'medium')
            ur_priorities[priority] = ur_priorities.get(priority, 0) + 1
        
        for sr in software_requirements:
            priority = sr.metadata.get('priority', 'medium')
            sr_priorities[priority] = sr_priorities.get(priority, 0) + 1
            
            req_type = sr.metadata.get('requirement_type', 'functional')
            sr_types[req_type] = sr_types.get(req_type, 0) + 1
        
        return {
            'user_requirements': {
                'total': len(user_requirements),
                'priorities': ur_priorities,
                'avg_acceptance_criteria': sum(len(ur.acceptance_criteria) for ur in user_requirements) / max(len(user_requirements), 1)
            },
            'software_requirements': {
                'total': len(software_requirements),
                'priorities': sr_priorities,
                'types': sr_types,
                'avg_acceptance_criteria': sum(len(sr.acceptance_criteria) for sr in software_requirements) / max(len(software_requirements), 1)
            },
            'traceability': {
                'ur_to_sr_ratio': len(software_requirements) / max(len(user_requirements), 1),
                'requirements_with_traceability': len([sr for sr in software_requirements if sr.derived_from])
            }
        }
    
    def _generate_with_validation(
        self,
        prompt: str,
        system_prompt: str,
        operation: str,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        max_retries: int = 2
    ) -> tuple[Optional[str], Optional[ValidationResult]]:
        """
        Generate text with comprehensive validation and retry logic.
        
        Args:
            prompt: The generation prompt
            system_prompt: System prompt for context
            operation: Operation type for validation
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retry attempts
            
        Returns:
            Tuple of (generated_text, validation_result)
        """
        last_validation_result = None
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Requirements generation attempt {attempt + 1}/{max_retries + 1} for {operation}")
                
                # Generate using LLM backend
                response_text = self.llm_backend.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Validate the response content
                validation_result = self._validate_requirements_response(response_text, operation)
                
                if validation_result.is_valid:
                    logger.debug(f"Requirements generation successful for {operation} on attempt {attempt + 1}")
                    return response_text, validation_result
                
                # Log validation issues
                logger.warning(f"Requirements generation validation failed on attempt {attempt + 1}: {[e.error_message for e in validation_result.errors]}")
                last_validation_result = validation_result
                
                # Check if we should retry
                if not validation_result.should_retry() or attempt >= max_retries:
                    break
                
                self._generation_stats['retry_attempts'] += 1
                
                # Adjust parameters for retry
                if attempt == 0:
                    # First retry: increase temperature slightly for more creativity
                    temperature = min(temperature + 0.1, 1.0)
                elif attempt == 1:
                    # Second retry: increase max_tokens in case response was truncated
                    max_tokens = min(max_tokens + 500, 4000)
                
            except LLMError as e:
                logger.error(f"LLM error during requirements generation attempt {attempt + 1}: {e}")
                if not e.recoverable or attempt >= max_retries:
                    break
                self._generation_stats['retry_attempts'] += 1
            except Exception as e:
                logger.error(f"Unexpected error during requirements generation attempt {attempt + 1}: {e}")
                break
        
        return None, last_validation_result
    
    def _validate_requirements_response(self, response_text: str, operation: str) -> ValidationResult:
        """
        Validate requirements generation response content.
        
        Args:
            response_text: The generated response text
            operation: Operation type for validation
            
        Returns:
            ValidationResult with validation details
        """
        from ..llm.api_response_validator import ValidationResult, ValidationStatus, ErrorDetails, ErrorSeverity, RecoveryAction
        
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            metadata={'operation': operation, 'response_length': len(response_text)}
        )
        
        try:
            # Basic content validation
            if not response_text or not response_text.strip():
                result.add_error(ErrorDetails(
                    error_code="EMPTY_RESPONSE",
                    error_message="Generated response is empty",
                    severity=ErrorSeverity.HIGH,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                ))
                return result
            
            # Check if response looks like JSON
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            if not (response_text.startswith('[') or response_text.startswith('{')):
                result.add_warning("Response does not appear to be JSON format")
                result.confidence *= 0.8
            
            # Try to parse as JSON
            try:
                import json
                parsed_data = json.loads(response_text)
                
                # Validate structure based on operation
                if operation == "user_requirements_generation":
                    if not self._validate_user_requirements_structure(parsed_data, result):
                        result.confidence *= 0.7
                elif operation == "software_requirements_generation":
                    if not self._validate_software_requirements_structure(parsed_data, result):
                        result.confidence *= 0.7
                
                result.extracted_data = {'parsed_requirements': parsed_data}
                
            except json.JSONDecodeError as e:
                result.add_error(ErrorDetails(
                    error_code="INVALID_JSON",
                    error_message=f"Response is not valid JSON: {str(e)}",
                    error_context={'response_preview': response_text[:200]},
                    severity=ErrorSeverity.HIGH,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                ))
            
            # Check for common error patterns
            error_patterns = [
                'i cannot', 'i am unable', 'sorry', 'apologize',
                'error occurred', 'failed to', 'unable to process'
            ]
            
            response_lower = response_text.lower()
            for pattern in error_patterns:
                if pattern in response_lower:
                    result.add_warning(f"Response may contain error indication: '{pattern}'")
                    result.confidence *= 0.9
                    break
            
        except Exception as e:
            result.add_error(ErrorDetails(
                error_code="VALIDATION_EXCEPTION",
                error_message=f"Validation failed with exception: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
        
        return result
    
    def _validate_user_requirements_structure(self, data: Any, result: ValidationResult) -> bool:
        """Validate user requirements data structure."""
        if not isinstance(data, list):
            result.add_error(ErrorDetails(
                error_code="INVALID_STRUCTURE",
                error_message="User requirements should be a list",
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return False
        
        if len(data) == 0:
            result.add_error(ErrorDetails(
                error_code="EMPTY_REQUIREMENTS",
                error_message="No user requirements generated",
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return False
        
        if len(data) > 10:
            result.add_warning(f"Generated {len(data)} user requirements, which is more than expected (max 10)")
        
        # Validate each requirement
        for i, req in enumerate(data):
            if not isinstance(req, dict):
                result.add_warning(f"User requirement {i+1} is not a dictionary")
                continue
            
            if 'description' not in req:
                result.add_warning(f"User requirement {i+1} missing description")
            elif len(req['description'].strip()) < 10:
                result.add_warning(f"User requirement {i+1} description is too short")
            
            if 'acceptance_criteria' not in req:
                result.add_warning(f"User requirement {i+1} missing acceptance criteria")
            elif not isinstance(req['acceptance_criteria'], list) or len(req['acceptance_criteria']) == 0:
                result.add_warning(f"User requirement {i+1} has invalid acceptance criteria")
        
        return True
    
    def _validate_software_requirements_structure(self, data: Any, result: ValidationResult) -> bool:
        """Validate software requirements data structure."""
        if not isinstance(data, list):
            result.add_error(ErrorDetails(
                error_code="INVALID_STRUCTURE",
                error_message="Software requirements should be a list",
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return False
        
        if len(data) == 0:
            result.add_error(ErrorDetails(
                error_code="EMPTY_REQUIREMENTS",
                error_message="No software requirements generated",
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return False
        
        if len(data) > 8:
            result.add_warning(f"Generated {len(data)} software requirements, which is more than expected (max 8)")
        
        # Validate each requirement
        for i, req in enumerate(data):
            if not isinstance(req, dict):
                result.add_warning(f"Software requirement {i+1} is not a dictionary")
                continue
            
            if 'description' not in req:
                result.add_warning(f"Software requirement {i+1} missing description")
            elif len(req['description'].strip()) < 10:
                result.add_warning(f"Software requirement {i+1} description is too short")
            
            if 'acceptance_criteria' not in req:
                result.add_warning(f"Software requirement {i+1} missing acceptance criteria")
            elif not isinstance(req['acceptance_criteria'], list) or len(req['acceptance_criteria']) == 0:
                result.add_warning(f"Software requirement {i+1} has invalid acceptance criteria")
            
            # Validate requirement type if present
            if 'type' in req:
                valid_types = ['functional', 'performance', 'security', 'safety', 'interface', 'data']
                if req['type'] not in valid_types:
                    result.add_warning(f"Software requirement {i+1} has invalid type: {req['type']}")
        
        return True
    
    def _validate_requirements_data(self, requirements_data: List[Dict[str, Any]], req_type: str) -> bool:
        """
        Validate parsed requirements data for completeness and correctness.
        
        Args:
            requirements_data: List of requirement dictionaries
            req_type: Type of requirements ('user' or 'software')
            
        Returns:
            True if data is valid, False otherwise
        """
        if not requirements_data:
            logger.warning(f"No {req_type} requirements data to validate")
            return False
        
        valid_count = 0
        
        for i, req_data in enumerate(requirements_data):
            if not isinstance(req_data, dict):
                logger.warning(f"{req_type.title()} requirement {i+1} is not a dictionary")
                continue
            
            # Check required fields
            if 'description' not in req_data or not req_data['description'].strip():
                logger.warning(f"{req_type.title()} requirement {i+1} missing or empty description")
                continue
            
            if 'acceptance_criteria' not in req_data:
                logger.warning(f"{req_type.title()} requirement {i+1} missing acceptance criteria")
                continue
            
            if not isinstance(req_data['acceptance_criteria'], list) or len(req_data['acceptance_criteria']) == 0:
                logger.warning(f"{req_type.title()} requirement {i+1} has invalid acceptance criteria")
                continue
            
            # Additional validation for software requirements
            if req_type == 'software' and 'type' in req_data:
                valid_types = ['functional', 'performance', 'security', 'safety', 'interface', 'data']
                if req_data['type'] not in valid_types:
                    logger.warning(f"Software requirement {i+1} has invalid type: {req_data['type']}")
            
            valid_count += 1
        
        # At least 50% of requirements should be valid
        validity_ratio = valid_count / len(requirements_data)
        if validity_ratio < 0.5:
            logger.warning(f"Only {validity_ratio:.1%} of {req_type} requirements are valid (minimum 50% required)")
            return False
        
        logger.debug(f"Validated {valid_count}/{len(requirements_data)} {req_type} requirements ({validity_ratio:.1%})")
        return True
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about requirements generation performance.
        
        Returns:
            Dictionary with generation statistics
        """
        total_requests = self._generation_stats['total_requests']
        success_rate = (self._generation_stats['successful_requests'] / max(total_requests, 1)) * 100
        
        return {
            'total_requests': total_requests,
            'successful_requests': self._generation_stats['successful_requests'],
            'failed_requests': self._generation_stats['failed_requests'],
            'validation_failures': self._generation_stats['validation_failures'],
            'fallback_generations': self._generation_stats['fallback_generations'],
            'retry_attempts': self._generation_stats['retry_attempts'],
            'success_rate': round(success_rate, 2),
            'fallback_rate': round((self._generation_stats['fallback_generations'] / max(total_requests, 1)) * 100, 2)
        }
    
    def reset_generation_statistics(self) -> None:
        """Reset generation statistics."""
        self._generation_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'validation_failures': 0,
            'fallback_generations': 0,
            'retry_attempts': 0
        }
        logger.info("Requirements generation statistics reset")