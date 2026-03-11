import ast
import glob
import os
import sys
import re

class DocCoverage:
    def check_python_coverage(self, codebase_path):
        """Check documentation coverage for Python codebase"""
        results = {
            'total_functions': 0,
            'documented_functions': 0,
            'total_classes': 0,
            'documented_classes': 0,
            'missing_docs': []
        }

        pattern = os.path.join(codebase_path, 'backend', '**', '*.py')
        for file_path in glob.glob(pattern, recursive=True):
            if 'venv' in file_path or 'tests' in file_path:
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    module = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(module):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('__'):
                        continue
                    results['total_functions'] += 1
                    if ast.get_docstring(node):
                        results['documented_functions'] += 1
                    else:
                        results['missing_docs'].append({
                            'type': 'Function',
                            'name': node.name,
                            'file': os.path.relpath(file_path, codebase_path)
                        })

                elif isinstance(node, ast.ClassDef):
                    results['total_classes'] += 1
                    if ast.get_docstring(node):
                        results['documented_classes'] += 1
                    else:
                        results['missing_docs'].append({
                            'type': 'Class',
                            'name': node.name,
                            'file': os.path.relpath(file_path, codebase_path)
                        })

        return results

    def check_js_coverage(self, codebase_path):
        """Check documentation coverage for JS/JSX codebase using simple heuristics"""
        results = {
            'total_functions': 0,
            'documented_functions': 0,
            'missing_docs': []
        }
        
        # Regex to find JS/React function components or regular functions
        func_pattern = re.compile(r'(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(|const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>')
        jsdoc_pattern = re.compile(r'/\*\*[\s\S]*?\*/\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+[a-zA-Z0-9_]+\s*\(|/\*\*[\s\S]*?\*/\s*(?:export\s+(?:default\s+)?)?const\s+[a-zA-Z0-9_]+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>')

        pattern = os.path.join(codebase_path, 'frontend', '**', '*.js')
        for file_path in glob.glob(pattern, recursive=True):
            if 'node_modules' in file_path or '.next' in file_path:
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Quick heuristic: find all functions
            lines = content.split('\n')
            for i, line in enumerate(lines):
                match = func_pattern.search(line)
                if match:
                    func_name = match.group(1) or match.group(2)
                    results['total_functions'] += 1
                    
                    # Check if there's a JSDoc right above it
                    # This is a naive check. A better approach parses AST.
                    has_jsdoc = False
                    for j in range(i-1, i-5, -1):
                        if j >= 0 and '*/' in lines[j]:
                            has_jsdoc = True
                            break
                            
                    if has_jsdoc:
                        results['documented_functions'] += 1
                    else:
                        results['missing_docs'].append({
                            'type': 'JS Function',
                            'name': func_name,
                            'file': os.path.relpath(file_path, codebase_path)
                        })
                        
        return results

    def print_report(self, py_results, js_results):
        print("="*50)
        print("Documentation Coverage Report")
        print("="*50)
        
        py_funcs = py_results['total_functions']
        py_func_doc = py_results['documented_functions']
        py_classes = py_results['total_classes']
        py_class_doc = py_results['documented_classes']
        
        if py_funcs > 0:
            print(f"Python Functions: {py_func_doc}/{py_funcs} ({(py_func_doc/py_funcs)*100:.1f}%)")
        if py_classes > 0:
            print(f"Python Classes: {py_class_doc}/{py_classes} ({(py_class_doc/py_classes)*100:.1f}%)")
            
        js_funcs = js_results['total_functions']
        js_func_doc = js_results['documented_functions']
        if js_funcs > 0:
            print(f"JavaScript Functions: {js_func_doc}/{js_funcs} ({(js_func_doc/js_funcs)*100:.1f}%)")
            
        total_items = py_funcs + py_classes + js_funcs
        total_doc = py_func_doc + py_class_doc + js_func_doc
        
        if total_items > 0:
            total_pct = (total_doc/total_items)*100
            print("-" * 50)
            print(f"Total Coverage: {total_pct:.1f}%")
            if total_pct < 80.0:
                print("⚠️  Warning: Total documentation coverage is below 80%.")
                
        print("\nMissing Documentation Examples (up to 10):")
        all_missing = py_results['missing_docs'] + js_results['missing_docs']
        for item in all_missing[:10]:
            print(f" - [{item['type']}] {item['name']} in {item['file']}")
        
        if len(all_missing) > 10:
            print(f"   ...and {len(all_missing) - 10} more.")

def main():
    if len(sys.argv) > 1:
        codebase_path = sys.argv[1]
    else:
        codebase_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
    checker = DocCoverage()
    py_results = checker.check_python_coverage(codebase_path)
    js_results = checker.check_js_coverage(codebase_path)
    
    checker.print_report(py_results, js_results)
    
if __name__ == '__main__':
    main()
