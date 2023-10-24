#!/usr/bin/env python
import logging
import warnings
from argparse import ArgumentParser

from colorama import Fore, Back
from pyhelpers import (
    PlotCreator,
    QVoterAppError,
    SimulCollector,
    open_spec_file,
    set_logger,
)

# constants stored by the argparser:
# * str_spec_path = "plot.spec.json"
# * str_data_path = "data.xml"
# * chunk_size = 5

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
parser.add_argument(
    "-d",
    "--data-storage",
    default="data.xml",
    help="path to the data storage file. It is recommended to use one for all the simulations",
)
parser.add_argument(
    "-c",
    "--chunk-size",
    default=5,
    type=int,
    help="approximated chunks size (number of simulations) for distrubuted computing",
)


def main(args) -> None:
    hello_msg = "Welcome to the q-voter exit time & exit probability simulation app!"
    print(f"{Fore.CYAN}\n{hello_msg}\n{'-' * len(hello_msg)}\n{Fore.RESET}")
    open_spec_file(args.plot_spec)  # it still asks if you want to open
    _enter_str = f"{Back.CYAN}{Fore.BLACK}ENTER{Fore.CYAN}{Back.RESET}"
    input(
        f"{Fore.CYAN}\nAre you ready for some magic? Press {_enter_str} if so ;){Fore.RESET}"
    )
    # logger and the parameters
    warnings.filterwarnings("ignore")
    set_logger()
    # execution
    ## simulation
    print(f"{Fore.CYAN}\n*** SIMULATING ***{Fore.RESET}")
    SimulCollector(
        str_spec_path=args.plot_spec,
        str_data_path=args.data_storage,
        chunk_size=args.chunk_size,
    ).run()
    ## plotting
    if not args.only_simulations:
        print(f"{Fore.CYAN}\n*** PLOTTING ***{Fore.RESET}")
        PlotCreator(str_spec_path=args.plot_spec, str_data_path=args.data_storage).run()


if __name__ == "__main__":
    args = parser.parse_args()
    try:
        main(args)
    except QVoterAppError as err:
        logging.error(f"{err.__class__.__name__}: {err}")
    else:
        print(f"{Fore.LIGHTGREEN_EX}\nExecution successful!{Fore.RESET}")
    input()