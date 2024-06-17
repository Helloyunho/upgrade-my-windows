import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from utils.is_me import is_me


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="sync",
        description="Syncs the bot's commands with Discord.",
    )
    @is_me()
    async def sync_command(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        self.bot.tree.copy_global_to(guild=discord.Object(id=interaction.guild_id))  # type: ignore
        await interaction.response.send_message("Commands synced.")

    @app_commands.command(
        name="reboot",
        description="Reboots the VM.",
    )
    @is_me()
    async def reboot_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.bot.force_shutdown_domain()
        await asyncio.sleep(2)
        self.bot.start_domain()
        await interaction.followup.send("Restarted the VM.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
