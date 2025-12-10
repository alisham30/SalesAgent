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
        
        # STRICT FILTER: Only fetch emails with "rfp" or "tender" in subject
        # Using Gmail search operators to filter at API level for efficiency
        query = 'subject:(rfp OR tender)'
        logger.info(f"Filtering emails with RFP or Tender in subject: {query}")
        
        # Fetch emails matching the query (with or without attachments)
        filtered_messages = self.gmail_reader.get_messages(query=query, max_results=100)
        
        logger.info(f"Found {len(filtered_messages)} emails matching RFP/Tender criteria")
        
        downloaded_pdfs = []
        for message in filtered_messages:
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
        logger.info(f"Portal PDF directory: {config.PORTAL_PDFS_DIR}")
        
        # Ensure directory exists
        config.PORTAL_PDFS_DIR.mkdir(parents=True, exist_ok=True)
        
        pdf_files = list_pdf_files(config.PORTAL_PDFS_DIR)
        logger.info(f"Found {len(pdf_files)} PDFs in portal directory")
        
        if pdf_files:
            for pdf_file in pdf_files:
                logger.info(f"  - {pdf_file.name}")
        else:
            logger.warning(f"No PDFs found in {config.PORTAL_PDFS_DIR}")
        
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
        
        # Extract tender ID (prioritize PDF filename)
        tender_id = self.tender_id_detector.get_or_generate_tender_id(text, pdf_path)
        
        # Extract technical specifications from main PDF first
        tech_specs = self.tech_spec_extractor.extract_specs(text, use_llm=True)
        main_tech_specs = tech_specs.get('formatted_specs', '')
        
        # Scan for hyperlinks and download linked PDFs
        logger.info(f"Scanning {pdf_path.name} for hyperlinks and specification documents...")
        linked_pdfs = self.hyperlink_scanner.scan_and_download_links(pdf_path)
        if linked_pdfs:
            logger.info(f"✓ Downloaded {len(linked_pdfs)} linked PDF(s) from {pdf_path.name}")
            for linked_pdf in linked_pdfs:
                logger.info(f"  - {linked_pdf.name}")
        else:
            logger.info(f"No linked PDFs found in {pdf_path.name}")
        
        # Process linked PDFs and extract technical specs from them
        linked_tech_specs = []
        linked_texts = []
        
        for linked_pdf in linked_pdfs:
            try:
                linked_text = self.pdf_extractor.extract_text(linked_pdf)
                if linked_text:
                    linked_texts.append(linked_text)
                    text += "\n\n" + linked_text
                    
                    # Extract technical specifications from this linked PDF
                    linked_specs = self.tech_spec_extractor.extract_specs(linked_text, use_llm=True)
                    if linked_specs.get('formatted_specs'):
                        linked_tech_specs.append(linked_specs.get('formatted_specs'))
                        logger.info(f"Found technical specifications in linked PDF: {linked_pdf.name}")
            except Exception as e:
                logger.error(f"Error processing linked PDF {linked_pdf}: {e}")
        
        # Combine technical specifications: prioritize linked PDFs if main PDF has none
        if not main_tech_specs and linked_tech_specs:
            # If main PDF has no tech specs, use specs from linked PDFs
            tech_specs = {
                'formatted_specs': '\n\n'.join(linked_tech_specs),
                'raw_specs': [],
                'count': len(linked_tech_specs)
            }
            logger.info("Using technical specifications from linked PDFs")
        elif main_tech_specs and linked_tech_specs:
            # Combine both main and linked PDF specs
            combined_specs = main_tech_specs
            for linked_spec in linked_tech_specs:
                if linked_spec and linked_spec not in combined_specs:
                    combined_specs += '\n\n' + linked_spec
            tech_specs = {
                'formatted_specs': combined_specs,
                'raw_specs': tech_specs.get('raw_specs', []),
                'count': tech_specs.get('count', 0) + len(linked_tech_specs)
            }
            logger.info("Combined technical specifications from main and linked PDFs")
        # If main_tech_specs exists and no linked specs, use main (already set above)
        
        # Extract important information from combined text
        important_info = self.info_extractor.extract_all(text)
        
        # Try LLM extraction for additional structured info
        llm_info = {}
        if self.llm_agent.api_key:
            try:
                llm_info = self.llm_agent.extract_structured_info(text)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
        
        # Extract only the requested fields: technical_specs, delivery deadline, tender_id, project_name, ministry
        # Get technical specifications (if already present in document)
        tech_specs_str = tech_specs.get('formatted_specs', '')
        if not isinstance(tech_specs_str, str):
            tech_specs_str = str(tech_specs_str) if tech_specs_str else ''
        
        llm_tech_specs = llm_info.get('technical_specs', '')
        if isinstance(llm_tech_specs, list):
            # Convert list to vertical string format
            llm_tech_specs = '\n'.join(str(item) for item in llm_tech_specs if item) if llm_tech_specs else ''
        elif isinstance(llm_tech_specs, dict):
            # Convert dict to key-value string format
            llm_tech_specs = '\n'.join(f"{k}: {v}" for k, v in llm_tech_specs.items() if v) if llm_tech_specs else ''
        elif not isinstance(llm_tech_specs, str):
            llm_tech_specs = str(llm_tech_specs) if llm_tech_specs else ''
        
        technical_specifications = tech_specs_str or llm_tech_specs
        
        # Get delivery deadline
        delivery_deadline = important_info.get('delivery') or important_info.get('deadline') or llm_info.get('delivery', '')
        if not isinstance(delivery_deadline, str):
            delivery_deadline = str(delivery_deadline) if delivery_deadline else ''
        
        # Get project name and ministry (try LLM first, then regex fallback)
        project_name = llm_info.get('project_name', '') or self.info_extractor.extract_project_name(text)
        if not isinstance(project_name, str):
            project_name = str(project_name) if project_name else ''
        
        ministry = llm_info.get('ministry', '') or self.info_extractor.extract_ministry(text)
        if not isinstance(ministry, str):
            ministry = str(ministry) if ministry else ''
        
        # Only include technical_specifications if it's not empty
        result = {
            'tender_id': tender_id,
            'delivery_deadline': delivery_deadline,
            'project_name': project_name,
            'ministry': ministry
        }
        
        # Only add technical_specifications if it exists and is a non-empty string
        if technical_specifications and isinstance(technical_specifications, str) and technical_specifications.strip():
            # Limit to reasonable length and ensure vertical format
            specs_clean = technical_specifications.strip()
            # If too long, truncate (keep first 2000 chars)
            if len(specs_clean) > 2000:
                specs_clean = specs_clean[:2000] + "..."
            result['technical_specifications'] = specs_clean
        
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
        logger.info("=" * 60)
        logger.info("STEP 1: Processing Gmail emails...")
        logger.info("=" * 60)
        gmail_pdfs = self.process_gmail_emails()
        logger.info(f"Downloaded {len(gmail_pdfs)} PDFs from Gmail")
        
        # Process portal PDFs
        logger.info("=" * 60)
        logger.info("STEP 2: Processing portal PDFs...")
        logger.info("=" * 60)
        portal_pdfs = self.process_portal_pdfs()
        logger.info(f"Found {len(portal_pdfs)} PDFs in portal directory")
        
        # Combine all PDFs to process, removing duplicates by absolute path
        all_pdfs_dict = {}
        for pdf in gmail_pdfs + portal_pdfs:
            all_pdfs_dict[str(pdf.resolve())] = pdf
        
        all_pdfs = list(all_pdfs_dict.values())
        
        logger.info("=" * 60)
        logger.info(f"STEP 3: Processing {len(all_pdfs)} unique PDFs...")
        logger.info("=" * 60)
        
        if not all_pdfs:
            logger.warning("No PDFs to process!")
            return
        
        # Process each PDF
        processed_count = 0
        
        for i, pdf_path in enumerate(all_pdfs, 1):
            try:
                # Check if already processed (by checking if output file exists)
                # We'll check this after extracting tender_id to use the correct filename
                logger.info(f"[{i}/{len(all_pdfs)}] Processing: {pdf_path.name}")
                
                tender_data = self.process_pdf(pdf_path)
                
                if tender_data:
                    tender_id = tender_data.get('tender_id', 'UNKNOWN')
                    self.save_tender_output(tender_data)
                    processed_count += 1
                    logger.info(f"✓ Successfully processed: {pdf_path.name} -> {tender_id}")
                else:
                    logger.warning(f"✗ Failed to process: {pdf_path.name}")
                    
            except Exception as e:
                logger.error(f"✗ Error processing PDF {pdf_path.name}: {e}", exc_info=True)
        
        logger.info("=" * 60)
        logger.info(f"Processing Summary:")
        logger.info(f"  - Total PDFs found: {len(all_pdfs)}")
        logger.info(f"  - Successfully processed: {processed_count}")
        logger.info(f"  - Failed: {len(all_pdfs) - processed_count}")
        logger.info("=" * 60)

