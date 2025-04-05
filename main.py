#!/usr/bin/env python

import os
import asyncio
from telethon import TelegramClient
from dotenv import dotenv_values
from datetime import datetime, timedelta, timezone


def load_config():
    config = dotenv_values(".env")

    if not config.get("API_ID") or not config.get("API_HASH") or not config.get("APP_NAME"):
        raise ValueError("API_ID, API_HASH, and APP_NAME must be set in the .env file")

    return config


class TelegramGroup:
    def __init__(self, client: TelegramClient, group_name: str):
        self.client = client
        self.group_name = group_name

    async def fetch_history(self, start_date: datetime, end_date: datetime = None, limit: int = None):
        """
        Fetches the message history of a Telegram group.
        :param start_date:
        :param end_date:
        :param limit:
        :return:
        messages: List[Dict[str, Any]]
        """
        messages = []
        async for message in self.client.iter_messages(
                self.group_name,
                offset_date=start_date,
                limit=limit,
                wait_time=1,
        ):

            if end_date and message.date > end_date:
                break

            sender = await self.client.get_entity(message.sender_id)
            peer_id = message.peer_id.channel_id if message.peer_id else None
            message_info = {
                "id": message.id,
                "peer_id": peer_id,
                "date": message.date,
                "date_str": message.date.isoformat(),
                "message": message.message,
                "sender_id": message.sender_id,
                "sender_username": sender.username,
                "from_id": message.from_id,
                "reply_to_msg_id": message.reply_to_msg_id,
                "media": message.media,
                "entities": message.entities,
                "views": message.views,
                "forwards": message.forwards,
                "replies": message.replies,
                "edit_date": message.edit_date,
                "post_author": message.post_author,
                "grouped_id": message.grouped_id,
            }
            messages.append(message_info)
        return messages


async def main():
    config = load_config()

    async with TelegramClient(config["APP_NAME"], int(config["API_ID"]), config["API_HASH"]) as client:
        me = await client.get_me()
        print(f"Welcome back {me.first_name}!")

        tgroup = TelegramGroup(client, config["GROUP_NAME"])
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)
        print(f"Start date: {start_date.isoformat()}, end date: {end_date.isoformat()}")
        messages = await tgroup.fetch_history(start_date, limit=100)

        print(f"Fetched {len(messages)} messages from {config['GROUP_NAME']} group.")

        for message in messages[:5]:
            print(f"Message ID: {message['id']}, Date: {message['date_str']}, Sender: {message['sender_username']}, Message: {message['message']}")


if __name__ == "__main__":
    asyncio.run(main())
