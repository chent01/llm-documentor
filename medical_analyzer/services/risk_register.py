"""
Risk register generation and management service.

This module handles the generation, filtering, and export of risk registers
following ISO 14971 compliance requirements for medical device software.
"""

import csv
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ..models.core import RiskItem, Requirement
from ..models.enums import Severity, Probability, RiskLevel
from ..models.result_models import HazardIdentificationResult
from .hazard_identifier import HazardIdentifier


class RiskRegisterResult:
    """Result of risk register generation process."""
    
    def __init__(self, risk_items: List[RiskItem], metadata: Dict[str, Any]):
        self.risk_items = risk_items
        self.metadata = metadata
        self.generation_time = datetime.now()
    
    @property
    def total_risks(self) -> int:
        """Total number of risks in the register."""
        return len(self.risk_items)
    
    @property
    def high_priority_risks(self) -> List[RiskItem]:
        """Get high priority risks (Unacceptable level)."""
        return [r for r in self.risk_items if r.risk_level == RiskLevel.UNACCEPTABLE]
    
    @property
    def medium_priority_risks(self) -> List[RiskItem]:
        """Get medium priority risks (Undesirable level)."""
        return [r for r in self.risk_items if r.risk_level == RiskLevel.UNDESIRABLE]
    
    @property
    def low_priority_risks(self) -> List[RiskItem]:
        """Get low priority risks (Acceptable and Negligible levels)."""
        return [r for r in self.risk_items if r.risk_level in [RiskLevel.ACCEPTABLE, RiskLevel.NEGLIGIBLE]]


class RiskRegister:
    """Service for generating and managing ISO 14971 compliant risk registers."""
    
    def __init__(self, hazard_identifier: Optional[HazardIdentifier] = None):
        """
        Initialize the risk register service.
        
        Args:
            hazard_identifier: Optional hazard identifier service for generating new risks
        """
        self.hazard_identifier = hazard_identifier
    
    def generate_risk_register(self, 
                             software_requirements: List[Requirement], 
                             project_description: str = "",
                             include_mitigation_strategies: bool = True) -> RiskRegisterResult:
        """
        Generate a complete risk register from Software Requirements.
        
        Args:
            software_requirements: List of Software Requirements to analyze
            project_description: Description of the project context
            include_mitigation_strategies: Whether to include mitigation strategies
            
        Returns:
            RiskRegisterResult with generated risk register and metadata
        """
        if not self.hazard_identifier:
            raise ValueError("HazardIdentifier is required for risk register generation")
        
        # Identify hazards using the hazard identifier
        hazard_result = self.hazard_identifier.identify_hazards(
            software_requirements, project_description
        )
        
        # Enhance risk items with additional ISO 14971 compliance features
        enhanced_risks = self._enhance_risk_items(hazard_result.risk_items, include_mitigation_strategies)
        
        # Generate metadata
        metadata = {
            'generation_method': 'automated_llm',
            'total_requirements_analyzed': len(software_requirements),
            'hazard_identification_confidence': hazard_result.confidence_score,
            'processing_time': hazard_result.processing_time,
            'iso_14971_compliant': True,
            'mitigation_strategies_included': include_mitigation_strategies,
            'risk_statistics': self._calculate_risk_statistics(enhanced_risks),
            'generation_timestamp': datetime.now().isoformat(),
            'errors': hazard_result.errors
        }
        
        return RiskRegisterResult(enhanced_risks, metadata)
    
    def _enhance_risk_items(self, risk_items: List[RiskItem], include_mitigation: bool) -> List[RiskItem]:
        """Enhance risk items with additional ISO 14971 compliance features."""
        enhanced_risks = []
        
        for risk in risk_items:
            # Calculate residual risk
            mitigation_effectiveness = self._estimate_mitigation_effectiveness(risk.mitigation)
            residual_severity = self._reduce_severity(risk.severity, mitigation_effectiveness)
            residual_probability = self._reduce_probability(risk.probability, mitigation_effectiveness)
            residual_risk_level = self._calculate_risk_level(residual_severity, residual_probability)
            
            # Determine risk acceptability
            acceptability_data = self._determine_risk_acceptability(risk)
            
            # Create enhanced copy with new ISO 14971 fields
            enhanced_risk = RiskItem(
                id=risk.id,
                hazard=risk.hazard,
                cause=risk.cause,
                effect=risk.effect,
                severity=risk.severity,
                probability=risk.probability,
                risk_level=risk.risk_level,
                mitigation=risk.mitigation if include_mitigation else "",
                verification=risk.verification if include_mitigation else "",
                related_requirements=risk.related_requirements.copy(),
                metadata=risk.metadata.copy(),
                # New ISO 14971 specific fields
                risk_control_measures=self._extract_risk_control_measures(risk.mitigation),
                residual_risk_severity=residual_severity,
                residual_risk_probability=residual_probability,
                residual_risk_level=residual_risk_level,
                risk_acceptability="Acceptable" if acceptability_data.get('acceptable', False) else "Not Acceptable",
                risk_control_effectiveness=mitigation_effectiveness,
                post_market_surveillance=self._generate_surveillance_plan(risk),
                risk_benefit_analysis=self._generate_risk_benefit_analysis(risk)
            )
            
            # Add ISO 14971 specific metadata
            enhanced_risk.metadata.update({
                'iso_14971_compliant': True,
                'risk_number': risk.id,
                'risk_score': self._calculate_detailed_risk_score(risk),
                'residual_risk_assessment': self._assess_residual_risk(risk),
                'risk_acceptability': self._determine_risk_acceptability(risk),
                'post_mitigation_severity': self._estimate_post_mitigation_severity(risk),
                'post_mitigation_probability': self._estimate_post_mitigation_probability(risk)
            })
            
            enhanced_risks.append(enhanced_risk)
        
        return enhanced_risks
    
    def _calculate_detailed_risk_score(self, risk: RiskItem) -> Dict[str, Any]:
        """Calculate detailed risk score with multiple metrics."""
        severity_values = {
            Severity.CATASTROPHIC: 4,
            Severity.SERIOUS: 3,
            Severity.MINOR: 2,
            Severity.NEGLIGIBLE: 1
        }
        
        probability_values = {
            Probability.HIGH: 4,
            Probability.MEDIUM: 3,
            Probability.LOW: 2,
            Probability.REMOTE: 1
        }
        
        severity_score = severity_values[risk.severity]
        probability_score = probability_values[risk.probability]
        raw_score = severity_score * probability_score
        
        return {
            'raw_score': raw_score,
            'severity_score': severity_score,
            'probability_score': probability_score,
            'normalized_score': raw_score / 16.0,  # Normalize to 0-1 scale
            'risk_priority': self._get_risk_priority_number(raw_score)
        }
    
    def _get_risk_priority_number(self, raw_score: int) -> int:
        """Get risk priority number (RPN) for sorting."""
        # Higher scores = higher priority
        if raw_score >= 12:  # Catastrophic/High, Catastrophic/Medium, Serious/High
            return 1  # Highest priority
        elif raw_score >= 8:  # Serious/Medium, Catastrophic/Low, Minor/High
            return 2  # High priority
        elif raw_score >= 4:  # Serious/Low, Minor/Medium, Catastrophic/Remote
            return 3  # Medium priority
        else:  # Minor/Low, Minor/Remote, Negligible/*
            return 4  # Low priority
    
    def _assess_residual_risk(self, risk: RiskItem) -> Dict[str, Any]:
        """Assess residual risk after mitigation."""
        # Estimate residual risk based on mitigation quality
        mitigation_effectiveness = self._estimate_mitigation_effectiveness(risk.mitigation)
        
        # Reduce severity and probability based on mitigation effectiveness
        residual_severity = self._reduce_severity(risk.severity, mitigation_effectiveness)
        residual_probability = self._reduce_probability(risk.probability, mitigation_effectiveness)
        
        return {
            'residual_severity': residual_severity.value,
            'residual_probability': residual_probability.value,
            'mitigation_effectiveness': mitigation_effectiveness,
            'residual_risk_level': self._calculate_risk_level(residual_severity, residual_probability).value
        }
    
    def _estimate_mitigation_effectiveness(self, mitigation: str) -> float:
        """Estimate mitigation effectiveness based on content analysis."""
        if not mitigation:
            return 0.0
        
        mitigation_lower = mitigation.lower()
        effectiveness = 0.3  # Base effectiveness
        
        # High-effectiveness indicators
        high_effectiveness_terms = [
            'redundant', 'backup', 'failsafe', 'automatic', 'monitoring',
            'validation', 'verification', 'testing', 'review', 'independent'
        ]
        
        # Medium-effectiveness indicators
        medium_effectiveness_terms = [
            'check', 'control', 'limit', 'prevent', 'detect', 'alert',
            'notification', 'warning', 'guidance', 'training'
        ]
        
        # Count effectiveness indicators
        high_count = sum(1 for term in high_effectiveness_terms if term in mitigation_lower)
        medium_count = sum(1 for term in medium_effectiveness_terms if term in mitigation_lower)
        
        # Calculate effectiveness score
        effectiveness += high_count * 0.2  # High-impact terms
        effectiveness += medium_count * 0.1  # Medium-impact terms
        
        # Cap at 0.9 (no mitigation is 100% effective)
        return min(effectiveness, 0.9)
    
    def _reduce_severity(self, severity: Severity, effectiveness: float) -> Severity:
        """Reduce severity based on mitigation effectiveness."""
        if effectiveness < 0.3:
            return severity  # No reduction
        
        severity_order = [Severity.NEGLIGIBLE, Severity.MINOR, Severity.SERIOUS, Severity.CATASTROPHIC]
        current_index = severity_order.index(severity)
        
        if effectiveness >= 0.7:
            # High effectiveness: reduce by 2 levels
            new_index = max(0, current_index - 2)
        elif effectiveness >= 0.5:
            # Medium effectiveness: reduce by 1 level
            new_index = max(0, current_index - 1)
        else:
            # Low effectiveness: no reduction
            new_index = current_index
        
        return severity_order[new_index]
    
    def _reduce_probability(self, probability: Probability, effectiveness: float) -> Probability:
        """Reduce probability based on mitigation effectiveness."""
        if effectiveness < 0.3:
            return probability  # No reduction
        
        probability_order = [Probability.REMOTE, Probability.LOW, Probability.MEDIUM, Probability.HIGH]
        current_index = probability_order.index(probability)
        
        if effectiveness >= 0.7:
            # High effectiveness: reduce by 2 levels
            new_index = max(0, current_index - 2)
        elif effectiveness >= 0.5:
            # Medium effectiveness: reduce by 1 level
            new_index = max(0, current_index - 1)
        else:
            # Low effectiveness: no reduction
            new_index = current_index
        
        return probability_order[new_index]
    
    def _extract_risk_control_measures(self, mitigation: str) -> List[str]:
        """Extract individual risk control measures from mitigation text."""
        if not mitigation:
            return []
        
        # Split mitigation text into individual measures
        # Look for common separators and bullet points
        measures = []
        
        # Split by common separators
        for separator in [';', '\n', '•', '-', '*']:
            if separator in mitigation:
                parts = mitigation.split(separator)
                measures.extend([part.strip() for part in parts if part.strip()])
                break
        
        # If no separators found, treat as single measure
        if not measures:
            measures = [mitigation.strip()]
        
        # Clean up and filter measures
        cleaned_measures = []
        for measure in measures:
            # Remove common prefixes
            measure = measure.lstrip('- •*').strip()
            if measure and len(measure) > 10:  # Filter out very short measures
                cleaned_measures.append(measure)
        
        return cleaned_measures[:5]  # Limit to 5 measures for practicality
    
    def _generate_surveillance_plan(self, risk: RiskItem) -> str:
        """Generate post-market surveillance plan based on risk characteristics."""
        if risk.risk_level in [RiskLevel.UNACCEPTABLE, RiskLevel.UNDESIRABLE]:
            if risk.severity == Severity.CATASTROPHIC:
                return ("Continuous monitoring required with immediate reporting of incidents. "
                       "Monthly review of risk control effectiveness. "
                       "Annual comprehensive risk assessment update.")
            elif risk.severity == Severity.SERIOUS:
                return ("Quarterly monitoring of risk control measures. "
                       "Semi-annual review of incident reports. "
                       "Annual risk assessment update.")
            else:
                return ("Semi-annual monitoring of risk control effectiveness. "
                       "Annual review of related incidents and near-misses.")
        else:
            return ("Annual review of risk status and control measure effectiveness. "
                   "Monitor through routine post-market surveillance activities.")
    
    def _generate_risk_benefit_analysis(self, risk: RiskItem) -> str:
        """Generate risk-benefit analysis statement."""
        if risk.risk_level == RiskLevel.UNACCEPTABLE:
            return ("Risk is not acceptable without additional risk control measures. "
                   "Benefits do not justify the risk level. "
                   "Additional risk controls must be implemented before market release.")
        elif risk.risk_level == RiskLevel.UNDESIRABLE:
            return ("Risk is acceptable only with proper risk control measures in place. "
                   "Clinical benefits justify the residual risk when controls are effective. "
                   "Risk-benefit ratio is favorable with implemented mitigations.")
        elif risk.risk_level == RiskLevel.ACCEPTABLE:
            return ("Risk is acceptable with current control measures. "
                   "Clinical benefits clearly outweigh the minimal residual risk. "
                   "Risk-benefit analysis supports market approval.")
        else:  # NEGLIGIBLE
            return ("Risk is negligible and does not impact the overall risk-benefit profile. "
                   "Clinical benefits significantly outweigh the minimal risk. "
                   "No additional risk controls required.")
    
    def _calculate_risk_level(self, severity: Severity, probability: Probability) -> RiskLevel:
        """Calculate risk level from severity and probability (same as HazardIdentifier)."""
        if severity == Severity.NEGLIGIBLE:
            return RiskLevel.NEGLIGIBLE
        
        if severity == Severity.CATASTROPHIC:
            if probability in [Probability.HIGH, Probability.MEDIUM]:
                return RiskLevel.UNACCEPTABLE
            else:
                return RiskLevel.UNDESIRABLE
        
        if severity == Severity.SERIOUS:
            if probability == Probability.HIGH:
                return RiskLevel.UNACCEPTABLE
            elif probability == Probability.MEDIUM:
                return RiskLevel.UNDESIRABLE
            else:
                return RiskLevel.ACCEPTABLE
        
        if severity == Severity.MINOR:
            if probability in [Probability.HIGH, Probability.MEDIUM]:
                return RiskLevel.UNDESIRABLE
            else:
                return RiskLevel.ACCEPTABLE
        
        return RiskLevel.ACCEPTABLE
    
    def _determine_risk_acceptability(self, risk: RiskItem) -> Dict[str, Any]:
        """Determine risk acceptability per ISO 14971."""
        acceptability_criteria = {
            RiskLevel.UNACCEPTABLE: {
                'acceptable': False,
                'action_required': 'Immediate risk control measures required',
                'approval_needed': True,
                'documentation_level': 'Comprehensive'
            },
            RiskLevel.UNDESIRABLE: {
                'acceptable': True,  # With proper risk control
                'action_required': 'Risk control measures recommended',
                'approval_needed': True,
                'documentation_level': 'Detailed'
            },
            RiskLevel.ACCEPTABLE: {
                'acceptable': True,
                'action_required': 'Risk control measures may be considered',
                'approval_needed': False,
                'documentation_level': 'Standard'
            },
            RiskLevel.NEGLIGIBLE: {
                'acceptable': True,
                'action_required': 'No specific action required',
                'approval_needed': False,
                'documentation_level': 'Minimal'
            }
        }
        
        return acceptability_criteria[risk.risk_level]
    
    def _estimate_post_mitigation_severity(self, risk: RiskItem) -> str:
        """Estimate severity after mitigation implementation."""
        effectiveness = self._estimate_mitigation_effectiveness(risk.mitigation)
        reduced_severity = self._reduce_severity(risk.severity, effectiveness)
        return reduced_severity.value
    
    def _estimate_post_mitigation_probability(self, risk: RiskItem) -> str:
        """Estimate probability after mitigation implementation."""
        effectiveness = self._estimate_mitigation_effectiveness(risk.mitigation)
        reduced_probability = self._reduce_probability(risk.probability, effectiveness)
        return reduced_probability.value
    
    def _calculate_risk_statistics(self, risk_items: List[RiskItem]) -> Dict[str, Any]:
        """Calculate comprehensive risk statistics."""
        if not risk_items:
            return {
                'total_risks': 0,
                'severity_distribution': {},
                'probability_distribution': {},
                'risk_level_distribution': {},
                'priority_distribution': {},
                'average_risk_score': 0.0
            }
        
        # Count by severity
        severity_dist = {}
        for risk in risk_items:
            sev = risk.severity.value
            severity_dist[sev] = severity_dist.get(sev, 0) + 1
        
        # Count by probability
        probability_dist = {}
        for risk in risk_items:
            prob = risk.probability.value
            probability_dist[prob] = probability_dist.get(prob, 0) + 1
        
        # Count by risk level
        risk_level_dist = {}
        for risk in risk_items:
            level = risk.risk_level.value
            risk_level_dist[level] = risk_level_dist.get(level, 0) + 1
        
        # Count by priority
        priority_dist = {}
        for risk in risk_items:
            score_data = risk.metadata.get('risk_score', {})
            if isinstance(score_data, dict):
                priority = score_data.get('risk_priority', 4)
            else:
                priority = 4  # Default priority for non-dict risk_score
            priority_dist[f'Priority_{priority}'] = priority_dist.get(f'Priority_{priority}', 0) + 1
        
        # Calculate average risk score
        risk_scores = []
        for risk in risk_items:
            score_data = risk.metadata.get('risk_score', {})
            if isinstance(score_data, dict):
                risk_scores.append(score_data.get('raw_score', 0))
            else:
                # Handle case where risk_score is not a dict (legacy format)
                risk_scores.append(score_data if isinstance(score_data, (int, float)) else 0)
        
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
        
        return {
            'total_risks': len(risk_items),
            'severity_distribution': severity_dist,
            'probability_distribution': probability_dist,
            'risk_level_distribution': risk_level_dist,
            'priority_distribution': priority_dist,
            'average_risk_score': avg_risk_score,
            'max_risk_score': max(risk_scores) if risk_scores else 0,
            'min_risk_score': min(risk_scores) if risk_scores else 0
        }
    
    def filter_by_severity(self, risk_items: List[RiskItem], min_severity: Severity) -> List[RiskItem]:
        """
        Filter risks by minimum severity level.
        
        Args:
            risk_items: List of risk items to filter
            min_severity: Minimum severity level to include
            
        Returns:
            Filtered list of risk items
        """
        severity_order = {
            Severity.NEGLIGIBLE: 1,
            Severity.MINOR: 2,
            Severity.SERIOUS: 3,
            Severity.CATASTROPHIC: 4
        }
        
        min_order = severity_order[min_severity]
        return [r for r in risk_items if severity_order[r.severity] >= min_order]
    
    def filter_by_risk_level(self, risk_items: List[RiskItem], min_level: RiskLevel) -> List[RiskItem]:
        """
        Filter risks by minimum risk level.
        
        Args:
            risk_items: List of risk items to filter
            min_level: Minimum risk level to include
            
        Returns:
            Filtered list of risk items
        """
        level_order = {
            RiskLevel.NEGLIGIBLE: 1,
            RiskLevel.ACCEPTABLE: 2,
            RiskLevel.UNDESIRABLE: 3,
            RiskLevel.UNACCEPTABLE: 4
        }
        
        min_order = level_order[min_level]
        return [r for r in risk_items if level_order[r.risk_level] >= min_order]
    
    def sort_by_priority(self, risk_items: List[RiskItem]) -> List[RiskItem]:
        """
        Sort risks by priority (highest risk first).
        
        Args:
            risk_items: List of risk items to sort
            
        Returns:
            Sorted list of risk items
        """
        def get_sort_key(risk: RiskItem) -> Tuple[int, int]:
            score_data = risk.metadata.get('risk_score', {})
            priority = score_data.get('risk_priority', 4)
            raw_score = score_data.get('raw_score', 0)
            return (priority, -raw_score)  # Sort by priority, then by raw score descending
        
        return sorted(risk_items, key=get_sort_key)
    
    def export_to_csv(self, risk_items: List[RiskItem], output_path: str) -> bool:
        """
        Export risk register to CSV format.
        
        Args:
            risk_items: List of risk items to export
            output_path: Path to output CSV file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Risk_ID', 'Hazard', 'Cause', 'Effect', 'Severity', 'Probability',
                    'Risk_Level', 'Risk_Score', 'Priority', 'Mitigation', 'Verification',
                    'Related_Requirements', 'Risk_Control_Measures', 'Residual_Severity', 
                    'Residual_Probability', 'Residual_Risk_Level', 'Risk_Acceptability',
                    'Control_Effectiveness', 'Post_Market_Surveillance', 'Risk_Benefit_Analysis',
                    'Action_Required'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for risk in risk_items:
                    score_data = risk.metadata.get('risk_score', {})
                    acceptability_data = risk.metadata.get('risk_acceptability', {})
                    
                    row = {
                        'Risk_ID': risk.id,
                        'Hazard': risk.hazard,
                        'Cause': risk.cause,
                        'Effect': risk.effect,
                        'Severity': risk.severity.value,
                        'Probability': risk.probability.value,
                        'Risk_Level': risk.risk_level.value,
                        'Risk_Score': score_data.get('raw_score', 0),
                        'Priority': score_data.get('risk_priority', 4),
                        'Mitigation': risk.mitigation,
                        'Verification': risk.verification,
                        'Related_Requirements': '; '.join(risk.related_requirements),
                        'Risk_Control_Measures': '; '.join(risk.risk_control_measures) if risk.risk_control_measures else '',
                        'Residual_Severity': risk.residual_risk_severity.value if risk.residual_risk_severity else '',
                        'Residual_Probability': risk.residual_risk_probability.value if risk.residual_risk_probability else '',
                        'Residual_Risk_Level': risk.residual_risk_level.value if risk.residual_risk_level else '',
                        'Risk_Acceptability': risk.risk_acceptability or '',
                        'Control_Effectiveness': f"{risk.risk_control_effectiveness:.2f}" if risk.risk_control_effectiveness else '',
                        'Post_Market_Surveillance': risk.post_market_surveillance or '',
                        'Risk_Benefit_Analysis': risk.risk_benefit_analysis or '',
                        'Action_Required': acceptability_data.get('action_required', '')
                    }
                    
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error exporting risk register to CSV: {e}")
            return False
    
    def export_to_json(self, risk_items: List[RiskItem], output_path: str, include_metadata: bool = True) -> bool:
        """
        Export risk register to JSON format.
        
        Args:
            risk_items: List of risk items to export
            output_path: Path to output JSON file
            include_metadata: Whether to include detailed metadata
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'risk_register': {
                    'export_timestamp': datetime.now().isoformat(),
                    'total_risks': len(risk_items),
                    'iso_14971_compliant': True,
                    'risks': []
                }
            }
            
            for risk in risk_items:
                risk_data = {
                    'id': risk.id,
                    'hazard': risk.hazard,
                    'cause': risk.cause,
                    'effect': risk.effect,
                    'severity': risk.severity.value,
                    'probability': risk.probability.value,
                    'risk_level': risk.risk_level.value,
                    'mitigation': risk.mitigation,
                    'verification': risk.verification,
                    'related_requirements': risk.related_requirements,
                    'risk_control_measures': risk.risk_control_measures,
                    'residual_risk_severity': risk.residual_risk_severity.value if risk.residual_risk_severity else None,
                    'residual_risk_probability': risk.residual_risk_probability.value if risk.residual_risk_probability else None,
                    'residual_risk_level': risk.residual_risk_level.value if risk.residual_risk_level else None,
                    'risk_acceptability': risk.risk_acceptability,
                    'risk_control_effectiveness': risk.risk_control_effectiveness,
                    'post_market_surveillance': risk.post_market_surveillance,
                    'risk_benefit_analysis': risk.risk_benefit_analysis
                }
                
                if include_metadata:
                    risk_data['metadata'] = risk.metadata
                
                export_data['risk_register']['risks'].append(risk_data)
            
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting risk register to JSON: {e}")
            return False
    
    def generate_iso_14971_report(self, risk_items: List[RiskItem], output_path: str, 
                                 project_info: Dict[str, Any] = None) -> bool:
        """
        Generate a comprehensive ISO 14971 compliant risk management report.
        
        Args:
            risk_items: List of risk items to include in report
            output_path: Path to output report file
            project_info: Optional project information for the report
            
        Returns:
            True if report generation successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate report content
            report_content = self._generate_report_content(risk_items, project_info or {})
            
            with open(output_file, 'w', encoding='utf-8') as report_file:
                report_file.write(report_content)
            
            return True
            
        except Exception as e:
            print(f"Error generating ISO 14971 report: {e}")
            return False
    
    def _generate_report_content(self, risk_items: List[RiskItem], project_info: Dict[str, Any]) -> str:
        """Generate the content for ISO 14971 risk management report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self._calculate_risk_statistics(risk_items)
        
        # Sort risks by priority for report
        sorted_risks = self.sort_by_priority(risk_items)
        
        report = f"""# ISO 14971 Risk Management Report

## Project Information
- **Project Name**: {project_info.get('name', 'Medical Device Software Project')}
- **Report Generated**: {timestamp}
- **Total Risks Identified**: {stats['total_risks']}
- **ISO 14971 Compliance**: Yes

## Executive Summary

This risk management report has been prepared in accordance with ISO 14971:2019 
"Medical devices — Application of risk management to medical devices". The report 
documents the systematic risk analysis performed on the medical device software.

### Risk Summary
- **High Priority Risks (Unacceptable)**: {stats['risk_level_distribution'].get('Unacceptable', 0)}
- **Medium Priority Risks (Undesirable)**: {stats['risk_level_distribution'].get('Undesirable', 0)}
- **Low Priority Risks (Acceptable/Negligible)**: {stats['risk_level_distribution'].get('Acceptable', 0) + stats['risk_level_distribution'].get('Negligible', 0)}
- **Average Risk Score**: {stats['average_risk_score']:.2f}

### Severity Distribution
"""
        
        for severity, count in stats['severity_distribution'].items():
            report += f"- **{severity}**: {count} risks\n"
        
        report += f"""
### Probability Distribution
"""
        
        for probability, count in stats['probability_distribution'].items():
            report += f"- **{probability}**: {count} risks\n"
        
        report += f"""
## Detailed Risk Analysis

The following risks have been identified through systematic analysis of the software requirements:

"""
        
        for i, risk in enumerate(sorted_risks, 1):
            score_data = risk.metadata.get('risk_score', {})
            acceptability_data = risk.metadata.get('risk_acceptability', {})
            
            report += f"""### Risk {i}: {risk.id}

**Hazard**: {risk.hazard}

**Cause**: {risk.cause}

**Effect**: {risk.effect}

**Initial Risk Assessment**:
- Severity: {risk.severity.value}
- Probability: {risk.probability.value}
- Risk Level: {risk.risk_level.value}
- Risk Score: {score_data.get('raw_score', 0)}
- Priority: {score_data.get('risk_priority', 4)}

**Risk Control Measures**:
{risk.mitigation}

**Individual Control Measures**:
"""
            
            if risk.risk_control_measures:
                for j, measure in enumerate(risk.risk_control_measures, 1):
                    report += f"{j}. {measure}\n"
            else:
                report += "No specific control measures identified\n"
            
            report += f"""
**Verification of Risk Control**:
{risk.verification}

**Risk Control Effectiveness**: {f"{risk.risk_control_effectiveness:.2f}" if risk.risk_control_effectiveness is not None else 'Not assessed'}

**Residual Risk Assessment**:
- Residual Severity: {risk.residual_risk_severity.value if risk.residual_risk_severity else 'Not assessed'}
- Residual Probability: {risk.residual_risk_probability.value if risk.residual_risk_probability else 'Not assessed'}
- Residual Risk Level: {risk.residual_risk_level.value if risk.residual_risk_level else 'Not assessed'}

**Risk Acceptability**: {risk.risk_acceptability or 'Not determined'}

**Risk-Benefit Analysis**: 
{risk.risk_benefit_analysis or 'Not performed'}

**Post-Market Surveillance Plan**:
{risk.post_market_surveillance or 'Not specified'}

**Action Required**: {acceptability_data.get('action_required', 'None specified')}

**Related Requirements**: {', '.join(risk.related_requirements) if risk.related_requirements else 'None specified'}

---

"""
        
        report += f"""## Risk Management Conclusion

This risk analysis has identified {stats['total_risks']} potential risks associated with the medical device software. 
All risks have been assessed according to ISO 14971 principles and appropriate risk control measures have been proposed.

### Risk Acceptability Summary
- **Unacceptable Risks**: {stats['risk_level_distribution'].get('Unacceptable', 0)} (require immediate action)
- **Undesirable Risks**: {stats['risk_level_distribution'].get('Undesirable', 0)} (require risk control measures)
- **Acceptable Risks**: {stats['risk_level_distribution'].get('Acceptable', 0) + stats['risk_level_distribution'].get('Negligible', 0)} (may require monitoring)

### Recommendations
1. Implement all proposed risk control measures for unacceptable and undesirable risks
2. Verify effectiveness of risk control measures through testing and validation
3. Monitor residual risks throughout the product lifecycle
4. Review and update risk analysis when design changes occur

---

*This report was generated automatically using the Medical Software Analysis Tool in compliance with ISO 14971:2019 requirements.*
"""
        
        return report