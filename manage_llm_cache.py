#!/usr/bin/env python3
"""
Utility script for managing LLM query cache and project analysis cache.

This script provides commands to view, clear, and manage both types of caches:
- LLM query cache (individual API call responses)
- Project analysis cache (complete analysis results)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.llm.query_cache import LLMQueryCache, get_global_cache
from medical_analyzer.services.project_persistence import ProjectPersistenceService
from medical_analyzer.database.schema import DatabaseManager


def format_bytes(bytes_value):
    """Format bytes in human readable format."""
    if bytes_value is None:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} TB"


def format_duration(seconds):
    """Format duration in human readable format."""
    if seconds is None:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def show_llm_cache_stats():
    """Show LLM query cache statistics."""
    print("=== LLM Query Cache Statistics ===")
    
    try:
        cache = get_global_cache()
        stats = cache.get_statistics()
        
        if 'error' in stats:
            print(f"Error getting cache stats: {stats['error']}")
            return
        
        print(f"Hit Rate: {stats['hit_rate_percent']:.1f}%")
        print(f"Total Queries: {stats['total_queries']:,}")
        print(f"Cache Hits: {stats['cache_hits']:,}")
        print(f"Cache Misses: {stats['cache_misses']:,}")
        print(f"Evictions: {stats['evictions']:,}")
        print(f"")
        print(f"Cache Size: {format_bytes(stats['total_size_bytes'])} ({stats['total_size_mb']:.1f} MB)")
        print(f"Entry Count: {stats['entry_count']:,} / {stats['max_entries']:,}")
        print(f"Max Size: {stats['max_size_mb']} MB")
        print(f"TTL: {stats['default_ttl_seconds']}s ({stats['default_ttl_seconds']/3600:.1f}h)")
        print(f"")
        print(f"Avg Response Time: {format_duration(stats['avg_response_time'])}")
        print(f"Avg Time Saved: {format_duration(stats['avg_response_time_saved'])}")
        print(f"Total Accesses: {stats['total_accesses']:,}")
        print(f"")
        print(f"Oldest Entry: {stats['oldest_entry'] or 'None'}")
        print(f"Newest Access: {stats['newest_access'] or 'None'}")
        
        # Calculate potential time savings
        if stats['cache_hits'] > 0 and stats['avg_response_time_saved'] > 0:
            total_time_saved = stats['cache_hits'] * stats['avg_response_time_saved']
            print(f"")
            print(f"Total Time Saved: {format_duration(total_time_saved)}")
        
    except Exception as e:
        print(f"Error accessing LLM cache: {e}")


def show_project_cache_stats():
    """Show project analysis cache statistics."""
    print("=== Project Analysis Cache Statistics ===")
    
    try:
        db_manager = DatabaseManager()
        persistence = ProjectPersistenceService(db_manager.db_path)
        
        # Get project statistics
        projects = persistence.list_projects()
        print(f"Cached Projects: {len(projects)}")
        
        if not projects:
            print("No cached projects found.")
            return
        
        print(f"")
        print("Recent Projects:")
        for i, project in enumerate(projects[:10]):  # Show top 10
            print(f"  {i+1}. {project['name']}")
            print(f"     Path: {project['root_path']}")
            print(f"     Files: {project['selected_files_count']}")
            print(f"     Last Analyzed: {project['last_analyzed'] or 'Never'}")
            
            # Get analysis runs for this project
            runs = persistence.get_project_analysis_runs(project['id'])
            completed_runs = [r for r in runs if r['status'] == 'completed']
            print(f"     Analysis Runs: {len(runs)} total, {len(completed_runs)} completed")
            print()
        
        # Calculate total analysis runs
        total_runs = 0
        completed_runs = 0
        
        for project in projects:
            runs = persistence.get_project_analysis_runs(project['id'])
            total_runs += len(runs)
            completed_runs += len([r for r in runs if r['status'] == 'completed'])
        
        print(f"Total Analysis Runs: {total_runs}")
        print(f"Completed Runs: {completed_runs}")
        print(f"Success Rate: {(completed_runs/total_runs*100):.1f}%" if total_runs > 0 else "N/A")
        
        # Check artifacts directory
        artifacts_dir = Path("analysis_artifacts")
        if artifacts_dir.exists():
            artifact_files = list(artifacts_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in artifact_files)
            print(f"")
            print(f"Analysis Artifacts: {len(artifact_files)} files")
            print(f"Artifacts Size: {format_bytes(total_size)}")
        
    except Exception as e:
        print(f"Error accessing project cache: {e}")


def clear_llm_cache(older_than_hours=None):
    """Clear LLM query cache."""
    try:
        cache = get_global_cache()
        
        if older_than_hours:
            print(f"Clearing LLM cache entries older than {older_than_hours} hours...")
            cache.clear(older_than_hours)
            print("LLM cache cleared (old entries only).")
        else:
            print("Clearing entire LLM cache...")
            cache.clear()
            print("LLM cache cleared completely.")
            
    except Exception as e:
        print(f"Error clearing LLM cache: {e}")


def clear_project_cache(older_than_days=None):
    """Clear project analysis cache."""
    try:
        db_manager = DatabaseManager()
        persistence = ProjectPersistenceService(db_manager.db_path)
        
        if older_than_days:
            print(f"Clearing project cache entries older than {older_than_days} days...")
            
            # Get projects to remove
            projects = persistence.list_projects()
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            removed_count = 0
            for project in projects:
                if project['last_analyzed']:
                    last_analyzed = datetime.fromisoformat(project['last_analyzed'].replace(' ', 'T'))
                    if last_analyzed < cutoff_date:
                        persistence.delete_project(project['id'])
                        removed_count += 1
            
            print(f"Removed {removed_count} old project cache entries.")
        else:
            print("Clearing entire project cache...")
            
            # Remove all projects
            projects = persistence.list_projects()
            for project in projects:
                persistence.delete_project(project['id'])
            
            print(f"Removed {len(projects)} project cache entries.")
        
        # Clean up artifacts directory
        artifacts_dir = Path("analysis_artifacts")
        if artifacts_dir.exists():
            if older_than_days:
                cutoff_time = datetime.now() - timedelta(days=older_than_days)
                removed_files = 0
                
                for artifact_file in artifacts_dir.glob("*.json"):
                    file_time = datetime.fromtimestamp(artifact_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        artifact_file.unlink()
                        removed_files += 1
                
                print(f"Removed {removed_files} old artifact files.")
            else:
                artifact_files = list(artifacts_dir.glob("*.json"))
                for artifact_file in artifact_files:
                    artifact_file.unlink()
                
                print(f"Removed {len(artifact_files)} artifact files.")
        
    except Exception as e:
        print(f"Error clearing project cache: {e}")


def optimize_caches():
    """Optimize both caches by removing old/unused entries."""
    print("=== Cache Optimization ===")
    
    # Optimize LLM cache (remove entries older than 24 hours)
    print("Optimizing LLM cache...")
    try:
        cache = get_global_cache()
        cache.clear(older_than_hours=24)
        print("✓ LLM cache optimized (removed entries older than 24 hours)")
    except Exception as e:
        print(f"✗ LLM cache optimization failed: {e}")
    
    # Optimize project cache (remove entries older than 30 days)
    print("Optimizing project cache...")
    try:
        clear_project_cache(older_than_days=30)
        print("✓ Project cache optimized (removed entries older than 30 days)")
    except Exception as e:
        print(f"✗ Project cache optimization failed: {e}")
    
    print("Cache optimization completed.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage LLM query cache and project analysis cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_llm_cache.py stats                    # Show cache statistics
  python manage_llm_cache.py clear-llm               # Clear LLM cache
  python manage_llm_cache.py clear-llm --hours 24    # Clear LLM cache older than 24h
  python manage_llm_cache.py clear-project           # Clear project cache
  python manage_llm_cache.py clear-project --days 7  # Clear project cache older than 7 days
  python manage_llm_cache.py clear-all               # Clear both caches
  python manage_llm_cache.py optimize                # Optimize both caches
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show cache statistics')
    stats_parser.add_argument('--llm-only', action='store_true', help='Show only LLM cache stats')
    stats_parser.add_argument('--project-only', action='store_true', help='Show only project cache stats')
    
    # Clear LLM cache command
    clear_llm_parser = subparsers.add_parser('clear-llm', help='Clear LLM query cache')
    clear_llm_parser.add_argument('--hours', type=int, help='Only clear entries older than N hours')
    
    # Clear project cache command
    clear_project_parser = subparsers.add_parser('clear-project', help='Clear project analysis cache')
    clear_project_parser.add_argument('--days', type=int, help='Only clear entries older than N days')
    
    # Clear all caches command
    subparsers.add_parser('clear-all', help='Clear both LLM and project caches')
    
    # Optimize command
    subparsers.add_parser('optimize', help='Optimize both caches by removing old entries')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'stats':
        if args.project_only:
            show_project_cache_stats()
        elif args.llm_only:
            show_llm_cache_stats()
        else:
            show_llm_cache_stats()
            print()
            show_project_cache_stats()
    
    elif args.command == 'clear-llm':
        clear_llm_cache(args.hours)
    
    elif args.command == 'clear-project':
        clear_project_cache(args.days)
    
    elif args.command == 'clear-all':
        clear_llm_cache()
        clear_project_cache()
    
    elif args.command == 'optimize':
        optimize_caches()


if __name__ == "__main__":
    main()