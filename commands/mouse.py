import asyncio
from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

MOUSE_BUTTONS = {"left": 1, "middle": 2, "right": 3}

WHEEL_BUTTONS = {
    "up": 4,
    "down": 5,
    "left": 6,
    "right": 7,
}

logger = get_logger("Mouse")


@command_register(name="move")
@handle_exception(logger=logger)
async def move_command(bot, args):
    if args[0] == "center":
        await move_center_command(bot, args)
        return

    if len(args) < 2:
        await bot.send_message("X and Y coordinates are required.")
        return
    x, y = args[:2]
    try:
        x = int(x)
        y = int(y)
    except ValueError:
        await bot.send_message("Invalid coordinates.")
        return
    relative = False
    if len(args) > 2:
        relative = args[2].lower() == "relative"
    logger.debug(f"Moving the mouse to {x}, {y} requested")
    if not bot._is_vnc_connected or not bot.vnc.screen:
        logger.warning("VNC is not connected or screen is not available")
        await bot.send_message("VM is not running.")
        return

    if relative:
        x += bot.vnc.x
        y += bot.vnc.y

    if x < -1 or y < -1 or x > bot.vnc.screen.size[0] or y > bot.vnc.screen.size[1]:
        logger.debug("Request cancelled due to coordinates out of bounds")
        await bot.send_message("Coordinates are out of bounds.")
        return

    bot.vnc.mouseMove(x, y)


@handle_exception(logger=logger)
async def move_center_command(bot, _):
    logger.debug("Moving mouse to center requested")
    if not bot._is_vnc_connected or not bot.vnc.screen:
        logger.warning("VNC is not connected or screen is not available")
        await bot.send_message("VM is not running.")
        return

    x = bot.vnc.screen.size[0] // 2
    y = bot.vnc.screen.size[1] // 2

    bot.vnc.mouseMove(x, y)


@command_register(name="reset_cursor")
@handle_exception(logger=logger)
async def reset_cursor_command(bot, _):
    logger.debug("Resetting the mouse cursor requested")
    if not bot._is_vnc_connected or not bot.vnc.screen:
        logger.warning("VNC is not connected or screen is not available")
        await bot.send_message("VM is not running.")
        return

    bot.vnc.mouseMove(bot.vnc.screen.size[0], bot.vnc.screen.size[1])
    await asyncio.sleep(0.01)
    bot.vnc.mouseMove(0, 0)


@command_register(name="click")
@handle_exception(logger=logger)
async def click_command(bot, args):
    button = "left"
    if len(args) > 0:
        button = args[0].lower()

    if button == "list":
        await bot.send_message("Available buttons: left, middle, right")
        return

    logger.debug(f"Clicking the {button} button requested")
    if not bot._is_vnc_connected:
        logger.warning("VNC is not connected")
        await bot.send_message("VM is not running.")
        return

    button_code = MOUSE_BUTTONS.get(button)
    if not button_code:
        logger.debug("Request cancelled due to requesting invalid button")
        await bot.send_message("Invalid button. Available buttons: left, middle, right")
        return

    bot.vnc.mouseDown(button_code)
    await asyncio.sleep(0.001)
    bot.vnc.mouseUp(button_code)


@command_register(name="scroll")
@handle_exception(logger=logger)
async def scroll_command(bot, args):
    if len(args) < 1:
        await bot.send_message(
            "Direction is required. Available directions: up, down, left, right"
        )
        return
    direction = args[0].lower()
    if direction == "list":
        await bot.send_message("Available directions: up, down, left, right")
        return

    amount = 1
    if len(args) > 1:
        amount = args[1]

    try:
        amount = max(1, int(amount))
    except ValueError:
        await bot.send_message("Invalid amount.")
        return
    logger.debug(f"Scrolling the mouse {direction} requested")
    if not bot._is_vnc_connected:
        logger.warning("VNC is not connected")
        await bot.send_message("VM is not running.")
        return

    direction_code = WHEEL_BUTTONS.get(direction)
    if not direction_code:
        logger.debug("Request cancelled due to requesting invalid direction")
        await bot.send_message(
            "Invalid direction. Available directions: up, down, left, right"
        )
        return

    for _ in range(amount):
        bot.vnc.mousePress(direction_code)


@command_register(name="mouse")
@handle_exception(logger=logger)
async def mouse_command(bot, args):
    if len(args) < 1:
        await bot.send_message("No subcommand provided. Use `!!help` for help.")
        return
    command = args[0]
    shifted_args = args[1:]
    if command == "down":
        await mouse_down_command(bot, shifted_args)
    elif command == "up":
        await mouse_up_command(bot, shifted_args)
    else:
        await bot.send_message("Invalid subcommand. Use `!!help` for help.")


@handle_exception(logger=logger)
async def mouse_down_command(bot, args):
    if len(args) < 1:
        await bot.send_message(
            "No button provided. Available buttons: left, middle, right"
        )
        return
    button = args[0].lower()
    if button == "list":
        await bot.send_message("Available buttons: left, middle, right")
        return

    logger.debug(f"Pressing the {button} button requested")
    if not bot._is_vnc_connected:
        logger.warning("VNC is not connected")
        await bot.send_message("VM is not running.")
        return

    button_code = MOUSE_BUTTONS.get(button)
    if not button_code:
        logger.debug("Request cancelled due to requesting invalid button")
        await bot.send_message("Invalid button. Available buttons: left, middle, right")
        return

    bot.vnc.mouseDown(button_code)


@handle_exception(logger=logger)
async def mouse_up_command(bot, args):
    if len(args) < 1:
        await bot.send_message(
            "No button provided. Available buttons: left, middle, right"
        )
        return
    button = args[0].lower()
    if button == "list":
        await bot.send_message("Available buttons: left, middle, right")
        return

    logger.debug(f"Unpressing the {button} button requested")
    if not bot._is_vnc_connected:
        logger.warning("VNC is not connected")
        await bot.send_message("VM is not running.")
        return

    button_code = MOUSE_BUTTONS.get(button)
    if not button_code:
        logger.debug("Request cancelled due to requesting invalid button")
        await bot.send_message("Invalid button. Available buttons: left, middle, right")
        return

    bot.vnc.mouseUp(button_code)
