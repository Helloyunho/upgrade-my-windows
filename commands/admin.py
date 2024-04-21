import discord
from discord.ext import commands
from discord import app_commands

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
        await self.bot.tree.copy_global_to(guild=discord.Object(id=interaction.guild_id))  # type: ignore
        await self.bot.tree.sync()
        await interaction.response.send_message("Commands synced.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
