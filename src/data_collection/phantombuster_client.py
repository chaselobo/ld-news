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
        """Get results from a specific phantom"""
        headers = {
            'X-Phantombuster-Key-1': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Get the latest agent output
        url = f"{self.base_url}/agents/fetch-output"
        params = {'id': phantom_id}
        
        try:
            self.logger.info(f"Making request to: {url} with ID: {phantom_id}")
            response = requests.get(url, headers=headers, params=params)
            
            # Log the response details for debugging
            self.logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 400:
                # Try to get the actual error message
                try:
                    error_data = response.json()
                    self.logger.error(f"PhantomBuster API error: {error_data}")
                except:
                    self.logger.error(f"PhantomBuster API error (raw): {response.text}")
                
                # Try alternative: API key as query parameter
                self.logger.info("Trying API key as query parameter...")
                alt_params = {'id': phantom_id, 'key': self.api_key}
                alt_headers = {'Content-Type': 'application/json'}
                
                response = requests.get(url, headers=alt_headers, params=alt_params)
                self.logger.info(f"Alternative response status: {response.status_code}")
            
            response.raise_for_status()
            
            # Parse the results based on format (CSV or JSON)
            results_data = response.text
            self.logger.info(f"Successfully retrieved {len(results_data)} characters of data")
            
            if phantom_name in ['twitter_hashtag', 'twitter_search', 'twitter_extractor']:
                return self._parse_twitter_data(results_data, phantom_name)
            elif phantom_name == 'linkedin_posts':
                return self._parse_linkedin_data(results_data)
            
            return []
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Error for {phantom_name}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Error response body: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {phantom_name}: {e}")
            raise
    
    def _parse_twitter_data(self, data: str, source_type: str) -> List[Dict]:
        """Parse Twitter data from PhantomBuster"""
        entries = []
        
        try:
            # Assume CSV format
            lines = data.strip().split('\n')
            if len(lines) < 2:
                return entries
                
            reader = csv.DictReader(lines)
            
            for row in reader:
                # Filter for recent posts (last 24 hours)
                post_date = self._parse_date(row.get('timestamp', row.get('date', '')))
                if not post_date or post_date < datetime.now() - timedelta(days=1):
                    continue
                    
                entry = {
                    'source': f'Twitter ({source_type})',
                    'title': row.get('text', '')[:100] + '...' if len(row.get('text', '')) > 100 else row.get('text', ''),
                    'description': row.get('text', ''),
                    'url': row.get('url', ''),
                    'published_date': post_date.isoformat() if post_date else '',
                    'author': row.get('handle', row.get('username', '')),
                    'raw_data': row
                }
                
                entries.append(entry)
                
        except Exception as e:
            self.logger.error(f"Failed to parse Twitter data: {str(e)}")
            
        return entries
    
    def _parse_linkedin_data(self, data: str) -> List[Dict]:
        """Parse LinkedIn data from PhantomBuster"""
        entries = []
        
        try:
            # Assume CSV format
            lines = data.strip().split('\n')
            if len(lines) < 2:
                return entries
                
            reader = csv.DictReader(lines)
            
            for row in reader:
                # Filter for recent posts
                post_date = self._parse_date(row.get('timestamp', row.get('date', '')))
                if not post_date or post_date < datetime.now() - timedelta(days=1):
                    continue
                    
                entry = {
                    'source': 'LinkedIn',
                    'title': row.get('text', '')[:100] + '...' if len(row.get('text', '')) > 100 else row.get('text', ''),
                    'description': row.get('text', ''),
                    'url': row.get('url', ''),
                    'published_date': post_date.isoformat() if post_date else '',
                    'author': row.get('author', ''),
                    'raw_data': row
                }
                
                entries.append(entry)
                
        except Exception as e:
            self.logger.error(f"Failed to parse LinkedIn data: {str(e)}")
            
        return entries
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object"""
        if not date_str:
            return None
            
        # Try different date formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        return None