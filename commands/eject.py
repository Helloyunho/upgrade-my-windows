import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal


class Eject(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
    async def eject_command(
        self, interaction: discord.Interaction, type: Literal["cdrom", "floppy", "both"]
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        if type == "both":
            self.bot.set_device(None)
            self.bot.set_device(None, "floppy")
            await interaction.response.send_message("Both devices have been ejected.")
        else:
            self.bot.set_device(None, type)
            await interaction.response.send_message("Device has been ejected.")


async def setup(bot):
    await bot.add_cog(Eject(bot))
