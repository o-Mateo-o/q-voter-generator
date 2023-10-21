import logging
from multiprocessing.pool import ThreadPool
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.setapp import QVoterAppError


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


class Simulation:
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
                f"The {err} parameter is required for {self.net_type} graphs"
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
        return {"AvgExitTime": exit_time, "ExitProbability": exit_proba}


class BulkSimulator:
    def __init__(self, jl_interpreter: Any) -> None:
        # self.data = pd.DataFrame()
        self.data = pd.DataFrame(
            {
                "x": [0.5],
                "q": [2],
                "eps": [0.1],
                "size": [100],
                "net_type": ["BA"],
                "k": [4],
                "mc_runs": [1000],
            }
        )
        self.jl_interpreter = jl_interpreter

    def _run_one(self, ix: int) -> None:
        params_dict = self.data.iloc[ix].to_dict()
        mc_runs = params_dict.pop("mc_runs")
        results = Simulation(
            jl_interpreter=self.jl_interpreter,
            params=SystemParams(**params_dict),
            mc_runs=mc_runs,
        ).run()
        self.data.loc[0, results.keys()] = results.values()
        logging.info("done")

    def _run_chunk(self, chunk_ix: NDArray) -> None:
        indices = range(100)  # ! TODO
        [self._run_one(ix) for ix in indices]
        # ! save the results to the file (standard)

    def run(self):
        with ThreadPool(processes=10) as pool:
            pool.map(self._run_chunk, [np.arange(20)])
