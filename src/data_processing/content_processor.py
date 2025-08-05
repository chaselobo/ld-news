"""
Content processor with keyword filtering and OpenAI summarization
"""

import os
import openai
import logging
from typing import List, Dict
import re

class ContentProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Keywords to filter content
        self.keywords = [
            "Leave Delaware",
            "Delaware Taxes", 
            "Delaware Court of Chancery",
            "Companies reincorporating in Texas",
            "Companies reincorporating in Nevada",
            "Delaware incorporation",
            "Corporate law news",
            "RelocateFromDelaware",
            "LeaveDelaware",
            "corporate relocation"
        ]
    
    def _clean_html_tags(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return text
        
        # Remove HTML tags using regex
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up common HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, replacement in html_entities.items():
            clean_text = clean_text.replace(entity, replacement)
        
        # Clean up extra whitespace
        clean_text = ' '.join(clean_text.split())
        
        return clean_text

    def process_entries(self, entries: List[Dict]) -> List[Dict]:
        """Process entries: filter by keywords and generate summaries"""
        filtered_entries = self._filter_by_keywords(entries)
        processed_entries = []
        
        for entry in filtered_entries:
            try:
                processed_entry = self._process_single_entry(entry)
                if processed_entry:
                    processed_entries.append(processed_entry)
            except Exception as e:
                self.logger.error(f"Failed to process entry: {str(e)}")
                continue
                
        return processed_entries

    def _filter_by_keywords(self, entries: List[Dict]) -> List[Dict]:
        """Filter entries that contain relevant keywords"""
        filtered = []
        
        for entry in entries:
            text_content = f"{entry.get('title', '')} {entry.get('description', '')}".lower()
            
            # Check if any keyword is present
            if any(keyword.lower() in text_content for keyword in self.keywords):
                filtered.append(entry)
                
        self.logger.info(f"Filtered {len(filtered)} relevant entries from {len(entries)} total")
        return filtered

    def _process_single_entry(self, entry: Dict) -> Dict:
        """Process a single entry: generate title and summary"""
        # Clean HTML tags from title and description before processing
        cleaned_entry = entry.copy()
        cleaned_entry['title'] = self._clean_html_tags(entry.get('title', ''))
        cleaned_entry['description'] = self._clean_html_tags(entry.get('description', ''))
        
        # Generate title if missing or improve existing one
        title = self._generate_title(cleaned_entry)
        
        # Generate summary
        summary = self._generate_summary(cleaned_entry)
        
        # Determine content tag
        tag = self._determine_tag(cleaned_entry)
        
        processed_entry = {
            'tag': tag,
            'title': self._clean_html_tags(title),  # Clean title again just in case
            'summary': self._clean_html_tags(summary),  # Clean summary too
            'url': entry.get('url', ''),
            'source': entry.get('source', ''),
            'published_date': entry.get('published_date', ''),
            'author': entry.get('author', ''),
            'original_entry': entry
        }
        
        return processed_entry

    def _generate_title(self, entry: Dict) -> str:
        """Generate or improve title using OpenAI"""
        existing_title = entry.get('title', '')
        content = entry.get('description', '')
        
        # If title is good enough, use it
        if existing_title and len(existing_title) > 10 and not existing_title.startswith('http'):
            return existing_title
            
        # Generate new title
        prompt = f"""Generate a clear, concise title (max 80 characters) for this content about Delaware business/corporate news:

Content: {content[:500]}

Title:"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using GPT-4 as GPT-4.1 nano isn't available yet
                messages=[
                    {"role": "system", "content": "You are a news editor creating titles for Delaware business news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            title = response.choices[0].message.content.strip()
            return title if title else existing_title
            
        except Exception as e:
            self.logger.error(f"Failed to generate title: {str(e)}")
            return existing_title or "Delaware Business News"

    def _generate_summary(self, entry: Dict) -> str:
        """Generate 1-3 sentence summary using OpenAI"""
        content = entry.get('description', '') or entry.get('title', '')
        
        prompt = f"""Summarize this Delaware business/corporate news in 1-3 clear, concise sentences:

Content: {content[:1000]}

Summary:"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a news editor creating concise summaries for Delaware business news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            return summary if summary else content[:200] + "..."
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            return content[:200] + "..." if len(content) > 200 else content

    def _determine_tag(self, entry: Dict) -> str:
        """Determine the appropriate tag for the entry"""
        source = entry.get('source', '').lower()
        
        if 'twitter' in source or 'x post' in source:
            return 'X Post'
        elif 'linkedin' in source:
            return 'LinkedIn'
        elif 'rss' in source:
            return 'Article'
        else:
            return 'Article'