"""
Azure AI Search Index Schema Definition

This module defines the complete schema for the SharePoint AI search index,
including all fields, analyzers, vector search configuration, and semantic ranking.

Schema includes:
- Identity fields (id, document_id, chunk_id)
- Content fields (content, content_vector, title, title_vector)
- Organization fields (department, security_level, is_confidential, allowed_roles)
- Chunking fields (chunk_index, total_chunks)
- Metadata fields (created, modified, indexed_at)
- Analytics fields (confidence_base_score)
"""

from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)
from typing import Dict, Any


def get_search_index_schema(index_name: str) -> SearchIndex:
    """
    Create complete Azure AI Search index schema with hybrid search capabilities.
    
    Features:
    - Vector search (semantic similarity via embeddings)
    - Keyword search (BM25 full-text search)
    - Semantic ranking (Microsoft L2 re-ranking)
    - Security filtering (role-based access)
    - Faceting support (for UI filters)
    
    Args:
        index_name: Name of the search index
    
    Returns:
        SearchIndex object with complete schema
    """
    
    # ========================================
    # FIELD DEFINITIONS
    # ========================================
    
    fields = [
        # 🔑 IDENTITY FIELDS
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,  # Primary key
            filterable=True
        ),
        SimpleField(
            name="document_id",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        
        # 📄 CONTENT FIELDS
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="standard.lucene"  # Multi-language support, better than en.microsoft
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,  # CRITICAL: Must be searchable for vector search
            vector_search_dimensions=1536,  # text-embedding-ada-002 dimension
            vector_search_profile_name="vector-profile"
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="standard.lucene"
        ),
        SearchField(
            name="title_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="vector-profile"
        ),
        SimpleField(
            name="web_url",
            type=SearchFieldDataType.String,
            retrievable=True  # Can retrieve but not search/filter
        ),
        SimpleField(
            name="file_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True  # Enable faceting for UI
        ),
        
        # 🏢 ORGANIZATION FIELDS
        SimpleField(
            name="department",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,  # Enable department faceting
            sortable=True
        ),
        SimpleField(
            name="security_level",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True  # Values: Public, Department, Confidential
        ),
        SimpleField(
            name="is_confidential",
            type=SearchFieldDataType.Boolean,
            filterable=True  # Fast boolean filtering
        ),
        SimpleField(
            name="allowed_roles",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,  # Enable role-based filtering
            facetable=True
        ),
        
        # 🧩 CHUNKING FIELDS
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="total_chunks",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True
        ),
        
        # 📅 METADATA FIELDS
        SimpleField(
            name="created",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True  # Enable sorting by creation date
        ),
        SimpleField(
            name="modified",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True  # Enable sorting by modification date
        ),
        SimpleField(
            name="indexed_at",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True  # When document was indexed
        ),
        
        # 📊 ANALYTICS FIELDS
        SimpleField(
            name="confidence_base_score",
            type=SearchFieldDataType.Double,
            retrievable=True  # Store similarity scores for analytics
        )
    ]
    
    # ========================================
    # VECTOR SEARCH CONFIGURATION
    # ========================================
    
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config",
                parameters={
                    "m": 4,  # Number of bi-directional links (4 = balanced)
                    "efConstruction": 400,  # Index build quality (400 = good)
                    "efSearch": 500,  # Query time quality (500 = good)
                    "metric": "cosine"  # Cosine similarity for embeddings
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config"
            )
        ]
    )
    
    # ========================================
    # SEMANTIC SEARCH CONFIGURATION
    # ========================================
    
    semantic_config = SemanticConfiguration(
        name="semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),  # Primary semantic field
            content_fields=[
                SemanticField(field_name="content")  # Content for semantic understanding
            ],
            keywords_fields=[
                SemanticField(field_name="department")  # Additional context
            ]
        )
    )
    
    semantic_search = SemanticSearch(
        configurations=[semantic_config]
    )
    
    # ========================================
    # CREATE INDEX
    # ========================================
    
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    return index


def get_schema_summary() -> Dict[str, Any]:
    """
    Get human-readable summary of schema fields.
    
    Returns:
        Dictionary with field categories and descriptions
    """
    return {
        "identity_fields": {
            "id": "Primary key (Azure Search)",
            "document_id": "Original SharePoint document ID",
            "chunk_id": "Unique chunk identifier"
        },
        "content_fields": {
            "content": "Searchable text (keyword search)",
            "content_vector": "1536-dim embedding (vector search)",
            "title": "Document title (searchable)",
            "title_vector": "Title embedding (optional)",
            "web_url": "SharePoint URL",
            "file_type": "pdf, docx, txt, etc."
        },
        "organization_fields": {
            "department": "HR, Finance, IT, Sales, Legal",
            "security_level": "Public, Department, Confidential",
            "is_confidential": "Boolean for fast filtering",
            "allowed_roles": "Array of roles with access"
        },
        "chunking_fields": {
            "chunk_index": "Position in document (0, 1, 2...)",
            "total_chunks": "Total chunks for this document"
        },
        "metadata_fields": {
            "created": "Document creation date",
            "modified": "Last modified date",
            "indexed_at": "When indexed in search"
        },
        "analytics_fields": {
            "confidence_base_score": "Similarity/relevance score"
        },
        "search_capabilities": {
            "vector_search": "Semantic similarity via embeddings",
            "keyword_search": "BM25 full-text search",
            "semantic_ranking": "Microsoft L2 re-ranking",
            "hybrid_search": "Combines all three methods"
        }
    }


# Example usage and documentation
if __name__ == "__main__":
    import json
    
    print("=" * 70)
    print("AZURE AI SEARCH - INDEX SCHEMA SUMMARY")
    print("=" * 70)
    
    summary = get_schema_summary()
    print(json.dumps(summary, indent=2))
    
    print("\n" + "=" * 70)
    print("SCHEMA CONFIGURATION")
    print("=" * 70)
    print("\nVector Search:")
    print("  Algorithm: HNSW (Hierarchical Navigable Small World)")
    print("  Dimensions: 1536 (text-embedding-ada-002)")
    print("  Metric: Cosine similarity")
    print("  Parameters: m=4, efConstruction=400, efSearch=500")
    
    print("\nSemantic Ranking:")
    print("  Enabled: Yes")
    print("  Title field: title")
    print("  Content fields: content")
    print("  Keyword fields: department")
    
    print("\nHybrid Search:")
    print("  ✓ Vector search (semantic)")
    print("  ✓ Keyword search (BM25)")
    print("  ✓ Semantic ranking (L2)")
    print("  = Best results from all three methods")
    
    print("\n" + "=" * 70)
