from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Help")
HELP_PAGES = [
    "!!change os <os> "
    "- Changes the vm preset(memory size, cpu core count, etc.) and disc(or floppy disk) image selection to selected OS. ",
    "!!change image <type> <image> "
    "- Changes the disc(or floppy disk) image to selected image. ",
    "!!eject <type> "
    "- Ejects the disc(or floppy disk, or both). ",
    "!!type <text> "
    "- Types the text like you would type on your keyboard. ",
    "!!key down <key> "
    "- Presses and holds the key. ",
    "!!key up <key> "
    "- Releases the key. ",
    "!!info "
    "- Shows the current VM information. ",
    "!!move <x> <y> [relative] "
    "- Moves the mouse to the specified coordinates. If `relative` is provided, the coordinates are relative to the current mouse position. ",
    "!!move center "
    "- Moves the mouse to the center of the screen. ",
    "!!reset_cursor "
    "- Resets the mouse cursor to the top-left of the screen. ",
    "!!click [button] "
    "- Clicks the mouse. The button can be `left`, `right`, or `middle`. Default is `left`. ",
    "!!scroll <direction> [amount] "
    "- Scrolls the mouse wheel. The direction can be `up`, `down`, `left` or `right`. The amount is optional and defaults to 1. ",
    "!!mouse down <button> "
    "- Presses and holds the mouse button. The button can be `left`, `right`, or `middle`. ",
    "!!mouse up <button> "
    "- Releases the mouse button. The button can be `left`, `right`, or `middle`. ",
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
    await bot.send_message(HELP_PAGES[page - 1] + f"  {page}/{len(HELP_PAGES)}")
