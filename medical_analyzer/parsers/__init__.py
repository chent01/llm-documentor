"""
Code parsers for C and JavaScript analysis.
"""

from .c_parser import CParser

try:
    from .js_parser import JSParser
except ImportError:
    JSParser = None

try:
    from .parser_service import ParserService
except ImportError:
    ParserService = None

__all__ = ['CParser']
if JSParser:
    __all__.append('JSParser')
if ParserService:
    __all__.append('ParserService')