"""
SOUP (Software of Unknown Provenance) inventory management service.
Enhanced with IEC 62304 compliance features.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from ..models.core import SOUPComponent
from ..models.soup_models import (
    DetectedSOUPComponent, IEC62304Classification, SafetyAssessment,
    VersionChange, ComplianceValidation, SOUPAuditEntry, IEC62304SafetyClass,
    DetectionMethod
)
from ..database.schema import DatabaseManager
from .soup_detector import SOUPDetector
from .llm_soup_classifier import LLMSOUPClassifier, SOUPAnalysisContext
from .iec62304_compliance_manager import IEC62304ComplianceManager


class SOUPService:
    """Service for managing SOUP (Software of Unknown Provenance) components with IEC 62304 compliance."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SOUP service.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.soup_detector = SOUPDetector(use_llm_classification=True)
        self.llm_classifier = LLMSOUPClassifier()
        self.compliance_manager = IEC62304ComplianceManager()
        self._ensure_soup_tables()
    
    def _ensure_soup_tables(self):
        """Ensure SOUP-related tables exist in database."""
        # Original SOUP components table
        create_soup_table_sql = """
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
            updated_at TEXT NOT NULL,
            iec62304_classification TEXT,
            safety_assessment TEXT,
            compliance_status TEXT
        )
        """
        
        # IEC 62304 classifications table
        create_classification_table_sql = """
        CREATE TABLE IF NOT EXISTS soup_classifications (
            id TEXT PRIMARY KEY,
            component_id TEXT NOT NULL,
            safety_class TEXT NOT NULL,
            justification TEXT NOT NULL,
            risk_assessment TEXT NOT NULL,
            verification_requirements TEXT,
            documentation_requirements TEXT,
            change_control_requirements TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (component_id) REFERENCES soup_components (id)
        )
        """
        
        # Version changes table
        create_version_changes_table_sql = """
        CREATE TABLE IF NOT EXISTS soup_version_changes (
            id TEXT PRIMARY KEY,
            component_id TEXT NOT NULL,
            old_version TEXT NOT NULL,
            new_version TEXT NOT NULL,
            change_date TEXT NOT NULL,
            impact_analysis TEXT NOT NULL,
            approval_status TEXT NOT NULL,
            approver TEXT,
            approval_date TEXT,
            change_reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (component_id) REFERENCES soup_components (id)
        )
        """
        
        # Audit trail table
        create_audit_table_sql = """
        CREATE TABLE IF NOT EXISTS soup_audit_trail (
            id TEXT PRIMARY KEY,
            component_id TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            details TEXT,
            old_values TEXT,
            new_values TEXT,
            created_at TEXT NOT NULL
        )
        """
        
        with self.db_manager.get_connection() as conn:
            conn.execute(create_soup_table_sql)
            conn.execute(create_classification_table_sql)
            conn.execute(create_version_changes_table_sql)
            conn.execute(create_audit_table_sql)
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
        # Generate ID if not provided
        if not component.id:
            component.id = str(uuid.uuid4())
        
        # Validate component
        validation_errors = component.validate()
        if validation_errors:
            raise ValueError(f"Component validation failed: {', '.join(validation_errors)}")
        
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
    
    # Enhanced compliance features
    
    def add_component_with_classification(self, detected_component: DetectedSOUPComponent, 
                                        user: str = "system") -> str:
        """
        Add a SOUP component with automatic IEC 62304 classification.
        
        Args:
            detected_component: Detected SOUP component
            user: User performing the action
            
        Returns:
            Component ID
            
        Raises:
            ValueError: If component validation fails
            sqlite3.Error: If database operation fails
        """
        # Validate detected component
        validation_errors = detected_component.validate()
        if validation_errors:
            raise ValueError(f"Detected component validation failed: {', '.join(validation_errors)}")
        
        # Generate automatic classification
        classification = self.compliance_manager.classify_component_automatically(detected_component)
        
        # Convert to SOUPComponent
        component_id = str(uuid.uuid4())
        soup_component = SOUPComponent(
            id=component_id,
            name=detected_component.name,
            version=detected_component.version,
            usage_reason=f"Automatically detected from {detected_component.source_file}",
            safety_justification=classification.justification,
            supplier=detected_component.metadata.get('supplier', ''),
            license=detected_component.license or '',
            website=detected_component.homepage or '',
            description=detected_component.description or '',
            installation_date=datetime.now(),
            last_updated=datetime.now(),
            criticality_level=self._map_safety_class_to_criticality(classification.safety_class),
            verification_method='',
            anomaly_list=[],
            metadata=detected_component.metadata
        )
        
        # Add component to database
        self.add_component(soup_component)
        
        # Store classification
        self._store_classification(component_id, classification)
        
        # Create audit entry
        self._create_audit_entry(
            component_id=component_id,
            action="created_with_classification",
            user=user,
            details={
                "detection_method": detected_component.detection_method.value,
                "confidence": detected_component.confidence,
                "safety_class": classification.safety_class.value,
                "source_file": detected_component.source_file
            }
        )
        
        return component_id
    
    def classify_existing_component(self, component_id: str, user: str = "system") -> IEC62304Classification:
        """
        Classify an existing SOUP component according to IEC 62304.
        
        Args:
            component_id: Component ID
            user: User performing the classification
            
        Returns:
            IEC 62304 classification
            
        Raises:
            ValueError: If component not found
        """
        component = self.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        # Create a DetectedSOUPComponent for classification
        detected_component = DetectedSOUPComponent(
            name=component.name,
            version=component.version,
            source_file="existing",
            detection_method=DetectionMethod.MANUAL,
            confidence=1.0,
            description=component.description,
            license=component.license,
            metadata=component.metadata
        )
        
        # Generate classification
        classification = self.compliance_manager.classify_component_automatically(detected_component)
        
        # Store classification
        self._store_classification(component_id, classification)
        
        # Update component criticality
        component.criticality_level = self._map_safety_class_to_criticality(classification.safety_class)
        component.safety_justification = classification.justification
        self.update_component(component)
        
        # Create audit entry
        self._create_audit_entry(
            component_id=component_id,
            action="classified",
            user=user,
            details={
                "safety_class": classification.safety_class.value,
                "justification": classification.justification
            }
        )
        
        return classification
    
    def assess_component_safety(self, component_id: str, safety_impact: str,
                              failure_modes: List[str], mitigation_measures: List[str],
                              verification_methods: List[str], assessor: str = "system") -> SafetyAssessment:
        """
        Create safety assessment for a SOUP component.
        
        Args:
            component_id: Component ID
            safety_impact: Description of safety impact
            failure_modes: List of potential failure modes
            mitigation_measures: List of mitigation measures
            verification_methods: List of verification methods
            assessor: Person performing the assessment
            
        Returns:
            Safety assessment
            
        Raises:
            ValueError: If component not found
        """
        component = self.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        assessment = SafetyAssessment(
            component_id=component_id,
            safety_impact=safety_impact,
            failure_modes=failure_modes,
            mitigation_measures=mitigation_measures,
            verification_methods=verification_methods,
            assessor=assessor
        )
        
        # Validate assessment
        validation_errors = assessment.validate()
        if validation_errors:
            raise ValueError(f"Safety assessment validation failed: {', '.join(validation_errors)}")
        
        # Store assessment (you would implement this table)
        self._store_safety_assessment(assessment)
        
        # Create audit entry
        self._create_audit_entry(
            component_id=component_id,
            action="safety_assessed",
            user=assessor,
            details={
                "safety_impact": safety_impact,
                "failure_modes_count": len(failure_modes),
                "mitigation_measures_count": len(mitigation_measures)
            }
        )
        
        return assessment
    
    def track_version_change(self, component_id: str, new_version: str, 
                           impact_analysis: str, change_reason: str = "",
                           user: str = "system") -> VersionChange:
        """
        Track version change for a SOUP component with impact analysis.
        
        Args:
            component_id: Component ID
            new_version: New version
            impact_analysis: Analysis of change impact
            change_reason: Reason for the change
            user: User performing the change
            
        Returns:
            Version change record
            
        Raises:
            ValueError: If component not found or validation fails
        """
        component = self.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        old_version = component.version
        
        # Create version change record
        version_change = VersionChange(
            component_id=component_id,
            old_version=old_version,
            new_version=new_version,
            change_date=datetime.now(),
            impact_analysis=impact_analysis,
            approval_status="pending",
            change_reason=change_reason
        )
        
        # Validate version change
        validation_errors = version_change.validate()
        if validation_errors:
            raise ValueError(f"Version change validation failed: {', '.join(validation_errors)}")
        
        # Store version change
        self._store_version_change(version_change)
        
        # Update component version
        component.version = new_version
        component.last_updated = datetime.now()
        self.update_component(component)
        
        # Create audit entry
        self._create_audit_entry(
            component_id=component_id,
            action="version_changed",
            user=user,
            details={
                "old_version": old_version,
                "new_version": new_version,
                "change_reason": change_reason
            },
            old_values={"version": old_version},
            new_values={"version": new_version}
        )
        
        return version_change
    
    def validate_component_compliance(self, component_id: str) -> ComplianceValidation:
        """
        Validate IEC 62304 compliance for a SOUP component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Compliance validation result
            
        Raises:
            ValueError: If component not found
        """
        component = self.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        # Get classification
        classification = self.get_component_classification(component_id)
        if not classification:
            # Create default classification if none exists
            classification = self.classify_existing_component(component_id)
        
        # Validate compliance
        validation = self.compliance_manager.validate_compliance(component, classification)
        
        # Store validation result (you would implement this table)
        self._store_compliance_validation(validation)
        
        # Create audit entry
        self._create_audit_entry(
            component_id=component_id,
            action="compliance_validated",
            user="system",
            details={
                "is_compliant": validation.is_compliant,
                "missing_requirements_count": len(validation.missing_requirements),
                "warnings_count": len(validation.warnings)
            }
        )
        
        return validation
    
    def get_component_classification(self, component_id: str) -> Optional[IEC62304Classification]:
        """
        Get IEC 62304 classification for a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Classification or None if not found
        """
        select_sql = """
        SELECT safety_class, justification, risk_assessment, 
               verification_requirements, documentation_requirements,
               change_control_requirements, created_at, updated_at
        FROM soup_classifications
        WHERE component_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql, (component_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            (safety_class, justification, risk_assessment, 
             verification_reqs, documentation_reqs, change_control_reqs,
             created_at, updated_at) = row
            
            return IEC62304Classification(
                safety_class=IEC62304SafetyClass(safety_class),
                justification=justification,
                risk_assessment=risk_assessment,
                verification_requirements=json.loads(verification_reqs) if verification_reqs else [],
                documentation_requirements=json.loads(documentation_reqs) if documentation_reqs else [],
                change_control_requirements=json.loads(change_control_reqs) if change_control_reqs else [],
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at)
            )
    
    def get_component_version_history(self, component_id: str) -> List[VersionChange]:
        """
        Get version change history for a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            List of version changes
        """
        select_sql = """
        SELECT id, old_version, new_version, change_date, impact_analysis,
               approval_status, approver, approval_date, change_reason, created_at
        FROM soup_version_changes
        WHERE component_id = ?
        ORDER BY change_date DESC
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql, (component_id,))
            rows = cursor.fetchall()
            
            version_changes = []
            for row in rows:
                (id, old_version, new_version, change_date, impact_analysis,
                 approval_status, approver, approval_date, change_reason, created_at) = row
                
                version_changes.append(VersionChange(
                    component_id=component_id,
                    old_version=old_version,
                    new_version=new_version,
                    change_date=datetime.fromisoformat(change_date),
                    impact_analysis=impact_analysis,
                    approval_status=approval_status,
                    approver=approver,
                    approval_date=datetime.fromisoformat(approval_date) if approval_date else None,
                    change_reason=change_reason
                ))
            
            return version_changes
    
    def analyze_components_with_llm(self, project_path: str, 
                                  project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect and analyze SOUP components using LLM-based classification.
        
        Args:
            project_path: Path to the project root directory
            project_context: Optional project context for analysis
            
        Returns:
            Comprehensive analysis results with LLM-based classifications
        """
        # Detect components
        detected_components = self.soup_detector.detect_soup_components(project_path)
        
        if not detected_components:
            return {
                "summary": {
                    "total_components": 0,
                    "analysis_method": "llm_based",
                    "project_path": project_path
                },
                "components": [],
                "recommendations": ["No SOUP components detected in the project"]
            }
        
        # Get detailed LLM analysis for each component
        detailed_analyses = self.soup_detector.batch_classify_components(
            detected_components, project_context
        )
        
        # Compile summary statistics
        classification_counts = {"A": 0, "B": 0, "C": 0, "error": 0}
        high_risk_components = []
        recommendations = []
        
        for analysis in detailed_analyses:
            if "error" in analysis:
                classification_counts["error"] += 1
                if "fallback_classification" in analysis:
                    fallback_class = analysis["fallback_classification"]
                    if fallback_class:
                        classification_counts[fallback_class.value] += 1
            else:
                safety_class = analysis["classification"]["safety_class"]
                classification_counts[safety_class] += 1
                
                if safety_class == "C":
                    high_risk_components.append(analysis["component_info"]["name"])
        
        # Generate recommendations
        if classification_counts["C"] > 0:
            recommendations.append(f"Found {classification_counts['C']} Class C (life-threatening) components requiring immediate review")
        
        if classification_counts["B"] > 0:
            recommendations.append(f"Found {classification_counts['B']} Class B components requiring safety assessment")
        
        if classification_counts["error"] > 0:
            recommendations.append(f"LLM analysis failed for {classification_counts['error']} components - manual review required")
        
        if high_risk_components:
            recommendations.append(f"High-risk components requiring priority attention: {', '.join(high_risk_components[:5])}")
        
        return {
            "summary": {
                "total_components": len(detected_components),
                "classification_counts": classification_counts,
                "high_risk_components": len(high_risk_components),
                "analysis_method": "llm_based",
                "project_path": project_path,
                "llm_success_rate": (len(detailed_analyses) - classification_counts["error"]) / len(detailed_analyses) if detailed_analyses else 0
            },
            "components": detailed_analyses,
            "recommendations": recommendations,
            "project_context": project_context or {}
        }
    
    def get_component_llm_analysis(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get LLM-based analysis for an existing SOUP component.
        
        Args:
            component_id: Component ID
            
        Returns:
            LLM analysis results or None if component not found
        """
        component = self.get_component(component_id)
        if not component:
            return None
        
        # Convert SOUPComponent to DetectedSOUPComponent for analysis
        detected_component = DetectedSOUPComponent(
            name=component.name,
            version=component.version,
            source_file="existing_component",
            detection_method=DetectionMethod.MANUAL,
            confidence=1.0,
            description=component.description,
            license=component.license,
            metadata=component.metadata
        )
        
        # Get detailed analysis
        return self.soup_detector.get_detailed_classification(detected_component)
    
    def update_component_with_llm_classification(self, component_id: str, 
                                               user: str = "system") -> bool:
        """
        Update an existing component with fresh LLM-based classification.
        
        Args:
            component_id: Component ID
            user: User performing the update
            
        Returns:
            True if update was successful, False otherwise
        """
        component = self.get_component(component_id)
        if not component:
            return False
        
        try:
            # Get LLM analysis
            analysis = self.get_component_llm_analysis(component_id)
            if not analysis or "error" in analysis:
                return False
            
            classification_data = analysis["classification"]
            
            # Update component with new classification
            component.safety_justification = classification_data["justification"]
            component.criticality_level = self._map_safety_class_to_criticality(
                IEC62304SafetyClass(classification_data["safety_class"])
            )
            
            # Update metadata with LLM analysis results
            component.metadata.update({
                "llm_analysis": analysis,
                "last_llm_analysis": datetime.now().isoformat(),
                "analysis_method": "llm_based"
            })
            
            # Save updated component
            success = self.update_component(component)
            
            if success:
                # Create audit entry
                self._create_audit_entry(
                    component_id=component_id,
                    action="llm_classification_updated",
                    user=user,
                    details={
                        "safety_class": classification_data["safety_class"],
                        "method": "llm_based",
                        "confidence": analysis.get("classification", {}).get("metadata", {}).get("confidence_score", 0.8)
                    }
                )
            
            return success
            
        except Exception as e:
            # Log error but don't fail completely
            self._create_audit_entry(
                component_id=component_id,
                action="llm_classification_failed",
                user=user,
                details={"error": str(e)}
            )
            return False
    
    def get_component_audit_trail(self, component_id: str) -> List[SOUPAuditEntry]:
        """
        Get audit trail for a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            List of audit entries
        """
        select_sql = """
        SELECT action, timestamp, user, details, old_values, new_values, created_at
        FROM soup_audit_trail
        WHERE component_id = ?
        ORDER BY timestamp DESC
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(select_sql, (component_id,))
            rows = cursor.fetchall()
            
            audit_entries = []
            for row in rows:
                (action, timestamp, user, details, old_values, new_values, created_at) = row
                
                audit_entries.append(SOUPAuditEntry(
                    component_id=component_id,
                    action=action,
                    timestamp=datetime.fromisoformat(timestamp),
                    user=user,
                    details=json.loads(details) if details else {},
                    old_values=json.loads(old_values) if old_values else None,
                    new_values=json.loads(new_values) if new_values else None
                ))
            
            return audit_entries
    
    def approve_version_change(self, component_id: str, version_change_id: str,
                             approver: str) -> bool:
        """
        Approve a version change.
        
        Args:
            component_id: Component ID
            version_change_id: Version change ID (old_version for lookup)
            approver: Person approving the change
            
        Returns:
            True if approved successfully
        """
        update_sql = """
        UPDATE soup_version_changes
        SET approval_status = 'approved', approver = ?, approval_date = ?
        WHERE component_id = ? AND old_version = ?
        """
        
        approval_date = datetime.now().isoformat()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(update_sql, (approver, approval_date, component_id, version_change_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                # Create audit entry
                self._create_audit_entry(
                    component_id=component_id,
                    action="version_change_approved",
                    user=approver,
                    details={
                        "version_change_id": version_change_id,
                        "approval_date": approval_date
                    }
                )
                return True
            
            return False
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """
        Get compliance summary for all SOUP components.
        
        Returns:
            Dictionary with compliance statistics
        """
        components = self.get_all_components()
        
        summary = {
            "total_components": len(components),
            "by_safety_class": {"A": 0, "B": 0, "C": 0, "unclassified": 0},
            "compliance_status": {"compliant": 0, "non_compliant": 0, "not_validated": 0},
            "pending_approvals": 0,
            "recent_changes": 0
        }
        
        # Count by safety class and compliance
        for component in components:
            classification = self.get_component_classification(component.id)
            if classification:
                summary["by_safety_class"][classification.safety_class.value] += 1
                
                # Check compliance
                validation = self.validate_component_compliance(component.id)
                if validation.is_compliant:
                    summary["compliance_status"]["compliant"] += 1
                else:
                    summary["compliance_status"]["non_compliant"] += 1
            else:
                summary["by_safety_class"]["unclassified"] += 1
                summary["compliance_status"]["not_validated"] += 1
        
        # Count pending approvals
        pending_sql = """
        SELECT COUNT(*) FROM soup_version_changes 
        WHERE approval_status = 'pending'
        """
        
        # Count recent changes (last 30 days)
        recent_sql = """
        SELECT COUNT(*) FROM soup_version_changes 
        WHERE change_date >= date('now', '-30 days')
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(pending_sql)
            summary["pending_approvals"] = cursor.fetchone()[0]
            
            cursor = conn.execute(recent_sql)
            summary["recent_changes"] = cursor.fetchone()[0]
        
        return summary
    
    # Helper methods for compliance features
    
    def _map_safety_class_to_criticality(self, safety_class: IEC62304SafetyClass) -> str:
        """Map IEC 62304 safety class to criticality level."""
        mapping = {
            IEC62304SafetyClass.CLASS_A: "Low",
            IEC62304SafetyClass.CLASS_B: "Medium", 
            IEC62304SafetyClass.CLASS_C: "High"
        }
        return mapping.get(safety_class, "Medium")
    
    def _store_classification(self, component_id: str, classification: IEC62304Classification):
        """Store IEC 62304 classification in database."""
        insert_sql = """
        INSERT INTO soup_classifications (
            id, component_id, safety_class, justification, risk_assessment,
            verification_requirements, documentation_requirements,
            change_control_requirements, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        values = (
            str(uuid.uuid4()),
            component_id,
            classification.safety_class.value,
            classification.justification,
            classification.risk_assessment,
            json.dumps(classification.verification_requirements),
            json.dumps(classification.documentation_requirements),
            json.dumps(classification.change_control_requirements),
            now,
            now
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def _store_version_change(self, version_change: VersionChange):
        """Store version change in database."""
        insert_sql = """
        INSERT INTO soup_version_changes (
            id, component_id, old_version, new_version, change_date,
            impact_analysis, approval_status, approver, approval_date,
            change_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            str(uuid.uuid4()),
            version_change.component_id,
            version_change.old_version,
            version_change.new_version,
            version_change.change_date.isoformat(),
            version_change.impact_analysis,
            version_change.approval_status,
            version_change.approver,
            version_change.approval_date.isoformat() if version_change.approval_date else None,
            version_change.change_reason,
            datetime.now().isoformat()
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def _store_safety_assessment(self, assessment: SafetyAssessment):
        """Store safety assessment in database."""
        # This would require a safety_assessments table
        # For now, we'll store it as metadata in the component
        pass
    
    def _store_compliance_validation(self, validation: ComplianceValidation):
        """Store compliance validation in database."""
        # This would require a compliance_validations table
        # For now, we'll store it as metadata in the component
        pass
    
    def _create_audit_entry(self, component_id: str, action: str, user: str,
                          details: Dict[str, Any] = None, old_values: Dict[str, Any] = None,
                          new_values: Dict[str, Any] = None):
        """Create audit trail entry."""
        insert_sql = """
        INSERT INTO soup_audit_trail (
            id, component_id, action, timestamp, user, details,
            old_values, new_values, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now()
        values = (
            str(uuid.uuid4()),
            component_id,
            action,
            now.isoformat(),
            user,
            json.dumps(details) if details else None,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            now.isoformat()
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def _store_classification(self, component_id: str, classification: IEC62304Classification):
        """Store IEC 62304 classification in database."""
        insert_sql = """
        INSERT OR REPLACE INTO soup_classifications (
            id, component_id, safety_class, justification, risk_assessment,
            verification_requirements, documentation_requirements, 
            change_control_requirements, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        
        values = (
            str(uuid.uuid4()),
            component_id,
            classification.safety_class.value,
            classification.justification,
            classification.risk_assessment,
            json.dumps(classification.verification_requirements),
            json.dumps(classification.documentation_requirements),
            json.dumps(classification.change_control_requirements),
            now,
            now
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def _store_safety_assessment(self, assessment: SafetyAssessment):
        """Store safety assessment in database."""
        # This would require creating a safety_assessments table
        # For now, we'll store it as JSON in component metadata
        component = self.get_component(assessment.component_id)
        if component:
            component.metadata['safety_assessment'] = {
                'safety_impact': assessment.safety_impact,
                'failure_modes': assessment.failure_modes,
                'mitigation_measures': assessment.mitigation_measures,
                'verification_methods': assessment.verification_methods,
                'assessment_date': assessment.assessment_date.isoformat(),
                'assessor': assessment.assessor
            }
            self.update_component(component)
    
    def _store_version_change(self, version_change: VersionChange):
        """Store version change record in database."""
        insert_sql = """
        INSERT INTO soup_version_changes (
            id, component_id, old_version, new_version, change_date,
            impact_analysis, approval_status, approver, approval_date,
            change_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            str(uuid.uuid4()),
            version_change.component_id,
            version_change.old_version,
            version_change.new_version,
            version_change.change_date.isoformat(),
            version_change.impact_analysis,
            version_change.approval_status,
            version_change.approver,
            version_change.approval_date.isoformat() if version_change.approval_date else None,
            version_change.change_reason,
            datetime.now().isoformat()
        )
        
        with self.db_manager.get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def _store_compliance_validation(self, validation: ComplianceValidation):
        """Store compliance validation result."""
        # Store in component metadata for now
        component = self.get_component(validation.component_id)
        if component:
            component.metadata['compliance_validation'] = {
                'is_compliant': validation.is_compliant,
                'validation_date': validation.validation_date.isoformat(),
                'missing_requirements': validation.missing_requirements,
                'warnings': validation.warnings,
                'recommendations': validation.recommendations,
                'validator': validation.validator
            }
            self.update_component(component)
    
    def _map_safety_class_to_criticality(self, safety_class: IEC62304SafetyClass) -> str:
        """Map IEC 62304 safety class to criticality level."""
        mapping = {
            IEC62304SafetyClass.CLASS_A: "Low",
            IEC62304SafetyClass.CLASS_B: "Medium",
            IEC62304SafetyClass.CLASS_C: "High"
        }
        return mapping.get(safety_class, "Medium")
    
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