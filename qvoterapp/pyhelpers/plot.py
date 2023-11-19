"""Plotting and reporting features"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Union
from typing_extensions import Self

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from pyhelpers.dataoper import DataManager, SpecManager
from pyhelpers.setapp import FileManagementError, QVoterAppError
from pyhelpers.utils import CompoundVar, assure_direct_params


class TextTranslatorDict(dict):
    """A custom dictionary storing text translation settings"""

    def __getitem__(self, __key: str) -> Union[Self, Any]:
        """Access the text translation settings tree branch aliased by the given key.
        If the key was not found, return an empty object of the same type (to avoid nested read attempts)

        :param __key: Key of an element
        :type __key: str
        :return: Sub-TextTranslatorDictionary or a value from the settings tree
        :rtype: Union[Self, Any]
        """
        try:
            __val = super().__getitem__(__key)
        except KeyError as err:
            logging.warning(
                f"Access to the {err} variable in the text translation dictionary failed. Assigning '[ ? ]'"
            )
            return TextTranslatorDict()

        if isinstance(__val, dict):
            return TextTranslatorDict(__val)
        else:
            return __val

    def __str__(self) -> str:
        """Get a text representation of the dictionary. However, if it is empty,
        return a special placeholder value

        :raises ValueError: On non-empty settings tree displey attempts
        :return: A string placeholder (solely for an empty dict!!!)
        :rtype: str
        """
        if self:
            raise ValueError(
                "Non-empty text translation settings tree object cannot be printed"
            )
            # ? optionally can be changed to this: `return super().__str__()`
        else:
            return "[ ? ]"


class TextConfig(TextTranslatorDict):
    """A custom dictionary storing full text translation settings tree and loads it from file on init

    :raises FileManagementError: If the settings file cannot be read
    """

    def __init__(self) -> None:
        """Initialize an object and read load the settings file as items"""
        text_config_path = Path("qvoterapp", "text.config.json")
        if not text_config_path.is_file():
            raise FileManagementError(f"Text config file doesn't exist")
        with open(text_config_path, "r", encoding="utf-8") as f:
            try:
                self.update(json.load(f))
            except json.JSONDecodeError:
                raise FileManagementError("Cannot decode JSON spec file")


class TextBuilder:
    """A worker that processes the text values used either for plotting or generating plot captions"""

    def __init__(self) -> None:
        """Initialize an object."""
        self.text_config = TextConfig()

    def desc(self, name: str, mode: int) -> str:
        """Get a phrase describing a parameter (grammar cases switched with the ``mode`` argument)

        :param name: Name of the parameter (no prefixes)
        :type name: str
        :param mode: Number indicating a grammatical case. Please refer to the settings file to see the details
        :type mode: int
        :return: Phrase describing a parameter
        :rtype: str
        """
        if isinstance(name, str):
            res = self.text_config["desc"][name][mode]
        elif isinstance(name, CompoundVar):
            # ? Assumes that all all the operations (purpose of CompoundVar) on the parameter can be called 'scaling'
            res = f"{self.text_config['desc'][name.main][mode]}{self.text_config['connectors']['scale']}"
        else:
            logging.warning(f"Name for '{name}' could not be evaluated")
            res = "?"
        return res

    def symbol(
        self, raw: Any, depending_on_name: str = None, simple_latex: bool = False
    ) -> str:
        """Get a mathematical symbol representing a parameter as a latex string

        :param raw: A raw parameter name
        :type raw: Any
        :param depending_on_name: Name of the function argument if the main value is a function, defaults to None
        :type depending_on_name: str, optional
        :param simple_latex: Flag to simplify the latex (eg. for a silly - yet awesomoe - pyplot engine), defaults to False
        :type simple_latex: bool, optional
        :raises QVoterAppError: If the CompoundVar math symbol cannot is not available
        :return: A latex representation of the parameter
        :rtype: str
        """
        if isinstance(raw, int):
            res = f"\({raw}\)"
        elif isinstance(raw, float):
            res = f"\({{{str(raw).replace('.', '{,}')}}}\)"
        elif isinstance(raw, str):
            res = self.text_config["symbol"][raw]
        elif isinstance(raw, CompoundVar):
            args = [self.symbol(param) for param in raw.params]
            opers = [self.symbol(operation) for operation in raw.operations]
            res_list = [None] * (len(args) + len(opers))
            res_list[::2] = args
            res_list[1::2] = opers
            res = "".join(res_list)
            if len(args) > 2:
                logging.warning(
                    f"{raw} representation might be inaccurate. "
                    + "Currently there is no order-parenthesis support for complex compound variables"
                )
        else:
            raise QVoterAppError(f"Unknown math symbol type: {raw}")

        if depending_on_name:
            depending_on_res = self.symbol(depending_on_name)
            if isinstance(raw, CompoundVar):
                res = f"{res} ({depending_on_res})"
            else:
                res = f"{res}({depending_on_res})"

        if simple_latex:
            return res.replace("\(", "$").replace("\)", "$").replace("$$", "")
        else:
            return res.replace("\(\)", "")

    def net_alias(self, name: str) -> str:
        """Get a text representation of a network name (being given an alias for it's type)

        :param name: A network type alias
        :type name: str
        :raises QVoterAppError: If a given network type is not available
        :return: A text representation of a network name
        :rtype: str
        """
        if isinstance(name, str):
            return self.text_config["net_alias"][name]
        else:
            raise QVoterAppError(
                f"Wrong net alias variable type: {name}. Should be string"
            )


class PlotCreator:
    """A worker that creates all the plots and merges them into a tex report with captions

    :param str_spec_path: A path to the plot specification json file
    :type str_spec_path: str
    :param str_data_path: A path to the xml output data storage file
    :type str_data_path: str
    """

    def __init__(self, str_spec_path: str, str_data_path: str) -> None:
        """Initialize an object (having prepared all the data sets and plot settings)"""
        data_manager = DataManager(Path(str_data_path))
        spec_manager = SpecManager(Path(str_spec_path))
        data_reqs, data_req_descs = spec_manager.parse_req(plot_specific=True)
        visual_specs = spec_manager.parse_visual()
        data = data_manager.get_plotting_data(data_reqs)
        self.assets = {
            plot_name: {
                "data": plot_data,
                "visual_specs": visual_specs[plot_name],
                "param_desc": data_req_descs[plot_name],
            }
            for plot_name, plot_data in data.items()
        }
        self.text_config = TextConfig()
        self.text_builder = TextBuilder()
        self.out_dir = self._provide_dir()

    def _provide_dir(self) -> Path:
        """Create the directories for images & report. Add the timestamp to the name

        :return: A path to the newly created report directory
        :rtype: Path
        """
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        out_dir = Path("output", f"plots_{timestamp}")
        if not out_dir.is_dir():
            os.makedirs(Path(out_dir, "images"))  # to also have sub-folder for images
        return out_dir

    def _assign_plotting_cols(self, plot_name: str) -> pd.DataFrame:
        """Assign the plot argument & value columns to the data frame related to the given
        plot name

        :param plot_name: A name of the plot (given in the specification file)
        :type plot_name: str
        :return: A data frame enriched by the evaluated arguments & values
        :rtype: pd.DataFrame
        """
        df = self.assets[plot_name]["data"]
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        df["__ARGUMENTS__"] = df.apply(
            lambda rowdict: assure_direct_params(rowdict, args, on_colnames=True),
            axis=1,
        )
        df["__VALUES__"] = df.apply(
            lambda rowdict: assure_direct_params(rowdict, vals, on_colnames=True),
            axis=1,
        )

    def _create_single_plot(self, plot_name: str) -> None:
        """Create a single plot using seaborn/pyplot and save it to the pdf file

        :param plot_name: A name of the plot (given in the specification file)
        :type plot_name: str
        """
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        group = self.assets[plot_name]["visual_specs"]["group"]
        # create the basic plot
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(
            data=self.assets[plot_name]["data"],
            x="__ARGUMENTS__",
            y="__VALUES__",
            hue=group,
            palette=sns.color_palette("tab10"),
            marker="o",
            linewidth=1,
            linestyle="dashed",
            ax=ax,
        )
        # alter the plot
        ax.set_xscale(self.assets[plot_name]["visual_specs"]["x_ax_scale"])
        ax.set_yscale(self.assets[plot_name]["visual_specs"]["y_ax_scale"])
        ax.set_xlabel(self.text_builder.symbol(args, simple_latex=True))
        ax.set_ylabel(self.text_builder.symbol(vals, args, simple_latex=True))
        ax.grid(visible=True, alpha=0.2)
        # placing for both the cases when a legend is displyed and if it is not
        bea = tuple()
        if group:
            bea = (
                ax.legend(
                    title=self.text_builder.symbol(group, simple_latex=True),
                    loc="center left",
                    bbox_to_anchor=(1, 0.5),
                ),
            )
        # save the fig
        filename = f"{plot_name}.pdf"
        plt.savefig(
            Path(self.out_dir, "images", filename),
            bbox_extra_artists=bea,
            bbox_inches="tight",
        )

    def _create_single_tex_desc(self, plot_name: str) -> str:
        """Create a single plot caption describing all the parameters used in the
        plot

        :param plot_name: A name of the plot (given in the specification file)
        :type plot_name: str
        :return: A plot caption
        :rtype: str
        """
        params = self.assets[plot_name]["param_desc"]
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        group = self.assets[plot_name]["visual_specs"]["group"]
        net_type = params.pop("net_type")
        params = {
            param_key: param_val
            for param_key, param_val in params.items()
            if param_key not in {"avg_exit_time", "exit_proba"}
        }
        mc_runs = params.pop("mc_runs")
        other_params = [
            f"{self.text_builder.desc(key, 1)} {self.text_builder.symbol(key)}"
            + f"\( = \){self.text_builder.symbol(val)}"
            for key, val in params.items()
        ]
        group_info = ""
        if group:
            group_info = self.text_config["template.group_info"].format(
                group_desc=self.text_builder.desc(group, 2),
                group_sym=self.text_builder.symbol(group),
            )
        description = self.text_config["template.desc"].format(
            vals=f"{self.text_builder.desc(vals, 1)} ({self.text_builder.symbol(vals)})",
            args=f"{self.text_builder.desc(args, 1)} ({self.text_builder.symbol(args)})",
            graph=self.text_builder.net_alias(net_type),
            group=group_info,
            other_params=", ".join(other_params[:-1])
            + self.text_config["connectors"]["and1"]
            + other_params[-1],
            mc_runs=f"{self.text_builder.desc('mc_runs', 0)} {self.text_builder.symbol('mc_runs')}\( = {mc_runs}\)",
            info=self.assets[plot_name]["visual_specs"]["desc_info"],
        )
        description = description.replace("\)\(", "")
        return description

    def _figurize_desc(self, plot_name: str, desc: str) -> str:
        """Create a latex figure code for one plot

        :param plot_name: A name of the plot (given in the specification file)
        :type plot_name: str
        :param desc: The caption
        :type desc: str
        :return: Latex source code for the figure
        :rtype: str
        """
        tex_figure: str = self.text_config["template.fig"]
        return tex_figure.format(PARAM_plot_name=plot_name, PARAM_desc=desc)

    def _add_tex_struct(self, tex_figures: str) -> str:
        """Embed the latex figures in the latex document structure

        :param tex_figures: All the fiures combined as one string
        :type tex_figures: str
        :return: A full latex code of a report
        :rtype: str
        """
        content: str = self.text_config["template.doc"]
        return content.format(PARAM_tex_figures=tex_figures)

    def run(self) -> None:
        """Generate the entire report (and its image assets) and save it"""
        logging.info(
            f'Generating plots. They will be saved to "{self.out_dir.absolute()}"...'
        )
        tex_descs = []
        for plot_name in self.assets:
            self._assign_plotting_cols(plot_name)
            self._create_single_plot(plot_name)
            tex_descs.append(
                self._figurize_desc(plot_name, self._create_single_tex_desc(plot_name))
            )
            logging.info(f"Plot '{plot_name}' created and saved.")
        tex_figures = "\n\n".join(tex_descs)
        tex_content = self._add_tex_struct(tex_figures)
        with open(Path(self.out_dir, "plots.tex"), "w", encoding="utf-8") as f:
            f.write(tex_content)
        logging.info(
            "Tex file with all the plots and description has been added to the same folder."
        )
