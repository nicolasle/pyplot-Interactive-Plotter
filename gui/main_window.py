"""
Main Window for Pyplot Interactive Plotter
Integrates the persistent live plot canvas on the right with the
multi-tab configuration panels on the left.
Handles signal routing, click-to-inspect subplot interaction, and live redraws.
"""

import os
from typing import Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QTabWidget, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt

from core.models import FigureConfig, Dataset, TraceConfig
from core.data_loader import sniff_file_parameters, parse_file
from gui.plot_canvas import PlotCanvas
from gui.tabs.data_tab import DataTab
from gui.tabs.plot_tab import PlotTab
from gui.tabs.configurator_tab import ConfiguratorTab
from gui.tabs.template_tab import TemplateTab
from gui.tabs.export_tab import ExportTab
from gui.styles import DARK_THEME


class MainWindow(QMainWindow):
    """
    Primary Application Window.
    Maintains FigureConfig and loaded Datasets state.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pyplot Interactive Plotter - Scientific Publication Suite")
        self.resize(1380, 840)

        # Apply modern dark styling
        self.setStyleSheet(DARK_THEME)

        # Core State
        self.fig_config = FigureConfig(
            nrows=1, ncols=1,
            width_cm=14.0, height_cm=10.0,
            dpi=120,
            style="seaborn-v0_8-ticks"
        )
        self.datasets: Dict[str, Dataset] = {}

        # Build UI & Canvas
        self._setup_ui()
        self._connect_signals()

        # Load initial sample data for immediate interactive exploration
        self._load_sample_data()

        # Initial live render
        self.render_live_figure()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # Persistent Splitter: Left Controls | Right Live Preview Canvas
        self.splitter = QSplitter(Qt.Horizontal)

        # -------------------------------------------------------------
        # Left Panel: Multi-Tab Controls
        # -------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(540)

        # 1. Data Manager Tab
        self.data_tab = DataTab(self.datasets, parent=self)
        self.tabs.addTab(self.data_tab, "1. Data Manager")

        # 2. Plot Manager Tab
        self.plot_tab = PlotTab(self.fig_config, parent=self)
        self.tabs.addTab(self.plot_tab, "2. Plot Manager")

        # 3. Subplot Configurator Tab
        self.config_tab = ConfiguratorTab(self.fig_config, self.datasets, parent=self)
        self.tabs.addTab(self.config_tab, "3. Plot Configurator")

        # 4. Template & Batch Mode Tab
        self.template_tab = TemplateTab(self.fig_config, self.datasets, parent=self)
        self.tabs.addTab(self.template_tab, "4. Templates & Batch")

        # 5. Code & Export Hub Tab
        self.export_tab = ExportTab(self.fig_config, self.datasets, parent=self)
        self.tabs.addTab(self.export_tab, "5. Code & Export")

        self.splitter.addWidget(self.tabs)

        # -------------------------------------------------------------
        # Right Panel: Persistent Live Matplotlib Plot Canvas
        # -------------------------------------------------------------
        self.plot_canvas = PlotCanvas(parent=self)
        self.plot_canvas.setMinimumWidth(550)
        self.splitter.addWidget(self.plot_canvas)

        # Proportions: 45% left controls, 55% live plot canvas
        self.splitter.setSizes([580, 800])
        main_layout.addWidget(self.splitter)

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready. Select or click any subplot to configure channels.")

    def _connect_signals(self):
        # 1. Data modified & Column renamed
        self.data_tab.data_changed.connect(self._on_data_modified)
        self.data_tab.column_renamed.connect(self._on_column_renamed)

        # 2. Plot layout / styling changed
        self.plot_tab.config_changed.connect(self._on_plot_config_modified)

        # 3. Channel / Trace / Axes changed
        self.config_tab.config_changed.connect(self._on_trace_or_axis_modified)

        # 4. Template applied or session loaded
        self.template_tab.template_applied.connect(self._on_external_config_loaded)
        self.export_tab.session_loaded.connect(self._on_external_config_loaded)

        # 5. Tab switch: auto refresh code if moving to Export tab
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # 6. Click-to-Inspect: click subplot on live canvas -> select in Configurator tab!
        self.plot_canvas.axis_selected.connect(self._on_canvas_axis_clicked)

    def _on_canvas_axis_clicked(self, r: int, c: int):
        """User clicked an axis on the live canvas."""
        self.config_tab.select_subplot(r, c)
        self.tabs.setCurrentWidget(self.config_tab)
        self.statusBar.showMessage(f"Selected Subplot ({r}, {c}) in Configurator.", 3000)

    def _on_tab_changed(self, index: int):
        # If switching to Code & Export tab (index 4), refresh code
        if index == 4:
            self.export_tab.refresh_code()

    def _on_column_renamed(self, dataset_id: str, old_name: str, new_name: str):
        """Update any trace in FigureConfig that used old_name to use new_name."""
        self.fig_config.rename_column_in_traces(dataset_id, old_name, new_name)
        self.config_tab.load_active_subplot()
        self.render_live_figure()
        self.export_tab.refresh_code()
        self.statusBar.showMessage(f"Renamed column '{old_name}' -> '{new_name}' across all plots.", 4000)

    def _on_data_modified(self):
        self.config_tab.refresh_subplot_selector()
        self.render_live_figure()
        self.export_tab.refresh_code()

    def _on_plot_config_modified(self):
        self.config_tab.refresh_subplot_selector()
        self.render_live_figure()
        self.export_tab.refresh_code()

    def _on_trace_or_axis_modified(self):
        self.render_live_figure()
        self.export_tab.refresh_code()

    def _on_external_config_loaded(self):
        self.plot_tab.update_from_model()
        self.config_tab.refresh_subplot_selector()
        self.render_live_figure()
        self.export_tab.refresh_code()

    def render_live_figure(self):
        """Triggers live re-rendering on the embedded plot canvas."""
        try:
            self.plot_canvas.render(self.fig_config, self.datasets)
        except Exception as e:
            self.statusBar.showMessage(f"Render warning: {e}", 5000)

    def _load_sample_data(self):
        """Pre-loads sample files if present so user has immediate data to explore."""
        sample_files = [
            "sample_data/spectrum_with_comments.txt",
            "sample_data/messy_whitespace_no_header.dat",
            "sample_data/surface_map_2d.txt"
        ]

        for s_file in sample_files:
            if os.path.exists(s_file):
                base = os.path.splitext(os.path.basename(s_file))[0]
                sniff = sniff_file_parameters(s_file)
                df, mat, err = parse_file(s_file, sniff)
                if not err:
                    d_type = "2d_matrix" if "2d" in base else "1d_table"
                    ds = Dataset(name=base, data_type=d_type, df=df, matrix=mat, filepath=s_file, meta=sniff)
                    self.datasets[ds.id] = ds

        # Refresh dataset tab
        self.data_tab.refresh_dataset_list()

        # Configure default trace on subplot (0, 0)
        spec_ds = next((d for d in self.datasets.values() if "spectrum" in d.name), None)
        if spec_ds and spec_ds.df is not None and len(spec_ds.df.columns) >= 2:
            ax0 = self.fig_config.get_axis(0, 0)
            ax0.title = "Optical Emission Spectrum"
            ax0.xlabel = "Wavelength $\\lambda$ (nm)"
            ax0.ylabel = "Intensity (a.u.)"
            ax0.grid_major = True
            
            tr = TraceConfig(
                name="Scan 1",
                dataset_id=spec_ds.id,
                plot_type="line+scatter",
                x_col=spec_ds.df.columns[0],
                y_col=spec_ds.df.columns[1],
                yerr_col=spec_ds.df.columns[2] if len(spec_ds.df.columns) > 2 else None,
                color="#3b82f6",
                marker="o",
                markersize=5.0,
                linewidth=1.8,
                label="Sample A"
            )
            ax0.traces.append(tr)
            self.config_tab.refresh_subplot_selector()
