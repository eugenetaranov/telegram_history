#!/usr/bin/env python
import json
import os
import argparse
import asyncio
import sys

from loguru import logger
from telethon import TelegramClient
from dotenv import dotenv_values
from datetime import datetime, timedelta, timezone


# generate argparse func with these args - tg group name, start date, end date
def parse_args():
    parser = argparse.ArgumentParser(description="Fetch messages from a Telegram group.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("--group", type=str, help="The name of the Telegram group.")
    parser.add_argument("--start", type=str, help="The start date for fetching messages (YYYY-MM-DD).")
    parser.add_argument("--end", type=str, nargs='?', default=None, help="The end date for fetching messages (YYYY-MM-DD).")
    parser.add_argument("--output", type=str, default="history", help="Directory to save the fetched messages.")
    parser.add_argument("--limit", type=int, default=None, help="The number of messages to fetch, default is None (all messages).")
    return parser.parse_args()


def load_config():
    config = dotenv_values(".env")

    if not config.get("API_ID") or not config.get("API_HASH") or not config.get("APP_NAME"):
        raise ValueError("API_ID, API_HASH, and APP_NAME must be set in the .env file")

    return config


class TelegramGroup:
    def __init__(self, client: TelegramClient, group_name: str):
        self.client = client
        self.group_name = group_name
        self.history = []

    async def fetch_history(self, start_date: datetime, end_date: datetime = None, limit: int = None):
        """
        Fetches the message history of a Telegram group.
        :param start_date:
        :param end_date:
        :param limit:
        :return:
        """
        async for message in self.client.iter_messages(
                self.group_name,
                offset_date=start_date,
                limit=limit,
                wait_time=1,
        ):

            if end_date and message.date > end_date:
                break

            # sender = await self.client.get_entity(message.sender_id)
            # peer_id = message.peer_id.channel_id if message.peer_id else None

            # message_info = {
            #     "id": message.id,
            #     "peer_id": peer_id,
            #     "date": message.date,
            #     "date_str": message.date.isoformat(),
            #     "message": message.message,
            #     "sender_id": message.sender_id,
            #     "sender_username": sender.username,
            #     "from_id": message.from_id,
            #     "reply_to_msg_id": message.reply_to_msg_id,
            #     "media": message.media,
            #     "entities": message.entities,
            #     "views": message.views,
            #     "forwards": message.forwards,
            #     "replies": message.replies,
            #     "edit_date": message.edit_date,
            #     "post_author": message.post_author,
            #     "grouped_id": message.grouped_id,
            # }
            # messages.append(message_info)
            # logger.debug(f"Fetched message: {message.to_dict()}")

            self.history.append(message)


async def main():
    args = parse_args()
    config = load_config()

    logger.remove()
    if args.debug:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    async with TelegramClient(config["APP_NAME"], int(config["API_ID"]), config["API_HASH"]) as client:
        me = await client.get_me()

        tgroup = TelegramGroup(client, args.group)

        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            end_date = datetime.now(timezone.utc)

        logger.info(f"Fetching messages from {args.group} group from {start_date} to {end_date if end_date else 'now'}")

        await tgroup.fetch_history(
            start_date=start_date,
            end_date=end_date,
            limit=args.limit,
        )

        messages = tgroup.history

        logger.info(f"Fetched {len(messages)} messages from {config['GROUP_NAME']} group.")

        for message in messages[:5]:
            logger.debug(json.dumps(message.to_dict(), default=str, ensure_ascii=False))

        # Save messages to a file
        output_dir = args.output
        # create sub dir with the group name lowercase
        group_name = args.group.lower().replace(" ", "_")
        output_dir = str(os.path.join(output_dir, group_name))
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
        output_file = os.path.join(output_dir, filename)

        if os.path.exists(output_file):
            logger.warning(f"Output file `{output_file}` already exists. Overwriting.")

        with open(output_file, "w") as f:
            for message in messages:
                message_str = json.dumps(message.to_dict(), default=str, ensure_ascii=False)
                f.write(f"{message_str}\n")


if __name__ == "__main__":
    asyncio.run(main())
