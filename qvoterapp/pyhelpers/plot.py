import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from pyhelpers.dataoper import DataManager, SpecManager
from pyhelpers.setapp import FileManagementError, QVoterAppError
from pyhelpers.utils import CompoundVar, assure_direct_params


class TextConfig(dict):
    def __init__(self) -> None:
        text_config_path = Path("qvoterapp", "text.config.json")
        if not text_config_path.is_file():
            raise FileManagementError(f"Text config file doesn't exist")
        with open(text_config_path, "r", encoding="utf-8") as f:
            try:
                self.update(json.load(f))
            except json.JSONDecodeError:
                raise FileManagementError("Cannot decode JSON spec file")


class TextBuilder:
    def __init__(self) -> None:
        self.text_config = TextConfig()

    def desc(self, name: str, mode: int) -> str:
        if isinstance(name, str):
            res = self.text_config["desc"][name][mode]
        elif isinstance(name, CompoundVar):
            name_main = name.main
            res = f"{self.text_config['desc'][name_main][mode]}{self.text_config['connectors']['scale']}"
        else:
            logging.warning(f"Name for '{name}' could not be evaluated")
            res = "?"
        return res

    def symbol(
        self, raw: Any, depending_on_name: str = None, simple_latex: bool = False
    ) -> str:
        if isinstance(raw, int):
            res = f"\({raw}\)"
        elif isinstance(raw, float):
            res = f"\({str(raw).replace('.', '{,}')}\)"
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
        if isinstance(name, str):
            return self.text_config["net_alias"][name]
        else:
            raise QVoterAppError(
                f"Wrong net alias variable type: {name}. Should be string"
            )


class PlotCreator:
    def __init__(self, str_spec_path: str, str_data_path: str) -> None:
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
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        out_dir = Path("output", f"plots_{timestamp}")
        if not out_dir.is_dir():
            os.makedirs(Path(out_dir, "images"))  # to also have sub-folder for images
        return out_dir

    def _assign_plotting_cols(self, plot_name: str) -> pd.DataFrame:
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
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        group = self.assets[plot_name]["visual_specs"]["group"]
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
        ax.set_xscale(self.assets[plot_name]["visual_specs"]["x_ax_scale"])
        ax.set_yscale(self.assets[plot_name]["visual_specs"]["y_ax_scale"])
        ax.set_xlabel(self.text_builder.symbol(args, simple_latex=True))
        ax.set_ylabel(self.text_builder.symbol(vals, args, simple_latex=True))
        ax.grid(visible=True, alpha=0.2)

        bea = tuple()
        if group:
            bea = (
                ax.legend(
                    title=self.text_builder.symbol(group, simple_latex=True),
                    loc="center left",
                    bbox_to_anchor=(1, 0.5),
                ),
            )

        filename = f"{plot_name}.pdf"
        plt.savefig(
            Path(self.out_dir, "images", filename),
            bbox_extra_artists=bea,
            bbox_inches="tight",
        )

    def _create_single_tex_desc(self, plot_name: str) -> str:
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
        tex_figure: str = self.text_config["template.fig"]
        return tex_figure.format(PARAM_plot_name=plot_name, PARAM_desc=desc)

    def _add_tex_struct(self, tex_figures: str) -> str:
        content: str = self.text_config["template.doc"]
        return content.format(PARAM_tex_figures=tex_figures)

    def run(self) -> None:
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
