"""
URL resolver utility module
Resolves hyperlinks and downloads linked PDFs
"""
import re
import requests
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from backend.utils.logger import logger
from backend.utils.file_ops import save_pdf
from backend import config

def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from text using regex
    
    Args:
        text: Text to extract URLs from
    
    Returns:
        List of URLs found
    """
    # Common URL patterns
    url_patterns = [
        r'https?://[^\s<>"{}|\\^`\[\]]+',  # HTTP/HTTPS URLs
        r'www\.[^\s<>"{}|\\^`\[\]]+',      # www URLs
        r'[a-zA-Z0-9.-]+\.(?:pdf|PDF)',    # PDF filenames that might be URLs
    ]
    
    urls = []
    for pattern in url_patterns:
        matches = re.findall(pattern, text)
        urls.extend(matches)
    
    # Remove duplicates and clean
    unique_urls = list(set(urls))
    cleaned_urls = []
    for url in unique_urls:
        url = url.strip('.,;:()[]{}"\'')
        if url.startswith('www.'):
            url = 'https://' + url
        if url.startswith('http'):
            cleaned_urls.append(url)
    
    return cleaned_urls

def is_pdf_url(url: str) -> bool:
    """
    Check if URL points to a PDF file
    
    Args:
        url: URL to check
    
    Returns:
        True if URL is likely a PDF
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith('.pdf') or 'pdf' in path

def download_pdf_from_url(url: str, destination_dir: Path, timeout: int = 30) -> Optional[Path]:
    """
    Download PDF from URL
    
    Args:
        url: URL to download from
        destination_dir: Directory to save PDF
        timeout: Request timeout in seconds
    
    Returns:
        Path to downloaded file, or None if download failed
    """
    try:
        logger.info(f"Downloading PDF from URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            logger.warning(f"URL does not appear to be a PDF: {url}")
            return None
        
        # Extract filename from URL or headers
        filename = None
        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                filename = filename_match.group(1)
        
        if not filename:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "downloaded.pdf"
        
        # Save file
        temp_file = destination_dir / f"temp_{filename}"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Move to final location
        final_path = save_pdf(temp_file, destination_dir, filename)
        temp_file.unlink()  # Remove temp file
        
        logger.info(f"Successfully downloaded PDF: {final_path}")
        return final_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading PDF from {url}: {e}")
        return None

def resolve_relative_url(base_url: str, relative_url: str) -> str:
    """
    Resolve relative URL against base URL
    
    Args:
        base_url: Base URL
        relative_url: Relative URL to resolve
    
    Returns:
        Absolute URL
    """
    return urljoin(base_url, relative_url)

