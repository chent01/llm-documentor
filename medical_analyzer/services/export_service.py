"""
Comprehensive export service for creating regulatory submission bundles.
"""

import os
import json
import zipfile
import csv
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil

from ..models.core import SOUPComponent
from ..services.soup_service import SOUPService


class ExportService:
    """Service for creating comprehensive export bundles for regulatory submissions."""
    
    def __init__(self, soup_service: SOUPService):
        """
        Initialize export service.
        
        Args:
            soup_service: SOUP service for accessing SOUP inventory
        """
        self.soup_service = soup_service
        self.audit_log = []
    
    def log_action(self, action: str, details: str, user: str = "system", timestamp: Optional[datetime] = None):
        """
        Log an action for audit trail.
        
        Args:
            action: Action performed
            details: Details of the action
            user: User who performed the action
            timestamp: Timestamp of the action (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.audit_log.append({
            "timestamp": timestamp.isoformat(),
            "user": user,
            "action": action,
            "details": details
        })
    
    def create_comprehensive_export(self, 
                                  analysis_results: Dict[str, Any],
                                  project_name: str,
                                  project_path: str,
                                  output_dir: str = None) -> str:
        """
        Create a comprehensive export bundle containing all analysis artifacts.
        
        Args:
            analysis_results: Complete analysis results dictionary
            project_name: Name of the project
            project_path: Path to the project root
            output_dir: Directory to save the export (defaults to temp directory)
            
        Returns:
            Path to the created export bundle
            
        Raises:
            ValueError: If required data is missing
            OSError: If file operations fail
        """
        if not analysis_results:
            raise ValueError("Analysis results cannot be empty")
        
        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="medical_export_")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"{project_name}_export_{timestamp}"
        bundle_path = os.path.join(output_dir, bundle_name)
        
        try:
            # Create bundle directory
            os.makedirs(bundle_path, exist_ok=True)
            
            # Log export start
            self.log_action("export_started", f"Creating export bundle: {bundle_name}")
            
            # Export each component
            self._export_requirements(analysis_results, bundle_path)
            self._export_risk_register(analysis_results, bundle_path)
            self._export_traceability_matrix(analysis_results, bundle_path)
            self._export_test_results(analysis_results, bundle_path)
            self._export_soup_inventory(bundle_path)
            self._export_project_metadata(analysis_results, project_name, project_path, bundle_path)
            self._export_summary_report(analysis_results, bundle_path, project_name)
            
            # Log export completion
            self.log_action("export_completed", f"Export bundle created: {bundle_name}")
            
            # Export audit log after all logging is complete
            self._export_audit_log(bundle_path)
            
            # Create zip bundle
            zip_path = self._create_zip_bundle(bundle_path, bundle_name)
            
            return zip_path
            
        except Exception as e:
            # Log export failure
            self.log_action("export_failed", f"Export failed: {str(e)}")
            raise
    
    def _export_requirements(self, analysis_results: Dict[str, Any], bundle_path: str):
        """Export requirements to CSV and JSON formats."""
        requirements_dir = os.path.join(bundle_path, "requirements")
        os.makedirs(requirements_dir, exist_ok=True)
        
        # Export user requirements
        user_reqs = analysis_results.get('requirements', {}).get('user_requirements', [])
        if user_reqs:
            self._export_requirements_csv(user_reqs, os.path.join(requirements_dir, "user_requirements.csv"))
            self._export_requirements_json(user_reqs, os.path.join(requirements_dir, "user_requirements.json"))
        
        # Export software requirements
        software_reqs = analysis_results.get('requirements', {}).get('software_requirements', [])
        if software_reqs:
            self._export_requirements_csv(software_reqs, os.path.join(requirements_dir, "software_requirements.csv"))
            self._export_requirements_json(software_reqs, os.path.join(requirements_dir, "software_requirements.json"))
        
        self.log_action("requirements_exported", f"Exported {len(user_reqs)} URs and {len(software_reqs)} SRs")
    
    def _export_requirements_csv(self, requirements: List[Dict], file_path: str):
        """Export requirements to CSV format."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Description', 'Acceptance Criteria', 'Derived From', 'Code References'])
            
            for req in requirements:
                acceptance_criteria = '; '.join(req.get('acceptance_criteria', []))
                derived_from = '; '.join(req.get('derived_from', []))
                code_refs = '; '.join([f"{ref.get('file', '')}:{ref.get('line', '')}" 
                                     for ref in req.get('code_references', [])])
                
                writer.writerow([
                    req.get('id', ''),
                    req.get('description', ''),
                    acceptance_criteria,
                    derived_from,
                    code_refs
                ])
    
    def _export_requirements_json(self, requirements: List[Dict], file_path: str):
        """Export requirements to JSON format."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(requirements, f, indent=2, ensure_ascii=False)
    
    def _export_risk_register(self, analysis_results: Dict[str, Any], bundle_path: str):
        """Export risk register to CSV and JSON formats."""
        risks_dir = os.path.join(bundle_path, "risk_register")
        os.makedirs(risks_dir, exist_ok=True)
        
        risks = analysis_results.get('risks', [])
        if risks:
            # Export to CSV
            csv_path = os.path.join(risks_dir, "risk_register.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Hazard', 'Cause', 'Effect', 'Severity', 
                    'Probability', 'Risk Level', 'Mitigation', 'Verification', 'Related Requirements'
                ])
                
                for risk in risks:
                    related_reqs = '; '.join(risk.get('related_requirements', []))
                    writer.writerow([
                        risk.get('id', ''),
                        risk.get('hazard', ''),
                        risk.get('cause', ''),
                        risk.get('effect', ''),
                        risk.get('severity', ''),
                        risk.get('probability', ''),
                        risk.get('risk_level', ''),
                        risk.get('mitigation', ''),
                        risk.get('verification', ''),
                        related_reqs
                    ])
            
            # Export to JSON
            json_path = os.path.join(risks_dir, "risk_register.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(risks, f, indent=2, ensure_ascii=False)
            
            self.log_action("risk_register_exported", f"Exported {len(risks)} risk items")
    
    def _export_traceability_matrix(self, analysis_results: Dict[str, Any], bundle_path: str):
        """Export traceability matrix to CSV format."""
        traceability_dir = os.path.join(bundle_path, "traceability")
        os.makedirs(traceability_dir, exist_ok=True)
        
        traceability = analysis_results.get('traceability', {})
        if traceability:
            # Export matrix
            matrix_path = os.path.join(traceability_dir, "traceability_matrix.csv")
            with open(matrix_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                headers = ['Source Type', 'Source ID', 'Target Type', 'Target ID', 'Link Type', 'Evidence']
                writer.writerow(headers)
                
                # Write links
                links = traceability.get('links', [])
                for link in links:
                    writer.writerow([
                        link.get('source_type', ''),
                        link.get('source_id', ''),
                        link.get('target_type', ''),
                        link.get('target_id', ''),
                        link.get('link_type', ''),
                        link.get('evidence', '')
                    ])
            
            # Export gaps report if available
            gaps = traceability.get('gaps', [])
            if gaps:
                gaps_path = os.path.join(traceability_dir, "traceability_gaps.csv")
                with open(gaps_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Gap Type', 'Description', 'Severity', 'Recommendation'])
                    
                    for gap in gaps:
                        writer.writerow([
                            gap.get('type', ''),
                            gap.get('description', ''),
                            gap.get('severity', ''),
                            gap.get('recommendation', '')
                        ])
            
            self.log_action("traceability_exported", f"Exported traceability matrix with {len(links)} links")
    
    def _export_test_results(self, analysis_results: Dict[str, Any], bundle_path: str):
        """Export test results and generated test files."""
        tests_dir = os.path.join(bundle_path, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        
        tests = analysis_results.get('tests', {})
        if tests:
            # Export test summary
            summary_path = os.path.join(tests_dir, "test_summary.txt")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("TEST EXECUTION SUMMARY\n")
                f.write("=" * 30 + "\n\n")
                f.write(f"Total Tests: {tests.get('total_tests', 0)}\n")
                f.write(f"Passed: {tests.get('passed_tests', 0)}\n")
                f.write(f"Failed: {tests.get('failed_tests', 0)}\n")
                f.write(f"Skipped: {tests.get('skipped_tests', 0)}\n")
                f.write(f"Coverage: {tests.get('coverage', 0)}%\n")
                f.write(f"Execution Time: {tests.get('execution_time', 0):.1f}s\n\n")
                
                # Test suites
                suites = tests.get('test_suites', [])
                for suite in suites:
                    f.write(f"Suite: {suite.get('name', 'Unknown')}\n")
                    f.write(f"  Status: {suite.get('status', 'Unknown')}\n")
                    f.write(f"  Tests: {suite.get('total_tests', 0)}\n")
                    f.write(f"  Passed: {suite.get('passed_tests', 0)}\n")
                    f.write(f"  Failed: {suite.get('failed_tests', 0)}\n\n")
            
            # Export test files if available
            test_files = tests.get('generated_files', {})
            if test_files:
                test_files_dir = os.path.join(tests_dir, "generated_tests")
                os.makedirs(test_files_dir, exist_ok=True)
                
                for file_path, content in test_files.items():
                    full_path = os.path.join(test_files_dir, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            self.log_action("test_results_exported", f"Exported test results with {len(suites)} test suites")
    
    def _export_soup_inventory(self, bundle_path: str):
        """Export SOUP inventory to CSV and JSON formats."""
        soup_dir = os.path.join(bundle_path, "soup_inventory")
        os.makedirs(soup_dir, exist_ok=True)
        
        try:
            # Get SOUP inventory
            soup_data = self.soup_service.export_inventory()
            components = soup_data.get('soup_inventory', {}).get('components', [])
            
            if components:
                # Export to CSV
                csv_path = os.path.join(soup_dir, "soup_inventory.csv")
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'ID', 'Name', 'Version', 'Usage Reason', 'Safety Justification',
                        'Supplier', 'License', 'Website', 'Description', 'Installation Date',
                        'Last Updated', 'Criticality Level', 'Verification Method', 'Known Anomalies'
                    ])
                    
                    for comp in components:
                        anomalies = '; '.join(comp.get('anomaly_list', []))
                        writer.writerow([
                            comp.get('id', ''),
                            comp.get('name', ''),
                            comp.get('version', ''),
                            comp.get('usage_reason', ''),
                            comp.get('safety_justification', ''),
                            comp.get('supplier', ''),
                            comp.get('license', ''),
                            comp.get('website', ''),
                            comp.get('description', ''),
                            comp.get('installation_date', ''),
                            comp.get('last_updated', ''),
                            comp.get('criticality_level', ''),
                            comp.get('verification_method', ''),
                            anomalies
                        ])
                
                # Export to JSON
                json_path = os.path.join(soup_dir, "soup_inventory.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(soup_data, f, indent=2, ensure_ascii=False)
                
                self.log_action("soup_inventory_exported", f"Exported {len(components)} SOUP components")
            else:
                # Create empty inventory file
                empty_path = os.path.join(soup_dir, "soup_inventory_empty.txt")
                with open(empty_path, 'w', encoding='utf-8') as f:
                    f.write("No SOUP components have been added to the inventory.\n")
                    f.write("This file indicates that the SOUP inventory was checked but found empty.\n")
                
                self.log_action("soup_inventory_exported", "Exported empty SOUP inventory")
                
        except Exception as e:
            # Log error but continue
            self.log_action("soup_export_error", f"Failed to export SOUP inventory: {str(e)}")
    
    def _export_audit_log(self, bundle_path: str):
        """Export audit log to JSON format."""
        audit_dir = os.path.join(bundle_path, "audit")
        os.makedirs(audit_dir, exist_ok=True)
        
        audit_path = os.path.join(audit_dir, "audit_log.json")
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_log, f, indent=2, ensure_ascii=False)
        
        # Also export as human-readable text
        text_path = os.path.join(audit_dir, "audit_log.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write("AUDIT LOG\n")
            f.write("=" * 20 + "\n\n")
            
            for entry in self.audit_log:
                f.write(f"Timestamp: {entry['timestamp']}\n")
                f.write(f"User: {entry['user']}\n")
                f.write(f"Action: {entry['action']}\n")
                f.write(f"Details: {entry['details']}\n")
                f.write("-" * 40 + "\n\n")
    
    def _export_project_metadata(self, analysis_results: Dict[str, Any], project_name: str, 
                                project_path: str, bundle_path: str):
        """Export project metadata and analysis configuration."""
        metadata_dir = os.path.join(bundle_path, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Create project metadata
        metadata = {
            "project_name": project_name,
            "project_path": project_path,
            "export_timestamp": datetime.now().isoformat(),
            "analysis_timestamp": analysis_results.get('timestamp', ''),
            "analysis_version": "1.0.0",
            "summary": analysis_results.get('summary', {}),
            "file_count": analysis_results.get('file_count', 0),
            "lines_of_code": analysis_results.get('lines_of_code', 0)
        }
        
        metadata_path = os.path.join(metadata_dir, "project_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _export_summary_report(self, analysis_results: Dict[str, Any], bundle_path: str, project_name: str = "Unknown Project"):
        """Export a comprehensive summary report."""
        summary_path = os.path.join(bundle_path, "summary_report.txt")
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("MEDICAL SOFTWARE ANALYSIS - COMPREHENSIVE REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            # Project summary
            summary = analysis_results.get('summary', {})
            f.write("PROJECT SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Project Name: {project_name}\n")
            f.write(f"Software Class: {summary.get('software_class', 'Unknown')}\n")
            f.write(f"Confidence Level: {summary.get('confidence', 0)}%\n")
            f.write(f"Total Files Analyzed: {analysis_results.get('file_count', 0)}\n")
            f.write(f"Lines of Code: {analysis_results.get('lines_of_code', 0)}\n\n")
            
            # Requirements summary
            requirements = analysis_results.get('requirements', {})
            user_reqs = requirements.get('user_requirements', [])
            software_reqs = requirements.get('software_requirements', [])
            f.write("REQUIREMENTS SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"User Requirements: {len(user_reqs)}\n")
            f.write(f"Software Requirements: {len(software_reqs)}\n\n")
            
            # Risk summary
            risks = analysis_results.get('risks', [])
            high_risks = [r for r in risks if r.get('severity') == 'CATASTROPHIC']
            medium_risks = [r for r in risks if r.get('severity') == 'SERIOUS']
            low_risks = [r for r in risks if r.get('severity') == 'MINOR']
            
            f.write("RISK SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Risks: {len(risks)}\n")
            f.write(f"High Severity: {len(high_risks)}\n")
            f.write(f"Medium Severity: {len(medium_risks)}\n")
            f.write(f"Low Severity: {len(low_risks)}\n\n")
            
            # Test summary
            tests = analysis_results.get('tests', {})
            f.write("TEST SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Tests: {tests.get('total_tests', 0)}\n")
            f.write(f"Passed: {tests.get('passed_tests', 0)}\n")
            f.write(f"Failed: {tests.get('failed_tests', 0)}\n")
            f.write(f"Coverage: {tests.get('coverage', 0)}%\n\n")
            
            # SOUP summary
            try:
                soup_data = self.soup_service.export_inventory()
                soup_components = soup_data.get('soup_inventory', {}).get('components', [])
                f.write("SOUP INVENTORY SUMMARY\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total SOUP Components: {len(soup_components)}\n")
                
                criticality_counts = {}
                for comp in soup_components:
                    level = comp.get('criticality_level', 'Unknown')
                    criticality_counts[level] = criticality_counts.get(level, 0) + 1
                
                for level, count in criticality_counts.items():
                    f.write(f"{level} Criticality: {count}\n")
                f.write("\n")
                
            except Exception:
                f.write("SOUP INVENTORY SUMMARY\n")
                f.write("-" * 20 + "\n")
                f.write("SOUP inventory not available\n\n")
            
            # Export timestamp
            f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def _create_zip_bundle(self, bundle_path: str, bundle_name: str) -> str:
        """Create a zip file containing the entire export bundle."""
        zip_path = f"{bundle_path}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(bundle_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, bundle_path)
                    zipf.write(file_path, arc_name)
        
        # Remove the uncompressed bundle directory
        shutil.rmtree(bundle_path)
        
        return zip_path
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get a summary of the export contents."""
        return {
            "audit_log_entries": len(self.audit_log),
            "last_export_timestamp": self.audit_log[-1]['timestamp'] if self.audit_log else None,
            "export_actions": [entry['action'] for entry in self.audit_log]
        }
