import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog, filedialog
import threading
import time
import ctypes
import queue
import numpy as np
from PIL import Image, ImageTk
import json
import random
import traceback
import dxcam

# Constants for key codes
KEY_CODES = {
    'A': 0x1E,
    'S': 0x1F,
    'D': 0x20,
    'F': 0x21,
}

# Screen capture area (left, top, right, bottom)
CAPTURE_AREA = (376, 630, 990, 768)

# Default coordinates and colors for each key
DEFAULT_COORDINATES = [
    {'position': (77, 36), 'key': 'A', 'color': (217, 0, 255), 'dot_type': 'perfect'},
    {'position': (230, 36), 'key': 'S', 'color': (255, 0, 4), 'dot_type': 'perfect'},
    {'position': (383, 36), 'key': 'D', 'color': (255, 0, 4), 'dot_type': 'perfect'},
    {'position': (537, 36), 'key': 'F', 'color': (217, 0, 255), 'dot_type': 'perfect'},
]

# C struct redefinitions for simulating key presses
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class Input_I(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", ctypes.c_ubyte * 28),
        ("hi", ctypes.c_ubyte * 32),
    ]


class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", Input_I),
    ]


def press_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(
        0,
        scan_code,
        0x0008,  # KEYEVENTF_SCANCODE
        0,
        ctypes.pointer(extra),
    )
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(
        0,
        scan_code,
        0x0008 | 0x0002,  # KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
        0,
        ctypes.pointer(extra),
    )
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


class CoordinateSettingsWindow(tk.Toplevel):
    # ... [Rest of the class remains similar, with improvements if needed]
    pass


class ColorSettingsWindow(tk.Toplevel):
    # ... [Rest of the class remains similar, with improvements if needed]
    pass


class KeySettingsWindow(tk.Toplevel):
    # ... [Rest of the class remains similar, with improvements if needed]
    pass


class HumanizerSettingsWindow(tk.Toplevel):
    # ... [Rest of the class remains similar, with improvements if needed]
    pass


class AutoPlayerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rhythm Game Auto Player")
        self.geometry("300x450")
        self.configure(bg="#f0f0f0")
        self.running = False
        self.thread = None
        self.key_queue = queue.Queue()
        self.mode = tk.StringVar(value="normal")
        self.humanizer_settings = {}
        self.coordinates = DEFAULT_COORDINATES.copy()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, text="Auto Player", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Mode selection
        mode_label = ttk.Label(main_frame, text="Mode:", font=("Arial", 12))
        mode_label.pack(anchor='w')

        mode_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.mode,
            values=["normal", "spammer"],
            state="readonly",
        )
        mode_dropdown.pack(fill='x', pady=(0, 10))
        mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change)

        # Start and Stop buttons
        self.start_button = ttk.Button(
            main_frame, text="Start", command=self.start_script
        )
        self.start_button.pack(fill='x', pady=(0, 5))

        self.stop_button = ttk.Button(
            main_frame, text="Stop", command=self.stop_script, state=tk.DISABLED
        )
        self.stop_button.pack(fill='x', pady=(0, 10))

        self.status_label = ttk.Label(main_frame, text="Status: Idle", font=("Arial", 10))
        self.status_label.pack(pady=(0, 10))

        # Settings buttons
        self.color_settings_button = ttk.Button(
            main_frame, text="Change Colors", command=self.open_color_settings
        )
        self.color_settings_button.pack(fill='x', pady=(0, 5))

        self.key_settings_button = ttk.Button(
            main_frame, text="Change Keys", command=self.open_key_settings
        )
        self.key_settings_button.pack(fill='x', pady=(0, 5))

        self.coordinate_settings_button = ttk.Button(
            main_frame, text="Change Coordinates", command=self.open_coordinate_settings
        )
        self.coordinate_settings_button.pack(fill='x', pady=(0, 5))

        self.humanizer_button = ttk.Button(
            main_frame, text="Humanizer", command=self.open_humanizer_settings
        )
        self.humanizer_button.pack(fill='x', pady=(0, 5))

    def on_mode_change(self, event):
        if self.mode.get() == "spammer":
            self.humanizer_button.config(state="disabled")
        else:
            self.humanizer_button.config(state="normal")

    def open_color_settings(self):
        ColorSettingsWindow(self)

    def open_key_settings(self):
        KeySettingsWindow(self)

    def open_coordinate_settings(self):
        CoordinateSettingsWindow(self)

    def open_humanizer_settings(self):
        HumanizerSettingsWindow(self)

    def start_script(self):
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        self.thread = threading.Thread(target=self.run_script, daemon=True)
        self.thread.start()
        self.key_thread = threading.Thread(target=self.key_handler, daemon=True)
        self.key_thread.start()

    def stop_script(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped")

    def key_handler(self):
        while self.running:
            try:
                action, key = self.key_queue.get(timeout=0.01)
                scan_code = KEY_CODES.get(key)
                if scan_code:
                    if action == "press":
                        press_key(scan_code)
                    elif action == "release":
                        release_key(scan_code)
            except queue.Empty:
                continue

    def run_script(self):
        camera = dxcam.create()
        camera.start(region=CAPTURE_AREA)
        key_states = {key: False for key in KEY_CODES}
        key_hold_times = {key: 0 for key in KEY_CODES}
        key_release_times = {key: 0 for key in KEY_CODES}

        min_hold_time = 0.04 if self.mode.get() == "normal" else 0.03
        double_note_threshold = 0.04

        try:
            while self.running:
                image = camera.get_latest_frame()
                if image is None:
                    continue

                current_time = time.time()
                for config in self.coordinates:
                    x, y = config['position']
                    key = config['key']
                    target_rgb = config['color']
                    pixel = image[y, x]

                    if np.array_equal(pixel, target_rgb):
                        if not key_states[key]:
                            self.handle_key_press(key, current_time, key_states, key_hold_times)
                        elif current_time - key_release_times[key] < double_note_threshold:
                            self.key_queue.put(("release", key))
                            self.key_queue.put(("press", key))
                            key_hold_times[key] = current_time
                        else:
                            key_hold_times[key] = current_time
                    else:
                        if key_states[key]:
                            if current_time - key_hold_times[key] >= min_hold_time:
                                self.key_queue.put(("release", key))
                                key_states[key] = False
                                key_release_times[key] = current_time
                time.sleep(0.001)
        finally:
            for key, state in key_states.items():
                if state:
                    self.key_queue.put(("release", key))
            camera.stop()
            del camera
            self.status_label.config(text="Status: Idle")

    def handle_key_press(self, key, current_time, key_states, key_hold_times):
        if self.humanizer_settings:
            settings = self.humanizer_settings
            if random.random() * 100 > settings.get("miss_chance", 0):
                time.sleep(settings.get("reaction_time", 0) / 1000)
                time.sleep(random.uniform(0, settings.get("random_delay", 0) / 1000))
                self.key_queue.put(("press", key))
                key_states[key] = True
                key_hold_times[key] = current_time
        else:
            self.key_queue.put(("press", key))
            key_states[key] = True
            key_hold_times[key] = current_time


if __name__ == "__main__":
    try:
        app = AutoPlayerApp()
        app.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
