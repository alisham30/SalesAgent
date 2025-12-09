"""
Specification classifier module
Classifies lines as technical specifications
"""
from typing import List
from backend import config
from backend.utils.logger import logger

class SpecClassifier:
    """Classifies text lines as technical specifications"""
    
    def __init__(self):
        self.keywords = config.TECH_SPEC_KEYWORDS
    
    def is_technical_spec(self, text: str) -> bool:
        """
        Check if text contains technical specifications
        
        Args:
            text: Text to check
        
        Returns:
            True if text appears to be a technical specification
        """
        text_lower = text.lower()
        
        # Check for technical keywords
        keyword_matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
        
        # Check for standard references (IS, IEC, etc.)
        has_standard = any(
            std in text for std in ['IS ', 'IEC ', 'IEEE ', 'BS ', 'ASTM ', 'ISO ']
        )
        
        # Check for technical terms
        has_technical_terms = any(
            term in text_lower for term in [
                'conductor', 'insulation', 'sheath', 'voltage', 'grade',
                'specification', 'compliance', 'conforms', 'as per'
            ]
        )
        
        return keyword_matches >= 1 or (has_standard and has_technical_terms)
    
    def classify_lines(self, lines: List[str]) -> List[str]:
        """
        Filter lines that are technical specifications
        
        Args:
            lines: List of text lines
        
        Returns:
            List of lines identified as technical specifications
        """
        spec_lines = []
        for line in lines:
            if self.is_technical_spec(line):
                spec_lines.append(line)
        
        return spec_lines

