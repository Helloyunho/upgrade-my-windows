from discord import app_commands
from utils.cog_logger import CogLogger
from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Eject")


@command_register(name="eject")
@handle_exception(logger=logger)
async def eject_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No type provided. Available types: cdrom, floppy, both")
        return
    type = args[0]
    logger.debug(f"Ejecting {type} requested")
    if not bot._is_vm_running:
        logger.warning("VM is not running")
        await bot.send_message("VM is not running.")
        return

    if type == "both":
        await bot.set_device(None)
        await bot.set_device(None, "floppy")
        await bot.send_message("Both devices have been ejected.")
    else:
        await bot.set_device(None, type)
        await bot.send_message("Device has been ejected.")
