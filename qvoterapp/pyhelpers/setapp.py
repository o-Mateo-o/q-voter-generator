import logging
from logging.handlers import QueueHandler
from pathlib import Path
from typing import Any
import os

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


def open_spec_file(str_spec_path: str) -> None:
    if not Path(str_spec_path).is_file():
        try:
            with open(str_spec_path, "w"):
                pass
        except OSError:
            raise QVoterAppError(f"Spec file {str_spec_path} cannot be created")
    open_flag = input("\nDo you want to open the plot specification file? (y/n)\n> ")
    if not open_flag:
        print("[n]")
    if open_flag == "y":
        print("Opening the file. Close it when it is ready.")
        os.system(f"notepad.exe {str_spec_path}")
    else:
        print("As you wish sir/madam. I will NOT open it for you!")

def open_out_dir(out_dir: Path) -> None:
    open_flag = input("\nDo you want to open the output folder? (y/n)\n> ")
    if not open_flag:
        print("[n]")
    if open_flag == "y":
        if out_dir.is_dir():
            os.system(f"explorer.exe {out_dir}")
        else:
            raise QVoterAppError("Cannot open output folder. Try to do it manually.")
        