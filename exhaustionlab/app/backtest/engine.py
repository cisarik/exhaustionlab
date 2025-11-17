from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd


def compute_exhaustion_signals(df: pd.DataFrame, level1=9, level2=12, level3=14) -> pd.DataFrame:
    """Lightweight Python replica of your Exhaustion logic for GUI overlays.
    Returns DataFrame with boolean columns: bull_l1, bull_l2, bull_l3, bear_l1, bear_l2, bear_l3.
    Uses close vs close[n] rules.
    """
    n = len(df)
    bull = 0
    bear = 0
    out = {
        "bull_l1": [False] * n,
        "bull_l2": [False] * n,
        "bull_l3": [False] * n,
        "bear_l1": [False] * n,
        "bear_l2": [False] * n,
        "bear_l3": [False] * n,
    }
    closes = df["close"].tolist()

    def reset_and_recheck(c, c4):
        if c < c4:
            return 1, 0, 1  # bull, bear, cycle=bull
        if c > c4:
            return 0, 1, 1  # bull, bear, cycle=bear
        return 0, 0, 0

    cycle = 0
    for i in range(n):
        c = closes[i]
        c4 = closes[i - 4] if i - 4 >= 0 else c
        c3 = closes[i - 3] if i - 3 >= 0 else c
        c2 = closes[i - 2] if i - 2 >= 0 else c

        currentBull = bull
        currentBear = bear
        currentCycle = cycle

        if currentCycle < level1:
            if c < c4:
                bull = currentBull + 1
                bear = 0
                cycle = bull
            elif c > c4:
                bear = currentBear + 1
                bull = 0
                cycle = bear
            else:
                rb, rs, rc = reset_and_recheck(c, c4)
                bull, bear, cycle = rb, rs, rc
        else:
            if currentBull > 0:
                if currentBull < level2:
                    if c < c3:
                        bull = currentBull + 1
                        cycle = bull
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bull, bear, cycle = rb, rs, rc
                elif currentBull < level3 - 1:
                    if c < c2:
                        bull = currentBull + 1
                        cycle = bull
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bull, bear, cycle = rb, rs, rc
                elif currentBull == level3 - 1:
                    if c < c2:
                        bull = level3
                        cycle = bull
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bull, bear, cycle = rb, rs, rc
            elif currentBear > 0:
                if currentBear < level2:
                    if c > c3:
                        bear = currentBear + 1
                        cycle = bear
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bear, bull, cycle = rs, rb, rc
                elif currentBear < level3 - 1:
                    if c > c2:
                        bear = currentBear + 1
                        cycle = bear
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bear, bull, cycle = rs, rb, rc
                elif currentBear == level3 - 1:
                    if c > c2:
                        bear = level3
                        cycle = bear
                    else:
                        rb, rs, rc = reset_and_recheck(c, c4)
                        bear, bull, cycle = rs, rb, rc
            else:
                rb, rs, rc = reset_and_recheck(c, c4)
                bull, bear, cycle = rb, rs, rc

        # flags
        if bull == level1:
            out["bull_l1"][i] = True
        if bull == level2:
            out["bull_l2"][i] = True
        if bull == level3:
            out["bull_l3"][i] = True
        if bear == level1:
            out["bear_l1"][i] = True
        if bear == level2:
            out["bear_l2"][i] = True
        if bear == level3:
            out["bear_l3"][i] = True

        if bull == level3 or bear == level3:
            bull = 0
            bear = 0
            cycle = 0

    return pd.DataFrame(out)


@dataclass
class PyneRunResult:
    command: Iterable[str]
    returncode: int
    stdout: str
    stderr: str
    output_dir: Path


def run_pyne(
    input_ohlcv_path: str,
    script_name: str = "scripts/pyne/exhaustion_signal",
    *,
    params: Optional[Dict[str, str | float | int | bool]] = None,
    output_dir: str | Path | None = None,
    pyne_executable: str | None = None,
    timeout: int = 300,
) -> PyneRunResult:
    """Invoke PyneCore CLI (`pyne run ...`) from Python code.

    Args:
        input_ohlcv_path: Path to `.ohlcv` file or CSV ak to Pyne podporuje.
        script_name: PyneCore skript (lokálna cesta alebo entry v PYNE_PATH).
        params: voliteľné `key=value` páry, ktoré sa pridajú ako `--param key=value`.
        output_dir: ak zadáš, Pyne tam uloží výsledky; inak sa vytvorí dočasný priečinok.
        pyne_executable: custom binárka (default `pyne` podľa PATH alebo env `PYNE_BIN`).
        timeout: ochrana proti zaseknutému procesu (sekundy).

    Returns:
        PyneRunResult s cestou k výstupu + zachyteným stdout/stderr.

    Raises:
        FileNotFoundError: ak `pyne` nie je nainštalované.
        RuntimeError: pri nenulovom návratovom kóde (stderr je súčasťou výsledku).
    """

    pyne_bin = pyne_executable or os.environ.get("PYNE_BIN") or "pyne"
    resolved_bin = shutil.which(pyne_bin)
    if not resolved_bin:
        raise FileNotFoundError(f"Pyne executable '{pyne_bin}' not found. Install `pynesys-pynecore[cli]` inside the Poetry env.")

    input_path = Path(input_ohlcv_path).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input OHLCV file '{input_path}' does not exist.")

    out_dir = Path(output_dir).expanduser().resolve() if output_dir else Path(tempfile.mkdtemp(prefix="pyne-run-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [resolved_bin, "run", script_name, str(input_path), "--output", str(out_dir)]
    if params:
        for key, value in params.items():
            cmd.extend(["--param", f"{key}={value}"])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    result = PyneRunResult(
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        output_dir=out_dir,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Pyne run failed (exit {proc.returncode}).\nCMD: {' '.join(cmd)}\nSTDERR:\n{proc.stderr}")
    return result
