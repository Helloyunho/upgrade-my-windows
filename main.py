import asyncio
import logging
import discord
import libvirt
import os
from pathlib import Path
from PIL import Image
from discord.ext import commands
from xml.dom import minidom
from dotenv import load_dotenv
from typing import Literal
from typings.vminfo import VMInfo
from utils.display_window import DisplayWindow
from utils.logger import get_logger
from utils.vnc_client import VNCClient

COMMANDS = [
    "admin",
    "change",
    "mouse",
    "eject",
    "help",
    "info",
    "keyboard",
    "screenshot",
]

load_dotenv()


class UpgradeMyWindowsBot(commands.Bot):
    virt: libvirt.virConnect
    dom: libvirt.virDomain
    vnc: VNCClient
    image_path: Path
    display_window: DisplayWindow
    vm_loop: asyncio.Task | None
    audio_buffer: bytes
    logger: logging.Logger

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display_window = DisplayWindow()
        self.display_window.start()
        self.virt = libvirt.open()
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))
        self.vnc = VNCClient()  # dummy
        self.vm_loop = None
        self.image_path = Path(os.getenv("IMAGE_PATH") or "./images")
        self.audio_buffer = b""
        self.logger = get_logger(self.__class__.__name__)

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
        self.virt = libvirt.open()
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

    async def on_ready(self):
        self.logger.info(f"Logged on as {self.user}!")
        for command in COMMANDS:
            await self.load_extension(f"commands.{command}")

    async def close(self):
        self.logger.info("Closing bot")
        if self._closed:
            return
        self.display_window.close()
        self.display_window.join()
        await self.disconnect_qemu()
        await super().close()

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
            path = str(self.image_path / info["os"] / path) if path else None
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


intents = discord.Intents.default()
client = UpgradeMyWindowsBot("aaaaaaaaaaaaaaaaa", intents=intents)


client.run(os.getenv("DISCORD_TOKEN"))  # type: ignore
