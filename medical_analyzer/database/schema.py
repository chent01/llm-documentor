"""
SQLite database schema and management for the Medical Software Analysis Tool.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class DatabaseManager:
    """Manages SQLite database operations for the analysis tool."""
    
    def __init__(self, db_path: str = "medical_analyzer.db"):
        """Initialize database manager with path to SQLite database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    description TEXT,
                    metadata TEXT,  -- JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_analyzed TIMESTAMP
                )
            """)
            
            # Analysis runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
                    artifacts_path TEXT,
                    error_message TEXT,
                    metadata TEXT,  -- JSON string
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Traceability links table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traceability_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_run_id INTEGER NOT NULL,
                    source_type TEXT NOT NULL,  -- code, feature, requirement, risk
                    source_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    link_type TEXT NOT NULL,  -- implements, derives_from, mitigates, etc.
                    confidence REAL DEFAULT 1.0,
                    metadata TEXT,  -- JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_root_path 
                ON projects(root_path)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_runs_project_id 
                ON analysis_runs(project_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_traceability_source 
                ON traceability_links(source_type, source_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_traceability_target 
                ON traceability_links(target_type, target_id)
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def create_project(self, name: str, root_path: str, description: str = "", 
                      metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create a new project record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (name, root_path, description, metadata)
                VALUES (?, ?, ?, ?)
            """, (name, root_path, description, json.dumps(metadata or {})))
            conn.commit()
            return cursor.lastrowid
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                project = dict(row)
                project['metadata'] = json.loads(project['metadata'] or '{}')
                return project
            return None
    
    def get_project_by_path(self, root_path: str) -> Optional[Dict[str, Any]]:
        """Get project by root path."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE root_path = ?", (root_path,))
            row = cursor.fetchone()
            if row:
                project = dict(row)
                project['metadata'] = json.loads(project['metadata'] or '{}')
                return project
            return None
    
    def create_analysis_run(self, project_id: int, artifacts_path: str = "", 
                           metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create a new analysis run record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_runs (project_id, artifacts_path, metadata)
                VALUES (?, ?, ?)
            """, (project_id, artifacts_path, json.dumps(metadata or {})))
            conn.commit()
            return cursor.lastrowid
    
    def update_analysis_run_status(self, run_id: int, status: str, 
                                  error_message: str = ""):
        """Update analysis run status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE analysis_runs 
                SET status = ?, error_message = ?
                WHERE id = ?
            """, (status, error_message, run_id))
            conn.commit()
    
    def create_traceability_link(self, analysis_run_id: int, source_type: str,
                               source_id: str, target_type: str, target_id: str,
                               link_type: str, confidence: float = 1.0,
                               metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create a traceability link."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traceability_links 
                (analysis_run_id, source_type, source_id, target_type, 
                 target_id, link_type, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (analysis_run_id, source_type, source_id, target_type,
                  target_id, link_type, confidence, json.dumps(metadata or {})))
            conn.commit()
            return cursor.lastrowid
    
    def get_traceability_links(self, analysis_run_id: int) -> List[Dict[str, Any]]:
        """Get all traceability links for an analysis run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM traceability_links 
                WHERE analysis_run_id = ?
                ORDER BY created_at
            """, (analysis_run_id,))
            links = []
            for row in cursor.fetchall():
                link = dict(row)
                link['metadata'] = json.loads(link['metadata'] or '{}')
                links.append(link)
            return links


def init_database(db_path: str = "medical_analyzer.db") -> DatabaseManager:
    """Initialize and return a database manager instance."""
    return DatabaseManager(db_path)