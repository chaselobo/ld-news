"""
Gmail API integration for sending daily digests
"""

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from typing import Dict, List

class GmailSender:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.service = self._authenticate()
        
        # Email recipients
        self.recipients = os.getenv('GMAIL_RECIPIENTS', '').split(',')
        self.sender_email = os.getenv('GMAIL_SENDER_EMAIL')
        
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
        return build('gmail', 'v1', credentials=creds)
    
    def send_digest(self, digest: Dict) -> bool:
        """Send digest via Gmail"""
        try:
            for recipient in self.recipients:
                if recipient.strip():
                    self._send_email_to_recipient(digest, recipient.strip())
                    
            self.logger.info(f"Successfully sent digest to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Gmail digest: {str(e)}")
            return False
    
    def _send_email_to_recipient(self, digest: Dict, recipient: str):
        """Send email to a single recipient"""
        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = recipient
        message['from'] = self.sender_email
        message['subject'] = f"Leave Delaware Daily Digest - {digest['date']}"
        
        # Create text and HTML parts
        text_part = MIMEText(digest['formatted_text'], 'plain')
        html_part = MIMEText(digest['formatted_html'], 'html')
        
        message.attach(text_part)
        message.attach(html_part)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        self.service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        self.logger.info(f"Email sent to {recipient}")