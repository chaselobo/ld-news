@echo off
echo Setting up Leave Delaware News Aggregator...

REM Create virtual environment
python -m venv venv

REM Activate virtual environment
call venv\Scripts\activate

REM Install requirements
pip install -r requirements.txt

REM Create necessary directories
mkdir logs
mkdir src\data_collection
mkdir src\data_processing
mkdir src\output_formatting
mkdir src\delivery
mkdir src\utils

echo Setup complete!
echo Please:
echo 1. Update the .env file with your API keys
echo 2. Add your Google Alerts RSS URLs to rss_parser.py
echo 3. Set up Gmail OAuth credentials (credentials.json)
echo 4. Configure your PhantomBuster phantom IDs
echo 5. Run: python main.py