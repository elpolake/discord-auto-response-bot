import discord
from discord import DMChannel, GroupChannel
import threading
import time
import logging

from config import config_manager
from error_handling import safe_query
from api_client import OllamaClient
from gui import BotGUI


logging.basicConfig(level=logging.INFO)


class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.api_client = OllamaClient(config_manager.config["api_url"])
        self.selected_channels = set(
            int(c) for c in config_manager.config.get("selected_channels", [])
        )
        self.last_reply_time = 0
        self.cooldown_seconds = config_manager.config.get("cooldown_seconds", 60)
        self.root = None
        self.gui = None

    async def setup_hook(self):
        await self.api_client.setup()

    async def close(self):
        await self.api_client.cleanup()
        await super().close()

    async def on_ready(self):
        logging.info(f"✅ Logged in as {self.user} (ID: {self.user.id})")

        def start_gui():
            try:
                logging.info("🖥️ Starting GUI...")
                self.gui = BotGUI(self)
                self.root = self.gui.root
                self.gui.run()
                logging.info("✅ GUI event loop running")
            except Exception as e:
                logging.error(f"❌ Failed to start GUI: {str(e)}")

        threading.Thread(target=start_gui, daemon=True).start()

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        if message.author.bot:
            return

        if not isinstance(message.channel, (DMChannel, GroupChannel)):
            return

        if message.channel.id not in self.selected_channels:
            logging.info("⚠️ Channel not selected for auto-reply")
            return

        current_time = time.time()
        if current_time - self.last_reply_time < self.cooldown_seconds:
            logging.info("⏳ Still in cooldown period, skipping")
            return

        self.last_reply_time = current_time

        try:
            last_msg = None
            async for msg in message.channel.history(limit=1):
                last_msg = msg
                break

            if last_msg is None:
                logging.warning("⚠️ No messages found in channel")
                return

            prompt_template = config_manager.config.get(
                "bot_prompt",
                "You are a chatbot. Respond to this message: "
            )

            prompt = f"{prompt_template}\nMessage: {last_msg.content}"

            logging.info(f"🔥 Generating reply to message: {last_msg.content}")

            response = await safe_query(self.api_client, prompt)

            if response:
                await last_msg.reply(response)
                logging.info("✅ Reply sent successfully")
            else:
                await last_msg.reply("Couldn't think of a reply. 😤")
                logging.warning("⚠️ No response from API")

        except Exception as e:
            logging.error(f"❌ Error during message handling: {str(e)}")


