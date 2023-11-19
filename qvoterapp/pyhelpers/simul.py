"""Simulation features"""

import logging
import multiprocessing
import os
from logging.handlers import QueueListener
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.dataoper import DataManager, SpecManager
from pyhelpers.setapp import SimulationError, ensure_julia_env, init_julia_proc


class SimulParams:
    r"""Parameters for one simulation. This class comes along with a set of methods
    to parse the parameters and represent them

    .. note::
        You must stick to the `./models.md` guidelines when passing the parameters

    :param mc_runs: Monte Carlo runs number
    :type mc_runs: int
    :param x: Initial positive opinions rate in the system
    :type x: float
    :param q: Neighbor number parameter
    :type q: int
    :param eps: A noise level
    :type eps: float
    :param size: Size of a network
    :type size: int
    :param net_type: A network type alias
    :type net_type: str
    :param \**net_params: Network parameters other than its size
    """

    def __init__(
        self,
        mc_runs: int,
        x: float,
        q: int,
        eps: float,
        size: int,
        net_type: str,
        **net_params,
    ) -> None:
        """Initialize a class. Parse all the input parameters"""
        self.mc_runs: int = self.parse_param(mc_runs, "number")
        self.x: int = self.parse_param(x, "float_prop")
        self.q: int = self.parse_param(q, "number")
        self.eps: float = self.parse_param(eps, "float_prop")
        self.size: int = self.parse_param(size, "number")
        self.net_type: str = self.parse_param(net_type, "net_key")
        self.net_params: dict = self.parse_net_params(net_params, self.net_type)

    @staticmethod
    def parse_param(param: Any, expected_type: str) -> Any:
        """Parse one parameter value and validate it

        :param param: A raw value of the parameter
        :type param: Any
        :param expected_type: A kind of the given parameter.  Can be 'number' (a positive integer),
            'float_prop' (a proportion from [0, 1] range) or a 'net_key' (a network type alias)
        :type expected_type: str
        :raises SimulationError: If the parameter format is incorrect
        :return: A safe parameter
        :rtype: Any
        """
        if expected_type == "number":
            try:
                param = int(param)
            except ValueError:
                raise SimulationError(f"Parameter {param} must be numeric")
            if param < 1:
                raise SimulationError(f"Parameter {param} must be positive")
        elif expected_type == "float_prop":
            try:
                param = float(param)
            except ValueError:
                raise SimulationError(f"Parameter {param} must be numeric")
            if param < 0 or param > 1:
                raise SimulationError(f"Parameter {param} must be in [0, 1] range")
        elif expected_type == "net_key":
            try:
                param = str(param)
            except ValueError:
                raise SimulationError(f"Parameter {param} must be a string")
            if param not in ("BA", "WS", "C", "FB"):
                raise SimulationError(f"Net type {param} is not allowed")
        else:
            raise SimulationError(f"Unknown parameter type '{expected_type}'")
        return param

    def parse_net_params(self, net_params: dict, net_type: str) -> dict:
        """Extract the relevant network-related parameters from the dictionary and parse them
        based on the network type given in the second argument

        :param net_params: Network parameters other than its size
        :type net_params: dict
        :param net_type: A network type alias
        :type net_type: str
        :raises SimulationError: If a required parameter is missing
        :return: Parsed network-related parameters
        :rtype: dict
        """
        try:
            if net_type == "BA":
                return {"k": self.parse_param(net_params["k"], "number")}
            if net_type == "WS":
                return {
                    "k": self.parse_param(net_params["k"], "number"),
                    "beta": self.parse_param(net_params["beta"], "float_prop"),
                }
            if net_type in ("C", "FB"):
                return dict()
        except KeyError as err:
            raise SimulationError(
                f"The {err} parameter is required for {net_type} graphs"
            )

    @property
    def net_params_julia(self) -> str:
        """Get the network parameters other than its size as a julia source code
        to be inserted into the simulating function

        :return: Additional network parameters as a julia source code
        :rtype: str
        """
        if self.net_type == "BA":
            arg_list = [self.net_params["k"]]
        if self.net_type == "WS":
            arg_list = [self.net_params["k"], self.net_params["beta"]]
        if self.net_type in ("C", "FB"):
            arg_list = []
        return "," + ",".join(map(str, arg_list))

    def to_dict(self, formatted: bool = False) -> dict:
        """Get the dictionary of all the parameters. In the 'formatted' mode the additional
        net parameters are not the separate values but a formatted julia source code string

        :param formatted: Julia src flag to format the ``net_params`` as a string, defaults to False
        :type formatted: bool, optional
        :return: All the simulation parameters
        :rtype: dict
        """
        common_dict_part = {
            "x": self.x,
            "net_type": self.net_type,
            "mc_runs": self.mc_runs,
            "q": self.q,
            "eps": self.eps,
            "size": self.size,
        }
        if formatted:
            return {**common_dict_part, "net_params": self.net_params_julia}
        else:
            return {**common_dict_part, **self.net_params}

    def __str__(self) -> str:
        """Get a text description of an object and all the values it stores

        :return: String representation of the parameters
        :rtype: str
        """
        net_params_frmtd = ",".join(
            [
                f"{param_key}={param_val}"
                for param_key, param_val in self.net_params.items()
            ]
        )
        raw_string = f"""q-voter system for {self.net_type}({net_params_frmtd}) network
            of size N={self.size} with model params: x={self.x}, q={self.q}, eps={self.eps};
            (M={self.mc_runs} runs)"""
        return " ".join(raw_string.split())


class ResultsDict(dict):
    """A dictionary class with custom string representation for the outcomes

    .. note::
        Designed to use only for the average exit time and the exit probability values
    """

    def __str__(self) -> str:
        """Get a text representation of the results stored in the dict (exit time and probability)

        :raises KeyError: If an outcome value is missing in the dictionary
        :return: String representation of the outcomes
        :rtype: str
        """
        return f"T={self['avg_exit_time']}, E={self['exit_proba']}"


class SingleSimulation:
    """A worker that simulates one q-voter scenario using Julia and gathers
    resulting average exit time and exit probability


    :param simul_params: Parameters for one simulation
    :type simul_params: SimulParams
    """

    def __init__(
        self,
        simul_params: SimulParams,
    ) -> None:
        """Initialize an object"""
        self.simul_params = simul_params

    def run(self) -> dict:
        from julia import Main

        jl_statemet = 'examine_q_voter({x}, "{net_type}", {mc_runs}, {q}, {eps}, {size}{net_params})'.format(
            **self.simul_params.to_dict(formatted=True)
        )
        exit_time, exit_proba = Main.eval(jl_statemet)
        return ResultsDict({"avg_exit_time": exit_time, "exit_proba": exit_proba})


class SimulCollector:
    """A worker that collects all the simulation results and saves them to the database file.
    Required scenarios are automatically evaluated based on the input plot specification and
    the existing data

    :param str_spec_path: A path to the plot specification json file
    :type str_spec_path: str
    :param str_data_path: A path to the xml output data storage file
    :type str_data_path: str
    :param chunk_size: Average chunk size for the simulations, defaults to 5
    :type chunk_size: int, optional
    """

    def __init__(
        self,
        str_spec_path: str,
        str_data_path: str,
        chunk_size: int = 5,
    ) -> None:
        """Initialize an object (having prepared all the scenarios to be simulated)"""
        self.chunk_size: int = chunk_size
        self._data_manager = DataManager(Path(str_data_path))
        full_data_req = SpecManager(Path(str_spec_path)).parse_req()
        self.data: pd.DataFrame = self._data_manager.get_working_data(full_data_req)

    def _run_one(self, ix: int) -> None:
        """Run a single simulation scenario based on one parameter row
        in the data table and write the outcomes into that table
        Log the start & finish info

        :param ix: Index of the scenario row (from 0 to n-1)
        :type ix: int
        """
        raw_params_dict = self.data.iloc[ix].to_dict()
        simul_params = SimulParams(**raw_params_dict)
        logging.info(f"Starting simulation #{ix + 1}: {simul_params}.")
        results = SingleSimulation(simul_params).run()
        new_row = {**simul_params.to_dict(), **results}
        # add results & possibly rewrite the types (it's after SimulParams parsing)
        self.data.loc[ix, new_row.keys()] = new_row.values()
        logging.info(f"Simulation #{ix + 1} finished. Results: {results}.")

    def _run_chunk(self, chunk_indices: NDArray) -> None:
        """Run multiple simulations (a chunk) and update the database
        with the newly generated outcomes.
        Log the file update success info

        :param chunk_indices:  Indices of the scenario rows
            (an array containing numbers from 0 to n-1)
        :type chunk_indices: NDArray
        """
        [self._run_one(ix) for ix in chunk_indices]
        self._data_manager.update_file(self.data.iloc[chunk_indices])
        logging.info(
            f"--- Data chunk saved (#{chunk_indices.min()+1}-{chunk_indices.max()+1}/{len(self.data)})."
        )

    def _run(self) -> None:
        """Run all the simulations in separate processes on each the available cpu.
        In each process activate a julia env and map the simulation chunks

        :raises SimulationError: If *any* error occurred on a child process
        """
        data_indices = self.data.index.to_numpy()
        chunk_indices_list = np.array_split(
            data_indices, np.ceil(data_indices.size / self.chunk_size)
        )
        n_processes = os.cpu_count()
        multiprocessing.set_start_method("spawn")
        # logging setup
        mp_queue = multiprocessing.Queue()
        queue_listener = QueueListener(mp_queue, *logging.getLogger().handlers)
        queue_listener.start()
        # pool creation
        with Pool(
            processes=n_processes, initializer=init_julia_proc, initargs=[mp_queue]
        ) as pool:
            # log the pids
            pids = [str(process.pid) for process in multiprocessing.active_children()]
            logging.info(
                f"Julia is being activated on processes [{', '.join(pids)}]..."
            )
            # map the simulations
            logging.info(f"Launching {data_indices.size} simulations.")
            try:
                pool.map(self._run_chunk, chunk_indices_list)
            except Exception as err:
                raise SimulationError(err)
        queue_listener.stop()

    def run(self) -> None:
        """Make sure that all the Julia packages are installed and the environment (project) exist.
        Then, run all the simulation via a multiprocessing map and inform client about the progress
        """
        if self.data.empty:
            logging.info("No additional data required. Skipping simulations.")
        else:
            ensure_julia_env()
            self._run()
            logging.info("All the required simulations completed!")
