import pygame
from io import BytesIO


class DisplayWindow:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Upgrade My Windows")
        self.running = True

    def close(self):
        self.running = False

    def update_frame(self, image):
        mode = image.mode
        size = image.size
        data = image.tobytes()

        pygame_image = pygame.image.fromstring(data, size, mode)
        image_width, image_height = image.size
        if (
            image_width != self.screen.get_width()
            or image_height != self.screen.get_height()
        ):
            self.screen = pygame.display.set_mode((image_width, image_height))
            self.screen.fill((0, 0, 0))

        self.screen.blit(pygame_image, (0, 0))
        pygame.display.flip()

    async def pygame_loop(self):
        while self.running:
            pygame.display.flip()