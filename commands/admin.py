from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Admin")


@command_register(name="reboot")
@handle_exception(logger=logger)
async def reboot_command(bot, _):
    logger.debug("VM reboot requested")
    await bot.force_shutdown_domain()
    await bot.start_domain()
    await bot.send_message("VM has been rebooted.")
