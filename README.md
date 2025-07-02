# Fitness Coach Bot 🏋️‍♂️

A production-ready Telegram accountability bot that helps you track your fitness journey with daily check-ins and weekly recaps. The bot uses Claude AI for intelligent summary generation and stores all data in Google Docs for easy access and review.

## Features

- **Daily Check-ins**: Automated evening prompts at 20:30 Europe/London
- **AI-Powered Summaries**: Claude AI analyzes your responses and creates structured summaries
- **Goal Tracking**: Persistent short-term goal memory with next-day follow-ups
- **Weekly Recaps**: Comprehensive weekly analysis every Sunday at 20:00
- **Google Docs Integration**: All data automatically saved to your personal Google Doc
- **Timezone-Aware**: Properly handles Europe/London timezone for scheduling

## Architecture

```
fitness-coach-bot/
├── bot.py              # Main Telegram bot logic and handlers
├── scheduler.py        # APScheduler jobs for automated tasks
├── claude_api.py       # Claude AI integration for summaries
├── google_docs.py      # Google Docs API integration
├── goal_memory.py      # Goal persistence in JSON
├── config.py           # Configuration and environment variables
├── requirements.txt    # Python dependencies
├── tests/              # Unit tests
└── README.md          # This file
```

## Prerequisites

- Python 3.11 or higher
- Google Cloud Platform account
- Telegram Bot Token
- Claude API key (Anthropic)

## Setup Instructions

### 1. Google Cloud Setup

1. **Create a Google Cloud Project**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Docs API**:

   ```bash
   # Using gcloud CLI
   gcloud services enable docs.googleapis.com
   ```

   Or enable it through the [API Library](https://console.cloud.google.com/apis/library/docs.googleapis.com)

3. **Create Service Account**:

   ```bash
   # Create service account
   gcloud iam service-accounts create fitness-bot-service \
       --display-name="Fitness Bot Service Account"

   # Create and download key
   gcloud iam service-accounts keys create credentials.json \
       --iam-account=fitness-bot-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Create Google Doc**:
   - Create a new Google Doc for your fitness log
   - Share it with the service account email (fitness-bot-service@YOUR_PROJECT_ID.iam.gserviceaccount.com) with Editor access
   - Copy the document ID from the URL: `https://docs.google.com/document/d/DOCUMENT_ID/edit`

### 2. Telegram Bot Setup

1. **Create Telegram Bot**:

   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command to create a new bot
   - Save the bot token provided

2. **Get Your Chat ID**:
   - Start a conversation with your bot
   - Send any message to the bot
   - Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
   - Find your chat ID in the response

### 3. Claude API Setup

1. **Get Claude API Key**:
   - Sign up at [Anthropic Console](https://console.anthropic.com/)
   - Create an API key
   - Note: Claude API requires payment setup

### 4. Installation

1. **Clone and Setup**:

   ```bash
   git clone <your-repo-url>
   cd fitness-coach-bot

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file in the project root:

   ```bash
   # Telegram Configuration
   TELEGRAM_TOKEN=your_telegram_bot_token
   USER_CHAT_ID=your_chat_id_number

   # Claude API Configuration
   CLAUDE_API_KEY=your_claude_api_key
   CLAUDE_MODEL=claude-3-sonnet-20240229

   # Google Docs Configuration
   GOOGLE_DOC_ID=your_google_doc_id
   GOOGLE_CREDENTIALS_PATH=credentials.json

   # Optional Configuration
   TIMEZONE=Europe/London
   MAX_RETRIES=3
   LOG_LEVEL=INFO
   GOAL_MEMORY_FILE=goal_memory.json
   ```

3. **Place Credentials**:
   - Put your `credentials.json` file in the project root
   - Ensure it's not committed to git (already in .gitignore)

### 5. Running the Bot

1. **Development/Testing**:

   ```bash
   # Load environment variables
   export $(cat .env | xargs)  # On Windows: set each variable manually

   # Run the bot
   python bot.py
   ```

2. **Production Deployment**:

   **Option A: systemd (Linux)**:

   ```bash
   # Create service file
   sudo nano /etc/systemd/system/fitness-bot.service
   ```

   ```ini
   [Unit]
   Description=Fitness Coach Bot
   After=network.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/fitness-coach-bot
   Environment=TELEGRAM_TOKEN=your_token
   Environment=USER_CHAT_ID=your_chat_id
   Environment=CLAUDE_API_KEY=your_key
   Environment=GOOGLE_DOC_ID=your_doc_id
   ExecStart=/path/to/fitness-coach-bot/venv/bin/python bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   # Enable and start service
   sudo systemctl enable fitness-bot
   sudo systemctl start fitness-bot
   sudo systemctl status fitness-bot
   ```

   **Option B: Docker**:

   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .
   CMD ["python", "bot.py"]
   ```

## Usage

### Bot Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/daily` - Trigger manual daily check-in
- `/weekly` - Trigger manual weekly recap
- `/status` - Show current bot status

### Automated Schedule

- **Daily Prompts**: Every evening at 20:30 Europe/London
- **Weekly Recaps**: Every Sunday at 20:00 Europe/London

### Daily Check-in Flow

1. Bot sends evening prompt with three questions:

   - How was your workout today?
   - How did you feel about what you ate?
   - Any goals for tomorrow/next few days?

2. You respond with free text

3. Bot processes with Claude AI and returns structured summary

4. Data is saved to Google Docs and goals are stored for tomorrow's check-in

### Weekly Recap Flow

1. Bot analyzes past 7 daily summaries
2. Generates comprehensive weekly statistics
3. Asks for your weekly reflection and next week's goals
4. Saves everything to Google Docs

## Development

### Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio pytest-mock

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/

# Type checking
mypy --strict *.py
```

### Code Quality

The codebase follows these standards:

- **Type Hints**: Full type annotations with `from __future__ import annotations`
- **Docstrings**: All functions and classes documented
- **Error Handling**: Comprehensive exception handling with retries
- **Logging**: Structured logging throughout
- **Testing**: Unit tests for core functionality

## Troubleshooting

### Common Issues

1. **"Google Docs API not enabled"**:

   - Ensure the Docs API is enabled in Google Cloud Console
   - Check service account permissions

2. **"Telegram bot not responding"**:

   - Verify bot token is correct
   - Check USER_CHAT_ID matches your Telegram chat

3. **"Claude API errors"**:

   - Verify API key is valid and has credits
   - Check rate limits and quotas

4. **"Scheduler not working"**:
   - Confirm timezone settings
   - Check system time is correct
   - Verify the bot process is running continuously

### Logs

Check logs for debugging:

```bash
# If running with systemd
sudo journalctl -u fitness-bot -f

# If running directly
tail -f fitness-bot.log
```

## Security Notes

- Never commit API keys or tokens to version control
- Use environment variables for all sensitive configuration
- Restrict Google Cloud service account permissions to minimum required
- Consider using secret management systems in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure code passes `mypy --strict`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Search existing GitHub issues
3. Create a new issue with detailed information

---

**Happy fitness tracking! 💪**
