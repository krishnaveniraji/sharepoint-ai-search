"""
SharePoint connector using Microsoft Graph API
"""
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
import aiohttp
import asyncio
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SharePointConnector:
    """Connect to SharePoint and retrieve documents"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        self.client = GraphServiceClient(credentials=self.credential)
    
    async def get_site_id(self, site_url: str) -> str:
        """Get SharePoint site ID from URL"""
        try:
            # Extract hostname and path from URL
            # https://veniai.sharepoint.com/sites/HRDepartment
            # -> veniai.sharepoint.com:/sites/HRDepartment
            parts = site_url.replace("https://", "").split("/", 1)
            hostname = parts[0]
            site_path = "/" + parts[1] if len(parts) > 1 else "/"
            
            # Get site by URL
            site = await self.client.sites.by_site_id(f"{hostname}:{site_path}").get()
            logger.info(f"Found site: {site.display_name} (ID: {site.id})")
            return site.id
        except Exception as e:
            logger.error(f"Error getting site ID for {site_url}: {e}")
            raise
    
    async def list_documents(self, site_id: str) -> List[Dict]:
        """List all documents in a site's document library"""
        try:
            documents = []
            
            # Get default document library (drive)
            drive = await self.client.sites.by_site_id(site_id).drive.get()
            
            # Get items in root folder - FIXED API call
            items = await self.client.drives.by_drive_id(drive.id).items.by_drive_item_id('root').children.get()
            
            if items and items.value:
                for item in items.value:
                    if item.file:  # It's a file, not a folder
                        doc_info = {
                            "id": item.id,
                            "name": item.name,
                            "size": item.size,
                            "web_url": item.web_url,
                            "download_url": item.additional_data.get("@microsoft.graph.downloadUrl"),
                            "created": str(item.created_date_time) if item.created_date_time else None,
                            "modified": str(item.last_modified_date_time) if item.last_modified_date_time else None
                        }
                        documents.append(doc_info)
            
            logger.info(f"Found {len(documents)} documents in site")
            return documents
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise
    
    async def download_document_content(self, download_url: str) -> bytes:
        """Download document content"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        logger.info(f"Downloaded {len(content)} bytes")
                        return content
                    else:
                        raise Exception(f"Download failed: {response.status}")
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            raise
    
    async def get_all_documents_from_sites(self, site_urls: Dict[str, str]) -> List[Dict]:
        """Get all documents from multiple SharePoint sites"""
        all_documents = []
        
        for dept_name, site_url in site_urls.items():
            try:
                logger.info(f"\nProcessing {dept_name} site...")
                logger.info(f"URL: {site_url}")
                
                site_id = await self.get_site_id(site_url)
                documents = await self.list_documents(site_id)
                
                # Add department info to each document
                for doc in documents:
                    doc['department'] = dept_name
                    doc['site_url'] = site_url
                
                all_documents.extend(documents)
                logger.info(f"✓ Added {len(documents)} documents from {dept_name}")
                
            except Exception as e:
                logger.error(f"✗ Error processing {dept_name}: {e}")
                continue
        
        logger.info(f"\n✓ Total documents found: {len(all_documents)}")
        return all_documents


# Test function
async def test_connector():
    """Test the SharePoint connector"""
    from config.config import Config
    
    print("\n" + "="*60)
    print("Testing SharePoint Connector")
    print("="*60 + "\n")
    
    connector = SharePointConnector(
        tenant_id=Config.GRAPH_TENANT_ID,
        client_id=Config.GRAPH_CLIENT_ID,
        client_secret=Config.GRAPH_CLIENT_SECRET
    )
    
    documents = await connector.get_all_documents_from_sites(Config.SHAREPOINT_SITES)
    
    print(f"\n✓ Successfully connected to SharePoint!")
    print(f"✓ Found {len(documents)} total documents\n")
    
    # Show sample documents
    print("Sample documents:")
    for doc in documents[:5]:
        print(f"  - [{doc['department']}] {doc['name']}")
    
    return documents

if __name__ == "__main__":
    asyncio.run(test_connector())