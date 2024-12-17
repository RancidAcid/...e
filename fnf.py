import tkinter as tk
from tkinter import ttk
import threading
import time
import keyboard
import ctypes
import dxcam
import queue

# Key codes for A, S, D, F
KEY_A = 0x1E
KEY_S = 0x1F
KEY_D = 0x20
KEY_F = 0x21

# Area to capture on the screen
capture_area = (376, 630, 990, 768)

# Adjust coordinates relative to capture area
def adjust_coordinates(x, y):
    return x - capture_area[0], y - capture_area[1]

# Coordinates and target colors for each key
coordinates = [
    (adjust_coordinates(451, 661), KEY_A, (217, 0, 255)),
    (adjust_coordinates(604, 661), KEY_S, (255, 0, 4)),
    (adjust_coordinates(760, 661), KEY_D, (255, 0, 4)),
    (adjust_coordinates(913, 661), KEY_F, (217, 0, 255))
]

# Check if the pixel color matches the target color
def is_target_color(image, x, y, target_rgb):
    pixel = image[y, x]
    return pixel[0] == target_rgb[0] and pixel[1] == target_rgb[1] and pixel[2] == target_rgb[2]

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Press a key using scan code
def press_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

# Release a key using scan code
def release_key(scan_code):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

# Main application class
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("fnf auto")
        self.geometry("300x200")
        self.configure(bg="#f0f0f0")

        self.running = False
        self.thread = None
        self.key_queue = queue.Queue()

        self.create_widgets()

    # Create GUI widgets
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

        self.start_button = ttk.Button(main_frame, text="Start", command=self.start_script)
        self.start_button.grid(row=1, column=0, padx=5, pady=10, sticky="ew")

        self.stop_button = ttk.Button(main_frame, text="Stop", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        self.status_label = ttk.Label(main_frame, text="Status: Idle", font=("Arial", 10))
        self.status_label.grid(row=2, column=0, columnspan=2, pady=(10, 0))

    # Start the script
    def start_script(self):
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        self.thread = threading.Thread(target=self.run_script)
        self.thread.start()
        self.key_thread = threading.Thread(target=self.key_handler)
        self.key_thread.start()

    # Stop the script
    def stop_script(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped")

    # Handle key press and release actions
    def key_handler(self):
        while self.running:
            try:
                action, key = self.key_queue.get(timeout=0.1)
                if action == "press":
                    press_key(key)
                elif action == "release":
                    release_key(key)
            except queue.Empty:
                pass

    # Main script logic
    def run_script(self):
        print("Script started.")

        camera = dxcam.create()
        camera.start(region=capture_area)

        key_states = {key: False for _, key, _ in coordinates}
        key_timestamps = {key: 0 for _, key, _ in coordinates}
        min_hold_time = 0.1

        try:
            while self.running:
                image = camera.get_latest_frame()

                for (x, y), key, target_rgb in coordinates:
                    current_time = time.time()
                    if is_target_color(image, x, y, target_rgb):
                        if not key_states[key]:
                            print(f"Pressing key {chr(key + 0x41 - 0x1E)}")
                            self.key_queue.put(("press", key))
                            key_states[key] = True
                            key_timestamps[key] = current_time
                    else:
                        if key_states[key] and (current_time - key_timestamps[key]) >= min_hold_time:
                            print(f"Releasing key {chr(key + 0x41 - 0x1E)}")
                            self.key_queue.put(("release", key))
                            key_states[key] = False

                time.sleep(0.001)

        finally:
            camera.stop()
            print("Script stopped.")
            self.status_label.config(text="Status: Idle")

if __name__ == "__main__":
    app = App()
    app.mainloop()
