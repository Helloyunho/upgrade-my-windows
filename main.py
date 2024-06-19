import asyncio
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
    virt: libvirt.virConnect | None
    dom: libvirt.virDomain | None
    vnc: VNCClient | None
    image_path: Path
    display_window: DisplayWindow
    vm_loop: asyncio.Task | None
    audio_buffer: bytes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display_window = DisplayWindow()
        self.display_window.start()
        self.virt = None
        self.dom = None
        self.vnc = None
        self.vm_loop = None
        self.image_path = Path(os.getenv("IMAGE_PATH") or "./images")
        self.audio_buffer = b""

    def connect_qemu(self, reconnect=False):
        if self.virt or self.dom or self.vnc:
            if reconnect:
                self.disconnect_qemu()
            else:
                return
        self.virt = libvirt.open()
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))
        self.vm_loop = asyncio.create_task(self.vm_start_loop())

    async def vm_start_loop(self):
        while self.dom:
            await asyncio.sleep(1)
            if not self.dom.isActive() == 1:
                self.start_domain()
                self.connect_vnc(reconnect=True)

    def connect_vnc(self, reconnect=False):
        if self.vnc:
            if reconnect:
                self.disconnect_vnc()
            else:
                return
        self.vnc = VNCClient()
        self.vnc.add_event_listener("disconnect", self._on_vnc_disconnect)
        self.vnc.add_event_listener("screen_update", self._on_screen_update)
        self.vnc.add_event_listener("ready", self._on_vnc_ready)
        self.vnc.add_event_listener("audio_data", self._on_audio_data)
        self.vnc.start()

    async def _on_screen_update(self, image: Image.Image | None):
        if image:
            self.display_window.update_frame(image)

    async def _on_vnc_disconnect(self):
        if self.vnc and (not self.vnc.vnc.writer or self.vnc.vnc.writer.is_closing()):
            self.vnc = None

    async def _on_vnc_ready(self):
        if self.vnc:
            self.vnc.audioStreamBeginRequest()

    async def _on_audio_data(self, size: int, data: bytes):
        if len(self.audio_buffer) < 44100 * 2 * 2:
            self.audio_buffer += data
        else:
            if self.vnc and self.display_window:
                self.display_window.update_audio(self.audio_buffer)
            self.audio_buffer = b""

    def disconnect_vnc(self):
        if self.vnc:
            self.vnc.disconnect()
            self.vnc = None

    def shutdown_domain(self):
        if self.dom and self.dom.isActive() == 1:
            self.disconnect_vnc()
            self.dom.shutdown()

    def start_domain(self):
        if self.dom and not self.dom.isActive() == 1:
            self.dom.create()
            self.connect_vnc()

    def force_shutdown_domain(self):
        if self.dom and self.dom.isActive() == 1:
            self.disconnect_vnc()
            self.dom.destroy()

    def disconnect_qemu(self):
        if self.vnc:
            self.disconnect_vnc()
        if self.vm_loop:
            self.vm_loop.cancel()
            self.vm_loop = None
        if self.dom:
            self.dom = None
        if self.virt:
            self.virt.close()
            self.virt = None

    async def setup_hook(self):
        self.connect_qemu()
        self.start_domain()
        self.connect_vnc()

    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        for command in COMMANDS:
            await self.load_extension(f"commands.{command}")

    async def close(self):
        if self._closed:
            return
        self.display_window.close()
        self.display_window.join()
        self.disconnect_qemu()
        await super().close()

    async def get_screen_img(self) -> Image.Image | None:
        if not self.vnc:
            return None

        return self.vnc.screen

    def set_vcpus(self, vcpus: int):
        if self.dom:
            self.dom.setVcpusFlags(vcpus, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    def set_memory(self, memory: int):
        if self.dom:
            self.dom.setMemoryFlags(
                memory,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_DOMAIN_MEM_MAXIMUM,
            )
            self.dom.setMemoryFlags(memory, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    def set_device(
        self, path: str | None = None, type: Literal["cdrom", "floppy"] = "cdrom"
    ):
        if self.dom:
            path = str(self.image_path / self.get_current_info()["os"] / path) if path else None  # type: ignore
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

    def set_os(self, os: str):
        if self.dom:
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

    def get_current_info(self) -> VMInfo | None:
        if self.dom:
            memsize = self.dom.maxMemory()
            vcpus = self.dom.vcpus()[0][0][1]

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

            return {
                "memory": memsize / 1024,
                "cpu": vcpus,
                "cdrom": cdrom_path,
                "floppy": floppy,
                "os": os,
            }
        else:
            return None


intents = discord.Intents.default()
client = UpgradeMyWindowsBot("aaaaaaaaaaaaaaaaa", intents=intents)


client.run(os.getenv("DISCORD_TOKEN"))  # type: ignore
