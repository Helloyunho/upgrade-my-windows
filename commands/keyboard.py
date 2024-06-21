import asyncio
import codecs
import discord
import regex as re
from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception
from vncdotool.client import KEYMAP


TYPE_DELAY = 0.001

BACKTICK_RE = re.compile(r"(?<=(?<!\\)(?:\\\\)*)`((?:[^`\\]|\\.)*)`")
HYPEN_RE = re.compile(r"(?<=(?<!\\)(?:\\\\)*)-")

BACKSLASH_KEYMAP = {
    "\n": 0xFF0D,
    "\t": 0xFF09,
    "\r": 0xFF0D,
    "\b": 0xFF08,
    "\x1b": 0xFF1B,
}

for value in KEYMAP.values():
    BACKSLASH_KEYMAP[chr(value)] = value


class Keyboard(CogLogger):
    @handle_exception()
    async def char_split_press(
        self, text: str, key_down: bool = True, key_up: bool = True
    ):
        if not self.bot._is_vnc_connected:
            return

        for char in text:
            char = chr(BACKSLASH_KEYMAP[char]) if char in BACKSLASH_KEYMAP else char
            if key_down:
                self.bot.vnc.keyDown(char)
                await asyncio.sleep(TYPE_DELAY)
            if key_up:
                self.bot.vnc.keyUp(char)
                await asyncio.sleep(TYPE_DELAY)

    @handle_exception()
    async def key_press(self, text: str, key_down: bool = True, key_up: bool = True):
        self.logger.debug(f"Typing {text}")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            return

        # match backticks
        matches = BACKTICK_RE.findall(text)
        # split backticks and escape backslashes
        texts = [
            codecs.escape_decode(text.encode("utf-8"))[0].decode("utf-8")  # type: ignore - escape_decode returns Tuple[bytes, int]
            for text in BACKTICK_RE.split(text)[::2]
        ]

        for match, text in zip(matches, texts):
            await self.char_split_press(text, key_down, key_up)

            match_sequences = HYPEN_RE.split(match)
            length = len(match_sequences)
            for i, sequence in enumerate(match_sequences * 2):
                converted = KEYMAP.get(sequence)
                if converted:
                    if key_down and (i - length) < 0:
                        self.bot.vnc.keyDown(chr(converted))
                        await asyncio.sleep(TYPE_DELAY)
                    elif key_up and (i - length) >= 0:
                        self.bot.vnc.keyUp(chr(converted))
                        await asyncio.sleep(TYPE_DELAY)
                else:
                    if key_down and (i - length) < 0:
                        await self.char_split_press(sequence, key_down, False)
                    elif key_up and (i - length) >= 0:
                        await self.char_split_press(sequence, False, key_up)

        if len(texts) > len(matches):
            await self.char_split_press(texts[-1], key_down, key_up)

    @app_commands.command(
        name="type",
        description="Types the text like you would type on your keyboard. Nothing special...",
    )
    @app_commands.describe(text="The text you want to type.")
    @handle_exception()
    async def type_command(self, interaction: discord.Interaction, text: str):
        self.logger.debug(f"Typing {text} requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        await self.key_press(text)

        await interaction.followup.send("Text has been typed.")

    key_group = app_commands.Group(
        name="key", description="Presses(or depresses) a key."
    )

    @key_group.command(name="down", description="Presses a key.")
    @app_commands.describe(key="The key you want to press.")
    @handle_exception()
    async def key_down_command(self, interaction: discord.Interaction, key: str):
        self.logger.debug(f"Pressing {key} requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        await self.key_press(key, key_up=False)

        await interaction.followup.send("Key has been pressed.")

    @key_group.command(name="up", description="Depresses a key.")
    @app_commands.describe(key="The key you want to depress.")
    @handle_exception()
    async def key_up_command(self, interaction: discord.Interaction, key: str):
        self.logger.debug(f"Depressing {key} requested")
        if not self.bot._is_vnc_connected:
            self.logger.warn("VNC is not connected")
            await interaction.response.send_message("VM is not running.")
            return

        await interaction.response.defer()
        await self.key_press(key, key_down=False)

        await interaction.followup.send("Key has been depressed.")


async def setup(bot):
    await bot.add_cog(Keyboard(bot))
