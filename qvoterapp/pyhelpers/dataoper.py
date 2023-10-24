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

    def _parse_req_part(self, part_spec: Dict[str, Any]) -> pd.DataFrame:
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

    def parse_req(
        self, plot_specific: bool = False
    ) -> Union[pd.DataFrame, Dict[pd.Dataframe]]:
        # ! it takes care of the data quality as well,
        # ! so validates plot arg/group vs other available params relations
        part_req_dict = dict()
        for plot_name, part_spec in self.spec.items():
            try:
                part_req = self._parse_req_part(part_spec)
                part_req_dict.update({plot_name: part_req})
            except KeyError as err:
                raise SpecificationError(
                    f"Some key {err} is required but cannot be found in {plot_name} config"
                )
            except SpecificationError as err:
                raise SpecificationError(
                    f"The following issue encountered while parsing {plot_name} specification: {err}"
                )
        if plot_specific:
            return part_req_dict
        else:
            part_req_list = part_req_dict.values()
            full_req = pd.concat(part_req_list, ignore_index=True)
            full_req.drop_duplicates(inplace=True)
            return full_req

    def _parse_visual_part(self, part_spec: Dict[str, Any]) -> dict:
        plot_args = part_spec.pop("plot.args")
        plot_group = part_spec.get("plot.group")
        plot_vals = part_spec.pop("plot.vals")
        if plot_vals not in ("exit_proba", "avg_exit_time"):
            raise SpecificationError(f"Values {plot_vals} is an unknown measure")
        # !TODO!: plot_vals_scaling = (None,)
        desc_info = part_spec.get("y_ax_scale", "")
        x_ax_scale = part_spec.get("x_ax_scale", "linear")
        y_ax_scale = part_spec.get("y_ax_scale", "linear")
        accepted_ax_scales = ("linear", "log")
        if x_ax_scale not in accepted_ax_scales or x_ax_scale not in accepted_ax_scales:
            raise SpecificationError(
                f"Axis scaling must be chosen from {accepted_ax_scales} list"
            )
        return {
            "arg": plot_args,
            "group": plot_group,
            "vals": plot_vals,
            "a_scaling": None,  #!
            "v_scaling": None,  #!
            "desc_info": desc_info,
            "x_ax_scale": x_ax_scale,
            "y_ax_scale": y_ax_scale,
        }

    @staticmethod
    def _validate_plot_name(plot_name: str) -> None:
        if not plot_name.isalnum():
            raise SpecificationError(
                f"Plot name {plot_name} is invalid. It should be alpha-numeric"
            )

    def parse_visual(self):
        part_visual_dict = dict()
        for plot_name, part_spec in self.spec.items():
            try:
                self._validate_plot_name(plot_name)
                part_visual = self._parse_visual_part(part_spec)
                part_visual_dict.update({plot_name: part_visual})
            except KeyError as err:
                raise SpecificationError(
                    f"Some key {err} is required but cannot be found in {plot_name} config"
                )
            except SpecificationError as err:
                raise SpecificationError(
                    f"The following issue encountered while parsing {plot_name} specification: {err}"
                )
        return part_visual_dict


class DataManager:
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.PRECISION = 3

    def _read_file(self) -> pd.DataFrame:
        return pd.read_xml(self.data_path).set_index("index")

    def get_working_data(self, full_data_req: pd.DataFrame) -> pd.DataFrame:
        # get the existing data
        if self.data_path.is_file():
            existing_data = self._read_file()
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

    @staticmethod
    def _req_add_results(
        req: pd.DataFrame, available_data: pd.DataFrame
    ) -> pd.DataFrame:
        cols = req.columns.append(pd.Index(["avg_exit_time", "exit_proba"]))
        merged_data = pd.merge(
            available_data, req, how="outer", indicator=True
        )
        if not merged_data.query('_merge=="right_only"').empty:
            raise FileManagementError(
                "Data set for plots is not complete. Try to resimulate..."
            )
        data_selection = merged_data.query('_merge=="both"')[cols]
        if data_selection.isnull().any().any():
            raise FileManagementError("Some values required for plotting are not given")
        return data_selection

    def get_plotting_data(self, plot_reqs: Dict[pd.DataFrame]) -> Dict[pd.DataFrame]:
        if self.data_path.is_file():
            available_data = self._read_file()
        else:
            raise FileManagementError(
                f"Data file {self.data_path} does not exist. Plotting data cannot be prepared"
            )
        return {
            plot_name: self._req_add_results(plot_req, available_data)
            for plot_name, plot_req in plot_reqs.items()
        }

    def update_file(self, new_data_chunk: pd.DataFrame) -> None:
        if self.data_path.is_file():
            existing_data = self._read_file()
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
