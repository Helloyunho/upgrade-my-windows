import pygame
import threading
from PIL import Image, ImageOps
from utils.logger import get_logger


class DisplayWindow(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        pygame.mixer.pre_init(44100, -16, 2, buffer=512)
        self.screen = None
        self.running = True
        self.logger = get_logger(self.__class__.__name__)

    def close(self):
        self.running = False

    def update_frame(self, image: Image.Image):
        if not self.screen:
            return
        self.screen.fill((0, 0, 0))
        _image = ImageOps.contain(image, (1600, 900), Image.Resampling.LANCZOS)
        mode = _image.mode
        size = _image.size
        data = _image.tobytes()

        pygame_image = pygame.image.fromstring(data, size, mode)  # type: ignore
        image_width, image_height = _image.size
        # center the image
        x = (1600 - image_width) // 2
        y = (900 - image_height) // 2
        self.screen.blit(pygame_image, (x, y))

    def update_audio(self, data: bytes):
        pygame.mixer.Sound(buffer=data).play()

    def run(self):
        pygame.init()
        pygame.display.set_caption("Upgrade My Windows")
        self.screen = pygame.display.set_mode((1600, 900))
        while self.running:
            pygame.event.pump()
            pygame.display.flip()

        pygame.quit()
