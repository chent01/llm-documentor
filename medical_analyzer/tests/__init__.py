"""
Test generation and testing utilities for the Medical Software Analysis Tool.

This module provides test generation capabilities and testing utilities
for medical device software analysis.
"""

from .test_generator import CodeTestGenerator, CodeTestSuite, CodeTestSkeleton

# Provide aliases for backward compatibility
TestGenerator = CodeTestGenerator
TestSuite = CodeTestSuite
TestSkeleton = CodeTestSkeleton

__all__ = ['CodeTestGenerator', 'CodeTestSuite', 'CodeTestSkeleton', 'TestGenerator', 'TestSuite', 'TestSkeleton']
