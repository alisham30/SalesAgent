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
        
        Args:
            text: Text to search for tender ID
        
        Returns:
            Tender ID if found, None otherwise
        """
        # Common tender ID patterns
        patterns = [
            r'tender\s+(?:no|number|id)[:\s]+([A-Z0-9\-/]+)',
            r'tender[:\s]+([A-Z0-9\-/]+)',
            r'bid\s+(?:no|number|id)[:\s]+([A-Z0-9\-/]+)',
            r'rfq[:\s]+([A-Z0-9\-/]+)',
            r'rfp[:\s]+([A-Z0-9\-/]+)',
            r'tender\s+reference[:\s]+([A-Z0-9\-/]+)',
            r'([A-Z]{2,10}[-/]\d{4}[-/]\d{3,6})',  # Pattern like TDR-2025-0012
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                tender_id = matches[0].strip().upper()
                logger.info(f"Extracted tender ID: {tender_id}")
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
    
    def get_or_generate_tender_id(self, text: str) -> str:
        """
        Extract tender ID from text or generate one
        
        Args:
            text: Text to search for tender ID
        
        Returns:
            Tender ID (extracted or generated)
        """
        tender_id = self.extract_tender_id(text)
        if tender_id:
            return tender_id
        return self.generate_tender_id()

