"""
Chart generation service for creating candlestick chart PNGs.

This module generates beautiful candlestick charts with volume bars,
signals, and technical indicators for display in the web UI.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from ..app.backtest.engine import compute_exhaustion_signals
from ..app.data.binance_rest import fetch_klines_csv_like

matplotlib.use("Agg")  # Non-interactive backend for server-side rendering

LOGGER = logging.getLogger(__name__)


class ChartGenerator:
    """Generate candlestick charts as PNG images."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize chart generator.

        Args:
            cache_dir: Directory to cache generated charts (None = no caching)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Color scheme
        self.colors = {
            "bg": "#0a0e14",
            "axes_bg": "#0f1419",
            "grid": "#1a1f2e",
            "text": "#cfd8dc",
            "muted": "#7e8ba3",
            "up": "#30ff85",
            "down": "#ff5252",
        }

    def generate_chart(
        self,
        symbol: str = "ADAEUR",
        timeframe: str = "1m",
        limit: int = 200,
        width: int = 1400,
        height: int = 800,
        show_signals: bool = True,
        show_volume: bool = True,
        trades: Optional[List[Dict[str, Any]]] = None,
        equity_curve: Optional[List[Dict[str, float]]] = None,
    ) -> bytes:
        """
        Generate a candlestick chart as PNG bytes.

        Args:
            symbol: Trading symbol (e.g., "ADAEUR")
            timeframe: Timeframe (e.g., "1m", "5m", "1h")
            limit: Number of candles to display
            width: Chart width in pixels
            height: Chart height in pixels
            show_signals: Whether to overlay exhaustion signals
            show_volume: Whether to show volume panel

        Returns:
            PNG image as bytes
        """
        cache_key = f"{symbol}_{timeframe}_{limit}_{width}x{height}_{show_signals}_{show_volume}"
        cache_file = self.cache_dir / f"{cache_key}.png" if self.cache_dir else None

        # Check cache (valid for 30 seconds)
        if cache_file and cache_file.exists():
            age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if age < 30:
                LOGGER.debug(f"Serving cached chart: {cache_key}")
                return cache_file.read_bytes()

        # Fetch data
        try:
            df = fetch_klines_csv_like(symbol=symbol, interval=timeframe, limit=limit)
            if df.empty:
                LOGGER.warning(f"No data for {symbol} {timeframe}")
                return self._generate_error_image(f"No data available for {symbol} {timeframe}", width, height)
        except Exception as exc:
            LOGGER.exception(f"Failed to fetch klines: {exc}")
            return self._generate_error_image(str(exc), width, height)

        # Prepare data for mplfinance
        df_plot = self._prepare_dataframe(df)

        # Generate chart
        try:
            img_bytes = self._render_chart(
                df_plot,
                df,
                symbol,
                timeframe,
                width,
                height,
                show_signals,
                show_volume,
                trades,
                equity_curve,
            )

            # Cache the result
            if cache_file:
                cache_file.write_bytes(img_bytes)
                LOGGER.debug(f"Cached chart: {cache_key}")

            return img_bytes

        except Exception as exc:
            LOGGER.exception(f"Failed to render chart: {exc}")
            return self._generate_error_image(str(exc), width, height)

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert klines DataFrame to mplfinance format."""
        df_plot = df.copy()

        # Convert timestamp to datetime index
        df_plot["datetime"] = pd.to_datetime(df_plot["ts_open"], unit="s")
        df_plot.set_index("datetime", inplace=True)

        # Rename columns for mplfinance
        df_plot.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )

        return df_plot[["Open", "High", "Low", "Close", "Volume"]]

    def _render_chart(
        self,
        df_plot: pd.DataFrame,
        df_orig: pd.DataFrame,
        symbol: str,
        timeframe: str,
        width: int,
        height: int,
        show_signals: bool,
        show_volume: bool,
        trades: Optional[List[Dict[str, Any]]] = None,
        equity_curve: Optional[List[Dict[str, float]]] = None,
    ) -> bytes:
        """Render the actual chart using matplotlib."""
        # Configure figure size (convert pixels to inches at 100 DPI)
        figsize = (width / 100, height / 100)

        # Create figure
        fig = Figure(figsize=figsize, facecolor=self.colors["bg"])

        if show_volume:
            # Create subplots: main chart (70%) and volume (30%)
            gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)
            ax_main = fig.add_subplot(gs[0])
            ax_vol = fig.add_subplot(gs[1], sharex=ax_main)
        else:
            ax_main = fig.add_subplot(111)
            ax_vol = None

        # Style main axis
        ax_main.set_facecolor(self.colors["axes_bg"])
        ax_main.grid(True, color=self.colors["grid"], linestyle="--", linewidth=0.5, alpha=0.5)
        ax_main.tick_params(colors=self.colors["muted"], labelsize=9)
        for spine in ax_main.spines.values():
            spine.set_color(self.colors["grid"])

        # Draw candlesticks
        self._draw_candlesticks(ax_main, df_plot)

        # Draw signals
        if show_signals:
            try:
                signals = compute_exhaustion_signals(df_orig)
                self._draw_signals(ax_main, df_plot, signals)
            except Exception as exc:
                LOGGER.warning(f"Failed to draw signals: {exc}")

        # Draw backtest trades
        if trades:
            try:
                self._draw_trades(ax_main, df_plot, trades)
            except Exception as exc:
                LOGGER.warning(f"Failed to draw trades: {exc}")

        # Draw equity curve
        if equity_curve and ax_vol:
            try:
                self._draw_equity_curve(ax_vol, equity_curve)
            except Exception as exc:
                LOGGER.warning(f"Failed to draw equity curve: {exc}")

        # Draw volume
        if show_volume and ax_vol:
            self._draw_volume(ax_vol, df_plot)

        # Set title
        ax_main.set_title(
            f"{symbol} - {timeframe}",
            fontsize=14,
            fontweight="bold",
            color="#e6f1ff",
            pad=15,
        )

        # Format x-axis
        ax_main.set_ylabel("Price", color=self.colors["text"], fontsize=10)
        if ax_vol:
            ax_vol.set_ylabel("Volume", color=self.colors["text"], fontsize=9)
            ax_vol.set_xlabel("Time", color=self.colors["text"], fontsize=9)
        else:
            ax_main.set_xlabel("Time", color=self.colors["text"], fontsize=9)

        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
            edgecolor="none",
        )
        plt.close(fig)

        buf.seek(0)
        return buf.read()

    def _draw_candlesticks(self, ax, df):
        """Draw candlestick chart."""
        for idx, (i, row) in enumerate(df.iterrows()):
            open_price = row["Open"]
            high = row["High"]
            low = row["Low"]
            close = row["Close"]

            color = self.colors["up"] if close >= open_price else self.colors["down"]

            # Draw wick
            ax.plot([idx, idx], [low, high], color=color, linewidth=1, alpha=0.8)

            # Draw body
            body_height = abs(close - open_price)
            body_bottom = min(open_price, close)

            rect = Rectangle(
                (idx - 0.3, body_bottom),
                0.6,
                body_height if body_height > 0 else 0.001,
                facecolor=color,
                edgecolor=color,
                alpha=0.9,
            )
            ax.add_patch(rect)

        ax.set_xlim(-1, len(df))
        ax.set_ylim(df["Low"].min() * 0.999, df["High"].max() * 1.001)

    def _draw_signals(self, ax, df, signals):
        """Draw exhaustion signals on chart."""
        signal_configs = [
            ("bull_l1", self.colors["up"], "^", df["Low"] * 0.998),
            ("bull_l2", "#00d1b2", "^", df["Low"] * 0.996),
            ("bull_l3", "#adffff", "^", df["Low"] * 0.994),
            ("bear_l1", self.colors["down"], "v", df["High"] * 1.002),
            ("bear_l2", "#ff7856", "v", df["High"] * 1.004),
            ("bear_l3", "#ffb478", "v", df["High"] * 1.006),
        ]

        for signal_type, color, marker, prices in signal_configs:
            if signal_type in signals.columns:
                mask = signals[signal_type].values
                if mask.any():
                    indices = [i for i, m in enumerate(mask) if m]
                    signal_prices = [prices.iloc[i] for i in indices]
                    ax.scatter(
                        indices,
                        signal_prices,
                        marker=marker,
                        s=120,
                        color=color,
                        alpha=0.8,
                        zorder=10,
                    )

    def _draw_volume(self, ax, df):
        """Draw volume bars."""
        ax.set_facecolor(self.colors["axes_bg"])
        ax.grid(True, color=self.colors["grid"], linestyle="--", linewidth=0.5, alpha=0.3)
        ax.tick_params(colors=self.colors["muted"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(self.colors["grid"])

        colors = [(self.colors["up"] if df["Close"].iloc[i] >= df["Open"].iloc[i] else self.colors["down"]) for i in range(len(df))]

        ax.bar(range(len(df)), df["Volume"], color=colors, alpha=0.6, width=0.7)
        ax.set_xlim(-1, len(df))

    def _draw_trades(self, ax, df, trades):
        """
        Draw trade markers on chart.

        trades format: [{"timestamp": ts, "type": "buy"/"sell", "price": price, "profit": float}, ...]
        """
        buy_indices = []
        buy_prices = []
        sell_indices = []
        sell_prices = []

        # Convert timestamps to indices
        timestamps = df.index.astype(int) // 10**9  # Convert to seconds

        for trade in trades:
            trade_ts = trade.get("timestamp", 0)
            trade_type = trade.get("type", "").lower()
            trade_price = trade.get("price", 0)

            # Find closest index
            try:
                idx = (timestamps - trade_ts).abs().argmin()

                if trade_type == "buy":
                    buy_indices.append(idx)
                    buy_prices.append(trade_price)
                elif trade_type == "sell":
                    sell_indices.append(idx)
                    sell_prices.append(trade_price)
            except Exception:
                continue

        # Draw buy markers (green triangles up)
        if buy_indices:
            ax.scatter(
                buy_indices,
                buy_prices,
                marker="^",
                s=200,
                color="#00ff88",
                edgecolors="white",
                linewidths=2,
                alpha=0.9,
                zorder=15,
                label="Buy",
            )

        # Draw sell markers (red triangles down)
        if sell_indices:
            ax.scatter(
                sell_indices,
                sell_prices,
                marker="v",
                s=200,
                color="#ff5252",
                edgecolors="white",
                linewidths=2,
                alpha=0.9,
                zorder=15,
                label="Sell",
            )

        # Add legend if trades exist
        if buy_indices or sell_indices:
            ax.legend(loc="upper left", framealpha=0.8, facecolor=self.colors["axes_bg"])

    def _draw_equity_curve(self, ax, equity_curve):
        """
        Draw equity curve on volume panel.

        equity_curve format: [{"timestamp": ts, "equity": value}, ...]
        """
        if not equity_curve:
            return

        # Extract data
        equities = [point["equity"] for point in equity_curve]
        indices = list(range(len(equities)))

        # Clear volume panel and repurpose for equity
        ax.clear()
        ax.set_facecolor(self.colors["axes_bg"])
        ax.grid(True, color=self.colors["grid"], linestyle="--", linewidth=0.5, alpha=0.3)
        ax.tick_params(colors=self.colors["muted"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(self.colors["grid"])

        # Plot equity curve
        ax.plot(indices, equities, color="#58a6ff", linewidth=2, alpha=0.9, label="Equity")
        ax.fill_between(
            indices,
            equities,
            equities[0],  # Starting equity as baseline
            alpha=0.2,
            color="#58a6ff",
        )

        # Add horizontal line at starting equity
        ax.axhline(
            y=equities[0],
            color=self.colors["muted"],
            linestyle="--",
            linewidth=1,
            alpha=0.5,
        )

        ax.set_xlim(-1, len(equities))
        ax.set_ylabel("Equity", color=self.colors["text"], fontsize=9)
        ax.legend(loc="upper left", framealpha=0.8, facecolor=self.colors["axes_bg"])

    def _generate_error_image(self, error_msg: str, width: int = 1400, height: int = 800) -> bytes:
        """Generate an error image with the error message."""
        fig = Figure(figsize=(width / 100, height / 100), facecolor="#0a0e14")
        ax = fig.add_subplot(111, facecolor="#0f1419")

        ax.text(
            0.5,
            0.5,
            f"Chart Generation Error\n\n{error_msg}",
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=14,
            color="#ff5252",
            transform=ax.transAxes,
        )

        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_color("#1a1f2e")
        ax.spines["bottom"].set_color("#1a1f2e")
        ax.spines["left"].set_color("#1a1f2e")
        ax.spines["right"].set_color("#1a1f2e")

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
        plt.close(fig)

        buf.seek(0)
        return buf.read()

    def clear_cache(self):
        """Clear all cached chart images."""
        if not self.cache_dir or not self.cache_dir.exists():
            return

        count = 0
        for file in self.cache_dir.glob("*.png"):
            try:
                file.unlink()
                count += 1
            except Exception as exc:
                LOGGER.warning(f"Failed to delete {file}: {exc}")

        LOGGER.info(f"Cleared {count} cached charts")


# Global instance with caching enabled
_chart_generator = ChartGenerator(cache_dir=Path.home() / ".cache" / "exhaustionlab_charts")


def get_chart_generator() -> ChartGenerator:
    """Get the global chart generator instance."""
    return _chart_generator
