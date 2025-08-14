"""
PhantomBuster API client for social media data collection
"""

import os
import json
import csv
import requests
import logging
from typing import List, Dict
from datetime import datetime, timedelta
import io
import re

class PhantomBusterClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('PHANTOMBUSTER_API_KEY')
        self.base_url = "https://api.phantombuster.com/api/v2"
        
        # PhantomBuster container IDs (you'll need to set these)
        self.phantoms = {
            'twitter_hashtag': os.getenv('PB_TWITTER_HASHTAG_ID'),
            'twitter_search': os.getenv('PB_TWITTER_SEARCH_ID'),
            'twitter_extractor': os.getenv('PB_TWITTER_EXTRACTOR_ID'),
            'linkedin_posts': os.getenv('PB_LINKEDIN_POSTS_ID')
        }
        # Configurable recency window (days)
        self.window_days = int(os.getenv('PHANTOM_WINDOW_DAYS', '1'))

    def collect_all_data(self) -> List[Dict]:
        """Collect data from all PhantomBuster phantoms"""
        all_data = []
        
        for phantom_name, phantom_id in self.phantoms.items():
            if phantom_id:
                try:
                    data = self._get_phantom_results(phantom_id, phantom_name)
                    all_data.extend(data)
                    self.logger.info(f"Collected {len(data)} entries from {phantom_name}")
                except Exception as e:
                    self.logger.error(f"Failed to collect from {phantom_name}: {str(e)}")
                    
        return all_data

    def _get_phantom_results(self, phantom_id: str, phantom_name: str) -> List[Dict]:
        """Get results from a specific phantom (downloads actual result files)"""
        headers = {
            'X-Phantombuster-Key-1': self.api_key,
            'Content-Type': 'application/json'
        }

        # Use endpoint that returns agent metadata (including S3 paths to results)
        url = f"{self.base_url}/agents/fetch"
        params = {'id': phantom_id}

        try:
            self.logger.info(f"Making request to: {url} with ID: {phantom_id}")
            response = requests.get(url, headers=headers, params=params)
            self.logger.info(f"Response status: {response.status_code}")

            if response.status_code == 400:
                try:
                    error_data = response.json()
                    self.logger.error(f"PhantomBuster API error: {error_data}")
                except Exception:
                    self.logger.error(f"PhantomBuster API error (raw): {response.text}")

                # Try alternative auth placement
                self.logger.info("Trying API key as query parameter...")
                alt_params = {'id': phantom_id, 'key': self.api_key}
                alt_headers = {'Content-Type': 'application/json'}
                response = requests.get(url, headers=alt_headers, params=alt_params)
                self.logger.info(f"Alternative response status: {response.status_code}")

            response.raise_for_status()

            agent_payload = response.json()
            self.logger.info(f"Agent data keys: {list(agent_payload.keys())}")

            # Some responses place fields at root (v2), others under "data"
            data_section = agent_payload.get('data') if isinstance(agent_payload, dict) and isinstance(agent_payload.get('data'), dict) else agent_payload

            # 1) If API provides direct URLs, try them first
            direct_urls = []
            for key in ('csvUrl', 'jsonUrl', 'resultsCsvUrl', 'resultsJsonUrl'):
                if isinstance(data_section.get(key), str) and data_section[key].startswith('http'):
                    direct_urls.append((data_section[key], 'csv' if 'csv' in key.lower() else 'json'))

            for url_item, dtype in direct_urls:
                try:
                    self.logger.info(f"Attempting direct download ({dtype}): {url_item}")
                    file_resp = requests.get(url_item)
                    if file_resp.status_code == 200 and file_resp.text.strip():
                        self.logger.info(f"Downloaded {dtype.upper()} with {len(file_resp.text)} chars")
                        return self._parse_data_by_type(file_resp.text, phantom_name, dtype)
                except Exception as e:
                    self.logger.warning(f"Direct download failed for {url_item}: {e}")

            # 2) Build S3 URLs using orgS3Folder + s3Folder
            s3_folder = data_section.get('s3Folder', '')
            org_s3_folder = data_section.get('orgS3Folder', '')

            if not s3_folder or not org_s3_folder:
                self.logger.error(f"Missing S3 folder info in response: {agent_payload}")
                return []

            # Extract filename from phantom arguments if provided (e.g., "csvName")
            candidate_names = []
            csv_name = None
            raw_arg = data_section.get('argument')
            if isinstance(raw_arg, str):
                try:
                    args_obj = json.loads(raw_arg)
                    csv_name = args_obj.get('csvName') or args_obj.get('csvFilename')
                    if csv_name:
                        candidate_names.append(csv_name)
                        self.logger.info(f"Using csvName from arguments: {csv_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to parse 'argument' JSON: {e}")

            # Add common defaults as fallbacks
            candidate_names.extend(['result', 'results', 'output', 'data', 'dataset'])

            # Try candidates: CSV first, then JSON
            for base in candidate_names:
                csv_url = f"https://phantombuster.s3.amazonaws.com/{org_s3_folder}/{s3_folder}/{base}.csv"
                json_url = f"https://phantombuster.s3.amazonaws.com/{org_s3_folder}/{s3_folder}/{base}.json"

                try:
                    self.logger.info(f"Attempting to download CSV from: {csv_url}")
                    csv_response = requests.get(csv_url)
                    if csv_response.status_code == 200 and csv_response.text.strip():
                        self.logger.info(f"Successfully downloaded CSV with {len(csv_response.text)} characters")
                        return self._parse_data_by_type(csv_response.text, phantom_name, 'csv')
                except Exception as e:
                    self.logger.warning(f"Failed to download CSV at {csv_url}: {e}")

                try:
                    self.logger.info(f"Attempting to download JSON from: {json_url}")
                    json_response = requests.get(json_url)
                    if json_response.status_code == 200 and json_response.text.strip():
                        self.logger.info(f"Successfully downloaded JSON with {len(json_response.text)} characters")
                        return self._parse_data_by_type(json_response.text, phantom_name, 'json')
                except Exception as e:
                    self.logger.warning(f"Failed to download JSON at {json_url}: {e}")

            self.logger.error("Could not download results from any discovered URL (CSV or JSON)")
            return []

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Error for {phantom_name}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Error response body: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {phantom_name}: {e}")
            raise

    def _parse_data_by_type(self, data: str, phantom_name: str, data_type: str) -> List[Dict]:
        """Parse data based on phantom type and data format"""
        if phantom_name in ['twitter_hashtag', 'twitter_search', 'twitter_extractor']:
            return self._parse_twitter_data(data, phantom_name)
        elif phantom_name == 'linkedin_posts':
            return self._parse_linkedin_data(data)
        return []

    def _parse_twitter_data(self, data: str, source_type: str) -> List[Dict]:
        """Parse Twitter data from PhantomBuster (supports JSON or CSV)"""
        entries: List[Dict] = []
        try:
            data_str = data.strip()
    
            # JSON path
            if data_str.startswith('{') or data_str.startswith('['):
                try:
                    obj = json.loads(data_str)
                    if isinstance(obj, dict) and isinstance(obj.get('data'), list):
                        rows = obj['data']
                    elif isinstance(obj, list):
                        rows = obj
                    else:
                        rows = []
                    
                    for row in rows:
                        # Prefer Tweet Date field, fallback to generic date extraction
                        post_dt, display_date = self._extract_tweet_date(row)
                        if post_dt is None:
                            post_dt = self._extract_date(row)
                            display_date = post_dt.date().isoformat() if post_dt else ''
                        if not self._is_recent(post_dt):
                            continue
                        text = row.get('text') or row.get('content') or row.get('message') or row.get('title') or ''
                        # Prefer explicit tweet link from PhantomBuster output
                        url = self._extract_tweet_link(row) or self._normalize_twitter_url(row)
                        author = row.get('handle') or row.get('username') or row.get('author') or row.get('poster') or row.get('name', '')
                        
                        entry = {
                            'source': f'Twitter ({source_type})',
                            'title': (text[:100] + '...') if len(text) > 100 else text,
                            'description': text,
                            'url': url,
                            'published_date': display_date,
                            'author': author,
                            'raw_data': row
                        }
                        entries.append(entry)
                    
                    return entries
                except Exception:
                    # Fall through to CSV parsing
                    pass
    
            # CSV path
            f = io.StringIO(data_str)
            try:
                dialect = csv.Sniffer().sniff(data_str[:1024])
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
            except Exception:
                f.seek(0)
                reader = csv.DictReader(f)
    
            parse_failures = 0
            for row in reader:
                # Prefer Tweet Date field, fallback to generic date extraction
                post_dt, display_date = self._extract_tweet_date(row)
                if post_dt is None:
                    post_dt = self._extract_date(row)
                    display_date = post_dt.date().isoformat() if post_dt else ''
                if not self._is_recent(post_dt):
                    if post_dt is None:
                        parse_failures += 1
                    continue
    
                text = row.get('text') or row.get('content') or row.get('message') or row.get('title') or ''
                # Prefer explicit tweet link from PhantomBuster output
                url = self._extract_tweet_link(row) or self._normalize_twitter_url(row)
                author = row.get('handle') or row.get('username') or row.get('author') or row.get('poster') or row.get('name', '')
    
                entry = {
                    'source': f'Twitter ({source_type})',
                    'title': (text[:100] + '...') if len(text) > 100 else text,
                    'description': text,
                    'url': url,
                    'published_date': display_date,
                    'author': author,
                    'raw_data': row
                }
                entries.append(entry)
    
            if parse_failures:
                self.logger.info(f"Twitter parser: {parse_failures} rows skipped due to unparseable dates")
    
        except Exception as e:
            self.logger.error(f"Failed to parse Twitter data: {str(e)}")
            
        return entries

    def _normalize_twitter_url(self, row: Dict) -> str:
        """Normalize Twitter/X URLs to ensure they work correctly"""
        # Prefer explicit tweet/post URLs first
        candidates = [
            row.get('tweetUrl'),
            row.get('postUrl'),
            row.get('url'),
            row.get('link')
        ]
        # Pick first non-empty URL
        url = next((c for c in candidates if c), '') or ''
        url = str(url).strip()

        # Helpers (local imports to avoid changing module imports)
        from urllib.parse import urlparse, parse_qs, unquote
        import re

        def _unwrap_google_redirect(u: str) -> str:
            try:
                p = urlparse(u)
                if p.netloc.endswith('google.com') and p.path.startswith('/url'):
                    qs = parse_qs(p.query)
                    # Google uses either 'q' or 'url'
                    target = qs.get('q') or qs.get('url')
                    if target and target[0]:
                        return unquote(target[0])
            except Exception:
                pass
            return u

        def _ensure_scheme(u: str) -> str:
            if not u:
                return u
            if u.startswith('//'):
                return f"https:{u}"
            if not re.match(r'^https?://', u, re.IGNORECASE):
                return f"https://{u.lstrip('/')}"
            return u

        # Unwrap redirects and ensure scheme
        url = _unwrap_google_redirect(url)
        url = _ensure_scheme(url)

        if not url:
            return url

        # Convert Twitter domains to x.com
        url = url.replace('mobile.twitter.com', 'twitter.com')
        url = url.replace('twitter.com', 'x.com')

        # Extract tweet ID from common patterns
        tweet_id_match = re.search(r'/status(?:es)?/(\d+)', url)
        if not tweet_id_match:
            tweet_id_match = re.search(r'/i/web/status/(\d+)', url)
        tweet_id = tweet_id_match.group(1) if tweet_id_match else None

        # Gather username from multiple potential fields
        username = (
            row.get('handle') or
            row.get('username') or
            row.get('userScreenName') or
            row.get('screen_name') or
            row.get('screenName') or
            row.get('author') or
            row.get('poster') or
            row.get('name', '')
        )
        username = (username or '').replace('@', '').strip()

        # If we have a tweet ID, construct canonical URL
        if tweet_id:
            if username:
                return f"https://x.com/{username}/status/{tweet_id}"
            return f"https://x.com/i/status/{tweet_id}"

        # Fallback if row carries an ID/tweetId field even when URL doesn’t
        row_id = (str(row.get('tweetId') or row.get('id') or row.get('status_id') or '')).strip()
        if row_id.isdigit():
            if username:
                return f"https://x.com/{username}/status/{row_id}"
            return f"https://x.com/i/status/{row_id}"

        # If no tweet ID, keep the normalized URL (at least scheme + x.com)
        return url

    def _parse_linkedin_data(self, data: str) -> List[Dict]:
        """Parse LinkedIn data from PhantomBuster (supports JSON or CSV)"""
        entries: List[Dict] = []
        try:
            data_str = data.strip()

            # JSON
            if data_str.startswith('{') or data_str.startswith('['):
                try:
                    obj = json.loads(data_str)
                    if isinstance(obj, dict) and isinstance(obj.get('data'), list):
                        rows = obj['data']
                    elif isinstance(obj, list):
                        rows = obj
                    else:
                        rows = []
                    
                    for row in rows:
                        post_date = self._extract_date(row)
                        if not self._is_recent(post_date):
                            continue
                        text = row.get('text') or row.get('content') or row.get('message') or row.get('title') or ''
                        url = row.get('url') or row.get('link') or row.get('postUrl') or ''
                        author = row.get('author') or row.get('username') or row.get('name', '')
                        entry = {
                            'source': 'LinkedIn',
                            'title': (text[:100] + '...') if len(text) > 100 else text,
                            'description': text,
                            'url': url,
                            'published_date': post_date.isoformat() if post_date else '',
                            'author': author,
                            'raw_data': row
                        }
                        entries.append(entry)
                    return entries
                except Exception:
                    pass

            # CSV
            f = io.StringIO(data_str)
            try:
                dialect = csv.Sniffer().sniff(data_str[:1024])
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
            except Exception:
                f.seek(0)
                reader = csv.DictReader(f)

            parse_failures = 0
            for row in reader:
                post_date = self._extract_date(row)
                if not self._is_recent(post_date):
                    if post_date is None:
                        parse_failures += 1
                    continue

                text = row.get('text') or row.get('content') or row.get('message') or row.get('title') or ''
                url = row.get('url') or row.get('link') or row.get('postUrl') or ''
                author = row.get('author') or row.get('username') or row.get('name', '')
                entry = {
                    'source': 'LinkedIn',
                    'title': (text[:100] + '...') if len(text) > 100 else text,
                    'description': text,
                    'url': url,
                    'published_date': post_date.isoformat() if post_date else '',
                    'author': author,
                    'raw_data': row
                }
                entries.append(entry)

            if parse_failures:
                self.logger.info(f"LinkedIn parser: {parse_failures} rows skipped due to unparseable dates")

        except Exception as e:
            self.logger.error(f"Failed to parse LinkedIn data: {str(e)}")
            
        return entries

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string or epoch to datetime object"""
        if not date_str:
            return None

        s = str(date_str).strip()

        # Epoch seconds/milliseconds
        if re.fullmatch(r'\d{10,13}', s):
            try:
                ts = int(s)
                if ts >= 1_000_000_000_000:  # ms
                    ts /= 1000.0
                return datetime.fromtimestamp(ts)
            except Exception:
                pass

        # Remove timezone colon if present (e.g., +00:00 -> +0000)
        s_tz_fixed = re.sub(r'([+-]\d\d):(\d\d)$', r'\1\2', s)

        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S%z',
            '%a, %d %b %Y %H:%M:%S %z',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s_tz_fixed, fmt)
            except ValueError:
                continue

        return None

    def _extract_date(self, row: Dict) -> datetime:
        """Try a variety of common keys to extract a post date"""
        keys = [
            'timestamp', 'date', 'publishedAt', 'publicationDate', 'time',
            'created_at', 'post_date', 'timestampMs', 'epoch'
        ]
        for k in keys:
            v = row.get(k)
            if v:
                dt = self._parse_date(v)
                if dt:
                    return dt
        return None

    def _is_recent(self, dt: datetime) -> bool:
        if not dt:
            return False
        return dt >= (datetime.now() - timedelta(days=self.window_days))

    def _extract_tweet_date(self, row: Dict):
        """Extract Tweet Date from common PhantomBuster headers and return (datetime, 'YYYY-MM-DD')."""
        candidates = ['tweet date', 'tweet_date', 'tweetDate', 'tweeted at', 'tweeted_at', 'tweetedAt']
        val = self._get_caseinsensitive_field(row, candidates)
        if not val:
            return (None, '')
        s = str(val).strip()
        # Try full parsing to datetime
        dt = self._parse_date(s)
        if dt:
            return (dt, dt.date().isoformat())
        # Heuristic: find a date-like token and try parsing again
        import re
        patterns = [
            r'\d{4}-\d{2}-\d{2}',                # ISO: 2025-08-05
            r'\d{1,2}/\d{1,2}/\d{2,4}',          # US: 8/5/2025 or 08/05/25
            r'[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}'  # Aug 5, 2025
        ]
        for pat in patterns:
            m = re.search(pat, s)
            if m:
                token = m.group(0)
                dt2 = self._parse_date(token)
                if dt2:
                    return (dt2, dt2.date().isoformat())
                return (None, token)
        # Fallback: return raw string (sorting may be less accurate)
        return (None, s)
    def _extract_tweet_link(self, row: Dict) -> str:
        """Return the tweet link from row by matching common header variants, normalized to https and x.com."""
        candidates = [
            'tweet link', 'tweet url', 'tweet_url', 'tweetlink', 'tweetURL',
            'status url', 'status link', 'permalink', 'permalink url',
            'tweet permalink', 'tweet_perma_link', 'tweetpermalink'
        ]
        link = self._get_caseinsensitive_field(row, candidates)
        if not link:
            return ''

        link = str(link).strip()

        # Ensure scheme and normalize domain to x.com
        if link.startswith('//'):
            link = f'https:{link}'
        elif not re.match(r'^https?://', link, re.IGNORECASE):
            link = f'https://{link.lstrip("/")}'

        link = link.replace('mobile.twitter.com', 'twitter.com').replace('twitter.com', 'x.com')
        return link

    def _get_caseinsensitive_field(self, row: Dict, candidate_names: List[str]) -> str:
        """Fetch a field value by matching keys case-insensitively and ignoring non-alphanumerics."""
        # Build normalized-key map from the row
        normalized_map = {}
        for k, v in row.items():
            norm = re.sub(r'[^a-z0-9]', '', str(k).lower())
            normalized_map[norm] = v

        for name in candidate_names:
            key_norm = re.sub(r'[^a-z0-9]', '', name.lower())
            val = normalized_map.get(key_norm)
            if val not in (None, ''):
                return str(val)
        return ''