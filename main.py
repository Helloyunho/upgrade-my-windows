import asyncio
import discord
import asyncvnc
import libvirt
import io
import os
from PIL import Image
from discord import app_commands
from xml.dom import minidom
from dotenv import load_dotenv

from typings.vminfo import VMInfo
from typing import Literal

load_dotenv()


class MyClient(discord.Client):
    virt: libvirt.virConnect | None
    dom: libvirt.virDomain | None
    vnc: asyncvnc.Client | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.virt = None
        self.dom = None
        self.vnc = None

    async def connect_qemu(self, reconnect=False):
        if self.virt or self.dom or self.vnc:
            if reconnect:
                await self.disconnect_qemu()
            else:
                return
        self.virt = libvirt.open()
        self.dom = self.virt.lookupByUUIDString(os.getenv("VIRT_DOMAIN_UUID"))
        if not self.vnc:
            reader, writer = await asyncio.open_unix_connection("/tmp/umw-vnc.sock")
            self.vnc = await asyncvnc.Client.create(reader, writer, None, None, None)

    async def shutdown_domain(self):
        if self.dom and self.dom.isActive():
            self.dom.shutdown()

    async def start_domain(self):
        if self.dom and not self.dom.isActive():
            self.dom.create()

    async def force_shutdown_domain(self):
        if self.dom and self.dom.isActive():
            self.dom.destroy()

    async def disconnect_qemu(self):
        if self.dom:
            self.dom = None
        if self.virt:
            self.virt.close()
            self.virt = None
        if self.vnc and self.vnc.writer:
            self.vnc.writer.close()
            await self.vnc.writer.wait_closed()
            self.vnc = None

    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        await self.connect_qemu()

    async def on_disconnect(self):
        await self.disconnect_qemu()

    async def get_screen_img(self) -> Image.Image | None:
        if not self.vnc:
            return None

        pixels = await self.vnc.screenshot()
        image = Image.fromarray(pixels)
        return image

    def set_vcpus(self, vcpus: int):
        if self.dom:
            self.dom.setVcpusFlags(vcpus, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    def set_memory(self, memory: int):
        if self.dom:
            self.dom.setMemoryFlags(memory * 1024, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

    def set_cdrom(self, path: str, type: Literal["cdrom", "floppy"] = "cdrom"):
        if self.dom:
            raw_xml = self.dom.XMLDesc()
            xml = minidom.parseString(raw_xml)
            disks = xml.getElementsByTagName("disk")
            for disk in disks:
                if disk.getAttribute("device") == type:
                    disk.getElementsByTagName("source")[0].setAttribute("file", path)
                    self.dom.updateDeviceFlags(
                        disk.toxml("utf8").decode(),
                        libvirt.VIR_DOMAIN_AFFECT_CURRENT
                        | libvirt.VIR_DOMAIN_AFFECT_LIVE
                        | libvirt.VIR_DOMAIN_AFFECT_CONFIG,
                    )
                    break

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
                .title()
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


@tree.command(name="help")
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
        name="`/change os:`",
        value="Changes the vm preset(memory size, cpu core count, etc.) and disc(or floppy disk) image to selected OS.",
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
    await interaction.response.send_message(embed=embed)


@tree.command(name="info")
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
    embed.add_field(name="OS", value=info["os"], inline=True)
    await interaction.response.send_message(embed=embed)


@tree.command(name="screenshot")
async def screenshot_command(interaction: discord.Interaction):
    img = await client.get_screen_img()
    if not img:
        await interaction.response.send_message("VM is not running.")
        return

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")

    await interaction.response.send_message(
        file=discord.File(img_bytes, "screenshot.png")
    )
    img_bytes.close()
    img.close()


@tree.command(name="click")
@app_commands.describe(prompt="Describe the element you want to click.")
async def click_command(interaction: discord.Interaction, prompt: str):
    # TODO: Ask the AI to click the element
    await interaction.response.send_message("Not implemented yet.")


@tree.command(name="type")
@app_commands.describe(text="The text you want to type.")
async def type_command(interaction: discord.Interaction, text: str):
    if not client.vnc:
        await interaction.response.send_message("VM is not running.")
        return
    client.vnc.keyboard.write(text)


client.run(os.getenv("DISCORD_TOKEN"))  # type: ignore
