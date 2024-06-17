import asyncio
import threading
import time
from typing import Callable
from vncdotool.client import VNCDoToolClient
from PIL.Image import Image

FPS = 60


class VNCClient(threading.Thread):
    vnc: VNCDoToolClient
    on_close: Callable[[], None] | None
    on_screen_update: Callable[[Image | None], None] | None

    def __init__(self, on_close=None, on_screen_update=None):
        super().__init__()
        self.vnc = VNCDoToolClient()
        self.on_close = on_close
        self.on_screen_update = on_screen_update
        self.is_it_working = 0

    @property
    def screen(self) -> Image | None:
        return self.vnc.screen

    async def connect_vnc(self):
        reader, writer = await asyncio.open_unix_connection("/tmp/umw-vnc.sock")
        # reader, writer = await asyncio.open_connection("localhost", 5900)
        await self.vnc.connect(reader, writer)
        await self.vnc_refresh_loop()

    def disconnect(self):
        loop = asyncio.get_running_loop()
        loop.create_task(self.vnc.disconnect())

    async def vnc_refresh_loop(self):
        while True:
            await asyncio.sleep(1 / FPS)
            self.is_it_working += 1
            if self.is_it_working == 60:
                print(time.time())
                self.is_it_working = 0
            if self.vnc.writer.is_closing():
                if self.on_close:
                    self.on_close()
                break
            await self.vnc.refreshScreen()
            asyncio.create_task(self._on_screen_update())

    async def _on_screen_update(self) -> None:
        if self.on_screen_update:
            self.on_screen_update(self.vnc.screen)

    def run(self) -> None:
        asyncio.run(self.connect_vnc())
