import discord
import io
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


class Screenshot(CogLogger):
    @handle_exception()
    @app_commands.command(
        name="screenshot",
        description="Takes a screenshot of the VM and sends it to you.",
    )
    async def screenshot_command(self, interaction: discord.Interaction):
        self.logger.debug("Screenshot requested")
        img = await self.bot.get_screen_img()
        if not img:
            self.logger.warn("Failed to get VM screen")
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
