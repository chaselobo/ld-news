import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Slack client
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
channel = os.getenv('SLACK_CHANNEL', '#LD-News')

try:
    # Test message
    response = client.chat_postMessage(
        channel=channel,
        text="🤖 Test message from Leave Delaware News Bot! If you see this, the integration is working."
    )
    print(f"✅ Message sent successfully to {channel}")
    print(f"Message timestamp: {response['ts']}")
    
except SlackApiError as e:
    print(f"❌ Error sending message: {e.response['error']}")
    if e.response['error'] == 'channel_not_found':
        print("💡 Make sure the bot is added to the channel")
    elif e.response['error'] == 'invalid_auth':
        print("💡 Check your SLACK_BOT_TOKEN in .env file")
        
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")