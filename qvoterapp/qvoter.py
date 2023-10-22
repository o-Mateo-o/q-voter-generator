import logging
from argparse import ArgumentParser

from pyhelpers.setapp import QVoterAppError, set_julia, set_logger
from pyhelpers.simul import SimulCollector

SPEC_PATH = "plot.spec.json"
DATA_PATH = "data.xml"
PROCESSES = 10
CHUNK_SIZE = 10
from pyhelpers.setapp import QVoterAppError, set_julia, set_logger
from pyhelpers.simul import SimulCollector

SPEC_PATH = "plot.spec.json"
DATA_PATH = "data.xml"
PROCESSES = 10
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
    print("Welcome to the q-voter exit time and exit probability simulation app :)")
    set_logger()
    JuliaMain = set_julia()

    if args.plot_spec:
        spec_path = args.plot_spec
    else:
        spec_path = SPEC_PATH

    try:
        SimulCollector(JuliaMain, spec_path, DATA_PATH, PROCESSES, CHUNK_SIZE).run()
        if not args.only_simulations:
            pass
    except QVoterAppError as err:
        logging.error(f"{err.__class__.__name__}: {err}")
