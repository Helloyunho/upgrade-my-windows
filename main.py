import asyncio
import discord
from vncdotool.client import VNCDoToolClient
import libvirt
import io
import os
from pathlib import Path
from PIL import Image
from discord import app_commands
from xml.dom import minidom
from dotenv import load_dotenv

from typings.vminfo import VMInfo
from typing import Literal

from config import os_list

load_dotenv()


class MyClient(discord.Client):
    virt: libvirt.virConnect | None
    dom: libvirt.virDomain | None
    vnc: VNCDoToolClient | None
    image_path: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.virt = None
        self.dom = None
        self.vnc = None
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
        asyncio.create_task(self.vnc_refresh_loop())

    async def vnc_refresh_loop(self):
        while self.vnc:
            await asyncio.sleep(1 / 60)
            await self.vnc.refreshScreen()

    async def disconnect_vnc(self):
        if self.vnc:
            await self.vnc.disconnect()
            self.vnc = None

    async def shutdown_domain(self):
        if self.dom and self.dom.isActive():
            await self.disconnect_vnc()
            self.dom.shutdown()

    async def start_domain(self):
        if self.dom and not self.dom.isActive():
            self.dom.create()
            await self.connect_vnc()

    async def force_shutdown_domain(self):
        if self.dom and self.dom.isActive():
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
        await self.connect_qemu()
        await self.start_domain()
        await self.connect_vnc()

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
            self.dom.setMemoryFlags(memory * 1024, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

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
                    cdrom_path = (
                        disk.getElementsByTagName("source")[0]
                        .getAttribute("file")
                        .split("/")[-1]
                    )
                    continue
                if disk.getAttribute("device") == "floppy" and floppy is None:
                    floppy = (
                        disk.getElementsByTagName("source")[0]
                        .getAttribute("file")
                        .split("/")[-1]
                    )
                    continue
                if cdrom_path and floppy:
                    break

            return {
                "memory": memsize // 1024,
                "cpu": vcpus,
                "cdrom": cdrom_path,
                "floppy": floppy,
                "os": os,
            }
        else:
            return None


intents = discord.Intents.default()
client = MyClient(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="help", description="Shows the help message.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Upgrade My Windows",
        description="You upgrades my Windows VM from 1.0 to 10!",
        color=0x447DD2,
    )
    embed.add_field(
        name="`/click prompt:`",
        value="Clicks the element. The AI will interpret your prompt and the bot will click the corresponding element. For example, you can ask it to click 'Next' button.",
        inline=True,
    )
    embed.add_field(
        name="`/type text:`",
        value="Types the text like you would type on your keyboard. Nothing special...",
        inline=True,
    )
    embed.add_field(
        name="`/change os os:`",
        value="Changes the vm preset(memory size, cpu core count, etc.) and disc(or floppy disk) image selection to selected OS.",
        inline=True,
    )
    embed.add_field(
        name="`/change image type: image:`",
        value="Changes the disc(or floppy disk) image to selected image.",
        inline=True,
    )
    embed.add_field(
        name="`/eject type:`",
        value="Ejects the disc(or floppy disk, or both).",
        inline=True,
    )
    embed.add_field(
        name="`/screenshot`",
        value="Takes a screenshot of the VM and sends it to you.",
        inline=True,
    )
    embed.add_field(
        name="`/info`",
        value="Shows the current VM information.",
        inline=True,
    )
    embed.add_field(name="`/help`", value="Shows this help message.", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="info", description="Shows the current VM information.")
async def info_command(interaction: discord.Interaction):
    info = client.get_current_info()
    if not info:
        await interaction.response.send_message("VM is not running.")
        return

    embed = discord.Embed(
        title="VM Information",
        description="Information about the current VM.",
        color=0x447DD2,
    )
    embed.add_field(name="Memory", value=f"{info['memory']} MB", inline=True)
    embed.add_field(name="CPU", value=f"{info['cpu']} cores", inline=True)
    embed.add_field(name="CD-ROM", value=info["cdrom"] or "None", inline=True)
    embed.add_field(name="Floppy", value=info["floppy"] or "None", inline=True)
    embed.add_field(
        name="OS",
        value=f"Windows {info['os'].title() if info['os'] == 'vista' else info['os'].upper()}",
        inline=True,
    )
    await interaction.response.send_message(embed=embed)


@tree.command(
    name="screenshot", description="Takes a screenshot of the VM and sends it to you."
)
async def screenshot_command(interaction: discord.Interaction):
    img = await client.get_screen_img()
    if not img:
        await interaction.response.send_message("VM is not running.")
        return

    with io.BytesIO() as image_binary:
        img.save(image_binary, format="PNG")
        image_binary.seek(0)
        await interaction.response.send_message(
            file=discord.File(image_binary, filename="screenshot.png")
        )


@tree.command(name="click", description="Clicks the element.")
@app_commands.describe(prompt="Describe the element you want to click.")
async def click_command(interaction: discord.Interaction, prompt: str):
    # TODO: Ask the AI to click the element
    await interaction.response.send_message("Not implemented yet.")


@tree.command(
    name="type",
    description="Types the text like you would type on your keyboard. Nothing special...",
)
@app_commands.describe(text="The text you want to type.")
async def type_command(interaction: discord.Interaction, text: str):
    if not client.vnc:
        await interaction.response.send_message("VM is not running.")
        return
    for char in text:
        await client.vnc.keyDown(char)
        await client.vnc.keyUp(char)

    await interaction.response.send_message("Text has been typed.")


change_group = app_commands.Group(name="change", description="Change VM settings.")


@change_group.command(
    name="os",
    description="Changes the vm preset and disk image selection to selected OS.",
)
@app_commands.describe(
    os="The OS you want to change to.",
)
@app_commands.choices(
    os=[
        app_commands.Choice(
            name=f"Windows {os_name.title() if os_name == 'vista' else os_name.upper()}",
            value=os_name,
        )
        for os_name in [preset["os"] for preset in os_list]
    ]
)
async def change_os_command(
    interaction: discord.Interaction,
    os: str,
):
    if not client.vnc:
        await interaction.response.send_message("VM is not running.")
        return

    os_preset = next((preset for preset in os_list if preset["os"] == os), None)
    if not os_preset:
        await interaction.response.send_message("OS not found.")
        return

    client.set_vcpus(os_preset["vcpus"])
    client.set_memory(os_preset["memory"])
    client.set_os(os)
    if os_preset["cdrom"]:
        client.set_device(os_preset["cdrom"][0])
    else:
        client.set_device()
    if os_preset["floppy"]:
        client.set_device(os_preset["floppy"][0], "floppy")
    else:
        client.set_device(type="floppy")

    await interaction.response.send_message("VM has been updated.")


@change_group.command(
    name="image",
    description="Changes the disc(or floppy disk) image to selected image.",
)
@app_commands.describe(
    type="The type of the device you want to change.",
    image="The image you want to change.",
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="CD-ROM", value="cdrom"),
        app_commands.Choice(name="Floppy", value="floppy"),
    ]
)
async def change_image_command(
    interaction: discord.Interaction,
    type: Literal["cdrom", "floppy"],
    image: str,
):
    if not client.vnc:
        await interaction.response.send_message("VM is not running.")
        return

    info = client.get_current_info()
    if not info:
        await interaction.response.send_message("VM is not running.")
        return

    os_preset = next((preset for preset in os_list if preset["os"] == info["os"]), None)
    if not os_preset:
        await interaction.response.send_message(
            "OS not found. Which is impossible. Please contact the developer."
        )
        return

    if not os_preset[type]:
        await interaction.response.send_message(f"{type} image for this OS not found.")
        return
    try:
        index = os_preset[type].index(image)  # type: ignore
    except ValueError:
        await interaction.response.send_message("Image not found.")
        return
    client.set_device(os_preset[type][index])  # type: ignore

    await interaction.response.send_message("Image has been updated.")


@change_image_command.autocomplete("image")
async def change_image_image_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    info = client.get_current_info()
    if not info:
        return []

    os_preset = next((preset for preset in os_list if preset["os"] == info["os"]), None)
    if not os_preset:
        return []

    type_ = next((option for option in interaction.data["options"] if option["name"] == "type"), None)  # type: ignore
    if not type_:
        return []
    type_: str = type_["value"]  # type: ignore

    if not os_preset[type_]:
        return []

    return [
        app_commands.Choice(name=image, value=image)
        for image in os_preset[type_]
        if image.lower().startswith(current.lower())
    ]


tree.add_command(change_group)


@tree.command(name="eject", description="Ejects the disc(or floppy disk, or both).")
@app_commands.describe(type="The type of the device you want to eject.")
@app_commands.choices(
    type=[
        app_commands.Choice(name="CD-ROM", value="cdrom"),
        app_commands.Choice(name="Floppy", value="floppy"),
        app_commands.Choice(name="Both", value="both"),
    ]
)
async def eject_command(
    interaction: discord.Interaction, type: Literal["cdrom", "floppy", "both"]
):
    if not client.vnc:
        await interaction.response.send_message("VM is not running.")
        return

    if type == "both":
        client.set_device(None)
        client.set_device(None, "floppy")
        await interaction.response.send_message("Both devices have been ejected.")
    else:
        client.set_device(None, type)
        await interaction.response.send_message("Device has been ejected.")


client.run(os.getenv("DISCORD_TOKEN"))  # type: ignore
