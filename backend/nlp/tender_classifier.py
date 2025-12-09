"""
Tender classifier module
NLP classifier for tender emails and PDF content
"""
from typing import List
from backend import config
from backend.utils.logger import logger

class TenderClassifier:
    """Classifies text as tender-related"""
    
    def __init__(self):
        self.keywords = config.TENDER_KEYWORDS
    
    def classify(self, text: str) -> bool:
        """
        Classify if text is tender-related
        
        Args:
            text: Text to classify
        
        Returns:
            True if text is tender-related
        """
        text_lower = text.lower()
        
        # Count keyword matches
        keyword_matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
        
        # Check for strong indicators
        strong_indicators = [
            'tender', 'bid', 'bidding', 'rfq', 'rfp',
            'procurement', 'technical specification', 'boq'
        ]
        strong_matches = sum(1 for indicator in strong_indicators if indicator in text_lower)
        
        # Classification logic
        if strong_matches >= 2:
            return True
        if keyword_matches >= 3:
            return True
        if strong_matches >= 1 and keyword_matches >= 2:
            return True
        
        return False
    
    def classify_batch(self, texts: List[str]) -> List[bool]:
        """
        Classify multiple texts
        
        Args:
            texts: List of texts to classify
        
        Returns:
            List of classification results
        """
        return [self.classify(text) for text in texts]

