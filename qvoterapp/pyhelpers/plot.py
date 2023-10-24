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
        data_reqs = spec_manager.parse_req(plot_specific=True)
        visual_specs = spec_manager.parse_visual()
        data = data_manager.get_plotting_data(data_reqs)
        self.assets = {
            plot_name: {
                "data": plot_data,
                "visual_specs": visual_specs[plot_name],
            }
            for plot_name, plot_data in data.items()
        }
        self.out_dir = self._provide_dir()
        self.plot_translator = {
            "mc_runs": "$M$",
            "net_type": "Model grafu",
            "q": "$q$",
            "x": "$x$",
            "size": "$N$",
            "eps": "$\\varepsilon$",
            "avg_exit_time": "$T$",
            "exit_proba": "$E$",
            "k": "$k$",
            "beta": "$\\beta$",
        }
        self.desc_translator = {
            "mc_runs": "liczba uśrednień Monte Carlo",
            "net_type": "model grafu",
            "q": "liczba $q$ sąsiadów",
            "x": "początkowa proporcja opinii",
            "size": "rozmiar",
            "eps": "szum",
            "avg_exit_time": "średni czas wyjścia",
            "exit_proba": "prawdopodobieństwo wyjścia",
        }
        # ! later, when preparing plot desc, get the first row of data but prev:
        # ! -- select only non-vals/args/group(cb null) columns
        # ! -- select non-null columns
        # ! for some dict - if val not given, assign '?'

    def _provide_dir(self) -> Path:
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        out_dir = Path("output", f"plots_{timestamp}")
        if not out_dir.is_dir():
            os.makedirs(Path(out_dir, "images"))  # to also have sub-folder for images
        return out_dir

    def _single_plot(self, plot_name: str):
        fig, ax = plt.subplots(figsize=(6, 4))
        args = self.assets[plot_name]["visual_specs"]["args"]
        vals = self.assets[plot_name]["visual_specs"]["vals"]
        group = self.assets[plot_name]["visual_specs"]["group"]
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
        ax.set_xlabel(f"{self.plot_translator[args]}")
        ax.set_ylabel(f"{self.plot_translator[vals]}({self.plot_translator[args]})")
        ax.grid(visible=True, alpha=0.2)

        if group:
            lgd = ax.legend(
                title=self.plot_translator[group],
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

    def run(self) -> None:
        logging.info(
            f'Generating plots. They will be saved to "{self.out_dir.absolute()}"...'
        )
        for plot_name in self.assets:
            self._single_plot(plot_name)
            logging.info(f"Plot '{plot_name}' created and saved.")
