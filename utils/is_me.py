import discord
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()


def is_me():
    def predicate(interaction: discord.Interaction):
        owner_id = os.getenv("OWNER_ID")
        if owner_id is None:
            raise ValueError("OWNER_ID is not set in the environment variables.")
        return interaction.user.id == int(owner_id)

    return app_commands.check(predicate)
