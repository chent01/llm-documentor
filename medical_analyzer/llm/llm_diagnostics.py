#!/usr/bin/env python3
"""
Comprehensive LLM backend diagnostics and debugging tool.

This script provides detailed diagnostics for local LLM backends,
including connection testing, performance analysis, and configuration validation.
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

import requests

# Add the parent directory to the path so we can import medical_analyzer modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_analyzer.llm.debug_config import LLMDebugConfig, create_llm_debug_session
from medical_analyzer.llm.backend import LLMBackend
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.llm.llama_cpp_backend import LlamaCppBackend
from medical_analyzer.llm.operation_configs import get_operation_params
from medical_analyzer.llm.config import LLMConfig


class LLMDiagnostics:
    """Comprehensive LLM backend diagnostics."""
    
    def __init__(self, debug_session: Optional[str] = None):
        """
        Initialize diagnostics.
        
        Args:
            debug_session: Optional debug session name for detailed logging
        """
        self.debug_session = debug_session
        self.debug_config = None
        
        if debug_session:
            session_dir = create_llm_debug_session(debug_session)
            print(f"🔍 Debug session '{debug_session}' started")
            print(f"📁 Logs will be saved to: {session_dir}")
        else:
            self.debug_config = LLMDebugConfig({'debug_level': 'INFO'})
            self.debug_config.setup_llm_logging()
        
        self.logger = logging.getLogger('medical_analyzer.llm.diagnostics')
        self.results = {}
    
    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics on all LLM backends."""
        print("🏥 Medical Analyzer - LLM Backend Diagnostics")
        print("=" * 60)
        
        self.logger.info("Starting comprehensive LLM diagnostics")
        
        # Test 1: Configuration validation
        print("\n1. 📋 Configuration Validation")
        config_results = self.test_configuration()
        self.results['configuration'] = config_results
        
        # Test 2: Local server detection and testing
        print("\n2. 🔍 Local Server Detection")
        server_results = self.test_local_servers()
        self.results['local_servers'] = server_results
        
        # Test 3: LlamaCpp backend testing
        print("\n3. 🦙 LlamaCpp Backend Testing")
        llamacpp_results = self.test_llamacpp_backend()
        self.results['llamacpp'] = llamacpp_results
        
        # Test 4: Backend integration testing
        print("\n4. 🔗 Backend Integration Testing")
        integration_results = self.test_backend_integration()
        self.results['integration'] = integration_results
        
        # Test 5: Performance benchmarking
        print("\n5. ⚡ Performance Benchmarking")
        performance_results = self.test_performance()
        self.results['performance'] = performance_results
        
        # Generate summary report
        print("\n6. 📊 Summary Report")
        self.generate_summary_report()
        
        return self.results
    
    def test_configuration(self) -> Dict[str, Any]:
        """Test LLM configuration validation."""
        results = {'status': 'unknown', 'details': {}}
        
        try:
            # Test loading default configuration
            config = LLMConfig.get_default_config()
            results['details']['default_config'] = 'loaded'
            
            # Test configuration validation
            validation_errors = config.get_validation_errors()
            if validation_errors:
                results['status'] = 'warning'
                results['details']['validation_errors'] = validation_errors
                print(f"   ⚠️  Configuration warnings: {len(validation_errors)}")
                for error in validation_errors:
                    print(f"      • {error}")
            else:
                results['status'] = 'success'
                results['details']['validation'] = 'passed'
                print("   ✅ Configuration validation passed")
            
            # Test enabled backends
            enabled_backends = config.get_enabled_backends()
            results['details']['enabled_backends'] = [b.name for b in enabled_backends]
            print(f"   📋 Enabled backends: {', '.join(b.name for b in enabled_backends)}")
            
            # Test configuration file loading
            try:
                from medical_analyzer.llm.config import get_config_path, load_config
                config_path = get_config_path()
                if Path(config_path).exists():
                    file_config = load_config()
                    results['details']['config_file'] = 'loaded'
                    print(f"   📄 Configuration file loaded: {config_path}")
                else:
                    results['details']['config_file'] = 'not_found'
                    print(f"   📄 No configuration file found at: {config_path}")
            except Exception as e:
                results['details']['config_file_error'] = str(e)
                print(f"   ❌ Configuration file error: {e}")
            
        except Exception as e:
            results['status'] = 'error'
            results['details']['error'] = str(e)
            print(f"   ❌ Configuration test failed: {e}")
            self.logger.error(f"Configuration test error: {traceback.format_exc()}")
        
        return results
    
    def test_local_servers(self) -> Dict[str, Any]:
        """Test local LLM server detection and connectivity."""
        results = {'status': 'unknown', 'servers': {}}
        
        # Common LLM server ports and descriptions
        common_ports = [
            (1234, "LM Studio default"),
            (8000, "FastAPI/Uvicorn default"),
            (8080, "Alternative web server"),
            (5000, "Flask default"),
            (3000, "Node.js default"),
            (7860, "Gradio default"),
            (11434, "Ollama default"),
            (8001, "Alternative API server"),
            (9000, "Alternative server")
        ]
        
        working_servers = []
        
        for port, description in common_ports:
            server_result = self.test_server_on_port(port, description)
            results['servers'][port] = server_result
            
            if server_result['status'] == 'working':
                working_servers.append((port, description))
        
        if working_servers:
            results['status'] = 'success'
            print(f"   ✅ Found {len(working_servers)} working server(s)")
            for port, desc in working_servers:
                print(f"      • Port {port}: {desc}")
        else:
            results['status'] = 'no_servers'
            print("   ❌ No working LLM servers detected")
            print("   💡 Try running LM Studio or another local LLM server")
        
        return results
    
    def test_server_on_port(self, port: int, description: str) -> Dict[str, Any]:
        """Test a specific server port for LLM compatibility."""
        result = {'status': 'unknown', 'port': port, 'description': description, 'endpoints': {}}
        
        base_url = f"http://localhost:{port}"
        
        # Test connectivity
        try:
            response = requests.get(base_url, timeout=3)
            result['connectivity'] = 'success'
        except requests.exceptions.ConnectionError:
            result['status'] = 'not_running'
            result['connectivity'] = 'connection_refused'
            return result
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['connectivity'] = 'timeout'
            return result
        except Exception as e:
            result['status'] = 'error'
            result['connectivity'] = str(e)
            return result
        
        # Test LLM-specific endpoints
        test_endpoints = [
            ("/v1/models", "GET", None),
            ("/v1/chat/completions", "POST", {
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }),
            ("/v1/completions", "POST", {
                "prompt": "test",
                "max_tokens": 5
            })
        ]
        
        working_endpoints = []
        
        for endpoint, method, data in test_endpoints:
            endpoint_result = self.test_endpoint(base_url, endpoint, method, data)
            result['endpoints'][endpoint] = endpoint_result
            
            if endpoint_result['status'] == 'success':
                working_endpoints.append(endpoint)
        
        if working_endpoints:
            result['status'] = 'working'
            result['working_endpoints'] = working_endpoints
        else:
            result['status'] = 'not_llm_server'
        
        return result
    
    def test_endpoint(self, base_url: str, endpoint: str, method: str, data: Optional[Dict]) -> Dict[str, Any]:
        """Test a specific API endpoint."""
        result = {'status': 'unknown', 'method': method}
        
        try:
            url = urljoin(base_url, endpoint)
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
            
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['status'] = 'success'
                try:
                    response_data = response.json()
                    if endpoint == "/v1/models" and "data" in response_data:
                        models = [model.get("id", "unknown") for model in response_data["data"]]
                        result['models'] = models
                    elif "choices" in response_data:
                        result['response_type'] = 'completion'
                except:
                    result['response_type'] = 'non_json'
            elif response.status_code < 500:
                result['status'] = 'client_error'
            else:
                result['status'] = 'server_error'
        
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def test_llamacpp_backend(self) -> Dict[str, Any]:
        """Test LlamaCpp backend availability and functionality."""
        results = {'status': 'unknown', 'details': {}}
        
        try:
            # Test llama-cpp-python import
            try:
                import llama_cpp
                results['details']['llama_cpp_available'] = True
                results['details']['llama_cpp_version'] = getattr(llama_cpp, '__version__', 'unknown')
                print("   ✅ llama-cpp-python is available")
            except ImportError:
                results['status'] = 'not_available'
                results['details']['llama_cpp_available'] = False
                print("   ❌ llama-cpp-python not installed")
                print("   💡 Install with: pip install llama-cpp-python")
                return results
            
            # Test backend creation with minimal config
            test_config = {
                'model_path': '',  # Empty path for testing
                'debug_enabled': True
            }
            
            try:
                backend = LlamaCppBackend(test_config)
                results['details']['backend_creation'] = 'success'
                
                # Test availability (should be False without model)
                available = backend.is_available()
                results['details']['availability'] = available
                
                if available:
                    results['status'] = 'working'
                    print("   ✅ LlamaCpp backend is working")
                    
                    # Test model info
                    try:
                        model_info = backend.get_model_info()
                        results['details']['model_info'] = model_info.__dict__
                        print(f"   📋 Model: {model_info.name}")
                    except Exception as e:
                        results['details']['model_info_error'] = str(e)
                else:
                    results['status'] = 'no_model'
                    print("   ⚠️  LlamaCpp backend available but no model loaded")
                    print("   💡 Configure a model path to use LlamaCpp backend")
                
            except Exception as e:
                results['status'] = 'error'
                results['details']['backend_error'] = str(e)
                print(f"   ❌ LlamaCpp backend error: {e}")
        
        except Exception as e:
            results['status'] = 'error'
            results['details']['error'] = str(e)
            print(f"   ❌ LlamaCpp test failed: {e}")
            self.logger.error(f"LlamaCpp test error: {traceback.format_exc()}")
        
        return results
    
    def test_backend_integration(self) -> Dict[str, Any]:
        """Test backend integration with the main system."""
        results = {'status': 'unknown', 'backends': {}}
        
        # Test LocalServerBackend with detected servers
        if 'local_servers' in self.results:
            working_servers = [
                port for port, server_data in self.results['local_servers']['servers'].items()
                if server_data.get('status') == 'working'
            ]
            
            for port in working_servers:
                backend_result = self.test_local_server_backend(port)
                results['backends'][f'local_server_{port}'] = backend_result
        
        # Test LlamaCpp backend if available
        if self.results.get('llamacpp', {}).get('details', {}).get('llama_cpp_available'):
            backend_result = self.test_llamacpp_integration()
            results['backends']['llamacpp'] = backend_result
        
        # Determine overall status
        working_backends = [
            name for name, data in results['backends'].items()
            if data.get('status') == 'working'
        ]
        
        if working_backends:
            results['status'] = 'success'
            print(f"   ✅ {len(working_backends)} backend(s) working")
        else:
            results['status'] = 'no_working_backends'
            print("   ❌ No working backends found")
        
        return results
    
    def test_local_server_backend(self, port: int) -> Dict[str, Any]:
        """Test LocalServerBackend integration."""
        result = {'status': 'unknown', 'port': port}
        
        try:
            config = {
                'base_url': f'http://localhost:{port}',
                'timeout': 10,
                'debug_enabled': True,
                'log_requests': True,
                'log_responses': True
            }
            
            backend = LocalServerBackend(config)
            
            # Test availability
            available = backend.is_available()
            result['available'] = available
            
            if available:
                # Test simple generation
                try:
                    params = get_operation_params("diagnostic_test")
                    response = backend.generate(
                        prompt="Say 'Hello' and nothing else.",
                        **params
                    )
                    result['status'] = 'working'
                    result['test_response'] = response[:50]  # First 50 chars
                    print(f"      ✅ Port {port}: Working (response: '{response[:30]}...')")
                except Exception as e:
                    result['status'] = 'generation_error'
                    result['error'] = str(e)
                    print(f"      ⚠️  Port {port}: Available but generation failed: {e}")
            else:
                result['status'] = 'not_available'
                print(f"      ❌ Port {port}: Backend not available")
        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"      ❌ Port {port}: Backend error: {e}")
        
        return result
    
    def test_llamacpp_integration(self) -> Dict[str, Any]:
        """Test LlamaCpp backend integration."""
        result = {'status': 'unknown'}
        
        # This would require a model file, so we'll just test the interface
        try:
            config = {
                'model_path': '/nonexistent/model.gguf',  # Intentionally invalid
                'debug_enabled': True
            }
            
            backend = LlamaCppBackend(config)
            result['backend_created'] = True
            
            # Test availability (should be False)
            available = backend.is_available()
            result['available'] = available
            
            if not available:
                result['status'] = 'no_model'
                print("      ⚠️  LlamaCpp: Interface working but no model configured")
            else:
                result['status'] = 'working'
                print("      ✅ LlamaCpp: Working with configured model")
        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"      ❌ LlamaCpp: Integration error: {e}")
        
        return result
    
    def test_performance(self) -> Dict[str, Any]:
        """Test performance of available backends."""
        results = {'status': 'unknown', 'benchmarks': {}}
        
        # Only test backends that are working
        working_backends = []
        if 'integration' in self.results:
            for name, data in self.results['integration']['backends'].items():
                if data.get('status') == 'working':
                    working_backends.append((name, data))
        
        if not working_backends:
            results['status'] = 'no_backends'
            print("   ❌ No working backends to benchmark")
            return results
        
        print(f"   🏃 Benchmarking {len(working_backends)} backend(s)")
        
        for backend_name, backend_data in working_backends:
            benchmark_result = self.benchmark_backend(backend_name, backend_data)
            results['benchmarks'][backend_name] = benchmark_result
        
        results['status'] = 'completed'
        return results
    
    def benchmark_backend(self, backend_name: str, backend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark a specific backend."""
        result = {'status': 'unknown', 'metrics': {}}
        
        try:
            # Recreate backend for testing
            if 'local_server' in backend_name:
                port = backend_data['port']
                config = {
                    'base_url': f'http://localhost:{port}',
                    'timeout': 30,
                    'debug_enabled': False  # Reduce logging noise during benchmark
                }
                backend = LocalServerBackend(config)
            else:
                # Skip LlamaCpp benchmarking without a real model
                result['status'] = 'skipped'
                result['reason'] = 'no_model_configured'
                return result
            
            # Simple performance test
            test_prompt = "Generate a short response about artificial intelligence."
            
            start_time = time.time()
            params = get_operation_params("diagnostic_test")
            response = backend.generate(
                prompt=test_prompt,
                **params
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            response_length = len(response)
            
            result['metrics'] = {
                'response_time': response_time,
                'response_length': response_length,
                'chars_per_second': response_length / response_time if response_time > 0 else 0
            }
            result['status'] = 'completed'
            
            print(f"      📊 {backend_name}: {response_time:.2f}s, {response_length} chars, "
                  f"{result['metrics']['chars_per_second']:.1f} chars/s")
        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"      ❌ {backend_name}: Benchmark failed: {e}")
        
        return result
    
    def generate_summary_report(self) -> None:
        """Generate a comprehensive summary report."""
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC SUMMARY REPORT")
        print("=" * 60)
        
        # Configuration summary
        config_status = self.results.get('configuration', {}).get('status', 'unknown')
        print(f"\n📋 Configuration: {self._status_emoji(config_status)} {config_status.upper()}")
        
        # Server detection summary
        servers = self.results.get('local_servers', {}).get('servers', {})
        working_servers = [p for p, d in servers.items() if d.get('status') == 'working']
        print(f"🔍 Local Servers: {len(working_servers)} working out of {len(servers)} tested")
        
        # Backend summary
        backends = self.results.get('integration', {}).get('backends', {})
        working_backends = [n for n, d in backends.items() if d.get('status') == 'working']
        print(f"🔗 Backend Integration: {len(working_backends)} working backends")
        
        # Performance summary
        benchmarks = self.results.get('performance', {}).get('benchmarks', {})
        completed_benchmarks = [n for n, d in benchmarks.items() if d.get('status') == 'completed']
        print(f"⚡ Performance: {len(completed_benchmarks)} backends benchmarked")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if not working_servers:
            print("   • Install and start LM Studio or another local LLM server")
            print("   • Run 'python diagnose_lm_studio.py' for LM Studio setup help")
        
        if not working_backends:
            print("   • Check server configuration and connectivity")
            print("   • Verify API endpoints are working correctly")
        
        llamacpp_available = self.results.get('llamacpp', {}).get('details', {}).get('llama_cpp_available', False)
        if not llamacpp_available:
            print("   • Install llama-cpp-python for local model support: pip install llama-cpp-python")
        
        # Save detailed report
        if self.debug_session:
            report_path = Path.home() / '.medical_analyzer' / 'logs' / f'diagnostic_report_{self.debug_session}.json'
        else:
            report_path = Path.home() / '.medical_analyzer' / 'logs' / 'diagnostic_report.json'
        
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
    
    def _status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        emoji_map = {
            'success': '✅',
            'working': '✅',
            'completed': '✅',
            'warning': '⚠️',
            'no_servers': '❌',
            'no_backends': '❌',
            'not_available': '❌',
            'error': '❌',
            'unknown': '❓'
        }
        return emoji_map.get(status, '❓')


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='LLM Backend Diagnostics Tool')
    parser.add_argument('--debug-session', type=str, help='Create a debug session with detailed logging')
    parser.add_argument('--quick', action='store_true', help='Run quick diagnostics (skip performance tests)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set up diagnostics
    diagnostics = LLMDiagnostics(debug_session=args.debug_session)
    
    try:
        if args.quick:
            # Run quick diagnostics (skip performance tests)
            print("🏥 Medical Analyzer - Quick LLM Diagnostics")
            print("=" * 50)
            
            diagnostics.test_configuration()
            diagnostics.test_local_servers()
            diagnostics.test_llamacpp_backend()
            diagnostics.test_backend_integration()
            
            print("\n📊 Quick diagnostics completed")
        else:
            # Run full diagnostics
            results = diagnostics.run_full_diagnostics()
        
        print("\n✅ Diagnostics completed successfully")
        
    except KeyboardInterrupt:
        print("\n⏹️  Diagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Diagnostics failed: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()