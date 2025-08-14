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
            # Exclude X posts that mention @LeaveDelaware
            source_str = (entry.get('source') or '').lower()
            tag_str = (entry.get('tag') or '').lower()
            is_x_post = ('twitter' in source_str) or (tag_str == 'x post') or ('x post' in source_str)
            if is_x_post and '@leavedelaware' in text_content:
                self.logger.info(f"Skipping X post mentioning @LeaveDelaware: {entry.get('title', '')[:80]}")
                continue
            
            # Initial coarse keyword check
            if not any(keyword.lower() in text_content for keyword in self.keywords):
                continue

            # NEW: Validate that keywords appear in the main article content (RSS only)
            validate_main = (os.getenv('ARTICLE_VALIDATE_MAIN_CONTENT', '1') != '0')
            if validate_main and ('rss' in source_str):
                is_relevant, canonical_url = self._validate_article_main_content(entry.get('url'))
                if not is_relevant:
                    self.logger.info("Skipping RSS entry: keywords not found in main article body (likely sidebar/suggested match).")
                    continue
                if canonical_url:
                    entry['url'] = canonical_url  # prefer canonical article URL

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
        
        # Determine content tag
        tag = self._determine_tag(cleaned_entry)
        
        # Generate summary (skip for X posts so we only show headline in notifications)
        if tag == 'X Post':
            summary = ''  # no summary for X posts
        else:
            summary = self._generate_summary(cleaned_entry)
        
        # Normalize any Google redirect links
        normalized_url = self._normalize_generic_url(entry.get('url', ''))
        
        processed_entry = {
            'tag': tag,
            'title': self._clean_html_tags(title),  # Clean title again just in case
            'summary': self._clean_html_tags(summary),  # Clean summary too
            'url': normalized_url,
            'source': entry.get('source', ''),
            'published_date': entry.get('published_date', ''),
            'author': entry.get('author', ''),
            'original_entry': entry
        }
        
        return processed_entry

    def _normalize_generic_url(self, url: str) -> str:
        """Unwrap common Google redirect links and ensure http/https scheme"""
        if not url:
            return url
        from urllib.parse import urlparse, parse_qs, unquote
        try:
            u = str(url).strip()
            p = urlparse(u)
            if p.netloc.endswith('google.com') and p.path.startswith('/url'):
                qs = parse_qs(p.query)
                target = qs.get('q') or qs.get('url')
                if target and target[0]:
                    u = unquote(target[0])
                    p = urlparse(u)
            if not p.scheme:
                u = f"https://{u.lstrip('/')}"
            return u
        except Exception:
            return url

    # NEW: Main-article validation to avoid suggested/related-only matches
    def _validate_article_main_content(self, url: str) -> (bool, str):
        """
        Fetch the page, extract the main article text, and confirm at least one keyword
        appears in the main content. Returns (is_relevant, canonical_url_if_found).
        """
        if not url:
            return False, None

        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            real_url = self._normalize_generic_url(url)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            timeout = int(os.getenv('ARTICLE_FETCH_TIMEOUT', '8'))
            resp = requests.get(real_url, headers=headers, timeout=timeout, allow_redirects=True)
            if not (200 <= resp.status_code < 300):
                self.logger.warning(f"Fetch failed ({resp.status_code}) for URL: {real_url}")
                return True, None  # do not over-filter if fetch fails

            soup = BeautifulSoup(resp.text, "html.parser")

            # Resolve canonical URL if present
            canonical_url = None
            link_canon = soup.find("link", rel=lambda v: v and "canonical" in v)
            if link_canon and link_canon.get("href"):
                canonical_url = urljoin(resp.url, link_canon["href"])
            if not canonical_url:
                og_url = soup.find("meta", attrs={"property": "og:url"})
                if og_url and og_url.get("content"):
                    canonical_url = urljoin(resp.url, og_url["content"])

            # Strip non-content blocks
            for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "form"]):
                tag.decompose()

            # Remove common sidebar/related/recommended/latest sections
            def is_noise(el):
                for attr in ("class", "id"):
                    val = " ".join(el.get(attr, []) if isinstance(el.get(attr, []), list) else [el.get(attr, "")]).lower()
                    if re.search(r"(related|recommend|latest|sidebar|trending|most-read|more|footer|nav|menu)", val):
                        return True
                return False

            for el in soup.find_all(is_noise):
                el.decompose()

            # Prefer <article> or <main>, else pick largest multi-paragraph block
            candidates = []
            for sel in ["article", "main", "section"]:
                for el in soup.select(sel):
                    text = el.get_text(separator=" ", strip=True)
                    if text and len(text.split()) > 80:
                        candidates.append((len(text), text))
            if not candidates:
                for div in soup.find_all("div"):
                    ps = div.find_all("p")
                    if len(ps) >= 2:
                        text = " ".join(p.get_text(' ', strip=True) for p in ps)
                        if text and len(text.split()) > 80:
                            candidates.append((len(text), text))
            if not candidates and soup.body:
                body_text = soup.body.get_text(" ", strip=True)
                candidates.append((len(body_text), body_text))

            candidates.sort(reverse=True, key=lambda x: x[0])
            main_text = candidates[0][1] if candidates else ""

            main_text_lower = main_text.lower()
            has_keyword = any(k.lower() in main_text_lower for k in self.keywords)

            return has_keyword, canonical_url

        except Exception as e:
            self.logger.warning(f"Main-content validation failed for URL: {url} ({e})")
            return True, None

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