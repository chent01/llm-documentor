# TestSuite Attribute Error Fix

## Problem
The AnalysisOrchestrator was trying to access `test_suite.frameworks_used` attribute which doesn't exist in the TestSuite class.

## Root Cause
The TestSuite dataclass has these attributes:
- `project_name: str`
- `test_skeletons: List[TestSkeleton]`
- `framework_configs: Dict[str, Dict[str, Any]]`
- `integration_tests: List[TestSkeleton]`
- `created_at: datetime`

But the analysis orchestrator was trying to access a non-existent `frameworks_used` attribute.

## Solution
Fixed the `_stage_test_generation()` method in AnalysisOrchestrator to extract framework information from the existing `framework_configs` attribute instead of trying to access the non-existent `frameworks_used` attribute.

### Code Changes

#### Before (Broken):
```python
def _stage_test_generation(self) -> Dict[str, Any]:
    """Stage 6: Test generation and validation."""
    project_structure = self.current_analysis['results']['project_ingestion']['project_structure']
    parsed_files = self.current_analysis['results']['code_parsing']['parsed_files']
    
    test_suite = self.test_generator.generate_test_suite(project_structure, parsed_files)
    
    return {
        'test_suite': test_suite,
        'total_tests': len(test_suite.test_skeletons),
        'test_frameworks': test_suite.frameworks_used  # ❌ Attribute doesn't exist
    }
```

#### After (Fixed):
```python
def _stage_test_generation(self) -> Dict[str, Any]:
    """Stage 6: Test generation and validation."""
    project_structure = self.current_analysis['results']['project_ingestion']['project_structure']
    parsed_files = self.current_analysis['results']['code_parsing']['parsed_files']
    
    test_suite = self.test_generator.generate_test_suite(project_structure, parsed_files)
    
    # Extract frameworks from framework_configs
    frameworks_used = list(test_suite.framework_configs.keys()) if test_suite.framework_configs else []
    
    return {
        'test_suite': test_suite,
        'total_tests': len(test_suite.test_skeletons),
        'test_frameworks': frameworks_used  # ✅ Correctly extracted from framework_configs
    }
```

## Verification
- ✅ AnalysisOrchestrator initializes successfully
- ✅ Test generation stage works correctly
- ✅ Framework information is properly extracted from framework_configs
- ✅ Returns correct list of frameworks (e.g., ['c', 'javascript'])
- ✅ All attribute errors resolved

## Impact
- Fixed critical AttributeError that was preventing test generation stage from running
- Improved robustness of the analysis pipeline
- Maintained compatibility with existing TestSuite functionality
- Proper extraction of framework information for reporting

## Files Modified
- `medical_analyzer/services/analysis_orchestrator.py`
  - Fixed `_stage_test_generation()` method to use correct attribute

## Testing
All tests pass successfully:
- Test generation stage completes without errors
- Framework information is correctly extracted
- TestSuite object is properly handled
- No attribute errors remain

## Related TestSuite Structure
For reference, the TestSuite class structure:
```python
@dataclass
class TestSuite:
    """Collection of test skeletons for a project."""
    project_name: str
    test_skeletons: List[TestSkeleton]
    framework_configs: Dict[str, Dict[str, Any]]  # ✅ This is the correct attribute to use
    integration_tests: List[TestSkeleton]
    created_at: datetime
```

The `framework_configs` typically contains:
```python
{
    'c': {'framework': 'unity'},
    'javascript': {'framework': 'jest'}
}
```

So extracting `list(framework_configs.keys())` gives us `['c', 'javascript']` which represents the frameworks used.