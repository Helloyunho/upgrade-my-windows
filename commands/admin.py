import datetime
from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Admin")


@command_register(name="reboot", super_chat_only=True)
@handle_exception(logger=logger)
async def reboot_command(bot, _):
    logger.debug("VM reboot requested")
    await bot.force_shutdown_domain()
    await bot.start_domain()
    await bot.send_message("VM has been rebooted.")


@command_register(name="console", owner_only=True)
@handle_exception(logger=logger)
async def console_command(bot, _):
    logger.debug("Console command input requested")
    await bot.send_message("Entering console command mode. Chat input will be blocked.")
    bot.block_chat = True
    await bot.input_through_console()
    bot.started_at = datetime.datetime.now(datetime.timezone.utc)
    bot.block_chat = False
    await bot.send_message("Exiting console command mode. Chat input is unblocked.")
