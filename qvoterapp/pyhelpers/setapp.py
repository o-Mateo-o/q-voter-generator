import logging
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
            "DEBUG": "cyan",
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
    logging.info(f"All the logs are available in `{LOG_FILE}` file")
    log.addHandler(file)


def set_julia() -> Any:
    from julia import Main as JuliaMain
    from julia import Pkg as JuliaPkg

    logging.info("Preparing Julia...")
    # project
    JuliaPkg.activate(".")
    # packages
    JuliaMain.include("qvoterapp/packages.jl")
    JuliaMain.eval("ensure_packages()")
    # simulation module
    JuliaMain.include("qvoterapp/jlhelpers/NetSimul.jl")
    JuliaMain.eval("using .NetSimul")
    logging.info("Julia NetSimul module ready!")

    return JuliaMain
