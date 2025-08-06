import tkinter as tk
from tkinter import ttk, messagebox
from config import config_manager

class PromptGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Edit Bot Prompt")

        ttk.Label(self.root, text="Edit bot reply prompt:").pack(padx=10, pady=5)

        self.text = tk.Text(self.root, width=60, height=10)
        self.text.pack(padx=10, pady=5)
        # Load current prompt from config
        self.text.insert("1.0", config_manager.config.get("bot_prompt", ""))

        save_btn = ttk.Button(self.root, text="Save", command=self.save_prompt)
        save_btn.pack(pady=10)

    def save_prompt(self):
        new_prompt = self.text.get("1.0", "end").strip()
        if not new_prompt:
            messagebox.showwarning("Empty Prompt", "Prompt cannot be empty!")
            return

        config_manager.config["bot_prompt"] = new_prompt
        config_manager.save_config(config_manager.config)
        messagebox.showinfo("Saved", "Prompt saved successfully.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()
