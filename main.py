# made by polak no one else
# best discord self bot

import asyncio
from bot import DiscordBot
from config import config_manager

async def main():
    token = config_manager.config["bot_token"]

    if not token:
        raise ValueError("Bot token not configured in config.json")

    bot = DiscordBot()
    try:
        await bot.start(token)
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
