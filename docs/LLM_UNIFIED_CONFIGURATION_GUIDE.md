# LLM Unified Configuration System

## Problem Statement

The codebase previously suffered from scattered LLM parameters with inconsistent values and maintenance difficulties:

- **Scattered Parameters**: Temperature and max_tokens hardcoded throughout services
- **Inconsistent Values**: Same operations using different parameters in different places
- **Maintenance Nightmare**: Changing parameters required hunting through multiple files
- **No Rationale**: No clear reasoning for why different operations used different values
- **JSON Response Chaos**: Different modules handled LLM responses inconsistently

## Solution Overview

The unified configuration system addresses these issues through:

1. **Centralized Operation Configs**: All LLM parameters defined in one place
2. **Operation-Specific Settings**: Each operation type has optimized parameters
3. **Unified Response Handling**: Consistent JSON parsing across all modules
4. **Easy Maintenance**: Change parameters in one config file
5. **Clear Documentation**: Each operation explains why it uses specific parameters

## Architecture

### Core Components

```
medical_analyzer/llm/
├── operation_configs.py     # Centralized parameter management
├── response_handler.py      # Unified JSON response parsing
└── config/
    └── llm_operation_configs.json  # Configuration file
```

### Operation Configuration System

#### 1. Operation Configs (`operation_configs.py`)

```python
from medical_analyzer.llm.operation_configs import get_operation_params

# Old way (scattered, inconsistent)
response = llm_backend.generate(
    prompt=prompt,
    temperature=0.7,  # Why 0.7? Who knows!
    max_tokens=4000,  # Is this enough? Too much?
    system_prompt=system_prompt
)

# New way (centralized, documented)
params = get_operation_params("user_requirements_generation")
response = llm_backend.generate(
    prompt=prompt,
    system_prompt=system_prompt,
    **params  # temperature=0.7, max_tokens=4000
)
```

#### 2. Unified Response Handler (`response_handler.py`)

```python
from medical_analyzer.llm.response_handler import get_response_handler, ResponseFormat

# Old way (inconsistent parsing)
try:
    data = json.loads(response)
    # Hope it's valid JSON...
    # Different error handling everywhere
except:
    # Various fallback strategies

# New way (unified, robust)
handler = get_response_handler()
result = handler.parse_response(response, ResponseFormat.JSON_OBJECT)

if result.success:
    data = result.data  # Guaranteed to be valid
else:
    logger.error(f"Parsing failed: {result.error}")
```

## Operation Types and Rationale

### High Creativity Operations
- **User Requirements Generation** (temp=0.7): Needs creativity for comprehensive coverage
- **Software Requirements Generation** (temp=0.6): Moderate creativity with technical precision

### Precision Operations  
- **SOUP Classification** (temp=0.1): Consistency critical for regulatory compliance
- **Test Case Generation** (temp=0.1): Precision needed for reliable test procedures
- **Hazard Identification** (temp=0.1): Systematic analysis, no creativity needed

### Balanced Operations
- **Feature Extraction** (temp=0.5): Moderate creativity for comprehensive analysis
- **Risk Assessment** (temp=0.2): Low creativity, systematic evaluation

### Diagnostic Operations
- **LLM Diagnostics** (temp=0.1, tokens=50): Minimal output, maximum consistency

## Configuration File Structure

```json
{
  "operation_name": {
    "temperature": 0.7,
    "max_tokens": 4000,
    "operation_name": "operation_name",
    "description": "Why these parameters make sense"
  }
}
```

## Migration Guide

### Step 1: Add Imports

```python
# Add to existing imports
from ..llm.operation_configs import get_operation_params
from ..llm.response_handler import get_response_handler, ResponseFormat
```

### Step 2: Replace Hardcoded Parameters

```python
# Before
response = self.llm_backend.generate(
    prompt=prompt,
    system_prompt=self.system_prompt,
    temperature=0.7,
    max_tokens=4000
)

# After  
params = get_operation_params("user_requirements_generation")
response = self.llm_backend.generate(
    prompt=prompt,
    system_prompt=self.system_prompt,
    **params
)
```

### Step 3: Unify Response Parsing

```python
# Before
try:
    data = json.loads(response)
    # Custom validation logic
except json.JSONDecodeError:
    # Custom error handling

# After
handler = get_response_handler()
result = handler.parse_requirements_response(response)

if result.success:
    data = result.data
else:
    logger.error(f"Parsing failed: {result.error}")
```

## Benefits

### 1. Maintainability
- **Single Source of Truth**: All parameters in one config file
- **Easy Updates**: Change parameters without code changes
- **Clear Documentation**: Each operation explains its parameter choices

### 2. Consistency
- **Standardized Values**: Same operations use same parameters everywhere
- **Unified Error Handling**: Consistent response parsing across modules
- **Predictable Behavior**: No surprises from scattered configurations

### 3. Performance
- **Optimized Parameters**: Each operation uses parameters tuned for its purpose
- **Efficient Parsing**: Unified response handler with optimized error handling
- **Reduced Redundancy**: No duplicate parsing logic

### 4. Developer Experience
- **Clear Intent**: Operation names make purpose obvious
- **Easy Configuration**: JSON file is human-readable and editable
- **Migration Tools**: Scripts help identify and fix scattered parameters

## Usage Examples

### Requirements Generation
```python
# Automatically uses temperature=0.7, max_tokens=4000
params = get_operation_params("user_requirements_generation")
response = llm_backend.generate(prompt=prompt, **params)

# Parse with validation
result = handler.parse_requirements_response(response)
```

### SOUP Classification
```python
# Automatically uses temperature=0.1, max_tokens=1500  
params = get_operation_params("soup_classification")
response = llm_backend.generate(prompt=prompt, **params)

# Parse with schema validation
result = handler.parse_soup_classification_response(response)
```

### Test Case Generation
```python
# Automatically uses temperature=0.1, max_tokens=1000
params = get_operation_params("test_case_generation") 
response = llm_backend.generate(prompt=prompt, **params)

# Parse as JSON array
result = handler.parse_json_list(response)
```

## Configuration Management

### Runtime Updates
```python
configs = get_operation_configs()

# Update specific operation
configs.update_operation_temperature("soup_classification", 0.05)

# Save changes
configs.save_to_file("config/llm_operation_configs.json")
```

### Custom Operations
```python
# Add new operation
new_config = OperationConfig(
    temperature=0.3,
    max_tokens=1500,
    operation_name="custom_analysis",
    description="Custom analysis with balanced parameters"
)

configs.set_config("custom_analysis", new_config)
```

## Migration Tools

### Parameter Scanner
```bash
python scripts/migrate_to_unified_llm_config.py
```

This tool:
- Scans codebase for scattered parameters
- Suggests appropriate operation names
- Provides specific migration instructions
- Validates configuration consistency

## Testing

### Configuration Validation
```python
# Test configuration loading
configs = get_operation_configs()
assert configs.get_config("user_requirements_generation").temperature == 0.7

# Test parameter retrieval
params = get_operation_params("soup_classification")
assert params["temperature"] == 0.1
assert params["max_tokens"] == 1500
```

### Response Handler Testing
```python
# Test JSON parsing
handler = get_response_handler()
result = handler.parse_response('{"test": "data"}')
assert result.success
assert result.data["test"] == "data"

# Test error handling
result = handler.parse_response('invalid json')
assert not result.success
assert "JSON decode error" in result.error
```

## Best Practices

### 1. Operation Naming
- Use descriptive, consistent names
- Follow pattern: `{domain}_{action}` (e.g., `soup_classification`)
- Document the purpose in the description field

### 2. Parameter Selection
- **High creativity** (0.6-0.8): Requirements, feature extraction
- **Medium creativity** (0.3-0.5): Analysis, assessment  
- **Low creativity** (0.1-0.2): Classification, testing
- **Minimal creativity** (0.0-0.1): Diagnostics, validation

### 3. Token Limits
- **Short responses** (50-500): Classifications, diagnostics
- **Medium responses** (1000-2000): Test cases, hazards
- **Long responses** (3000-4000): Requirements, features

### 4. Response Handling
- Always use the unified response handler
- Implement operation-specific validation when needed
- Log parsing errors with context
- Provide fallback strategies for critical operations

## Conclusion

The unified LLM configuration system eliminates the maintenance nightmare of scattered parameters while providing:

- **Centralized Management**: One place to configure all operations
- **Consistent Behavior**: Same operations behave identically everywhere  
- **Clear Documentation**: Each parameter choice is explained and justified
- **Easy Maintenance**: Update configurations without touching code
- **Robust Parsing**: Unified error handling and validation

This system transforms LLM parameter management from a source of technical debt into a well-organized, maintainable component of the architecture.