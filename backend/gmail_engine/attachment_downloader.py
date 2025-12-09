"""
Attachment downloader module
Downloads PDF attachments from Gmail messages
"""
from pathlib import Path
from typing import List, Optional
from backend import config
from backend.utils.logger import logger
from backend.utils.file_ops import save_pdf
from backend.gmail_engine.gmail_reader import GmailReader

class AttachmentDownloader:
    """Downloads PDF attachments from Gmail"""
    
    def __init__(self, gmail_reader: GmailReader):
        self.gmail_reader = gmail_reader
    
    def download_pdf_attachments(self, message: dict) -> List[Path]:
        """
        Download all PDF attachments from a Gmail message
        
        Args:
            message: Gmail message dictionary
        
        Returns:
            List of paths to downloaded PDF files
        """
        attachments = self.gmail_reader.get_attachments(message)
        pdf_attachments = [
            att for att in attachments 
            if att['mime_type'] == 'application/pdf' or att['filename'].lower().endswith('.pdf')
        ]
        
        if not pdf_attachments:
            logger.info("No PDF attachments found in message")
            return []
        
        downloaded_files = []
        message_id = message['id']
        
        for attachment in pdf_attachments:
            try:
                logger.info(f"Downloading attachment: {attachment['filename']}")
                attachment_data = self.gmail_reader.download_attachment(
                    message_id, attachment['attachment_id']
                )
                
                if attachment_data:
                    # Save to temporary location first
                    temp_file = config.MAIL_PDFS_DIR / f"temp_{attachment['filename']}"
                    temp_file.write_bytes(attachment_data)
                    
                    # Save using file_ops to handle duplicates
                    saved_file = save_pdf(temp_file, config.MAIL_PDFS_DIR, attachment['filename'])
                    temp_file.unlink()  # Remove temp file
                    
                    downloaded_files.append(saved_file)
                    logger.info(f"Successfully downloaded: {saved_file}")
                else:
                    logger.warning(f"Failed to download attachment: {attachment['filename']}")
                    
            except Exception as e:
                logger.error(f"Error downloading attachment {attachment['filename']}: {e}")
        
        return downloaded_files

