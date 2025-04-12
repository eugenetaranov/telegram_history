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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch messages from a Telegram group."
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("--group", type=str, help="The name of the Telegram group.")
    parser.add_argument(
        "--start", type=str, help="The start date for fetching messages (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--end",
        type=str,
        nargs="?",
        default=None,
        help="The end date for fetching messages (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--day", type=str, help="Fetch messages for a single day (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="history",
        help="Directory to save the fetched messages.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="The number of messages to fetch, default is None (all messages).",
    )
    return parser.parse_args()


def load_config():
    config = dotenv_values(".env")

    if (
        not config.get("API_ID")
        or not config.get("API_HASH")
        or not config.get("APP_NAME")
    ):
        raise ValueError("API_ID, API_HASH, and APP_NAME must be set in the .env file")

    return config


class TelegramGroup:
    def __init__(self, client: TelegramClient, group_name: str):
        self.client = client
        self.group_name = group_name
        self.history = []

    async def fetch_history(
        self, start_date: datetime, end_date: datetime = None, limit: int = None
    ):
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

    async with TelegramClient(
        config["APP_NAME"], int(config["API_ID"]), config["API_HASH"]
    ) as client:
        # Handle date parameters
        if args.day:
            start_date = datetime.strptime(args.day, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            end_date = start_date + timedelta(days=1)

        else:
            if not args.start:
                logger.error("Either --day or --start must be provided")
                return

            start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if args.end:
                end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            else:
                end_date = datetime.now(timezone.utc)

        logger.info(
            f"Fetching messages from {args.group} between {start_date} and {end_date}"
        )

        # Setup output file
        output_dir = args.output
        group_name = args.group.lower().replace(" ", "_")
        output_dir = str(os.path.join(output_dir, group_name))
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.json"
        output_file = os.path.join(output_dir, filename)

        if os.path.exists(output_file):
            logger.warning(f"Output file {output_file} already exists. Overwriting.")

        entity = await client.get_entity(args.group)
        all_messages = []
        total_messages = 0

        # Start by getting the first message after or at our start date
        min_id = None
        max_id = None

        logger.debug(f"Finding initial message ID range for our date window")

        # Find a message at or after start_date to establish min_id
        async for message in client.iter_messages(
            entity, reverse=True, offset_date=start_date
        ):
            if start_date <= message.date < end_date:
                min_id = message.id
                logger.debug(
                    f"Found first message at/after start_date: {message.date}, ID: {min_id}"
                )
                break
            await asyncio.sleep(1)

        # Find a message just before end_date to establish max_id
        async for message in client.iter_messages(entity, offset_date=end_date):
            if message.date < end_date:
                max_id = message.id
                logger.debug(
                    f"Found last message before end_date: {message.date}, ID: {max_id}"
                )
                break
            await asyncio.sleep(0.1)

        if min_id is None or max_id is None:
            logger.warning(
                "Could not establish message ID range - there may be no messages in this period"
            )
            return

        else:
            logger.info(f"Fetching {max_id - min_id + 1} messages between IDs {min_id} and {max_id}")

            with open(output_file, "w", encoding="utf-8") as f:
                # Now fetch all messages in this ID range
                async for message in client.iter_messages(
                    entity,
                    min_id=min_id,
                    max_id=max_id + 1,
                    limit=args.limit,
                ):
                    # Double check the date is in our range
                    if start_date <= message.date < end_date:
                        all_messages.append(message.to_dict())
                        total_messages += 1
                    else:
                        logger.warning(
                            f"Message date {message.date} is outside the specified range"
                        )
                        continue

                    # Log progress periodically
                    if total_messages % 100 == 0 and total_messages > 0:
                        logger.info(f"Processed {total_messages} messages so far")

                    # Be nice to the API
                    await asyncio.sleep(1)

                # Write results
                json.dump(all_messages, f, default=str, ensure_ascii=False, indent=2)

        logger.info(f"Successfully saved {total_messages} messages to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
