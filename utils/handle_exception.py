import functools
import traceback
import logging
import discord
import inspect


def handle_exception(logger: "logging.Logger | None" = None):
    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if logger:
                        logger.exception(e)
                    else:
                        self = args[0] if len(args) > 0 else None
                        interaction = args[1] if len(args) > 1 else None
                        if (
                            self is not None
                            and hasattr(self, "logger")
                            and type(self.logger) == logging.Logger
                        ):
                            self.logger.exception(e)
                            if (
                                interaction is not None
                                and type(interaction) == discord.Interaction
                            ):
                                if interaction.response.is_done():
                                    await interaction.followup.send(
                                        "An error occurred. Please report this to the developer."
                                    )
                                else:
                                    await interaction.response.send_message(
                                        "An error occurred. Please report this to the developer."
                                    )
                        else:
                            traceback.print_exc()
                    return None

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if logger:
                        logger.exception(e)
                    else:
                        self = args[0] if len(args) > 0 else None
                        if (
                            self is not None
                            and hasattr(self, "logger")
                            and type(self.logger) == logging.Logger
                        ):
                            self.logger.exception(e)
                        else:
                            traceback.print_exc()
                    return None

            return wrapper

    return decorator
