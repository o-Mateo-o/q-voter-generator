from pyhelpers.dataoper import DataManager, SpecManager
from pathlib import Path


class PlotCreator:
    def __init__(self, str_spec_path: str, str_data_path: str) -> None:
        self.data_manager = DataManager(Path(str_data_path))
        # full_data_req = SpecManager(Path(str_spec_path)).parse()
