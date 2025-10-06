from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Info")


@command_register(name="info")
@handle_exception(logger=logger)
async def info_command(bot, _):
    logger.debug("Info requested")
    info = await bot.get_current_info()
    if not info:
        logger.warning("Failed to get VM info")
        await bot.send_message("VM is not running.")
        return

    size = None
    if bot._is_vnc_connected and bot.vnc.screen:
        size = bot.vnc.screen.size
    else:
        logger.warning("Failed to get VM screen")
    await bot.send_message(
        f"Memory: {info['memory']} MB, "
        f"CPU: {info['cpu']} cores, "
        f"Resolution: {size[0]}x{size[1]}, "
        if size is not None
        else "Unavailable"
    )
    await bot.send_message(
        f"CD-ROM: {info['cdrom'] or 'None'}, "
        f"Floppy: {info['floppy'] or 'None'}, "
        f"OS: {info['os']}"
    )
