"""
    Type support for int, str, float, date with validation.
"""
from enum import Enum
from typing import Any
from datetime import date, datetime


class ValueType(Enum):
    INT = "int"
    STR = "str"
    FLOAT = "float"
    DATE = "date"
    BOOL = "bool"


class TypeValidator:
    """Validation and conversion of value types"""

    @staticmethod
    def detect_type(value: Any) -> ValueType:
        """Automatically detect the type of the value"""
        if isinstance(value, bool):
            return ValueType.BOOL
        elif isinstance(value, int):
            return ValueType.INT
        elif isinstance(value, float):
            return ValueType.FLOAT
        elif isinstance(value, (date, datetime)):
            return ValueType.DATE
        elif isinstance(value, str):
            # Try parsing as int or date
            if value.isdigit():
                return ValueType.INT
            try:
                float(value)
                return ValueType.FLOAT
            except ValueError:
                pass
            try:
                datetime.fromisoformat(value)
                return ValueType.DATE
            except (ValueError, TypeError):
                pass
            return ValueType.STR
        else:
            return ValueType.STR

    @staticmethod
    def convert_to_type(value: Any, target_type: ValueType) -> Any:
        """Convert value to target type"""
        if target_type == ValueType.INT:
            return int(value)
        elif target_type == ValueType.FLOAT:
            return float(value)
        elif target_type == ValueType.DATE:
            if isinstance(value, str):
                return datetime.fromisoformat(value).date()
            elif isinstance(value, datetime):
                return value.date()
            return value
        elif target_type == ValueType.BOOL:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        else:  # STR
            return str(value)

    @staticmethod
    def validate_and_convert(value: Any, target_type: ValueType) -> Any:
        """Validate and convert value"""
        try:
            return TypeValidator.convert_to_type(value, target_type)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert {value} to {target_type.value}: {str(e)}")

    @staticmethod
    def compare(value1: Any, value2: Any, operator: str) -> bool:
        """Compare values according to operator"""
        operators = {
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '<=': lambda a, b: a <= b,
            '>': lambda a, b: a > b,
            '>=': lambda a, b: a >= b,
        }

        if operator not in operators:
            raise ValueError(f"Unknown operator: {operator}")

        try:
            return operators[operator](value1, value2)
        except TypeError as e:
            raise TypeError(f"Cannot compare {type(value1).__name__} and {type(value2).__name__}: {str(e)}")