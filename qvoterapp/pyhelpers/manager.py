from itertools import product
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.setapp import QVoterAppError


class SpecificationError(QVoterAppError):
    ...


def update_data(new_data: pd.DataFrame, data_path: Path = Path("data.xml")) -> None:
    if data_path.is_file():
        existing_data = pd.read_xml(data_path).set_index("index")
        data = pd.concat([existing_data, new_data])
    else:
        data = new_data

    data.reset_index(drop=True, inplace=True)
    data.to_xml(data_path)



class SpecParser:
    def __init__(self, spec: dict) -> None:
        self.spec = spec

    @staticmethod
    def _parse_value(
        val: Union[list, dict, int, float, str]
    ) -> Union[NDArray, int, float, str]:
        if isinstance(val, (int, float, str)):
            parsed_val = np.array([val])
        elif isinstance(val, list):
            parsed_val = np.unique(np.array(val))
            if parsed_val.size == 0:
                raise SpecificationError(
                    f"Value {val} presents an empty list of parameters"
                )
        elif isinstance(val, dict):
            try:
                start = val["start"]
                step = val["step"]
                stop = val["stop"]
            except KeyError as err:
                raise SpecificationError(
                    f"Value {val} is suposed to be in (start, step, stop) range dict format"
                )
            parsed_val = np.arange(start=start, step=step, stop=stop)
            if parsed_val.size == 0:
                raise SpecificationError(
                    f"Value {val} presents an empty list of parameters"
                )

        else:
            raise SpecificationError(
                f"Value {val} in config has an invalid type {type(val)}"
            )
        return parsed_val

    def _assess_part_data_req(self, part_spec: dict) -> pd.DataFrame:
        # general
        net = part_spec["net"]
        model = part_spec["model"]
        mc_runs = [part_spec.get("M")]  # can be blank
        # net
        net_type = self._parse_value(net.pop("name"))
        size = self._parse_value(net.pop("N"))
        net_params = {
            param_key: self._parse_value(param_val)
            for param_key, param_val in net.items()
        }
        # model
        x = self._parse_value(model["x"])
        q = self._parse_value(model["q"])
        eps = self._parse_value(model["eps"])

        parsed_values = {
            "mc_runs": mc_runs,
            "net_type": net_type,
            "size": size,
            **net_params,
            "x": x,
            "q": q,
            "eps": eps,
        }
        df = pd.DataFrame(
            list(product(*parsed_values.values())),
            columns=list(parsed_values.keys()),
        )
        print(df)

    # ! TODO type validation

    def asses_data_req(self) -> pd.DataFrame:
        for plot_name, part_spec in self.spec.items():
            try:
                self._assess_part_data_req(part_spec)
            except KeyError as err:
                raise SpecificationError(
                    f"Mandatory key {err} is missing in {plot_name} config"
                )


# ! always reset_index when joining!
# ! todo - always assing exit time and probability columns when creating
