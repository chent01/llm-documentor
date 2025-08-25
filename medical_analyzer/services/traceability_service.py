"""
Traceability service for creating and managing traceability links.

This service handles the creation of traceability links between different
analysis artifacts including code references, features, requirements, and risks.
"""

import logging
import csv
import io
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from ..models.core import (
    TraceabilityLink, CodeReference, Feature, Requirement, RiskItem,
    RequirementType
)
from ..database.schema import DatabaseManager


logger = logging.getLogger(__name__)


@dataclass
class TraceabilityMatrix:
    """Complete traceability matrix for an analysis run."""
    analysis_run_id: int
    links: List[TraceabilityLink]
    code_to_requirements: Dict[str, List[str]]  # code_ref_id -> requirement_ids
    user_to_software_requirements: Dict[str, List[str]]  # ur_id -> sr_ids
    requirements_to_risks: Dict[str, List[str]]  # requirement_id -> risk_ids
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class TraceabilityGap:
    """Represents a gap in traceability coverage."""
    gap_type: str  # 'orphaned_code', 'orphaned_requirement', 'missing_link', 'weak_link'
    source_type: str
    source_id: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    description: str = ""
    severity: str = "medium"  # 'low', 'medium', 'high'
    recommendation: str = ""


@dataclass
class TraceabilityTableRow:
    """Row in the tabular traceability matrix display."""
    code_reference: str
    file_path: str
    function_name: str
    feature_id: str
    feature_description: str
    user_requirement_id: str
    user_requirement_text: str
    software_requirement_id: str
    software_requirement_text: str
    risk_id: str
    risk_hazard: str
    confidence: float


class TraceabilityService:
    """Service for creating and managing traceability links."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize traceability service with database manager."""
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def create_traceability_matrix(
        self,
        analysis_run_id: int,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> TraceabilityMatrix:
        """
        Create complete traceability matrix for an analysis run.
        
        Args:
            analysis_run_id: ID of the analysis run
            features: List of extracted features
            user_requirements: List of user requirements
            software_requirements: List of software requirements
            risk_items: List of identified risks
            
        Returns:
            Complete traceability matrix
        """
        self.logger.info(f"Creating traceability matrix for analysis run {analysis_run_id}")
        
        links = []
        code_to_requirements = {}
        user_to_software_requirements = {}
        requirements_to_risks = {}
        
        # 1. Create code-to-feature links
        code_feature_links = self._create_code_to_feature_links(
            analysis_run_id, features
        )
        links.extend(code_feature_links)
        
        # 2. Create feature-to-user-requirement links
        feature_ur_links = self._create_feature_to_user_requirement_links(
            analysis_run_id, features, user_requirements
        )
        links.extend(feature_ur_links)
        
        # 3. Create user-requirement-to-software-requirement links
        ur_sr_links = self._create_user_to_software_requirement_links(
            analysis_run_id, user_requirements, software_requirements
        )
        links.extend(ur_sr_links)
        user_to_software_requirements = self._build_ur_to_sr_mapping(ur_sr_links)
        
        # 4. Create software-requirement-to-risk links
        sr_risk_links = self._create_software_requirement_to_risk_links(
            analysis_run_id, software_requirements, risk_items
        )
        links.extend(sr_risk_links)
        requirements_to_risks = self._build_requirement_to_risk_mapping(sr_risk_links)
        
        # 5. Create transitive code-to-software-requirement links
        code_sr_links = self._create_transitive_code_to_requirement_links(
            analysis_run_id, features, software_requirements, feature_ur_links, ur_sr_links
        )
        links.extend(code_sr_links)
        code_to_requirements = self._build_code_to_requirement_mapping(code_sr_links)
        
        # Store all links in database
        for link in links:
            self.db_manager.create_traceability_link(
                analysis_run_id=link.source_id if link.source_type == "analysis_run" else analysis_run_id,
                source_type=link.source_type,
                source_id=link.source_id,
                target_type=link.target_type,
                target_id=link.target_id,
                link_type=link.link_type,
                confidence=link.confidence,
                metadata=link.metadata
            )
        
        matrix = TraceabilityMatrix(
            analysis_run_id=analysis_run_id,
            links=links,
            code_to_requirements=code_to_requirements,
            user_to_software_requirements=user_to_software_requirements,
            requirements_to_risks=requirements_to_risks,
            metadata={
                "total_links": len(links),
                "code_feature_links": len(code_feature_links),
                "feature_ur_links": len(feature_ur_links),
                "ur_sr_links": len(ur_sr_links),
                "sr_risk_links": len(sr_risk_links),
                "code_sr_links": len(code_sr_links)
            },
            created_at=datetime.now()
        )
        
        self.logger.info(f"Created traceability matrix with {len(links)} total links")
        return matrix
    
    def _create_code_to_feature_links(
        self, 
        analysis_run_id: int, 
        features: List[Feature]
    ) -> List[TraceabilityLink]:
        """Create traceability links from code references to features."""
        links = []
        
        for feature in features:
            for code_ref in feature.evidence:
                link_id = f"code_feature_{len(links)}"
                code_ref_id = self._generate_code_reference_id(code_ref)
                
                link = TraceabilityLink(
                    id=link_id,
                    source_type="code",
                    source_id=code_ref_id,
                    target_type="feature",
                    target_id=feature.id,
                    link_type="implements",
                    confidence=feature.confidence,
                    metadata={
                        "file_path": code_ref.file_path,
                        "start_line": code_ref.start_line,
                        "end_line": code_ref.end_line,
                        "function_name": code_ref.function_name,
                        "feature_category": feature.category.value if hasattr(feature.category, 'value') else str(feature.category)
                    }
                )
                links.append(link)
        
        return links
    
    def _create_feature_to_user_requirement_links(
        self,
        analysis_run_id: int,
        features: List[Feature],
        user_requirements: List[Requirement]
    ) -> List[TraceabilityLink]:
        """Create traceability links from features to user requirements."""
        links = []
        
        # Create mapping of features to user requirements based on derived_from
        for ur in user_requirements:
            if ur.type == RequirementType.USER:
                for derived_feature_id in ur.derived_from:
                    # Find the feature
                    feature = next((f for f in features if f.id == derived_feature_id), None)
                    if feature:
                        link_id = f"feature_ur_{len(links)}"
                        
                        link = TraceabilityLink(
                            id=link_id,
                            source_type="feature",
                            source_id=feature.id,
                            target_type="requirement",
                            target_id=ur.id,
                            link_type="derives_to",
                            confidence=min(feature.confidence, 0.9),  # Slightly reduce confidence for derivation
                            metadata={
                                "requirement_type": "user",
                                "feature_description": feature.description,
                                "requirement_text": ur.text[:100] + "..." if len(ur.text) > 100 else ur.text
                            }
                        )
                        links.append(link)
        
        return links
    
    def _create_user_to_software_requirement_links(
        self,
        analysis_run_id: int,
        user_requirements: List[Requirement],
        software_requirements: List[Requirement]
    ) -> List[TraceabilityLink]:
        """Create traceability links from user requirements to software requirements."""
        links = []
        
        for sr in software_requirements:
            if sr.type == RequirementType.SOFTWARE:
                for derived_ur_id in sr.derived_from:
                    # Find the user requirement
                    ur = next((r for r in user_requirements if r.id == derived_ur_id), None)
                    if ur and ur.type == RequirementType.USER:
                        link_id = f"ur_sr_{len(links)}"
                        
                        link = TraceabilityLink(
                            id=link_id,
                            source_type="requirement",
                            source_id=ur.id,
                            target_type="requirement",
                            target_id=sr.id,
                            link_type="derives_to",
                            confidence=0.95,  # High confidence for requirement derivation
                            metadata={
                                "source_requirement_type": "user",
                                "target_requirement_type": "software",
                                "ur_text": ur.text[:100] + "..." if len(ur.text) > 100 else ur.text,
                                "sr_text": sr.text[:100] + "..." if len(sr.text) > 100 else sr.text
                            }
                        )
                        links.append(link)
        
        return links
    
    def _create_software_requirement_to_risk_links(
        self,
        analysis_run_id: int,
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityLink]:
        """Create traceability links from software requirements to risks."""
        links = []
        
        for risk in risk_items:
            for related_req_id in risk.related_requirements:
                # Find the software requirement
                sr = next((r for r in software_requirements if r.id == related_req_id), None)
                if sr and sr.type == RequirementType.SOFTWARE:
                    link_id = f"sr_risk_{len(links)}"
                    
                    link = TraceabilityLink(
                        id=link_id,
                        source_type="requirement",
                        source_id=sr.id,
                        target_type="risk",
                        target_id=risk.id,
                        link_type="mitigated_by",
                        confidence=0.9,  # High confidence for requirement-risk relationships
                        metadata={
                            "requirement_type": "software",
                            "hazard": risk.hazard,
                            "severity": risk.severity.value if hasattr(risk.severity, 'value') else str(risk.severity),
                            "probability": risk.probability.value if hasattr(risk.probability, 'value') else str(risk.probability),
                            "risk_level": risk.risk_level.value if hasattr(risk.risk_level, 'value') else str(risk.risk_level)
                        }
                    )
                    links.append(link)
        
        return links
    
    def _create_transitive_code_to_requirement_links(
        self,
        analysis_run_id: int,
        features: List[Feature],
        software_requirements: List[Requirement],
        feature_ur_links: List[TraceabilityLink],
        ur_sr_links: List[TraceabilityLink]
    ) -> List[TraceabilityLink]:
        """Create transitive traceability links from code to software requirements."""
        links = []
        
        # Build mapping from features to user requirements
        feature_to_ur = {}
        for link in feature_ur_links:
            if link.source_type == "feature" and link.target_type == "requirement":
                if link.source_id not in feature_to_ur:
                    feature_to_ur[link.source_id] = []
                feature_to_ur[link.source_id].append(link.target_id)
        
        # Build mapping from user requirements to software requirements
        ur_to_sr = {}
        for link in ur_sr_links:
            if link.source_type == "requirement" and link.target_type == "requirement":
                if link.source_id not in ur_to_sr:
                    ur_to_sr[link.source_id] = []
                ur_to_sr[link.source_id].append(link.target_id)
        
        # Create transitive links from code to software requirements
        for feature in features:
            for code_ref in feature.evidence:
                code_ref_id = self._generate_code_reference_id(code_ref)
                
                # Get user requirements for this feature
                ur_ids = feature_to_ur.get(feature.id, [])
                
                for ur_id in ur_ids:
                    # Get software requirements for this user requirement
                    sr_ids = ur_to_sr.get(ur_id, [])
                    
                    for sr_id in sr_ids:
                        link_id = f"code_sr_{len(links)}"
                        
                        link = TraceabilityLink(
                            id=link_id,
                            source_type="code",
                            source_id=code_ref_id,
                            target_type="requirement",
                            target_id=sr_id,
                            link_type="implements",
                            confidence=feature.confidence * 0.8,  # Reduce confidence for transitive links
                            metadata={
                                "file_path": code_ref.file_path,
                                "start_line": code_ref.start_line,
                                "end_line": code_ref.end_line,
                                "function_name": code_ref.function_name,
                                "via_feature": feature.id,
                                "via_user_requirement": ur_id,
                                "link_type": "transitive"
                            }
                        )
                        links.append(link)
        
        return links
    
    def _generate_code_reference_id(self, code_ref: CodeReference) -> str:
        """Generate a unique ID for a code reference."""
        return f"{code_ref.file_path}:{code_ref.start_line}-{code_ref.end_line}"
    
    def _build_code_to_requirement_mapping(
        self, 
        code_sr_links: List[TraceabilityLink]
    ) -> Dict[str, List[str]]:
        """Build mapping from code references to software requirements."""
        mapping = {}
        
        for link in code_sr_links:
            if link.source_type == "code" and link.target_type == "requirement":
                if link.source_id not in mapping:
                    mapping[link.source_id] = []
                mapping[link.source_id].append(link.target_id)
        
        return mapping
    
    def _build_ur_to_sr_mapping(
        self, 
        ur_sr_links: List[TraceabilityLink]
    ) -> Dict[str, List[str]]:
        """Build mapping from user requirements to software requirements."""
        mapping = {}
        
        for link in ur_sr_links:
            if link.source_type == "requirement" and link.target_type == "requirement":
                if link.source_id not in mapping:
                    mapping[link.source_id] = []
                mapping[link.source_id].append(link.target_id)
        
        return mapping
    
    def _build_requirement_to_risk_mapping(
        self, 
        sr_risk_links: List[TraceabilityLink]
    ) -> Dict[str, List[str]]:
        """Build mapping from software requirements to risks."""
        mapping = {}
        
        for link in sr_risk_links:
            if link.source_type == "requirement" and link.target_type == "risk":
                if link.source_id not in mapping:
                    mapping[link.source_id] = []
                mapping[link.source_id].append(link.target_id)
        
        return mapping
    
    def get_traceability_matrix(self, analysis_run_id: int) -> Optional[TraceabilityMatrix]:
        """Retrieve traceability matrix from database."""
        links_data = self.db_manager.get_traceability_links(analysis_run_id)
        
        if not links_data:
            return None
        
        # Convert database records to TraceabilityLink objects
        links = []
        for link_data in links_data:
            link = TraceabilityLink(
                id=str(link_data['id']),
                source_type=link_data['source_type'],
                source_id=link_data['source_id'],
                target_type=link_data['target_type'],
                target_id=link_data['target_id'],
                link_type=link_data['link_type'],
                confidence=link_data['confidence'],
                metadata=link_data['metadata']
            )
            links.append(link)
        
        # Rebuild mappings from links
        code_to_requirements = {}
        user_to_software_requirements = {}
        requirements_to_risks = {}
        
        for link in links:
            if link.source_type == "code" and link.target_type == "requirement":
                if link.source_id not in code_to_requirements:
                    code_to_requirements[link.source_id] = []
                code_to_requirements[link.source_id].append(link.target_id)
            
            elif (link.source_type == "requirement" and link.target_type == "requirement" and
                  link.metadata.get("source_requirement_type") == "user" and
                  link.metadata.get("target_requirement_type") == "software"):
                if link.source_id not in user_to_software_requirements:
                    user_to_software_requirements[link.source_id] = []
                user_to_software_requirements[link.source_id].append(link.target_id)
            
            elif link.source_type == "requirement" and link.target_type == "risk":
                if link.source_id not in requirements_to_risks:
                    requirements_to_risks[link.source_id] = []
                requirements_to_risks[link.source_id].append(link.target_id)
        
        return TraceabilityMatrix(
            analysis_run_id=analysis_run_id,
            links=links,
            code_to_requirements=code_to_requirements,
            user_to_software_requirements=user_to_software_requirements,
            requirements_to_risks=requirements_to_risks,
            metadata={
                "total_links": len(links),
                "retrieved_from_database": True
            },
            created_at=datetime.now()
        )
    
    def validate_traceability_matrix(self, matrix: TraceabilityMatrix) -> List[str]:
        """
        Validate traceability matrix for completeness and consistency.
        
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check for orphaned links
        source_ids = set()
        target_ids = set()
        
        for link in matrix.links:
            source_ids.add(f"{link.source_type}:{link.source_id}")
            target_ids.add(f"{link.target_type}:{link.target_id}")
        
        # Check for broken chains
        feature_links = [l for l in matrix.links if l.source_type == "feature"]
        requirement_links = [l for l in matrix.links if l.source_type == "requirement"]
        
        if not feature_links:
            issues.append("No feature-to-requirement traceability links found")
        
        if not requirement_links:
            issues.append("No requirement-to-requirement or requirement-to-risk links found")
        
        # Check confidence levels
        low_confidence_links = [l for l in matrix.links if l.confidence < 0.5]
        if low_confidence_links:
            issues.append(f"Found {len(low_confidence_links)} links with low confidence (<0.5)")
        
        return issues
    
    def generate_tabular_matrix(
        self, 
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityTableRow]:
        """
        Generate tabular representation of traceability matrix.
        
        Args:
            matrix: The traceability matrix
            features: List of features
            user_requirements: List of user requirements
            software_requirements: List of software requirements
            risk_items: List of risk items
            
        Returns:
            List of table rows for display
        """
        self.logger.info("Generating tabular traceability matrix")
        
        # Create lookup dictionaries for efficient access
        feature_lookup = {f.id: f for f in features}
        ur_lookup = {r.id: r for r in user_requirements if r.type == RequirementType.USER}
        sr_lookup = {r.id: r for r in software_requirements if r.type == RequirementType.SOFTWARE}
        risk_lookup = {r.id: r for r in risk_items}
        
        # Build reverse mappings for easier traversal
        feature_to_code = {}
        for link in matrix.links:
            if link.source_type == "code" and link.target_type == "feature":
                if link.target_id not in feature_to_code:
                    feature_to_code[link.target_id] = []
                feature_to_code[link.target_id].append(link)
        
        ur_to_features = {}
        for link in matrix.links:
            if link.source_type == "feature" and link.target_type == "requirement":
                if link.target_id not in ur_to_features:
                    ur_to_features[link.target_id] = []
                ur_to_features[link.target_id].append(link)
        
        sr_to_ur = {}
        for link in matrix.links:
            if (link.source_type == "requirement" and link.target_type == "requirement" and
                link.metadata.get("source_requirement_type") == "user" and
                link.metadata.get("target_requirement_type") == "software"):
                if link.target_id not in sr_to_ur:
                    sr_to_ur[link.target_id] = []
                sr_to_ur[link.target_id].append(link)
        
        risk_to_sr = {}
        for link in matrix.links:
            if link.source_type == "requirement" and link.target_type == "risk":
                if link.target_id not in risk_to_sr:
                    risk_to_sr[link.target_id] = []
                risk_to_sr[link.target_id].append(link)
        
        rows = []
        
        # Start from code references and trace forward
        processed_combinations = set()
        
        for feature in features:
            code_links = feature_to_code.get(feature.id, [])
            
            for code_link in code_links:
                # Get code reference details from metadata
                file_path = code_link.metadata.get("file_path", "")
                function_name = code_link.metadata.get("function_name", "")
                code_ref = code_link.source_id
                
                # Find user requirements linked to this feature
                ur_links = ur_to_features.get(feature.id, [])
                if not ur_links:
                    # Create row with no UR/SR/Risk
                    row = TraceabilityTableRow(
                        code_reference=code_ref,
                        file_path=file_path,
                        function_name=function_name,
                        feature_id=feature.id,
                        feature_description=feature.description,
                        user_requirement_id="",
                        user_requirement_text="",
                        software_requirement_id="",
                        software_requirement_text="",
                        risk_id="",
                        risk_hazard="",
                        confidence=code_link.confidence
                    )
                    rows.append(row)
                    continue
                
                for ur_link in ur_links:
                    ur = ur_lookup.get(ur_link.target_id)
                    if not ur:
                        continue
                    
                    # Find software requirements linked to this UR
                    sr_links = [link for link in matrix.links 
                              if (link.source_type == "requirement" and 
                                  link.target_type == "requirement" and
                                  link.source_id == ur.id)]
                    
                    if not sr_links:
                        # Create row with UR but no SR/Risk
                        row = TraceabilityTableRow(
                            code_reference=code_ref,
                            file_path=file_path,
                            function_name=function_name,
                            feature_id=feature.id,
                            feature_description=feature.description,
                            user_requirement_id=ur.id,
                            user_requirement_text=ur.text[:100] + "..." if len(ur.text) > 100 else ur.text,
                            software_requirement_id="",
                            software_requirement_text="",
                            risk_id="",
                            risk_hazard="",
                            confidence=min(code_link.confidence, ur_link.confidence)
                        )
                        rows.append(row)
                        continue
                    
                    for sr_link in sr_links:
                        sr = sr_lookup.get(sr_link.target_id)
                        if not sr:
                            continue
                        
                        # Find risks linked to this SR
                        risk_links = [link for link in matrix.links
                                    if (link.source_type == "requirement" and
                                        link.target_type == "risk" and
                                        link.source_id == sr.id)]
                        
                        if not risk_links:
                            # Create row with UR/SR but no Risk
                            row = TraceabilityTableRow(
                                code_reference=code_ref,
                                file_path=file_path,
                                function_name=function_name,
                                feature_id=feature.id,
                                feature_description=feature.description,
                                user_requirement_id=ur.id,
                                user_requirement_text=ur.text[:100] + "..." if len(ur.text) > 100 else ur.text,
                                software_requirement_id=sr.id,
                                software_requirement_text=sr.text[:100] + "..." if len(sr.text) > 100 else sr.text,
                                risk_id="",
                                risk_hazard="",
                                confidence=min(code_link.confidence, ur_link.confidence, sr_link.confidence)
                            )
                            rows.append(row)
                            continue
                        
                        for risk_link in risk_links:
                            risk = risk_lookup.get(risk_link.target_id)
                            if not risk:
                                continue
                            
                            # Create complete row
                            combination_key = f"{code_ref}|{feature.id}|{ur.id}|{sr.id}|{risk.id}"
                            if combination_key not in processed_combinations:
                                row = TraceabilityTableRow(
                                    code_reference=code_ref,
                                    file_path=file_path,
                                    function_name=function_name,
                                    feature_id=feature.id,
                                    feature_description=feature.description,
                                    user_requirement_id=ur.id,
                                    user_requirement_text=ur.text[:100] + "..." if len(ur.text) > 100 else ur.text,
                                    software_requirement_id=sr.id,
                                    software_requirement_text=sr.text[:100] + "..." if len(sr.text) > 100 else sr.text,
                                    risk_id=risk.id,
                                    risk_hazard=risk.hazard,
                                    confidence=min(code_link.confidence, ur_link.confidence, sr_link.confidence, risk_link.confidence)
                                )
                                rows.append(row)
                                processed_combinations.add(combination_key)
        
        self.logger.info(f"Generated {len(rows)} traceability table rows")
        return rows
    
    def export_to_csv(
        self, 
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem],
        include_metadata: bool = False
    ) -> str:
        """
        Export traceability matrix to CSV format.
        
        Args:
            matrix: The traceability matrix
            features: List of features
            user_requirements: List of user requirements
            software_requirements: List of software requirements
            risk_items: List of risk items
            include_metadata: Whether to include metadata columns
            
        Returns:
            CSV content as string
        """
        self.logger.info("Exporting traceability matrix to CSV")
        
        # Generate tabular data
        rows = self.generate_tabular_matrix(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        
        # Create CSV content
        output = io.StringIO()
        
        # Define headers
        headers = [
            "Code Reference",
            "File Path", 
            "Function Name",
            "Feature ID",
            "Feature Description",
            "User Requirement ID",
            "User Requirement Text",
            "Software Requirement ID", 
            "Software Requirement Text",
            "Risk ID",
            "Risk Hazard",
            "Confidence"
        ]
        
        if include_metadata:
            headers.extend([
                "Analysis Run ID",
                "Export Timestamp",
                "Total Links",
                "Link Types"
            ])
        
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # Write data rows
        for row in rows:
            csv_row = [
                row.code_reference,
                row.file_path,
                row.function_name,
                row.feature_id,
                row.feature_description,
                row.user_requirement_id,
                row.user_requirement_text,
                row.software_requirement_id,
                row.software_requirement_text,
                row.risk_id,
                row.risk_hazard,
                f"{row.confidence:.3f}"
            ]
            
            if include_metadata:
                # Get unique link types from matrix
                link_types = list(set(link.link_type for link in matrix.links))
                csv_row.extend([
                    str(matrix.analysis_run_id),
                    datetime.now().isoformat(),
                    str(len(matrix.links)),
                    "; ".join(link_types)
                ])
            
            writer.writerow(csv_row)
        
        csv_content = output.getvalue()
        output.close()
        
        self.logger.info(f"Exported {len(rows)} rows to CSV")
        return csv_content
    
    def detect_traceability_gaps(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityGap]:
        """
        Detect gaps and issues in traceability coverage.
        
        Args:
            matrix: The traceability matrix
            features: List of features
            user_requirements: List of user requirements
            software_requirements: List of software requirements
            risk_items: List of risk items
            
        Returns:
            List of detected traceability gaps
        """
        self.logger.info("Detecting traceability gaps")
        gaps = []
        
        # Create sets of linked entities
        linked_features = set()
        linked_user_requirements = set()
        linked_software_requirements = set()
        linked_risks = set()
        linked_code_refs = set()
        
        for link in matrix.links:
            if link.source_type == "code":
                linked_code_refs.add(link.source_id)
            elif link.source_type == "feature":
                linked_features.add(link.source_id)
            elif link.source_type == "requirement":
                if link.metadata.get("source_requirement_type") == "user":
                    linked_user_requirements.add(link.source_id)
                elif link.metadata.get("requirement_type") == "software":
                    linked_software_requirements.add(link.source_id)
            
            if link.target_type == "feature":
                linked_features.add(link.target_id)
            elif link.target_type == "requirement":
                if link.metadata.get("target_requirement_type") == "software":
                    linked_software_requirements.add(link.target_id)
                elif link.metadata.get("requirement_type") == "user":
                    linked_user_requirements.add(link.target_id)
            elif link.target_type == "risk":
                linked_risks.add(link.target_id)
        
        # 1. Check for orphaned features (no code evidence)
        all_code_refs = set()
        for feature in features:
            for evidence in feature.evidence:
                code_ref_id = self._generate_code_reference_id(evidence)
                all_code_refs.add(code_ref_id)
                
                if code_ref_id not in linked_code_refs:
                    gaps.append(TraceabilityGap(
                        gap_type="orphaned_code",
                        source_type="code",
                        source_id=code_ref_id,
                        description=f"Code reference {evidence.file_path}:{evidence.start_line}-{evidence.end_line} is not linked to any feature",
                        severity="medium",
                        recommendation="Verify if this code implements a feature or remove from analysis"
                    ))
        
        # 2. Check for features without user requirements
        for feature in features:
            if feature.id not in linked_features:
                gaps.append(TraceabilityGap(
                    gap_type="orphaned_feature",
                    source_type="feature",
                    source_id=feature.id,
                    description=f"Feature '{feature.description}' is not linked to any user requirement",
                    severity="high",
                    recommendation="Create user requirement for this feature or remove if not needed"
                ))
        
        # 3. Check for user requirements without software requirements
        for ur in user_requirements:
            if ur.type == RequirementType.USER and ur.id not in linked_user_requirements:
                gaps.append(TraceabilityGap(
                    gap_type="orphaned_requirement",
                    source_type="requirement",
                    source_id=ur.id,
                    description=f"User requirement '{ur.id}' is not linked to any software requirement",
                    severity="high",
                    recommendation="Create software requirements to implement this user requirement"
                ))
        
        # 4. Check for software requirements without risks
        for sr in software_requirements:
            if sr.type == RequirementType.SOFTWARE and sr.id not in linked_software_requirements:
                gaps.append(TraceabilityGap(
                    gap_type="orphaned_requirement",
                    source_type="requirement",
                    source_id=sr.id,
                    description=f"Software requirement '{sr.id}' is not linked to any risk",
                    severity="medium",
                    recommendation="Analyze potential risks for this requirement or mark as low-risk"
                ))
        
        # 5. Check for risks without requirements
        for risk in risk_items:
            if risk.id not in linked_risks:
                gaps.append(TraceabilityGap(
                    gap_type="orphaned_risk",
                    source_type="risk",
                    source_id=risk.id,
                    description=f"Risk '{risk.hazard}' is not linked to any software requirement",
                    severity="high",
                    recommendation="Link this risk to relevant software requirements or remove if not applicable"
                ))
        
        # 6. Check for weak links (low confidence)
        weak_threshold = 0.5
        for link in matrix.links:
            if link.confidence < weak_threshold:
                gaps.append(TraceabilityGap(
                    gap_type="weak_link",
                    source_type=link.source_type,
                    source_id=link.source_id,
                    target_type=link.target_type,
                    target_id=link.target_id,
                    description=f"Weak traceability link ({link.confidence:.2f}) between {link.source_type} '{link.source_id}' and {link.target_type} '{link.target_id}'",
                    severity="low",
                    recommendation="Review and strengthen this traceability link or provide additional evidence"
                ))
        
        # 7. Check for missing transitive links
        # Find features with code but no direct software requirement links
        for feature in features:
            has_code = len(feature.evidence) > 0
            has_ur_link = any(link.source_id == feature.id and link.target_type == "requirement" 
                            for link in matrix.links)
            
            if has_code and not has_ur_link:
                gaps.append(TraceabilityGap(
                    gap_type="missing_link",
                    source_type="feature",
                    source_id=feature.id,
                    target_type="requirement",
                    description=f"Feature '{feature.description}' has code evidence but no requirement links",
                    severity="high",
                    recommendation="Create user requirement for this implemented feature"
                ))
        
        self.logger.info(f"Detected {len(gaps)} traceability gaps")
        return gaps
    
    def generate_gap_report(self, gaps: List[TraceabilityGap]) -> str:
        """
        Generate a human-readable gap analysis report.
        
        Args:
            gaps: List of detected gaps
            
        Returns:
            Formatted gap report as string
        """
        if not gaps:
            return "No traceability gaps detected. Traceability matrix is complete."
        
        # Group gaps by severity
        high_gaps = [g for g in gaps if g.severity == "high"]
        medium_gaps = [g for g in gaps if g.severity == "medium"]
        low_gaps = [g for g in gaps if g.severity == "low"]
        
        # Group gaps by type
        gap_types = {}
        for gap in gaps:
            if gap.gap_type not in gap_types:
                gap_types[gap.gap_type] = []
            gap_types[gap.gap_type].append(gap)
        
        report = []
        report.append("TRACEABILITY GAP ANALYSIS REPORT")
        report.append("=" * 40)
        report.append(f"Total gaps detected: {len(gaps)}")
        report.append(f"High severity: {len(high_gaps)}")
        report.append(f"Medium severity: {len(medium_gaps)}")
        report.append(f"Low severity: {len(low_gaps)}")
        report.append("")
        
        # Summary by gap type
        report.append("GAP TYPES SUMMARY:")
        report.append("-" * 20)
        for gap_type, type_gaps in gap_types.items():
            report.append(f"{gap_type.replace('_', ' ').title()}: {len(type_gaps)} gaps")
        report.append("")
        
        # Detailed gaps by severity
        for severity, severity_gaps in [("high", high_gaps), ("medium", medium_gaps), ("low", low_gaps)]:
            if not severity_gaps:
                continue
                
            report.append(f"{severity.upper()} SEVERITY GAPS:")
            report.append("-" * 25)
            
            for i, gap in enumerate(severity_gaps, 1):
                report.append(f"{i}. {gap.description}")
                report.append(f"   Type: {gap.gap_type}")
                report.append(f"   Source: {gap.source_type} '{gap.source_id}'")
                if gap.target_type and gap.target_id:
                    report.append(f"   Target: {gap.target_type} '{gap.target_id}'")
                report.append(f"   Recommendation: {gap.recommendation}")
                report.append("")
        
        return "\n".join(report)