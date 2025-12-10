"""
Tender ID detector module
Extracts tender ID from text or generates one if not found
"""
import re
from typing import Optional
from pathlib import Path
from backend import config
from backend.utils.logger import logger

class TenderIDDetector:
    """Detects or generates tender IDs"""
    
    def __init__(self):
        self.prefix = config.TENDER_ID_PREFIX
        self.year = config.TENDER_ID_YEAR
        self.counter_file = config.MODELS_DIR / "tender_counter.txt"
        self._load_counter()
    
    def _load_counter(self):
        """Load counter from file"""
        if self.counter_file.exists():
            try:
                with open(self.counter_file, 'r') as f:
                    self.counter = int(f.read().strip())
            except Exception:
                self.counter = config.TENDER_ID_COUNTER_START
        else:
            self.counter = config.TENDER_ID_COUNTER_START
    
    def _save_counter(self):
        """Save counter to file"""
        self.counter_file.parent.mkdir(exist_ok=True)
        with open(self.counter_file, 'w') as f:
            f.write(str(self.counter))
    
    def extract_tender_id(self, text: str) -> Optional[str]:
        """
        Extract tender ID from text
        Prioritizes RFP/RFQ IDs, then tender numbers, then bid numbers
        
        Args:
            text: Text to search for tender ID
        
        Returns:
            Tender ID if found, None otherwise
        """
        # Priority 1: RFP/RFQ patterns (most specific)
        rfp_patterns = [
            r'rfp[:\s\-]+([A-Z0-9\-/]+)',  # RFP-2025-002, RFP: 2025-002
            r'request\s+for\s+proposal[:\s\-]+([A-Z0-9\-/]+)',
            r'rfq[:\s\-]+([A-Z0-9\-/]+)',
            r'request\s+for\s+quotation[:\s\-]+([A-Z0-9\-/]+)',
            r'([Rr][Ff][Pp][-:]\d{4}[-:]\d{3,6})',  # RFP-2025-002
            r'([Rr][Ff][Qq][-:]\d{4}[-:]\d{3,6})',  # RFQ-2025-002
        ]
        
        for pattern in rfp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                tender_id = matches[0].strip().upper()
                # Clean up common prefixes/suffixes
                tender_id = re.sub(r'^[:\s\-]+|[:\s\-]+$', '', tender_id)
                if len(tender_id) > 3:  # Valid ID should be at least 4 chars
                    logger.info(f"Extracted RFP/RFQ ID: {tender_id}")
                    return tender_id
        
        # Priority 2: Tender number patterns
        tender_patterns = [
            r'tender\s+(?:no|number|id|reference)[:\s\-]+([A-Z0-9\-/]+)',
            r'tender[:\s\-]+([A-Z0-9\-/]{4,20})',  # Tender: ABC-123
            r'([Tt][Ee][Nn][Dd][Ee][Rr][-:]\d{4}[-:]\d{3,6})',  # TENDER-2025-001
        ]
        
        for pattern in tender_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                tender_id = matches[0].strip().upper()
                tender_id = re.sub(r'^[:\s\-]+|[:\s\-]+$', '', tender_id)
                if len(tender_id) > 3:
                    logger.info(f"Extracted Tender ID: {tender_id}")
                    return tender_id
        
        # Priority 3: Bid number patterns
        bid_patterns = [
            r'bid\s+(?:no|number|id)[:\s\-]+([A-Z0-9\-/]+)',
            r'bid[:\s\-]+([A-Z0-9\-/]{4,20})',
            r'([Bb][Ii][Dd][-:]\d{4}[-:]\d{3,6})',  # BID-2025-001
        ]
        
        for pattern in bid_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                tender_id = matches[0].strip().upper()
                tender_id = re.sub(r'^[:\s\-]+|[:\s\-]+$', '', tender_id)
                if len(tender_id) > 3:
                    logger.info(f"Extracted Bid ID: {tender_id}")
                    return tender_id
        
        # Priority 4: GeM Bid numbers (GEM/2025/B/6866936)
        gem_patterns = [
            r'([Gg][Ee][Mm][/\-]\d{4}[/\-][A-Z][/\-]\d{6,10})',  # GEM/2025/B/6866936
            r'bid\s+number[:\s]+([Gg][Ee][Mm][/\-]\d{4}[/\-][A-Z][/\-]\d+)',
        ]
        
        for pattern in gem_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                tender_id = matches[0].strip().upper()
                logger.info(f"Extracted GeM Bid ID: {tender_id}")
                return tender_id
        
        # Priority 5: Generic pattern (like TDR-2025-0012)
        generic_pattern = r'([A-Z]{2,10}[-/]\d{4}[-/]\d{3,6})'
        matches = re.findall(generic_pattern, text, re.IGNORECASE)
        if matches:
            tender_id = matches[0].strip().upper()
            logger.info(f"Extracted generic ID: {tender_id}")
            return tender_id
        
        return None
    
    def generate_tender_id(self) -> str:
        """
        Generate a new tender ID
        
        Returns:
            Generated tender ID
        """
        self.counter += 1
        self._save_counter()
        
        tender_id = f"{self.prefix}-{self.year}-{self.counter:04d}"
        logger.info(f"Generated tender ID: {tender_id}")
        return tender_id
    
    def get_or_generate_tender_id(self, text: str, pdf_path: Optional[Path] = None) -> str:
        """
        Extract tender ID from PDF filename, text, or generate one
        Priority: PDF filename > Text extraction > Generated ID
        
        Args:
            text: Text to search for tender ID
            pdf_path: Optional path to PDF file (to extract ID from filename)
        
        Returns:
            Tender ID (from filename, extracted, or generated)
        """
        # Priority 1: Extract from PDF filename (e.g., "GeM-Bidding-8616346.pdf" -> "GeM-Bidding-8616346")
        if pdf_path:
            filename_stem = pdf_path.stem  # Gets filename without extension
            # Check if filename looks like a tender ID (has numbers, letters, hyphens)
            if re.match(r'^[A-Za-z0-9\-_]+$', filename_stem) and len(filename_stem) > 5:
                # Clean up common prefixes/suffixes
                clean_id = filename_stem.strip()
                # Remove common file prefixes like "temp_", "downloaded_", etc.
                if not clean_id.startswith(('temp_', 'downloaded_', 'attachment_')):
                    logger.info(f"Using tender ID from filename: {clean_id}")
                    return clean_id
        
        # Priority 2: Extract from text
        tender_id = self.extract_tender_id(text)
        if tender_id:
            return tender_id
        
        # Priority 3: Generate new ID
        return self.generate_tender_id()

