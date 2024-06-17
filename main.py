import asyncio
import discord
from vncdotool.client import VNCDoToolClient
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

FPS = 15

load_dotenv()


class UpgradeMyWindowsBot(commands.Bot):
    virt: libvirt.virConnect | None
    dom: libvirt.virDomain | None
    vnc: VNCDoToolClient | None
    vnc_loop_task: asyncio.Task | None
    image_path: Path
    display_window: DisplayWindow

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.virt = None
        self.dom = None
        self.vnc = None
        self.vnc_loop_task = None
        self.image_path = Path(os.getenv("IMAGE_PATH") or "./images")

    async def connect_qemu(self, reconnect=False):
        if self.virt or self.dom or self.vnc:
            if reconnect:
                await self.disconnect_qemu()
            else:
                return
        self.virt = libvirt.open()
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))

    async def connect_vnc(self, reconnect=False):
        if self.vnc:
            if reconnect:
                await self.disconnect_vnc()
            else:
                return
        self.vnc = VNCDoToolClient()
        reader, writer = await asyncio.open_unix_connection("/tmp/umw-vnc.sock")
        # reader, writer = await asyncio.open_connection("localhost", 5900)
        await self.vnc.connect(reader, writer)
        self.vnc_loop_task = asyncio.create_task(self.vnc_refresh_loop())

    async def vnc_refresh_loop(self):
        while self.vnc:
            await asyncio.sleep(1 / FPS)
            if self.vnc.writer.is_closing():
                self.vnc = None
                break
            await self.vnc.refreshScreen()
            asyncio.create_task(self.show_screen())

    async def show_screen(self):
        if self.vnc and self.vnc.screen:
            self.display_window.update_frame(self.vnc.screen)

    async def disconnect_vnc(self):
        if self.vnc_loop_task:
            self.vnc_loop_task.cancel()
            self.vnc_loop_task = None
        if self.vnc:
            await self.vnc.disconnect()
            self.vnc = None

    async def shutdown_domain(self):
        if self.dom and self.dom.isActive() == 1:
            await self.disconnect_vnc()
            self.dom.shutdown()

    async def start_domain(self):
        if self.dom and not self.dom.isActive() == 1:
            self.dom.create()
            await self.connect_vnc()

    async def force_shutdown_domain(self):
        if self.dom and self.dom.isActive() == 1:
            await self.disconnect_vnc()
            self.dom.destroy()

    async def disconnect_qemu(self):
        if self.vnc:
            await self.disconnect_vnc()
        if self.dom:
            self.dom = None
        if self.virt:
            self.virt.close()
            self.virt = None

    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        self.display_window = DisplayWindow()
        asyncio.create_task(self.display_window.pygame_loop())
        await self.connect_qemu()
        await self.start_domain()
        await self.connect_vnc()
        for command in COMMANDS:
            await self.load_extension(f"commands.{command}")

    async def on_disconnect(self):
        await self.disconnect_qemu()

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
