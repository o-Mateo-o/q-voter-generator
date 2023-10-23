#!/usr/bin/env python
import logging
import warnings
from argparse import ArgumentParser

from colorama import Fore
from pyhelpers import QVoterAppError, SimulCollector, set_logger

SPEC_PATH = "plot.spec.json"
DATA_PATH = "data.xml"
CHUNK_SIZE = 10

parser = ArgumentParser(
    prog="Q-voter exit time and exit probability simulation & plotting app",
    description="This is an app created by Mateusz Machaj (2023) to support the research related to the bachelor's thesis.",
)
parser.add_argument(
    "-s",
    "--only-simulations",
    action="store_true",
    help="use if you don't want to automatically create plots",
)
parser.add_argument(
    "-p",
    "--plot-spec",
    default="plot.spec.json",
    help="path to the plot specification file containing all input configutrations",
)

if __name__ == "__main__":
    args = parser.parse_args()
    # hello message
    hello_msg = "Welcome to the q-voter exit time & exit probability simulation app :)"
    print(f"{Fore.CYAN}\n{hello_msg}\n{'-' * len(hello_msg)}\n{Fore.RESET}")
    # logger and the parameters
    warnings.filterwarnings("ignore")
    set_logger()
    if args.plot_spec:
        spec_path = args.plot_spec
    else:
        spec_path = SPEC_PATH
    # execution
    try:
        print(f"{Fore.CYAN}\n*** SIMULATING ***{Fore.RESET}")
        SimulCollector(spec_path, DATA_PATH, CHUNK_SIZE).run()
        if not args.only_simulations:
            print(f"{Fore.CYAN}\n*** PLOTTING ***{Fore.RESET}")
            pass
    except QVoterAppError as err:
        logging.error(f"{err.__class__.__name__}: {err}")
    else:
        print(f"{Fore.LIGHTGREEN_EX}\nExecution successful!{Fore.RESET}")
