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
import os
import random
import traceback

# Key codes for A, S, D, F
KEY_A, KEY_S, KEY_D, KEY_F = 0x1E, 0x1F, 0x20, 0x21

# Area to capture on the screen
capture_area = (376, 630, 990, 768)

# Coordinates and target colors for each key
coordinates = [
    ((453 - 376, 666 - 630), KEY_A, (217, 0, 255), 'perfect'),
    ((606 - 376, 666 - 630), KEY_S, (255, 0, 4), 'perfect'),
    ((759 - 376, 666 - 630), KEY_D, (255, 0, 4), 'perfect'),
    ((913 - 376, 666 - 630), KEY_F, (217, 0, 255), 'perfect')
]

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", ctypes.c_ubyte * 28), ("hi", ctypes.c_ubyte * 32)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

# Optimized key press and release functions
SendInput = ctypes.windll.user32.SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)

def press_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

class CoordinateSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Coordinate Settings")
        self.geometry("800x600")
        self.parent = parent
        self.dots = {'early': [], 'perfect': [], 'late': []}
        self.lines = {'early_perfect': [], 'perfect_late': []}
        self.temp_coordinates = self.parent.coordinates.copy()
        self.temp_coordinate_data = self.parent.coordinate_data.copy() if self.parent.coordinate_data else None
        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, width=614, height=138)
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.screenshot = self.take_screenshot()
        self.photo = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        for i, ((x, y), key, color, dot_type) in enumerate(self.temp_coordinates):
            early_dot = self.canvas.create_oval(x-5, y-15, x+5, y-5, fill="blue", tags=(f"early{i}",))
            perfect_dot = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="red", tags=(f"perfect{i}",))
            late_dot = self.canvas.create_oval(x-5, y+5, x+5, y+15, fill="green", tags=(f"late{i}",))
            
            self.dots['early'].append(early_dot)
            self.dots['perfect'].append(perfect_dot)
            self.dots['late'].append(late_dot)
            
            early_perfect_line = self.canvas.create_line(x, y-10, x, y, fill="purple", width=2, tags=(f"early_perfect{i}",))
            perfect_late_line = self.canvas.create_line(x, y, x, y+10, fill="orange", width=2, tags=(f"perfect_late{i}",))
            
            self.lines['early_perfect'].append(early_perfect_line)
            self.lines['perfect_late'].append(perfect_late_line)
            
            for dot_type in ['early', 'perfect', 'late']:
                self.canvas.tag_bind(f"{dot_type}{i}", "<ButtonPress-1>", lambda event, i=i, t=dot_type: self.on_press(event, i, t))
                self.canvas.tag_bind(f"{dot_type}{i}", "<B1-Motion>", lambda event, i=i, t=dot_type: self.on_drag(event, i, t))

        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_coordinates)
        save_button.pack(side=tk.LEFT, padx=5)

        load_button = ttk.Button(button_frame, text="Load", command=self.load_coordinates)
        load_button.pack(side=tk.LEFT, padx=5)

        use_button = ttk.Button(button_frame, text="Use", command=self.use_coordinates)
        use_button.pack(side=tk.LEFT, padx=5)

    def take_screenshot(self):
        camera = dxcam.create()
        frame = camera.grab(region=capture_area)
        camera.stop()
        return Image.fromarray(frame)

    def on_press(self, event, i, dot_type):
        self.drag_data = {'x': event.x, 'y': event.y, 'index': i, 'type': dot_type}

    def on_drag(self, event, i, dot_type):
        dx = event.x - self.drag_data['x']
        dy = event.y - self.drag_data['y']
        self.canvas.move(self.dots[dot_type][i], dx, dy)
        self.drag_data['x'] = event.x
        self.drag_data['y'] = event.y
        x, y = self.canvas.coords(self.dots[dot_type][i])[:2]
        self.temp_coordinates[i] = ((int(x+5), int(y+5)), self.temp_coordinates[i][1], self.temp_coordinates[i][2], dot_type)
        self.update_lines(i)

    def update_lines(self, i):
        early_x, early_y = self.canvas.coords(self.dots['early'][i])[:2]
        perfect_x, perfect_y = self.canvas.coords(self.dots['perfect'][i])[:2]
        late_x, late_y = self.canvas.coords(self.dots['late'][i])[:2]
        
        self.canvas.coords(self.lines['early_perfect'][i], early_x+5, early_y+5, perfect_x+5, perfect_y+5)
        self.canvas.coords(self.lines['perfect_late'][i], perfect_x+5, perfect_y+5, late_x+5, late_y+5)

    def save_coordinates(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            save_data = []
            for i, ((x, y), key, color, dot_type) in enumerate(self.temp_coordinates):
                early_x, early_y = self.canvas.coords(self.dots['early'][i])[:2]
                perfect_x, perfect_y = self.canvas.coords(self.dots['perfect'][i])[:2]
                late_x, late_y = self.canvas.coords(self.dots['late'][i])[:2]
                save_data.append({
                    'key': key,
                    'color': color,
                    'early': (int(early_x+5), int(early_y+5)),
                    'perfect': (int(perfect_x+5), int(perfect_y+5)),
                    'late': (int(late_x+5), int(late_y+5))
                })
            with open(filename, 'w') as f:
                json.dump(save_data, f)
            self.temp_coordinate_data = save_data

    def load_coordinates(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filename:
            with open(filename, 'r') as f:
                loaded_data = json.load(f)
            for i, data in enumerate(loaded_data):
                self.temp_coordinates[i] = (tuple(data['perfect']), data['key'], tuple(data['color']), 'perfect')
                self.canvas.coords(self.dots['early'][i], data['early'][0]-5, data['early'][1]-5, data['early'][0]+5, data['early'][1]+5)
                self.canvas.coords(self.dots['perfect'][i], data['perfect'][0]-5, data['perfect'][1]-5, data['perfect'][0]+5, data['perfect'][1]+5)
                self.canvas.coords(self.dots['late'][i], data['late'][0]-5, data['late'][1]-5, data['late'][0]+5, data['late'][1]+5)
                self.update_lines(i)
            self.temp_coordinate_data = loaded_data

    def use_coordinates(self):
        self.parent.coordinates = self.temp_coordinates.copy()
        self.parent.coordinate_data = self.temp_coordinate_data.copy() if self.temp_coordinate_data else None
        self.destroy()

class ColorSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Color Settings")
        self.geometry("300x200")
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("TButton", padding=5, font=("Arial", 10))

        for i, (key, label) in enumerate(zip([KEY_A, KEY_S, KEY_D, KEY_F], ["A", "S", "D", "F"])):
            button = ttk.Button(main_frame, text=f"Set Color for {label}", command=lambda k=key: self.choose_color(k))
            button.grid(row=i, column=0, pady=5, sticky="ew")

    def choose_color(self, key):
        color = colorchooser.askcolor()[0]
        if color:
            rgb_color = tuple(int(c) for c in color)
            for i, (coord, k, _, dot_type) in enumerate(coordinates):
                if k == key:
                    coordinates[i] = (coord, k, rgb_color, dot_type)
                    break

class KeySettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Key Settings")
        self.geometry("300x200")
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("TButton", padding=5, font=("Arial", 10))

        for i, (key, label) in enumerate(zip([KEY_A, KEY_S, KEY_D, KEY_F], ["A", "S", "D", "F"])):
            button = ttk.Button(main_frame, text=f"Set Key for {label}", command=lambda k=key: self.choose_key(k))
            button.grid(row=i, column=0, pady=5, sticky="ew")

    def choose_key(self, key):
        new_key = simpledialog.askstring("Input", f"Enter new key for {key}:")
        if new_key:
            scan_code = ord(new_key.upper()) - 65 + 0x1E  # Convert to scan code
            for i, (coord, k, color, dot_type) in enumerate(coordinates):
                if k == key:
                    coordinates[i] = (coord, scan_code, color, dot_type)
                    break

class HumanizerSettings(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Humanizer Settings")
        self.geometry("400x500")
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ttk.Label(main_frame, text="Profile:").grid(row=0, column=0, sticky="w", pady=5)
        self.profile = ttk.Combobox(main_frame, values=["Beginner", "Intermediate", "Above Medium", "Good", "Normal"], state="readonly")
        self.profile.grid(row=0, column=1, sticky="ew", pady=5)
        self.profile.bind("<<ComboboxSelected>>", self.on_profile_change)

        ttk.Label(main_frame, text="Random Delay (ms):").grid(row=1, column=0, sticky="w", pady=5)
        self.random_delay = ttk.Scale(main_frame, from_=0, to=100, orient="horizontal")
        self.random_delay.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Miss Chance (%):").grid(row=2, column=0, sticky="w", pady=5)
        self.miss_chance = ttk.Scale(main_frame, from_=0, to=10, orient="horizontal")
        self.miss_chance.grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Press Duration Variation (ms):").grid(row=3, column=0, sticky="w", pady=5)
        self.press_duration_variation = ttk.Scale(main_frame, from_=0, to=50, orient="horizontal")
        self.press_duration_variation.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Reaction Time (ms):").grid(row=4, column=0, sticky="w", pady=5)
        self.reaction_time = ttk.Scale(main_frame, from_=0, to=200, orient="horizontal")
        self.reaction_time.grid(row=4, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Timing Error (ms):").grid(row=5, column=0, sticky="w", pady=5)
        self.timing_error = ttk.Scale(main_frame, from_=0, to=50, orient="horizontal")
        self.timing_error.grid(row=5, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Early Click Chance (%):").grid(row=6, column=0, sticky="w", pady=5)
        self.early_click_chance = ttk.Scale(main_frame, from_=0, to=50, orient="horizontal")
        self.early_click_chance.grid(row=6, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Late Click Chance (%):").grid(row=7, column=0, sticky="w", pady=5)
        self.late_click_chance = ttk.Scale(main_frame, from_=0, to=50, orient="horizontal")
        self.late_click_chance.grid(row=7, column=1, sticky="ew", pady=5)

        ttk.Button(main_frame, text="Apply", command=self.apply_settings).grid(row=8, column=0, columnspan=2, pady=20)

    def on_profile_change(self, event):
        profile = self.profile.get()
        if profile == "Beginner":
            self.random_delay.set(30)
            self.miss_chance.set(5)
            self.press_duration_variation.set(25)
            self.reaction_time.set(120)
            self.timing_error.set(25)
            self.early_click_chance.set(30)
            self.late_click_chance.set(30)
        elif profile == "Intermediate":
            self.random_delay.set(20)
            self.miss_chance.set(3)
            self.press_duration_variation.set(20)
            self.reaction_time.set(90)
            self.timing_error.set(20)
            self.early_click_chance.set(20)
            self.late_click_chance.set(20)
        elif profile == "Above Medium":
            self.random_delay.set(15)
            self.miss_chance.set(2)
            self.press_duration_variation.set(15)
            self.reaction_time.set(70)
            self.timing_error.set(15)
            self.early_click_chance.set(15)
            self.late_click_chance.set(15)
        elif profile == "Good":
            self.random_delay.set(10)
            self.miss_chance.set(1)
            self.press_duration_variation.set(10)
            self.reaction_time.set(50)
            self.timing_error.set(10)
            self.early_click_chance.set(10)
            self.late_click_chance.set(10)
        elif profile == "Normal":
            self.random_delay.set(0)
            self.miss_chance.set(0)
            self.press_duration_variation.set(0)
            self.reaction_time.set(0)
            self.timing_error.set(0)
            self.early_click_chance.set(0)
            self.late_click_chance.set(0)

    def apply_settings(self):
        self.parent.humanizer_settings = {
            "random_delay": self.random_delay.get(),
            "miss_chance": self.miss_chance.get(),
            "press_duration_variation": self.press_duration_variation.get(),
            "reaction_time": self.reaction_time.get(),
            "timing_error": self.timing_error.get(),
            "early_click_chance": self.early_click_chance.get(),
            "late_click_chance": self.late_click_chance.get(),
        }
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("fnf auto")
        self.geometry("300x450")
        self.configure(bg="#f0f0f0")
        self.running = False
        self.thread = None
        self.key_queue = queue.Queue()
        self.mode = tk.StringVar(value="normal")
        self.humanizer_settings = None
        self.coordinate_data = None
        self.coordinates = coordinates.copy()  # Initialize with default coordinates
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("TButton", padding=10, font=("Arial", 12))
        style.configure("TLabel", font=("Arial", 12))

        title_label = ttk.Label(main_frame, text="auto play", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        mode_label = ttk.Label(main_frame, text="Mode:", font=("Arial", 12))
        mode_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        mode_dropdown = ttk.Combobox(main_frame, textvariable=self.mode, values=["normal", "spammer"], state="readonly")
        mode_dropdown.grid(row=1, column=1, sticky="ew", pady=(0, 10))
        mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.start_button = ttk.Button(main_frame, text="Start", command=self.start_script)
        self.start_button.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

        self.stop_button = ttk.Button(main_frame, text="Stop", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

        self.status_label = ttk.Label(main_frame, text="Status: Idle", font=("Arial", 10))
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        self.color_settings_button = ttk.Button(main_frame, text="Change Colors", command=self.open_color_settings)
        self.color_settings_button.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        self.key_settings_button = ttk.Button(main_frame, text="Change Keys", command=self.open_key_settings)
        self.key_settings_button.grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        self.coordinate_settings_button = ttk.Button(main_frame, text="Change Coordinates", command=self.open_coordinate_settings)
        self.coordinate_settings_button.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        self.humanizer_button = ttk.Button(main_frame, text="Humanizer", command=self.open_humanizer_settings)
        self.humanizer_button.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="ew")

    def on_mode_change(self, event):
        print(f"Mode changed to: {self.mode.get()}")
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
        HumanizerSettings(self)

    def start_script(self):
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        self.thread = threading.Thread(target=self.run_script)
        self.thread.start()
        self.key_thread = threading.Thread(target=self.key_handler)
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
                if action == "press":
                    press_key(key)
                elif action == "release":
                    release_key(key)
            except queue.Empty:
                pass

    def run_script(self):
        print("Script started.")
        camera = dxcam.create()
        camera.start(region=capture_area)
        key_states = {key: False for _, key, _, _ in self.coordinates}
        key_hold_times = {key: 0 for _, key, _, _ in self.coordinates}
        key_release_times = {key: 0 for _, key, _, _ in self.coordinates}
        
        if self.mode.get() == "normal":
            min_hold_time = 0.04
            double_note_threshold = 0.04
        else:  # spammer mode
            min_hold_time = 0.03
            min_release_time = 0.02

        try:
            while self.running:
                image = camera.get_latest_frame()
                if image is None:
                    continue

                current_time = time.time()

                if self.mode.get() == "normal" and self.coordinate_data:
                    # Normal mode logic with humanizer
                    for data in self.coordinate_data:
                        x, y = data['perfect']
                        key = data['key']
                        target_rgb = tuple(data['color'])
                        early_x, early_y = data['early']
                        perfect_x, perfect_y = data['perfect']
                        late_x, late_y = data['late']
                        
                        pixel = image[y, x]
                        if np.array_equal(pixel, target_rgb):
                            if not key_states[key]:
                                if self.humanizer_settings:
                                    # Apply humanizer settings
                                    if random.random() * 100 > self.humanizer_settings["miss_chance"]:
                                        time.sleep(max(0, self.humanizer_settings["reaction_time"] / 1000))
                                        time.sleep(max(0, random.uniform(0, self.humanizer_settings["random_delay"] / 1000)))
                                        
                                        # Determine click type based on probabilities
                                        click_type = random.choices(
                                            ['early', 'perfect', 'late'],
                                            weights=[
                                                self.humanizer_settings["early_click_chance"],
                                                100 - self.humanizer_settings["early_click_chance"] - self.humanizer_settings["late_click_chance"],
                                                self.humanizer_settings["late_click_chance"]
                                            ]
                                        )[0]
                                        
                                        if click_type == 'early':
                                            click_y = random.uniform(early_y, perfect_y)
                                        elif click_type == 'perfect':
                                            click_y = perfect_y
                                        else:  # late
                                            click_y = random.uniform(perfect_y, late_y)
                                        
                                        timing_error = abs(click_y - perfect_y) / (late_y - early_y) * self.humanizer_settings["timing_error"]
                                        time.sleep(max(0, timing_error / 1000))
                                        
                                        self.key_queue.put(("press", key))
                                        key_states[key] = True
                                        key_hold_times[key] = current_time
                                else:
                                    self.key_queue.put(("press", key))
                                    key_states[key] = True
                                    key_hold_times[key] = current_time
                            elif current_time - key_release_times[key] < double_note_threshold:
                                self.key_queue.put(("release", key))
                                self.key_queue.put(("press", key))
                                key_hold_times[key] = current_time
                            else:
                                key_hold_times[key] = current_time
                        else:
                            if key_states[key]:
                                hold_time = min_hold_time
                                if self.humanizer_settings:
                                    hold_time += max(0, random.uniform(-self.humanizer_settings["press_duration_variation"] / 1000, self.humanizer_settings["press_duration_variation"] / 1000))
                                if current_time - key_hold_times[key] >= hold_time:
                                    self.key_queue.put(("release", key))
                                    key_states[key] = False
                                    key_release_times[key] = current_time
                else:
                    # Spammer mode logic
                    for data in self.coordinate_data:
                        x, y = data['perfect']
                        key = data['key']
                        target_rgb = tuple(data['color'])
                        pixel = image[y, x]
                        if np.array_equal(pixel, target_rgb):
                            if not key_states[key]:
                                if current_time - key_release_times[key] >= min_release_time:
                                    self.key_queue.put(("press", key))
                                    key_states[key] = True
                                    key_hold_times[key] = current_time
                        elif key_states[key] and (current_time - key_hold_times[key]) >= min_hold_time:
                            self.key_queue.put(("release", key))
                            key_states[key] = False
                            key_release_times[key] = current_time

                # Small delay to prevent excessive CPU usage
                

        finally:
            # Ensure all keys are released when the script stops
            for key, state in key_states.items():
                if state:
                    self.key_queue.put(("release", key))
            
            camera.stop()
            del camera
            print("Script stopped.")
            self.status_label.config(text="Status: Idle")

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()
