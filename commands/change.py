from config import os_list
from utils.handle_exception import handle_exception
from utils.command_register import command_register
from utils.logger import get_logger

logger = get_logger("Change")


@command_register(name="change")
@handle_exception(logger=logger)
async def change_command(bot, args):
    logger.debug("Change command requested")
    if len(args) < 1:
        await bot.send_message("No subcommand provided. Use `!!help` for help.")
    command = args[0]
    shifted_args = args[1:]
    if command == "os":
        await change_os_command(bot, shifted_args)
    elif command == "image":
        await change_image_command(bot, shifted_args)
    else:
        await bot.send_message("Invalid subcommand. Use `!!help` for help.")


@handle_exception(logger=logger)
async def change_os_command(bot, args):
    if args[0] == "list":
        logger.debug("OS list requested")
        await bot.send_message(
            "Available OS: " + ", ".join([os["os"] for os in os_list])
        )
        return

    os = args[0]
    logger.debug(f"Changing OS to {os} requested")
    if not bot._is_vm_running:
        logger.warning("VM is not running")
        await bot.send_message("VM is not running.")
        return

    os_preset = next((preset for preset in os_list if preset["os"] == os), None)
    if not os_preset:
        logger.warning(f"OS {os} not found")
        await bot.send_message("OS not found.")
        return

    await bot.set_vcpus(os_preset["vcpus"])
    await bot.set_memory(os_preset["memory"])
    await bot.set_os(os)
    if os_preset["cdrom"]:
        await bot.set_device(os_preset["cdrom"][0])
    else:
        await bot.set_device()
    if os_preset["floppy"]:
        await bot.set_device(os_preset["floppy"][0], "floppy")
    else:
        await bot.set_device(type="floppy")

    await bot.send_message(
        "VM has been updated. Restart(or shut down) the VM to apply the cpu and memory changes."
    )


@handle_exception(logger=logger)
async def change_image_command(bot, args):
    if args[0] == "list":
        logger.debug("Image type list requested")
        await bot.send_message("Available image types: cdrom, floppy")
        return

    type = args[0]
    if type not in ["cdrom", "floppy"]:
        await bot.send_message(
            "Invalid device type. Use `!!change image list` to see available types."
        )
        return

    if args[1] == "list":
        logger.debug(f"{type} image list requested")
        info = await bot.get_current_info()
        if not bot._is_vm_running or not info:
            logger.warning("VM is not running")
            await bot.send_message("VM is not running.")
            return

        os_preset = next(
            (preset for preset in os_list if preset["os"] == info["os"]), None
        )
        if not os_preset:
            logger.error(f"OS {info['os']} not found which is impossible")
            await bot.send_message(
                "OS not found. Which is impossible. Please contact the developer."
            )
            return

        if not os_preset[type]:
            logger.warning(f"{type} image not found for {info['os']}")
            await bot.send_message(f"{type} image for this OS not found.")
            return

        await bot.send_message(f"Available {type} images: {', '.join(os_preset[type])}")
        return
    image = args[1]

    logger.debug(f"Changing {type} image to {image} requested")
    info = await bot.get_current_info()
    if not bot._is_vm_running or not info:
        logger.warning("VM is not running")
        await bot.send_message("VM is not running.")
        return

    os_preset = next((preset for preset in os_list if preset["os"] == info["os"]), None)
    if not os_preset:
        logger.error(f"OS {info['os']} not found which is impossible")
        await bot.send_message(
            "OS not found. Which is impossible. Please contact the developer."
        )
        return

    try:
        index = os_preset[type].index(image)  # type: ignore
        await bot.set_device(os_preset[type][index], type)  # type: ignore
    except ValueError:
        if type == "cdrom" and image == "half-life.iso":
            await bot.set_device(image, type)
        else:
            logger.warning(f"Image {image} not found")
            await bot.send_message(
                f"Image not found. Use `!!change image {type} list` to see available images."
            )
            return

    await bot.send_message("Image has been updated.")
