"""
SOUP (Software of Unknown Provenance) inventory management service.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from ..models.core import SOUPComponent
from ..database.schema import DatabaseManager


class SOUPService:
    """Service for managing SOUP (Software of Unknown Provenance) components."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SOUP service.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._ensure_soup_table()
    
    def _ensure_soup_table(self):
        """Ensure SOUP table exists in database."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS soup_components (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            usage_reason TEXT NOT NULL,
            safety_justification TEXT NOT NULL,
            supplier TEXT,
            license TEXT,
            website TEXT,
            description TEXT,
            installation_date TEXT,
            last_updated TEXT,
            criticality_level TEXT,
            verification_method TEXT,
            anomaly_list TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        
        with self.db_manager.get_connection() as conn:
            conn.execute(create_table_sql)
            conn.commit()
    
    def add_component(self, component: SOUPComponent) -> str:
        """
        Add a new SOUP component to the inventory.
        
        Args:
            component: SOUPComponent instance to add
            
        Returns:
            Component ID
            
        Raises:
            ValueError: If component validation fails
            sqlite3.Error: If database operation fails
        """
        # Validate component
        validation_errors = component.validate()
        if validation_errors:
            raise ValueError(f"Component validation failed: {', '.join(validation_errors)}")
        
        # Generate ID if not provided
        if not component.id:
            component.id = str(uuid.uuid4())
        
        # Prepare data for database
        now = datetime.now().isoformat()
        
        insert_sql = """
        INSERT INTO soup_components (
            id, name, version, usage_reason, safety_justification,
            supplier, license, website, description, installation_date,
            last_updated, criticality_level, verification_method,
            anomaly_list, metadata, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            component.id,
            component.name,
            component.version,
            component.usage_reason,
            component.safety_justification,
            component.supplier,
            component.license,
            component.website,
            component.description,
            component.installation_date.isoformat() if component.installation_date else None,
            component.last_updated.isoformat() if component.last_updated else None,
            component.criticality_level,
            component.verification_method,
            json.dumps(component.anomaly_list),
            json.dumps(component.metadata),
            now,
            now
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
        
        return component.id
    
    def update_component(self, component: SOUPComponent) -> bool:
        """
        Update an existing SOUP component.
        
        Args:
            component: SOUPComponent instance with updated data
            
        Returns:
            True if component was updated, False if not found
            
        Raises:
            ValueError: If component validation fails
            sqlite3.Error: If database operation fails
        """
        # Validate component
        validation_errors = component.validate()
        if validation_errors:
            raise ValueError(f"Component validation failed: {', '.join(validation_errors)}")
        
        update_sql = """
        UPDATE soup_components SET
            name = ?, version = ?, usage_reason = ?, safety_justification = ?,
            supplier = ?, license = ?, website = ?, description = ?,
            installation_date = ?, last_updated = ?, criticality_level = ?,
            verification_method = ?, anomaly_list = ?, metadata = ?, updated_at = ?
        WHERE id = ?
        """
        
        values = (
            component.name,
            component.version,
            component.usage_reason,
            component.safety_justification,
            component.supplier,
            component.license,
            component.website,
            component.description,
            component.installation_date.isoformat() if component.installation_date else None,
            component.last_updated.isoformat() if component.last_updated else None,
            component.criticality_level,
            component.verification_method,
            json.dumps(component.anomaly_list),
            json.dumps(component.metadata),
            datetime.now().isoformat(),
            component.id
        )
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(update_sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_component(self, component_id: str) -> Optional[SOUPComponent]:
        """
        Get a SOUP component by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            SOUPComponent instance or None if not found
        """
        select_sql = """
        SELECT id, name, version, usage_reason, safety_justification,
               supplier, license, website, description, installation_date,
               last_updated, criticality_level, verification_method,
               anomaly_list, metadata
        FROM soup_components
        WHERE id = ?
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql, (component_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_component(row)
    
    def get_all_components(self) -> List[SOUPComponent]:
        """
        Get all SOUP components.
        
        Returns:
            List of SOUPComponent instances
        """
        select_sql = """
        SELECT id, name, version, usage_reason, safety_justification,
               supplier, license, website, description, installation_date,
               last_updated, criticality_level, verification_method,
               anomaly_list, metadata
        FROM soup_components
        ORDER BY name, version
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql)
            rows = cursor.fetchall()
            
            return [self._row_to_component(row) for row in rows]
    
    def delete_component(self, component_id: str) -> bool:
        """
        Delete a SOUP component.
        
        Args:
            component_id: Component ID
            
        Returns:
            True if component was deleted, False if not found
        """
        delete_sql = "DELETE FROM soup_components WHERE id = ?"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(delete_sql, (component_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search_components(self, query: str) -> List[SOUPComponent]:
        """
        Search SOUP components by name, supplier, or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching SOUPComponent instances
        """
        search_sql = """
        SELECT id, name, version, usage_reason, safety_justification,
               supplier, license, website, description, installation_date,
               last_updated, criticality_level, verification_method,
               anomaly_list, metadata
        FROM soup_components
        WHERE name LIKE ? OR supplier LIKE ? OR description LIKE ?
        ORDER BY name, version
        """
        
        search_pattern = f"%{query}%"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(search_sql, (search_pattern, search_pattern, search_pattern))
            rows = cursor.fetchall()
            
            return [self._row_to_component(row) for row in rows]
    
    def get_components_by_criticality(self, criticality_level: str) -> List[SOUPComponent]:
        """
        Get SOUP components by criticality level.
        
        Args:
            criticality_level: "High", "Medium", or "Low"
            
        Returns:
            List of SOUPComponent instances
        """
        select_sql = """
        SELECT id, name, version, usage_reason, safety_justification,
               supplier, license, website, description, installation_date,
               last_updated, criticality_level, verification_method,
               anomaly_list, metadata
        FROM soup_components
        WHERE criticality_level = ?
        ORDER BY name, version
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql, (criticality_level,))
            rows = cursor.fetchall()
            
            return [self._row_to_component(row) for row in rows]
    
    def export_inventory(self) -> Dict[str, Any]:
        """
        Export complete SOUP inventory as dictionary.
        
        Returns:
            Dictionary containing all SOUP components and metadata
        """
        components = self.get_all_components()
        
        return {
            "soup_inventory": {
                "export_timestamp": datetime.now().isoformat(),
                "component_count": len(components),
                "components": [
                    {
                        "id": comp.id,
                        "name": comp.name,
                        "version": comp.version,
                        "usage_reason": comp.usage_reason,
                        "safety_justification": comp.safety_justification,
                        "supplier": comp.supplier,
                        "license": comp.license,
                        "website": comp.website,
                        "description": comp.description,
                        "installation_date": comp.installation_date.isoformat() if comp.installation_date else None,
                        "last_updated": comp.last_updated.isoformat() if comp.last_updated else None,
                        "criticality_level": comp.criticality_level,
                        "verification_method": comp.verification_method,
                        "anomaly_list": comp.anomaly_list,
                        "metadata": comp.metadata
                    }
                    for comp in components
                ]
            }
        }
    
    def _row_to_component(self, row) -> SOUPComponent:
        """
        Convert database row to SOUPComponent instance.
        
        Args:
            row: Database row tuple
            
        Returns:
            SOUPComponent instance
        """
        (id, name, version, usage_reason, safety_justification,
         supplier, license, website, description, installation_date,
         last_updated, criticality_level, verification_method,
         anomaly_list, metadata) = row
        
        return SOUPComponent(
            id=id,
            name=name,
            version=version,
            usage_reason=usage_reason,
            safety_justification=safety_justification,
            supplier=supplier,
            license=license,
            website=website,
            description=description,
            installation_date=datetime.fromisoformat(installation_date) if installation_date else None,
            last_updated=datetime.fromisoformat(last_updated) if last_updated else None,
            criticality_level=criticality_level,
            verification_method=verification_method,
            anomaly_list=json.loads(anomaly_list) if anomaly_list else [],
            metadata=json.loads(metadata) if metadata else {}
        )