# Requirements Flow Architecture Fix

## Problem Identified

The original architecture had a conceptual mix-up in the requirements flow. The system was trying to:

1. **Risk Register** was expecting `software_requirements` as input, but these didn't exist yet
2. **Feature Extractor** was correctly extracting features from code ✓
3. **Traceability Service** was trying to link everything but the flow was backwards

The flow was: **Code → Features → ??? → Risks** (missing requirements generation)

## Solution Implemented

### Correct Requirements Engineering Flow

The proper flow should be:
**Code → Features → User Requirements → Software Requirements → Risks → Traceability**

### New Architecture

1. **Code Analysis** → Extract features from source code
2. **Feature Analysis** → Generate user requirements from features  
3. **Requirements Derivation** → Generate software requirements from user requirements
4. **Risk Analysis** → Generate risks from software requirements
5. **Traceability Analysis** → Create full traceability matrix

### Implementation Changes

#### 1. New Requirements Generator Service

Created `medical_analyzer/services/requirements_generator.py`:

- **`RequirementsGenerator`** class that takes features and generates both user and software requirements
- **LLM-based generation** with heuristic fallback
- **Proper traceability** - user requirements trace to features, software requirements trace to user requirements
- **Category-based grouping** - features are grouped by category to create meaningful user requirements

#### 2. Updated Analysis Orchestrator

Modified `medical_analyzer/services/analysis_orchestrator.py`:

- **Added Stage 4**: Requirements Generation (between Feature Extraction and Hazard Identification)
- **Updated stage numbers**: All subsequent stages renumbered (5-9 instead of 4-8)
- **Updated total stages**: From 8 to 9 stages
- **Fixed traceability flow**: Now passes proper requirements to traceability service
- **Updated results compilation**: Uses generated requirements instead of converting features

#### 3. Enhanced Result Models

Updated `medical_analyzer/models/result_models.py`:

- **Added `RequirementsGenerationResult`** - contains both user and software requirements with metadata

#### 4. Fixed Data Model Issues

- **Priority field**: Moved from direct field to metadata (Requirement model doesn't have priority field)
- **Traceability links**: Now properly connects the full chain from code to risks

### Flow Verification

The test script `test_requirements_flow.py` demonstrates:

```
✓ Features → User Requirements: 3 → 3
✓ User Requirements → Software Requirements: 3 → 3
✓ Feature traceability: 3/3 features traced
✓ UR traceability: 3/3 URs traced
```

### Example Output

**Features:**
- FEAT_0001: Input data validation functionality
- FEAT_0002: Main user interface window  
- FEAT_0003: Database data storage functionality

**User Requirements (generated from features):**
- UR_0001: The system shall provide data validation features
- UR_0002: The system shall provide an intuitive user interface
- UR_0003: The system shall provide data storage capabilities

**Software Requirements (generated from user requirements):**
- SR_0001: Software shall implement Input data validation functionality
- SR_0002: Software shall implement Main user interface window
- SR_0003: Software shall implement Database data storage functionality

### Benefits

1. **Proper Requirements Engineering**: Follows standard requirements engineering practices
2. **Full Traceability**: Complete chain from code to risks with proper intermediate steps
3. **Medical Device Compliance**: Aligns with medical device software development standards
4. **Maintainable Architecture**: Clear separation of concerns and proper data flow
5. **LLM Integration**: Uses AI to generate meaningful requirements with fallback to heuristics

### Risk Register Integration

Now the Risk Register can properly:
1. Receive **software requirements** as input (instead of empty lists)
2. Generate risks that are **traceable to specific requirements**
3. Create **proper risk-requirement relationships** for compliance

### Next Steps

The architecture now supports the complete flow:
1. ✅ Code → Features (implemented)
2. ✅ Features → User Requirements (implemented) 
3. ✅ User Requirements → Software Requirements (implemented)
4. ✅ Software Requirements → Risks (existing, now properly fed)
5. ✅ Full Traceability Matrix (existing, now properly connected)

This fix resolves the fundamental architectural issue and enables proper medical device software analysis with full requirements traceability.