import discord
from discord import DMChannel, GroupChannel
import threading
import time
import logging
import json
from pathlib import Path

from config import config_manager
from error_handling import safe_query
from api_client import OllamaClient
from gui import BotGUI


logging.basicConfig(level=logging.INFO)


class DiscordBot(discord.Client):
    MEMORY_FILE = Path("chat_memory.json")

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
        self.chat_memory = self.load_memory()  # Dict[channel_id, List[str]]

    def load_memory(self):
        if self.MEMORY_FILE.exists():
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load memory: {e}")
        return {}

    def save_memory(self):
        try:
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.chat_memory, f, indent=2)
        except Exception as e:
            print(f"Failed to save memory: {e}")


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
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
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

        channel_id = str(message.channel.id)
        if channel_id not in self.chat_memory:
            self.chat_memory[channel_id] = []

        # Append new message to chat memory
        self.chat_memory[channel_id].append({
            "author": message.author.name,
            "content": message.content,
            "timestamp": message.created_at.isoformat()
        })


        max_messages = config_manager.config.get("max_saved_messages", 50)

        if len(self.chat_memory[channel_id]) > max_messages:
            self.chat_memory[channel_id] = self.chat_memory[channel_id][-max_messages:]

        self.save_memory()

        # Build the message history text for prompt
        messages_history = "\n".join(
            f"{msg['author']}: {msg['content']}" for msg in self.chat_memory[channel_id]
        )

        prompt_template = config_manager.config.get(
            "bot_prompt",
            "You are a chatbot. Respond to this message:"
        )

        prompt = f"{prompt_template}\nChat history:\n{messages_history}\nUser: {message.content}"

        logging.info(f"🔥 Generating reply in channel {message.channel.id}")

        try:
            response = await safe_query(self.api_client, prompt)
            if response:
                await message.reply(response)
                logging.info("✅ Reply sent successfully")

                # Save bot reply in memory
                self.chat_memory[channel_id].append({
                    "author": self.user.name,
                    "content": response,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                })

                # Trim again if over 50
                if len(self.chat_memory[channel_id]) > 50:
                    self.chat_memory[channel_id] = self.chat_memory[channel_id][-50:]

                self.save_memory()
            else:
                await message.reply("Couldn't think of a reply. 😤")
                logging.warning("⚠️ No response from API")

        except Exception as e:
            logging.error(f"❌ Error during message handling: {str(e)}")
