"""
Simple GUI for updating eBay sales data and generating machine profit reports.
"""

import customtkinter as CTk
import yaml
import json
from pathlib import Path
from tkinter import filedialog

import create_database
import eBay_interface
import aggregate

CTk.set_default_color_theme("blue")


DEFAULT_YAML = {
    "api.ebay.com": {
        "compatability": 719,
        "appid": "",
        "devid": "",
        "certid": "",
        "token": ""
    }
}


class GUI(CTk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aggregation Tool")
        self.geometry("600x400")
        self.minsize(500, 350)
        CTk.set_appearance_mode("dark")

        self.center_window(600, 400)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)

        self.ensure_files_exist()
        self.create_widgets()

        # Settings button (top right)
        self.settings_btn = CTk.CTkButton(
            self, text="⚙️", width=40, height=40, corner_radius=20,
            fg_color="transparent", hover_color=("#3a7ebf", "#2a5d8f"),
            font=CTk.CTkFont(size=20), command=self.open_settings
        )
        self.settings_btn.place(relx=0.95, rely=0.05, anchor="ne")

    def center_window(self, w: int, h: int):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def ensure_files_exist(self):
        if not Path("ebay_sales.db").exists():
            self.status_update("Creating database...")
            create_database.create_db()

        yaml_path = Path("ebay.yaml")
        if not yaml_path.exists():
            self.status_update("Creating ebay.yaml...")
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(DEFAULT_YAML, f, default_flow_style=False, sort_keys=False)

    def status_update(self, text: str):
        if hasattr(self, "status"):
            self.status.configure(text=text)
            self.update_idletasks()

    def create_widgets(self):
        CTk.CTkLabel(
            self, text="Aggregation Tool",
            font=CTk.CTkFont(size=32, weight="bold")
        ).grid(row=0, column=0, pady=(40, 20), sticky="nsew")

        CTk.CTkButton(
            self, text="Update Info", command=self.update_info,
            height=50, font=CTk.CTkFont(size=18, weight="bold"), corner_radius=12
        ).grid(row=1, column=0, padx=100, pady=10, sticky="ew")

        CTk.CTkButton(
            self, text="Create File", command=self.create_file,
            height=50, font=CTk.CTkFont(size=18, weight="bold"), corner_radius=12
        ).grid(row=2, column=0, padx=100, pady=10, sticky="ew")

        self.status = CTk.CTkLabel(
            self, text="Ready", font=CTk.CTkFont(size=16, weight="bold")
        )
        self.status.grid(row=3, column=0, pady=(20, 40), sticky="nsew")

    def update_info(self):
        config = self.load_yaml_config()
        required = {"appid", "devid", "certid", "token"}
        missing = required - {k for k, v in config.items() if v}

        if missing:
            self.status.configure(text=f"Missing: {', '.join(missing)}")
            CTk.CTkMessagebox(
                title="eBay Credentials Required",
                message=f"Missing fields:\n\n{', '.join(missing)}\n\n"
                        "Please fill them in Settings → eBay API tab.",
                icon="warning"
            )
            return

        self.status_update("Updating from eBay...")
        try:
            eBay_interface.main()
            self.status_update("Info Updated.")
        except Exception as e:
            self.status_update(f"Error: {e}")

    def create_file(self):
        self.status_update("Creating report...")
        try:
            aggregate.main(parent=self)
            self.status_update("Report Created.")
        except Exception as e:
            self.status_update(f"Error: {e}")

    def load_yaml_config(self) -> dict:
        path = Path("ebay.yaml")
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("api.ebay.com", {})

    def save_yaml_config(self, api_config: dict):
        with open("ebay.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump({"api.ebay.com": api_config}, f,
                           default_flow_style=False, sort_keys=False)

    def open_settings(self):
        # ── Settings window ───────────────────────────────────────
        win = CTk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("720x580")
        win.resizable(False, False)
        win.grab_set()
        win.transient(self)

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 360
        y = self.winfo_y() + (self.winfo_height() // 2) - 290
        win.geometry(f"+{x}+{y}")

        tabs = CTk.CTkTabview(win)
        tabs.pack(fill="both", expand=True, padx=20, pady=20)

        tab_api = tabs.add("eBay API")
        tab_stop = tabs.add("Stop Words")

        # API tab
        CTk.CTkLabel(tab_api, text="eBay API Configuration",
                     font=CTk.CTkFont(size=18, weight="bold")).pack(pady=15)

        api_frame = CTk.CTkFrame(tab_api)
        api_frame.pack(padx=20, pady=10, fill="both", expand=True)

        config = self.load_yaml_config()
        entries = {}
        fields = [("appid", "App ID"), ("devid", "Dev ID"),
                  ("certid", "Cert ID"), ("token", "Auth Token")]

        for key, label in fields:
            row = CTk.CTkFrame(api_frame)
            row.pack(fill="x", padx=20, pady=10)
            CTk.CTkLabel(row, text=label + ":", width=130, anchor="w").pack(side="left")
            show = "*" if key == "token" else ""
            entry = CTk.CTkEntry(row, width=350, show=show)
            entry.pack(side="right", padx=(10, 0))
            if key != "token":
                entry.insert(0, config.get(key, ""))
            entries[key] = entry

        # Stop words tab
        CTk.CTkLabel(tab_stop, text="Stop Words Management",
                     font=CTk.CTkFont(size=18, weight="bold")).pack(pady=15)

        stop_frame = CTk.CTkFrame(tab_stop)
        stop_frame.pack(padx=20, pady=10, fill="both", expand=True)

        current_words = self._load_stop_words_for_display()

        display_frame = CTk.CTkFrame(stop_frame)
        display_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        text = CTk.CTkTextbox(display_frame, wrap="none")
        text.pack(side="left", fill="both", expand=True)

        scroll = CTk.CTkScrollbar(display_frame, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set, state="disabled")

        def refresh_display():
            text.configure(state="normal")
            text.delete("1.0", "end")
            for w in sorted(current_words):
                text.insert("end", w + "\n")
            text.configure(state="disabled")

        refresh_display()

        # Controls
        ctrl = CTk.CTkFrame(stop_frame)
        ctrl.pack(pady=10)

        entry = CTk.CTkEntry(ctrl, width=300, placeholder_text="Type a stop word (e.g. grill)")
        entry.pack(side="left", padx=10)

        def add():
            word = entry.get().strip().upper()
            if word and word not in current_words:
                current_words.append(word)
                current_words.sort()
                refresh_display()
            entry.delete(0, "end")

        def remove():
            word = entry.get().strip().upper()
            if word in current_words:
                current_words.remove(word)
                refresh_display()
            entry.delete(0, "end")

        CTk.CTkButton(ctrl, text="Add", width=100, command=add).pack(side="left", padx=5)
        CTk.CTkButton(ctrl, text="Remove", width=100, command=remove).pack(side="left", padx=5)

        # Save / Cancel
        btns = CTk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=20)

        def save():
            api_data = {k: e.get().strip() for k, e in entries.items()}
            api_data = {k: v for k, v in api_data.items() if v}
            self.save_yaml_config(api_data)

            with open("stop_words.json", "w", encoding="utf-8") as f:
                json.dump(sorted(current_words), f, indent=2)

            self.status.configure(text="Settings saved.")
            win.destroy()

        CTk.CTkButton(btns, text="Save All", width=140, command=save).pack(side="left", padx=20)
        CTk.CTkButton(btns, text="Cancel", width=140, command=win.destroy).pack(side="right", padx=20)

    def _load_stop_words_for_display(self) -> list[str]:
        path = Path("stop_words.json")
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return sorted(w.strip().upper() for w in json.load(f) if w.strip())
        return []


if __name__ == "__main__":
    app = GUI()
    app.mainloop()