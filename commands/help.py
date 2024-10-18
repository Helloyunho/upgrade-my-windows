from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Help")
HELP_PAGES = [
    "- !!change os <os>\n"
    "Changes the vm preset(memory size, cpu core count, etc.) and disc(or floppy disk) image selection to selected OS.\n",
    "- !!change image <type> <image>\n"
    "Changes the disc(or floppy disk) image to selected image.\n"
    "- !!eject <type>\n"
    "Ejects the disc(or floppy disk, or both).\n",
    "- !!type <text>\n"
    "Types the text like you would type on your keyboard.\n"
    "- !!key down <key>\n"
    "Presses and holds the key.\n"
    "- !!key up <key>\n"
    "Releases the key.\n"
    "- !!info\n"
    "Shows the current VM information.\n",
    "- !!move <x> <y> [relative]\n"
    "Moves the mouse to the specified coordinates. If `relative` is provided, the coordinates are relative to the current mouse position.\n",
    "- !!move center\n"
    "Moves the mouse to the center of the screen.\n"
    "- !!reset_cursor\n"
    "Resets the mouse cursor to the top-left of the screen.\n",
    "- !!click [button]\n"
    "Clicks the mouse. The button can be `left`, `right`, or `middle`. Default is `left`.\n",
    "- !!scroll <direction> [amount]\n"
    "Scrolls the mouse wheel. The direction can be `up`, `down`, `left` or `right`. The amount is optional and defaults to 1.\n",
    "- !!mouse down <button>\n"
    "Presses and holds the mouse button. The button can be `left`, `right`, or `middle`.\n",
    "- !!mouse up <button>\n"
    "Releases the mouse button. The button can be `left`, `right`, or `middle`.\n",
]


@command_register(name="help")
@handle_exception(logger=logger)
async def help_command(bot, args):
    logger.debug("Help command requested")
    page = 1
    if len(args) > 0:
        try:
            page = int(args[0])
        except ValueError:
            await bot.send_message("Invalid page number.")
            return
    if page < 1 or page > len(HELP_PAGES):
        await bot.send_message("Invalid page number.")
        return
    await bot.send_message(HELP_PAGES[page - 1] + f"\n\n{page}/{len(HELP_PAGES)}")
