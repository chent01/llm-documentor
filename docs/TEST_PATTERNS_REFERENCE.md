# Test Patterns Quick Reference

## Overview

This document provides a quick reference for common test patterns, solutions to frequent issues, and best practices for the medical software analyzer project.

## Common Test Patterns

### 1. Mock Configuration Patterns

#### LLM Backend Mocks
```python
# ✅ Correct backend mock configuration
from tests.test_utils import MockConfigurationManager

# OpenAI backend mock
mock_openai = MockConfigurationManager.create_llm_backend_mock('openai')
mock_openai.generate_response.return_value = "Expected response"

# Anthropic backend mock
mock_anthropic = MockConfigurationManager.create_llm_backend_mock('anthropic')
mock_anthropic.generate_response.return_value = "Expected response"
```

#### Service Mocks
```python
# ✅ Service mock with proper method availability
mock_service = MockConfigurationManager.create_service_mock(SOUPService)
mock_service.add_component.return_value = "generated-id"
mock_service.validate_component.return_value = True
```

#### Configuration Mocks
```python
# ✅ Configuration mock with consistent types
mock_config = Mock()
mock_config.get_backend_type.return_value = 'openai'  # String, not Mock
mock_config.validate.return_value = True  # Boolean, not Mock
mock_config.save.return_value = None
```

### 2. UI Testing Patterns

#### Widget Visibility Testing
```python
from tests.test_utils import UITestHelper

# ✅ Safe widget visibility check
def test_error_display(widget):
    # Trigger error condition
    widget.show_error("Test error")
    UITestHelper.process_events()
    
    # Verify error display
    UITestHelper.verify_widget_visibility(widget.error_label, True)
```

#### Signal Emission Testing
```python
# ✅ Reliable signal emission testing
def test_signal_emission(widget):
    def trigger_action():
        widget.button.click()
    
    count = UITestHelper.count_signal_emissions(
        widget.signal_name, 
        trigger_action
    )
    assert count == 1
```

#### Table Widget Testing
```python
from PyQt6.QtWidgets import QTableWidgetItem

# ✅ Table widget interaction testing
def test_table_interaction(widget):
    # Add item to table
    item = QTableWidgetItem("Test Item")
    widget.table.setItem(0, 0, item)
    
    # Verify item text
    UITestHelper.verify_table_item_text(widget.table, 0, 0, "Test Item")
```

### 3. Error Handling Test Patterns

#### Exception Testing
```python
# ✅ Proper exception testing
def test_file_not_found_error():
    parser = CodeParser()
    
    with pytest.raises(FileNotFoundError):
        parser.parse_file("nonexistent_file.py")
```

#### Error State Testing
```python
# ✅ Error state validation
def test_error_state_handling(service):
    # Create error condition
    with patch('os.path.exists', return_value=False):
        result = service.process_file("test.py")
    
    # Verify error handling
    assert result.has_error
    assert "File not found" in result.error_message
```

### 4. Data Validation Patterns

#### Model Validation Testing
```python
# ✅ Comprehensive model validation
def test_component_validation():
    # Valid component
    valid_component = SOUPComponent(
        id="comp-001",
        name="Test Component",
        version="1.0.0",
        usage_reason="Testing purposes",
        safety_justification="Test justification",
        supplier="Test Supplier",
        license="MIT",
        website="https://example.com",
        description="Test description",
        criticality_level="Low"
    )
    
    assert valid_component.validate()
    
    # Invalid component (missing required field)
    with pytest.raises(ValidationError):
        SOUPComponent(
            id="",  # Invalid empty ID
            name="Test Component"
        )
```

#### Service Validation Testing
```python
# ✅ Service validation with proper test data
def test_service_validation(soup_service):
    component = create_test_component()  # Use factory function
    
    result = soup_service.add_component(component)
    
    assert result is not None
    assert result.startswith("comp-")  # Verify ID format
```

### 5. Integration Test Patterns

#### Database Integration
```python
# ✅ Database integration testing
@pytest.fixture
def temp_database():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)

def test_database_integration(temp_database):
    db_manager = DatabaseManager(temp_database)
    service = SOUPService(db_manager)
    
    # Test database operations
    component = create_test_component()
    component_id = service.add_component(component)
    
    retrieved = service.get_component(component_id)
    assert retrieved.name == component.name
```

#### Service Integration
```python
# ✅ Service integration testing
def test_service_integration():
    # Setup services
    parser_service = ParserService()
    analysis_service = AnalysisService()
    
    # Test integration
    parsed_data = parser_service.parse_file("test_file.py")
    analysis_result = analysis_service.analyze(parsed_data)
    
    assert analysis_result.is_valid
    assert len(analysis_result.findings) > 0
```

## Common Solutions

### 1. Import Issues

#### Missing PyQt6 Imports
```python
# ❌ Common mistake
def test_table_widget():
    item = QTableWidgetItem("test")  # NameError

# ✅ Solution
from PyQt6.QtWidgets import QTableWidgetItem

def test_table_widget():
    item = QTableWidgetItem("test")
```

#### Circular Import Issues
```python
# ❌ Problematic import
from medical_analyzer.services import all_services

# ✅ Solution - specific imports
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.services.parser_service import ParserService
```

### 2. Mock Configuration Issues

#### Backend Type Mismatches
```python
# ❌ Wrong mock configuration
mock_config = Mock()
mock_config.get_backend_type.return_value = Mock()  # Returns Mock object

# ✅ Correct mock configuration
mock_config = Mock()
mock_config.get_backend_type.return_value = 'openai'  # Returns string
```

#### Inconsistent Mock Behavior
```python
# ❌ Inconsistent mock setup
mock_service = Mock()
mock_service.method1.return_value = "value1"
# mock_service.method2 not configured - returns Mock

# ✅ Consistent mock setup
mock_service = Mock()
mock_service.method1.return_value = "value1"
mock_service.method2.return_value = "value2"
mock_service.method3.return_value = None  # Explicit None
```

### 3. UI Component Issues

#### Widget Attribute Errors
```python
# ❌ Assuming widget structure
assert widget.errors_group.isVisible()  # May not exist

# ✅ Safe widget checking
assert hasattr(widget, 'errors_group')
if hasattr(widget, 'errors_group'):
    assert widget.errors_group.isVisible()
```

#### Event Processing Issues
```python
# ❌ Not processing events
widget.button.click()
assert widget.result_label.text() == "Clicked"  # May fail

# ✅ Process events before assertion
widget.button.click()
UITestHelper.process_events()
assert widget.result_label.text() == "Clicked"
```

### 4. Test Environment Issues

#### sys.argv Conflicts
```python
# ❌ sys.argv conflicts with pytest
import sys
sys.argv = ['program', '--config', 'test.json']

# ✅ Proper argument mocking
from unittest.mock import patch

with patch('sys.argv', ['program', '--config', 'test.json']):
    # Test code here
    pass
```

#### Environment Variable Issues
```python
# ❌ Environment pollution
import os
os.environ['TEST_VAR'] = 'value'

# ✅ Proper environment management
from unittest.mock import patch

with patch.dict(os.environ, {'TEST_VAR': 'value'}):
    # Test code here
    pass
```

## Test Utilities Reference

### MockConfigurationManager

```python
from tests.test_utils import MockConfigurationManager

# Create LLM backend mock
mock_backend = MockConfigurationManager.create_llm_backend_mock('openai')

# Create service mock
mock_service = MockConfigurationManager.create_service_mock(ServiceClass)

# Create widget mock
mock_widget = MockConfigurationManager.create_widget_mock()
```

### UITestHelper

```python
from tests.test_utils import UITestHelper

# Process UI events
UITestHelper.process_events()

# Verify widget visibility
UITestHelper.verify_widget_visibility(widget, True)

# Verify widget enabled state
UITestHelper.verify_widget_enabled(button, False)

# Verify table item text
UITestHelper.verify_table_item_text(table, row, col, "Expected")

# Count signal emissions
count = UITestHelper.count_signal_emissions(signal, action_function)
```

### DeterministicTestMixin

```python
from tests.test_utils import DeterministicTestMixin

class TestMyComponent(DeterministicTestMixin):
    def test_something(self):
        # Test runs in isolated environment
        # sys.argv, environment variables properly managed
        pass
```

## Debugging Patterns

### 1. Test Failure Investigation

```python
# Add debugging output
def test_failing_function():
    result = function_under_test()
    print(f"DEBUG: result = {result}")  # Temporary debug output
    print(f"DEBUG: type = {type(result)}")
    assert result == expected_value
```

### 2. Mock Behavior Debugging

```python
# Verify mock calls
def test_with_mock_debugging():
    mock_service = Mock()
    
    # Call function under test
    result = function_that_uses_service(mock_service)
    
    # Debug mock calls
    print(f"Mock called with: {mock_service.method.call_args_list}")
    assert mock_service.method.called
```

### 3. UI State Debugging

```python
# Debug widget state
def test_widget_state():
    widget = create_widget()
    
    # Debug widget properties
    print(f"Widget visible: {widget.isVisible()}")
    print(f"Widget enabled: {widget.isEnabled()}")
    print(f"Widget attributes: {dir(widget)}")
    
    # Continue with test
    assert widget.isVisible()
```

## Performance Patterns

### 1. Efficient Test Setup

```python
# ✅ Use class-level fixtures for expensive setup
class TestExpensiveSetup:
    @pytest.fixture(scope="class")
    def expensive_resource(self):
        resource = create_expensive_resource()
        yield resource
        cleanup_resource(resource)
```

### 2. Parallel Test Execution

```python
# Run tests in parallel
# pytest -n auto tests/

# Mark tests that can't run in parallel
@pytest.mark.no_parallel
def test_requires_exclusive_access():
    pass
```

### 3. Test Data Optimization

```python
# ✅ Use factories for consistent test data
def create_minimal_component():
    return SOUPComponent(
        id="test-001",
        name="Test",
        version="1.0"
        # Only required fields
    )

def create_full_component():
    return SOUPComponent(
        # All fields for comprehensive testing
        **get_full_component_data()
    )
```

## Conclusion

This reference guide provides quick solutions to common testing challenges. Keep it handy during development and update it as new patterns emerge.

For more detailed information, refer to:
- [Test Maintenance Guide](TEST_MAINTENANCE_GUIDE.md)
- [Development Workflow](DEVELOPMENT_WORKFLOW.md)
- Test utility source code in `tests/test_utils.py`