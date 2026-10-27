"""
Main Window for Pyplot Interactive Plotter
Integrates the persistent live plot canvas on the right with the
multi-tab configuration panels on the left.
Handles signal routing, click-to-inspect subplot interaction, and live redraws.
"""

import os
from typing import Dict, Tuple, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QStatusBar, QMessageBox, QFileDialog, QToolBar,
    QLabel, QSizePolicy, QApplication, QLineEdit, QAbstractSpinBox
)
from PySide6.QtCore import Qt, QLocale, QObject, QEvent
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent

from core.models import FigureConfig, Dataset, TraceConfig
from core.data_loader import sniff_file_parameters, parse_file
from core.project_manager import (
    save_project_to_file, load_project_from_file, PROJECT_FILE_FILTER
)
from gui.plot_canvas import PlotCanvas
from gui.tabs.data_tab import DataTab
from gui.tabs.plot_tab import PlotTab
from gui.tabs.configurator_tab import ConfiguratorTab
from gui.tabs.template_tab import TemplateTab
from gui.tabs.export_tab import ExportTab
from gui.styles import DARK_THEME


class NumericInputFilter(QObject):
    """
    Translates comma key presses into periods for numeric spin boxes and
    limit fields, ensuring seamless input on European/French keyboard layouts.
    """
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.text() == ",":
            if isinstance(obj, QLineEdit):
                parent = obj.parent()
                if isinstance(parent, QAbstractSpinBox) or obj.objectName() == "numeric_lim_edit":
                    new_event = QKeyEvent(
                        event.type(),
                        Qt.Key.Key_Period,
                        event.modifiers(),
                        "."
                    )
                    QApplication.sendEvent(obj, new_event)
                    return True
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    """
    Primary Application Window.
    Maintains FigureConfig and loaded Datasets state.
    """
    def __init__(self):
        super().__init__()
        # Force C locale globally so numbers always format with decimal point (.)
        QLocale.setDefault(QLocale.c())
        self.setLocale(QLocale.c())

        app_inst = QApplication.instance()
        if app_inst and not getattr(app_inst, "_decimal_filter_installed", False):
            self._decimal_filter = NumericInputFilter(app_inst)
            app_inst.installEventFilter(self._decimal_filter)
            app_inst._decimal_filter_installed = True

        self.setWindowTitle("Pyplot Interactive Plotter - Scientific Publication Suite")
        self.resize(1380, 840)

        # Apply modern dark styling
        self.setStyleSheet(DARK_THEME)

        # Core State
        self.fig_config = FigureConfig(
            nrows=1, ncols=1,
            width_cm=14.0, height_cm=10.0,
            dpi=120,
            style="default"
        )
        self.datasets: Dict[str, Dataset] = {}
        self.current_project_path: Optional[str] = None

        # Build UI & Canvas
        self._setup_ui()
        self._setup_menu_and_toolbar()
        self._connect_signals()

        # Load initial sample data for immediate interactive exploration
        self._load_sample_data()

        # Update initial window title
        self._update_window_title()

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
            ax0.grid_major = False
            
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

    def _setup_menu_and_toolbar(self):
        """Constructs top application menu bar and quick project toolbar."""
        # 1. Menu Bar
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        self.new_act = QAction("➕ &New Project", self)
        self.new_act.setShortcut(QKeySequence.New)
        self.new_act.setStatusTip("Create a new blank project workspace")
        self.new_act.triggered.connect(self.new_project)
        file_menu.addAction(self.new_act)

        self.open_act = QAction("📂 &Open Project State...", self)
        self.open_act.setShortcut(QKeySequence.Open)
        self.open_act.setStatusTip("Open a saved project state (.plotproj / .json)")
        self.open_act.triggered.connect(self.open_project_state)
        file_menu.addAction(self.open_act)

        self.save_act = QAction("💾 &Save Project State", self)
        self.save_act.setShortcut(QKeySequence.Save)
        self.save_act.setStatusTip("Save current workspace state with all datasets and plots")
        self.save_act.triggered.connect(lambda: self.save_project_state(save_as=False))
        file_menu.addAction(self.save_act)

        self.save_as_act = QAction("💾 Save Project State &As...", self)
        self.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_as_act.setStatusTip("Save project state under a new filename")
        self.save_as_act.triggered.connect(lambda: self.save_project_state(save_as=True))
        file_menu.addAction(self.save_as_act)

        file_menu.addSeparator()

        self.export_fig_act = QAction("🖼️ &Export Figure Image...", self)
        self.export_fig_act.setShortcut(QKeySequence("Ctrl+E"))
        self.export_fig_act.setStatusTip("Export current publication figure (PDF, PNG, SVG, EPS)")
        self.export_fig_act.triggered.connect(self._quick_export_figure)
        file_menu.addAction(self.export_fig_act)

        self.export_py_act = QAction("🐍 Export &Python Script...", self)
        self.export_py_act.setStatusTip("Export standalone reproducible Matplotlib Python script")
        self.export_py_act.triggered.connect(self._export_python_script)
        file_menu.addAction(self.export_py_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.setStatusTip("Exit application")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # 2. Project ToolBar
        toolbar = QToolBar("Project Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        toolbar.addAction(self.new_act)
        toolbar.addAction(self.open_act)
        toolbar.addAction(self.save_act)
        toolbar.addAction(self.save_as_act)

        toolbar.addSeparator()

        self.project_status_label = QLabel(" Project: <b>Untitled Workspace</b> ")
        self.project_status_label.setStyleSheet("color: #93c5fd; padding: 2px 8px; font-size: 12px;")
        toolbar.addWidget(self.project_status_label)

        # Spacer to push quick actions right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        redraw_act = QAction("🔄 Redraw Canvas", self)
        redraw_act.setStatusTip("Force live redraw of Matplotlib canvas")
        redraw_act.triggered.connect(self.render_live_figure)
        toolbar.addAction(redraw_act)

        toolbar.addAction(self.export_fig_act)

    def _update_window_title(self):
        """Updates window title and status bar/toolbar with active project filename."""
        proj_name = os.path.basename(self.current_project_path) if self.current_project_path else "Untitled Workspace"
        self.setWindowTitle(f"Pyplot Interactive Plotter - [{proj_name}]")
        if hasattr(self, "project_status_label"):
            self.project_status_label.setText(f" Project: <b>{proj_name}</b> ")

    def new_project(self) -> bool:
        """Resets the workspace to an empty project after confirmation."""
        reply = QMessageBox.question(
            self,
            "New Project Workspace",
            "Start a new project? Any unsaved changes in the current workspace will be discarded.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False

        new_fig = FigureConfig(
            nrows=1, ncols=1,
            width_cm=14.0, height_cm=10.0,
            dpi=120,
            style="default"
        )
        new_datasets: Dict[str, Dataset] = {}
        self.current_project_path = None
        self._apply_loaded_project(new_fig, new_datasets, active_coord=(0, 0))
        self._update_window_title()
        self.statusBar.showMessage("New project workspace created.", 4000)
        return True

    def save_project_state(self, save_as: bool = False) -> bool:
        """
        Saves the entire project workspace state (.plotproj / .json):
        All imported datasets (with full DataFrames and matrices), figure configuration,
        channels, styles, reference lines, panel labels, and layout.
        """
        target_path = self.current_project_path
        if target_path is None or save_as:
            default_name = target_path or os.path.join(os.getcwd(), "project.plotproj")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Project State",
                default_name,
                PROJECT_FILE_FILTER
            )
            if not file_path:
                return False
            if not (file_path.endswith(".plotproj") or file_path.endswith(".json")):
                file_path += ".plotproj"
            target_path = file_path

        try:
            active_coord = getattr(self.config_tab, "current_coord", (0, 0))
            save_project_to_file(target_path, self.fig_config, self.datasets, active_coord=active_coord)
            self.current_project_path = target_path
            self._update_window_title()
            self.statusBar.showMessage(f"Project state saved successfully to: {os.path.basename(target_path)}", 5000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Project Error", f"Failed to save project state:\n{e}")
            return False

    def open_project_state(self) -> bool:
        """
        Prompts user to select a project file (.plotproj / .json) and restores the complete state.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project State",
            self.current_project_path or "",
            PROJECT_FILE_FILTER
        )
        if not file_path:
            return False

        try:
            fig_config, datasets, active_coord = load_project_from_file(file_path)
            self._apply_loaded_project(fig_config, datasets, active_coord)
            self.current_project_path = file_path
            self._update_window_title()
            self.statusBar.showMessage(f"Project loaded successfully: {os.path.basename(file_path)}", 5000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Open Project Error", f"Failed to load project state:\n{e}")
            return False

    def _apply_loaded_project(
        self,
        new_fig: FigureConfig,
        new_datasets: Dict[str, Dataset],
        active_coord: Tuple[int, int] = (0, 0)
    ):
        """Replaces active workspace state and updates all tabs and canvas."""
        self.fig_config = new_fig
        self.datasets.clear()
        self.datasets.update(new_datasets)

        # 1. Synchronize Data Tab
        self.data_tab.datasets = self.datasets
        self.data_tab.active_dataset_id = None
        self.data_tab.refresh_dataset_list()

        # 2. Synchronize Plot Layout Tab
        self.plot_tab.fig_config = self.fig_config
        self.plot_tab.update_from_model()

        # 3. Synchronize Subplot Configurator Tab
        self.config_tab.fig_config = self.fig_config
        self.config_tab.datasets = self.datasets
        self.config_tab.refresh_subplot_selector()
        if active_coord in self.fig_config.axes:
            self.config_tab.select_subplot(active_coord[0], active_coord[1])
        else:
            self.config_tab.select_subplot(0, 0)

        # 4. Synchronize Template & Export Tabs
        self.template_tab.fig_config = self.fig_config
        self.template_tab.datasets = self.datasets

        self.export_tab.fig_config = self.fig_config
        self.export_tab.datasets = self.datasets
        self.export_tab.refresh_code()

        # 5. Live Canvas Redraw
        self.render_live_figure()

    def _quick_export_figure(self):
        """Triggers figure export dialog from ExportTab."""
        self.export_tab._export_figure_image()

    def _export_python_script(self):
        """Triggers python script export dialog from ExportTab."""
        self.export_tab._save_python_script()
