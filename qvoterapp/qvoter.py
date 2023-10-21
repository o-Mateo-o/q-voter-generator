import logging
from argparse import ArgumentParser

from pyhelpers.setapp import QVoterAppError, read_spec_file, set_julia, set_logger

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
    print("Welcome to the q-voter exit time and exit probability simulation app :)")
    set_logger()
    JuliaMain = set_julia()

    # TODO: the following
    # if args.only_simulations:
    #     pass
    # else:
    #     pass

    try:
        plot_spec: dict = read_spec_file(args.plot_spec)
        from pyhelpers.manager import SpecParser
        SpecParser(plot_spec).asses_data_req()
    except QVoterAppError as err:
        logging.error(f"{err.__class__.__name__}: {err}")
