import logging
from typing import Any, Iterable, List, Union

from pyhelpers.setapp import SpecificationError


class CompoundVar:
    def __init__(
        self, params: list, operations: list, order: Union[List[int], None] = None
    ) -> None:
        self.oper_translator = {
            "//": lambda a, b: a // b,
            "/": lambda a, b: a / b,
            "*": lambda a, b: a * b,
            "^": lambda a, b: a**b,
        }
        self._validate_input(params, operations)
        self.params = params
        self.operations = operations
        self.order = list(range(len(operations)))  # default

        if isinstance(order, list):
            if len(order) != len(operations) or sorted(order) != sorted(self.order):
                logging.warning(
                    f"Assigning default order to {self} with original o={order}. "
                    + "Given list had an invalid length or not consecutive elements"
                )
            else:
                self.order = order

    def _validate_input(self, params: Any, operations: Any) -> None:
        if not isinstance(params, list) or not isinstance(operations, list):
            raise SpecificationError(
                f"Invalid compound parameter structure: p={params},o={operations}"
            )
        if not (len(params) == len(operations) + 1) or len(params) < 2:
            raise SpecificationError(
                f"Invalid component/operation numbers: p={params},o={operations}"
            )
        for operation in operations:
            if operation not in self.oper_translator:
                raise SpecificationError(f"Unknown operation '{operation}'")

    @property
    def main(self) -> Any:
        return self.params[0]

    @staticmethod
    def _param_as_numeric(param: Any, data: dict) -> Union[float, int]:
        if isinstance(param, (float, int)):
            return param
        elif isinstance(param, str):
            try:
                return data[param]
            except KeyError as err:
                raise SpecificationError(
                    f"Cannot evaluate a compound value. Parameter {err} not found"
                )
        else:
            raise SpecificationError(f"Unknown compound parameter '{param}' type type")

    def eval(self, data: dict) -> Any:
        values = self.params.copy()
        popped = []
        try:
            for oper_ix in self.order:
                fun = self.oper_translator[self.operations[oper_ix]]
                curpar_ix_corrected = oper_ix - len(
                    list(filter(lambda x: x <= oper_ix, popped))
                )
                nextpar_ix_corrected = (
                    oper_ix + 1 - len(list(filter(lambda x: x <= oper_ix + 1, popped)))
                )
                values[curpar_ix_corrected] = fun(
                    self._param_as_numeric(values[curpar_ix_corrected], data),
                    self._param_as_numeric(values[nextpar_ix_corrected], data),
                )
                popped.append(nextpar_ix_corrected)
                values.pop(nextpar_ix_corrected)
        except TypeError as err:
            raise SpecificationError(f"Cannot evaluate a compound value: {err}")
        return values[0]

    def transform_names(self, fun: callable) -> None:
        self.params = [fun(param) for param in self.params]

    def __eq__(self, other) -> bool:
        return (
            (self.params == other.params)
            and (self.operations == other.operations)
            and (self.order == other.order)
        )

    def __str__(self) -> str:
        return f"<Compound variable param: {self.params}, oper: {self.operations}, ord: {self.order}>"

    def __hash__(self) -> int:
        return hash((tuple(self.params), tuple(self.operations), tuple(self.order)))


def assure_direct_params(rowdict: dict, value: Any, on_colnames: bool = False):
    # ! colname is the one that we take value to transform from
    if isinstance(value, CompoundVar):
        try:
            return value.eval(rowdict)
        except KeyError:
            raise SpecificationError(
                f"Unknown values assigned to the compound value '{value}' on input"
            )
    elif on_colnames:
        return rowdict[value]
    else:
        return value


def is_dict_with_keys(obj: Union[dict, Any], keys: Iterable) -> bool:
    if isinstance(obj, dict):
        return all(key in obj for key in keys)
    else:
        return False
