# Design Document

## Overview

The Medical Software Analysis Tool is a PyQt6 desktop application that provides comprehensive analysis of C and JavaScript/Electron medical device software projects. The system operates entirely locally, using local LLMs and static analysis tools to generate requirements documentation, risk registers, traceability matrices, and test skeletons that comply with medical device software standards.

## Architecture

### High-Level Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Layer      │    │  Core Services  │    │  Data Layer     │
│   (PyQt6)       │◄──►│   (Business     │◄──►│  (SQLite +      │
│                 │    │    Logic)       │    │   Files)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  External Tools │    │   Local LLM     │    │   Vector Store  │
│ (cppcheck, etc) │    │   Backend       │    │    (FAISS)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Architecture

The system is organized into the following main components:

1. **UI Layer**: PyQt6-based user interface
2. **Core Services**: Business logic and orchestration
3. **Parser Layer**: Code analysis and AST processing
4. **LLM Service**: Local language model integration
5. **Analysis Pipeline**: Requirements and risk analysis
6. **Export System**: Documentation generation and bundling

## Components and Interfaces

### UI Components

#### MainWindow
- **Purpose**: Primary application window and orchestration
- **Key Methods**:
  - `select_project_folder()`: Opens folder selection dialog
  - `populate_file_tree()`: Displays project structure with checkboxes
  - `start_analysis()`: Initiates analysis pipeline
  - `update_progress()`: Updates progress indicators

#### FileTreeWidget
- **Purpose**: Interactive file selection with checkboxes
- **Key Methods**:
  - `load_directory_structure()`: Scans and displays folder hierarchy
  - `get_selected_files()`: Returns list of selected files
  - `filter_supported_files()`: Filters C and JS files only

#### ResultsTabWidget
- **Purpose**: Tabbed display of analysis results
- **Tabs**:
  - Summary: Project overview and confidence metrics
  - Requirements: Editable UR/SR lists
  - Risk Register: ISO 14971 compliant risk table
  - Traceability: Matrix viewer with export
  - Tests: Generated test files and execution results
  - SOUP: Software inventory management

### Core Service Components

#### IngestionService
```python
class IngestionService:
    def scan_project(self, root_path: str) -> ProjectStructure
    def filter_files(self, files: List[str]) -> List[str]
    def get_file_metadata(self, file_path: str) -> FileMetadata
```

#### ParserService
```python
class ParserService:
    def parse_c_file(self, file_path: str) -> CCodeStructure
    def parse_js_file(self, file_path: str) -> JSCodeStructure
    def extract_functions(self, ast: AST) -> List[Function]
    def chunk_code(self, code_structure: CodeStructure) -> List[CodeChunk]
```

#### LLMService
```python
class LLMService:
    def generate_response(self, prompt: str, context: List[CodeChunk]) -> str
    def embed_chunks(self, chunks: List[CodeChunk]) -> List[Embedding]
    def retrieve_relevant_chunks(self, query: str, k: int) -> List[CodeChunk]
```

#### AnalysisOrchestrator
```python
class AnalysisOrchestrator:
    def run_feature_extraction(self, chunks: List[CodeChunk]) -> List[Feature]
    def generate_requirements(self, features: List[Feature]) -> RequirementsSet
    def generate_risk_register(self, requirements: RequirementsSet) -> RiskRegister
    def build_traceability_matrix(self, requirements: RequirementsSet, chunks: List[CodeChunk]) -> TraceabilityMatrix
```

### Parser Layer

#### CParser
- **Technology**: tree-sitter + libclang
- **Capabilities**:
  - AST parsing for C code
  - Function extraction with signatures
  - Static analysis integration (cppcheck)
  - Hardware interface detection

#### JSParser
- **Technology**: tree-sitter
- **Capabilities**:
  - JavaScript/Electron AST parsing
  - Function and class extraction
  - Module dependency analysis
  - Optional ESLint integration

### LLM Integration Layer

#### LLMBackend (Abstract Interface)
```python
class LLMBackend:
    def generate(self, prompt: str, context_chunks: List[str], 
                temperature: float, max_tokens: int) -> str
    def is_available(self) -> bool
    def get_model_info(self) -> ModelInfo
```

#### Concrete Implementations
- **LlamaCppBackend**: Integration with llama.cpp
- **LocalServerBackend**: REST API integration for local model servers
- **HuggingFaceBackend**: Direct HuggingFace model integration

#### EmbeddingService
- **Technology**: sentence-transformers + FAISS
- **Capabilities**:
  - Code chunk embedding generation
  - Vector similarity search
  - Efficient retrieval for RAG pipeline

## Data Models

### Core Data Structures

#### ProjectStructure
```python
@dataclass
class ProjectStructure:
    root_path: str
    selected_files: List[str]
    description: str
    metadata: Dict[str, Any]
    timestamp: datetime
```

#### CodeChunk
```python
@dataclass
class CodeChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    function_name: Optional[str]
    chunk_type: ChunkType  # FUNCTION, CLASS, MODULE
    metadata: Dict[str, Any]
```

#### Feature
```python
@dataclass
class Feature:
    id: str
    description: str
    confidence: float
    evidence: List[CodeReference]
    category: FeatureCategory
```

#### Requirement
```python
@dataclass
class Requirement:
    id: str
    type: RequirementType  # USER, SOFTWARE
    text: str
    acceptance_criteria: List[str]
    derived_from: List[str]  # Feature IDs or parent requirement IDs
    code_references: List[CodeReference]
```

#### RiskItem
```python
@dataclass
class RiskItem:
    id: str
    hazard: str
    cause: str
    effect: str
    severity: Severity  # CATASTROPHIC, SERIOUS, MINOR
    probability: Probability  # HIGH, MEDIUM, LOW
    risk_level: RiskLevel
    mitigation: str
    verification: str
    related_requirements: List[str]
```

### Database Schema

#### SQLite Tables
```sql
-- Project metadata and analysis runs
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT,
    root_path TEXT,
    description TEXT,
    created_at TIMESTAMP,
    last_analyzed TIMESTAMP
);

-- Analysis artifacts storage
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    run_timestamp TIMESTAMP,
    status TEXT,
    artifacts_path TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Traceability relationships
CREATE TABLE traceability_links (
    id INTEGER PRIMARY KEY,
    analysis_run_id INTEGER,
    source_type TEXT,
    source_id TEXT,
    target_type TEXT,
    target_id TEXT,
    link_type TEXT,
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

## Error Handling

### Error Categories and Strategies

#### File System Errors
- **Strategy**: Graceful degradation with user notification
- **Implementation**: Try-catch blocks with specific error messages
- **Recovery**: Allow partial analysis with available files

#### Parser Errors
- **Strategy**: Skip problematic files with detailed logging
- **Implementation**: Individual file error handling in parser loop
- **Recovery**: Continue analysis with successfully parsed files

#### LLM Service Errors
- **Strategy**: Fallback to template-based generation
- **Implementation**: Circuit breaker pattern for LLM calls
- **Recovery**: Provide manual input options for failed generations

#### Analysis Pipeline Errors
- **Strategy**: Stage-wise error handling with checkpoint recovery
- **Implementation**: Pipeline state management with rollback capability
- **Recovery**: Resume from last successful stage

### Error Reporting
```python
class AnalysisError(Exception):
    def __init__(self, stage: str, details: str, recoverable: bool = True):
        self.stage = stage
        self.details = details
        self.recoverable = recoverable
        super().__init__(f"Analysis error in {stage}: {details}")
```

## Testing Strategy

### Unit Testing
- **Framework**: pytest for Python components
- **Coverage**: Minimum 80% code coverage for core services
- **Mocking**: Mock external dependencies (LLM, file system)
- **Test Data**: Synthetic C and JS code samples for parser testing

### Integration Testing
- **Scope**: End-to-end pipeline testing with real code samples
- **Environment**: Docker containers for isolated testing
- **Data**: Curated medical device code examples
- **Validation**: Output format and content validation

### UI Testing
- **Framework**: pytest-qt for PyQt6 testing
- **Scope**: User interaction flows and widget behavior
- **Automation**: Automated UI test scenarios
- **Manual**: Usability testing with target users

### Performance Testing
- **Metrics**: Analysis time for various project sizes
- **Benchmarks**: Memory usage and processing speed
- **Optimization**: Profiling and bottleneck identification
- **Scalability**: Testing with large codebases (>100k LOC)

### Security Testing
- **Local Model Security**: Validate no external network calls
- **File System Security**: Sandbox file access validation
- **Input Validation**: Malformed file and input handling
- **Data Privacy**: Ensure no data leakage in logs or exports

### Compliance Testing
- **Standards Validation**: ISO 14971 and IEC 62304 compliance
- **Output Verification**: Generated documents meet regulatory requirements
- **Traceability Validation**: Complete requirement-to-code traceability
- **Audit Trail**: Comprehensive logging for regulatory review