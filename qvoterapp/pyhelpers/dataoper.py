"""Input parsing and data related features"""

import json
import logging
from itertools import product
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pyhelpers.setapp import FileManagementError, SpecificationError
from pyhelpers.utils import CompoundVar, assure_direct_params, is_dict_with_keys


class SpecManager:
    """Input specification parser

    :param spec_path: Path to the input specification file
    :type spec_path: Path
    """

    def __init__(self, spec_path: Path) -> None:
        """Initialize an object and load the specification file"""
        self.spec = self.read_file(spec_path)

    @staticmethod
    def read_file(spec_path: Path) -> dict:
        """Read the input json file

        :param spec_path: Path to the input specification file
        :type spec_path: Path
        :raises FileManagementError: If the json file does not exist or it is corrupted
        :return: A raw input specification
        :rtype: dict
        """
        if not spec_path.is_file():
            raise FileManagementError(f"Config file '{spec_path}' doesn't exist")
        with open(spec_path, "r", encoding="utf-8") as f:
            try:
                plot_scpec = json.load(f)
            except json.JSONDecodeError:
                raise FileManagementError("Cannot decode JSON spec file")
        return plot_scpec

    @staticmethod
    def _process_value(
        val: Any, multiple: bool = False, single_str: bool = False
    ) -> Union[NDArray, str]:
        """Validate the raw value type (only [list, dict, int, float, str] allowed) and parse it.
        Create an array containing all the possible values (either the raw value itself or a processed
        list, range dictionary or a compound variable dictionary).

        :param val: A raw value
        :type val: Any
        :param multiple: A flag for scenarios where more than one value is allowed, defaults to False
        :type multiple: bool, optional
        :param single_str: A flag for scenarios where output should be a single string,
            instead of the standard array, defaults to False
        :type single_str: bool, optional
        :raises SpecificationError: In case value does not stick to the guidelines
        :return: (A) parsed value(s)
        :rtype: Union[NDArray, str]
        """
        if isinstance(val, (int, float, str)):
            parsed_val = val
        # list scenario
        elif multiple and isinstance(val, list):
            try:
                parsed_val = np.unique(np.array(val))
            except TypeError:
                raise SpecificationError(f"Invalid types of the list elements: {val}")
            if parsed_val.size == 0:
                raise SpecificationError(
                    f"Value {val} presents an empty list of parameters"
                )
        # dictionary scenarios
        elif multiple and is_dict_with_keys(val, ("start", "step", "stop")):
            parsed_val = np.arange(
                start=val["start"], step=val["step"], stop=val["stop"] + val["step"]
            )
            if parsed_val.size == 0:
                raise SpecificationError(
                    f"Value {val} presents an empty list of parameters"
                )
        elif is_dict_with_keys(val, ("params", "operations")):
            parsed_val = CompoundVar(val["params"], val["operations"], val.get("order"))
        elif isinstance(val, dict):
            raise SpecificationError(f"Dictionary value {val} schema not recognized")
        # unknown scenarios
        elif val is None:
            return None
        elif not multiple and isinstance(val, (list, dict)):
            raise SpecificationError(f"Value {val} in config cannot be non-singular")
        else:
            raise SpecificationError(
                f"Value {val} in config has an invalid type {type(val)}"
            )

        if not isinstance(parsed_val, np.ndarray) and not single_str:
            return np.array([parsed_val])
        else:
            return parsed_val

    @staticmethod
    def _drop_param_prefix(param: str) -> str:
        """Find the core name based on the prefixed json parameter keys

        :param param: A parameter key
        :type param: str
        :return: The last member of the name
        :rtype: str
        """
        return param.split(".")[-1]

    def _param_cart(self, param_dict: Dict[str, NDArray]) -> pd.DataFrame:
        """Find all the possible parameter combinations represented as data frame rows

        :param param_dict: Dictionary of the parsed values
        :type param_dict: Dict[NDArray]
        :return: Cartesian product of the possible values.
            Column names are the cleansed parameter core names
        :rtype: pd.DataFrame
        """
        # get rid of the param key prefixes
        golden_param_dict = {
            self._drop_param_prefix(param_key): param_val
            for param_key, param_val in param_dict.items()
        }
        # find all the possibilites
        product_df = pd.DataFrame(
            list(product(*golden_param_dict.values())),
            columns=list(golden_param_dict.keys()),
        )
        return product_df

    def _parse_req_part(self, part_spec: Dict[str, Any]) -> Tuple[pd.DataFrame, set]:
        """Find all the simulation parameter sets required to create one plot.
        Validate the values and process them, eventually generating all the possible combinations

        .. note::
            It does not replace compound values yet.

        :param part_spec: Sub-dictionary of a specification dictionary describing one plot
        :type part_spec: Dict[str, Any]
        :raises SpecificationError: In case value does not stick to the guidelines
        :return: Data requirements for one plot and the set of initially covered parameters
        :rtype: Tuple[pd.DataFrame, set]
        """
        part_spec = part_spec.copy()
        # process arguments to get the column with multiple values possible
        plot_args = part_spec.pop("plot.args")
        if isinstance(plot_args, str):
            plot_main_var = plot_args
        elif isinstance(self._process_value(plot_args), CompoundVar):
            plot_main_var = self._process_value(plot_args).main
        else:
            raise SpecificationError("Unknown plot argument specification")
        # Process groups
        try:
            plot_group = part_spec.pop("plot.group")
            if not isinstance(plot_group, str):
                raise SpecificationError(
                    "Grouping by a non direct parameter is not possible"
                )
        except KeyError:
            plot_group = None
        if plot_main_var == plot_group:
            raise SpecificationError(
                "Groupping variable cannot be the one used for arguments"
            )
        # both cases - group section exists and not
        if "groups" in part_spec:
            # check some conditions before further processing
            if isinstance(self._process_value(plot_main_var), CompoundVar):
                raise SpecificationError(
                    "Cannot specify compound variables for various series using 'groups' section"
                )
            if plot_group is None:
                raise SpecificationError(
                    "'groups' section can be used only if `plot.group` parameter added"
                )
            if plot_main_var in part_spec or plot_group in part_spec:
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
                    plot_main_var: self._process_value(
                        group.pop(plot_main_var), multiple=True
                    ),
                    plot_group: self._process_value(
                        group.pop(plot_group), multiple=True
                    ),
                }
                if group:
                    logging.warning(
                        f"Parser is skipping parameters remaining in some 'group' sections: {group}"
                    )
                all_plot_rel_params.append(single_plot_rel_params)
            pre_covered_param_keys = {plot_main_var, plot_group}
        else:
            # initially prepare only plot arguments
            single_plot_rel_params = {
                plot_main_var: self._process_value(
                    part_spec.pop(plot_main_var), multiple=True
                )
            }
            pre_covered_param_keys = {plot_main_var}
            # if grouping variable exists, update the data with it
            if plot_group is not None:
                single_plot_rel_params.update(
                    {
                        plot_group: self._process_value(
                            part_spec.pop(plot_group), multiple=True
                        )
                    }
                )
                pre_covered_param_keys.add(plot_group)
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
        left_mandatory_param_keys = mandatory_param_keys - pre_covered_param_keys
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
        pre_covered_param_keys_cleansed = {
            self._drop_param_prefix(param_key) for param_key in pre_covered_param_keys
        }
        return part_req, pre_covered_param_keys_cleansed
        # TODO: check if there are the same rows between `all_plot_rel_params` if so, ERROR

    def _replace_compound_vals(self, part_req: pd.DataFrame) -> pd.DataFrame:
        """Evaluate compound variables in partial requirements table

        :param part_req: A raw partial requirements table
        :type part_req: pd.DataFrame
        :return: A partial requirements table with evaluated compound variables
        :rtype: pd.DataFrame
        """
        if part_req.empty:
            return part_req
        # do it just if df is not empty
        part_req_transformed = pd.DataFrame()
        for rowdict in part_req.to_dict(orient="records"):
            rowdict_transformed = {
                colname: assure_direct_params(rowdict, rowdict[colname])
                for colname in rowdict
            }
            # ? not really efficient but the dfs tend to be small
            part_req_transformed = pd.concat(
                [part_req_transformed, pd.DataFrame([rowdict_transformed])],
                ignore_index=True,
            )
        return part_req_transformed

    @staticmethod
    def _get_part_req_desc(
        part_req: pd.DataFrame, plot_rel_param_keys: set = {}
    ) -> dict:
        """Generate the dictionary of parameter values used for a specific part (one plot).
        It can be utilized while creating a plot captions or other descriptions

        .. warning::
            Use before the compound variables evaluation.

        :param part_req: A raw requirements table with evaluated compound variables
        :type part_req: pd.DataFrame
        :param plot_rel_param_keys: Keys of the plot-related parameters, defaults to {}
        :type plot_rel_param_keys: set, optional
        :return: A parameter description dictionary
        :rtype: dict
        """
        req_desc = part_req.iloc[0].to_dict()
        req_desc = {
            param_key: param_val
            for param_key, param_val in req_desc.items()
            if param_key not in plot_rel_param_keys
        }
        return req_desc

    def parse_req(
        self, plot_specific: bool = False
    ) -> Union[pd.DataFrame, Tuple[Dict[str, pd.DataFrame]]]:
        """Prepare the full requirements for all the plots. In the 'plot_specific' mode return them
        separately in dictionaries and return also the values for the descriptions. Otherwise,
        return just a table of all the unique sets of parameters (in rows) required for plotting

        .. note::
            Methods used to get the result take care of the data quality as well,
            so they validates 'plot arg/group vs other available params' relations

        :param plot_specific: 'Plot specific' mode flag, defaults to False
        :type plot_specific: bool, optional
        :raises SpecificationError: In case of parameter key errors or other specification-related issues
        :return: Depending on the mode - a tuple of dictionaries with partial requirement tables and value descriptions
            for each plot (in a 'plot specific' mode). In a 'non plot specific' mode just a table of all the unique
            parameter combinations that has to be provided
        :rtype: Union[pd.DataFrame, Tuple[Dict[str, pd.DataFrame]]]
        """

        part_req_dict = dict()
        part_req_desc_dict = dict()
        for plot_name, part_spec in self.spec.items():
            try:
                part_req, plot_rel_param_keys = self._parse_req_part(part_spec)
                part_req_desc_dict.update(
                    {plot_name: self._get_part_req_desc(part_req, plot_rel_param_keys)}
                )
                part_req_dict.update({plot_name: self._replace_compound_vals(part_req)})
            except KeyError as err:
                raise SpecificationError(
                    f"Some key {err} is required but cannot be found in {plot_name} config"
                )
            except SpecificationError as err:
                raise SpecificationError(
                    f"The following issue encountered while parsing '{plot_name}' specification: {err}"
                )
        if plot_specific:
            return part_req_dict, part_req_desc_dict
        else:
            part_req_list = part_req_dict.values()
            full_req = pd.concat(part_req_list, ignore_index=True)
            full_req.drop_duplicates(inplace=True)
            return self._replace_compound_vals(full_req)

    def _parse_visual_part(self, part_spec: Dict[str, Any]) -> dict:
        """Prepare the graph configuration values for one plot

        :param part_spec: Sub-dictionary of a specification dictionary describing one plot
        :type part_spec: Dict[str, Any]
        :raises SpecificationError: _description_
        :return: Plotting parameters (graph configuration - scales, labels, etc/.)
        :rtype: dict
        """
        part_spec = part_spec.copy()
        plot_args = self._process_value(part_spec.pop("plot.args"), single_str=True)
        plot_group = self._process_value(part_spec.get("plot.group"), single_str=True)
        plot_vals = self._process_value(part_spec.pop("plot.vals"), single_str=True)
        if not isinstance(plot_vals, CompoundVar) and plot_vals not in (
            "exit_proba",
            "avg_exit_time",
        ):
            raise SpecificationError(f"Values {plot_vals} is an unknown measure")
        desc_info = self._process_value(
            part_spec.get("plot.desc_info", ""), single_str=True
        )
        x_ax_scale = self._process_value(
            part_spec.get("plot.x_ax_scale", "linear"), single_str=True
        )
        y_ax_scale = self._process_value(
            part_spec.get("plot.y_ax_scale", "linear"), single_str=True
        )
        accepted_ax_scales = ("linear", "log")
        if x_ax_scale not in accepted_ax_scales or x_ax_scale not in accepted_ax_scales:
            raise SpecificationError(
                f"Axis scaling must be chosen from {accepted_ax_scales} list"
            )
        if isinstance(plot_args, CompoundVar):
            plot_args.transform_names(self._drop_param_prefix)
            plot_args_var = plot_args
        else:
            plot_args_var = self._drop_param_prefix(plot_args)
        if plot_group:
            plot_group_var = self._drop_param_prefix(plot_group)
        else:
            plot_group_var = None
        return {
            "args": plot_args_var,
            "group": plot_group_var,
            "vals": plot_vals,
            "desc_info": desc_info,
            "x_ax_scale": x_ax_scale,
            "y_ax_scale": y_ax_scale,
        }

    @staticmethod
    def _validate_plot_name(plot_name: str) -> None:
        """Check if the plot name is won't cause system errors neither when saving
        as files nor rendering a latex output.
        Only alpha-numerical characters are allowed

        :param plot_name: An inserted plot name
        :type plot_name: str
        :raises SpecificationError: If the name is not valid
        """
        if not plot_name.isalnum():
            raise SpecificationError(
                f"Plot name {plot_name} is invalid. It should be alpha-numeric"
            )

    def parse_visual(self) -> Dict[str, dict]:
        """Get the plotting parameters for each plot and present them as a dictionary
        of 'visiual parameter dictionaries' with plot names as keys

        :raises SpecificationError: In case of parameter key errors or other specification-related issues
        :return: Plotting parameters for each plot
        :rtype: Dict[str, dict]
        """
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
                    f"The following issue encountered while parsing '{plot_name}' specification: {err}"
                )
        return part_visual_dict


class DataManager:
    """Output data manager. It can update the database, inform which records
    are still not in the database and add the outcome fields to the given
    secections of data

    :param data_path: A path to the data storage xml file
    :type data_path: Path
    """

    PRECISION = 3

    def __init__(self, data_path: Path) -> None:
        """Initialize an object"""
        self.data_path = data_path

    def _read_file(self) -> pd.DataFrame:
        """Read the xml data storage file

        :return: Table of the existing (simulated) data
        :rtype: pd.DataFrame
        """
        return pd.read_xml(self.data_path).set_index("index")

    def get_working_data(self, full_data_req: pd.DataFrame) -> pd.DataFrame:
        """Transform a given requirements table by skipping the rows that are already simulated
        and applying basic cleanse operations (dropna, null outcome cols assignment)

        :param full_data_req: A full requirements table (parameter sets for all the plot cases)
        :type full_data_req: pd.DataFrame
        :raises FileManagementError: If the data file is somehow incomplete/damaged and cannot be processed
        :return: Parameter sets that are not yet simulated (were not found in the database).
            Moreover, exit time and probability columns are added to the result with the null values
        :rtype: pd.DataFrame
        """
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

    def _req_add_results(
        self, req: pd.DataFrame, available_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Enrich a requirements table by the previously simulated outcomes. A helper method

        :param req: A requirements table
        :type req: pd.DataFrame
        :param available_data: A table of the simulated data
        :type available_data: pd.DataFrame
        :raises FileManagementError: If some records required for plotting are missing in the existing data frame
        :return: A rquirement table enriched by the exit times and probabilities
        :rtype: pd.DataFrame
        """
        cols = req.columns.append(pd.Index(["avg_exit_time", "exit_proba"]))
        merged_data = pd.merge(
            available_data.round(self.PRECISION),
            req.round(self.PRECISION),
            how="outer",
            indicator=True,
        )
        if not merged_data.query('_merge=="right_only"').empty:
            raise FileManagementError(
                "Data set for plots is not complete. Try to resimulate..."
            )
        data_selection = merged_data.query('_merge=="both"')[cols]
        if data_selection.isnull().any().any():
            raise FileManagementError("Some values required for plotting are not given")
        return data_selection

    def get_plotting_data(
        self, plot_reqs: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Based on a data requirements tables, get the simulated data required for plotting.
        Use the simulated records stored in the xml file

        :param plot_reqs: A plot requirements table
        :type plot_reqs: Dict[str, pd.DataFrame]
        :raises FileManagementError: If the data file cannot be read
        :return: Requirement tables enriched by the exit times and probabilities
        :rtype: Dict[str, pd.DataFrame]
        """
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
        """Append newly simulated data to the xml data storage file

        :param new_data_chunk: A chunk of some freshly simulated data
        :type new_data_chunk: pd.DataFrame
        """
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
