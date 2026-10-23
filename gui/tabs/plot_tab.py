"""
Plot Manager Tab
Configures figure-level layout (nrows, ncols, sharex, sharey),
physical dimensions (cm / inches, DPI), publication presets (Nature, APS, IEEE),
and global typography / style sheets.
"""

from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QGroupBox, QLineEdit,
    QGridLayout, QScrollArea, QPushButton
)
from PySide6.QtCore import Signal

from core.models import FigureConfig
from core.presets import PUBLICATION_PRESETS


class PlotTab(QWidget):
    """
    Plot Manager tab:
    - Grid layout (rows x cols, sharex, sharey)
    - Publication presets
    - Figure dimensions (width, height cm, DPI)
    - Theme & typography
    """
    config_changed = Signal()

    def __init__(self, fig_config: FigureConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.fig_config = fig_config
        self._block_signals = False

        self._setup_ui()
        self.update_from_model()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # 1. Publication Presets Group
        preset_box = QGroupBox("One-Click Publication & Layout Presets")
        preset_layout = QVBoxLayout(preset_box)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom", "Custom")
        for preset_name in PUBLICATION_PRESETS.keys():
            self.preset_combo.addItem(preset_name, preset_name)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        self.preset_desc = QLabel("Select a preset or customize parameters below.")
        self.preset_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.preset_desc.setWordWrap(True)
        preset_layout.addWidget(self.preset_desc)
        layout.addWidget(preset_box)

        # 2. Grid & Subplot Layout Group
        grid_box = QGroupBox("Subplot Grid Layout")
        grid_layout = QGridLayout(grid_box)
        grid_layout.setSpacing(8)

        grid_layout.addWidget(QLabel("Rows (N):"), 0, 0)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 8)
        self.rows_spin.valueChanged.connect(self._on_ui_changed)
        grid_layout.addWidget(self.rows_spin, 0, 1)

        grid_layout.addWidget(QLabel("Cols (M):"), 0, 2)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 8)
        self.cols_spin.valueChanged.connect(self._on_ui_changed)
        grid_layout.addWidget(self.cols_spin, 0, 3)

        grid_layout.addWidget(QLabel("Share X:"), 1, 0)
        self.sharex_combo = QComboBox()
        self.sharex_combo.addItems(["none", "all", "row", "col"])
        self.sharex_combo.currentIndexChanged.connect(self._on_ui_changed)
        grid_layout.addWidget(self.sharex_combo, 1, 1)

        grid_layout.addWidget(QLabel("Share Y:"), 1, 2)
        self.sharey_combo = QComboBox()
        self.sharey_combo.addItems(["none", "all", "row", "col"])
        self.sharey_combo.currentIndexChanged.connect(self._on_ui_changed)
        grid_layout.addWidget(self.sharey_combo, 1, 3)

        layout.addWidget(grid_box)

        # 3. Physical Dimensions & Output Group
        dim_box = QGroupBox("Physical Figure Dimensions")
        dim_layout = QGridLayout(dim_box)
        dim_layout.setSpacing(8)

        dim_layout.addWidget(QLabel("Width (cm):"), 0, 0)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(3.0, 60.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.valueChanged.connect(self._on_ui_changed)
        dim_layout.addWidget(self.width_spin, 0, 1)

        dim_layout.addWidget(QLabel("Height (cm):"), 0, 2)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(3.0, 60.0)
        self.height_spin.setSingleStep(0.5)
        self.height_spin.valueChanged.connect(self._on_ui_changed)
        dim_layout.addWidget(self.height_spin, 0, 3)

        dim_layout.addWidget(QLabel("DPI (Resolution):"), 1, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.valueChanged.connect(self._on_ui_changed)
        dim_layout.addWidget(self.dpi_spin, 1, 1)

        self.tight_layout_cb = QCheckBox("Tight Layout (auto padding)")
        self.tight_layout_cb.stateChanged.connect(self._on_ui_changed)
        dim_layout.addWidget(self.tight_layout_cb, 1, 2, 1, 2)

        layout.addWidget(dim_box)

        # 4. Global Style & Typography Group
        style_box = QGroupBox("Global Styling & Typography")
        style_layout = QGridLayout(style_box)
        style_layout.setSpacing(8)

        style_layout.addWidget(QLabel("Style Sheet:"), 0, 0)
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "default",
            "seaborn-v0_8-ticks",
            "seaborn-v0_8-whitegrid",
            "classic",
            "ggplot",
            "tableau-colorblind10"
        ])
        self.style_combo.currentIndexChanged.connect(self._on_ui_changed)
        style_layout.addWidget(self.style_combo, 0, 1)

        style_layout.addWidget(QLabel("Font Family:"), 0, 2)
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["sans-serif", "serif", "monospace"])
        self.font_family_combo.currentIndexChanged.connect(self._on_ui_changed)
        style_layout.addWidget(self.font_family_combo, 0, 3)

        style_layout.addWidget(QLabel("Base Font Size (pt):"), 1, 0)
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(5.0, 32.0)
        self.font_size_spin.setSingleStep(0.5)
        self.font_size_spin.valueChanged.connect(self._on_ui_changed)
        style_layout.addWidget(self.font_size_spin, 1, 1)

        self.usetex_cb = QCheckBox("LaTeX Rendering (usetex)")
        self.usetex_cb.stateChanged.connect(self._on_ui_changed)
        style_layout.addWidget(self.usetex_cb, 1, 2, 1, 2)

        style_layout.addWidget(QLabel("Figure Super-Title:"), 2, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Optional overall title...")
        self.title_edit.textChanged.connect(self._on_ui_changed)
        style_layout.addWidget(self.title_edit, 2, 1, 1, 3)

        layout.addWidget(style_box)

        # 5. Publication Panel Labels Group
        panel_box = QGroupBox("Subplot Panel Labels (a, b, c...)")
        panel_layout = QGridLayout(panel_box)
        panel_layout.setSpacing(8)

        self.btn_enable_all_panels = QPushButton("Enable on All Subplots")
        self.btn_enable_all_panels.setStyleSheet("font-weight: bold; padding: 5px;")
        self.btn_enable_all_panels.clicked.connect(self._on_enable_all_panel_labels)
        panel_layout.addWidget(self.btn_enable_all_panels, 0, 0)

        self.btn_disable_all_panels = QPushButton("Disable All Labels")
        self.btn_disable_all_panels.setStyleSheet("padding: 5px;")
        self.btn_disable_all_panels.clicked.connect(self._on_disable_all_panel_labels)
        panel_layout.addWidget(self.btn_disable_all_panels, 0, 1)

        self.btn_reset_panel_letters = QPushButton("Reset to a, b, c... (Grid Order)")
        self.btn_reset_panel_letters.setStyleSheet("padding: 5px;")
        self.btn_reset_panel_letters.clicked.connect(self._on_reset_panel_letters)
        panel_layout.addWidget(self.btn_reset_panel_letters, 1, 0)

        self.batch_square_cb = QCheckBox("Black Square on All")
        self.batch_square_cb.setChecked(True)
        self.batch_square_cb.stateChanged.connect(self._on_batch_square_toggled)
        panel_layout.addWidget(self.batch_square_cb, 1, 1)

        layout.addWidget(panel_box)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_from_model(self):
        """Reflect figure config values in UI."""
        self._block_signals = True
        c = self.fig_config

        self.rows_spin.setValue(c.nrows)
        self.cols_spin.setValue(c.ncols)
        
        idx = self.sharex_combo.findText(c.sharex)
        if idx >= 0:
            self.sharex_combo.setCurrentIndex(idx)
            
        idx = self.sharey_combo.findText(c.sharey)
        if idx >= 0:
            self.sharey_combo.setCurrentIndex(idx)

        self.width_spin.setValue(c.width_cm)
        self.height_spin.setValue(c.height_cm)
        self.dpi_spin.setValue(c.dpi)
        self.tight_layout_cb.setChecked(c.tight_layout)

        idx = self.style_combo.findText(c.style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        idx = self.font_family_combo.findText(c.font_family)
        if idx >= 0:
            self.font_family_combo.setCurrentIndex(idx)

        self.font_size_spin.setValue(c.font_size)
        self.usetex_cb.setChecked(c.usetex)
        self.title_edit.setText(c.figure_title)

        idx = self.preset_combo.findText(c.preset_name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

        self._block_signals = False

    def _on_preset_selected(self, index: int):
        if self._block_signals:
            return
        preset_name = self.preset_combo.itemText(index)
        if preset_name in PUBLICATION_PRESETS:
            p = PUBLICATION_PRESETS[preset_name]
            self._block_signals = True

            self.width_spin.setValue(p["width_cm"])
            self.height_spin.setValue(p["height_cm"])
            self.dpi_spin.setValue(p["dpi"])
            self.font_size_spin.setValue(p["font_size"])
            
            idx = self.font_family_combo.findText(p.get("font_family", "sans-serif"))
            if idx >= 0:
                self.font_family_combo.setCurrentIndex(idx)

            idx = self.style_combo.findText(p.get("style", "default"))
            if idx >= 0:
                self.style_combo.setCurrentIndex(idx)

            self.preset_desc.setText(p.get("description", ""))
            self.fig_config.preset_name = preset_name
            self._block_signals = False
            self._on_ui_changed()
        else:
            self.fig_config.preset_name = "Custom"
            self.preset_desc.setText("Custom layout settings.")

    def _on_ui_changed(self):
        if self._block_signals:
            return

        c = self.fig_config
        c.nrows = self.rows_spin.value()
        c.ncols = self.cols_spin.value()
        c.ensure_axes_grid()

        c.sharex = self.sharex_combo.currentText()
        c.sharey = self.sharey_combo.currentText()
        c.width_cm = self.width_spin.value()
        c.height_cm = self.height_spin.value()
        c.dpi = self.dpi_spin.value()
        c.tight_layout = self.tight_layout_cb.isChecked()

        c.style = self.style_combo.currentText()
        c.font_family = self.font_family_combo.currentText()
        c.font_size = self.font_size_spin.value()
        c.usetex = self.usetex_cb.isChecked()
        c.figure_title = self.title_edit.text()

        self.config_changed.emit()

    def _on_enable_all_panel_labels(self):
        self.fig_config.set_all_panel_labels_visible(True)
        self.config_changed.emit()

    def _on_disable_all_panel_labels(self):
        self.fig_config.set_all_panel_labels_visible(False)
        self.config_changed.emit()

    def _on_reset_panel_letters(self):
        self.fig_config.reset_default_panel_labels()
        self.config_changed.emit()

    def _on_batch_square_toggled(self, state: int):
        self.fig_config.set_all_panel_labels_square(self.batch_square_cb.isChecked())
        self.config_changed.emit()
