#!/usr/bin/env python3
"""
Leave Delaware News Aggregator
Main orchestration script that runs the daily content aggregation pipeline.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our custom modules
from src.data_collection.rss_parser import RSSParser
from src.data_collection.phantombuster_client import PhantomBusterClient
from src.data_processing.content_processor import ContentProcessor
from src.output_formatting.digest_formatter import DigestFormatter
from src.delivery.slack_sender import SlackSender
from src.delivery.gmail_sender import GmailSender
from src.utils.logger import setup_logger

def main():
    """Main pipeline execution"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Leave Delaware News Aggregator")
    
    try:
        # Initialize components
        rss_parser = RSSParser()
        phantombuster_client = PhantomBusterClient()
        content_processor = ContentProcessor()
        digest_formatter = DigestFormatter()
        slack_sender = SlackSender()
        gmail_sender = GmailSender()
        
        # Step 1: Data Collection
        logger.info("Starting data collection...")
        
        # Collect RSS data
        rss_data = rss_parser.collect_feeds()
        logger.info(f"Collected {len(rss_data)} RSS entries")
        
        # Collect PhantomBuster data
        pb_data = phantombuster_client.collect_all_data()
        logger.info(f"Collected {len(pb_data)} PhantomBuster entries")
        
        # Combine all data
        all_data = rss_data + pb_data
        logger.info(f"Total entries collected: {len(all_data)}")
        
        # Step 2: Data Processing
        logger.info("Processing content...")
        processed_data = content_processor.process_entries(all_data)
        logger.info(f"Processed {len(processed_data)} relevant entries")
        
        # Step 3: Format Output
        logger.info("Formatting digest...")
        digest = digest_formatter.format_digest(processed_data)
        
        # Step 4: Delivery
        logger.info("Sending digest...")
        
        # Send to Slack
        slack_result = slack_sender.send_digest(digest)
        logger.info(f"Slack delivery: {'Success' if slack_result else 'Failed'}")
        
        # Send to Gmail
        gmail_result = gmail_sender.send_digest(digest)
        logger.info(f"Gmail delivery: {'Success' if gmail_result else 'Failed'}")
        
        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()