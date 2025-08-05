"""
Digest formatter for creating structured output
"""

import logging
from typing import List, Dict
from datetime import datetime

class DigestFormatter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def format_digest(self, entries: List[Dict]) -> Dict:
        """Format entries into a structured digest"""
        if not entries:
            return self._create_empty_digest()
            
        # Sort entries by published date (newest first)
        sorted_entries = sorted(
            entries, 
            key=lambda x: x.get('published_date', ''), 
            reverse=True
        )
        
        # Create formatted digest
        digest = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_entries': len(sorted_entries),
            'formatted_text': self._format_text_digest(sorted_entries),
            'formatted_html': self._format_html_digest(sorted_entries),
            'entries': sorted_entries
        }
        
        return digest
    
    def _format_text_digest(self, entries: List[Dict]) -> str:
        """Format digest as plain text for Slack"""
        header = f"📰 *Leave Delaware Daily Digest - {datetime.now().strftime('%B %d, %Y')}*\n"
        header += f"Found {len(entries)} relevant items today\n\n"
        
        formatted_entries = []
        
        for i, entry in enumerate(entries, 1):
            formatted_entry = f"{i}. *[{entry['tag']}]* {entry['title']}\n"
            formatted_entry += f"   {entry['summary']}\n"
            formatted_entry += f"   🔗 {entry['url']}\n"
            
            formatted_entries.append(formatted_entry)
            
        return header + "\n".join(formatted_entries)
    
    def _format_html_digest(self, entries: List[Dict]) -> str:
        """Format digest as HTML for Gmail"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .entry {{ margin-bottom: 25px; padding: 15px; border-left: 4px solid #007cba; background-color: #f9f9f9; }}
                .tag {{ background-color: #007cba; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
                .title {{ font-weight: bold; margin: 10px 0 5px 0; color: #2c3e50; }}
                .summary {{ margin: 10px 0; }}
                .url {{ margin-top: 10px; }}
                .url a {{ color: #007cba; text-decoration: none; }}
                .url a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📰 Leave Delaware Daily Digest</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                <p><strong>Total Items:</strong> {len(entries)}</p>
            </div>
        """
        
        for i, entry in enumerate(entries, 1):
            html += f"""
            <div class="entry">
                <span class="tag">{entry['tag']}</span>
                <div class="title">{i}. {entry['title']}</div>
                <div class="summary">{entry['summary']}</div>
                <div class="url"><a href="{entry['url']}" target="_blank">Read More →</a></div>
            </div>
            """
            
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _create_empty_digest(self) -> Dict:
        """Create digest when no entries are found"""
        empty_text = f"📰 *Leave Delaware Daily Digest - {datetime.now().strftime('%B %d, %Y')}*\n\nNo relevant news found today."
        empty_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📰 Leave Delaware Daily Digest</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            <p>No relevant news found today.</p>
        </body>
        </html>
        """
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_entries': 0,
            'formatted_text': empty_text,
            'formatted_html': empty_html,
            'entries': []
        }