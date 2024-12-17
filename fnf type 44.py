import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog, filedialog
import threading
import time
import ctypes
import dxcam
import queue
import numpy as np
from PIL import Image, ImageTk
import json
import random
import traceback

# Key codes for A, S, D, F
KEY_CODES = {
    'A': 0x1E,
    'S': 0x1F,
    'D': 0x20,
    'F': 0x21
}

# Area to capture on the screen
CAPTURE_AREA = (376, 630, 990, 768)

# Default coordinates and target colors for each key
DEFAULT_COORDINATES = [
    {'position': (77, 36), 'key': 'A', 'color': (217, 0, 255), 'dot_type': 'perfect'},
    {'position': (230, 36), 'key': 'S', 'color': (255, 0, 4), 'dot_type': 'perfect'},
    {'position': (383, 36), 'key': 'D', 'color': (255, 0, 4), 'dot_type': 'perfect'},
    {'position': (537, 36), 'key': 'F', 'color': (217, 0, 255), 'dot_type': 'perfect'}
]

# C struct redefinitions for keyboard input
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]


# Functions to simulate key presses
def press_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


class CoordinateSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Coordinate Settings")
        self.geometry("800x600")
        self.parent = parent
        self.canvas = tk.Canvas(self, width=614, height=138)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.coordinates = self.parent.coordinates.copy()
        self.dots = []
        self.create_widgets()

    def create_widgets(self):
        # Take a screenshot of the capture area
        screenshot = self.take_screenshot()
        self.photo = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Draw dots for each coordinate
        for i, coord in enumerate(self.coordinates):
            x, y = coord['position']
            dot = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")
            self.dots.append(dot)
            self.canvas.tag_bind(dot, "<ButtonPress-1>", lambda event, i=i: self.on_dot_press(event, i))
            self.canvas.tag_bind(dot, "<B1-Motion>", lambda event, i=i: self.on_dot_drag(event, i))

        # Buttons to save, load, and use coordinates
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, pady=10)
        ttk.Button(button_frame, text="Save", command=self.save_coordinates).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load", command=self.load_coordinates).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Use", command=self.use_coordinates).pack(side=tk.LEFT, padx=5)

    def take_screenshot(self):
        camera = dxcam.create()
        frame = camera.grab(region=CAPTURE_AREA)
        camera.stop()
        return Image.fromarray(frame)

    def on_dot_press(self, event, index):
        self.selected_dot = index
        self.lastx = event.x
        self.lasty = event.y

    def on_dot_drag(self, event, index):
        dx = event.x - self.lastx
        dy = event.y - self.lasty
        self.canvas.move(self.dots[index], dx, dy)
        self.coordinates[index]['position'] = (
            self.coordinates[index]['position'][0] + dx,
            self.coordinates[index]['position'][1] + dy
        )
        self.lastx = event.x
        self.lasty = event.y

    def save_coordinates(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON files", "*.json")])
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.coordinates, f)

    def load_coordinates(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filename:
            with open(filename, 'r') as f:
                self.coordinates = json.load(f)
            self.update_dots()

    def update_dots(self):
        for i, dot in enumerate(self.dots):
            x, y = self.coordinates[i]['position']
            self.canvas.coords(dot, x - 5, y - 5, x + 5, y + 5)

    def use_coordinates(self):
        self.parent.coordinates = self.coordinates.copy()
        self.destroy()


class ColorSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Color Settings")
        self.geometry("300x200")
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        for key in KEY_CODES.keys():
            button = ttk.Button(main_frame, text=f"Set Color for {key}",
                                command=lambda k=key: self.choose_color(k))
            button.pack(fill=tk.X, pady=5)

    def choose_color(self, key):
        color = colorchooser.askcolor()[0]
        if color:
            rgb_color = tuple(int(c) for c in color)
            for coord in self.parent.coordinates:
                if coord['key'] == key:
                    coord['color'] = rgb_color
                    break


class KeySettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Key Settings")
        self.geometry("300x200")
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        for key in KEY_CODES.keys():
            button = ttk.Button(main_frame, text=f"Set Key for {key}",
                                command=lambda k=key: self.set_key(k))
            button.pack(fill=tk.X, pady=5)

    def set_key(self, old_key):
        new_key = simpledialog.askstring("Input", f"Enter new key for {old_key}:")
        if new_key:
            new_key = new_key.upper()
            scan_code = ord(new_key) - 65 + 0x1E  # Convert letter to scan code
            KEY_CODES[new_key] = scan_code
            del KEY_CODES[old_key]
            for coord in self.parent.coordinates:
                if coord['key'] == old_key:
                    coord['key'] = new_key
                    break


class HumanizerSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Humanizer Settings")
        self.geometry("400x400")
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.settings = {
            'reaction_time': tk.DoubleVar(value=0.1),
            'timing_variance': tk.DoubleVar(value=0.05),
            'miss_chance': tk.DoubleVar(value=0.0),
            'early_chance': tk.DoubleVar(value=0.0),
            'late_chance': tk.DoubleVar(value=0.0),
            'hold_variance': tk.DoubleVar(value=0.05)
        }

        for i, (key, var) in enumerate(self.settings.items()):
            ttk.Label(main_frame, text=f"{key.replace('_', ' ').title()}:").grid(row=i, column=0, sticky="w")
            ttk.Entry(main_frame, textvariable=var).grid(row=i, column=1)

        ttk.Button(main_frame, text="Apply", command=self.apply_settings).grid(row=i+1, column=0, columnspan=2, pady=10)

    def apply_settings(self):
        self.parent.humanizer_settings = {k: v.get() for k, v in self.settings.items()}
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FNF Auto Player")
        self.geometry("300x500")
        self.configure(bg="#f0f0f0")
        self.running = False
        self.key_queue = queue.Queue()
        self.coordinates = DEFAULT_COORDINATES.copy()
        self.humanizer_settings = None
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="Auto Play", font=("Arial", 16, "bold")).pack(pady=10)

        # Mode selection
        self.mode = tk.StringVar(value="Normal")
        ttk.Label(main_frame, text="Select Mode:").pack(anchor="w")
        ttk.Combobox(main_frame, textvariable=self.mode, values=["Normal", "Spammer"], state="readonly").pack(fill=tk.X)

        # Start and Stop buttons
        self.start_button = ttk.Button(main_frame, text="Start", command=self.start_script)
        self.start_button.pack(fill=tk.X, pady=5)
        self.stop_button = ttk.Button(main_frame, text="Stop", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=5)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Status: Idle")
        self.status_label.pack(pady=5)

        # Settings buttons
        ttk.Button(main_frame, text="Coordinate Settings", command=self.open_coordinate_settings).pack(fill=tk.X, pady=5)
        ttk.Button(main_frame, text="Color Settings", command=self.open_color_settings).pack(fill=tk.X, pady=5)
        ttk.Button(main_frame, text="Key Settings", command=self.open_key_settings).pack(fill=tk.X, pady=5)

        # Humanizer settings
        self.humanizer_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Enable Humanizer", variable=self.humanizer_enabled).pack(anchor="w", pady=5)
        ttk.Button(main_frame, text="Humanizer Settings", command=self.open_humanizer_settings).pack(fill=tk.X, pady=5)

    def open_coordinate_settings(self):
        CoordinateSettingsWindow(self)

    def open_color_settings(self):
        ColorSettingsWindow(self)

    def open_key_settings(self):
        KeySettingsWindow(self)

    def open_humanizer_settings(self):
        HumanizerSettingsWindow(self)

    def start_script(self):
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        threading.Thread(target=self.run_script).start()
        threading.Thread(target=self.key_handler).start()

    def stop_script(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped")

    def key_handler(self):
        while self.running:
            try:
                action, key = self.key_queue.get(timeout=0.01)
                scan_code = KEY_CODES[key]
                if action == "press":
                    press_key(scan_code)
                elif action == "release":
                    release_key(scan_code)
            except queue.Empty:
                continue

    def run_script(self):
        camera = dxcam.create()
        camera.start(region=CAPTURE_AREA)
        key_states = {coord['key']: False for coord in self.coordinates}

        try:
            while self.running:
                frame = camera.get_latest_frame()
                if frame is None:
                    continue

                for coord in self.coordinates:
                    x, y = coord['position']
                    key = coord['key']
                    target_color = coord['color']
                    pixel_color = tuple(frame[int(y), int(x)])

                    if pixel_color == target_color:
                        if not key_states[key]:
                            # Apply humanizer settings
                            if self.humanizer_enabled.get() and self.humanizer_settings:
                                delay = self.humanizer_settings.get('reaction_time', 0.1)
                                miss_chance = self.humanizer_settings.get('miss_chance', 0.0)
                                if random.random() > miss_chance:
                                    time.sleep(delay)
                                    self.key_queue.put(("press", key))
                                    key_states[key] = True
                            else:
                                self.key_queue.put(("press", key))
                                key_states[key] = True
                    else:
                        if key_states[key]:
                            self.key_queue.put(("release", key))
                            key_states[key] = False

                time.sleep(0.01)

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
        finally:
            camera.stop()
            self.stop_script()

    def open_humanizer_settings(self):
        HumanizerSettingsWindow(self)


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
