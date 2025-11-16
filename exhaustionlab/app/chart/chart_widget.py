import asyncio
import datetime as dt
from typing import Callable, Dict, List, Optional

import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .candle_item import CandlestickItem
from ..backtest.engine import compute_exhaustion_signals
from ..backtest.indicators import compute_squeeze_momentum
from ..config.indicator_params import load_active_squeeze_params
from ..data.binance_rest import fetch_klines_csv_like
from ..data.binance_ws import BinanceBookTickerWS, BinanceWS


class TimeAxisItem(pg.AxisItem):
    """Axis that renders bar indices as HH:MM timestamps."""

    def __init__(self, get_df: Callable[[], pd.DataFrame]):
        super().__init__(orientation="bottom")
        self._get_df = get_df

    def tickStrings(self, values, scale, spacing):
        df = self._get_df()
        if df.empty:
            return ["" for _ in values]
        ts = df["ts_open"].tolist()
        last_idx = len(ts) - 1
        out = []
        for v in values:
            idx = int(round(v))
            if 0 <= idx <= last_idx:
                stamp = dt.datetime.fromtimestamp(ts[idx])
                out.append(stamp.strftime("%H:%M"))
            else:
                out.append("")
        return out


class ChartWidget(QWidget):
    LEVEL_KEYS = ("l1", "l2", "l3", "bl1", "bl2", "bl3")

    def __init__(self, show_l1=True, show_l2=True, show_l3=True, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.info_label = QLabel("Loading candlesticks...")
        self.info_label.setObjectName("chart-info-label")
        self.info_label.setStyleSheet(
            "#chart-info-label { color: #cfd8dc; font-size: 12px; padding: 4px 8px; }"
        )
        layout.addWidget(self.info_label)

        axis_main = TimeAxisItem(lambda: self._df)
        self.view = pg.PlotWidget(axisItems={"bottom": axis_main}, enableMenu=False)
        self.view.showGrid(x=True, y=True, alpha=0.2)
        self.view.setBackground("k")
        self.view.setMenuEnabled(False)
        self.view.hideButtons()
        self.view.getAxis("bottom").setStyle(showValues=False)
        layout.addWidget(self.view, 4)

        axis_sqz = TimeAxisItem(lambda: self._df)
        self.squeeze_view = pg.PlotWidget(
            axisItems={"bottom": axis_sqz}, enableMenu=False
        )
        self.squeeze_view.setBackground("#05070b")
        self.squeeze_view.showGrid(x=False, y=True, alpha=0.1)
        self.squeeze_view.setMenuEnabled(False)
        self.squeeze_view.hideButtons()
        self.squeeze_view.setMouseEnabled(x=False, y=False)
        self.squeeze_view.getAxis("bottom").setStyle(showValues=False)
        layout.addWidget(self.squeeze_view, 2)
        self.squeeze_view.setXLink(self.view)

        axis_vol = TimeAxisItem(lambda: self._df)
        self.volume_view = pg.PlotWidget(
            axisItems={"bottom": axis_vol}, enableMenu=False
        )
        self.volume_view.setBackground("#080b10")
        self.volume_view.showGrid(x=False, y=True, alpha=0.15)
        self.volume_view.setMaximumHeight(160)
        self.volume_view.setMenuEnabled(False)
        self.volume_view.hideButtons()
        self.volume_view.setMouseEnabled(x=False, y=False)
        self.volume_view.getAxis("right").setStyle(showValues=False)
        layout.addWidget(self.volume_view, 1)
        self.volume_view.setXLink(self.view)

        self._show = dict(l1=show_l1, l2=show_l2, l3=show_l3)
        self._candle_item = None
        self._scatter_items = {k: [] for k in self.LEVEL_KEYS}
        self._kline_ws = None
        self._quote_ws = None
        self._last_sig = None
        self._latest_quote: Dict[str, float] | None = None
        self._crosshair_active = False
        self._volume_items: List[pg.BarGraphItem] = []
        self._squeeze_df = pd.DataFrame()
        self._squeeze_hist_items: List[pg.BarGraphItem] = []
        self._squeeze_zero_items: List[pg.ScatterPlotItem] = []
        self._auto_follow = True
        self._last_price_value: Optional[float] = None
        self._price_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(38, 174, 255, 200), width=1.25)
        )
        self._price_curve.setZValue(15)
        self.view.addItem(self._price_curve)
        self._sqz_params = load_active_squeeze_params()

        self._level_styles = {
            "l1": dict(color=(48, 255, 133), angle=90, field="low", factor=0.998),
            "l2": dict(color=(0, 209, 178), angle=90, field="low", factor=0.996),
            "l3": dict(color=(173, 255, 255), angle=90, field="low", factor=0.994),
            "bl1": dict(color=(255, 82, 82), angle=-90, field="high", factor=1.002),
            "bl2": dict(color=(255, 120, 86), angle=-90, field="high", factor=1.004),
            "bl3": dict(color=(255, 180, 120), angle=-90, field="high", factor=1.006),
        }
        self._sqz_bar_colors = {
            "lime": (48, 255, 133, 230),
            "green": (0, 190, 120, 220),
            "red": (255, 82, 82, 230),
            "maroon": (190, 45, 45, 220),
        }
        self._sqz_zero_colors = {
            "blue": (0, 136, 255),
            "black": (20, 24, 28),
            "gray": (140, 150, 160),
        }

        self._plot_item = self.view.getPlotItem()
        self._v_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=(150, 150, 150, 160), style=Qt.DashLine, width=1),
        )
        self._h_line = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(color=(150, 150, 150, 160), style=Qt.DashLine, width=1),
        )
        self._volume_v_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=(80, 80, 80, 150), style=Qt.DashLine, width=1),
        )
        self._squeeze_v_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=(80, 80, 80, 150), style=Qt.DashLine, width=1),
        )
        self._v_line.setZValue(100)
        self._h_line.setZValue(100)
        self._volume_v_line.setZValue(50)
        self.view.addItem(self._v_line, ignoreBounds=True)
        self.view.addItem(self._h_line, ignoreBounds=True)
        self.volume_view.addItem(self._volume_v_line, ignoreBounds=True)
        self.squeeze_view.addItem(self._squeeze_v_line, ignoreBounds=True)
        self._set_crosshair_visible(False)
        self._mouse_proxy = pg.SignalProxy(
            self.view.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved
        )

        self._price_lines = {
            "last": self._create_price_line(color=(0, 170, 255), prefix="Last "),
            "bid": self._create_price_line(color=(48, 255, 133), prefix="Bid  "),
            "ask": self._create_price_line(color=(255, 82, 82), prefix="Ask  "),
        }

    def leaveEvent(self, event):
        self._set_crosshair_visible(False)
        super().leaveEvent(event)

    def set_signal_visibility(self, l1=None, l2=None, l3=None):
        if l1 is not None:
            self._show["l1"] = l1
        if l2 is not None:
            self._show["l2"] = l2
        if l3 is not None:
            self._show["l3"] = l3
        self._replot_signals()

    def set_squeeze_param(self, name: str, value):
        if name not in self._sqz_params:
            return
        if self._sqz_params[name] == value:
            return
        self._sqz_params[name] = value
        self._update_squeeze_data()

    def _replot_signals(self):
        if self._last_sig is not None:
            self._overlay_scatter(self._last_sig)

    def bootstrap_load(
        self, symbol="ADAEUR", timeframe="1m", enable_ws=True, limit=500
    ):
        # 1) initial REST load
        df = fetch_klines_csv_like(
            symbol=symbol, interval=timeframe, limit=min(max(limit, 50), 1000)
        )
        self._set_df(df)
        # 2) live updates
        if enable_ws:
            self._start_ws(symbol, timeframe)
        else:
            self._stop_ws()

    def _set_df(self, df: pd.DataFrame):
        self._df = df.sort_values("ts_open").reset_index(drop=True)
        if self._candle_item is None:
            self._candle_item = CandlestickItem(self._df)
            self.view.addItem(self._candle_item)
        else:
            self._candle_item.update_data(self._df)
        self._candle_item.setZValue(10)
        self._update_price_curve()
        self._recompute_and_overlay_signals()
        self._update_squeeze_data()
        self._update_volume_bars()

        self._last_price_value = None
        if not self._df.empty:
            self._set_price_line("last", float(self._df["close"].iloc[-1]))
        self._set_price_line("bid", None)
        self._set_price_line("ask", None)
        self._latest_quote = None
        self._auto_range(force=True)
        self._update_info_label()

    def _recompute_and_overlay_signals(self):
        if self._df.empty:
            return
        sig = compute_exhaustion_signals(self._df)
        self._last_sig = sig
        self._overlay_scatter(sig)

    def _overlay_scatter(self, sig: pd.DataFrame):
        self._clear_scatter_items()

        # Add new (indices = x, price = y)
        def add_markers(mask, key):
            base = key.replace("bl", "l")
            if not self._show.get(base, True):
                return
            idxs = [i for i, flag in enumerate(mask) if flag]
            if not idxs:
                return
            style = self._level_styles[key]
            items = []
            for i in idxs:
                price = self._df.loc[i, style["field"]] * style["factor"]
                color = style["color"]
                arrow = pg.ArrowItem(
                    angle=style["angle"],
                    brush=pg.mkBrush(*color, 230),
                    pen=pg.mkPen(color=color, width=1),
                    headLen=10,
                    headWidth=7,
                    tailLen=6,
                )
                arrow.setPos(i, price)
                arrow.setZValue(40)
                self.view.addItem(arrow)
                items.append(arrow)
            self._scatter_items[key] = items

        add_markers(sig["bull_l1"].tolist(), "l1")
        add_markers(sig["bull_l2"].tolist(), "l2")
        add_markers(sig["bull_l3"].tolist(), "l3")
        add_markers(sig["bear_l1"].tolist(), "bl1")
        add_markers(sig["bear_l2"].tolist(), "bl2")
        add_markers(sig["bear_l3"].tolist(), "bl3")

    def _start_ws(self, symbol, timeframe):
        self._stop_ws()
        self._kline_ws = BinanceWS(
            symbol=symbol, interval=timeframe, on_kline=self._on_kline
        )
        self._quote_ws = BinanceBookTickerWS(symbol=symbol, on_quote=self._on_quote)
        loop = asyncio.get_event_loop()
        loop.create_task(self._kline_ws.start())
        loop.create_task(self._quote_ws.start())

    def _stop_ws(self):
        loop = asyncio.get_event_loop()
        if self._kline_ws:
            loop.create_task(self._kline_ws.stop())
            self._kline_ws = None
        if self._quote_ws:
            loop.create_task(self._quote_ws.stop())
            self._quote_ws = None

    def _on_kline(self, kline: dict):
        # kline: dict with 't','o','h','l','c','v','x' (binance)
        if self._df.empty:
            return
        # append or update last
        last_idx = len(self._df) - 1
        is_closed = kline.get("x", False)
        row = {
            "ts_open": kline["t"] / 1000.0,
            "open": float(kline["o"]),
            "high": float(kline["h"]),
            "low": float(kline["l"]),
            "close": float(kline["c"]),
            "volume": float(kline["v"]),
        }
        # if same bar (same open time), replace last; else append
        if int(self._df.loc[last_idx, "ts_open"] * 1000) == int(kline["t"]):
            for k, v in row.items():
                self._df.loc[last_idx, k] = v
        else:
            self._df.loc[len(self._df)] = row

        # update graphics & overlays
        self._candle_item.update_data(self._df)
        self._set_price_line("last", row["close"])
        self._update_price_curve()
        self._update_squeeze_data()
        self._update_volume_bars()
        if not self._crosshair_active:
            self._update_info_label()

        # recompute signals only on closed bar for stability
        if is_closed:
            self._recompute_and_overlay_signals()
            self._auto_range()
        else:
            self._ensure_latest_visible()

    def _on_quote(self, quote: dict):
        self._latest_quote = quote
        self._set_price_line("bid", quote["bid"])
        self._set_price_line("ask", quote["ask"])
        if not self._crosshair_active:
            self._update_info_label()

    def set_auto_follow(self, enabled: bool):
        self._auto_follow = bool(enabled)
        if enabled:
            self._auto_range(force=True)

    def _auto_range(self, lookback: int = 200, force: bool = False):
        if self._df.empty:
            return
        right = len(self._df) - 1
        left = max(0, right - lookback)
        if self._auto_follow or force:
            self.view.setXRange(left, right + 1, padding=0)
            self.squeeze_view.setXRange(left, right + 1, padding=0)
            self.volume_view.setXRange(left, right + 1, padding=0)
        window = self._df.iloc[left:]
        if not window.empty:
            y_min = float(window["low"].min())
            y_max = float(window["high"].max())
        else:
            y_min = float(self._df["low"].min())
            y_max = float(self._df["high"].max())
        padding = (y_max - y_min) * 0.05 if y_max != y_min else max(y_max * 0.01, 0.1)
        self.view.setYRange(y_min - padding, y_max + padding)
        self._update_volume_range(start_index=left)

    def _ensure_latest_visible(self):
        if self._df.empty or not self._auto_follow:
            return
        x_range, _ = self.view.viewRange()
        right = len(self._df) - 1
        if right - x_range[1] < 5:
            width = max(50, x_range[1] - x_range[0])
            left = max(0, right - width)
            self.view.setXRange(left, right + 1, padding=0)
            self.squeeze_view.setXRange(left, right + 1, padding=0)
            self.volume_view.setXRange(left, right + 1, padding=0)

    def _create_price_line(self, color, prefix):
        line = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen(color=color, width=1.2)
        )
        line.setZValue(90)
        self.view.addItem(line)
        label = pg.InfLineLabel(
            line,
            text="",
            position=0.96,
            anchors=(1, 1),
            color=color,
            fill=(15, 18, 25, 220),
        )
        line.hide()
        label.setVisible(False)
        return {"line": line, "label": label, "prefix": prefix}

    def _set_price_line(self, key: str, price: float | None):
        item = self._price_lines[key]
        line = item["line"]
        label = item["label"]
        prefix = item["prefix"]
        if price is None:
            line.hide()
            label.setVisible(False)
            return
        arrow = ""
        if key == "last":
            if self._last_price_value is not None:
                if price > self._last_price_value:
                    arrow = " ^"
                elif price < self._last_price_value:
                    arrow = " v"
            self._last_price_value = price
        line.setPos(price)
        line.show()
        label.setText(f"{prefix}{price:.5f}{arrow}")
        label.setVisible(True)

    def _set_crosshair_visible(self, visible: bool):
        self._crosshair_active = visible
        self._v_line.setVisible(visible)
        self._h_line.setVisible(visible)
        self._volume_v_line.setVisible(visible)
        self._squeeze_v_line.setVisible(visible)
        if not visible:
            self._update_info_label()

    def _on_mouse_moved(self, evt):
        if self._df.empty:
            return
        pos = evt[0]
        if not self.view.sceneBoundingRect().contains(pos):
            self._set_crosshair_visible(False)
            return
        mouse_point = self._plot_item.vb.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()
        if x < 0 or x > len(self._df) - 1:
            self._set_crosshair_visible(False)
            return

        idx = int(round(x))
        row = self._df.iloc[idx]
        self._set_crosshair_visible(True)
        self._v_line.setPos(idx)
        self._h_line.setPos(y)
        self._volume_v_line.setPos(idx)
        self._squeeze_v_line.setPos(idx)
        self._update_info_label(row=row, bar_index=idx)

    def _update_info_label(self, row=None, bar_index: int | None = None):
        if row is None:
            if self._df.empty:
                self.info_label.setText("Waiting for data...")
                return
            row = self._df.iloc[-1]
            bar_index = len(self._df) - 1
        ts = dt.datetime.fromtimestamp(row["ts_open"]).strftime("%Y-%m-%d %H:%M")
        prev_close = row["close"]
        if bar_index is not None and bar_index > 0:
            prev_close = self._df.iloc[bar_index - 1]["close"]
        delta = row["close"] - prev_close
        pct = (delta / prev_close * 100) if prev_close else 0.0
        info = (
            f"{ts}  |  O {row.open:.5f}  H {row.high:.5f}  "
            f"L {row.low:.5f}  C {row.close:.5f}  V {row.volume:.0f}  "
            f"Δ {delta:+.5f} ({pct:+.2f}%)"
        )
        if bar_index is not None:
            info = f"#{bar_index}  " + info
        if self._latest_quote:
            info += (
                f"  |  Bid {self._latest_quote['bid']:.5f}  "
                f"Ask {self._latest_quote['ask']:.5f}"
            )
        self.info_label.setText(info)

    def _clear_scatter_items(self):
        for items in self._scatter_items.values():
            for item in items:
                try:
                    self.view.removeItem(item)
                except Exception:
                    pass
        self._scatter_items = {k: [] for k in self.LEVEL_KEYS}

    def _update_price_curve(self):
        if self._df.empty:
            self._price_curve.clear()
            return
        x = list(range(len(self._df)))
        y = self._df["close"].tolist()
        self._price_curve.setData(x=x, y=y, connect="finite")

    def _update_squeeze_data(self):
        if self._df.empty:
            self._squeeze_df = pd.DataFrame()
            self._clear_squeeze_items()
            return
        self._squeeze_df = compute_squeeze_momentum(self._df, **self._sqz_params)
        self._update_squeeze_plot()

    def _clear_squeeze_items(self):
        for item in self._squeeze_hist_items + self._squeeze_zero_items:
            try:
                self.squeeze_view.removeItem(item)
            except Exception:
                pass
        self._squeeze_hist_items = []
        self._squeeze_zero_items = []

    def _update_squeeze_plot(self):
        self._clear_squeeze_items()
        if self._squeeze_df.empty:
            return
        data = self._squeeze_df
        for color_key, rgba in self._sqz_bar_colors.items():
            mask = data["bar_color"] == color_key
            if not mask.any():
                continue
            item = pg.BarGraphItem(
                x=data.index[mask].to_numpy(),
                height=data.loc[mask, "value"].to_numpy(),
                width=0.65,
                y0=0,
                brush=pg.mkBrush(rgba),
                pen=pg.mkPen(color=rgba, width=0.5),
            )
            self.squeeze_view.addItem(item)
            self._squeeze_hist_items.append(item)
        for color_key, rgb in self._sqz_zero_colors.items():
            mask = data["zero_color"] == color_key
            if not mask.any():
                continue
            scatter = pg.ScatterPlotItem(
                size=5,
                pen=pg.mkPen(color=rgb, width=1),
                brush=pg.mkBrush(rgb[0], rgb[1], rgb[2], 120),
                symbol="x",
            )
            scatter.addPoints([{"pos": (int(i), 0)} for i in data.index[mask]])
            self.squeeze_view.addItem(scatter)
            self._squeeze_zero_items.append(scatter)
        max_val = max(abs(data["value"].max()), abs(data["value"].min()))
        max_val = max_val if max_val > 0 else 1.0
        self.squeeze_view.setYRange(-max_val * 1.25, max_val * 1.25)

    def _update_volume_bars(self):
        for item in self._volume_items:
            try:
                self.volume_view.removeItem(item)
            except Exception:
                pass
        self._volume_items = []
        if self._df.empty:
            return
        volumes = self._df["volume"].tolist()
        up_idx = []
        up_vol = []
        down_idx = []
        down_vol = []
        closes = self._df["close"].tolist()
        opens = self._df["open"].tolist()
        for i in range(len(self._df)):
            if closes[i] >= opens[i]:
                up_idx.append(i)
                up_vol.append(volumes[i])
            else:
                down_idx.append(i)
                down_vol.append(volumes[i])
        if up_idx:
            up_item = pg.BarGraphItem(
                x=up_idx,
                height=up_vol,
                width=0.7,
                brush=pg.mkBrush(48, 255, 133, 160),
                pen=pg.mkPen(48, 255, 133, width=0.5),
            )
            self.volume_view.addItem(up_item)
            self._volume_items.append(up_item)
        if down_idx:
            down_item = pg.BarGraphItem(
                x=down_idx,
                height=down_vol,
                width=0.7,
                brush=pg.mkBrush(255, 82, 82, 160),
                pen=pg.mkPen(255, 82, 82, width=0.5),
            )
            self.volume_view.addItem(down_item)
            self._volume_items.append(down_item)
        self._update_volume_range()

    def _update_volume_range(self, start_index: int = 0):
        if self._df.empty:
            return
        window = self._df["volume"].iloc[start_index:]
        if window.empty:
            window = self._df["volume"]
        recent = window.tail(200)
        vmax = float(recent.max()) if not recent.empty else 0.0
        vmax = vmax if vmax > 0 else 1.0
        self.volume_view.setYRange(0, vmax * 1.25)

    def get_squeeze_params(self) -> Dict[str, float | int | bool]:
        return dict(self._sqz_params)
