import logging


time_formatter = logging.Formatter(
    "{asctime} - {name}:{levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(time_formatter)
logger = logging.getLogger("GN Session")
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
