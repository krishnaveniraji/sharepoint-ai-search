"""
Text chunking utility for better search granularity
"""
from typing import List, Dict
import re

class TextChunker:
    """Split documents into overlapping chunks for better search results"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target size in tokens (roughly 4 chars per token)
            chunk_overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size * 4  # Convert tokens to characters (rough estimate)
        self.chunk_overlap = chunk_overlap * 4
    
    def chunk_text(self, text: str, doc_id: str, doc_metadata: Dict) -> List[Dict]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Full document text
            doc_id: Document identifier
            doc_metadata: Document metadata (title, department, etc.)
        
        Returns:
            List of chunk dictionaries with metadata
        """
        # Clean text
        text = self._clean_text(text)
        
        if not text or len(text) < 100:
            # Document too short, return as single chunk
            return [{
                "id": f"{doc_id}_chunk_0",
                "content": text,
                "chunk_index": 0,
                "total_chunks": 1,
                **doc_metadata
            }]
        
        # Split into chunks
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Get chunk
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Try to end at sentence boundary
            if end < len(text):
                # Find last period, exclamation, or question mark
                last_sentence = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('! '),
                    chunk_text.rfind('? ')
                )
                
                if last_sentence > self.chunk_size * 0.7:  # At least 70% of chunk size
                    end = start + last_sentence + 2
                    chunk_text = text[start:end]
            
            # Create chunk record
            chunk = {
                "id": f"{doc_id}_chunk_{chunk_index}",
                "content": chunk_text.strip(),
                "chunk_index": chunk_index,
                "total_chunks": -1,  # Will update after all chunks created
                **doc_metadata
            }
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            chunk_index += 1
        
        # Update total_chunks in all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def get_chunk_context(self, chunk: Dict) -> str:
        """
        Generate context string for chunk display
        
        Args:
            chunk: Chunk dictionary
        
        Returns:
            Context string (e.g., "Section 2 of 5")
        """
        if chunk["total_chunks"] == 1:
            return ""
        return f"Section {chunk['chunk_index'] + 1} of {chunk['total_chunks']}"