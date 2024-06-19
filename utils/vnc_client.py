import asyncio
import threading
import traceback
from typing import Callable
from vncdotool.client import VNCDoToolClient
from PIL.Image import Image

FPS = 60


class CustomVNCClient(VNCDoToolClient):
    on_ready: Callable[[], None] | None

    def __init__(self, on_ready=None):
        super().__init__()
        self.on_ready = on_ready

    async def vncConnectionMade(self):
        await super().vncConnectionMade()
        if self.on_ready:
            self.on_ready()


class VNCClient(threading.Thread):
    vnc: VNCDoToolClient
    on_close: Callable[[], None] | None
    on_screen_update: Callable[[Image | None], None] | None
    is_ready: asyncio.Event

    def __init__(self, on_close=None, on_screen_update=None):
        super().__init__()
        self.vnc = CustomVNCClient(on_ready=self.on_ready)
        self.on_close = on_close
        self.on_screen_update = on_screen_update
        self.is_ready = asyncio.Event()

    @property
    def screen(self) -> Image | None:
        return self.vnc.screen

    @property
    def x(self) -> int:
        return self.vnc.x

    @property
    def y(self) -> int:
        return self.vnc.y

    async def connect_vnc(self):
        reader, writer = await asyncio.open_unix_connection("/tmp/umw-vnc.sock")
        # reader, writer = await asyncio.open_connection("localhost", 5900)
        await self.vnc.connect(reader, writer)
        await self.vnc_refresh_loop()

    def disconnect(self):
        asyncio.create_task(self.vnc.disconnect())

    def keyDown(self, key: str):
        asyncio.create_task(self.vnc.keyDown(key))

    def keyUp(self, key: str):
        asyncio.create_task(self.vnc.keyUp(key))

    def mouseMove(self, x: int, y: int):
        asyncio.create_task(self.vnc.mouseMove(x, y))

    def mouseDrag(self, x: int, y: int, step: int):
        asyncio.create_task(self.vnc.mouseDrag(x, y, step))

    def mouseDown(self, button: int):
        asyncio.create_task(self.vnc.mouseDown(button))

    def mouseUp(self, button: int):
        asyncio.create_task(self.vnc.mouseUp(button))

    def mousePress(self, button: int):
        asyncio.create_task(self.vnc.mousePress(button))

    def on_ready(self):
        self.is_ready.set()

    async def vnc_refresh_loop(self):
        await self.is_ready.wait()
        while True:
            if not self.vnc.writer or self.vnc.writer.is_closing():
                if self.on_close:
                    self.on_close()
                break
            await self.vnc.refreshScreen(incremental=True)
            asyncio.create_task(self._on_screen_update())

    async def _on_screen_update(self) -> None:
        if self.on_screen_update:
            self.on_screen_update(self.vnc.screen)

    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect_vnc())
        except Exception as e:
            traceback.print_exc()
            if self.on_close:
                self.on_close()
