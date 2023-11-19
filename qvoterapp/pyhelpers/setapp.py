"""Functions that set up the environment or perform the app-system comunication actions"""

import logging
import os
from logging.handlers import QueueHandler
from multiprocessing import Queue as mpQueue
from pathlib import Path

from colorlog import ColoredFormatter


class QVoterAppError(Exception):
    """A general App error"""

    ...


class SpecificationError(QVoterAppError):
    """An error related to specification file processing"""

    ...


class FileManagementError(QVoterAppError):
    """An error related to file management jobs"""

    ...


class SimulationError(QVoterAppError):
    """An error in the simulation workflow"""

    ...


def set_logger() -> None:
    """Set up a logger to display colorful messages in the terminal
    and save them also into the file (with timestamps)
    """
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


def ensure_julia_env() -> None:
    """Create a julia project if there is no such
    and install all the missing julia packages"""
    from julia import Main, Pkg

    logging.info("Ensuring Julia packages...")
    Pkg.activate(".")
    Main.include("qvoterapp/packages.jl")
    Main.eval("ensure_packages()")
    logging.info("Julia project ready!")


def init_julia_proc(q: mpQueue) -> None:
    """Initialize the julia project, load the net simulation module
    and set up a logging queue handler.
    Use this function on children processes

    :param q: A multiprocessing queue to store the logs
    :type q: mpQueue
    """
    from julia import Main, Pkg

    Pkg.activate(".")
    Main.include("qvoterapp/jlhelpers/NetSimul.jl")
    Main.eval("using .NetSimul")

    queue_handler = QueueHandler(q)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)


def open_spec_file(str_spec_path: str) -> None:
    """Open the specification file in a Windows notepad

    :param str_spec_path: Path to the plot specification json file
    :type str_spec_path: str
    :raises QVoterAppError: If the specfication file cannot be create
    """
    if not Path(str_spec_path).is_file():
        try:
            with open(str_spec_path, "w"):
                pass
        except OSError:
            raise QVoterAppError(f"Spec file {str_spec_path} cannot be created")
    open_flag = input("\nDo you want to open the plot specification file? (y/n)\n> ")
    if not open_flag:
        print("[n]")
    if open_flag.upper() == "Y":
        print("Opening the file. Close it when it is ready.")
        os.system(f"notepad.exe {str_spec_path}")
    else:
        print("As you wish sir/madam. I will NOT open it for you!")


def open_out_dir(out_dir: Path) -> None:
    """Open the results directory in Windows file explorer

    :param out_dir: Path to the specific results sub-directory
    :type out_dir: Path
    :raises QVoterAppError: If the folder cannot be opened
    """
    open_flag = input("\nDo you want to open the output folder? (y/n)\n> ")
    if not open_flag:
        print("[n]")
    if open_flag.upper() == "Y":
        if out_dir.is_dir():
            os.system(f"explorer.exe {out_dir}")
        else:
            raise QVoterAppError("Cannot open output folder. Try to do it manually.")
