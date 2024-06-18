import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal

from config import os_list


class Change(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        self,
        interaction: discord.Interaction,
        os: str,
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        os_preset = next((preset for preset in os_list if preset["os"] == os), None)
        if not os_preset:
            await interaction.response.send_message("OS not found.")
            return

        self.bot.set_vcpus(os_preset["vcpus"])
        self.bot.set_memory(os_preset["memory"])
        self.bot.set_os(os)
        if os_preset["cdrom"]:
            self.bot.set_device(os_preset["cdrom"][0])
        else:
            self.bot.set_device()
        if os_preset["floppy"]:
            self.bot.set_device(os_preset["floppy"][0], "floppy")
        else:
            self.bot.set_device(type="floppy")

        await interaction.response.send_message(
            "VM has been updated. Restart(or shut down) the VM to apply the cpu and memory changes."
        )

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
        self,
        interaction: discord.Interaction,
        type: Literal["cdrom", "floppy"],
        image: str,
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        info = self.bot.get_current_info()
        if not info:
            await interaction.response.send_message("VM is not running.")
            return

        os_preset = next(
            (preset for preset in os_list if preset["os"] == info["os"]), None
        )
        if not os_preset:
            await interaction.response.send_message(
                "OS not found. Which is impossible. Please contact the developer."
            )
            return

        if not os_preset[type]:
            await interaction.response.send_message(
                f"{type} image for this OS not found."
            )
            return
        try:
            index = os_preset[type].index(image)  # type: ignore
        except ValueError:
            await interaction.response.send_message("Image not found.")
            return
        self.bot.set_device(os_preset[type][index], type)  # type: ignore

        await interaction.response.send_message("Image has been updated.")

    @change_image_command.autocomplete("image")
    async def change_image_image_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        info = self.bot.get_current_info()
        if not info:
            return []

        os_preset = next(
            (preset for preset in os_list if preset["os"] == info["os"]), None
        )
        if not os_preset:
            return []

        type_ = next((option for option in interaction.data["options"][0]["options"] if option["name"] == "type"), None)  # type: ignore
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


async def setup(bot):
    await bot.add_cog(Change(bot))
