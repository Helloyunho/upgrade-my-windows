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

    def close(self):
        self.running = False

    def update_frame(self, image: Image.Image):
        numpy_image = np.array(image)
        img = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
        self.screen.put(img, block=False)

    def update_audio(self, data: bytes):
        pygame.mixer.Sound(buffer=data).play()

    def run(self):
        pygame.mixer.init(44100, -16, 2, buffer=512)
        cv2.namedWindow("Upgrade My Windows", cv2.WINDOW_AUTOSIZE)
        while self.running:
            if not self.screen.empty():
                image = self.screen.get()
                cv2.imshow("Upgrade My Windows", image)
            cv2.waitKey(0)

        cv2.destroyAllWindows()
