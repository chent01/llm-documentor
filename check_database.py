#!/usr/bin/env python3
"""
Script to check the database for cached analysis results.
"""

import sqlite3
import json
from pathlib import Path

def check_database():
    db_path = "medical_analyzer.db"
    
    if not Path(db_path).exists():
        print("Database file does not exist")
        return
    
    print(f"Database file exists: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTables in database: {[table[0] for table in tables]}")
        
        # Check projects
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        project_count = cursor.fetchone()[0]
        print(f"\nProjects in database: {project_count}")
        
        if project_count > 0:
            cursor.execute("SELECT id, name, root_path, last_analyzed FROM projects ORDER BY last_analyzed DESC")
            projects = cursor.fetchall()
            print("\nProjects:")
            for project in projects:
                print(f"  ID: {project['id']}, Name: {project['name']}")
                print(f"      Path: {project['root_path']}")
                print(f"      Last analyzed: {project['last_analyzed']}")
        
        # Check analysis runs
        cursor.execute("SELECT COUNT(*) as count FROM analysis_runs")
        run_count = cursor.fetchone()[0]
        print(f"\nAnalysis runs in database: {run_count}")
        
        if run_count > 0:
            cursor.execute("""
                SELECT ar.id, ar.project_id, ar.status, ar.run_timestamp, p.name as project_name
                FROM analysis_runs ar
                JOIN projects p ON ar.project_id = p.id
                ORDER BY ar.run_timestamp DESC
                LIMIT 10
            """)
            runs = cursor.fetchall()
            print("\nRecent analysis runs:")
            for run in runs:
                print(f"  Run ID: {run['id']}, Project: {run['project_name']}")
                print(f"      Status: {run['status']}, Time: {run['run_timestamp']}")
        
        # Check traceability links
        cursor.execute("SELECT COUNT(*) as count FROM traceability_links")
        link_count = cursor.fetchone()[0]
        print(f"\nTraceability links in database: {link_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database()