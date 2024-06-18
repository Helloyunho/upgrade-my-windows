import discord
from discord.ext import commands
from discord import app_commands
import asyncio


MOUSE_BUTTONS = {"left": 1, "middle": 2, "right": 3}

WHEEL_BUTTONS = {
    "up": 4,
    "down": 5,
    "left": 6,
    "right": 7,
}


class Mouse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    move_group = app_commands.Group(name="move", description="Moves the element.")

    @move_group.command(name="ai", description="Moves the element using AI.")
    @app_commands.describe(
        prompt="Describe the element you want to move the mouse cursor to."
    )
    async def move_command(self, interaction: discord.Interaction, prompt: str):
        # TODO: Ask the AI to move to the element
        await interaction.response.send_message("Not implemented yet.")

    @move_group.command(
        name="xy",
        description="Moves the mouse using XY coordinates. (0, 0) is the top-left corner.",
    )
    @app_commands.describe(x="The X coordinate.", y="The Y coordinate.")
    async def move_xy_command(self, interaction: discord.Interaction, x: int, y: int):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseMove(x, y)

        await interaction.followup.send(f"Moved the mouse cursor to {x}, {y}.")

    @app_commands.command(
        name="drag",
        description="Moves the mouse relatively using XY coordinates.",
    )
    @app_commands.describe(
        x="The X coordinate.",
        y="The Y coordinate.",
        step="How many coordinates to move per 200ms. Default is 10.",
    )
    async def move_xy_command(
        self, interaction: discord.Interaction, x: int, y: int, step: int = 10
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseDrag(x, y, step)

        await interaction.followup.send(f"Moved the mouse cursor to {x}, {y}.")

    @app_commands.command(name="click", description="Clicks the mouse.")
    @app_commands.describe(button="The button to click.")
    @app_commands.choices(
        button=[
            app_commands.Choice(name="Left", value="left"),
            app_commands.Choice(name="Middle", value="middle"),
            app_commands.Choice(name="Right", value="right"),
        ]
    )
    async def click_command(
        self, interaction: discord.Interaction, button: str = "left"
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseDown(button_code)
        await asyncio.sleep(0.001)
        self.bot.vnc.mouseUp(button_code)

        await interaction.followup.send("Clicked the mouse.")

    @app_commands.command(name="scroll", description="Scrolls the mouse.")
    @app_commands.describe(
        direction="The direction to scroll.", amount="The amount to scroll."
    )
    @app_commands.choices(
        direction=[
            app_commands.Choice(name="Up", value="up"),
            app_commands.Choice(name="Down", value="down"),
            app_commands.Choice(name="Left", value="left"),
            app_commands.Choice(name="Right", value="right"),
        ]
    )
    async def scroll_command(
        self, interaction: discord.Interaction, direction: str = "up", amount: int = 1
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        direction_code = WHEEL_BUTTONS.get(direction.lower())
        if not direction_code:
            await interaction.response.send_message("Invalid direction.")
            return

        amount = max(1, amount)

        await interaction.response.defer()
        for _ in range(amount):
            self.bot.vnc.mousePress(direction_code)

        await interaction.followup.send("Scrolled the mouse.")

    mouse_group = app_commands.Group(name="mouse", description="Controls the mouse.")

    @mouse_group.command(name="down", description="Presses a mouse button.")
    @app_commands.describe(button="The button to press.")
    @app_commands.choices(
        button=[
            app_commands.Choice(name="Left", value="left"),
            app_commands.Choice(name="Middle", value="middle"),
            app_commands.Choice(name="Right", value="right"),
        ]
    )
    async def mouse_down_command(
        self, interaction: discord.Interaction, button: str = "left"
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseDown(button_code)

        await interaction.followup.send("Pressed the mouse button.")

    @mouse_group.command(name="up", description="Depresses a mouse button.")
    @app_commands.describe(button="The button to depress.")
    @app_commands.choices(
        button=[
            app_commands.Choice(name="Left", value="left"),
            app_commands.Choice(name="Middle", value="middle"),
            app_commands.Choice(name="Right", value="right"),
        ]
    )
    async def mouse_up_command(
        self, interaction: discord.Interaction, button: str = "left"
    ):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseUp(button_code)

        await interaction.followup.send("Depressed the mouse button.")


async def setup(bot):
    await bot.add_cog(Mouse(bot))
