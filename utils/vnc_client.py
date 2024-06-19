import asyncio
import threading
import traceback
from typing import Callable, Generic, Literal, TypeVar, Awaitable
from vncdotool.client import VNCDoToolClient
from PIL.Image import Image

FPS = 60

Events = TypeVar("Events", bound=str)


class EventListener(Generic[Events]):
    event_listeners: dict[Events, Callable[..., Awaitable[None]]]

    def __init__(self):
        self.event_listeners = {}

    def add_event_listener(
        self, event: Events, callback: Callable[..., Awaitable[None]]
    ):
        self.event_listeners[event] = callback

    def remove_event_listener(self, event: Events):
        self.event_listeners.pop(event, None)

    async def dispatch_event(self, event: Events, *args):
        if event in self.event_listeners:
            await self.event_listeners[event](*args)


vnc_events = Literal["ready", "audio_start", "audio_stop", "audio_data"]


class CustomVNCClient(EventListener[vnc_events], VNCDoToolClient):
    def __init__(self):
        super().__init__()
        VNCDoToolClient.__init__(self)

    async def vncConnectionMade(self):
        await super().vncConnectionMade()
        await self.dispatch_event("ready")

    async def audio_stream_begin(self) -> None:
        await self.dispatch_event("audio_start")

    async def audio_stream_end(self) -> None:
        await self.dispatch_event("audio_stop")

    async def audio_stream_data(self, size: int, data: bytes) -> None:
        await self.dispatch_event("audio_data", size, data)


class VNCClient(
    EventListener[Literal[vnc_events, "disconnect", "screen_update"]], threading.Thread
):
    vnc: VNCDoToolClient
    is_ready: asyncio.Event

    def __init__(self):
        super().__init__()
        threading.Thread.__init__(self)
        self.vnc = CustomVNCClient()
        self.is_ready = asyncio.Event()
        self.vnc.add_event_listener("ready", self.on_ready)
        self.vnc.add_event_listener("audio_start", self._on_audio_start)
        self.vnc.add_event_listener("audio_stop", self._on_audio_stop)
        self.vnc.add_event_listener("audio_data", self._on_audio_data)

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
        self.vnc.updateCommited.set()

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

    def audioStreamBeginRequest(self):
        asyncio.create_task(self.vnc.audioStreamBeginRequest())

    def audioStreamStopRequest(self):
        asyncio.create_task(self.vnc.audioStreamStopRequest())

    async def on_ready(self):
        await self.dispatch_event("ready")
        self.is_ready.set()

    async def vnc_refresh_loop(self):
        await self.is_ready.wait()
        while True:
            if not self.vnc.writer or self.vnc.writer.is_closing():
                await self.dispatch_event("disconnect")
                break
            await self.vnc.refreshScreen(incremental=True)
            asyncio.create_task(self._on_screen_update())

    async def _on_screen_update(self) -> None:
        await self.dispatch_event("screen_update", self.vnc.screen)

    async def _on_audio_start(self):
        await self.dispatch_event("audio_start")

    async def _on_audio_stop(self):
        await self.dispatch_event("audio_stop")

    async def _on_audio_data(self, size: int, data: bytes):
        await self.dispatch_event("audio_data", size, data)

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.connect_vnc())
        except Exception as e:
            traceback.print_exc()
            loop.run_until_complete(self.dispatch_event("disconnect"))
