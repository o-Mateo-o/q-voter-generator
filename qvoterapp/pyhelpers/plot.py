import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from pyhelpers.dataoper import DataManager, SpecManager


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
        self.out_dir = self._provide_dir()
        self.graph_translator = {
            "BA": "Barabasiego-Alberta",
            "WS": "Wattsa-Strogatza",
            "C": "pełnym",
        }
        self.plot_translator = {
            "mc_runs": "\(M\)",
            "net_type": "Model grafu",
            "q": "\(q\)",
            "x": "\(x\)",
            "size": "\(N\)",
            "eps": "\(\\varepsilon\)",
            "avg_exit_time": "\(T\)",
            "exit_proba": "\(E\)",
            "k": "\(k\)",
            "beta": "\(\\beta\)",
        }
        self.desc_translator = {
            "mc_runs": (
                "Liczba uśrednień Monte Carlo",
                "Liczby uśrednień Monte Carlo",
                "Liczb uśrednień Monte Carlo",
            ),
            "net_type": ("model grafu", "modelu grafu", "modeli grafu"),
            "q": ("wartość", "wartości", "wartości"),
            "x": (
                "początkowa proporcja opinii",
                "początkowej proporcji opinii",
                "początkowych proporcji opinii",
            ),
            "size": ("rozmiar systemu", "rozmiaru systemu", "rozmiarów systemu"),
            "eps": ("poziom szumu", "poziomu szumu", "poziomów szumu"),
            "avg_exit_time": (
                "średni czas wyjścia",
                "średniego czasu wyjścia",
                "średnich czasów wyjścia",
            ),
            "exit_proba": (
                "prawdopodobieństwo wyjścia",
                "prawdopodobieństwa wyjścia",
                "prawdopodobieństw wyjścia",
            ),
        }

    def _provide_dir(self) -> Path:
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        out_dir = Path("output", f"plots_{timestamp}")
        if not out_dir.is_dir():
            os.makedirs(Path(out_dir, "images"))  # to also have sub-folder for images
        return out_dir

    @staticmethod
    def _simplyfy_math(expr: str) -> str:
        return expr.replace("\(", "$").replace("\)", "$")

    def _assign_final_val_col(self, plot_name: str) -> pd.DataFrame:
        df = self.assets[plot_name]["data"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        # TODO ------------------------------------------------------ if not isintance(vals, CompoundVar):
        df["VALUES"] = df[vals]

    def _create_single_plot(self, plot_name: str) -> None:
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        group = self.assets[plot_name]["visual_specs"]["group"]
        self._assign_final_val_col(plot_name)
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(
            data=self.assets[plot_name]["data"],
            x=args,
            y=vals,
            hue=group,
            palette=sns.color_palette("tab10"),
            marker="o",
            linewidth=1,
            linestyle="dashed",
            ax=ax,
        )
        ax.set_xscale(self.assets[plot_name]["visual_specs"]["x_ax_scale"])
        ax.set_yscale(self.assets[plot_name]["visual_specs"]["y_ax_scale"])
        ax.set_xlabel(self._simplyfy_math(f"{self.plot_translator[args]}"))
        ax.set_ylabel(
            # TODO: SOLVE THE COMPOUND VALUE CASE -- consider that `vals` is either a single variable or CompoundVar
            self._simplyfy_math(
                f"{self.plot_translator[vals]}({self.plot_translator[args]})"
            )
        )
        ax.grid(visible=True, alpha=0.2)

        if group:
            lgd = ax.legend(
                title=self._simplyfy_math(self.plot_translator[group]),
                loc="center left",
                bbox_to_anchor=(1, 0.5),
            )
        else:
            lgd = ax.legend().set_visible(False)
        bea = (lgd,) if lgd else tuple()

        filename = f"{plot_name}.pdf"
        plt.savefig(
            Path(self.out_dir, "images", filename),
            bbox_extra_artists=bea,
            bbox_inches="tight",
        )

    def _create_single_tex_desc(self, plot_name: str) -> str:
        params: dict = self.assets[plot_name]["param_desc"]

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
            f"{self.desc_translator[key][1]} {self.plot_translator[key]}\( = {str(val).replace('.', '{,}')}\)"
            for key, val in params.items()
        ]
        desc = "Zależność {vals} od {args} na grafie {graph}, dla {group}{other_params}. {mc_runs}. {info}".format(
            # TODO: SOLVE THE COMPOUND VALUE CASE -- consider that `vals` is either a single variable or CompoundVar ----- also there
            # TODO: generally translating all the args should be replaced by that, 'cause there is a possibility...
            vals=self.desc_translator[vals][1],
            args=self.desc_translator[args][1],
            graph=self.graph_translator[net_type],
            group=f"różnych {self.desc_translator[group][2]} oraz " if group else "",
            other_params=", ".join(other_params[:-1]) + " i " + other_params[-1],
            mc_runs=f"{self.desc_translator['mc_runs'][0]} {self.plot_translator['mc_runs']}\( = {mc_runs}\)",
            info=self.assets[plot_name]["visual_specs"]["desc_info"],
        )
        desc = desc.replace("\)\(", "")
        return desc

    @staticmethod
    def _figurize_desc(plot_name: str, desc: str) -> str:
        tex_figure = f"""
        \\begin{{figure}}[]
        \centering
        \includegraphics[width=13cm]{{images/{plot_name}.pdf}}
        \caption{{{desc}}}
        \label{{fig:{plot_name}}}
        \end{{figure}}"""
        return tex_figure

    @staticmethod
    def _add_tex_struct(tex_figures: str) -> str:
        content = f"""
        \\documentclass{{report}}
        \\usepackage[utf8]{{inputenc}}
        \\usepackage{{graphicx}}
        \\usepackage{{polski}}
        \\begin{{document}}
        {tex_figures}
        \\end{{document}}"""
        return content

    def run(self) -> None:
        logging.info(
            f'Generating plots. They will be saved to "{self.out_dir.absolute()}"...'
        )
        tex_descs = []
        for plot_name in self.assets:
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
