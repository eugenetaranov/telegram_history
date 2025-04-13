"""
Unit tests for the TelegramGroup class.

This module contains tests to verify the functionality of the TelegramGroup class,
including its ability to fetch and process message history from a Telegram group.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest

# Add parent directory to path so Python can find main module
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__)))) # pylint: disable=wrong-import-position
from main import TelegramGroup


@pytest.mark.asyncio
async def test_tg_group_fetch_history():
    """
    Tests the `fetch_history` method of the `TelegramGroup` class.

    Verifies that:
    - Messages within the specified date range are fetched correctly.
    - Messages outside the date range are excluded.
    - The content and metadata of fetched messages match the expected values.
    """
    start_date = datetime(2025, 3, 31, 12, 0, tzinfo=timezone.utc)
    end_date = datetime(2025, 4, 1, 12, 0, tzinfo=timezone.utc)

    mock_client = AsyncMock()
    group = TelegramGroup(mock_client, "TestGroup")

    # Create multiple test messages with different content
    test_messages = [
        {
            "id": 1,
            "date": start_date + timedelta(minutes=45),
            "sender_id": 12345,
            "username": "user1",
            "reply_to_msg_id": None,
            "message": "Hello world",
        },
        {
            "id": 2,
            "date": start_date + timedelta(minutes=60),
            "sender_id": 67890,
            "username": "user2",
            "reply_to_msg_id": 1,
            "message": "Reply to first message",
        },
        {
            "id": 3,
            "date": start_date + timedelta(minutes=90),
            "sender_id": 12345,
            "username": "user1",
            "reply_to_msg_id": None,
            "message": "Test message 3",
        },
        {
            "id": 4,
            "date": end_date - timedelta(minutes=1),
            "sender_id": 12345,
            "username": "user1",
            "reply_to_msg_id": None,
            "message": "Test message 4",
        },
        {
            "id": 5,
            "date": end_date + timedelta(minutes=1),
            "sender_id": 12345,
            "username": "user1",
            "reply_to_msg_id": None,
            "message": "Test message 5",
        },
    ]

    mock_messages = []
    for msg in test_messages:
        mock_msg = AsyncMock()
        mock_msg.id = msg["id"]
        mock_msg.date = msg["date"]
        mock_msg.sender_id = msg["sender_id"]
        mock_msg.sender = AsyncMock()
        mock_msg.sender.username = msg["username"]
        mock_msg.reply_to_msg_id = msg["reply_to_msg_id"]
        mock_msg.message = msg["message"]
        mock_messages.append(mock_msg)

    # Create an async generator to yield all messages
    async def mock_iter_messages(*args, **kwargs):  # pylint: disable=unused-argument
        for msg in mock_messages:
            yield msg

    # Replace the method with our custom function
    mock_client.iter_messages = mock_iter_messages

    await group.fetch_history(
        start_date=start_date,
        end_date=end_date,
    )

    # Verify the number of messages
    assert len(group.history) == len(test_messages) - 1

    # Verify specific message content
    assert group.history[0].message == test_messages[0]["message"]
    assert group.history[1].message == test_messages[1]["message"]
    assert group.history[1].reply_to_msg_id == test_messages[1]["reply_to_msg_id"]
    assert group.history[2].sender_username == test_messages[2]["username"]
    assert group.history[-1].id == test_messages[-2]["id"]
