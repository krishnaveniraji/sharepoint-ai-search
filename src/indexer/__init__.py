"""
Document Indexer Module

Provides reusable indexer classes for SharePoint document indexing.

Classes:
- DocumentIndexer: Main indexer for full and incremental indexing
- IncrementalIndexer: Future enhancement for delta indexing
"""

from src.indexer.document_indexer import DocumentIndexer

__all__ = ['DocumentIndexer']
