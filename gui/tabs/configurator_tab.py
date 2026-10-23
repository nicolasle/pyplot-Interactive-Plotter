"""
Single Plot Configurator Tab
Selects subplots (via dropdown or live canvas click-to-inspect),
adds, customizes, and deletes 1D/2D channels,
provides a full editor to add and remove reference lines/baselines,
and configures axes labels, limits, scales, grids, and legends.
"""

from typing import Dict, Optional, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QColorDialog,
    QSplitter, QTabWidget, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor

from core.models import FigureConfig, AxisConfig, TraceConfig, ReferenceLineConfig, Dataset


class ConfiguratorTab(QWidget):
    """
    Subplot & Channel Configurator:
    - Select active subplot ax(r, c)
    - Add/remove/customize traces (1D/2D)
    - Add/remove/customize reference lines and baselines
    - Configure axes labels, scales, limits, grid, ticks, and legend
    """
    config_changed = Signal()

    def __init__(
        self,
        fig_config: FigureConfig,
        datasets: Dict[str, Dataset],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.fig_config = fig_config
        self.datasets = datasets
        self.current_coord = (0, 0)
        self.active_trace_id: Optional[str] = None
        self.active_ref_id: Optional[str] = None
        self._block_signals = False

        self._setup_ui()
        self.refresh_subplot_selector()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Top Bar: Subplot Selector
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Target Subplot:</b>"))
        self.subplot_combo = QComboBox()
        self.subplot_combo.currentIndexChanged.connect(self._on_subplot_combo_changed)
        top_bar.addWidget(self.subplot_combo)

        top_bar.addStretch()
        canvas_hint = QLabel("(Tip: Click any subplot on the live plot to select it)")
        canvas_hint.setStyleSheet("color: #60a5fa; font-size: 11px;")
        top_bar.addWidget(canvas_hint)
        main_layout.addLayout(top_bar)

        # Tabs for Selected Subplot: [Data Channels], [Reference Lines & Baselines], [Axes & Scales]
        self.sub_tabs = QTabWidget()

        # -------------------------------------------------------------
        # TAB 1: Channels & Traces Manager
        # -------------------------------------------------------------
        traces_widget = QWidget()
        traces_layout = QVBoxLayout(traces_widget)
        traces_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Vertical)

        # Trace List & Action Buttons
        list_box = QGroupBox("Channels in Subplot")
        list_layout = QVBoxLayout(list_box)

        action_row = QHBoxLayout()
        add_1d_btn = QPushButton("+ 1D Trace")
        add_1d_btn.setObjectName("primaryBtn")
        add_1d_btn.clicked.connect(self._add_1d_trace)

        add_2d_btn = QPushButton("+ 2D Map (Imshow)")
        add_2d_btn.clicked.connect(self._add_2d_trace)

        del_trace_btn = QPushButton("Delete Selected")
        del_trace_btn.setStyleSheet("color: #f87171;")
        del_trace_btn.clicked.connect(self._delete_active_trace)

        action_row.addWidget(add_1d_btn)
        action_row.addWidget(add_2d_btn)
        action_row.addWidget(del_trace_btn)
        action_row.addStretch()
        list_layout.addLayout(action_row)

        self.traces_list = QListWidget()
        self.traces_list.currentRowChanged.connect(self._on_trace_selection_changed)
        list_layout.addWidget(self.traces_list)
        splitter.addWidget(list_box)

        # Trace Property Editor (Scrollable)
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        self.editor_container = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_container)
        self.editor_layout.setContentsMargins(6, 6, 6, 6)
        self.editor_layout.setSpacing(6)

        self._build_trace_editor()

        editor_scroll.setWidget(self.editor_container)
        splitter.addWidget(editor_scroll)
        splitter.setSizes([140, 300])

        traces_layout.addWidget(splitter)
        self.sub_tabs.addTab(traces_widget, "Data Channels")

        # -------------------------------------------------------------
        # TAB 2: Reference Lines & Baselines (Solves "baseline cannot be removed")
        # -------------------------------------------------------------
        ref_widget = QWidget()
        ref_layout = QVBoxLayout(ref_widget)
        ref_layout.setContentsMargins(4, 4, 4, 4)

        ref_splitter = QSplitter(Qt.Vertical)

        ref_list_box = QGroupBox("Reference Lines & Baselines")
        ref_list_layout = QVBoxLayout(ref_list_box)

        ref_btn_row = QHBoxLayout()
        add_hline_btn = QPushButton("+ Horizontal Baseline (y)")
        add_hline_btn.setObjectName("primaryBtn")
        add_hline_btn.clicked.connect(lambda: self._add_ref_line("hline"))

        add_vline_btn = QPushButton("+ Vertical Line (x)")
        add_vline_btn.clicked.connect(lambda: self._add_ref_line("vline"))

        add_span_btn = QPushButton("+ Shaded Span")
        add_span_btn.clicked.connect(lambda: self._add_ref_line("hspan"))

        del_ref_btn = QPushButton("Delete Selected Baseline")
        del_ref_btn.setStyleSheet("color: #f87171; font-weight: bold;")
        del_ref_btn.clicked.connect(self._delete_active_ref_line)

        ref_btn_row.addWidget(add_hline_btn)
        ref_btn_row.addWidget(add_vline_btn)
        ref_btn_row.addWidget(add_span_btn)
        ref_btn_row.addWidget(del_ref_btn)
        ref_btn_row.addStretch()
        ref_list_layout.addLayout(ref_btn_row)

        self.ref_list = QListWidget()
        self.ref_list.currentRowChanged.connect(self._on_ref_selection_changed)
        ref_list_layout.addWidget(self.ref_list)
        ref_splitter.addWidget(ref_list_box)

        # Ref Line Editor
        ref_editor_box = QGroupBox("Baseline / Reference Line Properties")
        ref_edit_layout = QGridLayout(ref_editor_box)
        ref_edit_layout.setSpacing(8)

        ref_edit_layout.addWidget(QLabel("Type:"), 0, 0)
        self.ref_type_combo = QComboBox()
        self.ref_type_combo.addItems(["hline", "vline", "hspan", "vspan"])
        self.ref_type_combo.currentIndexChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_type_combo, 0, 1)

        self.ref_val1_label = QLabel("Value (y / x):")
        ref_edit_layout.addWidget(self.ref_val1_label, 0, 2)
        self.ref_val1_spin = QDoubleSpinBox()
        self.ref_val1_spin.setRange(-1e9, 1e9)
        self.ref_val1_spin.setValue(0.0)
        self.ref_val1_spin.valueChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_val1_spin, 0, 3)

        self.ref_val2_label = QLabel("Span End (for spans):")
        ref_edit_layout.addWidget(self.ref_val2_label, 1, 0)
        self.ref_val2_spin = QDoubleSpinBox()
        self.ref_val2_spin.setRange(-1e9, 1e9)
        self.ref_val2_spin.setValue(1.0)
        self.ref_val2_spin.valueChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_val2_spin, 1, 1)

        ref_edit_layout.addWidget(QLabel("Linestyle:"), 1, 2)
        self.ref_style_combo = QComboBox()
        self.ref_style_combo.addItems(["--", "-", ":", "-."])
        self.ref_style_combo.currentIndexChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_style_combo, 1, 3)

        ref_edit_layout.addWidget(QLabel("Color:"), 2, 0)
        ref_color_row = QHBoxLayout()
        self.ref_color_edit = QLineEdit("#ef4444")
        self.ref_color_edit.textChanged.connect(self._on_ref_prop_changed)
        ref_color_btn = QPushButton("Pick...")
        ref_color_btn.clicked.connect(self._open_ref_color_picker)
        ref_color_row.addWidget(self.ref_color_edit)
        ref_color_row.addWidget(ref_color_btn)
        ref_edit_layout.addLayout(ref_color_row, 2, 1)

        ref_edit_layout.addWidget(QLabel("Linewidth:"), 2, 2)
        self.ref_lw_spin = QDoubleSpinBox()
        self.ref_lw_spin.setRange(0.2, 10.0)
        self.ref_lw_spin.setValue(1.2)
        self.ref_lw_spin.valueChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_lw_spin, 2, 3)

        ref_edit_layout.addWidget(QLabel("Alpha (opacity):"), 3, 0)
        self.ref_alpha_spin = QDoubleSpinBox()
        self.ref_alpha_spin.setRange(0.05, 1.0)
        self.ref_alpha_spin.setSingleStep(0.1)
        self.ref_alpha_spin.setValue(0.8)
        self.ref_alpha_spin.valueChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_alpha_spin, 3, 1)

        ref_edit_layout.addWidget(QLabel("Label:"), 3, 2)
        self.ref_label_edit = QLineEdit()
        self.ref_label_edit.setPlaceholderText("Optional legend label...")
        self.ref_label_edit.textChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_label_edit, 3, 3)

        self.ref_visible_cb = QCheckBox("Visible")
        self.ref_visible_cb.setChecked(True)
        self.ref_visible_cb.stateChanged.connect(self._on_ref_prop_changed)
        ref_edit_layout.addWidget(self.ref_visible_cb, 4, 0)

        ref_splitter.addWidget(ref_editor_box)
        ref_splitter.setSizes([180, 260])
        ref_layout.addWidget(ref_splitter)

        self.sub_tabs.addTab(ref_widget, "Baselines & Ref Lines")

        # -------------------------------------------------------------
        # TAB 3: Axes, Limits, Scales & Legend
        # -------------------------------------------------------------
        axes_scroll = QScrollArea()
        axes_scroll.setWidgetResizable(True)
        axes_container = QWidget()
        axes_layout = QVBoxLayout(axes_container)
        axes_layout.setSpacing(10)

        # Titles & Labels
        labels_box = QGroupBox("Labels (Supports LaTeX $...$)")
        labels_layout = QGridLayout(labels_box)
        labels_layout.addWidget(QLabel("Subplot Title:"), 0, 0)
        self.ax_title_edit = QLineEdit()
        self.ax_title_edit.textChanged.connect(self._on_axes_prop_changed)
        labels_layout.addWidget(self.ax_title_edit, 0, 1, 1, 3)

        labels_layout.addWidget(QLabel("X-Axis Label:"), 1, 0)
        self.ax_xlabel_edit = QLineEdit()
        self.ax_xlabel_edit.textChanged.connect(self._on_axes_prop_changed)
        labels_layout.addWidget(self.ax_xlabel_edit, 1, 1)

        labels_layout.addWidget(QLabel("Y-Axis Label:"), 1, 2)
        self.ax_ylabel_edit = QLineEdit()
        self.ax_ylabel_edit.textChanged.connect(self._on_axes_prop_changed)
        labels_layout.addWidget(self.ax_ylabel_edit, 1, 3)

        labels_layout.addWidget(QLabel("Twin-Y Label:"), 2, 0)
        self.ax_y2label_edit = QLineEdit()
        self.ax_y2label_edit.textChanged.connect(self._on_axes_prop_changed)
        labels_layout.addWidget(self.ax_y2label_edit, 2, 1)
        axes_layout.addWidget(labels_box)

        # Scales & Limits
        scale_box = QGroupBox("Scales & Limits")
        scale_layout = QGridLayout(scale_box)

        scale_layout.addWidget(QLabel("X-Scale:"), 0, 0)
        self.ax_xscale_combo = QComboBox()
        self.ax_xscale_combo.addItems(["linear", "log", "symlog"])
        self.ax_xscale_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_xscale_combo, 0, 1)

        scale_layout.addWidget(QLabel("Y-Scale:"), 0, 2)
        self.ax_yscale_combo = QComboBox()
        self.ax_yscale_combo.addItems(["linear", "log", "symlog"])
        self.ax_yscale_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_yscale_combo, 0, 3)

        scale_layout.addWidget(QLabel("Twin-Y Scale:"), 1, 0)
        self.ax_y2scale_combo = QComboBox()
        self.ax_y2scale_combo.addItems(["linear", "log", "symlog"])
        self.ax_y2scale_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_y2scale_combo, 1, 1)

        scale_layout.addWidget(QLabel("X-Min:"), 2, 0)
        self.ax_xmin_edit = QLineEdit()
        self.ax_xmin_edit.setPlaceholderText("Auto")
        self.ax_xmin_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_xmin_edit, 2, 1)

        scale_layout.addWidget(QLabel("X-Max:"), 2, 2)
        self.ax_xmax_edit = QLineEdit()
        self.ax_xmax_edit.setPlaceholderText("Auto")
        self.ax_xmax_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_xmax_edit, 2, 3)

        scale_layout.addWidget(QLabel("Y-Min:"), 3, 0)
        self.ax_ymin_edit = QLineEdit()
        self.ax_ymin_edit.setPlaceholderText("Auto")
        self.ax_ymin_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_ymin_edit, 3, 1)

        scale_layout.addWidget(QLabel("Y-Max:"), 3, 2)
        self.ax_ymax_edit = QLineEdit()
        self.ax_ymax_edit.setPlaceholderText("Auto")
        self.ax_ymax_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_ymax_edit, 3, 3)

        scale_layout.addWidget(QLabel("Twin-Y Min:"), 4, 0)
        self.ax_y2min_edit = QLineEdit()
        self.ax_y2min_edit.setPlaceholderText("Auto")
        self.ax_y2min_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_y2min_edit, 4, 1)

        scale_layout.addWidget(QLabel("Twin-Y Max:"), 4, 2)
        self.ax_y2max_edit = QLineEdit()
        self.ax_y2max_edit.setPlaceholderText("Auto")
        self.ax_y2max_edit.textChanged.connect(self._on_axes_prop_changed)
        scale_layout.addWidget(self.ax_y2max_edit, 4, 3)
        axes_layout.addWidget(scale_box)

        # Grids & Ticks
        grid_box = QGroupBox("Grids & Ticks")
        grid_layout = QGridLayout(grid_box)

        self.ax_grid_major_cb = QCheckBox("Major Grid")
        self.ax_grid_major_cb.stateChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_grid_major_cb, 0, 0)

        self.ax_grid_minor_cb = QCheckBox("Minor Grid")
        self.ax_grid_minor_cb.stateChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_grid_minor_cb, 0, 1)

        grid_layout.addWidget(QLabel("Grid Style:"), 0, 2)
        self.ax_grid_style_combo = QComboBox()
        self.ax_grid_style_combo.addItems(["--", ":", "-", "-."])
        self.ax_grid_style_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_grid_style_combo, 0, 3)

        grid_layout.addWidget(QLabel("Grid Opacity:"), 1, 0)
        self.ax_grid_alpha_spin = QDoubleSpinBox()
        self.ax_grid_alpha_spin.setRange(0.05, 1.0)
        self.ax_grid_alpha_spin.setSingleStep(0.05)
        self.ax_grid_alpha_spin.setValue(0.4)
        self.ax_grid_alpha_spin.valueChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_grid_alpha_spin, 1, 1)

        grid_layout.addWidget(QLabel("Tick Direction:"), 1, 2)
        self.ax_tick_dir_combo = QComboBox()
        self.ax_tick_dir_combo.addItems(["in", "out", "inout"])
        self.ax_tick_dir_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_tick_dir_combo, 1, 3)

        # X-Ticks Position & Visibility
        grid_layout.addWidget(QLabel("X-Ticks:"), 2, 0)
        self.ax_xtick_pos_combo = QComboBox()
        self.ax_xtick_pos_combo.addItem("Bottom (Default)", "bottom")
        self.ax_xtick_pos_combo.addItem("Top", "top")
        self.ax_xtick_pos_combo.addItem("Both (Top & Bottom)", "both")
        self.ax_xtick_pos_combo.addItem("Hide X Ticks (None)", "none")
        self.ax_xtick_pos_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_xtick_pos_combo, 2, 1)

        self.ax_show_xticklabels_cb = QCheckBox("Show X Values/Numbers")
        self.ax_show_xticklabels_cb.setChecked(True)
        self.ax_show_xticklabels_cb.stateChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_show_xticklabels_cb, 2, 2, 1, 2)

        # Y-Ticks Position & Visibility
        grid_layout.addWidget(QLabel("Y-Ticks:"), 3, 0)
        self.ax_ytick_pos_combo = QComboBox()
        self.ax_ytick_pos_combo.addItem("Left (Default)", "left")
        self.ax_ytick_pos_combo.addItem("Right", "right")
        self.ax_ytick_pos_combo.addItem("Both (Left & Right)", "both")
        self.ax_ytick_pos_combo.addItem("Hide Y Ticks (None)", "none")
        self.ax_ytick_pos_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_ytick_pos_combo, 3, 1)

        self.ax_show_yticklabels_cb = QCheckBox("Show Y Values/Numbers")
        self.ax_show_yticklabels_cb.setChecked(True)
        self.ax_show_yticklabels_cb.stateChanged.connect(self._on_axes_prop_changed)
        grid_layout.addWidget(self.ax_show_yticklabels_cb, 3, 2, 1, 2)

        axes_layout.addWidget(grid_box)

        # Legend Controls
        legend_box = QGroupBox("Legend")
        legend_layout = QGridLayout(legend_box)

        self.ax_show_legend_cb = QCheckBox("Show Legend")
        self.ax_show_legend_cb.stateChanged.connect(self._on_axes_prop_changed)
        legend_layout.addWidget(self.ax_show_legend_cb, 0, 0)

        self.ax_legend_frame_cb = QCheckBox("Legend Frame")
        self.ax_legend_frame_cb.stateChanged.connect(self._on_axes_prop_changed)
        legend_layout.addWidget(self.ax_legend_frame_cb, 0, 1)

        legend_layout.addWidget(QLabel("Location:"), 1, 0)
        self.ax_legend_loc_combo = QComboBox()
        self.ax_legend_loc_combo.addItems([
            "best", "upper right", "upper left", "lower left", "lower right",
            "center left", "center right", "lower center", "upper center", "center"
        ])
        self.ax_legend_loc_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        legend_layout.addWidget(self.ax_legend_loc_combo, 1, 1)

        legend_layout.addWidget(QLabel("Columns:"), 1, 2)
        self.ax_legend_ncol_spin = QSpinBox()
        self.ax_legend_ncol_spin.setRange(1, 6)
        self.ax_legend_ncol_spin.setValue(1)
        self.ax_legend_ncol_spin.valueChanged.connect(self._on_axes_prop_changed)
        legend_layout.addWidget(self.ax_legend_ncol_spin, 1, 3)
        axes_layout.addWidget(legend_box)

        # Panel Label (Publication Tag, e.g. a, b, c...)
        panel_box = QGroupBox("Panel Label (Publication Tag)")
        panel_layout = QGridLayout(panel_box)
        panel_layout.setSpacing(8)

        self.ax_show_panel_label_cb = QCheckBox("Show Panel Label")
        self.ax_show_panel_label_cb.stateChanged.connect(self._on_axes_prop_changed)
        panel_layout.addWidget(self.ax_show_panel_label_cb, 0, 0)

        panel_layout.addWidget(QLabel("Label Text:"), 0, 1)
        self.ax_panel_label_edit = QLineEdit()
        self.ax_panel_label_edit.setPlaceholderText("e.g. a, b, c...")
        self.ax_panel_label_edit.textChanged.connect(self._on_axes_prop_changed)
        panel_layout.addWidget(self.ax_panel_label_edit, 0, 2, 1, 3)

        panel_layout.addWidget(QLabel("Corner:"), 1, 0)
        self.ax_panel_label_pos_combo = QComboBox()
        self.ax_panel_label_pos_combo.addItem("Top-Left", "top-left")
        self.ax_panel_label_pos_combo.addItem("Top-Right", "top-right")
        self.ax_panel_label_pos_combo.addItem("Bottom-Left", "bottom-left")
        self.ax_panel_label_pos_combo.addItem("Bottom-Right", "bottom-right")
        self.ax_panel_label_pos_combo.currentIndexChanged.connect(self._on_axes_prop_changed)
        panel_layout.addWidget(self.ax_panel_label_pos_combo, 1, 1)

        self.ax_panel_label_square_cb = QCheckBox("Black square (white text)")
        self.ax_panel_label_square_cb.setChecked(True)
        self.ax_panel_label_square_cb.setToolTip("Checked: black square in corner with white letter.\nUnchecked: font in plain black without square.")
        self.ax_panel_label_square_cb.stateChanged.connect(self._on_axes_prop_changed)
        panel_layout.addWidget(self.ax_panel_label_square_cb, 1, 2, 1, 3)

        panel_layout.addWidget(QLabel("Font Size (pt):"), 2, 0)
        self.ax_panel_label_size_spin = QDoubleSpinBox()
        self.ax_panel_label_size_spin.setRange(5.0, 36.0)
        self.ax_panel_label_size_spin.setSingleStep(0.5)
        self.ax_panel_label_size_spin.setValue(11.0)
        self.ax_panel_label_size_spin.valueChanged.connect(self._on_panel_font_size_changed)
        panel_layout.addWidget(self.ax_panel_label_size_spin, 2, 1)

        panel_layout.addWidget(QLabel("Square Side (pt):"), 2, 2)
        self.ax_panel_label_box_spin = QDoubleSpinBox()
        self.ax_panel_label_box_spin.setRange(5.0, 72.0)
        self.ax_panel_label_box_spin.setSingleStep(0.5)
        self.ax_panel_label_box_spin.setValue(14.3)
        self.ax_panel_label_box_spin.setToolTip("Exact square side length in points. By default, 130% of font size.")
        self.ax_panel_label_box_spin.valueChanged.connect(self._on_axes_prop_changed)
        panel_layout.addWidget(self.ax_panel_label_box_spin, 2, 3)

        self.btn_apply_panel_sizes_all = QPushButton("Apply to All")
        self.btn_apply_panel_sizes_all.setToolTip("Apply current Font Size and Square Size to all subplots in the figure.")
        self.btn_apply_panel_sizes_all.setStyleSheet("padding: 3px 8px; font-weight: bold;")
        self.btn_apply_panel_sizes_all.clicked.connect(self._on_apply_panel_sizes_all)
        panel_layout.addWidget(self.btn_apply_panel_sizes_all, 2, 4)

        axes_layout.addWidget(panel_box)

        axes_layout.addStretch()
        axes_scroll.setWidget(axes_container)
        self.sub_tabs.addTab(axes_scroll, "Axes & Scales")

        main_layout.addWidget(self.sub_tabs)

    def _build_trace_editor(self):
        """Constructs widgets for editing the active trace."""
        grid = QGridLayout()
        grid.setSpacing(6)

        # Visible checkbox
        self.tr_visible_cb = QCheckBox("Visible on Plot")
        self.tr_visible_cb.setChecked(True)
        self.tr_visible_cb.stateChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_visible_cb, 0, 0, 1, 2)

        # Dataset
        grid.addWidget(QLabel("Dataset:"), 1, 0)
        self.tr_dataset_combo = QComboBox()
        self.tr_dataset_combo.currentIndexChanged.connect(self._on_trace_dataset_changed)
        grid.addWidget(self.tr_dataset_combo, 1, 1, 1, 3)

        # Plot type & Axis target
        grid.addWidget(QLabel("Plot Type:"), 2, 0)
        self.tr_type_combo = QComboBox()
        self.tr_type_combo.addItems([
            "line", "scatter", "line+scatter", "errorbar", "bar", "step", "fill_between",
            "imshow", "contour", "contourf"
        ])
        self.tr_type_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_type_combo, 2, 1)

        grid.addWidget(QLabel("Axis Target:"), 2, 2)
        self.tr_axis_combo = QComboBox()
        self.tr_axis_combo.addItems(["primary", "twinx"])
        self.tr_axis_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_axis_combo, 2, 3)

        # X and Y Column mapping
        grid.addWidget(QLabel("X Channel:"), 3, 0)
        self.tr_xcol_combo = QComboBox()
        self.tr_xcol_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_xcol_combo, 3, 1)

        grid.addWidget(QLabel("Y Channel:"), 3, 2)
        self.tr_ycol_combo = QComboBox()
        self.tr_ycol_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_ycol_combo, 3, 3)

        # Error bars
        grid.addWidget(QLabel("Y-Error:"), 4, 0)
        self.tr_yerr_combo = QComboBox()
        self.tr_yerr_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_yerr_combo, 4, 1)

        grid.addWidget(QLabel("X-Error:"), 4, 2)
        self.tr_xerr_combo = QComboBox()
        self.tr_xerr_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_xerr_combo, 4, 3)

        # Legend Label
        grid.addWidget(QLabel("Legend Label:"), 5, 0)
        self.tr_label_edit = QLineEdit()
        self.tr_label_edit.textChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_label_edit, 5, 1, 1, 3)

        # Color & Linestyle
        grid.addWidget(QLabel("Color:"), 6, 0)
        color_row = QHBoxLayout()
        self.tr_color_edit = QLineEdit("auto")
        self.tr_color_edit.textChanged.connect(self._on_trace_prop_changed)
        color_picker_btn = QPushButton("Pick...")
        color_picker_btn.clicked.connect(self._open_color_picker)
        color_row.addWidget(self.tr_color_edit)
        color_row.addWidget(color_picker_btn)
        grid.addLayout(color_row, 6, 1)

        grid.addWidget(QLabel("Linestyle:"), 6, 2)
        self.tr_linestyle_combo = QComboBox()
        self.tr_linestyle_combo.addItems(["-", "--", "-.", ":", "None"])
        self.tr_linestyle_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_linestyle_combo, 6, 3)

        # Linewidth & Alpha
        grid.addWidget(QLabel("Linewidth:"), 7, 0)
        self.tr_linewidth_spin = QDoubleSpinBox()
        self.tr_linewidth_spin.setRange(0.2, 10.0)
        self.tr_linewidth_spin.setSingleStep(0.5)
        self.tr_linewidth_spin.setValue(1.5)
        self.tr_linewidth_spin.valueChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_linewidth_spin, 7, 1)

        grid.addWidget(QLabel("Alpha (opacity):"), 7, 2)
        self.tr_alpha_spin = QDoubleSpinBox()
        self.tr_alpha_spin.setRange(0.05, 1.0)
        self.tr_alpha_spin.setSingleStep(0.05)
        self.tr_alpha_spin.setValue(1.0)
        self.tr_alpha_spin.valueChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_alpha_spin, 7, 3)

        # Marker & Size
        grid.addWidget(QLabel("Marker:"), 8, 0)
        self.tr_marker_combo = QComboBox()
        self.tr_marker_combo.addItems(["None", "o", "s", "^", "v", "D", "x", "+", "*", "p"])
        self.tr_marker_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_marker_combo, 8, 1)

        grid.addWidget(QLabel("Marker Size:"), 8, 2)
        self.tr_markersize_spin = QDoubleSpinBox()
        self.tr_markersize_spin.setRange(1.0, 30.0)
        self.tr_markersize_spin.setValue(6.0)
        self.tr_markersize_spin.valueChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_markersize_spin, 8, 3)

        # 2D Map specific controls
        grid.addWidget(QLabel("Colormap (2D):"), 9, 0)
        self.tr_cmap_combo = QComboBox()
        self.tr_cmap_combo.addItems([
            "viridis", "plasma", "inferno", "magma", "cividis",
            "coolwarm", "bwr", "RdBu_r", "Spectral_r", "jet", "turbo"
        ])
        self.tr_cmap_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_cmap_combo, 9, 1)

        self.tr_cbar_cb = QCheckBox("Show Colorbar")
        self.tr_cbar_cb.setChecked(True)
        self.tr_cbar_cb.stateChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_cbar_cb, 9, 2)

        grid.addWidget(QLabel("Interpolation:"), 10, 0)
        self.tr_interp_combo = QComboBox()
        self.tr_interp_combo.addItems(["nearest", "bilinear", "bicubic", "none"])
        self.tr_interp_combo.currentIndexChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_interp_combo, 10, 1)

        grid.addWidget(QLabel("Contour Levels:"), 10, 2)
        self.tr_levels_spin = QSpinBox()
        self.tr_levels_spin.setRange(2, 100)
        self.tr_levels_spin.setValue(10)
        self.tr_levels_spin.valueChanged.connect(self._on_trace_prop_changed)
        grid.addWidget(self.tr_levels_spin, 10, 3)

        self.editor_layout.addLayout(grid)
        self.editor_layout.addStretch()

    def refresh_subplot_selector(self):
        """Populates the dropdown with available (r, c) subplots."""
        self._block_signals = True
        self.subplot_combo.clear()
        for r in range(self.fig_config.nrows):
            for c in range(self.fig_config.ncols):
                self.subplot_combo.addItem(f"Subplot ({r}, {c})", (r, c))

        # Find matching index by explicit tuple/text comparison
        target_tuple = self.current_coord
        target_text = f"Subplot ({target_tuple[0]}, {target_tuple[1]})"
        found_idx = 0
        for i in range(self.subplot_combo.count()):
            if self.subplot_combo.itemData(i) == target_tuple or self.subplot_combo.itemText(i) == target_text:
                found_idx = i
                break
        self.subplot_combo.setCurrentIndex(found_idx)

        self._block_signals = False
        self.load_active_subplot()

    def select_subplot(self, r: int, c: int):
        """Called externally (e.g. from canvas click) to switch subplot."""
        self.current_coord = (r, c)
        target_tuple = (r, c)
        target_text = f"Subplot ({r}, {c})"

        found_idx = -1
        for i in range(self.subplot_combo.count()):
            if self.subplot_combo.itemData(i) == target_tuple or self.subplot_combo.itemText(i) == target_text:
                found_idx = i
                break

        self._block_signals = True
        if found_idx >= 0:
            self.subplot_combo.setCurrentIndex(found_idx)
        self._block_signals = False
        self.load_active_subplot()

    def _on_subplot_combo_changed(self):
        if self._block_signals:
            return
        coord = self.subplot_combo.currentData()
        if coord:
            self.current_coord = coord
            self.load_active_subplot()

    def load_active_subplot(self):
        """Populates UI with settings of the currently selected subplot."""
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        self._block_signals = True

        # Axes & Scales
        self.ax_title_edit.setText(ax_cfg.title)
        self.ax_xlabel_edit.setText(ax_cfg.xlabel)
        self.ax_ylabel_edit.setText(ax_cfg.ylabel)
        self.ax_y2label_edit.setText(ax_cfg.y2label)

        idx = self.ax_xscale_combo.findText(ax_cfg.xscale)
        if idx >= 0:
            self.ax_xscale_combo.setCurrentIndex(idx)

        idx = self.ax_yscale_combo.findText(ax_cfg.yscale)
        if idx >= 0:
            self.ax_yscale_combo.setCurrentIndex(idx)

        idx = self.ax_y2scale_combo.findText(ax_cfg.y2scale)
        if idx >= 0:
            self.ax_y2scale_combo.setCurrentIndex(idx)

        self.ax_xmin_edit.setText(str(ax_cfg.xlim_min) if ax_cfg.xlim_min is not None else "")
        self.ax_xmax_edit.setText(str(ax_cfg.xlim_max) if ax_cfg.xlim_max is not None else "")
        self.ax_ymin_edit.setText(str(ax_cfg.ylim_min) if ax_cfg.ylim_min is not None else "")
        self.ax_ymax_edit.setText(str(ax_cfg.ylim_max) if ax_cfg.ylim_max is not None else "")
        self.ax_y2min_edit.setText(str(ax_cfg.y2lim_min) if ax_cfg.y2lim_min is not None else "")
        self.ax_y2max_edit.setText(str(ax_cfg.y2lim_max) if ax_cfg.y2lim_max is not None else "")

        self.ax_grid_major_cb.setChecked(ax_cfg.grid_major)
        self.ax_grid_minor_cb.setChecked(ax_cfg.grid_minor)

        idx = self.ax_grid_style_combo.findText(ax_cfg.grid_style)
        if idx >= 0:
            self.ax_grid_style_combo.setCurrentIndex(idx)

        self.ax_grid_alpha_spin.setValue(ax_cfg.grid_alpha)

        idx = self.ax_tick_dir_combo.findText(ax_cfg.tick_direction)
        if idx >= 0:
            self.ax_tick_dir_combo.setCurrentIndex(idx)

        # X-Ticks
        x_pos = getattr(ax_cfg, "xtick_position", "bottom")
        for i in range(self.ax_xtick_pos_combo.count()):
            if self.ax_xtick_pos_combo.itemData(i) == x_pos:
                self.ax_xtick_pos_combo.setCurrentIndex(i)
                break
        self.ax_show_xticklabels_cb.setChecked(getattr(ax_cfg, "show_xticklabels", True))

        # Y-Ticks
        y_pos = getattr(ax_cfg, "ytick_position", "left")
        for i in range(self.ax_ytick_pos_combo.count()):
            if self.ax_ytick_pos_combo.itemData(i) == y_pos:
                self.ax_ytick_pos_combo.setCurrentIndex(i)
                break
        self.ax_show_yticklabels_cb.setChecked(getattr(ax_cfg, "show_yticklabels", True))

        self.ax_show_legend_cb.setChecked(ax_cfg.show_legend)
        self.ax_legend_frame_cb.setChecked(ax_cfg.legend_frame)

        idx = self.ax_legend_loc_combo.findText(ax_cfg.legend_loc)
        if idx >= 0:
            self.ax_legend_loc_combo.setCurrentIndex(idx)

        self.ax_legend_ncol_spin.setValue(ax_cfg.legend_ncol)

        # Panel Label
        self.ax_show_panel_label_cb.setChecked(getattr(ax_cfg, "show_panel_label", False))
        r, c = self.current_coord
        idx = r * self.fig_config.ncols + c
        default_lbl = chr(ord('a') + idx) if idx < 26 else f"p{idx+1}"
        self.ax_panel_label_edit.setText(ax_cfg.panel_label if ax_cfg.panel_label else default_lbl)

        loc = getattr(ax_cfg, "panel_label_loc", "top-left")
        for i in range(self.ax_panel_label_pos_combo.count()):
            if self.ax_panel_label_pos_combo.itemData(i) == loc:
                self.ax_panel_label_pos_combo.setCurrentIndex(i)
                break

        self.ax_panel_label_square_cb.setChecked(getattr(ax_cfg, "panel_label_square", True))

        lbl_size = ax_cfg.panel_label_size if ax_cfg.panel_label_size is not None else (self.fig_config.font_size + 1)
        self.ax_panel_label_size_spin.setValue(lbl_size)

        box_size = ax_cfg.panel_label_box_size if ax_cfg.panel_label_box_size is not None else round(lbl_size * 1.30, 1)
        self.ax_panel_label_box_spin.setValue(box_size)

        # Traces List
        self._refresh_traces_list()

        # Reference Lines List
        self._refresh_ref_list()

        self._block_signals = False

    def _refresh_traces_list(self):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        self.traces_list.clear()

        for idx, tr in enumerate(ax_cfg.traces):
            d = self.datasets.get(tr.dataset_id)
            d_name = d.name if d else "No Data"
            label = tr.label or tr.name or f"Trace {idx+1}"
            vis_badge = "[ON]" if tr.visible else "[OFF]"
            axis_badge = "[TwinX]" if tr.twin_axis == "twinx" else "[Primary]"
            item = QListWidgetItem(f"{vis_badge} {axis_badge} ({tr.plot_type}) {label} [{d_name}]")
            item.setData(Qt.UserRole, tr.id)
            self.traces_list.addItem(item)

        if self.traces_list.count() > 0:
            self.traces_list.setCurrentRow(0)
        else:
            self.active_trace_id = None
            self._clear_trace_editor()

    def _refresh_ref_list(self):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        self.ref_list.clear()

        for idx, ref in enumerate(ax_cfg.ref_lines):
            type_badge = ref.type.upper()
            lbl = ref.label or "Ref Line"
            if ref.type in ["hline", "vline"]:
                text = f"[{type_badge}] {lbl} @ {ref.val1:.4g}"
            else:
                text = f"[{type_badge}] {lbl} ({ref.val1:.4g} to {ref.val2:.4g})"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ref.id)
            self.ref_list.addItem(item)

        if self.ref_list.count() > 0:
            self.ref_list.setCurrentRow(0)
        else:
            self.active_ref_id = None

    def _clear_trace_editor(self):
        self._block_signals = True
        self.tr_label_edit.clear()
        self.tr_color_edit.setText("auto")
        self.tr_dataset_combo.clear()
        self.tr_xcol_combo.clear()
        self.tr_ycol_combo.clear()
        self._block_signals = False

    def _on_trace_selection_changed(self, row: int):
        if row < 0:
            return
        item = self.traces_list.item(row)
        if not item:
            return
        tr_id = item.data(Qt.UserRole)
        self.active_trace_id = tr_id
        self._load_trace_into_editor(tr_id)

    def _load_trace_into_editor(self, tr_id: str):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        tr = next((t for t in ax_cfg.traces if t.id == tr_id), None)
        if not tr:
            return

        self._block_signals = True

        self.tr_visible_cb.setChecked(tr.visible)

        # Populate datasets combo
        self.tr_dataset_combo.clear()
        for d_id, ds in self.datasets.items():
            self.tr_dataset_combo.addItem(ds.name, d_id)

        idx = self.tr_dataset_combo.findData(tr.dataset_id)
        if idx >= 0:
            self.tr_dataset_combo.setCurrentIndex(idx)

        # Plot type
        idx = self.tr_type_combo.findText(tr.plot_type)
        if idx >= 0:
            self.tr_type_combo.setCurrentIndex(idx)

        # Axis target
        idx = self.tr_axis_combo.findText(tr.twin_axis)
        if idx >= 0:
            self.tr_axis_combo.setCurrentIndex(idx)

        # Populate columns
        self._populate_column_combos(tr.dataset_id)

        # Set selected columns
        idx = self.tr_xcol_combo.findData(tr.x_col)
        if idx >= 0:
            self.tr_xcol_combo.setCurrentIndex(idx)

        idx = self.tr_ycol_combo.findData(tr.y_col)
        if idx >= 0:
            self.tr_ycol_combo.setCurrentIndex(idx)

        idx = self.tr_yerr_combo.findData(tr.yerr_col)
        if idx >= 0:
            self.tr_yerr_combo.setCurrentIndex(idx)

        idx = self.tr_xerr_combo.findData(tr.xerr_col)
        if idx >= 0:
            self.tr_xerr_combo.setCurrentIndex(idx)

        # Styling
        self.tr_label_edit.setText(tr.label)
        self.tr_color_edit.setText(tr.color)

        idx = self.tr_linestyle_combo.findText(tr.linestyle)
        if idx >= 0:
            self.tr_linestyle_combo.setCurrentIndex(idx)

        self.tr_linewidth_spin.setValue(tr.linewidth)
        self.tr_alpha_spin.setValue(tr.alpha)

        idx = self.tr_marker_combo.findText(tr.marker)
        if idx >= 0:
            self.tr_marker_combo.setCurrentIndex(idx)

        self.tr_markersize_spin.setValue(tr.markersize)

        idx = self.tr_cmap_combo.findText(tr.cmap)
        if idx >= 0:
            self.tr_cmap_combo.setCurrentIndex(idx)

        self.tr_cbar_cb.setChecked(tr.colorbar)

        idx = self.tr_interp_combo.findText(tr.interpolation)
        if idx >= 0:
            self.tr_interp_combo.setCurrentIndex(idx)

        self.tr_levels_spin.setValue(tr.contour_levels)

        self._block_signals = False

    def _populate_column_combos(self, dataset_id: str):
        ds = self.datasets.get(dataset_id)
        cols = ds.get_columns() if ds else []

        self.tr_xcol_combo.clear()
        self.tr_ycol_combo.clear()
        self.tr_yerr_combo.clear()
        self.tr_xerr_combo.clear()

        self.tr_xcol_combo.addItem("Index (0, 1, 2...)", "")
        self.tr_yerr_combo.addItem("None", "")
        self.tr_xerr_combo.addItem("None", "")

        for c in cols:
            self.tr_xcol_combo.addItem(c, c)
            self.tr_ycol_combo.addItem(c, c)
            self.tr_yerr_combo.addItem(c, c)
            self.tr_xerr_combo.addItem(c, c)

    def _on_trace_dataset_changed(self):
        if self._block_signals:
            return
        self._block_signals = True
        d_id = self.tr_dataset_combo.currentData()
        self._populate_column_combos(d_id)
        self._block_signals = False
        self._on_trace_prop_changed()

    def _open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.tr_color_edit.setText(color.name())
            self._on_trace_prop_changed()

    def _on_trace_prop_changed(self):
        if self._block_signals or not self.active_trace_id:
            return

        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        tr = next((t for t in ax_cfg.traces if t.id == self.active_trace_id), None)
        if not tr:
            return

        tr.visible = self.tr_visible_cb.isChecked()
        tr.dataset_id = self.tr_dataset_combo.currentData() or ""
        tr.plot_type = self.tr_type_combo.currentText()
        tr.twin_axis = self.tr_axis_combo.currentText()

        tr.x_col = self.tr_xcol_combo.currentData() or None
        tr.y_col = self.tr_ycol_combo.currentData() or None
        tr.yerr_col = self.tr_yerr_combo.currentData() or None
        tr.xerr_col = self.tr_xerr_combo.currentData() or None

        tr.label = self.tr_label_edit.text()
        tr.color = self.tr_color_edit.text().strip() or "auto"
        tr.linestyle = self.tr_linestyle_combo.currentText()
        tr.linewidth = self.tr_linewidth_spin.value()
        tr.alpha = self.tr_alpha_spin.value()

        tr.marker = self.tr_marker_combo.currentText()
        tr.markersize = self.tr_markersize_spin.value()
        tr.cmap = self.tr_cmap_combo.currentText()
        tr.colorbar = self.tr_cbar_cb.isChecked()
        tr.interpolation = self.tr_interp_combo.currentText()
        tr.contour_levels = self.tr_levels_spin.value()

        # Update trace list item label
        curr_row = self.traces_list.currentRow()
        if curr_row >= 0:
            d = self.datasets.get(tr.dataset_id)
            d_name = d.name if d else "No Data"
            label = tr.label or tr.name or f"Trace {curr_row+1}"
            vis_badge = "[ON]" if tr.visible else "[OFF]"
            axis_badge = "[TwinX]" if tr.twin_axis == "twinx" else "[Primary]"
            self.traces_list.item(curr_row).setText(f"{vis_badge} {axis_badge} ({tr.plot_type}) {label} [{d_name}]")

        self.config_changed.emit()

    # --- Reference Lines Management ---
    def _add_ref_line(self, line_type: str = "hline"):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ref = ReferenceLineConfig(
            type=line_type,
            val1=0.0,
            val2=1.0,
            color="#ef4444",
            linestyle="--",
            label="Baseline" if line_type == "hline" else "Threshold"
        )
        ax_cfg.ref_lines.append(ref)
        self._refresh_ref_list()
        self.ref_list.setCurrentRow(len(ax_cfg.ref_lines) - 1)
        self.config_changed.emit()

    def _delete_active_ref_line(self):
        if not self.active_ref_id:
            return
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ax_cfg.ref_lines = [r for r in ax_cfg.ref_lines if r.id != self.active_ref_id]
        self._refresh_ref_list()
        self.config_changed.emit()

    def _on_ref_selection_changed(self, row: int):
        if row < 0:
            return
        item = self.ref_list.item(row)
        if not item:
            return
        ref_id = item.data(Qt.UserRole)
        self.active_ref_id = ref_id
        self._load_ref_into_editor(ref_id)

    def _load_ref_into_editor(self, ref_id: str):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ref = next((r for r in ax_cfg.ref_lines if r.id == ref_id), None)
        if not ref:
            return

        self._block_signals = True
        idx = self.ref_type_combo.findText(ref.type)
        if idx >= 0:
            self.ref_type_combo.setCurrentIndex(idx)

        self.ref_val1_spin.setValue(ref.val1)
        self.ref_val2_spin.setValue(ref.val2)

        idx = self.ref_style_combo.findText(ref.linestyle)
        if idx >= 0:
            self.ref_style_combo.setCurrentIndex(idx)

        self.ref_color_edit.setText(ref.color)
        self.ref_lw_spin.setValue(ref.linewidth)
        self.ref_alpha_spin.setValue(ref.alpha)
        self.ref_label_edit.setText(ref.label)
        self.ref_visible_cb.setChecked(getattr(ref, "visible", True))
        self._block_signals = False

    def _open_ref_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.ref_color_edit.setText(color.name())
            self._on_ref_prop_changed()

    def _on_ref_prop_changed(self):
        if self._block_signals or not self.active_ref_id:
            return

        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ref = next((r for r in ax_cfg.ref_lines if r.id == self.active_ref_id), None)
        if not ref:
            return

        ref.type = self.ref_type_combo.currentText()
        ref.val1 = self.ref_val1_spin.value()
        ref.val2 = self.ref_val2_spin.value()
        ref.linestyle = self.ref_style_combo.currentText()
        ref.color = self.ref_color_edit.text().strip() or "#ef4444"
        ref.linewidth = self.ref_lw_spin.value()
        ref.alpha = self.ref_alpha_spin.value()
        ref.label = self.ref_label_edit.text()
        ref.visible = self.ref_visible_cb.isChecked()

        # Update item in list
        curr_row = self.ref_list.currentRow()
        if curr_row >= 0:
            type_badge = ref.type.upper()
            lbl = ref.label or "Ref Line"
            if ref.type in ["hline", "vline"]:
                text = f"[{type_badge}] {lbl} @ {ref.val1:.4g}"
            else:
                text = f"[{type_badge}] {lbl} ({ref.val1:.4g} to {ref.val2:.4g})"
            self.ref_list.item(curr_row).setText(text)

        self.config_changed.emit()

    def _on_panel_font_size_changed(self, val: float):
        if not self._block_signals:
            self.ax_panel_label_box_spin.blockSignals(True)
            self.ax_panel_label_box_spin.setValue(round(val * 1.30, 1))
            self.ax_panel_label_box_spin.blockSignals(False)
        self._on_axes_prop_changed()

    def _on_axes_prop_changed(self):
        if self._block_signals:
            return

        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ax_cfg.title = self.ax_title_edit.text()
        ax_cfg.xlabel = self.ax_xlabel_edit.text()
        ax_cfg.ylabel = self.ax_ylabel_edit.text()
        ax_cfg.y2label = self.ax_y2label_edit.text()

        ax_cfg.xscale = self.ax_xscale_combo.currentText()
        ax_cfg.yscale = self.ax_yscale_combo.currentText()
        ax_cfg.y2scale = self.ax_y2scale_combo.currentText()

        def parse_lim(text: str) -> Optional[float]:
            text = text.strip()
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                return None

        ax_cfg.xlim_min = parse_lim(self.ax_xmin_edit.text())
        ax_cfg.xlim_max = parse_lim(self.ax_xmax_edit.text())
        ax_cfg.ylim_min = parse_lim(self.ax_ymin_edit.text())
        ax_cfg.ylim_max = parse_lim(self.ax_ymax_edit.text())
        ax_cfg.y2lim_min = parse_lim(self.ax_y2min_edit.text())
        ax_cfg.y2lim_max = parse_lim(self.ax_y2max_edit.text())

        ax_cfg.grid_major = self.ax_grid_major_cb.isChecked()
        ax_cfg.grid_minor = self.ax_grid_minor_cb.isChecked()
        ax_cfg.grid_style = self.ax_grid_style_combo.currentText()
        ax_cfg.grid_alpha = self.ax_grid_alpha_spin.value()

        ax_cfg.tick_direction = self.ax_tick_dir_combo.currentText()
        ax_cfg.xtick_position = self.ax_xtick_pos_combo.currentData() or "bottom"
        ax_cfg.show_xticklabels = self.ax_show_xticklabels_cb.isChecked()
        ax_cfg.ytick_position = self.ax_ytick_pos_combo.currentData() or "left"
        ax_cfg.show_yticklabels = self.ax_show_yticklabels_cb.isChecked()
        ax_cfg.tick_top = ax_cfg.xtick_position in ("top", "both")
        ax_cfg.tick_right = ax_cfg.ytick_position in ("right", "both")

        ax_cfg.show_legend = self.ax_show_legend_cb.isChecked()
        ax_cfg.legend_frame = self.ax_legend_frame_cb.isChecked()
        ax_cfg.legend_loc = self.ax_legend_loc_combo.currentText()
        ax_cfg.legend_ncol = self.ax_legend_ncol_spin.value()

        # Panel Label
        ax_cfg.show_panel_label = self.ax_show_panel_label_cb.isChecked()
        ax_cfg.panel_label = self.ax_panel_label_edit.text()
        ax_cfg.panel_label_loc = self.ax_panel_label_pos_combo.currentData() or "top-left"
        ax_cfg.panel_label_square = self.ax_panel_label_square_cb.isChecked()
        ax_cfg.panel_label_size = self.ax_panel_label_size_spin.value()
        ax_cfg.panel_label_box_size = self.ax_panel_label_box_spin.value()

        self.config_changed.emit()

    def _on_apply_panel_sizes_all(self):
        """Applies current Font Size, Square Side, and Black Square setting to all subplots."""
        self._on_axes_prop_changed()
        font_sz = self.ax_panel_label_size_spin.value()
        box_sz = self.ax_panel_label_box_spin.value()
        is_sq = self.ax_panel_label_square_cb.isChecked()

        for r in range(self.fig_config.nrows):
            for c in range(self.fig_config.ncols):
                ax = self.fig_config.get_axis(r, c)
                ax.panel_label_size = font_sz
                ax.panel_label_box_size = box_sz
                ax.panel_label_square = is_sq

        self.config_changed.emit()

        orig_text = self.btn_apply_panel_sizes_all.text()
        self.btn_apply_panel_sizes_all.setText("Applied!")
        QTimer.singleShot(1500, lambda: self.btn_apply_panel_sizes_all.setText(orig_text))

    def _add_1d_trace(self):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        first_d_id = list(self.datasets.keys())[0] if self.datasets else ""
        ds = self.datasets.get(first_d_id)
        cols = ds.get_columns() if ds else []

        x_col = cols[0] if len(cols) > 0 else None
        y_col = cols[1] if len(cols) > 1 else (cols[0] if len(cols) > 0 else None)

        new_tr = TraceConfig(
            name=f"Trace {len(ax_cfg.traces)+1}",
            dataset_id=first_d_id,
            plot_type="line",
            x_col=x_col,
            y_col=y_col,
            label=f"Channel {len(ax_cfg.traces)+1}"
        )
        ax_cfg.traces.append(new_tr)
        self._refresh_traces_list()
        self.traces_list.setCurrentRow(len(ax_cfg.traces) - 1)
        self.config_changed.emit()

    def _add_2d_trace(self):
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        first_d_id = list(self.datasets.keys())[0] if self.datasets else ""
        new_tr = TraceConfig(
            name=f"Map {len(ax_cfg.traces)+1}",
            dataset_id=first_d_id,
            plot_type="imshow",
            cmap="viridis",
            colorbar=True,
            label=""
        )
        ax_cfg.traces.append(new_tr)
        self._refresh_traces_list()
        self.traces_list.setCurrentRow(len(ax_cfg.traces) - 1)
        self.config_changed.emit()

    def _delete_active_trace(self):
        if not self.active_trace_id:
            return
        ax_cfg = self.fig_config.get_axis(*self.current_coord)
        ax_cfg.traces = [t for t in ax_cfg.traces if t.id != self.active_trace_id]
        self._refresh_traces_list()
        self.config_changed.emit()
