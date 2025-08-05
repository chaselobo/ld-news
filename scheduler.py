"""
Daily scheduler for the Leave Delaware News Aggregator
Run this script to set up daily execution
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime

def run_aggregator():
    """Run the main aggregator script"""
    try:
        print(f"Starting Leave Delaware News Aggregator at {datetime.now()}")
        result = subprocess.run(['python', 'main.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Aggregator completed successfully")
        else:
            print(f"Aggregator failed with error: {result.stderr}")
            
    except Exception as e:
        print(f"Failed to run aggregator: {str(e)}")

# Schedule the job to run daily at 9:45 AM
schedule.every().day.at("09:45").do(run_aggregator)

print("Scheduler started. The aggregator will run daily at 9:45 AM.")
print("Press Ctrl+C to stop the scheduler.")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute