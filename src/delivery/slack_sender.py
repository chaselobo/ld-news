"""
Slack integration for sending daily digests
"""

import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Dict, List
from datetime import datetime
from urllib.parse import urlparse

class SlackSender:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        self.channel = os.getenv('SLACK_CHANNEL', '#LD-News').strip()
        
    def send_digest(self, digest: Dict) -> bool:
        """Send digest to Slack channel using Block Kit format in a single message"""
        try:
            if digest['total_entries'] == 0:
                blocks = self._create_empty_digest_blocks(digest)
            else:
                blocks = self._create_full_digest_blocks(digest)
            
            # Warn if using a channel name; Slack APIs generally prefer channel IDs (e.g., C0123ABCD)
            if self.channel.startswith('#'):
                self.logger.warning(f"SLACK_CHANNEL is set to '{self.channel}'. Consider using a channel ID for reliability.")

            # Send everything in one message
            result = self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                text=f"📰 Leave Delaware Daily Digest - {digest.get('total_entries', 0)} items"
            )
                
            # Enhanced success logging with channel id and permalink
            ok = result.get('ok', False)
            chan = result.get('channel', self.channel)
            ts = result.get('ts')
            self.logger.info(f"Slack post ok={ok}, channel={chan}, ts={ts}")
            try:
                if chan and ts:
                    perm = self.client.chat_getPermalink(channel=chan, message_ts=ts)
                    permalink = perm.get('permalink')
                    if permalink:
                        self.logger.info(f"Slack message permalink: {permalink}")
            except SlackApiError as e:
                self.logger.warning(f"Could not fetch Slack permalink: {e.response.get('error', 'unknown_error')}")
            except Exception as e:
                self.logger.warning(f"Could not fetch Slack permalink: {str(e)}")

            self.logger.info(f"Successfully sent digest to Slack channel {self.channel}")
            return True
            
        except SlackApiError as e:
            self.logger.error(f"Slack API error: {e.response['error']}")
            # Log raw response as well for troubleshooting
            try:
                self.logger.error(f"Slack API response: {e.response.data}")
            except Exception:
                pass
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

            # Validate URL for Slack button
            raw_url = (entry.get('url') or '').strip()
            try:
                parsed = urlparse(raw_url)
                url_ok = parsed.scheme in ('http', 'https') and bool(parsed.netloc)
            except Exception:
                url_ok = False

            # Build main text differently for X Posts (no summary)
            if entry.get('tag') == 'X Post':
                if url_ok:
                    main_text = f"*{i}. {entry['title']}*"
                else:
                    inline_link = f" <{raw_url}|Read More>" if raw_url else ""
                    main_text = f"*{i}. {entry['title']}*{inline_link}"
            else:
                # Non-X posts keep summary
                if url_ok:
                    main_text = f"*{i}. {entry['title']}*\n\n{entry['summary']}"
                else:
                    inline_link = f" <{raw_url}|Read More>" if raw_url else ""
                    main_text = f"*{i}. {entry['title']}*\n\n{entry['summary']}{inline_link}"

            # Main entry block
            entry_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": main_text
                }
            }

            # Only attach button accessory when the URL is valid to avoid invalid_blocks
            if url_ok:
                entry_block["accessory"] = {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Read More"
                    },
                    "url": raw_url,
                    "action_id": f"read_more_{i}"
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
            
            # For X Posts, add posted date (date only) if present
            if entry.get('tag') == 'X Post' and entry.get('published_date'):
                context_elements.append({
                    "type": "mrkdwn",
                    "text": f"• Posted: {entry['published_date']}"
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