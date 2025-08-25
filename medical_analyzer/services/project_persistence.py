"""
Project persistence service for managing ProjectStructure data with SQLite database.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..models import ProjectStructure, FileMetadata
from ..database.schema import DatabaseManager


class ProjectPersistenceService:
    """Service for persisting and retrieving ProjectStructure data."""
    
    def __init__(self, db_path: str = "medical_analyzer.db"):
        """Initialize the persistence service with database manager."""
        self.db_manager = DatabaseManager(db_path)
    
    def save_project(self, project: ProjectStructure) -> int:
        """
        Save a ProjectStructure to the database.
        
        Args:
            project: ProjectStructure instance to save
            
        Returns:
            Project ID from database
            
        Raises:
            ValueError: If project data is invalid
        """
        if not project.root_path:
            raise ValueError("Project root_path cannot be empty")
        
        if not os.path.exists(project.root_path):
            raise ValueError(f"Project root path does not exist: {project.root_path}")
        
        # Check if project already exists
        existing_project = self.db_manager.get_project_by_path(project.root_path)
        
        if existing_project:
            # Update existing project
            project_id = existing_project['id']
            self._update_project(project_id, project)
        else:
            # Create new project
            project_name = os.path.basename(project.root_path) or "Unnamed Project"
            
            # Prepare metadata including file metadata
            metadata = project.metadata.copy()
            metadata.update({
                'selected_files_count': len(project.selected_files),
                'file_metadata': [self._file_metadata_to_dict(fm) for fm in project.file_metadata],
                'timestamp': project.timestamp.isoformat(),
                'selected_files': project.selected_files
            })
            
            project_id = self.db_manager.create_project(
                name=project_name,
                root_path=project.root_path,
                description=project.description,
                metadata=metadata
            )
        
        return project_id
    
    def _update_project(self, project_id: int, project: ProjectStructure):
        """Update an existing project in the database."""
        metadata = project.metadata.copy()
        metadata.update({
            'selected_files_count': len(project.selected_files),
            'file_metadata': [self._file_metadata_to_dict(fm) for fm in project.file_metadata],
            'timestamp': project.timestamp.isoformat(),
            'selected_files': project.selected_files,
            'last_updated': datetime.now().isoformat()
        })
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects 
                SET description = ?, metadata = ?, last_analyzed = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (project.description, json.dumps(metadata), project_id))
            conn.commit()
    
    def load_project(self, project_id: int) -> Optional[ProjectStructure]:
        """
        Load a ProjectStructure from the database by ID.
        
        Args:
            project_id: Database ID of the project
            
        Returns:
            ProjectStructure instance or None if not found
        """
        project_data = self.db_manager.get_project(project_id)
        if not project_data:
            return None
        
        return self._dict_to_project_structure(project_data)
    
    def load_project_by_path(self, root_path: str) -> Optional[ProjectStructure]:
        """
        Load a ProjectStructure from the database by root path.
        
        Args:
            root_path: Root path of the project
            
        Returns:
            ProjectStructure instance or None if not found
        """
        project_data = self.db_manager.get_project_by_path(root_path)
        if not project_data:
            return None
        
        return self._dict_to_project_structure(project_data)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in the database.
        
        Returns:
            List of project summary dictionaries
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, root_path, description, created_at, last_analyzed,
                       metadata
                FROM projects 
                ORDER BY last_analyzed DESC, created_at DESC
            """)
            
            projects = []
            for row in cursor.fetchall():
                project_dict = dict(row)
                metadata = json.loads(project_dict['metadata'] or '{}')
                
                project_summary = {
                    'id': project_dict['id'],
                    'name': project_dict['name'],
                    'root_path': project_dict['root_path'],
                    'description': project_dict['description'],
                    'created_at': project_dict['created_at'],
                    'last_analyzed': project_dict['last_analyzed'],
                    'selected_files_count': metadata.get('selected_files_count', 0),
                    'total_files_discovered': metadata.get('total_files_discovered', 0)
                }
                projects.append(project_summary)
            
            return projects
    
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project and all associated data.
        
        Args:
            project_id: Database ID of the project to delete
            
        Returns:
            True if project was deleted, False if not found
        """
        project = self.db_manager.get_project(project_id)
        if not project:
            return False
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def create_analysis_run(self, project_id: int, artifacts_path: str = "",
                           metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Create a new analysis run for a project.
        
        Args:
            project_id: Database ID of the project
            artifacts_path: Path to analysis artifacts
            metadata: Additional metadata for the analysis run
            
        Returns:
            Analysis run ID
        """
        return self.db_manager.create_analysis_run(project_id, artifacts_path, metadata)
    
    def get_project_analysis_runs(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all analysis runs for a project.
        
        Args:
            project_id: Database ID of the project
            
        Returns:
            List of analysis run dictionaries
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_runs 
                WHERE project_id = ?
                ORDER BY run_timestamp DESC
            """, (project_id,))
            
            runs = []
            for row in cursor.fetchall():
                run_dict = dict(row)
                run_dict['metadata'] = json.loads(run_dict['metadata'] or '{}')
                runs.append(run_dict)
            
            return runs
    
    def validate_project_structure(self, project: ProjectStructure) -> List[str]:
        """
        Validate a ProjectStructure for consistency and completeness.
        
        Args:
            project: ProjectStructure to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not project.root_path:
            errors.append("Root path is required")
        elif not os.path.exists(project.root_path):
            errors.append(f"Root path does not exist: {project.root_path}")
        elif not os.path.isdir(project.root_path):
            errors.append(f"Root path is not a directory: {project.root_path}")
        
        # Check selected files
        if not project.selected_files:
            errors.append("No files selected for analysis")
        else:
            for file_path in project.selected_files:
                if not os.path.exists(file_path):
                    errors.append(f"Selected file does not exist: {file_path}")
                elif not os.path.isfile(file_path):
                    errors.append(f"Selected path is not a file: {file_path}")
        
        # Check file metadata consistency
        if len(project.file_metadata) != len(project.selected_files):
            errors.append(
                f"File metadata count ({len(project.file_metadata)}) "
                f"does not match selected files count ({len(project.selected_files)})"
            )
        
        # Validate file metadata
        for i, metadata in enumerate(project.file_metadata):
            if not isinstance(metadata, FileMetadata):
                errors.append(f"File metadata at index {i} is not a FileMetadata instance")
                continue
            
            if not metadata.file_path:
                errors.append(f"File metadata at index {i} has empty file_path")
            elif metadata.file_path not in project.selected_files:
                errors.append(
                    f"File metadata path '{metadata.file_path}' not in selected files"
                )
        
        return errors
    
    def _file_metadata_to_dict(self, metadata: FileMetadata) -> Dict[str, Any]:
        """Convert FileMetadata to dictionary for JSON serialization."""
        return {
            'file_path': metadata.file_path,
            'file_size': metadata.file_size,
            'last_modified': metadata.last_modified.isoformat(),
            'file_type': metadata.file_type,
            'encoding': metadata.encoding,
            'line_count': metadata.line_count,
            'function_count': metadata.function_count
        }
    
    def _dict_to_file_metadata(self, data: Dict[str, Any]) -> FileMetadata:
        """Convert dictionary to FileMetadata instance."""
        return FileMetadata(
            file_path=data['file_path'],
            file_size=data['file_size'],
            last_modified=datetime.fromisoformat(data['last_modified']),
            file_type=data['file_type'],
            encoding=data['encoding'],
            line_count=data['line_count'],
            function_count=data['function_count']
        )
    
    def _dict_to_project_structure(self, data: Dict[str, Any]) -> ProjectStructure:
        """Convert database row dictionary to ProjectStructure."""
        metadata = data['metadata']
        
        # Extract file metadata
        file_metadata = []
        if 'file_metadata' in metadata:
            file_metadata = [
                self._dict_to_file_metadata(fm_data) 
                for fm_data in metadata['file_metadata']
            ]
        
        # Extract selected files
        selected_files = metadata.get('selected_files', [])
        
        # Extract timestamp
        timestamp = datetime.now()
        if 'timestamp' in metadata:
            try:
                timestamp = datetime.fromisoformat(metadata['timestamp'])
            except (ValueError, TypeError):
                pass
        
        # Create base metadata without internal fields
        base_metadata = {k: v for k, v in metadata.items() 
                        if k not in ['file_metadata', 'selected_files', 'timestamp']}
        
        return ProjectStructure(
            root_path=data['root_path'],
            selected_files=selected_files,
            description=data['description'] or "",
            metadata=base_metadata,
            timestamp=timestamp,
            file_metadata=file_metadata
        )