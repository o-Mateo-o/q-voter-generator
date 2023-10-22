import logging
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.dataoper import DataManager, SpecManager
from pyhelpers.setapp import QVoterAppError


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
            if param < 0:
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
                return {self.parse_param(net_params["k"], "number")}
            if net_type == "WS":
                return {
                    self.parse_param(net_params["k"], "number"),
                    self.parse_param(net_params["beta"], "float_prop"),
                }
            if net_type == "C":
                return {}
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


class SingleSimulation:
    def __init__(
        self,
        jl_interpreter: Any,
        simul_params: SimulParams,
    ) -> None:
        self.jl_interpreter = jl_interpreter
        self.simul_params = simul_params

    def run(self) -> dict:
        jl_statemet = 'examine_q_voter({x}, "{net_type}", {M}, {q}, {eps}, {N}{net_params})'.format(
            **self.simul_params.to_dict(formatted=True)
        )
        exit_time, exit_proba = self.jl_interpreter.eval(jl_statemet)
        return {"avg_exit_time": exit_time, "exit_proba": exit_proba}


class SimulCollector:
    def __init__(
        self,
        jl_interpreter: Any,
        str_spec_path: str,
        str_data_path: str,
        processes: int = 10,
        chunk_size: int = 20,
    ) -> None:
        self.jl_interpreter = jl_interpreter
        self.processes = processes
        self.chunk_size = chunk_size
        self.data_manager = DataManager(Path(str_data_path))
        full_data_req = SpecManager(Path(str_spec_path)).parse()
        self.data = self.data_manager.get_working_data(full_data_req)

    def _run_one(self, ix: int) -> None:
        raw_params_dict = self.data.iloc[ix].to_dict()
        simul_params = SimulParams(**raw_params_dict)
        results = SingleSimulation(
            jl_interpreter=self.jl_interpreter,
            simul_params=simul_params,
        ).run()
        new_row = {**simul_params.to_dict(), **results}
        # add results & possibly rewrite the types (it's after SimulParams parsing)
        self.data.loc[ix, new_row.keys()] = new_row.values()
        logging.info(f"Simulation: {simul_params} finished. Results {results}")

    def _run_chunk(self, chunk_ixx: NDArray) -> None:
        [self._run_one(ix) for ix in chunk_ixx]
        self.data_manager.update_file(self.data.iloc[chunk_ixx])
        logging.info(
            f"Data chunk saved (indices {chunk_ixx.min()}-{chunk_ixx.max()} / {len(self.data)})"
        )

    def run(self) -> None:
        logging.info("Running the simulations in a thread pool...")
        data_indices = self.data.index.to_numpy()
        chunk_ixx_list = np.array_split(
            data_indices, data_indices.size / self.chunk_size
        )
        with ThreadPool(processes=self.processes) as pool:
            pool.map(self._run_chunk, chunk_ixx_list)
        logging.info("All the required simulations completed")
