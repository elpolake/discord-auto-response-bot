import tkinter as tk
from tkinter import ttk, messagebox
import discord
from config import config_manager


class BotGUI:
    def __init__(self, bot):
        self.bot = bot
        self.root = tk.Tk()
        self.root.title("Discord Selfbot - Auto Reply Config")

        self.checkbox_vars = {}
        self.chat_checkbuttons = {}
        self.known_chat_ids = set()  # Track already known chat IDs

        self.setup_gui()
        self.root.after(10000, self.refresh_chats)

    def setup_gui(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Select chats to auto-reply in:", font=('Helvetica', 12)).pack(anchor='w')

        select_all_button = ttk.Button(frame, text="Select All DMs", command=self.select_all_dms)
        select_all_button.pack(pady=(0, 5))

        # Auto-select new DMs checkbox
        self.auto_select_var = tk.BooleanVar(value=config_manager.config.get("auto_select_new_dms", False))
        auto_select_chk = ttk.Checkbutton(
            frame,
            text="Auto-select new DMs",
            variable=self.auto_select_var,
            command=self.on_auto_select_toggle
        )
        auto_select_chk.pack(pady=(0, 10))

        self.canvas = tk.Canvas(frame, height=300)
        self.scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.load_chats()

        cooldown_frame = ttk.Frame(frame)
        cooldown_frame.pack(fill="x", pady=10)

        ttk.Label(cooldown_frame, text="Cooldown between replies (seconds):").pack(side="left")
        self.cooldown_var = tk.IntVar(value=config_manager.config.get("cooldown_seconds", 10))
        cooldown_spin = ttk.Spinbox(cooldown_frame, from_=1, to=3600, textvariable=self.cooldown_var, width=5)
        cooldown_spin.pack(side="left", padx=5)
        cooldown_spin.bind("<FocusOut>", self.on_cooldown_change)
        cooldown_spin.bind("<Return>", self.on_cooldown_change)

        prompt_frame = ttk.Frame(frame)
        prompt_frame.pack(fill="both", expand=True, pady=10)

        ttk.Label(prompt_frame, text="Bot prompt/personality:").pack(anchor="w")
        self.prompt_text = tk.Text(prompt_frame, height=5, wrap="word")
        self.prompt_text.pack(fill="both", expand=True)
        self.prompt_text.insert("1.0", config_manager.config.get("bot_prompt", ""))
        self.prompt_text.bind("<FocusOut>", self.on_prompt_change)

        save_button = ttk.Button(frame, text="Save Configuration", command=self.save_config)
        save_button.pack(pady=10)

    def load_chats(self):
        current_chats = self.get_chats()
        to_remove = [ch_id for ch_id in self.checkbox_vars if ch_id not in {ch[0] for ch in current_chats}]
        for ch_id in to_remove:
            self.chat_checkbuttons[ch_id].destroy()
            del self.chat_checkbuttons[ch_id]
            del self.checkbox_vars[ch_id]
            self.known_chat_ids.discard(ch_id)

        auto_selected_any = False

        for ch_id, ch_name in current_chats:
            if ch_id not in self.checkbox_vars:
                var = tk.BooleanVar(value=ch_id in config_manager.config.get("selected_channels", []))
                chk = ttk.Checkbutton(self.scrollable_frame, text=ch_name, variable=var)
                chk.pack(anchor="w", pady=1)
                self.checkbox_vars[ch_id] = var
                self.chat_checkbuttons[ch_id] = chk

                if self.auto_select_var.get():
                    if ch_id not in self.known_chat_ids and ch_name.startswith("DM:"):
                        var.set(True)
                        auto_selected_any = True

                self.known_chat_ids.add(ch_id)

        if auto_selected_any:
            # Save immediately to config and update bot's selected_channels
            selected_channels = [ch_id for ch_id, var in self.checkbox_vars.items() if var.get()]
            config_manager.config["selected_channels"] = selected_channels
            config_manager.save_config(config_manager.config)
            self.bot.selected_channels = set(selected_channels)

    def refresh_chats(self):
        self.load_chats()
        self.root.after(10000, self.refresh_chats)

    def get_chats(self):
        chats = []
        for ch in self.bot.private_channels:
            if isinstance(ch, (discord.DMChannel, discord.GroupChannel)):
                if isinstance(ch, discord.DMChannel):
                    name = f"DM: {ch.recipient.name}" if ch.recipient else "DM (unknown recipient)"
                else:
                    name = f"Group: {ch.name if ch.name else ch.id}"
                chats.append((ch.id, name))
        return chats

    def select_all_dms(self):
        for ch_id, var in self.checkbox_vars.items():
            chk_widget = self.chat_checkbuttons[ch_id]
            if chk_widget.cget("text").startswith("DM:"):
                var.set(True)

    def on_cooldown_change(self, event=None):
        new_cooldown = self.cooldown_var.get()
        config_manager.config["cooldown_seconds"] = new_cooldown
        config_manager.save_config(config_manager.config)
        self.bot.cooldown_seconds = new_cooldown
        print(f"Cooldown updated to {new_cooldown} seconds")

    def on_prompt_change(self, event=None):
        new_prompt = self.prompt_text.get("1.0", "end").strip()
        if new_prompt:
            config_manager.config["bot_prompt"] = new_prompt
            config_manager.save_config(config_manager.config)
            print("Bot prompt updated")

    def on_auto_select_toggle(self):
        enabled = self.auto_select_var.get()
        config_manager.config["auto_select_new_dms"] = enabled
        config_manager.save_config(config_manager.config)
        print(f"Auto-select new DMs set to {enabled}")

    def save_config(self):
        selected_channels = [ch_id for ch_id, var in self.checkbox_vars.items() if var.get()]

        if not selected_channels:
            messagebox.showwarning("No selection", "Please select at least one chat to auto-reply.")
            return

        config_manager.config["selected_channels"] = selected_channels
        config_manager.save_config(config_manager.config)
        self.bot.selected_channels = set(selected_channels)

        # Save prompt and cooldown as well
        self.on_cooldown_change()
        self.on_prompt_change()

        messagebox.showinfo("Saved", "Configuration saved successfully.")

    def run(self):
        self.root.mainloop()
