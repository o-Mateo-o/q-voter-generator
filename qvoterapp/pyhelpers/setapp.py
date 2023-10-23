import logging
from logging.handlers import QueueHandler
from pathlib import Path
from typing import Any

from colorlog import ColoredFormatter


class QVoterAppError(Exception):
    ...


def set_logger() -> None:
    logging.root.setLevel(logging.INFO)
    LOG_FILE = Path("log.log")
    # stream
    formatter = ColoredFormatter(
        "%(log_color)s%(message)s%(reset)s",
        log_colors={
            "DEBUG": "purple",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    # file
    formatter = logging.Formatter("%(levelname)s: %(asctime)s | %(message)s")
    file = logging.FileHandler(LOG_FILE)
    file.setFormatter(formatter)
    # add handlers
    log = logging.getLogger()
    log.addHandler(stream)
    logging.info(f"All the logs are available in '{LOG_FILE}' file.")
    log.addHandler(file)


def ensure_julia_env() -> Any:
    from julia import Main, Pkg

    logging.info("Ensuring Julia packages...")
    Pkg.activate(".")
    Main.include("qvoterapp/packages.jl")
    Main.eval("ensure_packages()")
    logging.info("Julia project ready!")


def init_julia_proc(q):
    from julia import Main, Pkg

    Pkg.activate(".")
    Main.include("qvoterapp/jlhelpers/NetSimul.jl")
    Main.eval("using .NetSimul")

    queue_handler = QueueHandler(q)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)
