"""Helper objects and small functions"""

import logging
from typing import Any, Iterable, List, Union

from pyhelpers.setapp import SpecificationError


class CompoundVar:
    """A compund variable that consist of more than basic parameter or number
    and can be evaluated anytime.
    Objects of this type cannot be nested

    :param params: Parameters (numbers/symbols) being the variable components
    :type params: list
    :param operations: Operations performed on the parameters (basic algebra)
    :type operations: list
    :param order: Order of the operations, defaults to None
    :type order: Union[List[int], None], optional
    """

    def __init__(
        self, params: list, operations: list, order: Union[List[int], None] = None
    ) -> None:
        """Initializa an object. Validate the arguments and assign proper order"""
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
        """Check if the parameters and operations are of a correct type and stik to the natural guidelines

        :param params: A raw parameters collection
        :type params: Any
        :param operations: A raw operations collection
        :type operations: Any
        :raises SpecificationError: If the components or operations are incorrect
        """
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
        """Get the main (first) parameter

        :return: Main element of a variable
        :rtype: Any
        """
        return self.params[0]

    @staticmethod
    def _param_as_numeric(param: Any, data: dict) -> Union[float, int]:
        """Get the numeric value of a parameted. For the string input try to evaluate
        it from the data dict provided

        :param param: A parameter or any value
        :type param: Any
        :param data: Dictionary of parameter names and values
        :type data: dict
        :raises SpecificationError: If a parameter cannot be evaluated (is not found)
        :return:
        :rtype: Union[float, int]
        """
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
        """Find the ultimate value of the compound variable
        (perform the calculations specified on in init args)

        :param data: Dictionary of parameter names and values (real parameter values)
        :type data: dict
        :raises SpecificationError: If for some (type-related) reason the value cannot be found
        :return: Numerical value of the compound variable
        :rtype: Any
        """
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
        """Transform the compound variable parameter names using a given function

        :param fun: A relatively safe string transformation function
        :type fun: callable
        """
        self.params = [fun(param) for param in self.params]

    def __eq__(self, other) -> bool:
        """Tell if two compound variables are the same based on their parameters, operations
        and orders

        :param other: Another compound variable
        :type other: CompoundVar
        :return: Objects equality
        :rtype: bool
        """
        return (
            (self.params == other.params)
            and (self.operations == other.operations)
            and (self.order == other.order)
        )

    def __str__(self) -> str:
        """Get a string representation of the object

        :return: String representation
        :rtype: str
        """
        return f"<Compound variable param: {self.params}, oper: {self.operations}, ord: {self.order}>"

    def __hash__(self) -> int:
        """Find the hash value

        :return: Hash value
        :rtype: int
        """
        return hash((tuple(self.params), tuple(self.operations), tuple(self.order)))


def assure_direct_params(rowdict: dict, value: Any, on_colnames: bool = False) -> Any:
    """Assure the parameter value or name regardless of its compound/non-compound type

    :param rowdict: Some parameters
    :type rowdict: dict
    :param value: Name of the parameter
    :type value: Any
    :param on_colnames: Use if the input `value` are is a column name - not a direct 'value', defaults to False
    :type on_colnames: bool, optional
    :raises SpecificationError: If the compound variable cannot be evaluated
    :return: Safe, direct parameter or name
    :rtype: Any
    """
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
    """Check if a given object is a dictionary and has all the keys provided in the argument

    :param obj: A tested object
    :type obj: Union[dict, Any]
    :param keys: Collection of the required keys
    :type keys: Iterable
    :return: Info if the conditions are satisfied
    :rtype: bool
    """
    if isinstance(obj, dict):
        return all(key in obj for key in keys)
    else:
        return False
