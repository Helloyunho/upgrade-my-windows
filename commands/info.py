import discord
from discord.ext import commands
from discord import app_commands


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="info", description="Shows the current VM information.")
    async def info_command(self, interaction: discord.Interaction):
        info = self.bot.get_current_info()
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
