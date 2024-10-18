import cv2
import pygame
import threading
import queue
import numpy as np
from PIL import Image
from utils.logger import get_logger

MAX_WIDTH = 1920
MAX_HEIGHT = 1080


class DisplayWindow(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.screen = queue.Queue()
        self.running = True
        self.logger = get_logger(self.__class__.__name__)

    def close(self):
        self.running = False

    def update_frame(self, image: Image.Image):
        numpy_image = np.array(image)
        img = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]

        width_scale = MAX_WIDTH / w
        height_scale = MAX_HEIGHT / h

        scale = min(width_scale, height_scale)

        new_width = int(w * scale)
        new_height = int(h * scale)

        resized_image = cv2.resize(
            img, (new_width, new_height), interpolation=cv2.INTER_AREA
        )
        self.screen.put(resized_image, block=False)

    def update_audio(self, data: bytes):
        pygame.mixer.Sound(buffer=data).play()

    def run(self):
        pygame.mixer.init(44100, -16, 2, buffer=512)
        cv2.namedWindow(
            "Upgrade My Windows", cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL
        )
        while self.running:
            if not self.screen.empty():
                image = self.screen.get()
                cv2.imshow("Upgrade My Windows", image)
            cv2.waitKey(1)

        cv2.destroyAllWindows()
