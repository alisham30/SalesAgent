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
        STRICT: ONLY downloads PDFs that are mentioned under "Technical Specification" sections
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            List of paths to downloaded PDF files
        """
        logger.info(f"Scanning for hyperlinks in: {pdf_path.name}")
        
        # Extract text first to identify tech spec sections
        text = self.pdf_extractor.extract_text(pdf_path)
        if not text:
            logger.warning(f"Could not extract text from {pdf_path.name}")
            return []
        
        # STRICT: Only extract URLs from Technical Specification sections
        tech_spec_urls = self._extract_urls_from_tech_spec_section(text)
        logger.info(f"Found {len(tech_spec_urls)} URLs in Technical Specification/ATC sections")
        
        # Also check embedded links, but only if they're in tech spec context
        # First get ALL embedded links to see what we have
        all_embedded = self._extract_embedded_links(pdf_path)
        logger.info(f"Found {len(all_embedded)} total embedded links in PDF")
        if all_embedded:
            logger.debug(f"Sample embedded links: {[url[:60] for url in all_embedded[:3]]}")
        
        embedded_urls = self._extract_embedded_links_in_tech_spec_context(pdf_path, text)
        tech_spec_urls.extend(embedded_urls)
        logger.info(f"Found {len(embedded_urls)} embedded links in tech spec context")
        
        if not tech_spec_urls:
            logger.warning("No URLs found in Technical Specification/ATC sections - no linked PDFs to download")
            # Log a sample of the text to help debug
            if text:
                # Check if ATC section exists
                if 'additional terms' in text.lower() or 'atc' in text.lower():
                    logger.info("ATC section detected in PDF but no URLs found")
                # Log sample
                sample = text[:500].replace('\n', ' ')
                logger.debug(f"Sample text from PDF: {sample}...")
            return []
        
        # Remove duplicates
        unique_urls = list(set(tech_spec_urls))
        logger.info(f"Total unique URLs from tech spec sections: {len(unique_urls)}")
        
        # Filter for PDF URLs or specification document links ONLY
        pdf_urls = []
        exclude_keywords = [
            'categories', 'trials', 'allowed', 'list-of', 'list_of',
            'general terms', 'terms and conditions', 'terms-and-conditions',
            'disclaimer', 'conclusion', 'introduction', 'definitions'
        ]
        
        for url in unique_urls:
            # Skip irrelevant PDFs
            url_lower = url.lower()
            if any(exclude in url_lower for exclude in exclude_keywords):
                logger.info(f"⊘ Skipping irrelevant URL (not tech spec): {url[:80]}")
                continue
            
            # Must be a PDF or have spec-related keywords
            is_pdf = is_pdf_url(url)
            has_spec_keyword = any(keyword in url_lower for keyword in ['specification', 'spec', 'technical', 'tech', 'boq', 'specification document'])
            is_view_file = 'viewfile' in url_lower or 'view_file' in url_lower or 'view file' in url_lower
            
            if is_pdf and (has_spec_keyword or is_view_file):
                pdf_urls.append(url)
                logger.info(f"✓ Found tech spec PDF URL: {url[:80]}")
            elif has_spec_keyword or is_view_file:
                # Even if not .pdf extension, if it has spec keywords, try it
                pdf_urls.append(url)
                logger.info(f"✓ Found tech spec document URL: {url[:80]}")
        
        logger.info(f"Found {len(pdf_urls)} relevant PDF/specification URLs to download")
        
        # Download PDFs
        downloaded_files = []
        exclude_filename_keywords = [
            'categories', 'trials', 'allowed', 'list-of', 'list_of',
            'general terms', 'terms-and-conditions', 'disclaimer',
            'conclusion', 'introduction', 'definitions'
        ]
        
        for url in pdf_urls:
            try:
                downloaded_file = download_pdf_from_url(url, config.LINKED_PDFS_DIR)
                if downloaded_file:
                    # Double-check filename - filter out irrelevant PDFs
                    filename_lower = downloaded_file.name.lower()
                    if any(exclude in filename_lower for exclude in exclude_filename_keywords):
                        logger.info(f"⊘ Deleted irrelevant PDF: {downloaded_file.name}")
                        downloaded_file.unlink()  # Delete the file
                        continue
                    
                    downloaded_files.append(downloaded_file)
                    logger.info(f"✓ Downloaded tech spec PDF: {downloaded_file.name}")
            except Exception as e:
                logger.error(f"✗ Error downloading PDF from {url}: {e}")
        
        return downloaded_files
    
    def _extract_embedded_links_in_tech_spec_context(self, pdf_path: Path, text: str) -> List[str]:
        """
        Extract embedded links that are in tech spec sections ONLY
        Uses text context to determine if embedded link is actually in tech spec area
        
        Args:
            pdf_path: Path to PDF
            text: Extracted text for context
        
        Returns:
            List of URLs in tech spec context
        """
        # First get all embedded links
        all_embedded = self._extract_embedded_links(pdf_path)
        if not all_embedded:
            return []
        
        # Extract tech spec section text only
        tech_spec_section_text = self._extract_tech_spec_section_text_only(text)
        if not tech_spec_section_text:
            logger.debug("No tech spec section found - skipping embedded links")
            return []
        
        # Only include embedded links if:
        # 1. URL contains spec keywords, OR
        # 2. URL is mentioned in the tech spec section text
        tech_spec_urls = []
        tech_spec_text_lower = tech_spec_section_text.lower()
        
        for url in all_embedded:
            url_lower = url.lower()
            
            # Check if URL filename suggests it's a spec document
            has_spec_keyword = any(keyword in url_lower for keyword in ['specification', 'spec', 'technical', 'tech', 'boq', 'specification document'])
            
            # Check if URL appears in tech spec section text
            url_in_section = url in tech_spec_section_text or any(part in tech_spec_text_lower for part in url_lower.split('/')[-1].split('.'))
            
            # Only include if it's clearly a spec document
            if has_spec_keyword or url_in_section:
                tech_spec_urls.append(url)
                logger.debug(f"Found embedded link in tech spec context: {url[:80]}")
            else:
                logger.debug(f"Skipping embedded link (not in tech spec): {url[:80]}")
        
        return tech_spec_urls
    
    def _extract_tech_spec_section_text_only(self, text: str) -> str:
        """Extract only the text from Technical Specification sections"""
        import re
        
        lines = text.split('\n')
        tech_spec_patterns = [
            r'technical\s+specification[s]?[:\s]*',
            r'tech\s+spec[s]?[:\s]*',
            r'specification[s]?[:\s]*',
        ]
        
        in_tech_spec_section = False
        tech_spec_text = ""
        section_end_keywords = [
            'terms and conditions', 'general terms', 'payment terms', 'delivery',
            'warranty', 'evaluation', 'commercial', 'bid', 'submission', 'annexure',
            'appendix', 'schedule', 'boq', 'bill of quantities', 'categories where',
            'general terms and conditions', 'conclusion', 'disclaimer'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a tech spec header
            is_tech_spec_header = any(
                re.search(pattern, line_lower, re.IGNORECASE) 
                for pattern in tech_spec_patterns
            )
            
            if is_tech_spec_header:
                in_tech_spec_section = True
                tech_spec_text = line + "\n"
                continue
            
            # If we're in a tech spec section, collect text
            if in_tech_spec_section:
                # Check if we've reached the end of the section
                if any(keyword in line_lower for keyword in section_end_keywords):
                    # Check if this is just a sub-section
                    if not any(ts_keyword in line_lower for ts_keyword in ['specification', 'spec', 'technical']):
                        # We've left the tech spec section
                        break
                
                tech_spec_text += line + "\n"
                
                # Limit section size (max 200 lines after header)
                if len(tech_spec_text.split('\n')) > 200:
                    break
        
        return tech_spec_text
    
    def _find_tech_spec_sections(self, text: str) -> List[str]:
        """Find all technical specification section headers in text"""
        import re
        sections = []
        lines = text.split('\n')
        
        tech_spec_patterns = [
            r'technical\s+specification[s]?',
            r'tech\s+spec[s]?',
            r'specification[s]?[:\s]*$',
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(re.search(pattern, line_lower, re.IGNORECASE) for pattern in tech_spec_patterns):
                sections.append(line.strip())
        
        return sections
    
    def _extract_urls_from_tech_spec_section(self, text: str) -> List[str]:
        """
        Extract URLs that appear in or near "Technical Specification" sections
        Also checks ATC (Additional Terms & Conditions) sections for spec document links
        
        Args:
            text: Full PDF text
        
        Returns:
            List of URLs found in tech spec sections
        """
        import re
        from backend.utils.url_resolver import extract_urls_from_text
        
        # Patterns to identify technical specification sections
        tech_spec_patterns = [
            r'technical\s+specification[s]?[:\s]*',
            r'tech\s+spec[s]?[:\s]*',
            r'specification[s]?[:\s]*',
            r'technical\s+requirement[s]?[:\s]*',
            r'product\s+specification[s]?[:\s]*',
            r'item\s+specification[s]?[:\s]*',
            r'additional\s+terms\s+&?\s+conditions',  # ATC sections often have spec links
            r'atc\s*[:\s]*',  # ATC abbreviation
        ]
        
        # Split text into lines for context
        lines = text.split('\n')
        urls = []
        
        # Look for tech spec section headers
        in_tech_spec_section = False
        tech_spec_section_text = ""
        section_end_keywords = [
            'general terms and conditions', 'general terms', 'payment terms', 
            'delivery', 'warranty', 'evaluation', 'commercial', 'bid', 'submission', 
            'annexure', 'appendix', 'schedule', 'boq', 'bill of quantities',
            'emd detail', 'epbg detail', 'categories where'  # End markers
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is a tech spec header
            is_tech_spec_header = any(
                re.search(pattern, line_lower, re.IGNORECASE) 
                for pattern in tech_spec_patterns
            )
            
            if is_tech_spec_header:
                in_tech_spec_section = True
                tech_spec_section_text = line + "\n"
                logger.info(f"Found tech spec/ATC section: {line[:80]}")
                continue
            
            # If we're in a tech spec section, collect text
            if in_tech_spec_section:
                # Check if we've reached the end of the section
                if any(keyword in line_lower for keyword in section_end_keywords):
                    # Check if this is just a sub-section (like "Technical Specifications - Delivery")
                    if not any(ts_keyword in line_lower for ts_keyword in ['specification', 'spec', 'technical', 'atc', 'additional terms']):
                        # We've left the tech spec section
                        logger.debug(f"Ending tech spec section at: {line[:80]}")
                        break
                
                tech_spec_section_text += line + "\n"
                
                # Limit section size to avoid going too far (max 200 lines after header)
                if i > 0 and len(tech_spec_section_text.split('\n')) > 200:
                    logger.debug("Reached max section size limit")
                    break
        
        # Extract URLs from the tech spec section only
        if tech_spec_section_text:
            section_urls = extract_urls_from_text(tech_spec_section_text)
            urls.extend(section_urls)
            logger.info(f"Extracted {len(section_urls)} URLs from Technical Specification/ATC section")
            
            # Also look for "View File" or similar text patterns that might indicate links
            view_file_patterns = [
                r'view\s+file[:\s]*([^\s]+)',
                r'viewfile[:\s]*([^\s]+)',
                r'download[:\s]*([^\s]+)',
                r'click\s+here[:\s]*([^\s]+)',
                r'specification\s+document[:\s]*([^\s]+)',
            ]
            
            for pattern in view_file_patterns:
                matches = re.finditer(pattern, tech_spec_section_text, re.IGNORECASE)
                for match in matches:
                    potential_url = match.group(1).strip('.,;:()[]{}"\'')
                    if potential_url.startswith('http') or is_pdf_url(potential_url):
                        urls.append(potential_url)
                        logger.debug(f"Found 'View File' link: {potential_url[:80]}")
        
        return list(set(urls))  # Remove duplicates
    
    def _extract_embedded_links(self, pdf_path: Path) -> List[str]:
        """Extract embedded hyperlinks using pdfplumber and PyPDF2"""
        urls = []
        
        # Method 1: Try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract links from page hyperlinks
                        if hasattr(page, 'hyperlinks') and page.hyperlinks:
                            for link in page.hyperlinks:
                                if link:
                                    # pdfplumber hyperlinks can be dict or object
                                    if isinstance(link, dict):
                                        uri = link.get('uri') or link.get('url')
                                    elif hasattr(link, 'uri'):
                                        uri = link.uri
                                    elif hasattr(link, 'url'):
                                        uri = link.url
                                    else:
                                        continue
                                    
                                    if uri and isinstance(uri, str) and uri.startswith('http'):
                                        urls.append(uri)
                                        logger.info(f"Found pdfplumber link on page {page_num+1}: {uri[:80]}")
                        
                        # Also try to get links from page text/annotations
                        try:
                            if hasattr(page, 'annots') and page.annots:
                                for annot in page.annots:
                                    if isinstance(annot, dict):
                                        uri = annot.get('uri') or annot.get('url')
                                        if uri and isinstance(uri, str) and uri.startswith('http'):
                                            urls.append(uri)
                                            logger.info(f"Found pdfplumber annotation link on page {page_num+1}: {uri[:80]}")
                        except:
                            pass
                    except Exception as e:
                        logger.debug(f"Error extracting links from page {page_num+1} with pdfplumber: {e}")
                        continue
        except ImportError:
            logger.warning("pdfplumber not available for embedded link extraction")
        except Exception as e:
            logger.warning(f"Error extracting embedded links with pdfplumber: {e}")
        
        # Method 2: Try PyPDF2 for annotations
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        if '/Annots' in page:
                            annotations = page['/Annots']
                            for annotation in annotations:
                                annotation_obj = annotation.get_object()
                                if '/A' in annotation_obj:
                                    action = annotation_obj['/A']
                                    if '/URI' in action:
                                        uri = action['/URI']
                                        if isinstance(uri, str) and uri.startswith('http'):
                                            urls.append(uri)
                                            logger.debug(f"Found PyPDF2 link on page {page_num+1}: {uri[:80]}")
                    except Exception as e:
                        logger.debug(f"Error extracting links from page {page_num+1} with PyPDF2: {e}")
                        continue
        except ImportError:
            logger.debug("PyPDF2 not available for embedded link extraction")
        except Exception as e:
            logger.debug(f"Error extracting embedded links with PyPDF2: {e}")
        
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

