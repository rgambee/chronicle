import logging


class ColorFormatter(logging.Formatter):
    """Apply ANSI colors to log records based on their level

    Based on https://stackoverflow.com/a/56944256

    This formatter is only recommended when logging to the console, not
    for writing to a file.
    """

    RED = "\x1b[31;20m"
    YELLOW = "\x1b[33;20m"
    GRAY = "\x1b[38;20m"
    RESET = "\x1b[0m"

    LEVEL_TO_COLOR = {
        logging.ERROR: RED,
        logging.WARNING: YELLOW,
        logging.INFO: "",
        logging.DEBUG: GRAY,
    }

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        prefix = self.LEVEL_TO_COLOR.get(record.levelno, "")
        suffix = self.RESET
        return formatted.join([prefix, suffix])
