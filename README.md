# Telegram group history exporter [![Run Tests](https://github.com/eugenetaranov/telegram_history/actions/workflows/test.yml/badge.svg)](https://github.com/eugenetaranov/telegram_history/actions/workflows/test.yml)

A Python application to fetch and export Telegram group messages to JSON or CSV formats.

## Setup

### Prerequisites
- Python 3.8+
- Telegram account

### 1. Get Telegram API Credentials

1. Visit [my.telegram.org/apps](https://my.telegram.org/apps)
2. Login with your Telegram account
3. Create a new application
4. Note your `api_id` and `api_hash`

### 2. Create .env File

Create a `.env` file in the project root directory with:

```
API_ID=your_api_id
API_HASH=your_api_hash
APP_NAME=your_app_name
```

### 3. Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python main.py --group "GROUP_NAME" --day "YYYY-MM-DD" --format json
```

### Common Options:

- `--group`: Telegram group name or ID
- `--day`: Single day to fetch (format: YYYY-MM-DD)
- `--start`/`--end`: Date range (format: YYYY-MM-DD)
- `--format`: Output format (json or csv)
- `--output`: Output directory (default: history)
- `--limit`: Maximum number of messages to fetch
- `--debug`: Enable debug logging

### Note on Telegram Sessions

When you run this application for the first time, Telethon will create a local `.session` file storing your login data. Keep this file secure to protect your credentials, and do not commit it to version control.

## Examples

Fetch messages from a specific day:
```bash
python main.py --group "MyGroup" --day "2023-01-01" --format csv
```

Fetch messages for a date range:
```bash
python main.py --group "MyGroup" --start "2023-01-01" --end "2023-01-31" --format json
```

### Running Tests
To run the tests, use:

```bash
pip install -r tests/requirements.txt
pytest tests/
```
