"""
Main orchestrator module
Orchestrates the entire tender processing pipeline
"""
from pathlib import Path
from typing import Dict, List
from backend import config
from backend.utils.logger import logger
from backend.utils.file_ops import list_pdf_files, save_text_file, save_json_file
from backend.gmail_engine.gmail_reader import GmailReader
from backend.gmail_engine.email_classifier import EmailClassifier
from backend.gmail_engine.attachment_downloader import AttachmentDownloader
from backend.pdf_engine.pdf_extractor import PDFExtractor
from backend.pdf_engine.hyperlink_scanner import HyperlinkScanner
from backend.pdf_engine.important_info import ImportantInfoExtractor
from backend.pdf_engine.tender_id_detector import TenderIDDetector
from backend.nlp.tech_spec_extractor import TechSpecExtractor
from backend.nlp.llm_agent import LLMAgent

class TenderAgent:
    """Main tender processing agent"""
    
    def __init__(self):
        self.gmail_reader = None
        self.email_classifier = EmailClassifier()
        self.pdf_extractor = PDFExtractor()
        self.hyperlink_scanner = HyperlinkScanner()
        self.info_extractor = ImportantInfoExtractor()
        self.tender_id_detector = TenderIDDetector()
        self.tech_spec_extractor = TechSpecExtractor()
        self.llm_agent = LLMAgent()
        self.processed_tenders = {}  # Track processed tenders by ID
    
    def initialize_gmail(self):
        """Initialize Gmail reader"""
        try:
            self.gmail_reader = GmailReader()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gmail: {e}")
            return False
    
    def process_gmail_emails(self) -> List[Path]:
        """
        Process Gmail emails and download PDF attachments
        
        Returns:
            List of downloaded PDF file paths
        """
        if not self.gmail_reader:
            if not self.initialize_gmail():
                logger.warning("Gmail not available, skipping email processing")
                return []
        
        logger.info("Processing Gmail emails...")
        attachment_downloader = AttachmentDownloader(self.gmail_reader)
        
        # Fetch recent emails (increased limit and search for emails with attachments)
        # Search for emails with attachments first, then all emails
        messages_with_attachments = self.gmail_reader.get_messages(query="has:attachment", max_results=100)
        all_messages = self.gmail_reader.get_messages(query="", max_results=100)
        
        # Combine and deduplicate
        message_ids = set()
        all_unique_messages = []
        for msg in messages_with_attachments + all_messages:
            if msg.get('id') not in message_ids:
                message_ids.add(msg.get('id'))
                all_unique_messages.append(msg)
        
        logger.info(f"Processing {len(all_unique_messages)} unique messages")
        
        downloaded_pdfs = []
        for message in all_unique_messages:
            try:
                subject = self.gmail_reader.get_message_subject(message)
                body = self.gmail_reader.get_message_body(message)
                sender = self.gmail_reader.get_message_sender(message)
                
                # Check if email has PDF attachments
                attachments = self.gmail_reader.get_attachments(message)
                has_pdf = any(
                    att['mime_type'] == 'application/pdf' or 
                    att['filename'].lower().endswith('.pdf') 
                    for att in attachments
                )
                
                if attachments:
                    logger.debug(f"Email has {len(attachments)} attachment(s): {subject[:60]}")
                    for att in attachments:
                        logger.debug(f"  - {att.get('filename', 'unknown')} ({att.get('mime_type', 'unknown')})")
                
                # Classify email (STRICT MODE - only actual tender documents)
                if self.email_classifier.is_tender_email(subject, body, sender, has_pdf=has_pdf):
                    logger.info(f"✓ Processing tender email: {subject[:80]}")
                    if has_pdf:
                        logger.info(f"  → Found PDF attachment(s), downloading...")
                    
                    # Download PDF attachments
                    pdfs = attachment_downloader.download_pdf_attachments(message)
                    if pdfs:
                        logger.info(f"  → Successfully downloaded {len(pdfs)} PDF(s)")
                    downloaded_pdfs.extend(pdfs)
                else:
                    logger.debug(f"✗ Skipping non-tender email: {subject[:60]}")
                    
            except Exception as e:
                logger.error(f"Error processing email: {e}")
        
        logger.info(f"Downloaded {len(downloaded_pdfs)} PDFs from Gmail")
        return downloaded_pdfs
    
    def process_portal_pdfs(self) -> List[Path]:
        """
        Process PDFs from portal_pdfs directory
        
        Returns:
            List of PDF file paths
        """
        logger.info("Processing portal PDFs...")
        pdf_files = list_pdf_files(config.PORTAL_PDFS_DIR)
        logger.info(f"Found {len(pdf_files)} PDFs in portal directory")
        return pdf_files
    
    def process_pdf(self, pdf_path: Path) -> Dict:
        """
        Process a single PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with extracted information
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text
        text = self.pdf_extractor.extract_text(pdf_path)
        
        if not text:
            logger.warning(f"Could not extract text from {pdf_path}")
            return {}
        
        # Save raw text
        raw_text_file = save_text_file(
            text,
            config.RAW_TEXT_DIR,
            f"{pdf_path.stem}_raw.txt"
        )
        
        # Extract tender ID
        tender_id = self.tender_id_detector.get_or_generate_tender_id(text)
        
        # Scan for hyperlinks and download linked PDFs
        linked_pdfs = self.hyperlink_scanner.scan_and_download_links(pdf_path)
        logger.info(f"Downloaded {len(linked_pdfs)} linked PDFs")
        
        # Process linked PDFs and merge their text
        for linked_pdf in linked_pdfs:
            try:
                linked_text = self.pdf_extractor.extract_text(linked_pdf)
                if linked_text:
                    text += "\n\n" + linked_text
            except Exception as e:
                logger.error(f"Error processing linked PDF {linked_pdf}: {e}")
        
        # Extract important information
        important_info = self.info_extractor.extract_all(text)
        
        # Extract technical specifications
        tech_specs = self.tech_spec_extractor.extract_specs(text, use_llm=True)
        
        # Try LLM extraction for additional structured info
        llm_info = {}
        if self.llm_agent.api_key:
            try:
                llm_info = self.llm_agent.extract_structured_info(text)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
        
        # Combine all information
        result = {
            'tender_id': tender_id,
            'source_pdf': str(pdf_path),
            'linked_pdfs': [str(p) for p in linked_pdfs],
            'technical_specifications': tech_specs.get('formatted_specs', ''),
            'raw_technical_specs': tech_specs.get('raw_specs', []),
            'delivery': important_info.get('delivery') or llm_info.get('delivery'),
            'deadline': important_info.get('deadline') or llm_info.get('submission_date'),
            'warranty': important_info.get('warranty') or llm_info.get('warranty'),
            'quantities': important_info.get('quantities') or llm_info.get('quantities', []),
            'voltage': important_info.get('voltage') or llm_info.get('voltage'),
            'standards': important_info.get('standards') or llm_info.get('standards', []),
            'item_descriptions': important_info.get('item_descriptions') or llm_info.get('items', []),
            'raw_text_file': str(raw_text_file)
        }
        
        return result
    
    def save_tender_output(self, tender_data: Dict):
        """
        Save tender output as JSON
        
        Args:
            tender_data: Dictionary with tender information
        """
        tender_id = tender_data.get('tender_id', 'UNKNOWN')
        filename = f"{tender_id}.json"
        
        save_json_file(tender_data, config.EXTRACTED_DIR, filename)
        logger.info(f"Saved tender output: {filename}")
    
    def run(self):
        """Run the complete tender processing pipeline"""
        logger.info("Starting tender agent...")
        
        # Process Gmail emails
        gmail_pdfs = self.process_gmail_emails()
        
        # Process portal PDFs
        portal_pdfs = self.process_portal_pdfs()
        
        # Combine all PDFs to process
        all_pdfs = list(set(gmail_pdfs + portal_pdfs))
        
        logger.info(f"Total PDFs to process: {len(all_pdfs)}")
        
        # Process each PDF
        for pdf_path in all_pdfs:
            try:
                tender_data = self.process_pdf(pdf_path)
                
                if tender_data:
                    self.save_tender_output(tender_data)
                    logger.info(f"Successfully processed: {pdf_path}")
                else:
                    logger.warning(f"Failed to process: {pdf_path}")
                    
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path}: {e}")
        
        logger.info("Tender agent processing complete")

