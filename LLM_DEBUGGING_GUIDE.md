# LLM Backend Debugging and Logging Guide

This guide explains the comprehensive debugging and logging capabilities added to the Medical Analyzer's LLM backends, especially for local LLM servers.

## 🔍 Overview

The enhanced debugging system provides detailed logging and diagnostics for:
- **Connection issues** with local LLM servers
- **Performance monitoring** and bottleneck identification
- **Request/response tracking** for API calls
- **Model loading and initialization** problems
- **Error analysis** with actionable recommendations

## 🚀 Quick Start

### Enable Basic Debugging
```bash
# Enable standard debugging
python enable_llm_debugging.py --level INFO

# Enable verbose debugging (all details)
python enable_llm_debugging.py --verbose

# Enable only performance monitoring
python enable_llm_debugging.py --performance-only
```

### Run Comprehensive Diagnostics
```bash
# Full diagnostic suite
python medical_analyzer/llm/llm_diagnostics.py

# Quick diagnostics (skip performance tests)
python medical_analyzer/llm/llm_diagnostics.py --quick

# Create debug session with detailed logging
python medical_analyzer/llm/llm_diagnostics.py --debug-session troubleshooting
```

### Legacy LM Studio Diagnostics
```bash
# Simple LM Studio connection test
python diagnose_lm_studio.py

# Detailed connection test
python test_lm_studio_connection.py
```

## 📊 Logging Categories

### 1. Connection Logging
Tracks connectivity to local LLM servers:
- Server availability checks
- Port scanning and detection
- Connection health monitoring
- DNS and network issues

**Log file**: `llm_connections.log`

### 2. Performance Logging
Monitors performance metrics:
- Response times and throughput
- Token generation rates
- Memory usage patterns
- Slow request identification

**Log file**: `llm_performance.log`

### 3. Request/Response Logging
Detailed API interaction tracking:
- Request parameters and payloads
- Response content and metadata
- Token usage statistics
- API endpoint testing

**Log files**: `llm_requests.log`, `llm_responses.log`

### 4. Model Operations Logging
LlamaCpp-specific model operations:
- Model loading and initialization
- Generation parameters
- Token estimation and chunking
- GPU/CPU usage patterns

**Log file**: `llm_generation.log`

### 5. Error Logging
Comprehensive error tracking:
- Connection failures with diagnostics
- API errors with recovery suggestions
- Model loading issues
- Configuration problems

**Log file**: `llm_errors.log`

## 🛠️ Configuration Options

### Debug Configuration File
Create `~/.medical_analyzer/debug_config.json`:

```json
{
  "debug_level": "DEBUG",
  "enable_file_logging": true,
  "enable_console_logging": true,
  "log_requests": true,
  "log_responses": true,
  "log_connections": true,
  "log_performance": true,
  "log_model_operations": true,
  "log_errors": true,
  "max_log_size": 10485760,
  "backup_count": 5,
  "slow_request_threshold": 5.0
}
```

### Environment Variables
```bash
# Enable debugging via environment
export MEDICAL_ANALYZER_DEBUG=true
export MEDICAL_ANALYZER_LOG_LEVEL=DEBUG
export MEDICAL_ANALYZER_LOG_REQUESTS=true
```

### Programmatic Configuration
```python
from medical_analyzer.llm.debug_config import LLMDebugConfig

# Create custom debug configuration
config = {
    'debug_level': 'DEBUG',
    'log_connections': True,
    'log_performance': True,
    'log_requests': True
}

debug_config = LLMDebugConfig(config)
debug_config.setup_llm_logging()
```

## 🔧 Debug Sessions

Debug sessions create isolated logging environments with timestamps:

```bash
# Create a debug session
python enable_llm_debugging.py --session connection_issues

# Run diagnostics in the session
python medical_analyzer/llm/llm_diagnostics.py --debug-session connection_issues
```

Session logs are saved to:
`~/.medical_analyzer/logs/debug_session_connection_issues_20241202_143022/`

## 📈 Performance Monitoring

### Real-time Performance Metrics
The system tracks:
- **Response times**: Average, min, max response times
- **Throughput**: Tokens per second, characters per second
- **Success rates**: Request success/failure ratios
- **Cache performance**: Hit rates and efficiency
- **Connection health**: Consecutive failures, uptime

### Performance Alerts
Automatic warnings for:
- Slow responses (>5 seconds by default)
- High failure rates (>10%)
- Connection instability
- Memory usage issues

### Example Performance Log
```
2024-12-02 14:30:22 - INFO - [REQ-0001] Response received in 2.34s - Status: 200
2024-12-02 14:30:22 - INFO - [REQ-0001] Generated 156 characters in 1 choices
2024-12-02 14:30:22 - INFO - [REQ-0001] Token usage: 45 prompt + 38 completion = 83 total
2024-12-02 14:30:22 - INFO - [REQ-0001] Success - Generated 156 characters in 2.34s
2024-12-02 14:30:22 - INFO - Performance Summary - Requests: 10 (✅ 9, ❌ 1), Success Rate: 90.0%, Avg Response Time: 2.12s
```

## 🚨 Troubleshooting Common Issues

### Connection Refused Errors
```bash
# Check if server is running
python diagnose_lm_studio.py

# Enable connection debugging
python enable_llm_debugging.py --connections

# Check logs
tail -f ~/.medical_analyzer/logs/llm_connections.log
```

### Slow Response Times
```bash
# Enable performance monitoring
python enable_llm_debugging.py --performance-only

# Run performance benchmark
python medical_analyzer/llm/llm_diagnostics.py
```

### Model Loading Issues (LlamaCpp)
```bash
# Enable model operation logging
python enable_llm_debugging.py --verbose

# Check model logs
tail -f ~/.medical_analyzer/logs/llm_model.log
```

### API Compatibility Issues
```bash
# Test API endpoints
python test_lm_studio_connection.py

# Enable request/response logging
python enable_llm_debugging.py --requests
```

## 📁 Log File Locations

Default log directory: `~/.medical_analyzer/logs/`

### Main Log Files
- `llm_main.log` - General LLM operations
- `llm_connections.log` - Connection and server issues
- `llm_performance.log` - Performance metrics
- `llm_requests.log` - API request details
- `llm_responses.log` - API response details
- `llm_generation.log` - Text generation operations
- `llm_model.log` - Model loading and management
- `llm_errors.log` - Error tracking and analysis
- `llm_debug.log` - Detailed debug information

### Log Rotation
- Maximum file size: 10MB (configurable)
- Backup files: 5 (configurable)
- Automatic rotation when size limit reached

## 🔍 Advanced Debugging

### Request Tracing
Each request gets a unique ID for tracking:
```
[REQ-0001] Starting text_generation
[REQ-0001] Request parameters: {'prompt_length': 45, 'temperature': 0.1}
[REQ-0001] URL: http://localhost:1234/v1/chat/completions
[REQ-0001] Response received in 2.34s - Status: 200
[REQ-0001] Success - Generated 156 characters in 2.34s
```

### Performance Profiling
Detailed timing information:
```
[REQ-0001] Input tokens: 45, Available for generation: 512
[REQ-0001] Generation completed in 1.89s
[REQ-0001] Performance: 20.1 tokens/second
```

### Error Context
Rich error information:
```
[REQ-0001] Error: ConnectionError: Connection refused
[REQ-0001] Error context: {'url': 'http://localhost:1234', 'timeout': 30}
[REQ-0001] Connection failed - check if LLM server is running
```

## 🎯 Best Practices

### For Development
1. Use debug sessions for isolated testing
2. Enable verbose logging for new integrations
3. Monitor performance during development
4. Check connection logs for server issues

### For Production
1. Use INFO level logging by default
2. Enable performance monitoring
3. Set up log rotation
4. Monitor error rates and patterns

### For Troubleshooting
1. Start with comprehensive diagnostics
2. Enable relevant logging categories
3. Use debug sessions for focused investigation
4. Check both application and server logs

## 📚 API Reference

### LLMDebugConfig Class
```python
from medical_analyzer.llm.debug_config import LLMDebugConfig

# Initialize with custom config
debug_config = LLMDebugConfig(config_dict)

# Set up logging
debug_config.setup_llm_logging()

# Enable verbose debugging
debug_config.enable_verbose_debugging()

# Create debug session
session_dir = debug_config.create_debug_session("session_name")

# Get configuration summary
summary = debug_config.get_log_summary()
```

### Diagnostic Functions
```python
from medical_analyzer.llm.llm_diagnostics import LLMDiagnostics

# Run full diagnostics
diagnostics = LLMDiagnostics()
results = diagnostics.run_full_diagnostics()

# Test specific components
config_results = diagnostics.test_configuration()
server_results = diagnostics.test_local_servers()
backend_results = diagnostics.test_backend_integration()
```

## 🤝 Contributing

When adding new LLM backends or features:

1. Use the specialized loggers for appropriate categories
2. Include performance metrics in generation methods
3. Add connection health checks for server backends
4. Provide detailed error context and recovery suggestions
5. Update diagnostic tests for new functionality

## 📞 Support

For issues with LLM debugging:

1. Run comprehensive diagnostics first
2. Check relevant log files
3. Enable verbose debugging for the problematic component
4. Create a debug session for detailed investigation
5. Include log excerpts when reporting issues

The debugging system is designed to be self-documenting and provide actionable insights for resolving LLM backend issues quickly and efficiently.