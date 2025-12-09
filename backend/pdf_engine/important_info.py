"""
Important information extractor module
Extracts deadlines, BOQ, warranty, delivery, etc.
"""
import re
from typing import Dict, List, Optional
from datetime import datetime
from backend import config
from backend.utils.logger import logger

class ImportantInfoExtractor:
    """Extracts important tender information"""
    
    def __init__(self):
        self.keywords = config.IMPORTANT_INFO_KEYWORDS
    
    def extract_all(self, text: str) -> Dict:
        """
        Extract all important information from text
        
        Args:
            text: Text to extract from
        
        Returns:
            Dictionary with extracted information
        """
        return {
            'delivery': self.extract_delivery(text),
            'deadline': self.extract_deadline(text),
            'warranty': self.extract_warranty(text),
            'quantities': self.extract_quantities(text),
            'voltage': self.extract_voltage(text),
            'standards': self.extract_standards(text),
            'item_descriptions': self.extract_item_descriptions(text)
        }
    
    def extract_delivery(self, text: str) -> Optional[str]:
        """Extract delivery deadline information"""
        patterns = [
            r'delivery[:\s]+(\d+)\s*(?:days?|weeks?|months?)',
            r'delivery[:\s]+within\s+(\d+)\s*(?:days?|weeks?|months?)',
            r'delivery\s+period[:\s]+(\d+)\s*(?:days?|weeks?|months?)',
            r'lead\s+time[:\s]+(\d+)\s*(?:days?|weeks?|months?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def extract_deadline(self, text: str) -> Optional[str]:
        """Extract submission deadline"""
        patterns = [
            r'(?:submission|closing|last)\s+date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'bid\s+submission[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?:is\s+)?(?:the\s+)?(?:submission|closing|deadline)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def extract_warranty(self, text: str) -> Optional[str]:
        """Extract warranty information"""
        patterns = [
            r'warranty[:\s]+(\d+)\s*(?:years?|months?|days?)',
            r'guarantee[:\s]+(\d+)\s*(?:years?|months?|days?)',
            r'(\d+)\s*(?:years?|months?|days?)\s+warranty',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def extract_quantities(self, text: str) -> List[str]:
        """Extract quantity information"""
        patterns = [
            r'quantity[:\s]+(\d+(?:[.,]\d+)?)\s*(?:meters?|pieces?|units?|nos?\.?)',
            r'qty[:\s]+(\d+(?:[.,]\d+)?)\s*(?:meters?|pieces?|units?|nos?\.?)',
            r'(\d+(?:[.,]\d+)?)\s*(?:meters?|pieces?|units?|nos?\.?)\s+(?:of|quantity)',
        ]
        
        quantities = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            quantities.extend(matches)
        
        return quantities
    
    def extract_voltage(self, text: str) -> Optional[str]:
        """Extract voltage information"""
        patterns = [
            r'(\d+)\s*V\s*(?:grade|rating)',
            r'voltage[:\s]+(\d+)\s*V',
            r'(\d+)\s*V\s+voltage',
            r'voltage\s+grade[:\s]+(\d+)\s*V',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def extract_standards(self, text: str) -> List[str]:
        """Extract standard references (IS, IEC, etc.)"""
        patterns = [
            r'(?:IS|IEC|IEEE|BS|ASTM|ISO)\s+\d+(?:[/-]\d+)*',
            r'as\s+per\s+(?:IS|IEC|IEEE|BS|ASTM|ISO)\s+\d+',
            r'conforms?\s+to\s+(?:IS|IEC|IEEE|BS|ASTM|ISO)\s+\d+',
        ]
        
        standards = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            standards.extend(matches)
        
        return list(set(standards))  # Remove duplicates
    
    def extract_item_descriptions(self, text: str) -> List[str]:
        """Extract item descriptions from BOQ"""
        # Look for lines that contain product descriptions
        lines = text.split('\n')
        descriptions = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains product description indicators
            if any(keyword in line.lower() for keyword in [
                'cable', 'conductor', 'insulation', 'sheath', 'wire',
                'item', 'description', 'material', 'product'
            ]):
                # Check if it's not just a header
                if len(line) > 20 and not line.isupper():
                    descriptions.append(line)
        
        return descriptions

