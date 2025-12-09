"""
Paragraph parser module
Splits text into paragraphs and items
"""
from typing import List
from backend.utils.text_cleaner import split_into_paragraphs, extract_sentences

class ParagraphParser:
    """Parses text into structured paragraphs and items"""
    
    def parse_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs
        
        Args:
            text: Text to parse
        
        Returns:
            List of paragraphs
        """
        return split_into_paragraphs(text)
    
    def parse_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Text to parse
        
        Returns:
            List of sentences
        """
        return extract_sentences(text)
    
    def parse_bullet_points(self, text: str) -> List[str]:
        """
        Extract bullet points from text
        
        Args:
            text: Text to parse
        
        Returns:
            List of bullet point items
        """
        import re
        # Match common bullet point patterns
        bullet_patterns = [
            r'^[\u2022\u2023\u25E6\u2043\u2219\*\-\+]\s+(.+)$',  # Unicode bullets and common symbols
            r'^\d+[\.\)]\s+(.+)$',  # Numbered lists
            r'^[a-z][\.\)]\s+(.+)$',  # Lettered lists
        ]
        
        lines = text.split('\n')
        bullet_points = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in bullet_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    bullet_points.append(match.group(1).strip())
                    break
        
        return bullet_points

