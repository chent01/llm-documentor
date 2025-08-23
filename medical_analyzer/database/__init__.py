"""
Database layer for the Medical Software Analysis Tool.
"""

from .schema import DatabaseManager, init_database

__all__ = ['DatabaseManager', 'init_database']