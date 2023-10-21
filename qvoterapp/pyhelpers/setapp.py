import json
import logging
from pathlib import Path
from typing import Any

from colorlog import ColoredFormatter


class QVoterAppError(Exception):
    ...


class FileManagementError(QVoterAppError):
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
    logging.info(f"All the logs will are available in `{LOG_FILE}` file")
    log.addHandler(file)
    

def set_julia() -> Any:
    from julia import Main as JuliaMain
    from julia import Pkg as JuliaPkg

    logging.info("Preparing Julia...")
    JuliaPkg.activate(".")
    JuliaMain.include("qvoterapp/packages.jl")
    JuliaMain.include("qvoterapp/jlhelpers/NetSimul.jl")
    JuliaMain.eval("using .NetSimul")
    logging.info("Julia NetSimul module ready!")

    return JuliaMain


def read_spec_file(str_path: str) -> dict:
    path = Path(str_path)
    if not path.is_file():
        raise FileManagementError(f"Config file '{path}' doesn't exist")
    with open(path, "r") as f:
        plot_scpec = json.load(f)
    return plot_scpec
