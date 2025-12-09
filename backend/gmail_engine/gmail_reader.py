"""
Gmail reader module
Connects to Gmail API and fetches emails
"""
import base64
import os
from pathlib import Path
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend import config
from backend.utils.logger import logger

class GmailReader:
    """Gmail API reader for fetching emails"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Check if token exists (try multiple locations)
        token_path = Path(config.BASE_DIR) / config.GMAIL_TOKEN_FILE
        if not token_path.exists():
            token_path = Path(config.BASE_DIR) / "backend" / config.GMAIL_TOKEN_FILE
        
        # Check for credentials file (try multiple locations)
        credentials_path = Path(config.BASE_DIR) / config.GMAIL_CREDENTIALS_FILE
        if not credentials_path.exists():
            credentials_path = Path(config.BASE_DIR) / "backend" / config.GMAIL_CREDENTIALS_FILE
        
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), config.GMAIL_SCOPES)
            except Exception as e:
                logger.warning(f"Error loading token: {e}")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                if not credentials_path.exists():
                    logger.error(f"Credentials file not found: {credentials_path}")
                    logger.error("Please download credentials.json from Google Cloud Console")
                    raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), config.GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run (save in same location as credentials file)
            if credentials_path.parent == Path(config.BASE_DIR) / "backend":
                # If credentials are in backend, save token there too
                token_path = Path(config.BASE_DIR) / "backend" / config.GMAIL_TOKEN_FILE
            token_path.parent.mkdir(exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Successfully authenticated with Gmail API")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise
    
    def get_messages(self, query: str = "", max_results: int = 100) -> List[Dict]:
        """
        Fetch messages from Gmail
        
        Args:
            query: Gmail search query (e.g., "is:unread")
            max_results: Maximum number of results to return
        
        Returns:
            List of message dictionaries
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages")
            
            # Fetch full message details
            full_messages = []
            for msg in messages:
                try:
                    message = self.service.users().messages().get(
                        userId='me', id=msg['id'], format='full'
                    ).execute()
                    full_messages.append(message)
                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
            
            return full_messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching messages: {e}")
            return []
    
    def get_message_body(self, message: Dict) -> str:
        """
        Extract message body text
        
        Args:
            message: Gmail message dictionary
        
        Returns:
            Message body text
        """
        body = ""
        
        payload = message.get('payload', {})
        
        def extract_body(part):
            """Recursively extract body from message parts"""
            nonlocal body
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                    except Exception:
                        pass
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        # Simple HTML to text conversion
                        import re
                        html_body = re.sub(r'<[^>]+>', '', html_body)
                        body += html_body
                    except Exception:
                        pass
            
            # Check for nested parts
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_body(subpart)
        
        extract_body(payload)
        return body
    
    def get_message_subject(self, message: Dict) -> str:
        """
        Extract message subject
        
        Args:
            message: Gmail message dictionary
        
        Returns:
            Message subject
        """
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'subject':
                return header['value']
        return ""
    
    def get_message_sender(self, message: Dict) -> str:
        """
        Extract message sender
        
        Args:
            message: Gmail message dictionary
        
        Returns:
            Message sender email
        """
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'from':
                return header['value']
        return ""
    
    def get_attachments(self, message: Dict) -> List[Dict]:
        """
        Get list of attachments from message
        
        Args:
            message: Gmail message dictionary
        
        Returns:
            List of attachment dictionaries with 'filename' and 'attachment_id'
        """
        attachments = []
        payload = message.get('payload', {})
        
        def extract_attachments(part):
            """Recursively extract attachments from message parts"""
            if part.get('filename'):
                attachment_id = part.get('body', {}).get('attachmentId')
                if attachment_id:
                    attachments.append({
                        'filename': part['filename'],
                        'attachment_id': attachment_id,
                        'mime_type': part.get('mimeType', ''),
                        'size': part.get('body', {}).get('size', 0)
                    })
            
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_attachments(subpart)
        
        extract_attachments(payload)
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """
        Download attachment data
        
        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID
        
        Returns:
            Attachment data as bytes, or None if failed
        """
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id
            ).execute()
            
            data = attachment.get('data')
            if data:
                return base64.urlsafe_b64decode(data)
            return None
            
        except HttpError as e:
            logger.error(f"Error downloading attachment: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading attachment: {e}")
            return None

