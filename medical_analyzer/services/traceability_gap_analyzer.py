"""
Traceability gap analyzer for comprehensive gap detection and analysis.

This service identifies missing links, orphaned elements, and weak traceability
relationships in the traceability matrix with severity assessment and recommendations.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.core import (
    TraceabilityLink, CodeReference, Feature, Requirement, RiskItem,
    RequirementType
)
from .traceability_models import TraceabilityMatrix, TraceabilityGap


logger = logging.getLogger(__name__)


class GapType(Enum):
    """Types of traceability gaps."""
    ORPHANED_CODE = "orphaned_code"
    ORPHANED_FEATURE = "orphaned_feature"
    ORPHANED_REQUIREMENT = "orphaned_requirement"
    ORPHANED_RISK = "orphaned_risk"
    MISSING_LINK = "missing_link"
    WEAK_LINK = "weak_link"
    BROKEN_CHAIN = "broken_chain"
    DUPLICATE_LINK = "duplicate_link"


class GapSeverity(Enum):
    """Gap severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GapAnalysisResult:
    """Result of gap analysis with detailed metrics."""
    gaps: List[TraceabilityGap]
    total_gaps: int
    gaps_by_severity: Dict[str, int]
    gaps_by_type: Dict[str, int]
    coverage_metrics: Dict[str, float]
    recommendations: List[str]
    analysis_metadata: Dict[str, Any]


@dataclass
class CoverageMetrics:
    """Traceability coverage metrics."""
    code_coverage: float  # % of code with feature links
    feature_coverage: float  # % of features with requirement links
    requirement_coverage: float  # % of requirements with risk links
    end_to_end_coverage: float  # % of complete chains
    confidence_score: float  # Average confidence across all links
    completeness_score: float  # Overall completeness percentage


class TraceabilityGapAnalyzer:
    """Comprehensive traceability gap analysis service."""
    
    def __init__(self):
        """Initialize the gap analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration thresholds
        self.weak_confidence_threshold = 0.5
        self.low_confidence_threshold = 0.3
        self.minimum_chain_length = 3  # Code -> Feature -> Requirement -> Risk
        
    def analyze_gaps(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem],
        code_references: Optional[List[CodeReference]] = None
    ) -> GapAnalysisResult:
        """
        Perform comprehensive gap analysis on traceability matrix.
        
        Args:
            matrix: The traceability matrix to analyze
            features: List of extracted features
            user_requirements: List of user requirements
            software_requirements: List of software requirements
            risk_items: List of identified risks
            code_references: Optional list of code references
            
        Returns:
            Comprehensive gap analysis result
        """
        self.logger.info("Starting comprehensive traceability gap analysis")
        
        gaps = []
        
        # 1. Detect orphaned elements
        orphaned_gaps = self._detect_orphaned_elements(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        gaps.extend(orphaned_gaps)
        
        # 2. Detect missing links
        missing_link_gaps = self._detect_missing_links(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        gaps.extend(missing_link_gaps)
        
        # 3. Detect weak links
        weak_link_gaps = self._detect_weak_links(matrix)
        gaps.extend(weak_link_gaps)
        
        # 4. Detect broken chains
        broken_chain_gaps = self._detect_broken_chains(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        gaps.extend(broken_chain_gaps)
        
        # 5. Detect duplicate links
        duplicate_gaps = self._detect_duplicate_links(matrix)
        gaps.extend(duplicate_gaps)
        
        # 6. Calculate coverage metrics
        coverage_metrics = self._calculate_coverage_metrics(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        
        # 7. Generate recommendations
        recommendations = self._generate_recommendations(gaps, coverage_metrics)
        
        # 8. Compile results
        gaps_by_severity = self._count_gaps_by_severity(gaps)
        gaps_by_type = self._count_gaps_by_type(gaps)
        
        result = GapAnalysisResult(
            gaps=gaps,
            total_gaps=len(gaps),
            gaps_by_severity=gaps_by_severity,
            gaps_by_type=gaps_by_type,
            coverage_metrics=coverage_metrics.__dict__,
            recommendations=recommendations,
            analysis_metadata={
                "analysis_timestamp": matrix.created_at.isoformat(),
                "total_links": len(matrix.links),
                "weak_confidence_threshold": self.weak_confidence_threshold,
                "analyzer_version": "1.0"
            }
        )
        
        self.logger.info(f"Gap analysis completed: {len(gaps)} gaps detected")
        return result
        
    def _detect_orphaned_elements(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityGap]:
        """Detect orphaned elements (elements without proper links)."""
        gaps = []
        
        # Build sets of linked elements
        linked_elements = self._build_linked_elements_sets(matrix)
        
        # 1. Orphaned code references
        all_code_refs = set()
        for feature in features:
            for evidence in feature.evidence:
                code_ref_id = f"{evidence.file_path}:{evidence.start_line}-{evidence.end_line}"
                all_code_refs.add(code_ref_id)
                
                if code_ref_id not in linked_elements["code"]:
                    gaps.append(TraceabilityGap(
                        gap_type=GapType.ORPHANED_CODE.value,
                        source_type="code",
                        source_id=code_ref_id,
                        description=f"Code reference {evidence.file_path}:{evidence.start_line}-{evidence.end_line} in function '{evidence.function_name}' is not linked to any feature",
                        severity=GapSeverity.MEDIUM.value,
                        recommendation="Review if this code implements a feature or remove from analysis scope"
                    ))
        
        # 2. Orphaned features
        for feature in features:
            if feature.id not in linked_elements["features"]:
                gaps.append(TraceabilityGap(
                    gap_type=GapType.ORPHANED_FEATURE.value,
                    source_type="feature",
                    source_id=feature.id,
                    description=f"Feature '{feature.description}' (Category: {feature.category}) is not linked to any user requirement",
                    severity=GapSeverity.HIGH.value,
                    recommendation="Create user requirement for this feature or remove if not needed for the system"
                ))
        
        # 3. Orphaned user requirements
        for ur in user_requirements:
            if ur.type == RequirementType.USER and ur.id not in linked_elements["user_requirements"]:
                gaps.append(TraceabilityGap(
                    gap_type=GapType.ORPHANED_REQUIREMENT.value,
                    source_type="requirement",
                    source_id=ur.id,
                    description=f"User requirement '{ur.id}' is not linked to any software requirement",
                    severity=GapSeverity.HIGH.value,
                    recommendation="Create software requirements to implement this user requirement or mark as future enhancement"
                ))
        
        # 4. Orphaned software requirements
        for sr in software_requirements:
            if sr.type == RequirementType.SOFTWARE:
                # Check if linked to user requirements (backward)
                has_ur_link = sr.id in linked_elements["software_requirements_from_ur"]
                # Check if linked to risks (forward)
                has_risk_link = sr.id in linked_elements["software_requirements_to_risk"]
                
                if not has_ur_link:
                    gaps.append(TraceabilityGap(
                        gap_type=GapType.ORPHANED_REQUIREMENT.value,
                        source_type="requirement",
                        source_id=sr.id,
                        description=f"Software requirement '{sr.id}' is not derived from any user requirement",
                        severity=GapSeverity.HIGH.value,
                        recommendation="Link to appropriate user requirement or verify if this is a derived technical requirement"
                    ))
                
                if not has_risk_link:
                    gaps.append(TraceabilityGap(
                        gap_type=GapType.ORPHANED_REQUIREMENT.value,
                        source_type="requirement",
                        source_id=sr.id,
                        description=f"Software requirement '{sr.id}' is not linked to any risk assessment",
                        severity=GapSeverity.MEDIUM.value,
                        recommendation="Analyze potential risks for this requirement or document as low-risk with justification"
                    ))
        
        # 5. Orphaned risks
        for risk in risk_items:
            if risk.id not in linked_elements["risks"]:
                gaps.append(TraceabilityGap(
                    gap_type=GapType.ORPHANED_RISK.value,
                    source_type="risk",
                    source_id=risk.id,
                    description=f"Risk '{risk.hazard}' (Severity: {risk.severity}) is not linked to any software requirement",
                    severity=GapSeverity.HIGH.value,
                    recommendation="Link this risk to relevant software requirements or remove if not applicable to current system scope"
                ))
        
        return gaps
        
    def _detect_missing_links(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityGap]:
        """Detect missing traceability links in expected chains."""
        gaps = []
        
        # 1. Features with code but no requirements
        for feature in features:
            has_code = len(feature.evidence) > 0
            has_ur_link = any(
                link.source_id == feature.id and link.target_type == "requirement"
                for link in matrix.links
            )
            
            if has_code and not has_ur_link:
                gaps.append(TraceabilityGap(
                    gap_type=GapType.MISSING_LINK.value,
                    source_type="feature",
                    source_id=feature.id,
                    target_type="requirement",
                    description=f"Feature '{feature.description}' has code evidence but no requirement links",
                    severity=GapSeverity.HIGH.value,
                    recommendation="Create user requirement for this implemented feature to ensure traceability"
                ))
        
        # 2. User requirements without software requirements
        for ur in user_requirements:
            if ur.type == RequirementType.USER:
                has_sr_link = any(
                    link.source_id == ur.id and 
                    link.target_type == "requirement" and
                    link.metadata.get("target_requirement_type") == "software"
                    for link in matrix.links
                )
                
                if not has_sr_link:
                    gaps.append(TraceabilityGap(
                        gap_type=GapType.MISSING_LINK.value,
                        source_type="requirement",
                        source_id=ur.id,
                        target_type="requirement",
                        description=f"User requirement '{ur.id}' has no derived software requirements",
                        severity=GapSeverity.HIGH.value,
                        recommendation="Decompose this user requirement into specific software requirements"
                    ))
        
        # 3. High-risk items without sufficient requirement coverage
        high_risks = [r for r in risk_items if hasattr(r.severity, 'value') and r.severity.value in ['Serious', 'Catastrophic']]
        for risk in high_risks:
            linked_requirements = [
                link.source_id for link in matrix.links
                if link.target_id == risk.id and link.source_type == "requirement"
            ]
            
            if len(linked_requirements) < 2:  # High risks should have multiple mitigating requirements
                gaps.append(TraceabilityGap(
                    gap_type=GapType.MISSING_LINK.value,
                    source_type="risk",
                    source_id=risk.id,
                    target_type="requirement",
                    description=f"High severity risk '{risk.hazard}' has insufficient requirement coverage ({len(linked_requirements)} requirements)",
                    severity=GapSeverity.HIGH.value,
                    recommendation="Add additional software requirements to adequately mitigate this high-severity risk"
                ))
        
        return gaps
        
    def _detect_weak_links(self, matrix: TraceabilityMatrix) -> List[TraceabilityGap]:
        """Detect weak traceability links based on confidence scores."""
        gaps = []
        
        for link in matrix.links:
            if link.confidence < self.low_confidence_threshold:
                severity = GapSeverity.HIGH.value
                recommendation = "Review and strengthen this link with additional evidence or remove if invalid"
            elif link.confidence < self.weak_confidence_threshold:
                severity = GapSeverity.MEDIUM.value
                recommendation = "Review this link and provide additional evidence to increase confidence"
            else:
                continue  # Link is strong enough
                
            gaps.append(TraceabilityGap(
                gap_type=GapType.WEAK_LINK.value,
                source_type=link.source_type,
                source_id=link.source_id,
                target_type=link.target_type,
                target_id=link.target_id,
                description=f"Weak traceability link (confidence: {link.confidence:.2f}) between {link.source_type} '{link.source_id}' and {link.target_type} '{link.target_id}'",
                severity=severity,
                recommendation=recommendation
            ))
        
        return gaps
        
    def _detect_broken_chains(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> List[TraceabilityGap]:
        """Detect broken traceability chains."""
        gaps = []
        
        # Build chain mappings
        code_to_feature = {}
        feature_to_ur = {}
        ur_to_sr = {}
        sr_to_risk = {}
        
        for link in matrix.links:
            if link.source_type == "code" and link.target_type == "feature":
                if link.source_id not in code_to_feature:
                    code_to_feature[link.source_id] = []
                code_to_feature[link.source_id].append(link.target_id)
                
            elif link.source_type == "feature" and link.target_type == "requirement":
                if link.source_id not in feature_to_ur:
                    feature_to_ur[link.source_id] = []
                feature_to_ur[link.source_id].append(link.target_id)
                
            elif (link.source_type == "requirement" and link.target_type == "requirement" and
                  link.metadata.get("source_requirement_type") == "user" and
                  link.metadata.get("target_requirement_type") == "software"):
                if link.source_id not in ur_to_sr:
                    ur_to_sr[link.source_id] = []
                ur_to_sr[link.source_id].append(link.target_id)
                
            elif link.source_type == "requirement" and link.target_type == "risk":
                if link.source_id not in sr_to_risk:
                    sr_to_risk[link.source_id] = []
                sr_to_risk[link.source_id].append(link.target_id)
        
        # Check for broken chains starting from features with code
        for feature in features:
            if not feature.evidence:  # No code evidence
                continue
                
            # Check if feature leads to complete chain
            ur_ids = feature_to_ur.get(feature.id, [])
            if not ur_ids:
                continue  # Already detected as missing link
                
            for ur_id in ur_ids:
                sr_ids = ur_to_sr.get(ur_id, [])
                if not sr_ids:
                    gaps.append(TraceabilityGap(
                        gap_type=GapType.BROKEN_CHAIN.value,
                        source_type="feature",
                        source_id=feature.id,
                        target_type="requirement",
                        target_id=ur_id,
                        description=f"Broken chain: Feature '{feature.id}' → UR '{ur_id}' has no software requirements",
                        severity=GapSeverity.HIGH.value,
                        recommendation="Create software requirements to complete the traceability chain"
                    ))
                    continue
                    
                for sr_id in sr_ids:
                    risk_ids = sr_to_risk.get(sr_id, [])
                    if not risk_ids:
                        gaps.append(TraceabilityGap(
                            gap_type=GapType.BROKEN_CHAIN.value,
                            source_type="requirement",
                            source_id=sr_id,
                            description=f"Broken chain: Complete chain Feature '{feature.id}' → UR '{ur_id}' → SR '{sr_id}' has no risk assessment",
                            severity=GapSeverity.MEDIUM.value,
                            recommendation="Perform risk analysis for this software requirement to complete the chain"
                        ))
        
        return gaps
        
    def _detect_duplicate_links(self, matrix: TraceabilityMatrix) -> List[TraceabilityGap]:
        """Detect duplicate traceability links."""
        gaps = []
        seen_links = set()
        
        for link in matrix.links:
            link_signature = (link.source_type, link.source_id, link.target_type, link.target_id)
            
            if link_signature in seen_links:
                gaps.append(TraceabilityGap(
                    gap_type=GapType.DUPLICATE_LINK.value,
                    source_type=link.source_type,
                    source_id=link.source_id,
                    target_type=link.target_type,
                    target_id=link.target_id,
                    description=f"Duplicate link between {link.source_type} '{link.source_id}' and {link.target_type} '{link.target_id}'",
                    severity=GapSeverity.LOW.value,
                    recommendation="Remove duplicate link to clean up traceability matrix"
                ))
            else:
                seen_links.add(link_signature)
        
        return gaps
        
    def _build_linked_elements_sets(self, matrix: TraceabilityMatrix) -> Dict[str, Set[str]]:
        """Build sets of linked elements for orphan detection."""
        linked = {
            "code": set(),
            "features": set(),
            "user_requirements": set(),
            "software_requirements_from_ur": set(),
            "software_requirements_to_risk": set(),
            "risks": set()
        }
        
        for link in matrix.links:
            if link.source_type == "code":
                linked["code"].add(link.source_id)
            elif link.source_type == "feature":
                linked["features"].add(link.source_id)
            elif link.source_type == "requirement":
                if link.metadata.get("source_requirement_type") == "user":
                    linked["user_requirements"].add(link.source_id)
                elif link.metadata.get("requirement_type") == "software":
                    linked["software_requirements_to_risk"].add(link.source_id)
            
            if link.target_type == "feature":
                linked["features"].add(link.target_id)
            elif link.target_type == "requirement":
                if link.metadata.get("target_requirement_type") == "software":
                    linked["software_requirements_from_ur"].add(link.target_id)
            elif link.target_type == "risk":
                linked["risks"].add(link.target_id)
        
        return linked
        
    def _calculate_coverage_metrics(
        self,
        matrix: TraceabilityMatrix,
        features: List[Feature],
        user_requirements: List[Requirement],
        software_requirements: List[Requirement],
        risk_items: List[RiskItem]
    ) -> CoverageMetrics:
        """Calculate comprehensive coverage metrics."""
        
        # Count elements with links
        linked_elements = self._build_linked_elements_sets(matrix)
        
        # Code coverage (features with code evidence that have requirement links)
        features_with_code = [f for f in features if f.evidence]
        linked_features_with_code = [f for f in features_with_code if f.id in linked_elements["features"]]
        code_coverage = len(linked_features_with_code) / len(features_with_code) if features_with_code else 0.0
        
        # Feature coverage (features linked to requirements)
        feature_coverage = len(linked_elements["features"]) / len(features) if features else 0.0
        
        # Requirement coverage (software requirements linked to risks)
        sr_count = len([r for r in software_requirements if r.type == RequirementType.SOFTWARE])
        requirement_coverage = len(linked_elements["software_requirements_to_risk"]) / sr_count if sr_count else 0.0
        
        # End-to-end coverage (complete chains from code to risk)
        complete_chains = self._count_complete_chains(matrix, features)
        total_possible_chains = len(features_with_code)
        end_to_end_coverage = complete_chains / total_possible_chains if total_possible_chains else 0.0
        
        # Average confidence
        confidences = [link.confidence for link in matrix.links if link.confidence > 0]
        confidence_score = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Overall completeness
        completeness_score = (code_coverage + feature_coverage + requirement_coverage + end_to_end_coverage) / 4.0
        
        return CoverageMetrics(
            code_coverage=code_coverage,
            feature_coverage=feature_coverage,
            requirement_coverage=requirement_coverage,
            end_to_end_coverage=end_to_end_coverage,
            confidence_score=confidence_score,
            completeness_score=completeness_score
        )
        
    def _count_complete_chains(self, matrix: TraceabilityMatrix, features: List[Feature]) -> int:
        """Count the number of complete traceability chains."""
        complete_chains = 0
        
        # Build chain mappings
        feature_to_ur = {}
        ur_to_sr = {}
        sr_to_risk = {}
        
        for link in matrix.links:
            if link.source_type == "feature" and link.target_type == "requirement":
                if link.source_id not in feature_to_ur:
                    feature_to_ur[link.source_id] = []
                feature_to_ur[link.source_id].append(link.target_id)
                
            elif (link.source_type == "requirement" and link.target_type == "requirement" and
                  link.metadata.get("source_requirement_type") == "user"):
                if link.source_id not in ur_to_sr:
                    ur_to_sr[link.source_id] = []
                ur_to_sr[link.source_id].append(link.target_id)
                
            elif link.source_type == "requirement" and link.target_type == "risk":
                if link.source_id not in sr_to_risk:
                    sr_to_risk[link.source_id] = []
                sr_to_risk[link.source_id].append(link.target_id)
        
        # Count complete chains
        for feature in features:
            if not feature.evidence:  # Only count features with code
                continue
                
            ur_ids = feature_to_ur.get(feature.id, [])
            for ur_id in ur_ids:
                sr_ids = ur_to_sr.get(ur_id, [])
                for sr_id in sr_ids:
                    risk_ids = sr_to_risk.get(sr_id, [])
                    if risk_ids:  # Complete chain found
                        complete_chains += 1
                        break  # Count each feature only once
                if risk_ids:
                    break
        
        return complete_chains
        
    def _generate_recommendations(self, gaps: List[TraceabilityGap], coverage_metrics: CoverageMetrics) -> List[str]:
        """Generate actionable recommendations based on gap analysis."""
        recommendations = []
        
        # High-level recommendations based on coverage
        if coverage_metrics.completeness_score < 0.5:
            recommendations.append("Overall traceability completeness is low (<50%). Focus on establishing basic traceability links before detailed analysis.")
        
        if coverage_metrics.code_coverage < 0.7:
            recommendations.append("Many code features lack requirement links. Review feature extraction and ensure all implemented features have corresponding requirements.")
        
        if coverage_metrics.confidence_score < 0.6:
            recommendations.append("Average link confidence is low. Review traceability links and strengthen evidence for key relationships.")
        
        # Specific recommendations based on gap types
        gap_types = self._count_gaps_by_type(gaps)
        
        if gap_types.get("orphaned_requirement", 0) > 5:
            recommendations.append("High number of orphaned requirements detected. Review requirement derivation and ensure proper parent-child relationships.")
        
        if gap_types.get("weak_link", 0) > 10:
            recommendations.append("Many weak traceability links found. Consider improving feature extraction algorithms or providing additional evidence.")
        
        if gap_types.get("missing_link", 0) > 0:
            recommendations.append("Missing critical traceability links detected. Prioritize completing these links to ensure regulatory compliance.")
        
        # Severity-based recommendations
        gaps_by_severity = self._count_gaps_by_severity(gaps)
        
        if gaps_by_severity.get("high", 0) > 0:
            recommendations.append(f"Address {gaps_by_severity['high']} high-severity gaps immediately as they may impact regulatory compliance.")
        
        if gaps_by_severity.get("critical", 0) > 0:
            recommendations.append(f"URGENT: {gaps_by_severity['critical']} critical gaps require immediate attention before system release.")
        
        return recommendations
        
    def _count_gaps_by_severity(self, gaps: List[TraceabilityGap]) -> Dict[str, int]:
        """Count gaps by severity level."""
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for gap in gaps:
            counts[gap.severity] = counts.get(gap.severity, 0) + 1
        return counts
        
    def _count_gaps_by_type(self, gaps: List[TraceabilityGap]) -> Dict[str, int]:
        """Count gaps by type."""
        counts = {}
        for gap in gaps:
            counts[gap.gap_type] = counts.get(gap.gap_type, 0) + 1
        return counts
        
    def generate_gap_summary_report(self, analysis_result: GapAnalysisResult) -> str:
        """Generate a concise gap summary report."""
        lines = []
        lines.append("TRACEABILITY GAP ANALYSIS SUMMARY")
        lines.append("=" * 40)
        lines.append(f"Total Gaps: {analysis_result.total_gaps}")
        lines.append("")
        
        # Severity breakdown
        lines.append("By Severity:")
        for severity, count in analysis_result.gaps_by_severity.items():
            lines.append(f"  {severity.title()}: {count}")
        lines.append("")
        
        # Type breakdown
        lines.append("By Type:")
        for gap_type, count in analysis_result.gaps_by_type.items():
            lines.append(f"  {gap_type.replace('_', ' ').title()}: {count}")
        lines.append("")
        
        # Coverage metrics
        lines.append("Coverage Metrics:")
        for metric, value in analysis_result.coverage_metrics.items():
            if isinstance(value, float):
                lines.append(f"  {metric.replace('_', ' ').title()}: {value:.1%}")
        lines.append("")
        
        # Top recommendations
        if analysis_result.recommendations:
            lines.append("Key Recommendations:")
            for i, rec in enumerate(analysis_result.recommendations[:3], 1):
                lines.append(f"  {i}. {rec}")
        
        return "\n".join(lines)
        
    def export_detailed_gap_report(self, analysis_result: GapAnalysisResult, filename: str) -> bool:
        """Export detailed gap analysis report to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("DETAILED TRACEABILITY GAP ANALYSIS REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                # Summary
                f.write(self.generate_gap_summary_report(analysis_result))
                f.write("\n\n")
                
                # Detailed gaps by severity
                for severity in ["critical", "high", "medium", "low"]:
                    severity_gaps = [g for g in analysis_result.gaps if g.severity == severity]
                    if not severity_gaps:
                        continue
                        
                    f.write(f"{severity.upper()} SEVERITY GAPS\n")
                    f.write("-" * 30 + "\n")
                    
                    for i, gap in enumerate(severity_gaps, 1):
                        f.write(f"{i}. {gap.description}\n")
                        f.write(f"   Type: {gap.gap_type}\n")
                        f.write(f"   Source: {gap.source_type} '{gap.source_id}'\n")
                        if gap.target_type and gap.target_id:
                            f.write(f"   Target: {gap.target_type} '{gap.target_id}'\n")
                        f.write(f"   Recommendation: {gap.recommendation}\n\n")
                
                # Recommendations
                f.write("ACTIONABLE RECOMMENDATIONS\n")
                f.write("-" * 30 + "\n")
                for i, rec in enumerate(analysis_result.recommendations, 1):
                    f.write(f"{i}. {rec}\n")
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to export gap report: {e}")
            return False