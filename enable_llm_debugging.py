#!/usr/bin/env python3
"""
Enable comprehensive LLM debugging for the Medical Analyzer application.

This script configures detailed logging and debugging for LLM backends,
making it easier to troubleshoot connection issues and performance problems.
"""

import argparse
import sys
from pathlib import Path

# Add the medical_analyzer module to the path
sys.path.insert(0, str(Path(__file__).parent))

from medical_analyzer.llm.debug_config import (
    LLMDebugConfig, 
    enable_verbose_llm_debugging,
    create_llm_debug_session,
    quick_debug_setup
)


def main():
    """Main function for enabling LLM debugging."""
    parser = argparse.ArgumentParser(description='Enable LLM Backend Debugging')
    parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose debugging (all logging enabled)')
    parser.add_argument('--session', type=str, 
                       help='Create a debug session with timestamped logs')
    parser.add_argument('--performance-only', action='store_true',
                       help='Enable only performance and error logging')
    parser.add_argument('--requests', action='store_true',
                       help='Enable request/response logging')
    parser.add_argument('--connections', action='store_true',
                       help='Enable connection debugging')
    
    args = parser.parse_args()
    
    print("🔧 Medical Analyzer - LLM Debug Configuration")
    print("=" * 50)
    
    try:
        if args.session:
            # Create debug session
            session_dir = create_llm_debug_session(args.session)
            print(f"✅ Debug session '{args.session}' created")
            print(f"📁 Logs directory: {session_dir}")
            print("🔍 Verbose debugging enabled for this session")
            
        elif args.verbose:
            # Enable verbose debugging
            debug_config = enable_verbose_llm_debugging()
            print("✅ Verbose LLM debugging enabled")
            print("🔍 All LLM operations will be logged in detail")
            
        elif args.performance_only:
            # Performance-only logging
            debug_config = LLMDebugConfig()
            debug_config.enable_performance_only()
            print("✅ Performance-only logging enabled")
            print("📊 Only performance metrics and errors will be logged")
            
        else:
            # Custom configuration
            config = {
                'debug_level': args.level,
                'log_connections': args.connections or args.level == 'DEBUG',
                'log_performance': True,  # Always enabled
                'log_errors': True,       # Always enabled
                'log_requests': args.requests or args.level == 'DEBUG',
                'log_responses': args.requests or args.level == 'DEBUG'
            }
            
            debug_config = LLMDebugConfig(config)
            debug_config.setup_llm_debugging()
            
            print(f"✅ LLM debugging configured with level: {args.level}")
            
            enabled_features = []
            if config['log_connections']:
                enabled_features.append("connections")
            if config['log_requests']:
                enabled_features.append("requests/responses")
            if config['log_performance']:
                enabled_features.append("performance")
            
            if enabled_features:
                print(f"🔍 Enabled logging: {', '.join(enabled_features)}")
        
        # Show log directory
        log_dir = Path.home() / '.medical_analyzer' / 'logs'
        print(f"📁 Logs will be saved to: {log_dir}")
        
        # Show summary
        if not args.session:
            summary = debug_config.get_log_summary()
            print(f"\n📋 Configuration Summary:")
            print(f"   Debug Level: {summary['debug_level']}")
            print(f"   Log Directory: {summary['log_directory']}")
            print(f"   File Logging: {'✅' if summary['file_logging'] else '❌'}")
            print(f"   Console Logging: {'✅' if summary['console_logging'] else '❌'}")
        
        print(f"\n💡 Usage Tips:")
        print(f"   • Run your Medical Analyzer application normally")
        print(f"   • Check log files for detailed debugging information")
        print(f"   • Use 'python medical_analyzer/llm/llm_diagnostics.py' for comprehensive testing")
        print(f"   • Use '--session <name>' for isolated debug sessions")
        
        print(f"\n✅ LLM debugging is now enabled!")
        
    except Exception as e:
        print(f"❌ Failed to enable debugging: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()