import discord
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


class Info(CogLogger):
    @handle_exception()
    @app_commands.command(name="info", description="Shows the current VM information.")
    async def info_command(self, interaction: discord.Interaction):
        self.logger.debug("Info requested")
        info = await self.bot.get_current_info()
        if not info:
            self.logger.warn("Failed to get VM info")
            await interaction.response.send_message("VM is not running.")
            return

        size = None
        if self.bot._is_vnc_connected and self.bot.vnc.screen:
            self.logger.warn("Failed to get VM screen")
            size = self.bot.vnc.screen.size
        embed = discord.Embed(
            title="VM Information",
            description="Information about the current VM.",
            color=0x447DD2,
        )
        embed.add_field(name="Memory", value=f"{info['memory']} MB", inline=True)
        embed.add_field(name="CPU", value=f"{info['cpu']} cores", inline=True)
        embed.add_field(
            name="Resolution",
            value=f"{size[0]}x{size[1]}" if size is not None else "Unavailable",
            inline=True,
        )
        embed.add_field(name="CD-ROM", value=info["cdrom"] or "None", inline=True)
        embed.add_field(name="Floppy", value=info["floppy"] or "None", inline=True)
        embed.add_field(
            name="OS",
            value=f"Windows {info['os'].title() if info['os'] == 'vista' else info['os'].upper()}",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
