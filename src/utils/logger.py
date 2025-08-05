"""
Logging configuration
"""

import logging
import os
from datetime import datetime

def setup_logger() -> logging.Logger:
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    log_filename = f"logs/ldnews_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger('ldnews')