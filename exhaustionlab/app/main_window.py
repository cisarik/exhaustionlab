import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot, QTimer, QProcess, QSignalBlocker
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .chart.chart_widget import ChartWidget
from .config.indicator_params import (
    SQUEEZE_PARAM_SPECS,
    load_active_squeeze_params,
)
from ..utils.config import settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExhaustionLab — Candles + WS + Backtest")
        self.resize(1400, 900)

        self.active_symbol = settings.symbol
        self.active_timeframe = settings.timeframe
        self.ga_process: QProcess | None = None
        self._last_ga_fitness: float | None = None

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        toolbar = self._build_toolbar()
        root_layout.addLayout(toolbar)

        self.status_strip = QLabel("")
        self.status_strip.setObjectName("status-strip")
        self.status_strip.setStyleSheet(
            "#status-strip { padding: 4px; color: #cfd8dc; }"
        )
        root_layout.addWidget(self.status_strip)

        self.splitter = QSplitter(Qt.Horizontal)
        self.control_panel = self._build_control_panel()
        self.splitter.addWidget(self.control_panel)

        self.chart = ChartWidget()
        self.splitter.addWidget(self.chart)
        self.splitter.setStretchFactor(1, 1)
        root_layout.addWidget(self.splitter, 1)

        self._connect_top_bar()
        self._load_params_from_chart()
        self._update_status_strip()

        QTimer.singleShot(0, self._initial_bootstrap)

    # --- UI Builders -----------------------------------------------------------------
    def _build_toolbar(self):

        toolbar = QHBoxLayout()
        self.exchange_label = QLabel(
            f"Exchange={settings.exchange} Symbol={self.active_symbol} TF={self.active_timeframe}"
        )

        self.cb_l1 = QCheckBox("L1")
        self.cb_l1.setChecked(True)
        self.cb_l2 = QCheckBox("L2")
        self.cb_l2.setChecked(True)
        self.cb_l3 = QCheckBox("L3")
        self.cb_l3.setChecked(True)
        self.cb_follow = QCheckBox("Follow last")
        self.cb_follow.setChecked(True)
        self.btn_reload = QPushButton("Reload Window")
        self.btn_toggle_panel = QPushButton("Hide Panel")

        toolbar.addWidget(self.exchange_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.cb_l1)
        toolbar.addWidget(self.cb_l2)
        toolbar.addWidget(self.cb_l3)
        toolbar.addWidget(self.cb_follow)
        toolbar.addWidget(self.btn_reload)
        toolbar.addWidget(self.btn_toggle_panel)
        return toolbar

    def _build_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.sqz_controls = {}
        layout.addWidget(self._create_squeeze_group())
        layout.addWidget(self._create_data_group())
        layout.addWidget(self._create_ga_group())
        layout.addStretch(1)
        return panel

    def _create_squeeze_group(self):
        params = load_active_squeeze_params()
        group = QGroupBox("Squeeze Momentum (SQZMOM)")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setContentsMargins(8, 8, 8, 8)
        for spec in SQUEEZE_PARAM_SPECS:
            value = params.get(spec.name, spec.default)
            if spec.kind == "bool":
                ctrl = QCheckBox(spec.label)
                ctrl.setChecked(bool(value))
                ctrl.toggled.connect(
                    lambda state, name=spec.name: self._on_sqz_param_changed(
                        name, bool(state)
                    )
                )
                form.addRow(ctrl)
            else:
                if spec.kind == "int":
                    ctrl = QSpinBox()
                    ctrl.setRange(int(spec.min_value), int(spec.max_value))
                    ctrl.setSingleStep(int(spec.step))
                    ctrl.setValue(int(value))
                    ctrl.valueChanged.connect(
                        lambda val, name=spec.name: self._on_sqz_param_changed(
                            name, int(val)
                        )
                    )
                else:
                    ctrl = QDoubleSpinBox()
                    ctrl.setRange(float(spec.min_value), float(spec.max_value))
                    ctrl.setSingleStep(float(spec.step))
                    decimals = 0
                    step_str = f"{spec.step}"
                    if "." in step_str:
                        decimals = len(step_str.split(".")[1].rstrip("0"))
                    ctrl.setDecimals(decimals)
                    ctrl.setValue(float(value))
                    ctrl.valueChanged.connect(
                        lambda val, name=spec.name: self._on_sqz_param_changed(
                            name, float(val)
                        )
                    )
                form.addRow(spec.label, ctrl)
            self.sqz_controls[spec.name] = ctrl
        return group

    def _create_data_group(self):
        group = QGroupBox("Data Window")
        layout = QFormLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)

        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        symbols = [self.active_symbol, "BTCUSDT", "ETHUSDT"]
        seen = set()
        for sym in symbols:
            if sym not in seen:
                self.symbol_combo.addItem(sym)
                seen.add(sym)
        self.symbol_combo.setCurrentText(self.active_symbol)

        self.tf_combo = QComboBox()
        for tf in ["1m", "3m", "5m", "15m", "30m", "1h", "4h"]:
            self.tf_combo.addItem(tf)
        self.tf_combo.setCurrentText(self.active_timeframe)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(100, 2000)
        self.window_spin.setValue(720)
        self.window_spin.setSuffix(" bars")

        self.btn_reload_window = QPushButton("Apply & Reload")

        layout.addRow("Symbol", self.symbol_combo)
        layout.addRow("Timeframe", self.tf_combo)
        layout.addRow("Window", self.window_spin)
        layout.addRow(self.btn_reload_window)
        return group

    def _create_ga_group(self):
        group = QGroupBox("Backtest & GA")
        layout = QFormLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)

        self.ga_pop = QSpinBox()
        self.ga_pop.setRange(4, 200)
        self.ga_pop.setValue(30)
        self.ga_gen = QSpinBox()
        self.ga_gen.setRange(2, 200)
        self.ga_gen.setValue(25)
        self.ga_seed = QSpinBox()
        self.ga_seed.setRange(0, 100000)
        self.ga_seed.setValue(42)
        self.pyne_path = QLineEdit(
            str(Path("data") / f"{self.active_symbol}-{self.active_timeframe}.ohlcv")
        )

        self.btn_ga_window = QPushButton("Run GA (window)")
        self.btn_ga_daily = QPushButton("Run GA 24h")

        layout.addRow("Population", self.ga_pop)
        layout.addRow("Generations", self.ga_gen)
        layout.addRow("Seed", self.ga_seed)
        layout.addRow("Pyne .ohlcv", self.pyne_path)
        layout.addRow(self.btn_ga_window)
        layout.addRow(self.btn_ga_daily)

        self.ga_log = QPlainTextEdit()
        self.ga_log.setReadOnly(True)
        self.ga_log.setMinimumHeight(150)
        layout.addRow("Logs", self.ga_log)
        return group

    # --- Event wiring -----------------------------------------------------------------
    def _connect_top_bar(self):
        self.cb_l1.toggled.connect(lambda v: self.chart.set_signal_visibility(l1=v))
        self.cb_l2.toggled.connect(lambda v: self.chart.set_signal_visibility(l2=v))
        self.cb_l3.toggled.connect(lambda v: self.chart.set_signal_visibility(l3=v))
        self.cb_follow.toggled.connect(self.chart.set_auto_follow)
        self.btn_reload.clicked.connect(self._reload_window)
        self.btn_toggle_panel.clicked.connect(self._toggle_panel)
        self.btn_reload_window.clicked.connect(self._reload_window)
        self.btn_ga_window.clicked.connect(self._run_ga_for_window)
        self.btn_ga_daily.clicked.connect(self._run_ga_daily)

    # --- Actions ----------------------------------------------------------------------
    def _initial_bootstrap(self):
        self._reload_window()

    @Slot()
    def _reload_window(self):
        self.active_symbol = self.symbol_combo.currentText().strip().upper()
        self.active_timeframe = self.tf_combo.currentText().strip()
        limit = max(100, min(self.window_spin.value(), 2000))
        self.exchange_label.setText(
            f"Exchange={settings.exchange} Symbol={self.active_symbol} TF={self.active_timeframe}"
        )
        self.chart.bootstrap_load(
            symbol=self.active_symbol,
            timeframe=self.active_timeframe,
            enable_ws=settings.ws_enabled,
            limit=limit,
        )
        self._update_status_strip()

    def _toggle_panel(self):
        visible = self.control_panel.isVisible()
        self.control_panel.setVisible(not visible)
        self.btn_toggle_panel.setText("Show Panel" if visible else "Hide Panel")
        if not visible:
            self.splitter.setSizes([300, self.width() - 320])

    def _on_sqz_param_changed(self, name, value):
        self.chart.set_squeeze_param(name, value)
        self._update_status_strip()

    def _run_ga_for_window(self):
        symbol = self.symbol_combo.currentText().strip().upper()
        tf = self.tf_combo.currentText().strip()
        limit = max(100, min(self.window_spin.value(), 2000))
        cmd = [
            sys.executable,
            "-m",
            "exhaustionlab.app.backtest.ga_optimizer",
            "--symbol",
            symbol,
            "--interval",
            tf,
            "--limit",
            str(limit),
            "--population",
            str(self.ga_pop.value()),
            "--generations",
            str(self.ga_gen.value()),
            "--seed",
            str(self.ga_seed.value()),
            "--apply",
        ]
        pyne_path = self.pyne_path.text().strip()
        if pyne_path:
            cmd.extend(
                [
                    "--pyne-ohlcv",
                    pyne_path,
                    "--pyne-script",
                    "scripts/pyne/exhaustion_signal",
                ]
            )
        self._start_ga_process(cmd, f"GA window ({symbol} {tf})")

    def _run_ga_daily(self):
        symbol = self.symbol_combo.currentText().strip().upper()
        tf = self.tf_combo.currentText().strip()
        cmd = [
            sys.executable,
            "-m",
            "exhaustionlab.app.backtest.ga_optimizer",
            "--symbol",
            symbol,
            "--interval",
            tf,
            "--limit",
            "1440",
            "--population",
            str(self.ga_pop.value()),
            "--generations",
            str(self.ga_gen.value()),
            "--seed",
            str(self.ga_seed.value()),
            "--apply",
        ]
        pyne_path = self.pyne_path.text().strip()
        if pyne_path:
            cmd.extend(
                [
                    "--pyne-ohlcv",
                    pyne_path,
                    "--pyne-script",
                    "scripts/pyne/exhaustion_signal",
                ]
            )
        self._start_ga_process(cmd, "GA last 24h")

    def _start_ga_process(self, cmd, description):
        if self.ga_process and self.ga_process.state() != QProcess.NotRunning:
            QMessageBox.information(
                self, "GA running", "Another GA process is already running."
            )
            return
        self.ga_log.appendPlainText(f"\n>>> {description}\n{' '.join(cmd)}\n")
        self.ga_process = QProcess(self)
        self.ga_process.readyReadStandardOutput.connect(self._handle_ga_stdout)
        self.ga_process.readyReadStandardError.connect(self._handle_ga_stderr)
        self.ga_process.finished.connect(self._handle_ga_finished)
        self.ga_process.start(cmd[0], cmd[1:])

    def _handle_ga_stdout(self):
        if not self.ga_process:
            return
        text = bytes(self.ga_process.readAllStandardOutput()).decode()
        if not text:
            return
        self.ga_log.appendPlainText(text.rstrip())
        if "Best fitness:" in text:
            try:
                value = float(text.strip().split(":")[-1])
                self._last_ga_fitness = value
            except ValueError:
                pass
        if "Saved params" in text:
            self._reload_saved_params()
        self._update_status_strip()

    def _handle_ga_stderr(self):
        if not self.ga_process:
            return
        text = bytes(self.ga_process.readAllStandardError()).decode()
        if text:
            self.ga_log.appendPlainText(text.rstrip())

    def _handle_ga_finished(self):
        self.ga_log.appendPlainText("--- GA process finished ---")
        self.ga_process = None
        self._reload_saved_params()

    # --- Helpers ---------------------------------------------------------------------
    def _reload_saved_params(self):
        params = load_active_squeeze_params()
        for name, ctrl in self.sqz_controls.items():
            value = params.get(name)
            blocker = QSignalBlocker(ctrl)
            if isinstance(ctrl, QCheckBox):
                ctrl.setChecked(bool(value))
            elif isinstance(ctrl, QSpinBox):
                ctrl.setValue(int(value))
            elif isinstance(ctrl, QDoubleSpinBox):
                ctrl.setValue(float(value))
            del blocker
            self.chart.set_squeeze_param(name, value)
        self._update_status_strip()

    def _load_params_from_chart(self):
        params = self.chart.get_squeeze_params()
        for name, ctrl in self.sqz_controls.items():
            value = params.get(name)
            blocker = QSignalBlocker(ctrl)
            if isinstance(ctrl, QCheckBox):
                ctrl.setChecked(bool(value))
            elif isinstance(ctrl, QSpinBox):
                ctrl.setValue(int(value))
            elif isinstance(ctrl, QDoubleSpinBox):
                ctrl.setValue(float(value))
            del blocker

    def _update_status_strip(self):
        params = self.chart.get_squeeze_params()
        text = (
            f"SQZMOM BB {int(params['length_bb'])}/{float(params['mult_bb']):.2f}  |  "
            f"KC {int(params['length_kc'])}/{float(params['mult_kc']):.2f}  |  "
            f"TrueRange={'ON' if params['use_true_range'] else 'OFF'}"
        )
        if self._last_ga_fitness is not None:
            text += f"  |  Last GA fitness {self._last_ga_fitness:.4f}"
        self.status_strip.setText(text)
