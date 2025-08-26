1 Goals & constraints (MVP)

Input: local project folder only. User can choose subfolders/files to include in analysis.

Languages: C (embedded) and JavaScript / Electron (desktop control app) only.

LLMs must run locally (on machine or LAN-hosted local model servers). No cloud calls.

SOUP (software of unknown pedigree) detection: initially from user description only. Later implement auto-detection.

UI: PyQt6 desktop app written in Python for portability.

2 High-level flow (user journey)

User opens app and chooses project root folder.

App scans structure and shows a file tree. User selects relevant subfolders and files to include.

User enters a short project description (intended use, target device, user, brief hazards they expect, note about SOUP components).

User clicks Analyze. App runs static scans + LLM-driven analyses in stages:

Project summary & feature extraction.

Preliminary medical software class suggestion (human must confirm).

Generate candidate User Requirements (URs) and derived Software Requirements (SRs).

Generate risk register (hazards, severity, probability heuristics, mitigations).

Cross-reference code → requirements → risks to produce traceability matrix.

Generate test skeletons (unit tests, integration test stubs) and CI job templates.

Results shown in tabs. User can edit, accept/reject, run generated tests in sandbox (Docker) and export artifacts.

3 Minimum viable feature set (MVP)

Local folder ingestion and file selection UI.

Parser + static scan for C and JS (tree-sitter for AST + clang checks for C, eslint for JS optional integration).

Local LLM orchestration: RAG pipeline (chunk code files, embed, search local vector store) + LLM prompts.

Feature extraction → URs → SRs inference.

Risk register generation (ISO 14971 style fields: hazard, cause, effect, severity, probability, mitigation, verification).

Traceability matrix generation (CSV export).

Test skeleton generator for unit tests (C: Unity/MinUnit or googletest if native; JS: jest/mocha skeletons).

Simple sandbox run: run tests in Docker container and collect logs.

Save/export artifacts (zip with traces, test outputs, requirements, risk register).

4 Suggested tech stack & key libraries (Python-focused)

UI: PyQt6 (Qt Designer for rapid prototyping optional)

Parsing & AST:

tree-sitter bindings (python-tree-sitter) - single parser solution supporting C and JS.

libclang / clang.cindex for deeper C analysis where needed.

Static analysis:

C: cppcheck or clang-tidy (call as subprocess, parse outputs).

JS: eslint (call node/npm) — optional for MVP.

LLM embedding + RAG:

Embeddings: sentence-transformers (if model can run locally) or small local embedding models; store in FAISS or Chroma.

LLM runtime: llama.cpp/ggml interfaces, or local model server (text-generation-webui, vLLM, or a local REST wrapper around a Hugging Face model). Keep abstraction layer so the model backend can be swapped.

Vector DB: FAISS (local) for chunk retrieval.

Test generation: produce files compatible with Unity (for C embedded tests), pytest or jest for JS if relevant.

Containerization: Docker for sandboxed test execution.

Persistence: small SQLite DB for artifacts & traceability; files for evidence bundle.

5 Architecture & modules (python package outline)
medsw_ai/
├─ app.py              # launches PyQt6 UI
├─ ui/                 # Qt Designer .ui files or hand-coded widgets
├─ core/
│  ├─ ingestion.py     # folder scan, file selection model
│  ├─ parser_c.py      # tree-sitter + libclang helpers for C
│  ├─ parser_js.py     # tree-sitter for JS/Electron
│  ├─ static_scan.py   # wrappers for cppcheck/eslint
│  ├─ llm_service.py   # abstracts local model calls
│  ├─ embeddings.py    # chunking + embedding + FAISS index
│  ├─ raiser.py        # reasoning orchestrator: pipelines of prompts
│  ├─ requirements.py  # UR/SR representation, inference logic
│  ├─ risk.py          # hazard generation, RPN heuristics, mitigations
│  ├─ traceability.py  # build CSV/Excel and mapping storage
│  ├─ testgen.py       # generates unit/integration test skeletons
│  ├─ sandbox.py       # manages Docker run for tests
│  └─ persistence.py   # sqlite wrapper, artifact bundling
├─ models/             # project templates, prompt templates
└─ export/             # export helpers (pdf, csv, zip)
6 UI sketch (PyQt6 windows + main widgets)

Main window: left: project tree + checkboxes. right: tabbed results.

Top bar: project directory selector, short description text box, "Analyze" button, progress indicator.

Results tabs:

Summary: inferred software class, feature list, confidence, clickable evidence snippets.

Requirements: list of URs & SRs with editable text and ID fields.

Risk Register: hazards table editable (severity, prob., mitigation), filter by severity.

Traceability: matrix viewer + export button.

Tests: generated test files list, run button, pass/fail logs.

SOUP: user-entered SOUP inventory (free-text fields initially).

Bottom: audit log / actions (accept/reject) and "Export bundle".

7 Local LLM / RAG design (practical)

Principles: local embeddings + vector store + small LLM. Keep prompts short and evidence-backed.

Pipeline:

Chunking: break selected code files into logical chunks (function-level where possible) with metadata (file path, start/end line).

Embedding & Indexing: embed chunks and store in FAISS.

Retriever: for each prompt, retrieve top-K code chunks by similarity.

Prompting: pass retrieved chunks + short instruction to local LLM with a strict template. Include show_evidence: true flag so model outputs file:line references.

Post-process: parse LLM outputs into structured objects (requirements, risk items, test cases).

Implementation notes:

Provide a pluggable LLMBackend class with generate(prompt, context_chunks, temperature, max_tokens) so users can switch between llama.cpp, a local REST server, or a remote server later.

Keep maximum token sizes in mind: summarize long files before sending to model.

8 Prompt templates (starter)

Feature extraction prompt (concise)

You are a code analyst. Given the following code chunks and their file locations, list the implemented features as short bullet points. For each bullet, include: feature id, brief description (1-2 sentences), and the file:line evidence that supports it.


<code_chunks>


Return JSON array of {"id":"F1","desc":"...","evidence":[{"file":"...","start":12,"end":24}],"confidence":0-1}

Requirements generation (concise)

You are a systems engineer. From these features, infer User Requirements (UR) and for each UR derive 1-3 Software Requirements (SR) with IDs, brief text, and acceptance criteria. Include justification referencing feature IDs.

Risk generation

For each SR, identify potential hazards (what could go wrong leading to patient harm), list severity (Catastrophic/Serious/Minor), likelihood (High/Medium/Low), and propose at least one mitigation and a test that would verify the mitigation. Output as JSON.

Traceability linking

Given SRs and code chunk metadata, find code references that implement each SR and link them. Output mapping SR_ID -> [code_references].
9 Traceability CSV template (columns)
RequirementID,RequirementType,RequirementText,DerivedFromFeatureIDs,CodeReferences (semicolon separated file: start-end),TestCaseIDs,RiskIDs
UR-001,User,"Device shall...","F1;F2","src/control.c:120-160;src/ui/main.js:12-30","TC-001;TC-002","R-001"
10 Test generation strategy

Unit tests: generate small tests for pure functions. For hardware-facing functions, generate mocks/stubs.

Integration tests: simulate I/O using a software emulator or mocks. Provide a hardware_stub/ directory with clear TODOs where real hardware tests are required.

Fuzz tests: generate fuzz harness for parsers or comms message handlers (optional in later versions).

CI job: create a Dockerfile that builds project, runs tests, collects coverage (lcov for C, coverage.py for JS if applicable).

11 SOUP handling (MVP)

Initial: user-provided list in UI with fields: component name, version, reason for use, safety justification.

Later: auto-scan package.json, manifest and produce a found-software list with CVE lookups.

12 Persistence & evidence

Store a read-only snapshot: record selected files + commit-style checksum (timestamp + hash of included files) with each analysis run.

Save LLM outputs, chosen edits, approvals and test execution logs into an evidence bundle (zip) for audit.

13 Development plan (first 6 dev tasks)

UI: basic PyQt6 app with folder selector and file-tree with checkboxes.

Ingestion: implement ingestion.py to scan and return file metadata + simple preview.

Parser: wire up tree-sitter for C and JS and implement chunker that returns function-level chunks.

LLM backend stub: implement local LLMBackend interface abstracting a dummy model (returns deterministic templates) and FAISS embedding pipeline.

Requirements pipeline: implement simple prompt flow (feature extraction -> UR -> SR) using LLM backend.

Traceability CSV generator and simple export.

14 Acceptance & QA checklist (MVP)




15 Example next steps (I can do for you now)

Produce the PyQt6 skeleton for the main window + file-tree widget.

Produce ingestion.py implementation that lists files and returns line counts and a function-level splitter