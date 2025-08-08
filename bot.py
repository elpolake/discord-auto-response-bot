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
        self.chat_memory = {}  # Dict[channel_id, List[str]]

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
        # Ignore messages from self or bots
        if message.author.id == self.user.id or message.author.bot:
            return

        # Only listen to DMs or group chats
        if not isinstance(message.channel, (DMChannel, GroupChannel)):
            return

        # Only respond in selected channels
        if message.channel.id not in self.selected_channels:
            logging.info(f"⚠️ Channel {message.channel.id} not selected for auto-reply")
            return

        current_time = time.time()
        if current_time - self.last_reply_time < self.cooldown_seconds:
            logging.info("⏳ Still in cooldown period, skipping reply")
            return

        self.last_reply_time = current_time

        # Update chat memory
        mem = self.chat_memory.setdefault(message.channel.id, [])
        mem.append(f"{message.author.name}: {message.content}")
        if len(mem) > 50:
            mem.pop(0)

        # Compose prompt with memory + current message
        prompt_template = config_manager.config.get(
            "bot_prompt",
            "You are a chatbot. Respond to this message:"
        )
        history_text = "\n".join(mem)
        prompt = (
            f"{prompt_template}\n"
            f"Conversation history:\n{history_text}\n\n"
            f"New message: {message.content}"
        )

        logging.info(f"🔥 Generating reply in channel {message.channel.id}")

        try:
            response = await safe_query(self.api_client, prompt)
            if response:
                await message.reply(response)
                logging.info("✅ Reply sent successfully")
                # Save bot reply to memory as well to keep context
                mem.append(f"{self.user.name}: {response}")
                if len(mem) > 50:
                    mem.pop(0)
            else:
                await message.reply("Couldn't think of a reply. 😤")
                logging.warning("⚠️ No response from API")
        except Exception as e:
            logging.error(f"❌ Error during message handling: {str(e)}")
