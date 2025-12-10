"""
Email classifier module
Classifies emails as tender-related or not (STRICT MODE)
"""
from typing import Dict
from backend import config
from backend.utils.logger import logger
from backend.nlp.tender_classifier import TenderClassifier

class EmailClassifier:
    """Classifier for tender-related emails"""
    
    def __init__(self):
        self.tender_classifier = TenderClassifier()
        self.keywords = config.TENDER_KEYWORDS
    
    def is_tender_email(self, subject: str, body: str, sender: str = "", has_pdf: bool = False) -> bool:
        """
        Classify if email is tender-related
        STRICT MODE: Only accepts emails with "rfp" or "tender" in subject/caption
        
        Args:
            subject: Email subject
            body: Email body text
            sender: Email sender (optional)
            has_pdf: Whether email has PDF attachments
        
        Returns:
            True if email is tender-related
        """
        subject_lower = subject.lower()
        
        # STRICT CHECK: Only accept if subject contains "rfp" or "tender"
        # This is the primary and only check - no body checks, no other keywords
        strict_keywords = ['rfp', 'tender']
        
        for keyword in strict_keywords:
            if keyword in subject_lower:
                logger.info(f"✓ Email accepted (RFP/Tender in subject): {subject[:80]}")
                return True
        
        # If subject doesn't have rfp or tender, reject it
        logger.debug(f"✗ Email rejected (no RFP/Tender in subject): {subject[:60]}")
        return False
    
    def classify_message(self, message_data: Dict) -> bool:
        """
        Classify a Gmail message
        
        Args:
            message_data: Message dictionary with subject, body, etc.
        
        Returns:
            True if message is tender-related
        """
        subject = message_data.get('subject', '')
        body = message_data.get('body', '')
        sender = message_data.get('sender', '')
        
        return self.is_tender_email(subject, body, sender)

