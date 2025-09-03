#!/usr/bin/env python3
"""
Simple test script for cache management functionality.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from medical_analyzer.llm.query_cache import LLMQueryCache, get_global_cache
    from medical_analyzer.services.project_persistence import ProjectPersistenceService
    from medical_analyzer.database.schema import DatabaseManager
    
    print("=== Cache Management Test ===")
    
    # Test LLM cache
    print("\n--- LLM Cache Test ---")
    try:
        cache = get_global_cache()
        stats = cache.get_statistics()
        print(f"LLM Cache initialized successfully")
        print(f"Hit rate: {stats.get('hit_rate_percent', 0):.1f}%")
        print(f"Total queries: {stats.get('total_queries', 0)}")
        print(f"Cache entries: {stats.get('entry_count', 0)}")
    except Exception as e:
        print(f"LLM Cache error: {e}")
    
    # Test project cache
    print("\n--- Project Cache Test ---")
    try:
        db_manager = DatabaseManager()
        persistence = ProjectPersistenceService(db_manager.db_path)
        projects = persistence.list_projects()
        print(f"Project cache initialized successfully")
        print(f"Cached projects: {len(projects)}")
        
        for project in projects:
            print(f"  - {project['name']} (last analyzed: {project['last_analyzed']})")
    except Exception as e:
        print(f"Project Cache error: {e}")
    
    print("\n=== Test Complete ===")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()