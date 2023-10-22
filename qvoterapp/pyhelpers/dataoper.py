import json
from itertools import product
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.setapp import QVoterAppError


class SpecificationError(QVoterAppError):
    ...


class FileManagementError(QVoterAppError):
    ...


class SpecManager:
    def __init__(self, spec_path: Path) -> None:
        self.spec = self.read_file(spec_path)

    @staticmethod
    def read_file(spec_path: Path) -> dict:
        if not spec_path.is_file():
            raise FileManagementError(f"Config file '{spec_path}' doesn't exist")
        with open(spec_path, "r") as f:
            try:
                plot_scpec = json.load(f)
            except json.JSONDecodeError:
                raise FileManagementError("Cannot decode JSON spec file")
        return plot_scpec

    @staticmethod
    def _process_value(
        val: Union[list, dict, int, float, str], multiple: bool = False
    ) -> Union[NDArray, int, float, str]:
        if isinstance(val, (int, float, str)):
            parsed_val = np.array([val])
        elif multiple and isinstance(val, list):
            parsed_val = np.unique(np.array(val))
            if parsed_val.size == 0:
                raise SpecificationError(
                    f"Value {val} presents an empty list of parameters"
                )
        elif multiple and isinstance(val, dict):
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
        elif isinstance(val, (list, dict)):
            raise SpecificationError(f"Value {val} in config cannot be non-singular")
        else:
            raise SpecificationError(
                f"Value {val} in config has an invalid type {type(val)}"
            )
        return parsed_val

    def _parse_part(self, part_spec: Dict[str, Any]) -> pd.DataFrame:
        # find plot argument and group related keys
        plot_args = part_spec.pop("plot.args")
        try:
            plot_group = part_spec.pop("plot.group")
        except KeyError:
            plot_group = None
        if "groups" in part_spec:
            if plot_group is None:
                raise SpecificationError(
                    "'groups' section can be used only if `plot.group` parameter added"
                )
            if plot_args in part_spec or plot_group in part_spec:
                raise SpecificationError(
                    "Arguments and groups can't be given both in the 'groups' section and outside of it"
                )
            groups = part_spec.pop("groups")
            for group in groups:
                group: dict
                self._process_value(group.pop(plot_args), multiple=True)
                self._process_value(group.pop(plot_group), multiple=True)
                # ! if dict, raise warning że coś tam jest a nie powinno

            # ! zrobić słownik wszystkich do wyplucia, z odpowiednim parsowaniem
            # ! odjąć od słownika te elementy z groupa i arga
            # ! a następnie collectować
            # ! na koniec, pozostałe ".net"
        else:
            # ! wziąć na multiplu argumenty (warning jeśli jeden) (z popem)
            # ! jeśli plot_group, to wziąc na multiplu grupy (z popem)
            # !     i ostrzec warningiem jak pojedyncze ; przeciwnie pominąć
            # ! zrobić to samo z plującym słownikiem co wyżej, ale pamietać od
            # ! zależności od groupa
            pass

    def _parse_part_OLD(self, part_spec: Dict[str, Any]) -> pd.DataFrame:
        # general
        mc_runs = [part_spec.get("method.mc_runs")]  # can be blank
        # net
        net_type = self._process_value(part_spec.pop("net.name"))
        size = self._process_value(part_spec.pop("net.size"))
        net_params = {
            param_key.replace("net.", ""): self._process_value(param_val)
            for param_key, param_val in part_spec.items()
            if "net." in param_key
        }
        # model
        x = self._process_value(part_spec["x"])
        q = self._process_value(part_spec["q"])
        eps = self._process_value(part_spec["eps"])
        # "net.N": 200,
        parsed_values = {
            "mc_runs": mc_runs,
            "net_type": net_type,
            "size": size,
            **net_params,
            "x": x,
            "q": q,
            "eps": eps,
        }
        part_req = pd.DataFrame(
            list(product(*parsed_values.values())),
            columns=list(parsed_values.keys()),
        )
        return part_req

    def parse(self) -> pd.DataFrame:
        part_req_list = []
        for plot_name, part_spec in self.spec.items():
            try:
                part_req = self._parse_part(part_spec)
                part_req_list.append(part_req)
            except KeyError as err:
                raise SpecificationError(
                    f"Mandatory key {err} is missing somewhere in {plot_name} config"
                )
        full_req = pd.concat(part_req_list, ignore_index=True)
        full_req.drop_duplicates(inplace=True)
        return full_req


class DataManager:
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path

    def get_working_data(self, full_data_req: pd.DataFrame) -> pd.DataFrame:
        # get the existing data
        if self.data_path.is_file():
            existing_data = pd.read_xml(self.data_path).set_index("index")
        else:
            existing_data = pd.DataFrame()
        # process the data to skip the existing values
        # add also the columns for results
        existing_data = existing_data.assign(
            **{
                col: np.nan
                for col in full_data_req.columns.difference(existing_data.columns)
            }
        )[full_data_req.columns]
        try:
            full_data_req_prcsd = (
                pd.merge(full_data_req, existing_data, how="outer", indicator=True)
                .query('_merge=="left_only"')
                .drop("_merge", axis=1)
                .reset_index(drop=True)
                .assign(avg_exit_time=np.nan, exit_proba=np.nan)  # add result cols
            )
        except ValueError:
            raise FileManagementError(
                "Existing data dameged. Cannot compare it the plot specification requirements"
            )
        return full_data_req_prcsd

    def update_file(self, new_data_chunk: pd.DataFrame) -> None:
        if self.data_path.is_file():
            existing_data = pd.read_xml(self.data_path).set_index("index")
            data = pd.concat([existing_data, new_data_chunk], ignore_index=True)
        else:
            data = new_data_chunk

        data.reset_index(drop=True, inplace=True)
        data.to_xml(self.data_path)
