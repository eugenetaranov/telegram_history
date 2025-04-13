#!/usr/bin/env python
import csv
import json
import os
import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from loguru import logger
from telethon import TelegramClient
from dotenv import dotenv_values


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
        "--format",
        type=str,
        choices=["json", "csv"],
        default="json",
        help="Output format: json or csv.",
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


@dataclass
class Message:
    id: int
    date: datetime
    date_str: str
    sender_id: int
    sender_username: str
    reply_to_msg_id: int
    message: str


class TelegramGroup:
    def __init__(self, client: TelegramClient, group_name: str):
        self.client = client
        self.group_name = group_name
        self.history = []

    async def _find_message_id(
        self,
        start_date: datetime,
        end_date: datetime,
        find_min_id: bool = False,
        find_max_id: bool = False,
    ):
        """
        Finds the message ID closest to the start_date or end_date.
        :param start_date:
        :param end_date:
        :param find_min_id:
        :param find_max_id:
        :return:
        """
        if find_min_id:
            min_id = None
            async for message in self.client.iter_messages(
                self.group_name, reverse=True, offset_date=start_date
            ):
                if start_date <= message.date < end_date:
                    min_id = message.id
                    logger.info(
                        f"Found first message at/after start_date: {message.date}, ID: {min_id}"
                    )
                    break
                await asyncio.sleep(1)

            return min_id

        if find_max_id:
            max_id = None
            async for message in self.client.iter_messages(
                self.group_name, offset_date=end_date
            ):
                if message.date < end_date:
                    max_id = message.id
                    logger.info(
                        f"Found last message before end_date: {message.date}, ID: {max_id}"
                    )
                    break
                await asyncio.sleep(1)

            return max_id

        raise ValueError("Either min_id or max_id must be True")

    async def fetch_history(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = None,
    ):
        """
        Fetches the message history of a Telegram group.
        :param end_date:
        :param start_date:
        :param limit:
        :return:
        """
        min_id = await self._find_message_id(
            start_date=start_date,
            end_date=end_date,
            find_min_id=True,
        )

        max_id = await self._find_message_id(
            start_date=start_date,
            end_date=end_date,
            find_max_id=True,
        )

        if not min_id or not max_id:
            logger.warning(
                "Could not establish message ID range - there may be no messages in this period"
            )
            return []

        logger.info(
            f"Fetching messages between IDs {min_id} and {max_id}, "
            f"up to {max_id - min_id + 1} messages."
        )

        self.history = []
        async for message in self.client.iter_messages(
            self.group_name,
            min_id=min_id,
            max_id=max_id + 1,
            limit=limit,
            reverse=True,  # old messages are fetched first
        ):
            if start_date <= message.date < end_date:
                message_obj = Message(
                    id=message.id,
                    date=message.date,
                    date_str=message.date.isoformat(),
                    sender_id=message.sender_id,
                    sender_username=message.sender.username if message.sender else None,
                    reply_to_msg_id=message.reply_to_msg_id,
                    message=message.message,
                )

                logger.debug(f"Fetched message: {message_obj}")

                self.history.append(message_obj)

            else:
                logger.warning(
                    f"Message date {message.date} is outside the specified range"
                )
                continue

            await asyncio.sleep(1)

    def save_json(self, file_path: str):
        """
        Saves the fetched messages to a JSON file.
        :param file_path:
        :return:
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, default=str, ensure_ascii=False, indent=2)

        logger.info(f"Successfully saved {len(self.history)} messages to {file_path}")

    def save_csv(self, file_path: str):
        """
        Saves the fetched messages to a CSV file.
        :param file_path:
        :return:
        """
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["id", "date", "sender_id", "sender_username", "reply_to", "message"]
            )
            for msg in self.history:
                sanitized_message = msg.message.replace("\n", " ").replace("\r", "")
                writer.writerow(
                    [
                        msg.id,
                        msg.date_str,
                        msg.sender_id,
                        msg.sender_username,
                        msg.reply_to_msg_id,
                        sanitized_message,
                    ]
                )

        logger.info(f"Successfully saved {len(self.history)} messages to {file_path}")


def get_date_range(args):
    if args.day:
        start_date = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
    else:
        if not args.start:
            logger.error("Either --day or --start must be provided")
            return None, None
        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            end_date = datetime.now(timezone.utc)
    return start_date, end_date


def get_output_file(output_dir, group_name, start_date, end_date, file_format):
    group_name = group_name.lower().replace(" ", "_")
    output_dir = str(os.path.join(output_dir, group_name))
    os.makedirs(output_dir, exist_ok=True)

    if file_format == "csv":
        filename = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv"
    elif file_format == "json":
        filename = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.json"
    else:
        raise ValueError("Invalid format specified. Use 'json' or 'csv'.")

    return os.path.join(output_dir, filename)


async def main():
    args = parse_args()
    config = load_config()

    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.debug else "INFO")

    start_date, end_date = get_date_range(args)
    if not start_date or not end_date:
        return

    async with TelegramClient(
        config["APP_NAME"], int(config["API_ID"]), config["API_HASH"]
    ) as client:
        logger.info(
            f"Fetching messages from {args.group} between {start_date} and {end_date}"
        )

        output_file = get_output_file(args.output, args.group, start_date, end_date, args.format)
        if os.path.exists(output_file):
            logger.warning(f"Output file {output_file} already exists. Overwriting.")

        tg_group = TelegramGroup(client=client, group_name=args.group)
        await tg_group.fetch_history(start_date, end_date, limit=args.limit)

        if args.format == "csv":
            logger.info("Saving messages in CSV format.")
            tg_group.save_csv(output_file)
        else:
            logger.info("Saving messages in JSON format.")
            tg_group.save_json(output_file)


if __name__ == "__main__":
    asyncio.run(main())
