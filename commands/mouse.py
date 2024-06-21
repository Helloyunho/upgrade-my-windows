import asyncio
import discord
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception


MOUSE_BUTTONS = {"left": 1, "middle": 2, "right": 3}

WHEEL_BUTTONS = {
    "up": 4,
    "down": 5,
    "left": 6,
    "right": 7,
}


class Mouse(CogLogger):
    move_group = app_commands.Group(name="move", description="Moves the element.")

    @handle_exception()
    @move_group.command(name="ai", description="Moves the element using AI.")
    @app_commands.describe(
        prompt="Describe the element you want to move the mouse cursor to."
    )
    async def move_command(self, interaction: discord.Interaction, prompt: str):
        # TODO: Ask the AI to move to the element
        await interaction.response.send_message("Not implemented yet.")

    @handle_exception()
    @move_group.command(
        name="xy",
        description="Moves the mouse using XY coordinates. (0, 0) is the top-left corner.",
    )
    @app_commands.describe(
        x="The X coordinate.",
        y="The Y coordinate.",
        relative="Whether the coordinates are relative to the current position.",
    )
    async def move_xy_command(
        self, interaction: discord.Interaction, x: int, y: int, relative: bool = False
    ):
        self.logger.debug(f"Moving the mouse to {x}, {y} requested")
        if not self.bot._is_vnc_connected or not self.bot.vnc.screen:
            self.logger.warn("VNC is not connected or screen is not available")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        if relative:
            x += self.bot.vnc.x
            y += self.bot.vnc.y

        if (
            x < -1
            or y < -1
            or x > self.bot.vnc.screen.size[0]
            or y > self.bot.vnc.screen.size[1]
        ):
            self.logger.debug("Request cancelled due to coordinates out of bounds")
            await interaction.followup.send("Coordinates are out of bounds.")
            return

        self.bot.vnc.mouseMove(x, y)

        await interaction.followup.send(f"Moved the mouse cursor to {x}, {y}.")

    @handle_exception()
    @move_group.command(
        name="center",
        description="Moves the mouse to the center of the screen.",
    )
    async def move_center_command(self, interaction: discord.Interaction):
        self.logger.debug("Moving mouse to center requested")
        if not self.bot._is_vnc_connected or not self.bot.vnc.screen:
            self.logger.warn("VNC is not connected or screen is not available")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        x = self.bot.vnc.screen.size[0] // 2
        y = self.bot.vnc.screen.size[1] // 2

        self.bot.vnc.mouseMove(x, y)

        await interaction.followup.send(f"Moved the mouse to the center of the screen.")

    @handle_exception()
    @app_commands.command(
        name="reset_cursor",
        description="Resets the mouse cursor to the top-left of the screen.",
    )
    async def reset_cursor_command(self, interaction: discord.Interaction):
        self.logger.debug("Resetting the mouse cursor requested")
        if not self.bot._is_vnc_connected or not self.bot.vnc.screen:
            self.logger.warn("VNC is not connected or screen is not available")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseMove(self.bot.vnc.screen.size[0], self.bot.vnc.screen.size[1])
        await asyncio.sleep(0.01)
        self.bot.vnc.mouseMove(0, 0)

        await interaction.followup.send("Reset the mouse cursor.")

    @handle_exception()
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
        self.logger.debug(f"Clicking the {button} button requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            self.logger.debug("Request cancelled due to requesting invalid button")
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseDown(button_code)
        await asyncio.sleep(0.001)
        self.bot.vnc.mouseUp(button_code)

        await interaction.followup.send("Clicked the mouse.")

    @handle_exception()
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
        self.logger.debug(f"Scrolling the mouse {direction} requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        direction_code = WHEEL_BUTTONS.get(direction.lower())
        if not direction_code:
            self.logger.debug("Request cancelled due to requesting invalid direction")
            await interaction.response.send_message("Invalid direction.")
            return

        amount = max(1, amount)

        await interaction.response.defer()
        for _ in range(amount):
            self.bot.vnc.mousePress(direction_code)

        await interaction.followup.send("Scrolled the mouse.")

    mouse_group = app_commands.Group(name="mouse", description="Controls the mouse.")

    @handle_exception()
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
        self.logger.debug(f"Pressing the {button} button requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            self.logger.debug("Request cancelled due to requesting invalid button")
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseDown(button_code)

        await interaction.followup.send("Pressed the mouse button.")

    @handle_exception()
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
        self.logger.debug(f"Depressing the {button} button requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        button_code = MOUSE_BUTTONS.get(button.lower())
        if not button_code:
            self.logger.debug("Request cancelled due to requesting invalid button")
            await interaction.response.send_message("Invalid button.")
            return

        await interaction.response.defer()
        self.bot.vnc.mouseUp(button_code)

        await interaction.followup.send("Depressed the mouse button.")


async def setup(bot):
    await bot.add_cog(Mouse(bot))
