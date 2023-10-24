import json
import logging
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

    @staticmethod
    def _param_cart(param_dict: Dict[str, Any]) -> pd.DataFrame:
        # get rid of the param key prefixes
        golden_param_dict = {
            param_key.split(".")[-1]: param_val
            for param_key, param_val in param_dict.items()
        }
        # find all the possibilites
        product_df = pd.DataFrame(
            list(product(*golden_param_dict.values())),
            columns=list(golden_param_dict.keys()),
        )
        return product_df

    def _parse_part(self, part_spec: Dict[str, Any]) -> pd.DataFrame:
        # find plot argument and group related keys
        plot_args = part_spec.pop("plot.args")
        try:
            plot_group = part_spec.pop("plot.group")
        except KeyError:
            plot_group = None
        if plot_args == plot_group:
            raise SpecificationError(
                "Groupping variable cannot be the one used for arguments"
            )
        # both cases - group section exists and not
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
            if (not isinstance(groups, list)) or (not groups):
                raise SpecificationError(
                    "existing 'groups' section must contain a non-empty list"
                )
            # iterate over groups and add their parameters to lists
            all_plot_rel_params = []
            for group in groups:
                group: dict
                single_plot_rel_params = {
                    plot_args: self._process_value(group.pop(plot_args), multiple=True),
                    plot_group: self._process_value(
                        group.pop(plot_group), multiple=True
                    ),
                }
                if group:
                    logging.warning(
                        "Parser is skipping parameters remaining in some 'group' sections: {group}"
                    )
                all_plot_rel_params.append(single_plot_rel_params)
            covered_mandatory_param_keys = {plot_args, plot_group}
        else:
            # initially prepare only plot arguments
            single_plot_rel_params = {
                plot_args: self._process_value(part_spec.pop(plot_args), multiple=True)
            }
            covered_mandatory_param_keys = {plot_args}
            # if grouping variable exists, update the data with it
            if plot_group is not None:
                single_plot_rel_params.update(
                    {
                        plot_group: self._process_value(
                            part_spec.pop(plot_group), multiple=True
                        )
                    }
                )
                covered_mandatory_param_keys.add(plot_group)
            if any([params.size < 2 for params in single_plot_rel_params.values()]):
                logging.warning(
                    "Detected plot arguments or groups series of size 1. Continuing..."
                )
            all_plot_rel_params = [single_plot_rel_params]
        # process the rest of parameters
        mandatory_param_keys = {
            "net.net_type",
            "net.size",
            "method.mc_runs",
            "model.x",
            "model.q",
            "model.eps",
        }
        left_mandatory_param_keys = mandatory_param_keys - covered_mandatory_param_keys
        left_mandatory_params = {
            param_key: self._process_value(part_spec.pop(param_key))
            for param_key in left_mandatory_param_keys
        }
        # from the rest of parameters, get the optional net parameters
        net_params = {
            param_key.replace("net.", ""): self._process_value(param_val)
            for param_key, param_val in part_spec.items()
            if "net." in param_key
        }
        non_plot_rel_params = {**left_mandatory_params, **net_params}
        # get the products and glue the chunks together
        part_req_chunks = [
            self._param_cart({**non_plot_rel_params, **plot_rel_params_chunk})
            for plot_rel_params_chunk in all_plot_rel_params
        ]
        part_req = pd.concat(part_req_chunks, ignore_index=True)
        return part_req
        # TODO: check if there are the same rows between `all_plot_rel_params` if so, warn

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
            except SpecificationError as err:
                raise SpecificationError(
                    f"The following issue encountered while parsing {plot_name} specification: {err}"
                )
        full_req = pd.concat(part_req_list, ignore_index=True)
        full_req.drop_duplicates(inplace=True)
        return full_req


class DataManager:
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.PRECISION = 3

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
                pd.merge(
                    full_data_req.round(self.PRECISION),
                    existing_data.round(self.PRECISION),
                    how="outer",
                    indicator=True,
                )
                .query('_merge=="left_only"')
                .drop("_merge", axis=1)
                .drop_duplicates()
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
            data = pd.concat(
                [
                    existing_data.round(self.PRECISION),
                    new_data_chunk.round(self.PRECISION),
                ],
                ignore_index=True,
            )
        else:
            data = new_data_chunk

        data.reset_index(drop=True, inplace=True)
        data.to_xml(self.data_path)
