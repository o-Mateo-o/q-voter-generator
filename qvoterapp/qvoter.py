#!/usr/bin/env python
import logging
import warnings
from argparse import ArgumentParser

from colorama import Back, Fore
from pyhelpers import (
    PlotCreator,
    QVoterAppError,
    SimulCollector,
    open_out_dir,
    open_spec_file,
    set_logger,
)

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
parser.add_argument(
    "--silent",
    action="store_true",
    help="do not ask for any interactions",
)


def main(
    only_simulations: bool,
    plot_spec: str,
    data_storage: str,
    chunk_size: int,
    silent: bool,
) -> None:
    hello_msg = "Welcome to the q-voter exit time & exit probability simulation app!"
    print(f"{Fore.CYAN}\n{hello_msg}\n{'-' * len(hello_msg)}{Fore.RESET}")
    if not silent:
        open_spec_file(plot_spec)  # it still asks if you want to open
        _enter_str = f"{Back.CYAN}{Fore.BLACK}ENTER{Fore.CYAN}{Back.RESET}"
        input(
            f"{Fore.CYAN}\nAre you ready for some magic? Press {_enter_str} if so!{Fore.RESET}"
        )
    # logger and the parameters
    warnings.filterwarnings("ignore")
    # execution
    ## simulation
    print(f"{Fore.CYAN}\n*** SIMULATING ***{Fore.RESET}")
    SimulCollector(
        str_spec_path=plot_spec,
        str_data_path=data_storage,
        chunk_size=chunk_size,
    ).run()
    ## plotting
    if not only_simulations:
        print(f"{Fore.CYAN}\n*** PLOTTING ***{Fore.RESET}")
        plot_creator = PlotCreator(
            str_spec_path=plot_spec, str_data_path=data_storage
        )
        plot_creator.run()
    if not silent and not only_simulations:
        open_out_dir(plot_creator.out_dir)


if __name__ == "__main__":
    set_logger()
    args = parser.parse_args()
    try:
        main(**dict(args._get_kwargs()))
    except QVoterAppError as err:
        logging.error(f"{err.__class__.__name__}: {err}")
    except Exception as err:
        logging.error(err, exc_info=True)
    else:
        print(f"{Fore.LIGHTGREEN_EX}\nExecution successful!{Fore.RESET}")
