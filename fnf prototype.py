import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog, filedialog, messagebox
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
import cv2

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
    def __init__(self, master):
        super().__init__(master)
        self.title("Coordinate Settings")
        self.geometry("400x400")
        self.configure(bg="#f0f0f0")
        self.master = master
        self.coordinates = self.master.coordinates
        self.selected_index = None
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Listbox to display coordinates
        self.listbox = tk.Listbox(frame, height=10)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Populate the listbox
        self.update_listbox()

        # Buttons Frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        add_button = ttk.Button(buttons_frame, text="Add", command=self.add_coordinate)
        add_button.pack(fill='x', pady=2)

        edit_button = ttk.Button(buttons_frame, text="Edit", command=self.edit_coordinate)
        edit_button.pack(fill='x', pady=2)

        delete_button = ttk.Button(buttons_frame, text="Delete", command=self.delete_coordinate)
        delete_button.pack(fill='x', pady=2)

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for idx, coord in enumerate(self.coordinates):
            display_text = f"{idx + 1}. Key: {coord['key']}, Position: {coord['position']}, Color: {coord['color']}, Type: {coord['dot_type']}"
            self.listbox.insert(tk.END, display_text)

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.selected_index = selection[0]
        else:
            self.selected_index = None

    def add_coordinate(self):
        CoordinateDialog(self, "Add Coordinate")

    def edit_coordinate(self):
        if self.selected_index is not None:
            coord = self.coordinates[self.selected_index]
            CoordinateDialog(self, "Edit Coordinate", self.selected_index, coord)
        else:
            messagebox.showwarning("Edit Coordinate", "Please select a coordinate to edit.")

    def delete_coordinate(self):
        if self.selected_index is not None:
            confirm = messagebox.askyesno("Delete Coordinate", "Are you sure you want to delete this coordinate?")
            if confirm:
                del self.coordinates[self.selected_index]
                self.update_listbox()
        else:
            messagebox.showwarning("Delete Coordinate", "Please select a coordinate to delete.")

class CoordinateDialog(tk.Toplevel):
    def __init__(self, parent, title, index=None, coord=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x300")
        self.configure(bg="#f0f0f0")
        self.parent = parent
        self.index = index
        self.coord = coord
        self.result = None
        self.create_widgets()
        self.grab_set()
        self.focus_set()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Key selection
        key_label = ttk.Label(frame, text="Key:")
        key_label.pack(anchor='w')
        self.key_var = tk.StringVar()
        self.key_dropdown = ttk.Combobox(frame, textvariable=self.key_var, values=list(KEY_CODES.keys()), state="readonly")
        self.key_dropdown.pack(fill='x', pady=5)
        if self.coord:
            self.key_var.set(self.coord['key'])
        else:
            self.key_var.set(list(KEY_CODES.keys())[0])

        # Position inputs
        pos_frame = ttk.Frame(frame)
        pos_frame.pack(fill='x', pady=5)

        x_label = ttk.Label(pos_frame, text="X:")
        x_label.pack(side=tk.LEFT)
        self.x_entry = ttk.Entry(pos_frame)
        self.x_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        y_label = ttk.Label(pos_frame, text="Y:")
        y_label.pack(side=tk.LEFT)
        self.y_entry = ttk.Entry(pos_frame)
        self.y_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        if self.coord:
            self.x_entry.insert(0, str(self.coord['position'][0]))
            self.y_entry.insert(0, str(self.coord['position'][1]))

        # Color selector
        color_label = ttk.Label(frame, text="Color:")
        color_label.pack(anchor='w')
        self.color_button = ttk.Button(frame, text="Choose Color", command=self.choose_color)
        self.color_button.pack(fill='x', pady=5)
        self.selected_color = self.coord['color'] if self.coord else (255, 255, 255)
        self.update_color_button()

        # Dot type
        dot_label = ttk.Label(frame, text="Dot Type:")
        dot_label.pack(anchor='w')
        self.dot_var = tk.StringVar()
        self.dot_dropdown = ttk.Combobox(frame, textvariable=self.dot_var, values=["perfect", "good", "bad"], state="readonly")
        self.dot_dropdown.pack(fill='x', pady=5)
        if self.coord:
            self.dot_var.set(self.coord['dot_type'])
        else:
            self.dot_var.set("perfect")

        # Save and Cancel buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)

        save_button = ttk.Button(buttons_frame, text="Save", command=self.save)
        save_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color, title="Choose Color")
        if color[0]:
            self.selected_color = tuple(map(int, color[0]))
            self.update_color_button()

    def update_color_button(self):
        hex_color = '#{:02x}{:02x}{:02x}'.format(*self.selected_color)
        self.color_button.config(background=hex_color)

    def save(self):
        try:
            key = self.key_var.get()
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            dot_type = self.dot_var.get()
            color = self.selected_color
            coord = {
                'key': key,
                'position': (x, y),
                'color': color,
                'dot_type': dot_type
            }
            if self.index is not None:
                self.parent.coordinates[self.index] = coord
            else:
                self.parent.coordinates.append(coord)
            self.parent.update_listbox()
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numerical values for X and Y.")

class ColorSettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Color Settings")
        self.geometry("300x300")
        self.configure(bg="#f0f0f0")
        self.master = master
        self.coordinates = self.master.coordinates
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Listbox to display keys and their colors
        self.listbox = tk.Listbox(frame, height=10)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.update_listbox()

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Buttons Frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        change_button = ttk.Button(buttons_frame, text="Change Color", command=self.change_color)
        change_button.pack(fill='x', pady=2)

        reset_button = ttk.Button(buttons_frame, text="Reset to Default", command=self.reset_colors)
        reset_button.pack(fill='x', pady=2)

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for coord in self.coordinates:
            key = coord['key']
            color = coord['color']
            display_text = f"Key: {key}, Color: {color}"
            self.listbox.insert(tk.END, display_text)

    def change_color(self):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            coord = self.coordinates[index]
            initial_color = coord['color']
            color = colorchooser.askcolor(initialcolor=initial_color, title=f"Choose Color for Key {coord['key']}")
            if color[0]:
                self.coordinates[index]['color'] = tuple(map(int, color[0]))
                self.update_listbox()
        else:
            messagebox.showwarning("Change Color", "Please select a key to change its color.")

    def reset_colors(self):
        confirm = messagebox.askyesno("Reset Colors", "Are you sure you want to reset all colors to default?")
        if confirm:
            for coord, default_coord in zip(self.coordinates, DEFAULT_COORDINATES):
                coord['color'] = default_coord['color']
            self.update_listbox()

class KeySettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Key Settings")
        self.geometry("300x300")
        self.configure(bg="#f0f0f0")
        self.master = master
        self.coordinates = self.master.coordinates
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Listbox to display keys
        self.listbox = tk.Listbox(frame, height=10)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.update_listbox()

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Buttons Frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        change_button = ttk.Button(buttons_frame, text="Change Key", command=self.change_key)
        change_button.pack(fill='x', pady=2)

        reset_button = ttk.Button(buttons_frame, text="Reset to Default", command=self.reset_keys)
        reset_button.pack(fill='x', pady=2)

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for coord in self.coordinates:
            key = coord['key']
            display_text = f"Action: {key}, Current Key: {key}"
            self.listbox.insert(tk.END, display_text)

    def change_key(self):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            coord = self.coordinates[index]
            new_key = simpledialog.askstring("Change Key", f"Enter new key for {coord['key']}:")
            if new_key and new_key.upper() in KEY_CODES:
                coord['key'] = new_key.upper()
                self.update_listbox()
                # Update the main app's key codes if necessary
            else:
                messagebox.showerror("Invalid Key", "Please enter a valid key (A, S, D, F).")
        else:
            messagebox.showwarning("Change Key", "Please select a key to change.")

    def reset_keys(self):
        confirm = messagebox.askyesno("Reset Keys", "Are you sure you want to reset all keys to default?")
        if confirm:
            for coord, default_coord in zip(self.coordinates, DEFAULT_COORDINATES):
                coord['key'] = default_coord['key']
            self.update_listbox()

class HumanizerSettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Humanizer Settings")
        self.geometry("300x300")
        self.configure(bg="#f0f0f0")
        self.master = master
        self.humanizer_settings = self.master.humanizer_settings
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Reaction Time
        reaction_label = ttk.Label(frame, text="Reaction Time (ms):")
        reaction_label.pack(anchor='w')
        self.reaction_var = tk.DoubleVar(value=self.humanizer_settings.get("reaction_time", 0))
        self.reaction_entry = ttk.Entry(frame, textvariable=self.reaction_var)
        self.reaction_entry.pack(fill='x', pady=5)

        # Random Delay
        delay_label = ttk.Label(frame, text="Random Delay (ms):")
        delay_label.pack(anchor='w')
        self.delay_var = tk.DoubleVar(value=self.humanizer_settings.get("random_delay", 0))
        self.delay_entry = ttk.Entry(frame, textvariable=self.delay_var)
        self.delay_entry.pack(fill='x', pady=5)

        # Miss Chance
        miss_label = ttk.Label(frame, text="Miss Chance (%):")
        miss_label.pack(anchor='w')
        self.miss_var = tk.DoubleVar(value=self.humanizer_settings.get("miss_chance", 0))
        self.miss_entry = ttk.Entry(frame, textvariable=self.miss_var)
        self.miss_entry.pack(fill='x', pady=5)

        # Save and Cancel buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)

        save_button = ttk.Button(buttons_frame, text="Save", command=self.save)
        save_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

    def save(self):
        try:
            reaction_time = float(self.reaction_var.get())
            random_delay = float(self.delay_var.get())
            miss_chance = float(self.miss_var.get())

            if not (0 <= miss_chance <= 100):
                raise ValueError("Miss chance must be between 0 and 100.")

            self.humanizer_settings["reaction_time"] = reaction_time
            self.humanizer_settings["random_delay"] = random_delay
            self.humanizer_settings["miss_chance"] = miss_chance

            messagebox.showinfo("Humanizer Settings", "Settings saved successfully.")
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))

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
        if not self.coordinates:
            messagebox.showerror("Configuration Error", "No coordinates defined. Please set up coordinates first.")
            return

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

        original_width = CAPTURE_AREA[2] - CAPTURE_AREA[0]
        original_height = CAPTURE_AREA[3] - CAPTURE_AREA[1]

        scale_factor = 0.5

        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        scaled_coordinates = []
        for config in self.coordinates:
            scaled_x = int(config['position'][0] * scale_factor)
            scaled_y = int(config['position'][1] * scale_factor)
            scaled_coordinates.append({
                'position': (scaled_x, scaled_y),
                'key': config['key'],
                'color': config['color'],
                'dot_type': config['dot_type']
            })

        min_hold_time = 0.04 if self.mode.get() == "normal" else 0.03
        double_note_threshold = 0.04

        try:
            while self.running:
                image = camera.get_latest_frame()
                if image is None:
                    continue

                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

                current_time = time.time()
                for config in scaled_coordinates:
                    x, y = config['position']
                    key = config['key']
                    target_rgb = config['color']

                    if y < image.shape[0] and x < image.shape[1]:
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
            miss_chance = settings.get("miss_chance", 0)
            if random.random() * 100 >= miss_chance:
                reaction_time = settings.get("reaction_time", 0) / 1000
                random_delay = random.uniform(0, settings.get("random_delay", 0)) / 1000
                time.sleep(reaction_time)
                time.sleep(random_delay)
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
