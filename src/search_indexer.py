"""
Azure AI Search indexer with vector search capabilities and new schema
"""
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI
import logging
from typing import List, Dict
import time
from datetime import datetime

# Import schema
from config.config import Config
from src.search_schema import get_search_index_schema

logger = logging.getLogger(__name__)

class SearchIndexer:
    """Index documents in Azure AI Search with hybrid search capabilities"""
    
    def __init__(self, search_endpoint: str, search_key: str, 
                 openai_key: str, openai_endpoint: str, openai_version: str):
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_client = SearchIndexClient(search_endpoint, AzureKeyCredential(search_key))
        self.search_client = None  # Will be set after index creation
        
        # OpenAI client for embeddings
        self.openai_client = AzureOpenAI(
            api_key=openai_key,
            api_version=openai_version,
            azure_endpoint=openai_endpoint
        )
        
        # Configuration
        from config.config import Config
        self.generate_title_embeddings = Config.GENERATE_TITLE_EMBEDDINGS
    
    def create_index(self, index_name: str) -> None:
        """Create search index using schema definition"""
        try:
            logger.info(f"Creating index: {index_name}")
            logger.info("Configuring hybrid search (vector + keyword + semantic ranking)")
            
            # Get schema from centralized definition
            index = get_search_index_schema(index_name)
            
            # Create/update index
            result = self.index_client.create_or_update_index(index)
            
            logger.info(f"✓ Index created: {result.name}")
            logger.info(f"  ✓ Vector search: Enabled (HNSW algorithm)")
            logger.info(f"  ✓ Keyword search: Enabled (BM25 + standard.lucene analyzer)")
            logger.info(f"  ✓ Semantic ranking: Enabled (L2 re-ranking)")
            logger.info(f"  ✓ Hybrid search: Ready!")
            logger.info(f"  ✓ Title embeddings: {'Enabled' if self.generate_title_embeddings else 'Disabled'}")
            
            # Initialize search client
            self.search_client = SearchClient(
                self.search_endpoint,
                index_name,
                AzureKeyCredential(self.search_key)
            )
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        try:
            # Limit text to 8000 characters for embedding
            text = text[:8000]
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    def generate_rag_answer(self, query: str, search_results: list) -> dict:
    """
    Generate AI-powered answer using RAG pattern
    
    Args:
        query: User's question
        search_results: Top search results from hybrid search
        
    Returns:
        dict with 'answer' and 'sources'
    """
    try:
        # STEP 1: Build context from top 5 results
        context_parts = []
        for idx, result in enumerate(search_results[:5], 1):
            context_parts.append(f"""[{idx}] Title: {result['title']}
Department: {result['department']}
Content: {result['content'][:500]}...""")
        
        context = "\n\n".join(context_parts)
        
        # STEP 2: Build the prompt
        system_message = """You are a helpful SharePoint knowledge assistant.
Answer questions based ONLY on the provided context.
ALWAYS cite sources using [1], [2], etc. in your answer.
If the answer is not in the context, say "I cannot find that information in the available documents."
Be concise and direct."""
        
        user_message = f"""Context from SharePoint documents:

{context}

Question: {query}

Answer (remember to cite sources):"""
        
        # STEP 3: Call GPT-4
        from config.config import Config  # Import at top of file!
        
        response = self.openai_client.chat.completions.create(
            model=Config.AZURE_OPENAI_CHAT_MODEL,  # Use deployment name!
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0  # Deterministic for factual answers!
        )
        
        # STEP 4: Extract answer
        answer_text = response.choices[0].message.content.strip()
        
        # STEP 5: Return formatted result
        return {
            'answer': answer_text,
            'sources': [
                {
                    'index': idx,
                    'title': result['title'],
                    'department': result['department'],
                    'web_url': result.get('web_url', '#'),
                    'content': result['content'][:200]  # Preview
                }
                for idx, result in enumerate(search_results[:5], 1)
            ]
        }
        
    except Exception as e:
        logger.error(f"RAG error: {e}")
        return {
            'answer': "I encountered an error generating the answer. Please try again.",
            'sources': []
        }


        


    
    def index_documents(self, documents: List[Dict]) -> None:
        """Index documents with embeddings and new schema fields"""
        if not self.search_client:
            raise Exception("Search client not initialized. Call create_index first.")
        
        indexed_docs = []
        total_docs = len(documents)
        
        logger.info(f"\nStarting indexing of {total_docs} chunks...")
        
        for i, doc in enumerate(documents, 1):
            try:
                logger.info(f"\n[{i}/{total_docs}] Indexing: {doc['title']} (chunk {doc.get('chunk_index', 0)})")
                logger.info(f"  Department: {doc['department']}")
                logger.info(f"  Size: {len(doc['content'])} characters")
                
                # Generate content embedding
                logger.info(f"  Generating content embedding...")
                content_embedding = self.generate_embedding(doc['content'])
                logger.info(f"  ✓ Content embedding generated (dimension: {len(content_embedding)})")
                
                # Generate title embedding if enabled
                title_embedding = None
                if self.generate_title_embeddings:
                    logger.info(f"  Generating title embedding...")
                    title_embedding = self.generate_embedding(doc['title'])
                    logger.info(f"  ✓ Title embedding generated")
                
                
                # Prepare document for indexing with all new fields
                search_doc = {
                    # Identity fields
                    "id": doc['id'].replace('/', '_').replace('!', '_'),
                    "document_id": doc['id'],
                    "chunk_id": f"{doc['id']}_chunk_{doc.get('chunk_index', 0)}",
                    
                    # Content fields
                    "content": doc['content'][:10000],
                    "content_vector": content_embedding,
                    "title": doc['title'],
                    "web_url": doc['web_url'],
                    "file_type": doc['file_type'],
                    
                    # Organization fields
                    "department": doc['department'],
                    "security_level": doc.get('security_level', 'General'),
                    "is_confidential": doc.get('is_confidential', False),
                    "allowed_roles": doc.get('allowed_roles', ['All']),
                    
                    # Chunking fields
                    "chunk_index": doc.get('chunk_index', 0),
                    "total_chunks": doc.get('total_chunks', 1),
                    
                    # Metadata fields
                    "created": doc.get('created', ''),
                    "modified": doc.get('modified', ''),
                    "indexed_at": datetime.utcnow(),
                    
                    # Analytics fields
                    "confidence_base_score": 0.0
                }

                # Only add title_vector if it was generated
                if title_embedding is not None:
                    search_doc["title_vector"] = title_embedding
                
                indexed_docs.append(search_doc)
                
                # Upload in batches of 10
                if len(indexed_docs) >= 10:
                    logger.info(f"\n  Uploading batch of {len(indexed_docs)} documents...")
                    self.search_client.upload_documents(documents=indexed_docs)
                    logger.info(f"  ✓ Batch uploaded successfully")
                    indexed_docs = []
                    time.sleep(1)  # Small delay between batches
            
            except Exception as e:
                logger.error(f"  ✗ Error indexing {doc['title']}: {e}")
                continue
        
        # Upload remaining documents
        if indexed_docs:
            logger.info(f"\nUploading final batch of {len(indexed_docs)} documents...")
            self.search_client.upload_documents(documents=indexed_docs)
            logger.info(f"✓ Final batch uploaded")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Indexing complete!")
        logger.info(f"✓ Total documents indexed: {total_docs}")
        logger.info(f"{'='*60}\n")
