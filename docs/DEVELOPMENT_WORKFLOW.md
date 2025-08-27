# Development Workflow with Test Validation

## Overview

This document outlines the updated development workflow that includes comprehensive test validation steps to prevent test failures and maintain code quality.

## Core Principles

1. **Test-First Development**: Write tests before or alongside implementation
2. **Continuous Validation**: Run tests frequently during development
3. **Fail Fast**: Catch issues early in the development cycle
4. **Comprehensive Coverage**: Ensure all code paths are tested

## Workflow Stages

### 1. Pre-Development Setup

**Environment Preparation**:
```bash
# Ensure clean development environment
python -m pytest --version
python -c "from PyQt6 import QtWidgets; print('PyQt6 OK')"

# Install development dependencies
pip install -e ".[dev]"

# Verify test suite baseline
python -m pytest tests/ --tb=short
```

**Branch Setup**:
```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Verify starting test state
python -m pytest tests/ -x --tb=short
```

### 2. Feature Development Cycle

#### Phase 1: Planning and Test Design

**Requirements Analysis**:
1. Define feature requirements clearly
2. Identify affected components and interfaces
3. Plan test scenarios (happy path, edge cases, error conditions)
4. Document expected behavior changes

**Test Planning Checklist**:
- [ ] Unit tests for new functionality
- [ ] Integration tests for component interactions
- [ ] UI tests for interface changes
- [ ] Error handling tests for failure scenarios
- [ ] Performance tests for critical paths

#### Phase 2: Test-Driven Implementation

**Write Tests First**:
```bash
# Create test file for new feature
touch tests/test_new_feature.py

# Write failing tests that define expected behavior
python -m pytest tests/test_new_feature.py -v
# Expected: Tests fail (red phase)
```

**Implement Feature**:
```bash
# Implement minimum code to make tests pass
python -m pytest tests/test_new_feature.py -v
# Expected: Tests pass (green phase)

# Refactor and optimize
python -m pytest tests/test_new_feature.py -v
# Expected: Tests still pass (refactor phase)
```

#### Phase 3: Integration and Validation

**Module-Level Testing**:
```bash
# Test the entire module containing changes
python -m pytest tests/test_affected_module.py -v

# Check for regressions in related modules
python -m pytest tests/test_related_module.py -v
```

**Cross-Module Integration**:
```bash
# Run integration tests
python -m pytest tests/ -k "integration" -v

# Run UI tests if interface changes were made
python -m pytest tests/ -k "ui" -v
```

### 3. Quality Assurance Gates

#### Gate 1: Unit Test Validation

**Criteria**:
- All new unit tests pass
- No regressions in existing unit tests
- Code coverage maintained or improved

**Commands**:
```bash
# Run unit tests with coverage
python -m pytest tests/ --cov=medical_analyzer --cov-report=html

# Check coverage threshold (should be >80%)
python -m pytest tests/ --cov=medical_analyzer --cov-fail-under=80
```

#### Gate 2: Integration Test Validation

**Criteria**:
- All integration tests pass
- Component interactions work correctly
- No breaking changes to public interfaces

**Commands**:
```bash
# Run integration tests
python -m pytest tests/ -m "integration" -v

# Run end-to-end tests
python -m pytest tests/test_end_to_end_integration.py -v
```

#### Gate 3: Performance Validation

**Criteria**:
- Test execution time within limits (<5 minutes for full suite)
- No significant performance regressions
- Memory usage remains stable

**Commands**:
```bash
# Check test execution time
time python -m pytest tests/

# Profile slow tests
python -m pytest --durations=10 tests/
```

### 4. Pre-Commit Validation

**Automated Checks**:
```bash
# Run pre-commit validation script
./scripts/pre_commit_validation.sh

# Or manual validation
python -m pytest tests/ -x --tb=short
python -m flake8 medical_analyzer/
python -m mypy medical_analyzer/
```

**Pre-Commit Hook Setup**:
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Configure .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest tests/ -x --tb=short
        language: system
        pass_filenames: false
        always_run: true
EOF
```

### 5. Code Review Process

#### Reviewer Checklist

**Test Quality Review**:
- [ ] Tests cover new functionality completely
- [ ] Tests include edge cases and error conditions
- [ ] Test names clearly describe what is being tested
- [ ] Tests are independent and don't rely on execution order
- [ ] Mocks are properly configured and realistic

**Implementation Review**:
- [ ] Code changes align with test expectations
- [ ] Public interfaces are properly documented
- [ ] Error handling is comprehensive
- [ ] Performance implications are considered

**Integration Review**:
- [ ] Changes don't break existing functionality
- [ ] Database migrations are included if needed
- [ ] Configuration changes are documented
- [ ] UI changes are accessible and user-friendly

#### Review Commands

**For Reviewers**:
```bash
# Checkout the feature branch
git checkout feature/branch-name

# Run the full test suite
python -m pytest tests/ -v

# Check specific test files
python -m pytest tests/test_modified_component.py -v

# Verify test coverage
python -m pytest tests/ --cov=medical_analyzer --cov-report=term-missing
```

### 6. Continuous Integration Pipeline

#### CI Configuration (.github/workflows/tests.yml)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        python -m pytest tests/ --cov=medical_analyzer --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

#### CI Quality Gates

**Mandatory Checks**:
- All tests pass on supported Python versions
- Code coverage meets minimum threshold (80%)
- No critical security vulnerabilities
- Performance benchmarks within acceptable range

**Optional Checks**:
- Code style compliance (flake8, black)
- Type checking (mypy)
- Documentation builds successfully
- Integration tests with external services

### 7. Deployment Validation

#### Pre-Deployment Checklist

**Test Validation**:
- [ ] Full test suite passes in production-like environment
- [ ] Integration tests pass with production configurations
- [ ] Performance tests meet production requirements
- [ ] Security tests pass vulnerability scans

**Deployment Commands**:
```bash
# Run production-like test environment
ENVIRONMENT=production python -m pytest tests/ -v

# Run security tests
python -m pytest tests/ -m "security" -v

# Validate packaging
python setup.py check --strict --metadata
```

#### Post-Deployment Monitoring

**Health Checks**:
- Monitor application startup and basic functionality
- Verify database migrations completed successfully
- Check log files for unexpected errors
- Validate API endpoints respond correctly

**Rollback Criteria**:
- Any critical functionality broken
- Performance degradation >20%
- Security vulnerabilities introduced
- Data integrity issues detected

## Emergency Procedures

### Test Failure Response

**Immediate Actions**:
1. Stop deployment if in progress
2. Identify scope of test failures
3. Determine if failures are environmental or code-related
4. Create hotfix branch if critical issue

**Investigation Process**:
```bash
# Isolate failing tests
python -m pytest tests/ --lf -v

# Run with maximum verbosity
python -m pytest tests/failing_test.py -vvv -s

# Check for environmental issues
python -c "import sys; print(sys.version)"
pip list | grep -E "(pytest|PyQt6)"
```

### Rollback Procedures

**Code Rollback**:
```bash
# Revert to last known good commit
git revert HEAD

# Or reset to specific commit
git reset --hard <last-good-commit>

# Verify tests pass after rollback
python -m pytest tests/ -x --tb=short
```

**Database Rollback**:
```bash
# Run database rollback migration
python -m medical_analyzer.database.migrate rollback

# Verify data integrity
python -m pytest tests/test_database_integrity.py -v
```

## Metrics and Monitoring

### Test Quality Metrics

**Coverage Metrics**:
- Line coverage: >80%
- Branch coverage: >75%
- Function coverage: >90%

**Performance Metrics**:
- Full test suite execution: <5 minutes
- Unit tests: <2 minutes
- Integration tests: <3 minutes

**Reliability Metrics**:
- Test flakiness rate: <1%
- False positive rate: <0.5%
- Test maintenance overhead: <10% of development time

### Monitoring Dashboard

**Key Indicators**:
- Test pass rate over time
- Test execution time trends
- Code coverage trends
- Test failure categories

**Alerting Thresholds**:
- Test pass rate drops below 95%
- Test execution time increases by >20%
- Code coverage drops below 80%
- More than 5 test failures in a single run

## Tools and Resources

### Required Tools

**Development Environment**:
- Python 3.8+
- pytest 7.0+
- PyQt6
- coverage.py
- pre-commit

**Optional Tools**:
- pytest-xdist (parallel test execution)
- pytest-benchmark (performance testing)
- pytest-mock (enhanced mocking)
- pytest-html (HTML test reports)

### Useful Commands Reference

**Test Execution**:
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_module.py

# Run tests matching pattern
python -m pytest tests/ -k "test_pattern"

# Run tests with coverage
python -m pytest tests/ --cov=medical_analyzer

# Run tests in parallel
python -m pytest tests/ -n auto
```

**Test Debugging**:
```bash
# Run with pdb on failure
python -m pytest tests/ --pdb

# Run with verbose output
python -m pytest tests/ -vvv -s

# Run only failed tests from last run
python -m pytest tests/ --lf

# Run tests and stop on first failure
python -m pytest tests/ -x
```

## Conclusion

This workflow ensures that test validation is integrated throughout the development process, from initial planning to deployment. By following these procedures, teams can maintain high code quality, prevent regressions, and deliver reliable software.

Regular review and updates of this workflow ensure it remains effective as the project and team evolve.