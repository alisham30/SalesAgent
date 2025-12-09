"""
Hyperlink scanner module
Extracts hyperlinks from PDFs and downloads linked PDFs
"""
from pathlib import Path
from typing import List
from backend import config
from backend.utils.logger import logger
from backend.utils.url_resolver import extract_urls_from_text, is_pdf_url, download_pdf_from_url
from backend.pdf_engine.pdf_extractor import PDFExtractor

class HyperlinkScanner:
    """Scans PDFs for hyperlinks and downloads linked PDFs"""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
    
    def scan_and_download_links(self, pdf_path: Path) -> List[Path]:
        """
        Scan PDF for hyperlinks and download linked PDFs
        Extracts both text URLs and embedded hyperlink annotations
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            List of paths to downloaded PDF files
        """
        logger.info(f"Scanning for hyperlinks in: {pdf_path}")
        
        all_urls = []
        
        # Method 1: Extract URLs from text
        text = self.pdf_extractor.extract_text(pdf_path)
        if text:
            text_urls = extract_urls_from_text(text)
            all_urls.extend(text_urls)
            logger.info(f"Found {len(text_urls)} URLs in text")
        
        # Method 2: Extract embedded hyperlinks from PDF annotations (using pdfplumber)
        embedded_urls = self._extract_embedded_links(pdf_path)
        all_urls.extend(embedded_urls)
        logger.info(f"Found {len(embedded_urls)} embedded hyperlinks")
        
        # Method 3: Extract links from PyPDF2 annotations
        pypdf2_urls = self._extract_pypdf2_links(pdf_path)
        all_urls.extend(pypdf2_urls)
        logger.info(f"Found {len(pypdf2_urls)} links from PyPDF2 annotations")
        
        # Remove duplicates
        unique_urls = list(set(all_urls))
        logger.info(f"Total unique URLs found: {len(unique_urls)}")
        
        # Filter for PDF URLs or specification document links
        pdf_urls = []
        for url in unique_urls:
            if is_pdf_url(url):
                pdf_urls.append(url)
            elif 'specification' in url.lower() or 'spec' in url.lower() or 'download' in url.lower():
                # Might be a specification document
                pdf_urls.append(url)
        
        logger.info(f"Found {len(pdf_urls)} PDF/specification URLs")
        
        # Download PDFs
        downloaded_files = []
        for url in pdf_urls:
            try:
                downloaded_file = download_pdf_from_url(url, config.LINKED_PDFS_DIR)
                if downloaded_file:
                    downloaded_files.append(downloaded_file)
            except Exception as e:
                logger.error(f"Error downloading PDF from {url}: {e}")
        
        return downloaded_files
    
    def _extract_embedded_links(self, pdf_path: Path) -> List[str]:
        """Extract embedded hyperlinks using pdfplumber"""
        urls = []
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract links from page
                    if hasattr(page, 'hyperlinks'):
                        for link in page.hyperlinks:
                            if link and hasattr(link, 'uri'):
                                urls.append(link.uri)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Error extracting embedded links with pdfplumber: {e}")
        return urls
    
    def _extract_pypdf2_links(self, pdf_path: Path) -> List[str]:
        """Extract links from PyPDF2 annotations"""
        urls = []
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    if '/Annots' in page:
                        annotations = page['/Annots']
                        for annotation in annotations:
                            annotation_obj = annotation.get_object()
                            if '/A' in annotation_obj:
                                action = annotation_obj['/A']
                                if '/URI' in action:
                                    uri = action['/URI']
                                    if isinstance(uri, str):
                                        urls.append(uri)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Error extracting links with PyPDF2: {e}")
        return urls
    
    def extract_all_links(self, pdf_path: Path) -> List[str]:
        """
        Extract all hyperlinks from PDF (not just PDFs)
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            List of URLs found
        """
        text = self.pdf_extractor.extract_text(pdf_path)
        if not text:
            return []
        
        return extract_urls_from_text(text)

