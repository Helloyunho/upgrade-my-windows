import asyncio
import codecs
import regex as re
from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger
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

logger = get_logger("Keyboard")


@handle_exception(logger=logger)
async def char_split_press(bot, text: str, key_down: bool = True, key_up: bool = True):
    if not bot._is_vnc_connected:
        return

    for char in text:
        char = chr(BACKSLASH_KEYMAP[char]) if char in BACKSLASH_KEYMAP else char
        if key_down:
            bot.vnc.keyDown(char)
            await asyncio.sleep(TYPE_DELAY)
        if key_up:
            bot.vnc.keyUp(char)
            await asyncio.sleep(TYPE_DELAY)


@handle_exception(logger=logger)
async def key_press(bot, text: str, key_down: bool = True, key_up: bool = True):
    logger.debug(f"Typing {text}")
    if not bot._is_vnc_connected:
        logger.warning("VNC is not connected")
        return

    # match backticks
    matches = BACKTICK_RE.findall(text)
    # split backticks and escape backslashes
    texts = [
        codecs.escape_decode(text.encode("utf-8"))[0].decode("utf-8")  # type: ignore - escape_decode returns Tuple[bytes, int]
        for text in BACKTICK_RE.split(text)[::2]
    ]

    for match, text in zip(matches, texts):
        await char_split_press(bot, text, key_down, key_up)

        match_sequences = HYPEN_RE.split(match)
        length = len(match_sequences)
        for i, sequence in enumerate(match_sequences * 2):
            converted = KEYMAP.get(sequence)
            if converted:
                if key_down and (i - length) < 0:
                    bot.vnc.keyDown(chr(converted))
                    await asyncio.sleep(TYPE_DELAY)
                elif key_up and (i - length) >= 0:
                    bot.vnc.keyUp(chr(converted))
                    await asyncio.sleep(TYPE_DELAY)
            else:
                if key_down and (i - length) < 0:
                    await char_split_press(bot, sequence, key_down, False)
                elif key_up and (i - length) >= 0:
                    await char_split_press(bot, sequence, False, key_up)

    if len(texts) > len(matches):
        await char_split_press(bot, texts[-1], key_down, key_up)


@command_register(name="type")
@handle_exception(logger=logger)
async def type_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No text provided.")
        return
    text = " ".join(args)
    logger.debug(f"Typing {text} requested")
    await key_press(bot, text)


@command_register(name="key")
@handle_exception(logger=logger)
async def key_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No subcommand provided. Use `!!help` for help.")
        return
    command = args[0]
    shifted_args = args[1:]
    if command == "down":
        await key_down_command(bot, shifted_args)
    elif command == "up":
        await key_up_command(bot, shifted_args)
    else:
        await bot.send_message("Invalid subcommand. Use `!!help` for help.")


@handle_exception(logger=logger)
async def key_down_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No key provided.")
        return
    key = " ".join(args)
    logger.debug(f"Pressing {key} requested")
    await key_press(bot, key, key_up=False)


@handle_exception(logger=logger)
async def key_up_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No key provided.")
        return
    key = " ".join(args)
    logger.debug(f"Unpressing {key} requested")
    await key_press(bot, key, key_down=False)
