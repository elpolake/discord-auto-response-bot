import discord
import threading
import time
import logging
import json
from pathlib import Path
from typing import Dict, Any

from config import config_manager
from error_handling import safe_query
from api_client import OllamaClient
from gui import BotGUI

logging.basicConfig(level=logging.INFO)


class DiscordBot(discord.Client):
    MEMORY_FILE = Path("context_memory.json")  # only store distilled facts now

    def __init__(self):
        super().__init__()
        self.api_client = OllamaClient(config_manager.config["api_url"])
        self.selected_channels = set(
            int(c) for c in config_manager.config.get("selected_channels", [])
        )
        self.last_reply_times = {}
        self.cooldown_seconds = config_manager.config.get("cooldown_seconds", 60)
        self.root = None
        self.gui = None

        self.context_memory = self.load_memory()  # Distilled facts only

    def load_memory(self) -> Dict[str, Any]:
        if self.MEMORY_FILE.exists():
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load context memory: {e}")
        return {}

    def save_memory(self):
        try:
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.context_memory, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save context memory: {e}")

    async def setup_hook(self):
        await self.api_client.setup()

    async def close(self):
        await self.api_client.cleanup()
        await super().close()

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

        def start_gui():
            try:
                logging.info("Starting GUI...")
                self.gui = BotGUI(self)
                self.root = self.gui.root
                self.gui.run()
                logging.info("GUI event loop running")
            except Exception as e:
                logging.error(f"Failed to start GUI: {str(e)}")

        threading.Thread(target=start_gui, daemon=True).start()

    async def update_memory_with_ai(self, entity_key: str, new_message: str, existing_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask the AI what important facts to remember for a single person.
        AI should respond with a JSON object of facts for that person only.
        """
        existing_facts_str = json.dumps(existing_facts, indent=2)

        prompt = (
            "You are an assistant that keeps track of important facts about one person in a conversation. "
            "You have existing facts stored as JSON:\n"
            f"{existing_facts_str}\n\n"
            "A new message from them arrives:\n"
            f"\"{new_message}\"\n\n"
            "Update the facts JSON with any new or changed important information "
            "(like name, preferences, relationships, ongoing topics, etc.). "
            "Respond ONLY with the updated JSON object, no extra text."
        )

        try:
            response_text = await safe_query(self.api_client, prompt)
            if not response_text:
                return existing_facts

            try:
                updated_facts = json.loads(response_text)
                if isinstance(updated_facts, dict):
                    return updated_facts
                else:
                    logging.warning("AI did not return a JSON object, ignoring update.")
                    return existing_facts
            except json.JSONDecodeError:
                logging.warning("Failed to parse AI memory update as JSON, ignoring update.")
                return existing_facts

        except Exception as e:
            logging.error(f"Error updating memory with AI: {e}")
            return existing_facts

    async def on_message(self, message):
        # Ignore messages from self or bots
        if message.author.id == self.user.id or message.author.bot:
            return

        # Only listen to DMs or group chats
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return

        # Only respond in selected channels (by ID)
        if message.channel.id not in self.selected_channels:
            logging.info(f"Channel {message.channel.id} not selected for auto-reply")
            return

        # Determine human-readable key
        if isinstance(message.channel, discord.DMChannel):
            channel_key = f"DM:{message.channel.recipient.name}"
            person_name = message.channel.recipient.name
        elif isinstance(message.channel, discord.GroupChannel):
            group_name = message.channel.name or ", ".join(m.name for m in message.channel.recipients)
            channel_key = f"Group:{group_name}"
            person_name = message.author.name
        else:
            return

        # Check cooldown
        last_time = self.last_reply_times.get(channel_key, 0)
        if time.time() - last_time < self.cooldown_seconds:
            logging.info(f"Cooldown active for {channel_key}")
            return
        self.last_reply_times[channel_key] = time.time()

        # Initialize group structure if needed
        if channel_key not in self.context_memory:
            self.context_memory[channel_key] = {} if isinstance(message.channel, discord.GroupChannel) else {}

        # Select the memory slot for the current person
        if isinstance(message.channel, discord.GroupChannel):
            person_facts = self.context_memory[channel_key].get(person_name, {})
        else:
            person_facts = self.context_memory[channel_key]

        # Update only that person’s facts
        updated_facts = await self.update_memory_with_ai(channel_key, message.content, person_facts)

        if isinstance(message.channel, discord.GroupChannel):
            self.context_memory[channel_key][person_name] = updated_facts
        else:
            self.context_memory[channel_key] = updated_facts

        self.save_memory()

        # Build prompt
        if isinstance(message.channel, discord.GroupChannel):
            known_facts_str = json.dumps(updated_facts, indent=2) if updated_facts else "No known facts yet."
            prompt_template = config_manager.config.get(
                "bot_prompt",
                "You are a chatbot in a group chat. Respond to this message:"
            )
        else:
            known_facts_str = json.dumps(updated_facts, indent=2) if updated_facts else "No known facts yet."
            prompt_template = config_manager.config.get(
                "bot_prompt",
                "You are a chatbot. Respond to this message:"
            )

        prompt = (
            f"{prompt_template}\n\n"
            f"Known facts about {person_name}:\n{known_facts_str}\n\n"
            f"{person_name}: {message.content}"
        )

        logging.info(f"Generating reply for {channel_key} ({person_name})")

        try:
            response = await safe_query(self.api_client, prompt)
            if response:
                await message.reply(response)
                logging.info("Reply sent successfully")
            else:
                await message.reply("Sorry, I couldn't come up with a reply.")
                logging.warning("No response from AI")

        except Exception as e:
            logging.error(f"Error sending reply: {e}")
