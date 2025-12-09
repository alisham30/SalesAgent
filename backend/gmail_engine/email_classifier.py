"""
Email classifier module
Classifies emails as tender-related or not (STRICT MODE)
"""
import re
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
        Extracts ALL emails with RFP or Tender in subject/caption
        
        Args:
            subject: Email subject
            body: Email body text
            sender: Email sender (optional)
            has_pdf: Whether email has PDF attachments
        
        Returns:
            True if email is tender-related
        """
        subject_lower = subject.lower()
        body_lower = body.lower()
        text = f"{subject} {body}".lower()
        
        # PRIMARY CHECK: If subject contains RFP or Tender keywords, accept it
        subject_keywords = [
            'rfp',
            'request for proposal',
            'tender',
            'tender no',
            'tender number',
            'tender id',
            'tender reference',
            'rfq',
            'request for quotation',
            'invitation to tender',
            'bid',
            'bidding',
            'procurement'
        ]
        
        # Check subject line first - if it has RFP or Tender, accept it
        for keyword in subject_keywords:
            if keyword in subject_lower:
                logger.info(f"Email classified as tender (RFP/Tender in subject): {subject[:80]}")
                return True
        
        # EXCLUDE patterns - filter out notification/marketing emails (but only if not in subject)
        exclude_patterns = [
            'new global tenders added',
            'new indian tender',
            'tender results added',
            'verify your email',
            'email verification',
            'account verification',
            'newsletter',
            'update your preferences',
            'unsubscribe',
            'marketing',
            'promotional'
        ]
        
        # Only exclude if pattern is in body AND not in subject (subject takes priority)
        for pattern in exclude_patterns:
            if pattern in body_lower and pattern not in subject_lower:
                logger.debug(f"Email excluded (notification pattern in body): {subject[:50]}")
                return False
        
        # SECONDARY CHECK: Check body for tender keywords if subject doesn't have them
        body_keywords = [
            'rfp',
            'request for proposal',
            'tender',
            'rfq',
            'request for quotation',
            'technical specification',
            'boq',
            'bill of quantities',
            'procurement',
            'bid',
            'bidding'
        ]
        
        body_matches = sum(1 for keyword in body_keywords if keyword in body_lower)
        if body_matches >= 2:
            logger.info(f"Email classified as tender (tender keywords in body): {subject[:60]}")
            return True
        
        # If email has PDF attachment, check for any tender keywords
        if has_pdf:
            pdf_keywords = ['tender', 'bid', 'rfq', 'rfp', 'specification', 'boq', 'procurement']
            pdf_matches = sum(1 for keyword in pdf_keywords if keyword in text)
            if pdf_matches >= 1:
                logger.info(f"Email classified as tender (PDF with tender keywords): {subject[:60]}")
                return True
        
        # Check for tender number pattern in subject (e.g., "TDR-2025-0012", "Tender/2025/001")
        tender_number_patterns = [
            r'tender[:\s]+[A-Z0-9\-/]+',
            r'rfq[:\s]+[A-Z0-9\-/]+',
            r'rfp[:\s]+[A-Z0-9\-/]+',
            r'bid[:\s]+[A-Z0-9\-/]+',
            r'[A-Z]{2,10}[-/]\d{4}[-/]\d{3,6}'  # Pattern like TDR-2025-0012
        ]
        
        for pattern in tender_number_patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                logger.info(f"Email classified as tender (tender number pattern): {subject[:60]}")
                return True
        
        # If no matches, reject
        logger.debug(f"Email NOT classified as tender: {subject[:60]}")
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

