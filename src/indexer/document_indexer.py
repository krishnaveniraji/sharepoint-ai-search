"""
Reusable Document Indexer Class

Provides a clean, reusable interface for indexing SharePoint documents
with support for full indexing, single document indexing, and future
incremental indexing.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.sharepoint_connector import SharePointConnector
from src.search_indexer import SearchIndexer
from src.utils.text_extractor import TextExtractor
from src.utils.text_chunker import TextChunker
from config.config import Config
from src.rbac.document_classifier import classify_document

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexingMetrics:
    """Track indexing metrics"""
    def __init__(self):
        self.total_docs = 0
        self.successful_docs = 0
        self.failed_docs = 0
        self.total_chunks = 0
        self.skipped_docs = 0
        self.start_time = None
        self.end_time = None
        self.failed_documents = []
    
    def log_summary(self):
        """Log indexing summary"""
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        logger.info("\n" + "="*70)
        logger.info("INDEXING SUMMARY")
        logger.info("="*70)
        logger.info(f"Total documents processed: {self.total_docs}")
        logger.info(f"Successfully indexed: {self.successful_docs}")
        logger.info(f"Failed: {self.failed_docs}")
        logger.info(f"Skipped (no content): {self.skipped_docs}")
        logger.info(f"Total chunks created: {self.total_chunks}")
        logger.info(f"Duration: {duration:.1f} seconds")
        
        if self.failed_documents:
            logger.info("\nFailed documents:")
            for doc in self.failed_documents:
                logger.info(f"  - {doc['name']}: {doc['error']}")
        
        logger.info("="*70 + "\n")


class DocumentIndexer:
    """
    Reusable document indexer for SharePoint documents.
    
    Supports:
    - Full re-indexing
    - Single document indexing
    - Configuration validation
    - Error handling with continuation
    - Metrics tracking
    """
    
    def __init__(self, config=None):
        """
        Initialize document indexer.
        
        Args:
            config: Configuration object (defaults to Config)
        """
        self.config = config or Config
        self.metrics = IndexingMetrics()
        
        # Initialize connectors (lazy initialization)
        self._sharepoint_connector = None
        self._search_indexer = None
        self._chunker = None
    
    @property
    def sharepoint_connector(self):
        """Lazy initialize SharePoint connector"""
        if not self._sharepoint_connector:
            self._sharepoint_connector = SharePointConnector(
                tenant_id=self.config.GRAPH_TENANT_ID,
                client_id=self.config.GRAPH_CLIENT_ID,
                client_secret=self.config.GRAPH_CLIENT_SECRET
            )
        return self._sharepoint_connector
    
    @property
    def search_indexer(self):
        """Lazy initialize search indexer"""
        if not self._search_indexer:
            self._search_indexer = SearchIndexer(
                search_endpoint=self.config.AZURE_SEARCH_ENDPOINT,
                search_key=self.config.AZURE_SEARCH_KEY,
                openai_key=self.config.AZURE_OPENAI_KEY,
                openai_endpoint=self.config.AZURE_OPENAI_ENDPOINT,
                openai_version=self.config.AZURE_OPENAI_API_VERSION
            )
        return self._search_indexer
    
    @property
    def chunker(self):
        """Lazy initialize text chunker"""
        if not self._chunker:
            self._chunker = TextChunker(
                chunk_size=self.config.CHUNK_SIZE,
                chunk_overlap=self.config.CHUNK_OVERLAP
            )
        return self._chunker
    
    def validate_configuration(self):
        """
        Validate configuration before indexing.
        
        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("Validating configuration...")
        
        try:
            self.config.validate()
            logger.info("✓ Configuration valid")
            
            # Log configuration summary
            summary = self.config.get_summary()
            logger.info("\nConfiguration:")
            for key, value in summary.items():
                logger.info(f"  {key}: {value}")
            
            return True
        except ValueError as e:
            logger.error(f"✗ Configuration error: {e}")
            raise
    
    async def index_all_documents(self) -> IndexingMetrics:
        """
        Index all documents from all SharePoint sites.
        
        Returns:
            IndexingMetrics object with results
        """
        self.metrics = IndexingMetrics()
        self.metrics.start_time = datetime.now()
        
        try:
            # Step 1: Validate configuration
            self.validate_configuration()
            
            # Step 2: Connect to SharePoint
            logger.info("\n" + "="*70)
            logger.info("STEP 1: Connecting to SharePoint")
            logger.info("="*70)
            
            sharepoint_docs = await self.sharepoint_connector.get_all_documents_from_sites(
                self.config.SHAREPOINT_SITES
            )
            
            logger.info(f"✓ Found {len(sharepoint_docs)} documents")
            self.metrics.total_docs = len(sharepoint_docs)
            
            # Step 3: Extract text
            logger.info("\n" + "="*70)
            logger.info("STEP 2: Extracting text from documents")
            logger.info("="*70)
            
            extracted_docs = await self._extract_documents(sharepoint_docs)
            logger.info(f"✓ Extracted {len(extracted_docs)} documents")
            self.metrics.skipped_docs = len(sharepoint_docs) - len(extracted_docs)
            
            # Step 4: Chunk documents
            logger.info("\n" + "="*70)
            logger.info("STEP 3: Chunking documents")
            logger.info("="*70)
            
            chunks = self._chunk_documents(extracted_docs)
            logger.info(f"✓ Created {len(chunks)} chunks")
            self.metrics.total_chunks = len(chunks)
            
            # Step 5: Create index and upload
            logger.info("\n" + "="*70)
            logger.info("STEP 4: Indexing in Azure AI Search")
            logger.info("="*70)
            
            self.search_indexer.create_index(self.config.AZURE_SEARCH_INDEX_NAME)
            self.search_indexer.index_documents(chunks)
            
            self.metrics.successful_docs = len(extracted_docs)
            self.metrics.end_time = datetime.now()
            
            self.metrics.log_summary()
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            self.metrics.end_time = datetime.now()
            raise
    
    async def _extract_documents(self, sharepoint_docs: List[Dict]) -> List[Dict]:
        """Extract text from SharePoint documents"""
        extracted = []
        
        for i, doc in enumerate(sharepoint_docs, 1):
            try:
                logger.info(f"\n[{i}/{len(sharepoint_docs)}] {doc['name']}")
                logger.info(f"  Department: {doc['department']}")
                
                # Download
                content = await self.sharepoint_connector.download_document_content(doc['download_url'])
                logger.info(f"  ✓ Downloaded {len(content)} bytes")
                
                # Extract text
                text = TextExtractor.extract_text(doc['name'], content)
                classification = classify_document(doc['name'], doc['department'])
                if text:
                    extracted.append({
                        "id": doc['id'],
                        "title": doc['name'],
                        "content": text,
                        "department": doc['department'],
                        "file_type": TextExtractor.get_file_type(doc['name']),
                        "web_url": doc['web_url'],
                        "created": doc.get('created', ''),
                        "modified": doc.get('modified', ''),
                        # Security fields (default for now)
                        "security_level": classification['security_level'],
                        "is_confidential": classification['is_confidential'],
                        "allowed_roles": classification['allowed_roles']
                        
                    })
                    logger.info(f"  ✓ Extracted {len(text)} characters")
                else:
                    logger.warning(f"  ⚠ No text extracted")
                    
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
                self.metrics.failed_documents.append({
                    'name': doc['name'],
                    'error': str(e)
                })
                continue
        
        return extracted
    
    def _chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Chunk documents for better search granularity"""
        all_chunks = []
        
        for doc in documents:
            chunks = self.chunker.chunk_text(
                text=doc['content'],
                doc_id=doc['id'],
                doc_metadata={
                    'title': doc['title'],
                    'department': doc['department'],
                    'file_type': doc['file_type'],
                    'web_url': doc['web_url'],
                    'created': doc['created'],
                    'modified': doc['modified'],
                    'security_level': doc['security_level'],
                    'is_confidential': doc['is_confidential'],
                    'allowed_roles': doc['allowed_roles']
                }
            )
            all_chunks.extend(chunks)
            
            if len(chunks) > 1:
                logger.info(f"  {doc['title']}: {len(chunks)} chunks")
        
        logger.info(f"\nAverage: {len(all_chunks) / len(documents):.1f} chunks per document")
        return all_chunks
    
    # Future methods (stubs for Phase 2)
    async def index_document(self, document_id: str):
        """Index a single document (Future enhancement)"""
        raise NotImplementedError("Single document indexing coming in Phase 2")
    
    async def index_modified_since(self, timestamp: datetime):
        """Incremental indexing (Future enhancement)"""
        raise NotImplementedError("Incremental indexing coming in Phase 2")
    
    async def delete_document(self, document_id: str):
        """Delete document from index (Future enhancement)"""
        raise NotImplementedError("Document deletion coming in Phase 2")
