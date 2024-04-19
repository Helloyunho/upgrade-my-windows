import discord
import io
from discord.ext import commands
from discord import app_commands


class Screenshot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="screenshot",
        description="Takes a screenshot of the VM and sends it to you.",
    )
    async def screenshot_command(self, interaction: discord.Interaction):
        img = await self.bot.get_screen_img()
        if not img:
            await interaction.response.send_message("VM is not running.")
            return

        with io.BytesIO() as image_binary:
            img.save(image_binary, format="PNG")
            image_binary.seek(0)
            await interaction.response.send_message(
                file=discord.File(image_binary, filename="screenshot.png")
            )


async def setup(bot):
    await bot.add_cog(Screenshot(bot))
