#!/usr/bin/env python3
"""
Migration script to update LLM parameter usage to unified configuration system.

This script helps identify and update scattered LLM parameters across the codebase
to use the centralized operation configuration system.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class LLMParameterMigrator:
    """Migrates scattered LLM parameters to unified configuration."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.patterns = {
            # Pattern for temperature=X.X, max_tokens=XXXX
            'inline_params': re.compile(
                r'temperature=([0-9.]+),\s*max_tokens=(\d+)'
            ),
            # Pattern for generate calls with hardcoded params
            'generate_call': re.compile(
                r'\.generate\(\s*prompt=.*?temperature=([0-9.]+).*?max_tokens=(\d+).*?\)',
                re.DOTALL
            ),
            # Pattern for system_prompt parameter
            'system_prompt': re.compile(
                r'system_prompt="([^"]*)"'
            )
        }
        
        # Operation mapping based on context clues
        self.operation_mapping = {
            'user_requirements': 'user_requirements_generation',
            'software_requirements': 'software_requirements_generation',
            'soup': 'soup_classification',
            'risk': 'soup_risk_assessment',
            'test': 'test_case_generation',
            'hazard': 'hazard_identification',
            'feature': 'feature_extraction',
            'diagnostic': 'diagnostic_test'
        }
    
    def scan_files(self) -> List[Tuple[Path, List[Dict]]]:
        """
        Scan Python files for LLM parameter patterns.
        
        Returns:
            List of (file_path, issues) tuples
        """
        issues = []
        
        # Scan medical_analyzer directory
        for py_file in self.project_root.glob('medical_analyzer/**/*.py'):
            if py_file.name.startswith('__'):
                continue
                
            file_issues = self._scan_file(py_file)
            if file_issues:
                issues.append((py_file, file_issues))
        
        return issues
    
    def _scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for LLM parameter issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        issues = []
        
        # Check for inline parameters
        for match in self.patterns['inline_params'].finditer(content):
            temp, tokens = match.groups()
            line_num = content[:match.start()].count('\n') + 1
            
            issues.append({
                'type': 'inline_params',
                'line': line_num,
                'temperature': float(temp),
                'max_tokens': int(tokens),
                'match': match.group(0),
                'suggested_operation': self._guess_operation(content, match.start())
            })
        
        # Check for generate calls
        for match in self.patterns['generate_call'].finditer(content):
            temp = match.group(1)
            tokens = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            issues.append({
                'type': 'generate_call',
                'line': line_num,
                'temperature': float(temp),
                'max_tokens': int(tokens),
                'match': match.group(0)[:100] + '...',
                'suggested_operation': self._guess_operation(content, match.start())
            })
        
        return issues
    
    def _guess_operation(self, content: str, position: int) -> str:
        """Guess the operation type based on context."""
        # Look at surrounding context (500 chars before and after)
        start = max(0, position - 500)
        end = min(len(content), position + 500)
        context = content[start:end].lower()
        
        for keyword, operation in self.operation_mapping.items():
            if keyword in context:
                return operation
        
        return 'default'
    
    def generate_report(self) -> None:
        """Generate a migration report."""
        issues = self.scan_files()
        
        if not issues:
            print("✅ No LLM parameter issues found!")
            return
        
        print("🔍 LLM Parameter Migration Report")
        print("=" * 50)
        
        total_issues = sum(len(file_issues) for _, file_issues in issues)
        print(f"Found {total_issues} issues in {len(issues)} files\n")
        
        for file_path, file_issues in issues:
            rel_path = file_path.relative_to(self.project_root)
            print(f"📁 {rel_path}")
            print("-" * len(str(rel_path)))
            
            for issue in file_issues:
                print(f"  Line {issue['line']}: {issue['type']}")
                print(f"    Temperature: {issue['temperature']}")
                print(f"    Max tokens: {issue['max_tokens']}")
                print(f"    Suggested operation: {issue['suggested_operation']}")
                print(f"    Context: {issue['match'][:80]}...")
                print()
        
        print("\n🔧 Recommended Actions:")
        print("1. Add import: from ..llm.operation_configs import get_operation_params")
        print("2. Replace hardcoded parameters with: **get_operation_params('operation_name')")
        print("3. Update operation names based on suggestions above")
        print("4. Test the changes to ensure functionality is preserved")
    
    def suggest_fixes(self) -> None:
        """Suggest specific fixes for each file."""
        issues = self.scan_files()
        
        print("\n🛠️  Suggested Fixes:")
        print("=" * 50)
        
        for file_path, file_issues in issues:
            rel_path = file_path.relative_to(self.project_root)
            print(f"\n📁 {rel_path}")
            
            # Check if imports are needed
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                needs_import = 'get_operation_params' not in content
                
                if needs_import:
                    print("  ➕ Add import:")
                    print("     from ..llm.operation_configs import get_operation_params")
                
                for issue in file_issues:
                    operation = issue['suggested_operation']
                    print(f"  🔄 Line {issue['line']}:")
                    print(f"     Replace: temperature={issue['temperature']}, max_tokens={issue['max_tokens']}")
                    print(f"     With: **get_operation_params('{operation}')")
                
            except Exception as e:
                print(f"  ❌ Error reading file: {e}")


def main():
    """Main migration script."""
    project_root = Path(__file__).parent.parent
    migrator = LLMParameterMigrator(project_root)
    
    print("🚀 LLM Parameter Migration Tool")
    print("This tool helps migrate to the unified LLM configuration system\n")
    
    migrator.generate_report()
    migrator.suggest_fixes()
    
    print("\n📋 Summary:")
    print("The unified system provides:")
    print("- Centralized parameter management")
    print("- Operation-specific configurations")
    print("- Easy maintenance and tuning")
    print("- Consistent behavior across modules")
    print("\nConfiguration file: medical_analyzer/config/llm_operation_configs.json")


if __name__ == "__main__":
    main()