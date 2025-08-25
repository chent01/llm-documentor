"""
C code parser using tree-sitter for AST analysis.
"""

import os
import re
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
    """Represents a C function signature."""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]  # [{'type': 'int', 'name': 'param1'}, ...]
    start_line: int
    end_line: int
    is_static: bool = False
    is_inline: bool = False


@dataclass
class CCodeStructure:
    """Structure representing parsed C code."""
    file_path: str
    functions: List[FunctionSignature]
    includes: List[str]
    defines: List[Dict[str, str]]  # [{'name': 'MACRO', 'value': '42'}, ...]
    global_variables: List[Dict[str, str]]  # [{'type': 'int', 'name': 'var'}, ...]
    structs: List[Dict[str, Any]]
    enums: List[Dict[str, Any]]


class CParser:
    """Parser for C source code using tree-sitter."""
    
    def __init__(self):
        """Initialize the C parser with tree-sitter."""
        self.parser = None
        self.language = None
        self._setup_parser()
    
    def _setup_parser(self):
        """Set up tree-sitter parser for C."""
        if not TREE_SITTER_AVAILABLE:
            # Use fallback regex-based parsing when tree-sitter is not available
            self.parser = None
            self.language = None
            return
            
        try:
            # Try to use pre-built language if available
            import tree_sitter_c
            language_capsule = tree_sitter_c.language()
            self.language = Language(language_capsule)
            self.parser = Parser(self.language)
        except ImportError:
            try:
                # Try to load the C language using build_library
                C_LANGUAGE = Language(tree_sitter.Language.build_library(
                    # Store the library in the build directory
                    'build/my-languages.so',
                    # Include one or more languages
                    ['tree-sitter-c']
                ))
                
                self.parser = Parser(C_LANGUAGE)
                self.language = C_LANGUAGE
                
            except Exception as e:
                # Fall back to regex-based parsing
                print(f"Warning: Tree-sitter not available, using fallback parser: {e}")
                self.parser = None
                self.language = None
    
    def parse_file(self, file_path: str) -> CCodeStructure:
        """Parse a C file and extract its structure."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        
        return self.parse_source(source_code, file_path)
    
    def parse_source(self, source_code: str, file_path: str = "") -> CCodeStructure:
        """Parse C source code and extract structure."""
        if self.parser:
            # Use tree-sitter parsing
            return self._parse_with_tree_sitter(source_code, file_path)
        else:
            # Use fallback regex-based parsing
            return self._parse_with_regex(source_code, file_path)
    
    def _parse_with_tree_sitter(self, source_code: str, file_path: str) -> CCodeStructure:
        """Parse using tree-sitter (preferred method)."""
        # Parse the source code
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node
        
        # Extract different code elements
        functions = self._extract_functions(root_node, source_code)
        includes = self._extract_includes(root_node, source_code)
        defines = self._extract_defines(root_node, source_code)
        global_variables = self._extract_global_variables(root_node, source_code)
        structs = self._extract_structs(root_node, source_code)
        enums = self._extract_enums(root_node, source_code)
        
        return CCodeStructure(
            file_path=file_path,
            functions=functions,
            includes=includes,
            defines=defines,
            global_variables=global_variables,
            structs=structs,
            enums=enums
        )
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> CCodeStructure:
        """Fallback regex-based parsing when tree-sitter is not available."""
        lines = source_code.split('\n')
        
        # Extract different code elements using regex
        functions = self._extract_functions_regex(source_code, lines)
        includes = self._extract_includes_regex(lines)
        defines = self._extract_defines_regex(lines)
        global_variables = self._extract_global_variables_regex(lines)
        structs = self._extract_structs_regex(source_code, lines)
        enums = self._extract_enums_regex(source_code, lines)
        
        return CCodeStructure(
            file_path=file_path,
            functions=functions,
            includes=includes,
            defines=defines,
            global_variables=global_variables,
            structs=structs,
            enums=enums
        )
    
    def _extract_functions(self, root_node, source_code: str) -> List[FunctionSignature]:
        """Extract function signatures from the AST."""
        functions = []
        
        def traverse_for_functions(node):
            if node.type == 'function_definition':
                func_sig = self._parse_function_definition(node, source_code)
                if func_sig:
                    functions.append(func_sig)
            
            for child in node.children:
                traverse_for_functions(child)
        
        traverse_for_functions(root_node)
        return functions
    
    def _parse_function_definition(self, node, source_code: str) -> Optional[FunctionSignature]:
        """Parse a function definition node."""
        try:
            # Get function declarator
            declarator = None
            for child in node.children:
                if child.type == 'function_declarator':
                    declarator = child
                    break
            
            if not declarator:
                return None
            
            # Extract function name
            identifier = None
            for child in declarator.children:
                if child.type == 'identifier':
                    identifier = child
                    break
            
            if not identifier:
                return None
            
            func_name = source_code[identifier.start_byte:identifier.end_byte]
            
            # Extract return type (everything before the declarator)
            return_type = "void"  # default
            for child in node.children:
                if child == declarator:
                    break
                if child.type in ['primitive_type', 'type_identifier', 'struct_specifier']:
                    return_type = source_code[child.start_byte:child.end_byte]
            
            # Extract parameters
            parameters = []
            parameter_list = None
            for child in declarator.children:
                if child.type == 'parameter_list':
                    parameter_list = child
                    break
            
            if parameter_list:
                parameters = self._extract_parameters(parameter_list, source_code)
            
            # Check for static/inline modifiers
            is_static = 'static' in source_code[node.start_byte:declarator.start_byte]
            is_inline = 'inline' in source_code[node.start_byte:declarator.start_byte]
            
            return FunctionSignature(
                name=func_name,
                return_type=return_type.strip(),
                parameters=parameters,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                is_static=is_static,
                is_inline=is_inline
            )
            
        except Exception as e:
            # Log error but continue parsing
            print(f"Error parsing function: {e}")
            return None
    
    def _extract_parameters(self, parameter_list, source_code: str) -> List[Dict[str, str]]:
        """Extract function parameters."""
        parameters = []
        
        for child in parameter_list.children:
            if child.type == 'parameter_declaration':
                param = self._parse_parameter(child, source_code)
                if param:
                    parameters.append(param)
        
        return parameters
    
    def _parse_parameter(self, param_node, source_code: str) -> Optional[Dict[str, str]]:
        """Parse a parameter declaration."""
        try:
            param_type = ""
            param_name = ""
            
            for child in param_node.children:
                if child.type in ['primitive_type', 'type_identifier', 'struct_specifier']:
                    param_type = source_code[child.start_byte:child.end_byte]
                elif child.type == 'identifier':
                    param_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'pointer_declarator':
                    # Handle pointer parameters
                    param_type += "*"
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            param_name = source_code[grandchild.start_byte:grandchild.end_byte]
            
            return {
                'type': param_type.strip(),
                'name': param_name.strip() if param_name else 'unnamed'
            }
            
        except Exception:
            return None
    
    def _extract_includes(self, root_node, source_code: str) -> List[str]:
        """Extract #include statements."""
        includes = []
        
        def traverse_for_includes(node):
            if node.type == 'preproc_include':
                include_text = source_code[node.start_byte:node.end_byte]
                includes.append(include_text.strip())
            
            for child in node.children:
                traverse_for_includes(child)
        
        traverse_for_includes(root_node)
        return includes
    
    def _extract_defines(self, root_node, source_code: str) -> List[Dict[str, str]]:
        """Extract #define statements."""
        defines = []
        
        def traverse_for_defines(node):
            if node.type == 'preproc_def':
                define_text = source_code[node.start_byte:node.end_byte]
                # Parse #define NAME VALUE
                parts = define_text.split(None, 2)
                if len(parts) >= 2:
                    name = parts[1]
                    value = parts[2] if len(parts) > 2 else ""
                    defines.append({'name': name, 'value': value})
            
            for child in node.children:
                traverse_for_defines(child)
        
        traverse_for_defines(root_node)
        return defines
    
    def _extract_global_variables(self, root_node, source_code: str) -> List[Dict[str, str]]:
        """Extract global variable declarations."""
        variables = []
        
        def traverse_for_variables(node):
            if node.type == 'declaration' and node.parent == root_node:
                # This is a top-level declaration (global)
                var_info = self._parse_variable_declaration(node, source_code)
                if var_info:
                    variables.extend(var_info)
            
            for child in node.children:
                traverse_for_variables(child)
        
        traverse_for_variables(root_node)
        return variables
    
    def _parse_variable_declaration(self, node, source_code: str) -> List[Dict[str, str]]:
        """Parse a variable declaration."""
        variables = []
        var_type = ""
        
        # Extract type
        for child in node.children:
            if child.type in ['primitive_type', 'type_identifier', 'struct_specifier']:
                var_type = source_code[child.start_byte:child.end_byte]
                break
        
        # Extract variable names
        for child in node.children:
            if child.type == 'init_declarator':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        var_name = source_code[grandchild.start_byte:grandchild.end_byte]
                        variables.append({'type': var_type, 'name': var_name})
            elif child.type == 'identifier':
                var_name = source_code[child.start_byte:child.end_byte]
                variables.append({'type': var_type, 'name': var_name})
        
        return variables
    
    def _extract_structs(self, root_node, source_code: str) -> List[Dict[str, Any]]:
        """Extract struct definitions."""
        structs = []
        
        def traverse_for_structs(node):
            if node.type == 'struct_specifier':
                struct_info = self._parse_struct(node, source_code)
                if struct_info:
                    structs.append(struct_info)
            
            for child in node.children:
                traverse_for_structs(child)
        
        traverse_for_structs(root_node)
        return structs
    
    def _parse_struct(self, node, source_code: str) -> Optional[Dict[str, Any]]:
        """Parse a struct definition."""
        try:
            struct_name = ""
            fields = []
            
            # Extract struct name
            for child in node.children:
                if child.type == 'type_identifier':
                    struct_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'field_declaration_list':
                    # Extract fields
                    for field_node in child.children:
                        if field_node.type == 'field_declaration':
                            field_info = self._parse_struct_field(field_node, source_code)
                            if field_info:
                                fields.append(field_info)
            
            return {
                'name': struct_name,
                'fields': fields,
                'start_line': node.start_point[0] + 1,
                'end_line': node.end_point[0] + 1
            }
            
        except Exception:
            return None
    
    def _parse_struct_field(self, node, source_code: str) -> Optional[Dict[str, str]]:
        """Parse a struct field."""
        try:
            field_type = ""
            field_name = ""
            
            for child in node.children:
                if child.type in ['primitive_type', 'type_identifier']:
                    field_type = source_code[child.start_byte:child.end_byte]
                elif child.type == 'field_identifier':
                    field_name = source_code[child.start_byte:child.end_byte]
            
            return {'type': field_type, 'name': field_name}
            
        except Exception:
            return None
    
    def _extract_enums(self, root_node, source_code: str) -> List[Dict[str, Any]]:
        """Extract enum definitions."""
        enums = []
        
        def traverse_for_enums(node):
            if node.type == 'enum_specifier':
                enum_info = self._parse_enum(node, source_code)
                if enum_info:
                    enums.append(enum_info)
            
            for child in node.children:
                traverse_for_enums(child)
        
        traverse_for_enums(root_node)
        return enums
    
    def _parse_enum(self, node, source_code: str) -> Optional[Dict[str, Any]]:
        """Parse an enum definition."""
        try:
            enum_name = ""
            values = []
            
            for child in node.children:
                if child.type == 'type_identifier':
                    enum_name = source_code[child.start_byte:child.end_byte]
                elif child.type == 'enumerator_list':
                    for enum_child in child.children:
                        if enum_child.type == 'enumerator':
                            enum_value = source_code[enum_child.start_byte:enum_child.end_byte]
                            values.append(enum_value.strip())
            
            return {
                'name': enum_name,
                'values': values,
                'start_line': node.start_point[0] + 1,
                'end_line': node.end_point[0] + 1
            }
            
        except Exception:
            return None
    
    def extract_code_chunks(self, code_structure: CCodeStructure, 
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
                # Split into smaller chunks while preserving function boundaries
                sub_chunks = self._split_large_function(content, func, max_chunk_size)
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
                        'return_type': func.return_type,
                        'parameters': func.parameters,
                        'is_static': func.is_static,
                        'is_inline': func.is_inline
                    }
                )
                chunks.append(chunk)
        
        # Create chunks for global elements if they exist
        if code_structure.global_variables or code_structure.structs or code_structure.enums:
            global_content = self._extract_global_content(lines, code_structure)
            if global_content:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=1,
                    end_line=len(lines),
                    content=global_content,
                    chunk_type=ChunkType.GLOBAL,
                    metadata={
                        'includes': code_structure.includes,
                        'defines': code_structure.defines,
                        'global_variables': code_structure.global_variables,
                        'structs': code_structure.structs,
                        'enums': code_structure.enums
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_large_function(self, content: str, func: FunctionSignature, 
                            max_size: int) -> List[CodeChunk]:
        """Split a large function into smaller chunks."""
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
                    file_path=func.name,  # Will be set by caller
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
                file_path=func.name,  # Will be set by caller
                start_line=chunk_start_line,
                end_line=chunk_start_line + len(current_chunk_lines) - 1,
                content=chunk_content,
                function_name=func.name,
                chunk_type=ChunkType.FUNCTION,
                metadata={'is_partial': True, 'part_of': func.name}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_global_content(self, lines: List[str], 
                              code_structure: CCodeStructure) -> str:
        """Extract global content (includes, defines, global vars, structs, enums)."""
        global_lines = []
        
        # Add includes
        for include in code_structure.includes:
            global_lines.append(include)
        
        # Add defines
        for define in code_structure.defines:
            global_lines.append(f"#define {define['name']} {define['value']}")
        
        # Add struct definitions (simplified)
        for struct in code_structure.structs:
            struct_def = f"struct {struct['name']} {{"
            for field in struct['fields']:
                struct_def += f"\n    {field['type']} {field['name']};"
            struct_def += "\n};"
            global_lines.append(struct_def)
        
        # Add enum definitions
        for enum in code_structure.enums:
            enum_def = f"enum {enum['name']} {{"
            enum_def += ", ".join(enum['values'])
            enum_def += "};"
            global_lines.append(enum_def)
        
        return '\n'.join(global_lines) if global_lines else ""    
   
 # Regex-based fallback parsing methods
    def _extract_functions_regex(self, source_code: str, lines: List[str]) -> List[FunctionSignature]:
        """Extract functions using regex patterns."""
        functions = []
        
        # Pattern to match function definitions
        # This is a simplified pattern and may not catch all cases
        func_pattern = re.compile(
            r'^\s*(?:(static|inline|extern)\s+)*'  # Optional modifiers
            r'([a-zA-Z_][a-zA-Z0-9_*\s]+)\s+'      # Return type
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*'         # Function name
            r'\(([^)]*)\)\s*\{',                   # Parameters and opening brace
            re.MULTILINE
        )
        
        for match in func_pattern.finditer(source_code):
            modifiers = match.group(1) or ""
            return_type = match.group(2).strip()
            func_name = match.group(3)
            params_str = match.group(4)
            
            # Find line numbers
            start_pos = match.start()
            start_line = source_code[:start_pos].count('\n') + 1
            
            # Find end of function (simplified - look for matching braces)
            end_line = self._find_function_end_regex(source_code, match.end(), start_line)
            
            # Parse parameters
            parameters = self._parse_parameters_regex(params_str)
            
            func_sig = FunctionSignature(
                name=func_name,
                return_type=return_type,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                is_static='static' in modifiers,
                is_inline='inline' in modifiers
            )
            functions.append(func_sig)
        
        return functions
    
    def _find_function_end_regex(self, source_code: str, start_pos: int, start_line: int) -> int:
        """Find the end line of a function by counting braces."""
        brace_count = 1
        pos = start_pos
        line_num = start_line
        
        while pos < len(source_code) and brace_count > 0:
            char = source_code[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '\n':
                line_num += 1
            pos += 1
        
        return line_num
    
    def _parse_parameters_regex(self, params_str: str) -> List[Dict[str, str]]:
        """Parse function parameters from string."""
        parameters = []
        
        if not params_str.strip() or params_str.strip() == 'void':
            return parameters
        
        # Split by comma, but be careful of function pointers
        param_parts = []
        paren_count = 0
        current_param = ""
        
        for char in params_str:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                param_parts.append(current_param.strip())
                current_param = ""
                continue
            current_param += char
        
        if current_param.strip():
            param_parts.append(current_param.strip())
        
        # Parse each parameter
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
            
            # Simple parsing: last word is name, rest is type
            parts = param.split()
            if len(parts) >= 2:
                param_name = parts[-1]
                param_type = ' '.join(parts[:-1])
                
                # Handle pointer notation
                if param_name.startswith('*'):
                    param_type += '*'
                    param_name = param_name[1:]
                
                parameters.append({
                    'type': param_type,
                    'name': param_name
                })
            else:
                # Just type, no name
                parameters.append({
                    'type': param,
                    'name': 'unnamed'
                })
        
        return parameters
    
    def _extract_includes_regex(self, lines: List[str]) -> List[str]:
        """Extract include statements using regex."""
        includes = []
        include_pattern = re.compile(r'^\s*#include\s+[<"][^>"]+[>"]')
        
        for line in lines:
            match = include_pattern.match(line)
            if match:
                includes.append(match.group(0).strip())
        
        return includes
    
    def _extract_defines_regex(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extract define statements using regex."""
        defines = []
        define_pattern = re.compile(r'^\s*#define\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(.*)')
        
        for line in lines:
            match = define_pattern.match(line)
            if match:
                name = match.group(1)
                value = match.group(2).strip()
                defines.append({'name': name, 'value': value})
        
        return defines
    
    def _extract_global_variables_regex(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extract global variables using regex (simplified)."""
        variables = []
        
        # This is a very simplified approach
        # Look for lines that look like variable declarations at file scope
        var_pattern = re.compile(
            r'^\s*(?:static\s+|extern\s+|const\s+)*'
            r'([a-zA-Z_][a-zA-Z0-9_*\s]+)\s+'
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[;=]'
        )
        
        for line in lines:
            # Skip lines that are clearly not global variables
            if (line.strip().startswith('#') or 
                line.strip().startswith('//') or
                line.strip().startswith('/*') or
                '{' in line or '}' in line):
                continue
            
            match = var_pattern.match(line)
            if match:
                var_type = match.group(1).strip()
                var_name = match.group(2)
                variables.append({'type': var_type, 'name': var_name})
        
        return variables
    
    def _extract_structs_regex(self, source_code: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract struct definitions using regex."""
        structs = []
        
        # Pattern to match struct definitions
        struct_pattern = re.compile(
            r'struct\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
        
        for match in struct_pattern.finditer(source_code):
            struct_name = match.group(1)
            struct_body = match.group(2)
            
            # Find line numbers
            start_pos = match.start()
            end_pos = match.end()
            start_line = source_code[:start_pos].count('\n') + 1
            end_line = source_code[:end_pos].count('\n') + 1
            
            # Parse fields (simplified)
            fields = []
            field_lines = [line.strip() for line in struct_body.split('\n') if line.strip()]
            
            for field_line in field_lines:
                if field_line.endswith(';'):
                    field_line = field_line[:-1]  # Remove semicolon
                    parts = field_line.split()
                    if len(parts) >= 2:
                        field_type = ' '.join(parts[:-1])
                        field_name = parts[-1]
                        fields.append({'type': field_type, 'name': field_name})
            
            structs.append({
                'name': struct_name,
                'fields': fields,
                'start_line': start_line,
                'end_line': end_line
            })
        
        return structs
    
    def _extract_enums_regex(self, source_code: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract enum definitions using regex."""
        enums = []
        
        # Pattern to match enum definitions
        enum_pattern = re.compile(
            r'enum\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
        
        for match in enum_pattern.finditer(source_code):
            enum_name = match.group(1)
            enum_body = match.group(2)
            
            # Find line numbers
            start_pos = match.start()
            end_pos = match.end()
            start_line = source_code[:start_pos].count('\n') + 1
            end_line = source_code[:end_pos].count('\n') + 1
            
            # Parse enum values
            values = []
            enum_values = [v.strip() for v in enum_body.split(',') if v.strip()]
            
            for value in enum_values:
                # Remove any assignment (e.g., "VALUE = 1" -> "VALUE")
                if '=' in value:
                    value = value.split('=')[0].strip()
                values.append(value)
            
            enums.append({
                'name': enum_name,
                'values': values,
                'start_line': start_line,
                'end_line': end_line
            })
        
        return enums