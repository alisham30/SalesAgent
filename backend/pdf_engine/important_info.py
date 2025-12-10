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
    
    def extract_project_name(self, text: str) -> Optional[str]:
        """Extract project name from tender document"""
        patterns = [
            r'project[:\s]+(?:name|title)[:\s]+([^\n]{10,100})',
            r'project[:\s]+([A-Z][^\n]{20,150})',
            r'tender[:\s]+(?:for|of)[:\s]+([^\n]{10,100})',
            r'name[:\s]+of[:\s]+(?:the\s+)?project[:\s]+([^\n]{10,100})',
            r'title[:\s]+([^\n]{20,150})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                project_name = match.group(1).strip()
                # Clean up common suffixes
                project_name = re.sub(r'[:\-]+$', '', project_name).strip()
                if len(project_name) > 10:
                    return project_name
        
        # Try to find it in the first few lines (often project name is at the top)
        lines = text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                # Check if it looks like a project name (not all caps, has some structure)
                if not line.isupper() and not re.match(r'^\d+', line):
                    # Check for common project name indicators
                    if any(keyword in line.lower() for keyword in ['project', 'supply', 'procurement', 'tender']):
                        return line
        
        return None
    
    def extract_ministry(self, text: str) -> Optional[str]:
        """Extract ministry/department name from tender document"""
        patterns = [
            r'ministry[:\s]+of[:\s]+([A-Z][^\n]{5,80})',
            r'department[:\s]+of[:\s]+([A-Z][^\n]{5,80})',
            r'([A-Z][A-Z\s&]{5,50})\s+ministry',
            r'([A-Z][A-Z\s&]{5,50})\s+department',
            r'issuing[:\s]+(?:authority|organization)[:\s]+([^\n]{5,80})',
            r'procuring[:\s]+(?:entity|authority)[:\s]+([^\n]{5,80})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ministry = match.group(1).strip()
                # Clean up
                ministry = re.sub(r'[:\-]+$', '', ministry).strip()
                if len(ministry) > 3:
                    return ministry
        
        # Common Indian ministries/departments
        common_ministries = [
            'Ministry of Power', 'Ministry of Railways', 'Ministry of Defence',
            'Ministry of Electronics', 'Ministry of Communications',
            'Department of Telecommunications', 'Department of Power',
            'Central Public Works Department', 'CPWD'
        ]
        
        for ministry in common_ministries:
            if ministry.lower() in text.lower():
                return ministry
        
        return None

