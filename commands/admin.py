import discord
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception
from utils.is_me import is_me


class Admin(CogLogger):
    @handle_exception()
    @app_commands.command(
        name="sync",
        description="Syncs the bot's commands with Discord.",
    )
    @is_me()
    async def sync_command(self, interaction: discord.Interaction):
        self.logger.debug("Command sync requested")
        await self.bot.tree.sync()
        if interaction.guild_id:
            self.bot.tree.copy_global_to(guild=discord.Object(id=interaction.guild_id))
        await interaction.response.send_message("Commands synced.")

    @handle_exception()
    @app_commands.command(
        name="reboot",
        description="Reboots the VM.",
    )
    async def reboot_command(self, interaction: discord.Interaction):
        self.logger.debug("VM reboot requested")
        await interaction.response.defer()
        await self.bot.force_shutdown_domain()
        await self.bot.start_domain()
        await interaction.followup.send("Rebooted the VM.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
