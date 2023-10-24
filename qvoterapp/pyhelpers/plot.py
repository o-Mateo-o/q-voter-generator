from pathlib import Path
from typing import Dict

import pandas as pd
from pyhelpers.dataoper import DataManager, SpecManager


class PlotCreator:
    def __init__(self, str_spec_path: str, str_data_path: str) -> None:
        self._data_manager = DataManager(Path(str_data_path))
        spec_manager = SpecManager(Path(str_spec_path))
        data_reqs = spec_manager.parse_req(plot_specific=True)
        visual_specs = spec_manager.parse_visual()
        data = self._data_manager.get_plotting_data(data_reqs)
        # self.data: Dict[pd.DataFrame] --- słownik wspólny dla visual_spec i data pod jednymi kluczami
        # ! later, when preparing plot desc, get the first row of data but prev:
        # ! -- select only non-vals/args/group(cb null) columns
        # ! -- select non-null columns
        # ! for some dict - if val not given, assign '?'

    def run(self) -> None:
        pass
