import asyncio
import datetime
import logging
import libvirt
import os
import json
import grpc
import stream_list_pb2
import stream_list_pb2_grpc
from pathlib import Path
from PIL import Image
from xml.dom import minidom
from dotenv import load_dotenv
from typing import Literal
from typings.vminfo import VMInfo
from utils.display_window import DisplayWindow
from utils.logger import get_logger
from utils.vnc_client import VNCClient
from utils.command_register import COMMANDS
from importlib import import_module
from aiogoogle import Aiogoogle

COMMAND_FILES = [
    "admin",
    "change",
    "mouse",
    "eject",
    "help",
    "info",
    "keyboard",
]

load_dotenv()

with open("user_creds.json") as f:
    user_creds = json.load(f)

with open("client_creds.json") as f:
    client_creds = json.load(f)


class UpgradeMyWindowsBot:
    virt: libvirt.virConnect
    dom: libvirt.virDomain
    vnc: VNCClient
    image_path: Path
    display_window: DisplayWindow
    vm_loop: asyncio.Task | None
    audio_buffer: bytes
    logger: logging.Logger
    liveChatID: str
    started_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
    live_channel_id: str = os.getenv("YOUTUBE_CHANNEL_ID") or ""
    block_chat: bool = False

    def __init__(self, video_id, *args, **kwargs):
        self.display_window = DisplayWindow()
        self.display_window.start()
        self.virt = libvirt.open("qemu:///system")
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))
        self.vnc = VNCClient()  # dummy
        self.vm_loop = None
        self.image_path = Path(os.getenv("IMAGE_PATH") or "./images")
        self.audio_buffer = b""
        self.logger = get_logger(self.__class__.__name__)
        for file in COMMAND_FILES:
            try:
                import_module(f"commands.{file}")
            except ImportError as e:
                self.logger.error(f"Failed to import command module {file}: {e}")

        asyncio.run(self.get_live_chat_id(video_id))
        asyncio.run(self.setup_hook())
        asyncio.run(self.get_message())

    async def get_live_chat_id(self, video_id: str):
        async with Aiogoogle(user_creds=user_creds, client_creds=client_creds) as aiogoogle:  # type: ignore
            youtube = await aiogoogle.discover("youtube", "v3")
            stream_info = await aiogoogle.as_user(
                youtube.videos.list(
                    part="liveStreamingDetails",  # type: ignore
                    id=video_id,  # type: ignore
                )
            )
            self.liveChatID = stream_info["items"][0]["liveStreamingDetails"][
                "activeLiveChatId"
            ]

    @property
    def _is_virt_connected(self) -> bool:
        return self.virt.isAlive()

    @property
    def _is_vm_running(self) -> bool:
        return self._is_virt_connected and self.dom.isActive() == 1

    @property
    def _is_vnc_connected(self) -> bool:
        return self.vnc.is_alive() and self.vnc.is_connected

    async def connect_qemu(self, reconnect=False):
        self.logger.info("Connecting to QEMU")
        if self._is_virt_connected:
            if reconnect:
                self.logger.debug("Disconnecting from QEMU for reconnection")
                await self.disconnect_qemu()
            else:
                self.logger.warning(
                    "Already connected to QEMU, ignoring connection request"
                )
                return
        self.virt = libvirt.open("qemu:///system")
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))
        self.logger.info("Connected to QEMU")

    async def vm_start_loop(self):
        self.logger.info("VM start loop started")
        while self._is_virt_connected:
            await asyncio.sleep(1)
            if not self._is_vm_running:
                await self.start_domain()
                await self.connect_vnc(reconnect=True)
        self.logger.info("VM start loop stopped")

    async def connect_vnc(self, reconnect=False):
        self.logger.info("Connecting to VNC")
        if self._is_vnc_connected:
            if reconnect:
                self.logger.debug("Disconnecting from VNC for reconnection")
                await self.disconnect_vnc()
            else:
                self.logger.warning(
                    "Already connected to VNC, ignoring connection request"
                )
                return
        self.vnc = VNCClient()
        self.vnc.add_event_listener("screen_update", self._on_screen_update)
        self.vnc.add_event_listener("ready", self._on_vnc_ready)
        self.vnc.add_event_listener("audio_data", self._on_audio_data)
        self.vnc.start()
        self.logger.info("Connected to VNC")

    async def _on_screen_update(self, image: Image.Image | None):
        if image:
            self.display_window.update_frame(image)

    async def _on_vnc_ready(self):
        if self._is_vnc_connected:
            self.logger.info("VNC is ready")
            self.vnc.audioStreamBeginRequest()

    async def _on_audio_data(self, size: int, data: bytes):
        if len(self.audio_buffer) < 44100 * 2 * 2:
            self.audio_buffer += data
        else:
            if self._is_vnc_connected and self.display_window.running:
                self.display_window.update_audio(self.audio_buffer)
            self.audio_buffer = b""

    async def disconnect_vnc(self):
        self.logger.info("Disconnecting from VNC")
        if self._is_vnc_connected:
            self.vnc.remove_event_listener("screen_update")
            self.vnc.remove_event_listener("ready")
            self.vnc.remove_event_listener("audio_data")
            self.vnc.disconnect()
        self.logger.info("Disconnected from VNC")

    async def shutdown_domain(self):
        self.logger.info("Shutting down VM")
        if self._is_vm_running:
            await self.disconnect_vnc()
            self.dom.shutdown()
        self.logger.info("VM is shut down")

    async def start_domain(self):
        self.logger.info("Starting VM")
        if not self._is_vm_running:
            self.dom.create()
            await self.connect_vnc(reconnect=True)
        self.logger.info("VM is started")

    async def force_shutdown_domain(self):
        self.logger.info("Force shutting down VM")
        if self._is_vm_running:
            await self.disconnect_vnc()
            self.dom.destroy()
        self.logger.info("VM is force shut down")

    async def disconnect_qemu(self):
        self.logger.info("Disconnecting from QEMU")
        if self._is_vnc_connected:
            await self.disconnect_vnc()
        if self.vm_loop:
            self.vm_loop.cancel()
            self.vm_loop = None
        if self.virt:
            self.virt.close()
        self.logger.info("Disconnected from QEMU")

    async def setup_hook(self):
        self.logger.info("Doing initial setup")
        await self.connect_qemu()
        await self.start_domain()
        await self.connect_vnc()

    def terminate(self):
        self.display_window.close()
        self.display_window.join()
        asyncio.run(self.disconnect_qemu())

    async def get_screen_img(self) -> Image.Image | None:
        self.logger.debug("Getting screen image")
        if not self._is_vnc_connected:
            self.logger.warning("VNC is not connected")
            return None

        return self.vnc.screen

    async def set_vcpus(self, vcpus: int):
        self.logger.info(f"Setting vCPUs to {vcpus}")
        if self._is_virt_connected:
            self.dom.setVcpusFlags(vcpus, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    async def set_memory(self, memory: int):
        self.logger.info(f"Setting memory to {memory} KB")
        if self._is_virt_connected:
            self.dom.setMemoryFlags(
                memory,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_DOMAIN_MEM_MAXIMUM,
            )
            self.dom.setMemoryFlags(memory, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    async def set_device(
        self, path: str | None = None, type: Literal["cdrom", "floppy"] = "cdrom"
    ):
        self.logger.info(f"Setting {type} to {path}")
        if self._is_vm_running:
            info = await self.get_current_info()
            if not info:
                self.logger.warning("Failed to get VM info")
                return
            if path:
                if path == "half-life.iso" or path == "gparted.iso":
                    path = str(self.image_path / path)
                else:
                    path = str(self.image_path / info["os"] / path)
            else:
                path = None
            raw_xml = self.dom.XMLDesc()
            xml = minidom.parseString(raw_xml)
            disks = xml.getElementsByTagName("disk")
            for disk in disks:
                if disk.getAttribute("device") == type:
                    if not disk.getElementsByTagName("source"):
                        disk.appendChild(xml.createElement("source"))
                    disk.getElementsByTagName("source")[0].setAttribute(
                        "file", path or ""
                    )
                    self.dom.updateDeviceFlags(
                        disk.toxml("utf8").decode(),
                        libvirt.VIR_DOMAIN_AFFECT_CURRENT
                        | libvirt.VIR_DOMAIN_AFFECT_LIVE
                        | libvirt.VIR_DOMAIN_AFFECT_CONFIG,
                    )
                    break

    async def set_os(self, os: str):
        self.logger.info(f"Setting OS to {os}")
        if self._is_vm_running:
            raw_xml = self.dom.metadata(
                libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                "http://libosinfo.org/xmlns/libvirt/domain/1.0",
            )
            xml = minidom.parseString(raw_xml)
            osinfo = xml.getElementsByTagName("os")[0]
            osinfo.setAttribute("id", f"http://microsoft.com/win/{os.lower()}")
            self.dom.setMetadata(
                libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                xml.toxml("utf8").decode(),
                "libosinfo",
                "http://libosinfo.org/xmlns/libvirt/domain/1.0",
                libvirt.VIR_DOMAIN_AFFECT_CURRENT
                | libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG,
            )

    async def get_current_info(self) -> VMInfo | None:
        self.logger.debug("Getting current VM info")
        if self._is_vm_running:
            memsize = self.dom.maxMemory()
            vcpus = self.dom.vcpusFlags()

            raw_xml = self.dom.XMLDesc()
            xml = minidom.parseString(raw_xml)
            os = (
                xml.getElementsByTagName("libosinfo:os")[0]
                .getAttribute("id")
                .split("/")[-1]
            )
            disks = xml.getElementsByTagName("disk")
            cdrom_path = None
            floppy = None
            for disk in disks:
                if disk.getAttribute("device") == "cdrom" and cdrom_path is None:
                    if not disk.getElementsByTagName("source"):
                        continue
                    cdrom_path = (
                        disk.getElementsByTagName("source")[0]
                        .getAttribute("file")
                        .split("/")[-1]
                    )
                    continue
                if disk.getAttribute("device") == "floppy" and floppy is None:
                    if not disk.getElementsByTagName("source"):
                        continue
                    floppy = (
                        disk.getElementsByTagName("source")[0]
                        .getAttribute("file")
                        .split("/")[-1]
                    )
                    continue
                if cdrom_path and floppy:
                    break

            info: VMInfo = {
                "memory": memsize / 1024,
                "cpu": vcpus,
                "cdrom": cdrom_path,
                "floppy": floppy,
                "os": os,
            }
            self.logger.debug(f"Current VM info: {info}")
            return info
        else:
            return None

    async def send_message(self, message: str):
        async with Aiogoogle(
            user_creds=user_creds, client_creds=client_creds
        ) as aiogoogle:
            youtube = await aiogoogle.discover("youtube", "v3")
            await aiogoogle.as_user(
                youtube.liveChatMessages.insert(
                    part="snippet",  # type: ignore
                    json={  # type: ignore
                        "snippet": {
                            "liveChatId": self.liveChatID,
                            "type": "textMessageEvent",
                            "textMessageDetails": {"messageText": message},
                        },
                    },
                )
            )

    async def input_through_console(self):
        command = input("Enter command: ")
        command = command.split(" ")
        if command[0] in COMMANDS:
            command_func = COMMANDS[command[0]]["func"]
            await command_func(self, command[1:])

    async def get_message(self):
        creds = grpc.ssl_channel_credentials()
        async with grpc.aio.secure_channel(
            "dns:///youtube.googleapis.com:443", creds
        ) as channel:
            stub = stream_list_pb2_grpc.V3DataLiveChatMessageServiceStub(channel)
            metadata = (("x-goog-api-key", os.getenv("GOOGLE_API_KEY")),)
            next_page_token = None
            while True:
                if self.block_chat:
                    return
                request = stream_list_pb2.LiveChatMessageListRequest(  # type: ignore
                    part=["snippet", "authorDetails"],
                    live_chat_id=self.liveChatID,
                    max_results=5,
                    page_token=next_page_token,
                )
                async for response in stub.StreamList(request, metadata=metadata):  # type: ignore
                    for chat in response.items:
                        if (
                            chat.snippet.type == 1
                            and chat.snippet.author_channel_id != self.live_channel_id
                        ):  # textMessageEvent
                            published_at = datetime.datetime.fromisoformat(
                                chat.snippet.published_at.replace("Z", "+00:00")
                            )
                            if published_at > self.started_at:
                                message = chat.snippet.text_message_details.message_text
                                if message.startswith("!!"):
                                    command = message[2:].split(" ")[0]
                                    args = message[2:].split(" ")[1:]
                                    if command in COMMANDS:
                                        self.logger.info(
                                            f"User {chat.author_details.display_name} issued command {command} {' '.join(args)}"
                                        )
                                        command_props = COMMANDS[command]
                                        command_func = command_props["func"]
                                        if command_props["owner_only"]:
                                            if chat.author_details.is_chat_owner:
                                                await command_func(self, args)
                                            else:
                                                self.logger.warning(
                                                    f"User {chat.author_details.display_name} tried to use owner only command {command}"
                                                )
                                        elif command_props["mods_only"]:
                                            if (
                                                chat.author_details.is_chat_moderator
                                                or chat.author_details.is_chat_owner
                                            ):
                                                await command_func(self, args)
                                            else:
                                                self.logger.warning(
                                                    f"User {chat.author_details.display_name} tried to use mods only command {command}"
                                                )
                                        elif command_props["super_chat_only"]:
                                            if (
                                                chat.author_details.is_chat_owner
                                                or chat.author_details.is_chat_moderator
                                            ):
                                                await command_func(self, args)
                                        else:
                                            await command_func(self, args)
                        if (
                            chat.snippet.type == 15
                            and chat.snippet.author_channel_id != self.live_channel_id
                        ):  # superChatEvent
                            published_at = datetime.datetime.fromisoformat(
                                chat.snippet.published_at.replace("Z", "+00:00")
                            )
                            if published_at > self.started_at:
                                message = chat.snippet.super_chat_details.user_comment
                                if message.startswith("!!"):
                                    command = message[2:].split(" ")[0]
                                    args = message[2:].split(" ")[1:]
                                    if command in COMMANDS:
                                        self.logger.info(
                                            f"User {chat.author_details.display_name} issued command {command} {' '.join(args)}"
                                        )
                                        command_props = COMMANDS[command]
                                        command_func = command_props["func"]
                                        if command_props["owner_only"]:
                                            if chat.author_details.is_chat_owner:
                                                await command_func(self, args)
                                            else:
                                                self.logger.warning(
                                                    f"User {chat.author_details.display_name} tried to use owner only command {command}"
                                                )
                                        elif command_props["mods_only"]:
                                            if (
                                                chat.author_details.is_chat_moderator
                                                or chat.author_details.is_chat_owner
                                            ):
                                                await command_func(self, args)
                                            else:
                                                self.logger.warning(
                                                    f"User {chat.author_details.display_name} tried to use mods only command {command}"
                                                )
                                        elif command_props["super_chat_only"]:
                                            if (
                                                chat.author_details.is_chat_owner
                                                or chat.author_details.is_chat_moderator
                                                or chat.super_chat_details.tier >= 3
                                            ):
                                                await command_func(self, args)
                                        else:
                                            await command_func(self, args)

                    next_page_token = response.next_page_token


client = UpgradeMyWindowsBot(
    input("Enter the video(live) id: "),
)
