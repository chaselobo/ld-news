"""
Slack integration for sending daily digests
"""

import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Dict, List
from datetime import datetime

class SlackSender:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        self.channel = os.getenv('SLACK_CHANNEL', '#LD-News')
        
    def send_digest(self, digest: Dict) -> bool:
        """Send digest to Slack channel using Block Kit format in a single message"""
        try:
            if digest['total_entries'] == 0:
                blocks = self._create_empty_digest_blocks(digest)
            else:
                blocks = self._create_full_digest_blocks(digest)
            
            # Send everything in one message
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                text=f"📰 Leave Delaware Daily Digest - {digest.get('total_entries', 0)} items"
            )
                
            self.logger.info(f"Successfully sent digest to Slack channel {self.channel}")
            return True
            
        except SlackApiError as e:
            self.logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {str(e)}")
            return False
    
    def _create_empty_digest_blocks(self, digest: Dict) -> List[Dict]:
        """Create blocks for empty digest notification"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📰 Leave Delaware Daily Digest"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Date:* {datetime.now().strftime('%B %d, %Y')}\n*Status:* No relevant news found today"
                }
            },
            {
                "type": "divider"
            }
        ]
    
    def _create_full_digest_blocks(self, digest: Dict) -> List[Dict]:
        """Create all blocks for the complete digest in one message"""
        blocks = []
        
        # Header blocks
        blocks.extend([
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📰 Leave Delaware Daily Digest"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Date:* {datetime.now().strftime('%B %d, %Y')}\n*Total Items:* {digest['total_entries']} relevant news items found"
                }
            },
            {
                "type": "divider"
            }
        ])
        
        # Add all entries
        entries = digest['entries']
        for i, entry in enumerate(entries, 1):
            # Get emoji based on tag
            emoji = self._get_tag_emoji(entry['tag'])
            
            # Main entry block
            entry_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {entry['title']}*\n\n{entry['summary']}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Read More"
                    },
                    "url": entry['url'],
                    "action_id": f"read_more_{i}"
                }
            }
            
            # Context block with source info
            context_elements = [
                {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{entry['tag']}*"
                }
            ]
            
            # Add source and author if available
            if entry.get('source'):
                context_elements.append({
                    "type": "mrkdwn",
                    "text": f"• Source: {entry['source']}"
                })
            
            if entry.get('author'):
                context_elements.append({
                    "type": "mrkdwn",
                    "text": f"• Author: {entry['author']}"
                })
            
            context_block = {
                "type": "context",
                "elements": context_elements
            }
            
            blocks.extend([entry_block, context_block])
            
            # Add divider between entries (except for the last one)
            if i < len(entries):
                blocks.append({"type": "divider"})
        
        return blocks
    
    def _get_tag_emoji(self, tag: str) -> str:
        """Get appropriate emoji for content tag"""
        emoji_map = {
            'Article': '📄',
            'X Post': '🐦',
            'LinkedIn': '💼',
            'RSS': '📡'
        }
        return emoji_map.get(tag, '📰')