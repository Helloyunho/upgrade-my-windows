import tkinter as tk
from PIL import ImageTk
import asyncio


class DisplayWindow:
    def __init__(self, window, fps=60):
        self.window = window
        self.window.title("Upgrade My Windows")

        self.fps = fps
        self.delay = int(1000 / fps)  # Calculate delay in milliseconds

        # Placeholder for the initial image dimensions
        self.photo = None

        # Create the canvas without setting dimensions
        self.canvas = tk.Canvas(window)
        self.canvas.pack()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True

    def on_closing(self):
        self.running = False
        self.window.destroy()

    def update_frame(self, image):
        img = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img)
        self.photo = img  # Keep a reference to avoid garbage collection

    def set_canvas_size(self, image):
        self.canvas.config(width=image.width, height=image.height)


async def tkinter_event_loop(root):
    while True:
        root.update()
        await asyncio.sleep(1 / 1000)
