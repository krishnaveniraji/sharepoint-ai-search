"""
Full Document Indexing Script

Indexes all documents from all configured SharePoint sites.

Usage:
    python scripts/index_all.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer import DocumentIndexer
from config.config import Config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def main():
    """Main indexing entry point"""
    print("\n" + "="*70)
    print("SHAREPOINT AI - FULL DOCUMENT INDEXING")
    print("="*70 + "\n")
    
    try:
        # Initialize indexer
        indexer = DocumentIndexer(Config)
        
        # Run full indexing
        metrics = await indexer.index_all_documents()
        
        # Check results
        if metrics.failed_docs > 0:
            print(f"\n⚠️  Warning: {metrics.failed_docs} documents failed to index")
            sys.exit(1)
        else:
            print("\n✅ All documents indexed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Indexing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
