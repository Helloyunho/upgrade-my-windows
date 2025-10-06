from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Help")

ALLOWED_COMMANDS = [
    "type",
    "key",
    "info",
    "move",
    "reset_cursor",
    "click",
    "scroll",
    "mouse",
    "reboot (Super Chat with $5 and above only)",
]


@command_register(name="help")
@handle_exception(logger=logger)
async def help_command(bot, args):
    logger.debug("Help command requested")
    await bot.send_message(
        "Available commands: " + ", ".join([f"!!{cmd}" for cmd in ALLOWED_COMMANDS])
    )
    await bot.send_message("Use `!!<command> help` for more information on a command.")
