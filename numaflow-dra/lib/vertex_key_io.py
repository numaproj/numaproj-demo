from collections.abc import Iterable
from typing import Any, Self

# Support for Numpy
try:
    import numpy as np

    HAS_NUMPY = True
    NP_INTEGER = np.integer
    NP_FLOATING = np.floating
except Exception:
    HAS_NUMPY = False
    NP_INTEGER = int
    NP_FLOATING = float

Numeric = int | float | NP_INTEGER | NP_FLOATING


def _build_type_maps():
    """
    Define bidirectional map between type and type name
    """
    type_to_name: dict[type, str] = {
        int: 'int',
        float: 'float',
        str: 'str',
    }
    if HAS_NUMPY:
        # LHS is a class object, e.g. <class 'numpy.int64'>
        type_to_name.update(
            {
                np.int64: 'np.int64',
                np.float16: 'np.float16',
                np.float32: 'np.float32',
                np.float64: 'np.float64',
                np.longdouble: 'np.longdouble',
            }
        )
    # reverse mapping
    name_to_ctor: dict[str, Any] = {name: typ for typ, name in type_to_name.items()}
    return type_to_name, name_to_ctor


TYPE_TO_NAME, NAME_TO_CTOR = _build_type_maps()


class VertexKeyIO:
    """
    Use this Class to pass some data between Vertex.
    Data input/output in a Vertex is done through keys_list(a list of string).
    However, all internal data management is handled using dictionary type.

    Note: Here, "key" does not refer to a dictionary key
    , but to the "keys" variable used for data exchange between Vertices.
    e.g. Message class, Datum class

    - Most mutating methods return Self for method chaining.
    """

    # ---------- Initialization ----------
    def __init__(
        self,
        keys_list: Iterable[str] | None = None,
    ) -> None:
        """
        Accept either keys_list or data, or neither (both None).

        - If keys_list is provided, validate and load into the dict.
        """
        self._dict: dict[str, int] = {}
        # not operated internally, only used for io. Always synchronized with _dict
        self._keys_list: list[str] = []

        if keys_list is not None:
            self.set_keys_list(keys_list)

    # ---------- Read-only properties ----------
    @property
    def dict(self) -> dict[str, int]:
        """
        Return a COPY of the current dict to prevent external mutation.
        """
        return self._dict.copy()

    @property
    def keys_list(self) -> list[str]:
        """
        Return a list like ["k=v", ...] generated from the dict.
        A fresh list is returned each call (safe to modify outside).
        """
        self.dict_to_keys()
        return list(self._keys_list)  # return copy list safely

    # ---------- Conversion ----------
    def dict_to_keys(self) -> Self:
        """_dict -> _keys_list : key=(type)value"""
        out: list[str] = []
        for key, val in self._dict.items():
            type_name, str_val = self._dump(val)
            out.append(f'{key}=({type_name}){str_val}')
        self._keys_list = out
        return self

    # ---------- Setters ----------
    def set_keys_list(self, keys_list: Iterable[str]) -> Self:
        """
        Parse a `key=(type)value` list and load into the internal dict.
        Then, set _keys_list from the internal dict
        """
        tmp: dict[str, Numeric] = {}
        for idx, item in enumerate(keys_list):
            key, val = self._parse_item(item, idx)
            tmp[key] = val
        self._dict = tmp
        return self.dict_to_keys()

    # ---------- Mutations ----------
    def add(self, key: str, value: Numeric) -> Self:
        """Add or update an element and sync"""
        if not isinstance(value, tuple(TYPE_TO_NAME.keys())):
            msg = f'value must be one of {tuple(TYPE_TO_NAME.keys())}, got {type(value)!r}'
            raise TypeError(msg)
        self._dict[str(key)] = value
        return self.dict_to_keys()

    def remove(self, key: str) -> Self:
        """Remove element (ignore if absent) and sync"""
        self._dict.pop(str(key), None)
        return self.dict_to_keys()

    # ---------- Access (read-only) ----------
    def get(self, key: str, default: Numeric | None = None) -> int | None:
        """Get a value from the dict"""
        return self._dict.get(key, default)

    def __getitem__(self, key: str) -> int:
        """Allow m['x'] access (may raise KeyError)"""
        return self._dict[key]

    def __contains__(self, key: object) -> bool:  # type: ignore[override]
        """Support 'x' in m"""
        return key in self._dict

    def keys(self) -> tuple[str, ...]:
        """Keys as immutable tuple"""
        return tuple(self._dict.keys())

    def values(self) -> tuple[Numeric, ...]:
        """Values as immutable tuple"""
        return tuple(self._dict.values())

    def items(self) -> tuple[tuple[str, Numeric], ...]:
        """(key, value) Items as immutable tuple of tuples"""
        return tuple(self._dict.items())

    def __len__(self) -> int:
        """Number of items"""
        return len(self._dict)

    def __iter__(self):
        """Iterate over keys"""
        return iter(self._dict)

    # ---------- Internal utilities ----------
    @staticmethod
    def _split_key_rest(item: str, idx: int) -> tuple[str, str]:
        """
        Split once by '=' in the 'key=(type)value' format and return (key, rest).
        """
        if item.count('=') != 1:
            msg = f"keys_list[{idx}] must be 'key=(type)value': {item!r}"
            raise ValueError(msg)
        key, rest = (p.strip() for p in item.split('=', 1))
        if not key:
            msg = f'keys_list[{idx}] empty key: {item!r}'
            raise ValueError(msg)
        return key, rest

    def _parse_item(self, item: str, idx: int) -> tuple[str, int]:
        """
        Convert a single 'key=(type)value' item into (key, value).
        """
        key, v_str = VertexKeyIO._split_key_rest(item, idx)
        if not (v_str.startswith('(') and ')' in v_str):
            msg = f'keys_list[{idx}] must include explicit (type): {item!r}'
            raise ValueError(msg)
        r = v_str.find(')')
        type_name = v_str[1:r].strip()
        str_val = v_str[r + 1 :].strip()
        return key, self._load(type_name, str_val, idx, item)

    # ---------- Dump / Load ----------
    def _dump(self, value: Numeric) -> tuple[str, str]:
        """
        Get (type_name, str_val) from the given value.
        """
        for typ, type_name in TYPE_TO_NAME.items():
            if isinstance(value, typ):
                if typ is int or issubclass(typ, NP_INTEGER):
                    return type_name, str(value)
                if typ is float or issubclass(typ, NP_FLOATING):
                    return type_name, repr(
                        float(value)
                    )  # Use repr(float(...)) for float / np.floatXX for a stable string
                if typ is str:
                    return type_name, value

        msg = f'Unsupported value type: {type(value)!r}'
        raise TypeError(msg)

    def _load(self, type_name: str, str_val: str, idx: int, item: str) -> Numeric:
        """
        Reconstruct a value from (type_name, str_val).
        """
        # ctor is short for constructor.  It represents a type (class object),
        # and calling it generates an instance of that type.
        ctor = NAME_TO_CTOR.get(type_name)
        if ctor is None:
            allowed_type = ', '.join(sorted(NAME_TO_CTOR.keys()))
            msg = (
                f"keys_list[{idx}] unknown type '{type_name}'. "
                f'Allowed Type: {allowed_type}. '
                f'Item: {item!r}'
            )
            raise ValueError(msg)
        try:
            # int/float/np.floatXX can be constructed from str
            return ctor(str_val)
        except Exception as e:
            msg = f'keys_list[{idx}] cannot parse value for type {type_name}: {item!r}'
            raise ValueError(msg) from e
