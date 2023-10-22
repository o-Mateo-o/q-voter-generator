import logging
from multiprocessing.pool import ThreadPool
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pathlib import Path
from pyhelpers.setapp import QVoterAppError
from pyhelpers.dataoper import DataManager, SpecManager


class SimulationError(QVoterAppError):
    ...


class SystemParams:
    def __init__(
        self,
        x: float,
        q: int,
        eps: float,
        size: int,
        net_type: str,
        **net_params,
    ) -> None:
        self.x: int = x
        self.q: int = q
        self.eps: float = eps
        self.size: int = size
        self.net_type: str = net_type
        self.net_params: dict = net_params

    def __str__(self) -> str:
        net_params_frmtd = ",".join(
            [
                f"{param_key}={param_val}"
                for param_key, param_val in self.net_params.items()
            ]
        )
        raw_string = f"""q-voter system for {self.net_type}({net_params_frmtd}) network
            of size N={self.size} with model params: x={self.x}, q={self.q}, eps={self.eps}"""
        return " ".join(raw_string.split())


class SingleSimulation:
    def __init__(
        self,
        jl_interpreter: Any,
        params: SystemParams,
        mc_runs: int = 1000,
    ) -> None:
        self.jl_interpreter = jl_interpreter
        self.params = params
        self.mc_runs: int = mc_runs if mc_runs is not None else 1000

    def _pass_net_key(self) -> str:
        return self.params.net_type

    def _format_net_params(self):
        # ! stick to the `./models.md` guidelines
        # ! net_params are the other than size args
        try:
            if self.params.net_type == "BA":
                arg_list = [self.params.net_params["k"]]
            if self.params.net_type == "WS":
                arg_list = [self.params.net_params["k"], self.params.net_params["beta"]]
            if self.params.net_type == "C":
                arg_list = []
        except KeyError as err:
            raise SimulationError(
                f"The {err} parameter is required for {self.params.net_type} graphs"
            )
        return "," + ",".join(map(str, arg_list))

    def run(self) -> dict:
        jl_statemet = 'examine_q_voter({x}, "{net_type}", {M}, {q}, {eps}, {N}{net_params})'.format(
            x=self.params.x,
            net_type=self._pass_net_key(),
            M=self.mc_runs,
            q=self.params.q,
            eps=self.params.eps,
            N=self.params.size,
            net_params=self._format_net_params(),
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
        params_dict = self.data.iloc[ix].to_dict()
        mc_runs = params_dict.pop("mc_runs")
        system_params = SystemParams(**params_dict)
        results = SingleSimulation(
            jl_interpreter=self.jl_interpreter,
            params=system_params,
            mc_runs=mc_runs,
        ).run()
        self.data.loc[ix, results.keys()] = results.values()
        logging.info(f"Simulation: {system_params} finished (M={mc_runs})")

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
