import codecs
import discord
import regex as re
from vncdotool.client import KEYMAP
from discord.ext import commands
from discord import app_commands


BACKTICK_RE = re.compile(r"(?<=(?<!\\)(?:\\\\)*)`((?:[^`\\]|\\.)*)`")

BACKSLASH_KEYMAP = {
    "\n": 0xFF0D,
}

for value in KEYMAP.values():
    BACKSLASH_KEYMAP[chr(value & 0xFF)] = value


class Keyboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def char_split_press(
        self, text: str, key_down: bool = True, key_up: bool = True
    ):
        if not self.bot.vnc:
            return

        for char in text:
            char = chr(BACKSLASH_KEYMAP[char]) if char in BACKSLASH_KEYMAP else char
            if key_down:
                await self.bot.vnc.keyDown(char)
            if key_up:
                await self.bot.vnc.keyUp(char)

    async def key_press(self, text: str, key_down: bool = True, key_up: bool = True):
        if not self.bot.vnc:
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

            match_sequences = match.split(r"(?<=(?<!\\)(?:\\\\)*)-")
            length = len(match_sequences)
            for i, sequence in enumerate(match_sequences * 2):
                converted = KEYMAP.get(sequence)
                if converted:
                    if key_down and (i - length) < 0:
                        await self.bot.vnc.keyDown(chr(converted))
                    elif key_up and (i - length) >= 0:
                        await self.bot.vnc.keyUp(chr(converted))
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
    async def type_command(self, interaction: discord.Interaction, text: str):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        await self.key_press(text)

        await interaction.response.send_message("Text has been typed.")

    key_group = app_commands.Group(
        name="key", description="Presses(or depresses) a key."
    )

    @key_group.command(name="down", description="Presses a key.")
    @app_commands.describe(key="The key you want to press.")
    async def key_down_command(self, interaction: discord.Interaction, key: str):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        await self.key_press(key, key_up=False)

        await interaction.response.send_message("Key has been pressed.")

    @key_group.command(name="up", description="Depresses a key.")
    @app_commands.describe(key="The key you want to depress.")
    async def key_up_command(self, interaction: discord.Interaction, key: str):
        if not self.bot.vnc:
            await interaction.response.send_message("VM is not running.")
            return

        await self.key_press(key, key_down=False)

        await interaction.response.send_message("Key has been depressed.")


async def setup(bot):
    await bot.add_cog(Keyboard(bot))
