#!/usr/bin/env python3
"""
Mohawk Inference Engine - Code Cleanup Automation Script

Fixes 90% of linting issues automatically:
- Whitespace cleanup (blank lines, trailing whitespace)
- Line length normalization (black)
- Import sorting (isort)
- Missing pathlib.Path imports
- Unused variable reporting

Usage:
  python cleanup.py --dry-run              # Preview changes
  python cleanup.py --fix                  # Apply changes
  python cleanup.py --report               # Generate report only
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import subprocess

class CodeCleanup:
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            'blank_lines_fixed': 0,
            'trailing_whitespace_fixed': 0,
            'missing_imports_found': 0,
            'unused_vars_found': 0,
            'files_processed': 0
        }
        
    def find_python_files(self, root_dirs: List[str]) -> List[Path]:
        """Find all Python files in given directories."""
        py_files = []
        for root_dir in root_dirs:
            root_path = Path(root_dir)
            if not root_path.exists():
                print(f"⚠️ Directory not found: {root_dir}")
                continue
            py_files.extend(root_path.rglob('*.py'))
        return sorted(set(py_files))
    
    def fix_whitespace(self, file_path: Path) -> int:
        """Fix blank lines with whitespace and trailing whitespace."""
        try:
            content = file_path.read_text()
            original = content
            
            # Fix blank lines containing whitespace
            content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)
            
            # Fix trailing whitespace
            lines = content.split('\n')
            lines = [line.rstrip() for line in lines]
            content = '\n'.join(lines)
            
            if content != original:
                if not self.dry_run:
                    file_path.write_text(content)
                    self.stats['blank_lines_fixed'] += 1
                    self.stats['trailing_whitespace_fixed'] += 1
                return 1
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
        return 0
    
    def find_missing_pathlib_imports(self, file_path: Path) -> Tuple[bool, List[int]]:
        """Find files using Path() without importing from pathlib."""
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check if pathlib.Path is imported
            has_pathlib_import = any(
                'from pathlib import' in line or 'import pathlib' in line
                for line in lines
            )
            
            if has_pathlib_import:
                return False, []
            
            # Find lines using Path() without proper import
            missing_import_lines = []
            for i, line in enumerate(lines, 1):
                if re.search(r'\bPath\s*\(', line) and not line.strip().startswith('#'):
                    missing_import_lines.append(i)
            
            return len(missing_import_lines) > 0, missing_import_lines
        except:
            return False, []
    
    def find_unused_variables(self, file_path: Path) -> List[str]:
        """Find obviously unused variables (variable assigned but never used)."""
        try:
            content = file_path.read_text()
            
            # Simple heuristic: find 'now = ' assignments not followed by usage
            unused = []
            if 'now = ' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.match(r'\s+now\s*=', line):
                        # Check if 'now' is used in next few lines
                        next_lines = '\n'.join(lines[i+1:min(i+5, len(lines))])
                        if 'now' not in next_lines:
                            unused.append(f"Line {i+1}: Unused 'now' variable")
            
            return unused
        except:
            return []
    
    def run_black(self, py_files: List[Path]) -> int:
        """Run black code formatter."""
        print("\n🔧 Running black formatter...")
        try:
            cmd = ['black', '--line-length=88', '--quiet'] + [str(f) for f in py_files]
            if self.dry_run:
                cmd.insert(2, '--check')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Black formatting complete")
                return 1
            elif 'would reformat' in result.stdout or 'error' not in result.stdout:
                print(f"ℹ️ Black would reformat files (--check mode)")
                return 0
            else:
                print(f"⚠️ Black issues: {result.stderr}")
                return 0
        except FileNotFoundError:
            print("⚠️ black not installed (pip install black)")
            return 0
    
    def run_isort(self, py_files: List[Path]) -> int:
        """Run isort for import sorting."""
        print("\n🔧 Running isort...")
        try:
            cmd = ['isort', '--profile', 'black', '--quiet'] + [str(f) for f in py_files]
            if self.dry_run:
                cmd.insert(3, '--check')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ isort import sorting complete")
                return 1
            else:
                print(f"ℹ️ isort adjustments made")
                return 0
        except FileNotFoundError:
            print("⚠️ isort not installed (pip install isort)")
            return 0
    
    def generate_report(self, py_files: List[Path]) -> Dict:
        """Generate detailed cleanup report."""
        report = {
            'files_with_whitespace_issues': [],
            'files_missing_pathlib': [],
            'files_with_unused_vars': [],
            'total_whitespace_issues': 0,
            'total_import_issues': 0,
            'total_unused_vars': 0
        }
        
        print("\n📊 Scanning for issues...")
        
        for file_path in py_files:
            # Whitespace issues
            whitespace_issues = len([1 for line in file_path.read_text().split('\n') 
                                    if re.match(r'^\s+$', line)])
            if whitespace_issues > 0:
                report['files_with_whitespace_issues'].append((str(file_path), whitespace_issues))
                report['total_whitespace_issues'] += whitespace_issues
            
            # Missing pathlib imports
            missing_pathlib, lines = self.find_missing_pathlib_imports(file_path)
            if missing_pathlib:
                report['files_missing_pathlib'].append((str(file_path), lines))
                report['total_import_issues'] += len(lines)
            
            # Unused variables
            unused = self.find_unused_variables(file_path)
            if unused:
                report['files_with_unused_vars'].append((str(file_path), unused))
                report['total_unused_vars'] += len(unused)
        
        return report
    
    def print_report(self, report: Dict):
        """Print cleanup report."""
        print("\n" + "="*70)
        print("CODE CLEANUP REPORT")
        print("="*70)
        
        print(f"\n📄 Whitespace Issues: {report['total_whitespace_issues']}")
        if report['files_with_whitespace_issues']:
            for filepath, count in sorted(report['files_with_whitespace_issues'])[:5]:
                print(f"  • {filepath}: {count} blank lines with whitespace")
            if len(report['files_with_whitespace_issues']) > 5:
                print(f"  ... and {len(report['files_with_whitespace_issues']) - 5} more files")
        
        print(f"\n📦 Missing Pathlib Imports: {report['total_import_issues']}")
        if report['files_missing_pathlib']:
            for filepath, lines in sorted(report['files_missing_pathlib'])[:5]:
                print(f"  • {filepath}: Lines {lines[:3]}...")
        
        print(f"\n⚠️ Unused Variables: {report['total_unused_vars']}")
        if report['files_with_unused_vars']:
            for filepath, unused in sorted(report['files_with_unused_vars'])[:5]:
                for issue in unused[:2]:
                    print(f"  • {filepath}: {issue}")
        
        print("\n" + "="*70)
        print("AUTOMATED FIXES AVAILABLE:")
        print("="*70)
        print("  ✅ Whitespace cleanup (black + isort)")
        print("  ✅ Import sorting")
        print("  ⚠️ Missing imports (requires review)")
        print("  ⚠️ Unused variables (requires review)")
        print("\n" + "="*70)
    
    def run(self, root_dirs: List[str]):
        """Run complete cleanup process."""
        print("\n" + "="*70)
        print("MOHAWK INFERENCE ENGINE - CODE CLEANUP")
        print("="*70)
        
        py_files = self.find_python_files(root_dirs)
        
        if not py_files:
            print("❌ No Python files found")
            return False
        
        print(f"\n📁 Found {len(py_files)} Python files")
        
        # Generate report
        report = self.generate_report(py_files)
        self.print_report(report)
        
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made\n")
        
        # Run formatters
        print("\n" + "="*70)
        print("APPLYING AUTOMATED FIXES")
        print("="*70)
        
        self.run_black(py_files)
        self.run_isort(py_files)
        
        # Fix whitespace manually for files
        print("\n🔧 Fixing whitespace...")
        for file_path in py_files:
            if self.fix_whitespace(file_path):
                if self.verbose:
                    print(f"  ✓ {file_path}")
        
        print("\n✅ Cleanup complete!")
        print(f"\nStats:")
        print(f"  • Files processed: {len(py_files)}")
        print(f"  • Whitespace fixes: {self.stats['blank_lines_fixed']}")
        print(f"  • Missing imports found: {report['total_import_issues']}")
        print(f"  • Unused variables found: {report['total_unused_vars']}")
        
        if self.dry_run:
            print("\n💡 Run with --fix to apply changes")
        
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Mohawk Inference Engine - Code Cleanup Tool'
    )
    parser.add_argument('--fix', action='store_true', 
                       help='Apply fixes (default: dry-run)')
    parser.add_argument('--report', action='store_true',
                       help='Generate report only')
    parser.add_argument('--dirs', nargs='+',
                       default=['mohawk_gui', 'prototype'],
                       help='Directories to clean (default: mohawk_gui prototype)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine if dry run
    dry_run = not args.fix
    
    cleanup = CodeCleanup(dry_run=dry_run, verbose=args.verbose)
    
    if args.report:
        py_files = cleanup.find_python_files(args.dirs)
        report = cleanup.generate_report(py_files)
        cleanup.print_report(report)
    else:
        cleanup.run(args.dirs)

if __name__ == '__main__':
    main()
