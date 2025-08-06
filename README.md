
# Discord Selfbot Chat AI 🤖

A custom Discord selfbot that uses local AI (Ollama with Dolphin 3) to automatically reply in selected DMs or group chats with a configurable prompt and cooldown. Built with `discord.py-self`, `tkinter`, and `aiohttp`.

> ⚠️ This bot is for personal use and only works in **DMs** and **group chats**, not servers. Selfbots are against Discord ToS — use responsibly.

---

## 🛠 Features

- ✅ Automatically replies to selected DMs/group chats
- ⚙️ GUI to select chats, set prompt style, and cooldown
- 🔁 Auto-update for new DMs (no restart required)
- 🧠 AI-driven responses using [Ollama](https://ollama.com/)
- 🖥️ Local-first: works entirely on your machine
- 💾 Configuration is saved and updated automatically

---

## 📦 Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) installed locally
- Dolphin 3 model (`ollama run dolphin3`)
- `pip` packages listed in `requirements.txt`

---

## 🚀 Setup Guide

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/discord-selfbot-ai.git
cd discord-selfbot-ai
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Install Ollama and Dolphin 3

Follow the instructions on [ollama.com](https://ollama.com/download).

Then run this in your terminal:

```bash
ollama run dolphin3
```

Wait for the model to download completely.

---

## ⚙️ Configuration

1. Run the bot once to generate `config.json`:
    ```bash
    python main.py
    ```

2. A GUI will appear. Select chats you want to auto-reply in.

3. Enter your **Discord token** in `config.json`:
```json
{
  "bot_token": "YOUR_DISCORD_TOKEN",
  "api_url": "http://localhost:11434/api/chat",
  "cooldown_seconds": 30,
  "selected_channels": [],
  "prompt": "Reply harshly with a roast.",
  "log_level": "INFO",
  "max_retries": 3
}
```

> 🔐 Keep your token secret. Never share it.

---

## ▶️ Running the Bot

```bash
python main.py
```

The GUI will start. From there, you can:
- Select which chats the bot auto-replies to
- Change the prompt anytime
- Change the cooldown without restarting
- Auto-select new DMs automatically (optional)

---

## 🧠 Prompt Tips

You can make the bot act like:
- A roast bot: `Roast the user in one brutal sentence.`
- A friendly assistant: `Respond helpfully and kindly.`
- A character: `You are a sarcastic anime villain. Respond as them.`

---

## 📄 License

This project is licensed under the MIT License.
