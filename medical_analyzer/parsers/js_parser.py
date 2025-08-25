"""
JavaScript code parser using tree-sitter for AST analysis.
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Global flag for tree-sitter availability
TREE_SITTER_AVAILABLE = False

try:
    import tree_sitter
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    # Mock classes for when tree-sitter is not available
    class Language:
        pass
    class Parser:
        pass

from ..models.core import CodeChunk, FileMetadata, CodeReference
from ..models.enums import ChunkType


@dataclass
class FunctionSignature:
    """Represents a JavaScript function signature."""
    name: str
    parameters: List[str]  # Parameter names
    start_line: int
    end_line: int
    is_async: bool = False
    is_arrow: bool = False
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class ClassDefinition:
    """Represents a JavaScript class definition."""
    name: str
    methods: List[FunctionSignature]
    properties: List[str]
    extends: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


@dataclass
class JSCodeStructure:
    """Structure representing parsed JavaScript code."""
    file_path: str
    functions: List[FunctionSignature]
    classes: List[ClassDefinition]
    imports: List[Dict[str, str]]  # [{'type': 'import', 'source': 'module', 'items': ['item1']}, ...]
    exports: List[Dict[str, str]]  # [{'type': 'export', 'name': 'function'}, ...]
    variables: List[Dict[str, str]]  # [{'type': 'const', 'name': 'var'}, ...]
    requires: List[str]  # CommonJS requires


class JSParser:
    """Parser for JavaScript source code using tree-sitter."""
    
    def __init__(self):
        """Initialize the JavaScript parser with tree-sitter."""
        self.parser = None
        self.language = None
        self._setup_parser()
    
    def _setup_parser(self):
        """Set up tree-sitter parser for JavaScript."""
        if not TREE_SITTER_AVAILABLE:
            # Use fallback regex-based parsing when tree-sitter is not available
            self.parser = None
            self.language = None
            return
            
        try:
            # Try to use pre-built language if available
            import tree_sitter_javascript
            language_capsule = tree_sitter_javascript.language()
            self.language = Language(language_capsule)
            self.parser = Parser(self.language)
        except ImportError:
            try:
                # Try to load the JavaScript language using build_library
                JS_LANGUAGE = Language(tree_sitter.Language.build_library(
                    # Store the library in the build directory
                    'build/my-languages.so',
                    # Include one or more languages
                    ['tree-sitter-javascript']
                ))
                
                self.parser = Parser(JS_LANGUAGE)
                self.language = JS_LANGUAGE
                
            except Exception as e:
                # Fall back to regex-based parsing
                print(f"Warning: Tree-sitter JavaScript not available, using fallback parser: {e}")
                self.parser = None
                self.language = None
    
    def parse_file(self, file_path: str) -> JSCodeStructure:
        """Parse a JavaScript file and extract its structure."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        
        return self.parse_source(source_code, file_path)
    
    def parse_source(self, source_code: str, file_path: str = "") -> JSCodeStructure:
        """Parse JavaScript source code and extract structure."""
        if self.parser:
            # Use tree-sitter parsing
            return self._parse_with_tree_sitter(source_code, file_path)
        else:
            # Use fallback regex-based parsing
            return self._parse_with_regex(source_code, file_path)
    
    def _parse_with_tree_sitter(self, source_code: str, file_path: str) -> JSCodeStructure:
        """Parse using tree-sitter (preferred method)."""
        # Parse the source code
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node
        
        # Extract different code elements
        functions = self._extract_functions(root_node, source_code)
        classes = self._extract_classes(root_node, source_code)
        imports = self._extract_imports(root_node, source_code)
        exports = self._extract_exports(root_node, source_code)
        variables = self._extract_variables(root_node, source_code)
        requires = self._extract_requires(root_node, source_code)
        
        return JSCodeStructure(
            file_path=file_path,
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            variables=variables,
            requires=requires
        )
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> JSCodeStructure:
        """Fallback regex-based parsing when tree-sitter is not available."""
        lines = source_code.split('\n')
        
        # Extract different code elements using regex
        functions = self._extract_functions_regex(source_code, lines)
        classes = self._extract_classes_regex(source_code, lines)
        imports = self._extract_imports_regex(lines)
        exports = self._extract_exports_regex(lines)
        variables = self._extract_variables_regex(lines)
        requires = self._extract_requires_regex(lines)
        
        return JSCodeStructure(
            file_path=file_path,
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            variables=variables,
            requires=requires
        )
    
    def _extract_functions(self, root_node, source_code: str) -> List[FunctionSignature]:
        """Extract function signatures from the AST."""
        functions = []
        
        def traverse_for_functions(node, class_name=None):
            if node.type == 'function_declaration':
                func_sig = self._parse_function_declaration(node, source_code, class_name)
                if func_sig:
                    functions.append(func_sig)
            elif node.type == 'arrow_function':
                func_sig = self._parse_arrow_function(node, source_code, class_name)
                if func_sig:
                    functions.append(func_sig)
            elif node.type == 'method_definition':
                func_sig = self._parse_method_definition(node, source_code, class_name)
                if func_sig:
                    functions.append(func_sig)
            elif node.type == 'class_declaration':
                # Extract class name and traverse methods
                class_name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name_node = child
                        break
                
                if class_name_node:
                    current_class = source_code[class_name_node.start_byte:class_name_node.end_byte]
                    for child in node.children:
                        traverse_for_functions(child, current_class)
            else:
                for child in node.children:
                    traverse_for_functions(child, class_name)
        
        traverse_for_functions(root_node)
        return functions
    
    def _parse_function_declaration(self, node, source_code: str, class_name: Optional[str] = None) -> Optional[FunctionSignature]:
        """Parse a function declaration node."""
        try:
            # Extract function name
            func_name = ""
            parameters = []
            is_async = False
            
            for child in node.children:
                if child.type == 'identifier':
                    func_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'formal_parameters':
                    parameters = self._extract_parameters(child, source_code)
            
            # Check for async modifier
            func_text = source_code[node.start_byte:node.end_byte]
            is_async = func_text.strip().startswith('async')
            
            return FunctionSignature(
                name=func_name,
                parameters=parameters,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                is_async=is_async,
                is_arrow=False,
                is_method=class_name is not None,
                class_name=class_name
            )
            
        except Exception as e:
            print(f"Error parsing function: {e}")
            return None
    
    def _parse_arrow_function(self, node, source_code: str, class_name: Optional[str] = None) -> Optional[FunctionSignature]:
        """Parse an arrow function node."""
        try:
            parameters = []
            
            # Arrow functions can have different parameter structures
            for child in node.children:
                if child.type == 'formal_parameters':
                    parameters = self._extract_parameters(child, source_code)
                elif child.type == 'identifier':
                    # Single parameter without parentheses
                    param_name = source_code[child.start_byte:child.end_byte]
                    parameters = [param_name]
            
            # Arrow functions don't have explicit names, use context or "anonymous"
            func_name = "anonymous_arrow"
            
            return FunctionSignature(
                name=func_name,
                parameters=parameters,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                is_async=False,  # TODO: detect async arrow functions
                is_arrow=True,
                is_method=class_name is not None,
                class_name=class_name
            )
            
        except Exception as e:
            print(f"Error parsing arrow function: {e}")
            return None
    
    def _parse_method_definition(self, node, source_code: str, class_name: Optional[str] = None) -> Optional[FunctionSignature]:
        """Parse a method definition node."""
        try:
            method_name = ""
            parameters = []
            is_async = False
            
            for child in node.children:
                if child.type == 'property_identifier':
                    method_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'formal_parameters':
                    parameters = self._extract_parameters(child, source_code)
            
            # Check for async modifier
            method_text = source_code[node.start_byte:node.end_byte]
            is_async = 'async' in method_text
            
            return FunctionSignature(
                name=method_name,
                parameters=parameters,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                is_async=is_async,
                is_arrow=False,
                is_method=True,
                class_name=class_name
            )
            
        except Exception as e:
            print(f"Error parsing method: {e}")
            return None
    
    def _extract_parameters(self, parameter_node, source_code: str) -> List[str]:
        """Extract function parameters."""
        parameters = []
        
        for child in parameter_node.children:
            if child.type == 'identifier':
                param_name = source_code[child.start_byte:child.end_byte]
                parameters.append(param_name)
            elif child.type == 'rest_parameter':
                # Handle rest parameters (...args)
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        param_name = "..." + source_code[grandchild.start_byte:grandchild.end_byte]
                        parameters.append(param_name)
        
        return parameters
    
    def _extract_classes(self, root_node, source_code: str) -> List[ClassDefinition]:
        """Extract class definitions from the AST."""
        classes = []
        
        def traverse_for_classes(node):
            if node.type == 'class_declaration':
                class_def = self._parse_class_declaration(node, source_code)
                if class_def:
                    classes.append(class_def)
            
            for child in node.children:
                traverse_for_classes(child)
        
        traverse_for_classes(root_node)
        return classes
    
    def _parse_class_declaration(self, node, source_code: str) -> Optional[ClassDefinition]:
        """Parse a class declaration node."""
        try:
            class_name = ""
            extends = None
            methods = []
            properties = []
            
            for child in node.children:
                if child.type == 'identifier':
                    class_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'class_heritage':
                    # Extract extends clause
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            extends = source_code[grandchild.start_byte:grandchild.end_byte]
                elif child.type == 'class_body':
                    # Extract methods and properties
                    for method_node in child.children:
                        if method_node.type == 'method_definition':
                            method_sig = self._parse_method_definition(method_node, source_code, class_name)
                            if method_sig:
                                methods.append(method_sig)
                        elif method_node.type == 'field_definition':
                            # Extract property names
                            for prop_child in method_node.children:
                                if prop_child.type == 'property_identifier':
                                    prop_name = source_code[prop_child.start_byte:prop_child.end_byte]
                                    properties.append(prop_name)
            
            return ClassDefinition(
                name=class_name,
                methods=methods,
                properties=properties,
                extends=extends,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1
            )
            
        except Exception as e:
            print(f"Error parsing class: {e}")
            return None
    
    def _extract_imports(self, root_node, source_code: str) -> List[Dict[str, str]]:
        """Extract import statements from the AST."""
        imports = []
        
        def traverse_for_imports(node):
            if node.type == 'import_statement':
                import_info = self._parse_import_statement(node, source_code)
                if import_info:
                    imports.append(import_info)
            
            for child in node.children:
                traverse_for_imports(child)
        
        traverse_for_imports(root_node)
        return imports
    
    def _parse_import_statement(self, node, source_code: str) -> Optional[Dict[str, str]]:
        """Parse an import statement node."""
        try:
            import_text = source_code[node.start_byte:node.end_byte]
            
            # Simple parsing of import statement
            return {
                'type': 'import',
                'statement': import_text.strip(),
                'line': node.start_point[0] + 1
            }
            
        except Exception:
            return None
    
    def _extract_exports(self, root_node, source_code: str) -> List[Dict[str, str]]:
        """Extract export statements from the AST."""
        exports = []
        
        def traverse_for_exports(node):
            if node.type == 'export_statement':
                export_info = self._parse_export_statement(node, source_code)
                if export_info:
                    exports.append(export_info)
            
            for child in node.children:
                traverse_for_exports(child)
        
        traverse_for_exports(root_node)
        return exports
    
    def _parse_export_statement(self, node, source_code: str) -> Optional[Dict[str, str]]:
        """Parse an export statement node."""
        try:
            export_text = source_code[node.start_byte:node.end_byte]
            
            return {
                'type': 'export',
                'statement': export_text.strip(),
                'line': node.start_point[0] + 1
            }
            
        except Exception:
            return None
    
    def _extract_variables(self, root_node, source_code: str) -> List[Dict[str, str]]:
        """Extract variable declarations from the AST."""
        variables = []
        
        def traverse_for_variables(node):
            if node.type in ['variable_declaration', 'lexical_declaration']:
                var_info = self._parse_variable_declaration(node, source_code)
                if var_info:
                    variables.extend(var_info)
            
            for child in node.children:
                traverse_for_variables(child)
        
        traverse_for_variables(root_node)
        return variables
    
    def _parse_variable_declaration(self, node, source_code: str) -> List[Dict[str, str]]:
        """Parse a variable declaration node."""
        variables = []
        
        try:
            var_type = ""  # const, let, var
            
            for child in node.children:
                if child.type in ['const', 'let', 'var']:
                    var_type = child.type
                elif child.type == 'variable_declarator':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            var_name = source_code[grandchild.start_byte:grandchild.end_byte]
                            variables.append({
                                'type': var_type,
                                'name': var_name,
                                'line': node.start_point[0] + 1
                            })
            
        except Exception:
            pass
        
        return variables
    
    def _extract_requires(self, root_node, source_code: str) -> List[str]:
        """Extract CommonJS require statements from the AST."""
        requires = []
        
        def traverse_for_requires(node):
            if node.type == 'call_expression':
                # Check if this is a require() call
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = source_code[child.start_byte:child.end_byte]
                        if func_name == 'require':
                            # Extract the required module
                            for arg_child in node.children:
                                if arg_child.type == 'arguments':
                                    for arg in arg_child.children:
                                        if arg.type == 'string':
                                            module_name = source_code[arg.start_byte:arg.end_byte]
                                            requires.append(module_name.strip('"\''))
            
            for child in node.children:
                traverse_for_requires(child)
        
        traverse_for_requires(root_node)
        return requires    
   
 # Regex-based fallback parsing methods
    def _extract_functions_regex(self, source_code: str, lines: List[str]) -> List[FunctionSignature]:
        """Extract functions using regex patterns."""
        functions = []
        
        # Pattern for function declarations
        func_pattern = re.compile(
            r'^\s*(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)',
            re.MULTILINE
        )
        
        # Pattern for arrow functions assigned to variables
        arrow_pattern = re.compile(
            r'^\s*(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
            re.MULTILINE
        )
        
        # Pattern for method definitions in classes
        method_pattern = re.compile(
            r'^\s*(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        
        # Extract function declarations
        for match in func_pattern.finditer(source_code):
            func_name = match.group(1)
            params_str = match.group(2)
            
            start_pos = match.start()
            start_line = source_code[:start_pos].count('\n') + 1
            end_line = self._find_function_end_regex(source_code, match.end(), start_line)
            
            parameters = self._parse_js_parameters_regex(params_str)
            is_async = 'async' in match.group(0)
            
            functions.append(FunctionSignature(
                name=func_name,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                is_async=is_async,
                is_arrow=False,
                is_method=False
            ))
        
        # Extract arrow functions
        for match in arrow_pattern.finditer(source_code):
            func_name = match.group(1)
            params_str = match.group(2)
            
            start_pos = match.start()
            start_line = source_code[:start_pos].count('\n') + 1
            end_line = self._find_arrow_function_end_regex(source_code, match.end(), start_line)
            
            parameters = self._parse_js_parameters_regex(params_str)
            is_async = 'async' in match.group(0)
            
            functions.append(FunctionSignature(
                name=func_name,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                is_async=is_async,
                is_arrow=True,
                is_method=False
            ))
        
        return functions
    
    def _find_function_end_regex(self, source_code: str, start_pos: int, start_line: int) -> int:
        """Find the end line of a function by counting braces."""
        brace_count = 0
        pos = start_pos
        line_num = start_line
        found_opening = False
        
        while pos < len(source_code):
            char = source_code[pos]
            if char == '{':
                brace_count += 1
                found_opening = True
            elif char == '}':
                brace_count -= 1
                if found_opening and brace_count == 0:
                    break
            elif char == '\n':
                line_num += 1
            pos += 1
        
        return line_num
    
    def _find_arrow_function_end_regex(self, source_code: str, start_pos: int, start_line: int) -> int:
        """Find the end line of an arrow function."""
        pos = start_pos
        line_num = start_line
        
        # Skip whitespace to find the arrow function body
        while pos < len(source_code) and source_code[pos].isspace():
            if source_code[pos] == '\n':
                line_num += 1
            pos += 1
        
        if pos < len(source_code) and source_code[pos] == '{':
            # Block body - count braces
            return self._find_function_end_regex(source_code, pos, line_num)
        else:
            # Expression body - find end of statement
            while pos < len(source_code) and source_code[pos] not in ';\n':
                pos += 1
            if pos < len(source_code) and source_code[pos] == '\n':
                line_num += 1
            return line_num
    
    def _parse_js_parameters_regex(self, params_str: str) -> List[str]:
        """Parse JavaScript function parameters from string."""
        parameters = []
        
        if not params_str.strip():
            return parameters
        
        # Split by comma, handling destructuring and default values
        param_parts = []
        paren_count = 0
        bracket_count = 0
        brace_count = 0
        current_param = ""
        
        for char in params_str:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
            elif char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                param_parts.append(current_param.strip())
                current_param = ""
                continue
            current_param += char
        
        if current_param.strip():
            param_parts.append(current_param.strip())
        
        # Extract parameter names
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
            
            # Handle rest parameters
            if param.startswith('...'):
                param_name = param[3:].split('=')[0].strip()
                parameters.append(f"...{param_name}")
            # Handle destructuring (simplified)
            elif param.startswith('{') or param.startswith('['):
                parameters.append(param.split('=')[0].strip())
            else:
                # Regular parameter, possibly with default value
                param_name = param.split('=')[0].strip()
                parameters.append(param_name)
        
        return parameters
    
    def _extract_classes_regex(self, source_code: str, lines: List[str]) -> List[ClassDefinition]:
        """Extract class definitions using regex."""
        classes = []
        
        # Pattern for class declarations
        class_pattern = re.compile(
            r'^\s*class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?\s*\{',
            re.MULTILINE
        )
        
        for match in class_pattern.finditer(source_code):
            class_name = match.group(1)
            extends = match.group(2)
            
            start_pos = match.start()
            start_line = source_code[:start_pos].count('\n') + 1
            end_line = self._find_class_end_regex(source_code, match.end(), start_line)
            
            # Extract class body to find methods
            class_body = self._extract_class_body_regex(source_code, match.end(), end_line)
            methods = self._extract_class_methods_regex(class_body, class_name)
            
            classes.append(ClassDefinition(
                name=class_name,
                methods=methods,
                properties=[],  # Simplified - not extracting properties in regex mode
                extends=extends,
                start_line=start_line,
                end_line=end_line
            ))
        
        return classes
    
    def _find_class_end_regex(self, source_code: str, start_pos: int, start_line: int) -> int:
        """Find the end line of a class by counting braces."""
        return self._find_function_end_regex(source_code, start_pos - 1, start_line)
    
    def _extract_class_body_regex(self, source_code: str, start_pos: int, end_line: int) -> str:
        """Extract the body of a class."""
        lines = source_code.split('\n')
        start_line = source_code[:start_pos].count('\n')
        
        if start_line < len(lines) and end_line <= len(lines):
            return '\n'.join(lines[start_line:end_line])
        return ""
    
    def _extract_class_methods_regex(self, class_body: str, class_name: str) -> List[FunctionSignature]:
        """Extract methods from class body."""
        methods = []
        
        # Pattern for method definitions
        method_pattern = re.compile(
            r'^\s*(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        
        for match in method_pattern.finditer(class_body):
            method_name = match.group(1)
            params_str = match.group(2)
            
            # Skip constructor and other special cases
            if method_name in ['constructor', 'get', 'set']:
                continue
            
            start_pos = match.start()
            start_line = class_body[:start_pos].count('\n') + 1
            end_line = self._find_function_end_regex(class_body, match.end(), start_line)
            
            parameters = self._parse_js_parameters_regex(params_str)
            is_async = 'async' in match.group(0)
            
            methods.append(FunctionSignature(
                name=method_name,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                is_async=is_async,
                is_arrow=False,
                is_method=True,
                class_name=class_name
            ))
        
        return methods
    
    def _extract_imports_regex(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extract import statements using regex."""
        imports = []
        
        import_pattern = re.compile(r'^\s*import\s+.*from\s+[\'"][^\'"]+[\'"]')
        import_all_pattern = re.compile(r'^\s*import\s+[\'"][^\'"]+[\'"]')
        
        for i, line in enumerate(lines):
            if import_pattern.match(line) or import_all_pattern.match(line):
                imports.append({
                    'type': 'import',
                    'statement': line.strip(),
                    'line': i + 1
                })
        
        return imports
    
    def _extract_exports_regex(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extract export statements using regex."""
        exports = []
        
        export_pattern = re.compile(r'^\s*export\s+')
        
        for i, line in enumerate(lines):
            if export_pattern.match(line):
                exports.append({
                    'type': 'export',
                    'statement': line.strip(),
                    'line': i + 1
                })
        
        return exports
    
    def _extract_variables_regex(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extract variable declarations using regex."""
        variables = []
        
        var_pattern = re.compile(r'^\s*(const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)')
        
        for i, line in enumerate(lines):
            match = var_pattern.match(line)
            if match:
                var_type = match.group(1)
                var_name = match.group(2)
                variables.append({
                    'type': var_type,
                    'name': var_name,
                    'line': i + 1
                })
        
        return variables
    
    def _extract_requires_regex(self, lines: List[str]) -> List[str]:
        """Extract CommonJS require statements using regex."""
        requires = []
        
        require_pattern = re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
        
        for line in lines:
            matches = require_pattern.findall(line)
            requires.extend(matches)
        
        return requires
    
    def extract_code_chunks(self, code_structure: JSCodeStructure, 
                          max_chunk_size: int = 1000) -> List[CodeChunk]:
        """Extract code chunks for LLM processing."""
        chunks = []
        
        if not os.path.exists(code_structure.file_path):
            return chunks
        
        with open(code_structure.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Create chunks for each function
        for func in code_structure.functions:
            start_idx = max(0, func.start_line - 1)
            end_idx = min(len(lines), func.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            # If function is too large, split it
            if len(content) > max_chunk_size:
                sub_chunks = self._split_large_function_js(content, func, max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    content=content,
                    function_name=func.name,
                    chunk_type=ChunkType.FUNCTION,
                    metadata={
                        'parameters': func.parameters,
                        'is_async': func.is_async,
                        'is_arrow': func.is_arrow,
                        'is_method': func.is_method,
                        'class_name': func.class_name
                    }
                )
                chunks.append(chunk)
        
        # Create chunks for each class
        for cls in code_structure.classes:
            start_idx = max(0, cls.start_line - 1)
            end_idx = min(len(lines), cls.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            chunk = CodeChunk(
                file_path=code_structure.file_path,
                start_line=cls.start_line,
                end_line=cls.end_line,
                content=content,
                chunk_type=ChunkType.CLASS,
                metadata={
                    'class_name': cls.name,
                    'extends': cls.extends,
                    'methods': [m.name for m in cls.methods],
                    'properties': cls.properties
                }
            )
            chunks.append(chunk)
        
        # Create chunk for module-level code (imports, exports, global variables)
        if code_structure.imports or code_structure.exports or code_structure.variables:
            global_content = self._extract_global_content_js(lines, code_structure)
            if global_content:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=1,
                    end_line=len(lines),
                    content=global_content,
                    chunk_type=ChunkType.MODULE,
                    metadata={
                        'imports': code_structure.imports,
                        'exports': code_structure.exports,
                        'variables': code_structure.variables,
                        'requires': code_structure.requires
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_large_function_js(self, content: str, func: FunctionSignature, 
                               max_size: int, file_path: str = "") -> List[CodeChunk]:
        """Split a large JavaScript function into smaller chunks."""
        chunks = []
        lines = content.split('\n')
        current_chunk_lines = []
        current_size = 0
        chunk_start_line = func.start_line
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > max_size and current_chunk_lines:
                # Create chunk from accumulated lines
                chunk_content = '\n'.join(current_chunk_lines)
                chunk = CodeChunk(
                    file_path=file_path,
                    start_line=chunk_start_line,
                    end_line=chunk_start_line + len(current_chunk_lines) - 1,
                    content=chunk_content,
                    function_name=func.name,
                    chunk_type=ChunkType.FUNCTION,
                    metadata={'is_partial': True, 'part_of': func.name}
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk_lines = [line]
                current_size = line_size
                chunk_start_line = func.start_line + i
            else:
                current_chunk_lines.append(line)
                current_size += line_size
        
        # Add remaining lines as final chunk
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunk = CodeChunk(
                file_path=file_path,
                start_line=chunk_start_line,
                end_line=chunk_start_line + len(current_chunk_lines) - 1,
                content=chunk_content,
                function_name=func.name,
                chunk_type=ChunkType.FUNCTION,
                metadata={'is_partial': True, 'part_of': func.name}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_global_content_js(self, lines: List[str], 
                                 code_structure: JSCodeStructure) -> str:
        """Extract global content (imports, exports, global vars)."""
        global_lines = []
        
        # Add imports
        for imp in code_structure.imports:
            global_lines.append(imp['statement'])
        
        # Add exports
        for exp in code_structure.exports:
            global_lines.append(exp['statement'])
        
        # Add requires
        for req in code_structure.requires:
            global_lines.append(f"require('{req}')")
        
        # Add global variables (simplified)
        for var in code_structure.variables:
            global_lines.append(f"{var['type']} {var['name']}")
        
        return '\n'.join(global_lines) if global_lines else ""
    
    def extract_code_chunks(self, js_structure: JSCodeStructure, 
                          max_chunk_size: int = 1000) -> List[CodeChunk]:
        """Extract code chunks for LLM processing with actual file content."""
        chunks = []
        
        if not os.path.exists(js_structure.file_path):
            # Return simplified chunks if file doesn't exist
            return self._create_simplified_chunks(js_structure)
        
        with open(js_structure.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Create chunks for functions with actual content
        for func in js_structure.functions:
            start_idx = max(0, func.start_line - 1)
            end_idx = min(len(lines), func.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            # If function is too large, split it
            if len(content) > max_chunk_size:
                sub_chunks = self._split_large_function_js(content, func, max_chunk_size, js_structure.file_path)
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    file_path=js_structure.file_path,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    content=content,
                    function_name=func.name,
                    chunk_type=ChunkType.FUNCTION,
                    metadata={
                        'is_async': func.is_async,
                        'is_arrow': func.is_arrow,
                        'is_method': func.is_method,
                        'class_name': func.class_name,
                        'parameters': func.parameters
                    }
                )
                chunks.append(chunk)
        
        # Create chunks for classes with actual content
        for cls in js_structure.classes:
            start_idx = max(0, cls.start_line - 1)
            end_idx = min(len(lines), cls.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            chunk = CodeChunk(
                file_path=js_structure.file_path,
                start_line=cls.start_line,
                end_line=cls.end_line,
                content=content,
                function_name=None,
                chunk_type=ChunkType.CLASS,
                metadata={
                    'class_name': cls.name,
                    'extends': cls.extends,
                    'methods': [m.name for m in cls.methods],
                    'properties': cls.properties
                }
            )
            chunks.append(chunk)
        
        # Create chunk for module-level code (imports, exports, global variables)
        if js_structure.imports or js_structure.exports or js_structure.variables:
            global_content = self._extract_global_content_js(lines, js_structure)
            if global_content.strip():
                chunk = CodeChunk(
                    file_path=js_structure.file_path,
                    start_line=1,
                    end_line=len(lines),
                    content=global_content,
                    function_name=None,
                    chunk_type=ChunkType.MODULE,
                    metadata={
                        'imports': js_structure.imports,
                        'exports': js_structure.exports,
                        'variables': js_structure.variables,
                        'requires': js_structure.requires
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _create_simplified_chunks(self, js_structure: JSCodeStructure) -> List[CodeChunk]:
        """Create simplified chunks when file content is not available."""
        chunks = []
        
        # Create chunks for functions
        for func in js_structure.functions:
            chunk = CodeChunk(
                file_path=js_structure.file_path,
                start_line=func.start_line,
                end_line=func.end_line,
                content=f"Function: {func.name}({', '.join(func.parameters)})",
                function_name=func.name,
                chunk_type=ChunkType.FUNCTION,
                metadata={
                    'is_async': func.is_async,
                    'is_arrow': func.is_arrow,
                    'is_method': func.is_method,
                    'class_name': func.class_name,
                    'parameters': func.parameters
                }
            )
            chunks.append(chunk)
        
        # Create chunks for classes
        for cls in js_structure.classes:
            chunk = CodeChunk(
                file_path=js_structure.file_path,
                start_line=cls.start_line,
                end_line=cls.end_line,
                content=f"Class: {cls.name}",
                function_name=None,
                chunk_type=ChunkType.CLASS,
                metadata={
                    'class_name': cls.name,
                    'extends': cls.extends,
                    'methods': [m.name for m in cls.methods],
                    'properties': cls.properties
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """Extract metadata from a JavaScript file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = os.stat(file_path)
        
        # Parse the file to get structure info
        try:
            js_structure = self.parse_file(file_path)
            
            return FileMetadata(
                file_path=file_path,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                file_type="javascript",
                line_count=len(js_structure.file_path.split('\n')) if hasattr(js_structure, 'source_lines') else 0,
                function_count=len(js_structure.functions)
            )
        except Exception as e:
            # Return basic metadata if parsing fails
            return FileMetadata(
                file_path=file_path,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                file_type="javascript",
                line_count=0,
                function_count=0
            )