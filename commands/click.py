import discord
from discord.ext import commands
from discord import app_commands


class Click(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="click", description="Clicks the element.")
    @app_commands.describe(prompt="Describe the element you want to click.")
    async def click_command(self, interaction: discord.Interaction, prompt: str):
        # TODO: Ask the AI to click the element
        await interaction.response.send_message("Not implemented yet.")
