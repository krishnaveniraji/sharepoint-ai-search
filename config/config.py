"""
Configuration management for SharePoint AI application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for SharePoint AI"""
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_CHAT_MODEL = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4")
    AZURE_OPENAI_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # Azure AI Search Configuration
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "sharepoint-documents")
    
    # Microsoft Graph API Configuration
    GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID")
    GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID")
    GRAPH_CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET")
    
    # SharePoint Sites
    SHAREPOINT_SITES = {
        "HR": os.getenv("SHAREPOINT_SITE_HR"),
        "Finance": os.getenv("SHAREPOINT_SITE_FINANCE"),
        "IT": os.getenv("SHAREPOINT_SITE_IT"),
        "Sales": os.getenv("SHAREPOINT_SITE_SALES"),
        "Legal": os.getenv("SHAREPOINT_SITE_LEGAL")
    }
    
    # Chunking Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))  # In tokens
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))  # In tokens
    
    # Search Settings
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
    
    # Feature Flags
    GENERATE_TITLE_EMBEDDINGS = os.getenv("GENERATE_TITLE_EMBEDDINGS", "false").lower() == "true"
    
    # Default Security Settings
    DEFAULT_SECURITY_LEVEL = os.getenv("DEFAULT_SECURITY_LEVEL", "General")
    DEFAULT_ALLOWED_ROLES = os.getenv("DEFAULT_ALLOWED_ROLES", "All").split(",")
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        required_configs = [
            ("AZURE_OPENAI_KEY", cls.AZURE_OPENAI_KEY),
            ("AZURE_OPENAI_ENDPOINT", cls.AZURE_OPENAI_ENDPOINT),
            ("AZURE_SEARCH_ENDPOINT", cls.AZURE_SEARCH_ENDPOINT),
            ("AZURE_SEARCH_KEY", cls.AZURE_SEARCH_KEY),
            ("GRAPH_TENANT_ID", cls.GRAPH_TENANT_ID),
            ("GRAPH_CLIENT_ID", cls.GRAPH_CLIENT_ID),
            ("GRAPH_CLIENT_SECRET", cls.GRAPH_CLIENT_SECRET)
        ]
        
        missing = []
        for name, value in required_configs:
            if not value:
                missing.append(name)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        # Validate SharePoint sites
        if not any(cls.SHAREPOINT_SITES.values()):
            raise ValueError("At least one SharePoint site URL must be configured")
        
        return True
    
    @classmethod
    def get_summary(cls):
        """Get configuration summary for logging"""
        return {
            "azure_openai_endpoint": cls.AZURE_OPENAI_ENDPOINT,
            "azure_search_endpoint": cls.AZURE_SEARCH_ENDPOINT,
            "index_name": cls.AZURE_SEARCH_INDEX_NAME,
            "chunk_size": cls.CHUNK_SIZE,
            "chunk_overlap": cls.CHUNK_OVERLAP,
            "generate_title_embeddings": cls.GENERATE_TITLE_EMBEDDINGS,
            "sharepoint_sites": len([v for v in cls.SHAREPOINT_SITES.values() if v]),
            "default_security_level": cls.DEFAULT_SECURITY_LEVEL
        }
