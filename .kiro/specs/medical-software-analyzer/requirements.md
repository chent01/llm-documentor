# Requirements Document

## Introduction

This document outlines the requirements for a Medical Software Analysis Tool - a PyQt6 desktop application that analyzes local C and JavaScript/Electron projects to generate medical software documentation including requirements, risk registers, traceability matrices, and test skeletons. The tool operates entirely locally without cloud dependencies and follows medical device software development standards.

## Requirements

### Requirement 1

**User Story:** As a medical device software developer, I want to select and analyze local project files, so that I can generate comprehensive documentation for regulatory compliance.

#### Acceptance Criteria

1. WHEN the user opens the application THEN the system SHALL display a main window with project folder selection capability
2. WHEN the user selects a project root folder THEN the system SHALL scan and display the folder structure in a file tree
3. WHEN the user views the file tree THEN the system SHALL provide checkboxes for each file and subfolder to enable selective inclusion
4. WHEN the user selects files THEN the system SHALL only include C and JavaScript/Electron files in the analysis scope
5. IF the user selects unsupported file types THEN the system SHALL exclude them from analysis with appropriate notification

### Requirement 2

**User Story:** As a medical device software developer, I want to provide project context and run automated analysis, so that the system can generate accurate documentation based on my specific use case.

#### Acceptance Criteria

1. WHEN the user has selected files THEN the system SHALL provide a text input field for project description including intended use, target device, user type, expected hazards, and SOUP components
2. WHEN the user clicks "Analyze" THEN the system SHALL execute static code analysis and LLM-driven analysis in sequential stages
3. WHEN analysis is running THEN the system SHALL display progress indicators for each analysis stage
4. WHEN analysis completes THEN the system SHALL display results in organized tabs
5. IF analysis fails at any stage THEN the system SHALL provide clear error messages and allow partial results review

### Requirement 3

**User Story:** As a medical device software developer, I want the system to extract features and generate requirements, so that I can establish traceability from code to requirements.

#### Acceptance Criteria

1. WHEN code analysis runs THEN the system SHALL parse C files using tree-sitter and libclang for AST analysis
2. WHEN code analysis runs THEN the system SHALL parse JavaScript files using tree-sitter for AST analysis
3. WHEN feature extraction runs THEN the system SHALL identify implemented features with file and line number references
4. WHEN requirements generation runs THEN the system SHALL generate User Requirements (URs) derived from identified features
5. WHEN requirements generation runs THEN the system SHALL generate Software Requirements (SRs) derived from each UR
6. WHEN requirements are generated THEN the system SHALL provide editable text fields for requirement refinement

### Requirement 4

**User Story:** As a medical device software developer, I want the system to generate a risk register, so that I can identify and mitigate potential hazards in my software.

#### Acceptance Criteria

1. WHEN risk analysis runs THEN the system SHALL identify potential hazards for each Software Requirement
2. WHEN hazards are identified THEN the system SHALL assign severity levels (Catastrophic/Serious/Minor) using heuristics
3. WHEN hazards are identified THEN the system SHALL assign probability levels (High/Medium/Low) using heuristics
4. WHEN risk analysis completes THEN the system SHALL propose mitigation strategies for each identified hazard
5. WHEN risk register is generated THEN the system SHALL provide editable fields following ISO 14971 format
6. WHEN viewing risks THEN the system SHALL allow filtering by severity level

### Requirement 5

**User Story:** As a medical device software developer, I want the system to create traceability matrices, so that I can demonstrate compliance with medical device standards.

#### Acceptance Criteria

1. WHEN traceability analysis runs THEN the system SHALL map code references to Software Requirements
2. WHEN traceability analysis runs THEN the system SHALL map Software Requirements to User Requirements
3. WHEN traceability analysis runs THEN the system SHALL map requirements to identified risks
4. WHEN traceability matrix is complete THEN the system SHALL display the matrix in a tabular format
5. WHEN user requests export THEN the system SHALL generate CSV format traceability matrix
6. IF traceability gaps exist THEN the system SHALL highlight missing links for user review

### Requirement 6

**User Story:** As a medical device software developer, I want the system to generate test skeletons and run them in a sandbox, so that I can verify my software meets requirements.

#### Acceptance Criteria

1. WHEN test generation runs THEN the system SHALL create unit test skeletons for C functions using Unity/MinUnit framework
2. WHEN test generation runs THEN the system SHALL create unit test skeletons for JavaScript functions using Jest/Mocha framework
3. WHEN test generation runs THEN the system SHALL create integration test stubs with hardware mocks where applicable
4. WHEN user requests test execution THEN the system SHALL run tests in a Docker container sandbox
5. WHEN tests execute THEN the system SHALL collect and display test results with pass/fail status
6. WHEN tests complete THEN the system SHALL generate coverage reports where applicable

### Requirement 7

**User Story:** As a medical device software developer, I want all analysis to run locally using local LLMs, so that I can maintain confidentiality and avoid cloud dependencies.

#### Acceptance Criteria

1. WHEN LLM processing is required THEN the system SHALL use only locally hosted language models
2. WHEN embeddings are needed THEN the system SHALL use local embedding models with FAISS vector storage
3. WHEN LLM calls are made THEN the system SHALL provide an abstraction layer supporting multiple local LLM backends
4. IF local LLM is unavailable THEN the system SHALL provide clear error messages and graceful degradation
5. WHEN processing large files THEN the system SHALL chunk content appropriately for local model token limits

### Requirement 8

**User Story:** As a medical device software developer, I want to manage SOUP components and export comprehensive documentation, so that I can provide complete regulatory submissions.

#### Acceptance Criteria

1. WHEN SOUP management is accessed THEN the system SHALL provide fields for component name, version, usage reason, and safety justification
2. WHEN user enters SOUP information THEN the system SHALL store and display the SOUP inventory
3. WHEN user requests export THEN the system SHALL create a comprehensive zip bundle containing all generated artifacts
4. WHEN export is created THEN the system SHALL include requirements, risk register, traceability matrix, test results, and SOUP inventory
5. WHEN export is created THEN the system SHALL include audit logs of user actions and analysis timestamps
6. IF export fails THEN the system SHALL provide partial export options and clear error reporting