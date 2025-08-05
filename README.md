# Leave Delaware News Aggregator

A comprehensive Python tool that aggregates content related to "Leave Delaware" from multiple sources and delivers daily digests via Slack and Gmail. This tool is designed to help curate content for social media and weekly newsletters.

## 🎯 Overview

The Leave Delaware News Aggregator automatically:
- Collects data from Google Alerts RSS feeds and PhantomBuster social media scraping
- Filters content using relevant keywords
- Generates summaries and titles using OpenAI GPT-4
- Formats content into digestible daily reports
- Delivers reports via Slack and Gmail

## 🏗️ Architecture

### Data Collection Layer
- **RSS Parser**: Pulls Google Alerts RSS feeds for predefined keywords
- **PhantomBuster Integration**: Scrapes social media content from Twitter/X and LinkedIn

### Data Processing Layer
- **Keyword Filtering**: Filters content by Delaware-related business keywords
- **AI Summarization**: Uses OpenAI GPT-4 to generate concise summaries and clean titles

### Output Formatting Layer
- **Digest Formatter**: Creates structured text and HTML output
- **Content Tagging**: Categorizes content by source (Article, X Post, LinkedIn)

### Delivery Layer
- **Slack Integration**: Sends daily digest to #LD-News channel
- **Gmail Integration**: Sends HTML-formatted emails to internal recipients

## 📋 Requirements

### Python Dependencies
Python 3.8+
feedparser==6.0.10
requests==2.31.0
openai==0.28.1
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
slack-sdk==3.23.0
python-dotenv==1.0.0


### External Services
- OpenAI API account
- PhantomBuster account with configured phantoms
- Google Cloud Platform project with Gmail API enabled
- Slack workspace with bot permissions
- Google Alerts RSS feeds

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd LDNEWS

# Run setup script (Windows)
setup.bat

# Or manually:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

#### Environment Variables
Copy and configure the `.env` file:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# PhantomBuster API Key and Container IDs
PHANTOMBUSTER_API_KEY=your_phantombuster_api_key
PB_TWITTER_HASHTAG_ID=your_twitter_hashtag_phantom_id
PB_TWITTER_SEARCH_ID=your_twitter_search_phantom_id
PB_TWITTER_EXTRACTOR_ID=your_twitter_extractor_phantom_id
PB_LINKEDIN_POSTS_ID=your_linkedin_posts_phantom_id

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#LD-News

# Gmail Configuration
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
```

#### Google Alerts RSS Setup
1. Create Google Alerts for relevant keywords:
   - "Leave Delaware"
   - "Delaware Taxes"
   - "Delaware Court of Chancery"
   - "Companies reincorporating in Texas"
   - "Companies reincorporating in Nevada"
   - "Delaware incorporation"
   - "Corporate law news"

2. Get RSS feed URLs and add them to `src/data_collection/rss_parser.py`:

```python
self.rss_feeds = [
    "https://www.google.com/alerts/feeds/YOUR_FEED_ID_1/YOUR_USER_ID",
    "https://www.google.com/alerts/feeds/YOUR_FEED_ID_2/YOUR_USER_ID",
    # Add more RSS feed URLs
]
```

#### PhantomBuster Setup
1. Create and configure these phantoms:
   - **Twitter Hashtag Search Export**: For hashtags like #LeaveDelaware, #RelocateFromDelaware
   - **Twitter Search Export**: For keywords like "Leave Delaware", "corporate relocation"
   - **Twitter Tweet Extractor**: For specific accounts like @LeaveDelaware
   - **Extract Leads from LinkedIn Posts**: For LinkedIn posts with relevant keywords

2. Schedule phantoms to run daily
3. Get phantom IDs and add to `.env` file

#### Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download `credentials.json` to project root
6. Run the application once to complete OAuth flow

#### Slack Bot Setup
1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app
3. Add bot token scopes: `chat:write`, `channels:read`
4. Install app to workspace
5. Get bot token and add to `.env`
6. Invite bot to #LD-News channel

### 3. Running the Application

#### Manual Execution
```bash
python main.py
```

#### Scheduled Execution
```bash
# Run daily scheduler
python scheduler.py
```

The scheduler will run the aggregator daily at 9:00 AM.

## 📁 Project Structure
LDNEWS/
├── main.py                 # Main orchestration script
├── scheduler.py            # Daily scheduler
├── requirements.txt        # Python dependencies
├── setup.bat              # Windows setup script
├── .env                   # Environment variables
├── credentials.json       # Gmail OAuth credentials
├── token.json            # Gmail OAuth token (auto-generated)
├── logs/                 # Application logs
└── src/
├── data_collection/
│   ├── rss_parser.py         # RSS feed parsing
│   └── phantombuster_client.py # PhantomBuster integration
├── data_processing/
│   └── content_processor.py   # Content filtering and AI processing
├── output_formatting/
│   └── digest_formatter.py    # Output formatting
├── delivery/
│   ├── slack_sender.py       # Slack integration
│   └── gmail_sender.py       # Gmail integration
└── utils/
└── logger.py             # Logging configuration


## 🔧 Configuration Details

### Keyword Filtering
The system filters content using these keywords (configurable in `content_processor.py`):
- "Leave Delaware"
- "Delaware Taxes"
- "Delaware Court of Chancery"
- "Companies reincorporating in Texas or Nevada"
- "Delaware incorporation"
- "Corporate law news"
- "RelocateFromDelaware"
- "LeaveDelaware"
- "corporate relocation"

### Content Sources
- **RSS Feeds**: Google Alerts for news articles
- **Twitter/X**: Hashtag searches, keyword searches, specific account tweets
- **LinkedIn**: Posts and comments with relevant keywords

### Output Format
Each entry is formatted as:
[tag] (LinkedIn, X Post, Article)
Title: [Generated or original title]
Summary: [1–3 sentence summary]
URL: [link to post]


## 📊 Usage Examples

### Daily Digest Output
📰 Leave Delaware Daily Digest - December 15, 2024
Found 5 relevant items today

1. 1.
   [Article] Major Corporation Announces Delaware Exit
   XYZ Corp announced plans to reincorporate in Texas, citing Delaware's changing business climate and tax implications.
   🔗 https://example.com/news/xyz-corp-delaware-exit
2. 2.
   [X Post] Delaware Business Climate Discussion
   Thread discussing the pros and cons of Delaware incorporation for startups in 2024.
   🔗 https://twitter.com/user/status/123456789


## 🔍 Monitoring and Logs

- Application logs are stored in `logs/` directory
- Daily log files: `logs/ldnews_YYYYMMDD.log`
- Logs include data collection stats, processing results, and delivery status

## 🛠️ Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   - Check API key validity
   - Verify account has sufficient credits
   - Check rate limits

2. **PhantomBuster Connection Issues**
   - Verify API key and phantom IDs
   - Check phantom execution status
   - Ensure phantoms are scheduled to run

3. **Gmail Authentication Issues**
   - Re-run OAuth flow by deleting `token.json`
   - Check Gmail API is enabled in Google Cloud Console
   - Verify `credentials.json` is valid

4. **Slack Delivery Issues**
   - Check bot token permissions
   - Ensure bot is invited to target channel
   - Verify channel name format (#channel-name)

### Debug Mode
Add debug logging by modifying `src/utils/logger.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Customization

### Adding New Data Sources
1. Create new collector in `src/data_collection/`
2. Implement data collection interface
3. Add to main pipeline in `main.py`

### Modifying Keywords
Edit keyword list in `src/data_processing/content_processor.py`:
```python
self.keywords = [
    "Your new keyword",
    # ... existing keywords
]
```

### Changing Delivery Schedule
Modify schedule in `scheduler.py`:
```python
# Run twice daily
schedule.every().day.at("09:00").do(run_aggregator)
schedule.every().day.at("17:00").do(run_aggregator)
```

## 📝 License

This project is for internal use. Please ensure compliance with all third-party service terms of use.

## 🤝 Contributing

1. Follow the modular architecture
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Test with sample data before production

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review configuration in `.env` file
3. Verify all external service credentials
4. Test individual components separately

## 🔒 Security

**Important**: Never commit sensitive files to GitHub:
- `.env` (contains API keys)
- `credentials.json` (Google OAuth credentials)
- `token.json` (OAuth tokens)
- `logs/` (may contain sensitive data)

These files are already included in `.gitignore`.