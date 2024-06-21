import discord
from config import os_list
from discord import app_commands
from typing import Literal
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


class Change(CogLogger):
    change_group = app_commands.Group(name="change", description="Change VM settings.")

    @handle_exception()
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
        self.logger.debug(f"Changing OS to {os} requested")
        if not self.bot._is_vm_running:
            self.logger.warn("VM is not running")
            await interaction.response.send_message("VM is not running.")
            return

        os_preset = next((preset for preset in os_list if preset["os"] == os), None)
        if not os_preset:
            self.logger.warn(f"OS {os} not found")
            await interaction.response.send_message("OS not found.")
            return

        await self.bot.set_vcpus(os_preset["vcpus"])
        await self.bot.set_memory(os_preset["memory"])
        await self.bot.set_os(os)
        if os_preset["cdrom"]:
            await self.bot.set_device(os_preset["cdrom"][0])
        else:
            await self.bot.set_device()
        if os_preset["floppy"]:
            await self.bot.set_device(os_preset["floppy"][0], "floppy")
        else:
            await self.bot.set_device(type="floppy")

        await interaction.response.send_message(
            "VM has been updated. Restart(or shut down) the VM to apply the cpu and memory changes."
        )

    @handle_exception()
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
        self.logger.debug(f"Changing {type} image to {image} requested")
        info = await self.bot.get_current_info()
        if not self.bot._is_vm_running or not info:
            self.logger.warn("VM is not running")
            await interaction.response.send_message("VM is not running.")
            return

        os_preset = next(
            (preset for preset in os_list if preset["os"] == info["os"]), None
        )
        if not os_preset:
            self.logger.error(f"OS {info['os']} not found which is impossible")
            await interaction.response.send_message(
                "OS not found. Which is impossible. Please contact the developer."
            )
            return

        if not os_preset[type]:
            self.logger.warn(f"{type} image not found for {info['os']}")
            await interaction.response.send_message(
                f"{type} image for this OS not found."
            )
            return
        try:
            index = os_preset[type].index(image)  # type: ignore
        except ValueError:
            self.logger.warn(f"Image {image} not found")
            await interaction.response.send_message("Image not found.")
            return
        await self.bot.set_device(os_preset[type][index], type)  # type: ignore

        await interaction.response.send_message("Image has been updated.")

    @handle_exception()
    @change_image_command.autocomplete("image")
    async def change_image_image_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        self.logger.debug(f"Autocompletion for image {current} requested")
        info = await self.bot.get_current_info()
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

        choices = [
            app_commands.Choice(name=image, value=image)
            for image in os_preset[type_]
            if image.lower().startswith(current.lower())
        ][:25]

        self.logger.debug(f"Provided {len(choices)} choices")
        return choices


async def setup(bot):
    await bot.add_cog(Change(bot))
