"""
RSS Feed Parser for Google Alerts and other RSS sources
"""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from urllib.parse import urlparse

class RSSParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Google Alerts RSS feeds for "Leave Delaware" related keywords
        self.rss_feeds = [
            # Add your Google Alerts RSS URLs here
            # Example: "https://www.google.com/alerts/feeds/YOUR_FEED_ID/YOUR_USER_ID"
            "https://www.google.com/alerts/feeds/06601863395694669251/9995654798472005352",
            "https://www.google.com/alerts/feeds/06601863395694669251/16004259333949280068",
            "https://www.google.com/alerts/feeds/06601863395694669251/3680386234290564637",
            "https://www.google.com/alerts/feeds/06601863395694669251/18106957652211235157",                                                            
            "https://www.google.com/alerts/feeds/06601863395694669251/18106957652211235157"
            "https://www.google.com/alerts/feeds/06601863395694669251/3326337120077905925"
            "https://www.google.com/alerts/feeds/06601863395694669251/8167620267097628304"
            "https://www.google.com/alerts/feeds/06601863395694669251/6159050914814077015"   
        ]
        
    def collect_feeds(self) -> List[Dict]:
        """Collect and parse all RSS feeds"""
        all_entries = []
        
        for feed_url in self.rss_feeds:
            try:
                entries = self._parse_feed(feed_url)
                all_entries.extend(entries)
                self.logger.info(f"Parsed {len(entries)} entries from {feed_url}")
            except Exception as e:
                self.logger.error(f"Failed to parse feed {feed_url}: {str(e)}")
                
        return all_entries
    
    def _parse_feed(self, feed_url: str) -> List[Dict]:
        """Parse a single RSS feed"""
        feed = feedparser.parse(feed_url)
        entries = []
        
        # Only get entries from the last 24 hours
        cutoff_date = datetime.now() - timedelta(days=1)
        
        for entry in feed.entries:
            try:
                # Parse published date
                published_date = datetime(*entry.published_parsed[:6])
                
                # Skip old entries
                if published_date < cutoff_date:
                    continue
                    
                parsed_entry = {
                    'source': 'RSS',
                    'title': entry.title,
                    'description': getattr(entry, 'description', ''),
                    'url': entry.link,
                    'published_date': published_date.isoformat(),
                    'raw_data': entry
                }
                
                entries.append(parsed_entry)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse entry: {str(e)}")
                continue
                
        return entries