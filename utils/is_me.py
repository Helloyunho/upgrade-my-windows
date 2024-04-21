import discord
from discord import app_commands
import os


def is_me():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == os.getenv("OWNER_ID")

    return app_commands.check(predicate)
