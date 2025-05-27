"""
Пакет парсеров для различных фриланс площадок
"""

from .freelancespace_parser_simple import FreelanceSpaceParserSimple
from .fl_parser import FLParser
from .combined_parser import CombinedParser

__all__ = ['FreelanceSpaceParserSimple', 'FLParser', 'CombinedParser'] 