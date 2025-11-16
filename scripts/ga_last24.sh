#!/usr/bin/env bash
set -euo pipefail

SYMBOL=${1:-ADAEUR}
INTERVAL=${2:-1m}
WINDOW_MIN=${WINDOW_MIN:-1440}
POP=${GA_POPULATION:-30}
GEN=${GA_GENERATIONS:-25}
SEED=${GA_SEED:-42}

CSV_PATH="data/${SYMBOL}-${INTERVAL}-last${WINDOW_MIN}.csv"
OHL_PATH="data/${SYMBOL}-${INTERVAL}-last${WINDOW_MIN}.ohlcv"

echo "[GA-LAST24] Downloading ${WINDOW_MIN} bars for ${SYMBOL} ${INTERVAL}..."
poetry run python -m exhaustionlab.app.data.binance_rest \
  --symbol "${SYMBOL}" \
  --interval "${INTERVAL}" \
  --limit "${WINDOW_MIN}" \
  --csv "${CSV_PATH}"

GA_CMD=(poetry run python -m exhaustionlab.app.backtest.ga_optimizer
  --symbol "${SYMBOL}"
  --interval "${INTERVAL}"
  --limit "${WINDOW_MIN}"
  --population "${POP}"
  --generations "${GEN}"
  --seed "${SEED}"
  --apply
  --csv "${CSV_PATH}"
)

if [[ -f "${OHL_PATH}" ]]; then
  echo "[GA-LAST24] Found ${OHL_PATH}, PyneCore run will be triggered."
  GA_CMD+=(--pyne-ohlcv "${OHL_PATH}" --pyne-script scripts/pyne/exhaustion_signal)
else
  echo "[GA-LAST24] ${OHL_PATH} not found – PyneCore step skipped (optional)."
fi

echo "[GA-LAST24] Starting GA..."
"${GA_CMD[@]}"
