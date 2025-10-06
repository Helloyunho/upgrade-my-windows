import cv2
import pygame
import threading
import queue
import numpy as np
from PIL import Image
from utils.logger import get_logger


class DisplayWindow(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.screen = queue.Queue()
        self.running = True
        self.logger = get_logger(self.__class__.__name__)
        self.MAX_WIDTH = 2560
        self.MAX_HEIGHT = 1440

    def close(self):
        self.running = False

    def update_frame(self, image: Image.Image):
        numpy_image = np.array(image)
        img = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]

        ruler_thickness = 1
        major_tick_length = 15
        minor_tick_length = 7
        tick_color = (255, 255, 255)

        for x in range(0, w, 10):
            if x % 100 == 0:
                cv2.line(
                    img, (x, 0), (x, major_tick_length), tick_color, ruler_thickness
                )
            else:
                cv2.line(
                    img, (x, 0), (x, minor_tick_length), tick_color, ruler_thickness
                )

        for y in range(0, h, 10):
            if y % 100 == 0:
                cv2.line(
                    img, (0, y), (major_tick_length, y), tick_color, ruler_thickness
                )
            else:
                cv2.line(
                    img, (0, y), (minor_tick_length, y), tick_color, ruler_thickness
                )

        width_scale = self.MAX_WIDTH / w
        height_scale = self.MAX_HEIGHT / h

        scale = min(width_scale, height_scale)

        new_width = int(w * scale)
        new_height = int(h * scale)

        resized_image = cv2.resize(
            img, (new_width, new_height), interpolation=cv2.INTER_AREA
        )
        resized_image = cv2.copyMakeBorder(
            resized_image,
            (self.MAX_HEIGHT - new_height) // 2,
            (self.MAX_HEIGHT - new_height + 1) // 2,
            (self.MAX_WIDTH - new_width) // 2,
            (self.MAX_WIDTH - new_width + 1) // 2,
            cv2.BORDER_CONSTANT,
            value=[0, 0, 0],
        )

        self.screen.put(resized_image, block=False)

    def update_audio(self, data: bytes):
        pygame.mixer.Sound(buffer=data).play()

    def run(self):
        pygame.mixer.init(44100, -16, 2, buffer=512)
        cv2.namedWindow("Upgrade My Windows", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(
            "Upgrade My Windows", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        # _, _, self.MAX_WIDTH, self.MAX_HEIGHT = cv2.getWindowImageRect(
        #     "Upgrade My Windows"
        # ) # doesn't return correct size
        while self.running:
            if not self.screen.empty():
                image = self.screen.get()
                cv2.imshow("Upgrade My Windows", image)
            cv2.waitKey(1)

        cv2.destroyAllWindows()
