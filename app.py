"""
SharePoint AI Knowledge Assistant - Streamlit UI with RAG

A production-grade search interface with hybrid search + AI-powered answers.
"""

import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
from config.config import Config
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SharePoint AI Search",
    page_icon="🔍",
    layout="wide"
)

# Initialize clients (cached for performance)
@st.cache_resource
def get_search_client():
    """Initialize Azure Search client"""
    return SearchClient(
        endpoint=Config.AZURE_SEARCH_ENDPOINT,
        index_name=Config.AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(Config.AZURE_SEARCH_KEY)
    )

@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client for embeddings"""
    return AzureOpenAI(
        api_key=Config.AZURE_OPENAI_KEY,
        api_version=Config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
    )

def generate_query_embedding(query_text: str) -> list:
    """Generate embedding for search query"""
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            model=Config.AZURE_OPENAI_EMBEDDING_MODEL,
            input=query_text
        )
        return response.data[0].embedding
    except Exception as e:
        st.error(f"Error generating embedding: {e}")
        return None

def generate_rag_answer(query: str, search_results: list) -> dict:
    """Generate AI-powered answer using RAG pattern"""
    try:
        client = get_openai_client()
        
        # Build context from top 5 results
        context_parts = []
        for idx, result in enumerate(search_results[:5], 1):
            context_parts.append(f"""[{idx}] Title: {result.get('title', 'Unknown')}
Department: {result.get('department', 'Unknown')}
Content: {result.get('content', '')[:500]}...""")
        
        context = "\n\n".join(context_parts)
        
        # Build prompt
        system_message = """You are a helpful SharePoint knowledge assistant.
Answer questions based ONLY on the provided context.
ALWAYS cite sources using [1], [2], etc. in your answer.
If the answer is not in the context, say "I cannot find that information in the available documents."
Be concise and direct."""
        
        user_message = f"""Context from SharePoint documents:

{context}

Question: {query}

Answer (remember to cite sources):"""
        
        # Call GPT-4
        response = client.chat.completions.create(
            model=Config.AZURE_OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0
        )
        
        answer_text = response.choices[0].message.content.strip()
        
        # Return result
        return {
            'answer': answer_text,
            'sources': [
                {
                    'index': idx,
                    'title': result.get('title', 'Unknown'),
                    'department': result.get('department', 'Unknown'),
                    'web_url': result.get('web_url', '#'),
                    'content': result.get('content', '')[:200]
                }
                for idx, result in enumerate(search_results[:5], 1)
            ]
        }
        
    except Exception as e:
        st.error(f"RAG error: {e}")
        return {
            'answer': "I encountered an error generating the answer. Please try again.",
            'sources': []
        }

def hybrid_search(query_text: str, departments: list = None, top_k: int = 5):
    """
    Perform hybrid search with vector + keyword + semantic ranking
    """
    try:
        search_client = get_search_client()
        
        # Generate query embedding for vector search
        query_embedding = generate_query_embedding(query_text)
        
        if query_embedding is None:
            return None
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=50,
            fields="content_vector"
        )
        
        # Build filter for departments
        filter_expr = None
        if departments and len(departments) > 0:
            dept_filters = [f"department eq '{dept}'" for dept in departments]
            filter_expr = " or ".join(dept_filters)
        
        # Perform hybrid search
        results = search_client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name="semantic-config",
            select=[
                "id", "title", "content", "department", "file_type",
                "web_url", "chunk_index", "total_chunks", 
                "security_level", "created", "modified"
            ],
            filter=filter_expr,
            top=top_k
        )
        
        return list(results)
        
    except Exception as e:
        st.error(f"Search error: {e}")
        return None

def display_search_result(result, index):
    """Display a single search result"""
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Title with link
            st.markdown(f"### {index}. {result.get('title', 'Unknown')}")
            
            # Metadata badges
            metadata_html = f"""
            <div style="margin-bottom: 10px;">
                <span style="background-color: #1f77b4; color: white; padding: 3px 8px; border-radius: 3px; margin-right: 5px; font-size: 12px;">
                    {result.get('department', 'Unknown')}
                </span>
                <span style="background-color: #2ca02c; color: white; padding: 3px 8px; border-radius: 3px; margin-right: 5px; font-size: 12px;">
                    {result.get('file_type', 'Unknown').upper()}
                </span>
                <span style="background-color: #ff7f0e; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px;">
                    Chunk {result.get('chunk_index', 0) + 1} of {result.get('total_chunks', 1)}
                </span>
            </div>
            """
            st.markdown(metadata_html, unsafe_allow_html=True)
            
            # Content snippet
            content = result.get('content', '')
            snippet = content[:300] + "..." if len(content) > 300 else content
            st.markdown(f"*{snippet}*")
            
            # Link to SharePoint
            if result.get('web_url'):
                st.markdown(f"[📄 View in SharePoint]({result['web_url']})")
        
        with col2:
            # Score
            score = result.get('@search.score', 0)
            reranker_score = result.get('@search.reranker_score')
            
            st.metric("Relevance", f"{score:.2f}")
            
            if reranker_score:
                st.metric("Semantic", f"{reranker_score:.2f}")
        
        st.divider()

# Header
st.title("🔍 SharePoint AI Knowledge Assistant")
st.markdown("*Powered by Azure OpenAI + Hybrid Search + RAG*")

# Sidebar - Filters
with st.sidebar:
    st.header("⚙️ Filters")
    
    # Department filter
    st.subheader("Departments")
    dept_hr = st.checkbox("HR", value=True)
    dept_finance = st.checkbox("Finance", value=True)
    dept_it = st.checkbox("IT", value=True)
    dept_sales = st.checkbox("Sales", value=True)
    dept_legal = st.checkbox("Legal", value=True)
    
    # Number of results
    st.subheader("Results")
    top_k = st.slider("Number of results", 1, 10, 5)
    
    st.divider()
    
    # AI Features Toggle
    st.subheader("🤖 AI Features")
    enable_ai_answers = st.checkbox(
        "Enable AI Answers",
        value=True,
        help="Automatically generate AI-powered answers using GPT-4"
    )
    
    st.divider()
    
    # Info
    st.subheader("ℹ️ About")
    st.markdown("""
    This search uses:
    - **Vector Search**: Semantic understanding
    - **Keyword Search**: Exact matches
    - **Semantic Ranking**: AI re-ranking
    - **RAG**: AI-powered direct answers
    
    = Best of all worlds! 🎯
    """)

# Main search interface
search_query = st.text_input(
    "🔎 What are you looking for?",
    placeholder="e.g., How many vacation days do I get?",
    key="search_input"
)

# Search button
if st.button("Search", type="primary", use_container_width=True) or search_query:
    
    if not search_query or len(search_query.strip()) < 3:
        st.warning("⚠️ Please enter at least 3 characters to search.")
    else:
        # Build department filter
        selected_depts = []
        if dept_hr: selected_depts.append("HR")
        if dept_finance: selected_depts.append("Finance")
        if dept_it: selected_depts.append("IT")
        if dept_sales: selected_depts.append("Sales")
        if dept_legal: selected_depts.append("Legal")
        
        if not selected_depts:
            st.warning("⚠️ Please select at least one department.")
        else:
            # Perform search
            with st.spinner("🔍 Searching across SharePoint..."):
                results = hybrid_search(
                    query_text=search_query,
                    departments=selected_depts,
                    top_k=top_k
                )
            
            # Display results
            if results is None:
                st.error("❌ Search failed. Please check your configuration.")
            elif len(results) == 0:
                st.info("ℹ️ No results found. Try different keywords or departments.")
            else:
                st.success(f"✅ Found {len(results)} results")
                st.markdown("---")
                
                # Generate AI Answer (if enabled)
                if enable_ai_answers:
                    with st.spinner("🤖 Generating AI answer..."):
                        try:
                            rag_answer = generate_rag_answer(search_query, results)
                            
                            # Display AI Answer
                            st.markdown("### 💬 AI Answer")
                            st.info(rag_answer['answer'])
                            
                            # Display sources
                            with st.expander("📚 Sources Used", expanded=False):
                                for source in rag_answer['sources']:
                                    st.markdown(f"""
                                    **[{source['index']}] {source['title']}**  
                                    *Department:* {source['department']}  
                                    *Preview:* {source['content']}...  
                                    [View in SharePoint]({source['web_url']})
                                    """)
                            
                            st.markdown("---")
                        
                        except Exception as e:
                            st.error(f"Error generating AI answer: {e}")
                
                # Display full search results
                st.markdown("### 📄 Full Search Results")
                for idx, result in enumerate(results, 1):
                    display_search_result(result, idx)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    Built with ❤️ using Azure OpenAI, Azure AI Search, and Streamlit<br>
    Features: Hybrid Search (Vector + Keyword + Semantic) + RAG
</div>
""", unsafe_allow_html=True)
