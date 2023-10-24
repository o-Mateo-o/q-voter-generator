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
from pyhelpers.setapp import QVoterAppError, ensure_julia_env, init_julia_proc


class SimulationError(QVoterAppError):
    ...


class SimulParams:
    # ! stick to the `./models.md` guidelines
    # ! net_params are the other than size args
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
        self.mc_runs: int = self.parse_param(mc_runs, "number")
        self.x: int = self.parse_param(x, "float_prop")
        self.q: int = self.parse_param(q, "number")
        self.eps: float = self.parse_param(eps, "float_prop")
        self.size: int = self.parse_param(size, "number")
        self.net_type: str = self.parse_param(net_type, "net_key")
        self.net_params: dict = self.parse_net_params(net_params, self.net_type)

    @staticmethod
    def parse_param(param: Any, expected_type: str) -> Any:
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
            if param not in ("BA", "WS", "C"):
                raise SimulationError(f"Net type {param} is not allowed")
        else:
            raise SimulationError(f"Unknown parameter type '{expected_type}'")
        return param

    def parse_net_params(self, net_params: dict, net_type: str) -> dict:
        try:
            if net_type == "BA":
                return {"k": self.parse_param(net_params["k"], "number")}
            if net_type == "WS":
                return {
                    "k": self.parse_param(net_params["k"], "number"),
                    "beta": self.parse_param(net_params["beta"], "float_prop"),
                }
            if net_type == "C":
                return dict()
        except KeyError as err:
            raise SimulationError(
                f"The {err} parameter is required for {net_type} graphs"
            )

    @property
    def net_params_julia(self) -> str:
        if self.net_type == "BA":
            arg_list = [self.net_params["k"]]
        if self.net_type == "WS":
            arg_list = [self.net_params["k"], self.net_params["beta"]]
        if self.net_type == "C":
            arg_list = []
        return "," + ",".join(map(str, arg_list))

    def to_dict(self, formatted: bool = False) -> dict:
        common_dict_part = {
            "x": self.x,
            "net_type": self.net_type,
            "M": self.mc_runs,
            "q": self.q,
            "eps": self.eps,
            "N": self.size,
        }
        if formatted:
            return {**common_dict_part, "net_params": self.net_params_julia}
        else:
            return {**common_dict_part, **self.net_params}

    def __str__(self) -> str:
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
    def __str__(self) -> str:
        return f"T={self['avg_exit_time']}, E={self['exit_proba']}"


class SingleSimulation:
    def __init__(
        self,
        simul_params: SimulParams,
    ) -> None:
        self.simul_params = simul_params

    def run(self) -> dict:
        from julia import Main

        jl_statemet = 'examine_q_voter({x}, "{net_type}", {M}, {q}, {eps}, {N}{net_params})'.format(
            **self.simul_params.to_dict(formatted=True)
        )
        exit_time, exit_proba = Main.eval(jl_statemet)
        return ResultsDict({"avg_exit_time": exit_time, "exit_proba": exit_proba})


class SimulCollector:
    def __init__(
        self,
        str_spec_path: str,
        str_data_path: str,
        chunk_size: int = 20,
    ) -> None:
        self.chunk_size: int = chunk_size
        self._data_manager = DataManager(Path(str_data_path))
        full_data_req = SpecManager(Path(str_spec_path)).parse_req()
        self.data: pd.DataFrame = self.data_manager.get_working_data(full_data_req)

    def _run_one(self, ix: int) -> None:
        raw_params_dict = self.data.iloc[ix].to_dict()
        simul_params = SimulParams(**raw_params_dict)
        logging.info(f"Starting simulation #{ix + 1}: {simul_params}.")
        results = SingleSimulation(simul_params).run()
        new_row = {**simul_params.to_dict(), **results}
        # add results & possibly rewrite the types (it's after SimulParams parsing)
        self.data.loc[ix, new_row.keys()] = new_row.values()
        logging.info(f"Simulation #{ix + 1} finished. Results: {results}.")

    def _run_chunk(self, chunk_ixx: NDArray) -> None:
        [self._run_one(ix) for ix in chunk_ixx]
        self._data_manager.update_file(self.data.iloc[chunk_ixx])
        logging.info(
            f"--- Data chunk saved (#{chunk_ixx.min()+1}-{chunk_ixx.max()+1}/{len(self.data)})."
        )

    def _run(self) -> None:
        data_indices = self.data.index.to_numpy()
        chunk_ixx_list = np.array_split(
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
            logging.info(f"Launching {data_indices.size + 1} simulations.")
            pool.map(self._run_chunk, chunk_ixx_list)
        queue_listener.stop()

    def run(self) -> None:
        if self.data.empty:
            logging.info("No additional data required. Skipping simulations.")
        else:
            ensure_julia_env()
            self._run()
            logging.info("All the required simulations completed!")
