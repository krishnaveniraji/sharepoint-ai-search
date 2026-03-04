"""
Text extraction from various document formats
"""
import PyPDF2
import docx
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extract text from various document formats"""
    
    @staticmethod
    def extract_from_pdf(content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return ""
    
    @staticmethod
    def extract_from_docx(content: bytes) -> str:
        """Extract text from Word document"""
        try:
            doc_file = BytesIO(content)
            doc = docx.Document(doc_file)
            
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX: {e}")
            return ""
    
    @staticmethod
    def extract_from_txt(content: bytes) -> str:
        """Extract text from plain text file"""
        try:
            # Try UTF-8 first
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1
                return content.decode('latin-1')
        except Exception as e:
            logger.error(f"Error extracting TXT: {e}")
            return ""
    
    @staticmethod
    def extract_text(filename: str, content: bytes) -> str:
        """Extract text based on file extension"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.pdf'):
            return TextExtractor.extract_from_pdf(content)
        elif filename_lower.endswith('.docx'):
            return TextExtractor.extract_from_docx(content)
        elif filename_lower.endswith('.txt'):
            return TextExtractor.extract_from_txt(content)
        else:
            logger.warning(f"Unsupported file type: {filename}")
            return ""
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """Get file extension"""
        if '.' in filename:
            return filename.split('.')[-1].lower()
        return "unknown"
