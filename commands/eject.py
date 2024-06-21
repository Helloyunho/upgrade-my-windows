import discord
from discord import app_commands
from typing import Literal
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


class Eject(CogLogger):
    @app_commands.command(
        name="eject", description="Ejects the disc(or floppy disk, or both)."
    )
    @app_commands.describe(type="The type of the device you want to eject.")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="CD-ROM", value="cdrom"),
            app_commands.Choice(name="Floppy", value="floppy"),
            app_commands.Choice(name="Both", value="both"),
        ]
    )
    @handle_exception()
    async def eject_command(
        self, interaction: discord.Interaction, type: Literal["cdrom", "floppy", "both"]
    ):
        self.logger.debug(f"Ejecting {type} requested")
        if not self.bot._is_vm_running:
            self.logger.warn("VM is not running")
            await interaction.response.send_message("VM is not running.")
            return

        if type == "both":
            await self.bot.set_device(None)
            await self.bot.set_device(None, "floppy")
            await interaction.response.send_message("Both devices have been ejected.")
        else:
            await self.bot.set_device(None, type)
            await interaction.response.send_message("Device has been ejected.")


async def setup(bot):
    await bot.add_cog(Eject(bot))
