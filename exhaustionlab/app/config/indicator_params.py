from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class ParamSpec:
    name: str
    label: str
    default: float | int | bool
    min_value: float | int
    max_value: float | int
    step: float
    kind: str = "float"  # float | int | bool
    description: str = ""


SQUEEZE_PARAM_SPECS: Tuple[ParamSpec, ...] = (
    ParamSpec(
        name="length_bb",
        label="BB Length",
        default=20,
        min_value=5,
        max_value=200,
        step=1,
        kind="int",
        description="Number of bars for Bollinger Band SMA/stdev.",
    ),
    ParamSpec(
        name="mult_bb",
        label="BB Mult",
        default=2.0,
        min_value=1.0,
        max_value=4.0,
        step=0.1,
        kind="float",
        description="Std-dev multiplier for Bollinger Bands.",
    ),
    ParamSpec(
        name="length_kc",
        label="KC Length",
        default=20,
        min_value=5,
        max_value=200,
        step=1,
        kind="int",
        description="Rolling window for Keltner Channels.",
    ),
    ParamSpec(
        name="mult_kc",
        label="KC Mult",
        default=1.5,
        min_value=1.0,
        max_value=4.0,
        step=0.1,
        kind="float",
        description="ATR/TrueRange multiplier for Keltner Channels.",
    ),
    ParamSpec(
        name="use_true_range",
        label="Use True Range",
        default=True,
        min_value=0,
        max_value=1,
        step=1,
        kind="bool",
        description="If enabled, use True Range instead of High-Low for KC.",
    ),
)

_OVERRIDE_PATH = Path(__file__).with_name("squeeze_params.json")


def squeeze_default_params() -> Dict[str, float | int | bool]:
    return {spec.name: spec.default for spec in SQUEEZE_PARAM_SPECS}


def load_active_squeeze_params() -> Dict[str, float | int | bool]:
    params = squeeze_default_params()
    if _OVERRIDE_PATH.exists():
        try:
            overrides = json.loads(_OVERRIDE_PATH.read_text())
            for key, value in overrides.items():
                if key in params:
                    params[key] = value
        except json.JSONDecodeError:
            pass
    return params


def save_squeeze_params(params: Dict[str, float | int | bool]) -> None:
    _OVERRIDE_PATH.write_text(json.dumps(params, indent=2, sort_keys=True))


def squeeze_param_bounds() -> Dict[str, Tuple[float | int, float | int, float]]:
    """Metadata for GA / optimization search."""
    return {
        spec.name: (spec.min_value, spec.max_value, spec.step)
        for spec in SQUEEZE_PARAM_SPECS
    }


__all__ = [
    "ParamSpec",
    "SQUEEZE_PARAM_SPECS",
    "squeeze_default_params",
    "load_active_squeeze_params",
    "save_squeeze_params",
    "squeeze_param_bounds",
]
