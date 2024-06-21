import discord
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


class Help(CogLogger):
    @handle_exception()
    @app_commands.command(name="help", description="Shows the help message.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Upgrade My Windows",
            description="You upgrades my Windows VM from 1.0 to 10!",
            color=0x447DD2,
        )
        embed.add_field(
            name="`/click prompt:`",
            value="Clicks the element. The AI will interpret your prompt and the bot will click the corresponding element. For example, you can ask it to click 'Next' button.",
            inline=True,
        )
        embed.add_field(
            name="`/type text:`",
            value="Types the text like you would type on your keyboard. Nothing special...",
            inline=True,
        )
        embed.add_field(
            name="`/change os os:`",
            value="Changes the vm preset(memory size, cpu core count, etc.) and disc(or floppy disk) image selection to selected OS.",
            inline=True,
        )
        embed.add_field(
            name="`/change image type: image:`",
            value="Changes the disc(or floppy disk) image to selected image.",
            inline=True,
        )
        embed.add_field(
            name="`/eject type:`",
            value="Ejects the disc(or floppy disk, or both).",
            inline=True,
        )
        embed.add_field(
            name="`/screenshot`",
            value="Takes a screenshot of the VM and sends it to you.",
            inline=True,
        )
        embed.add_field(
            name="`/info`",
            value="Shows the current VM information.",
            inline=True,
        )
        embed.add_field(name="`/help`", value="Shows this help message.", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
