"""
Interactive Dialogs for Column Differentiation (dy/dx) and Smoothing Filters
"""

import re
from typing import Optional, Dict, Any, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QRadioButton, QButtonGroup, QStackedWidget, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
import numpy as np
import pandas as pd

from core.models import Dataset
from core.data_loader import (
    differentiate_columns,
    apply_gaussian_filter,
    apply_median_filter,
    apply_moving_average,
    apply_savgol_filter
)


class DifferentiateDialog(QDialog):
    """
    Modal dialog allowing the user to compute the numerical derivative
    of one column with respect to another (dy/dx) with live data preview.
    """
    def __init__(
        self,
        dataset: Dataset,
        initial_y: Optional[str] = None,
        initial_x: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.df if dataset.df is not None else pd.DataFrame()
        self.result_data: Optional[np.ndarray] = None
        self.new_col_name: str = ""
        self.formula_expr: str = ""

        self.setWindowTitle("Differentiate Column (dy/dx)")
        self.resize(540, 500)
        self._setup_ui(initial_y, initial_x)
        self._update_preview()

    def _setup_ui(self, initial_y: Optional[str], initial_x: Optional[str]):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header description
        header = QLabel(
            "<b>Numerical Differentiation (dy/dx)</b><br>"
            "<span style='color: #94a3b8; font-size: 11px;'>"
            "Calculates the derivative of column Y with respect to column X using second-order centered differences. "
            "Handles non-uniform X spacing natively."
            "</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Controls Group
        form_group = QGroupBox("Derivative Settings")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(8)

        cols = list(self.df.columns) if not self.df.empty else []

        # Row 1: Y column
        y_row = QHBoxLayout()
        y_row.addWidget(QLabel("<b>Y Column (Numerator):</b>"))
        self.y_combo = QComboBox()
        for c in cols:
            self.y_combo.addItem(str(c), str(c))
        if initial_y and initial_y in cols:
            self.y_combo.setCurrentText(initial_y)
        elif len(cols) > 1:
            self.y_combo.setCurrentIndex(1)
        self.y_combo.currentIndexChanged.connect(self._on_columns_changed)
        y_row.addWidget(self.y_combo, stretch=1)
        form_layout.addLayout(y_row)

        # Row 2: X column
        x_row = QHBoxLayout()
        x_row.addWidget(QLabel("<b>X Column (Denominator):</b>"))
        self.x_combo = QComboBox()
        for c in cols:
            self.x_combo.addItem(str(c), str(c))
        self.x_combo.addItem("(Row Index / dt=1.0)", "__index__")
        if initial_x and initial_x in cols:
            self.x_combo.setCurrentText(initial_x)
        elif len(cols) > 0:
            self.x_combo.setCurrentIndex(0)
        self.x_combo.currentIndexChanged.connect(self._on_columns_changed)
        x_row.addWidget(self.x_combo, stretch=1)
        form_layout.addLayout(x_row)

        # Row 3: Output Column Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("New Column Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. dY_dX")
        name_row.addWidget(self.name_edit, stretch=1)
        form_layout.addLayout(name_row)

        # Row 4: Optional Pre-Smoothing
        smooth_box = QHBoxLayout()
        self.pre_smooth_cb = QCheckBox("Smooth Y before differentiating (reduces noise amplification)")
        self.pre_smooth_cb.setChecked(False)
        self.pre_smooth_cb.stateChanged.connect(self._on_smooth_toggled)
        smooth_box.addWidget(self.pre_smooth_cb)

        self.smooth_sigma_label = QLabel("σ:")
        self.smooth_sigma_spin = QDoubleSpinBox()
        self.smooth_sigma_spin.setRange(0.2, 50.0)
        self.smooth_sigma_spin.setSingleStep(0.5)
        self.smooth_sigma_spin.setValue(1.5)
        self.smooth_sigma_spin.setEnabled(False)
        self.smooth_sigma_spin.valueChanged.connect(self._update_preview)
        smooth_box.addWidget(self.smooth_sigma_label)
        smooth_box.addWidget(self.smooth_sigma_spin)
        smooth_box.addStretch()
        form_layout.addLayout(smooth_box)

        layout.addWidget(form_group)

        # Live Data Preview Table
        preview_group = QGroupBox("Live Calculation Preview (First 8 Rows)")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["Row", "X", "Y", "dy/dx"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.setFixedHeight(150)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Calculate & Add Column")
        apply_btn.setObjectName("accentBtn")
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)

        layout.addLayout(btn_row)

        self._update_default_name()

    def _on_smooth_toggled(self, state: int):
        enabled = (state == Qt.Checked.value if hasattr(Qt.Checked, "value") else bool(state))
        self.smooth_sigma_spin.setEnabled(enabled)
        self._update_preview()

    def _on_columns_changed(self):
        self._update_default_name()
        self._update_preview()

    def _update_default_name(self):
        y_col = self.y_combo.currentText()
        x_data = self.x_combo.currentData()
        x_col = self.x_combo.currentText() if x_data != "__index__" else "index"
        
        # Clean col names for safe identifier
        y_clean = re.sub(r"\W+", "_", y_col).strip("_")
        x_clean = re.sub(r"\W+", "_", x_col).strip("_")
        
        if self.pre_smooth_cb.isChecked():
            default_name = f"d_{y_clean}_smooth_d_{x_clean}"
        else:
            default_name = f"d_{y_clean}_d_{x_clean}"
        self.name_edit.setText(default_name)

    def _compute_derivative(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        if self.df.empty:
            return None, None, None
        y_col = self.y_combo.currentText()
        x_data = self.x_combo.currentData()
        x_col = self.x_combo.currentText()

        if y_col not in self.df.columns:
            return None, None, None

        y_vals = pd.to_numeric(self.df[y_col], errors="coerce").to_numpy()

        if self.pre_smooth_cb.isChecked():
            sigma = self.smooth_sigma_spin.value()
            y_vals = apply_gaussian_filter(y_vals, sigma=sigma)

        if x_data == "__index__":
            x_vals = np.arange(len(y_vals), dtype=float)
            dydx = differentiate_columns(y_vals, None)
        else:
            if x_col not in self.df.columns:
                return None, None, None
            x_vals = pd.to_numeric(self.df[x_col], errors="coerce").to_numpy()
            dydx = differentiate_columns(y_vals, x_vals)

        return x_vals, y_vals, dydx

    def _update_preview(self):
        x_vals, y_vals, dydx = self._compute_derivative()
        if dydx is None or len(dydx) == 0:
            self.preview_table.setRowCount(0)
            return

        nrows = min(8, len(dydx))
        self.preview_table.setRowCount(nrows)
        for r in range(nrows):
            self.preview_table.setItem(r, 0, QTableWidgetItem(str(r)))
            
            x_str = f"{x_vals[r]:.5g}" if np.isfinite(x_vals[r]) else str(x_vals[r])
            self.preview_table.setItem(r, 1, QTableWidgetItem(x_str))
            
            y_str = f"{y_vals[r]:.5g}" if np.isfinite(y_vals[r]) else str(y_vals[r])
            self.preview_table.setItem(r, 2, QTableWidgetItem(y_str))
            
            d_str = f"{dydx[r]:.5g}" if np.isfinite(dydx[r]) else str(dydx[r])
            item = QTableWidgetItem(d_str)
            item.setForeground(Qt.cyan)
            self.preview_table.setItem(r, 3, item)

    def _apply(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid column name.")
            return

        if name in self.df.columns:
            ret = QMessageBox.question(
                self,
                "Column Exists",
                f"Column '{name}' already exists. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return

        x_vals, y_vals, dydx = self._compute_derivative()
        if dydx is None or len(dydx) == 0:
            QMessageBox.critical(self, "Calculation Error", "Failed to compute derivative. Check that columns contain numeric data.")
            return

        self.result_data = dydx
        self.new_col_name = name

        y_col = self.y_combo.currentText()
        x_data = self.x_combo.currentData()
        x_col = self.x_combo.currentText()
        if x_data == "__index__":
            self.formula_expr = f"diff({y_col})"
        else:
            if self.pre_smooth_cb.isChecked():
                self.formula_expr = f"diff(gaussian_filter({y_col}, {self.smooth_sigma_spin.value()}), {x_col})"
            else:
                self.formula_expr = f"diff({y_col}, {x_col})"

        self.accept()


class SmoothingFilterDialog(QDialog):
    """
    Modal dialog allowing the user to apply Gaussian blur, Median filter,
    Moving Average, or Savitzky-Golay smoothing to a column with live preview.
    """
    def __init__(
        self,
        dataset: Dataset,
        initial_col: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.df if dataset.df is not None else pd.DataFrame()
        self.result_data: Optional[np.ndarray] = None
        self.target_col_name: str = ""
        self.replace_inplace: bool = False
        self.formula_expr: str = ""

        self.setWindowTitle("Apply Smoothing Filter")
        self.resize(540, 520)
        self._setup_ui(initial_col)
        self._update_preview()

    def _setup_ui(self, initial_col: Optional[str]):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header description
        header = QLabel(
            "<b>Data Smoothing & Noise Reduction</b><br>"
            "<span style='color: #94a3b8; font-size: 11px;'>"
            "Apply statistical, Gaussian blur, or polynomial smoothing filters to reduce measurement noise."
            "</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Filter Settings Group
        form_group = QGroupBox("Filter Configuration")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(8)

        cols = list(self.df.columns) if not self.df.empty else []

        # Row 1: Target Column
        col_row = QHBoxLayout()
        col_row.addWidget(QLabel("<b>Target Column:</b>"))
        self.col_combo = QComboBox()
        for c in cols:
            self.col_combo.addItem(str(c), str(c))
        if initial_col and initial_col in cols:
            self.col_combo.setCurrentText(initial_col)
        elif len(cols) > 1:
            self.col_combo.setCurrentIndex(1)
        self.col_combo.currentIndexChanged.connect(self._on_target_changed)
        col_row.addWidget(self.col_combo, stretch=1)
        form_layout.addLayout(col_row)

        # Row 2: Filter Type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("<b>Filter Type:</b>"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("Gaussian Blur / Filter (gaussian_filter)", "gaussian")
        self.filter_type_combo.addItem("Median Filter - Spike Removal (median_filter)", "median")
        self.filter_type_combo.addItem("Moving Average - Rolling Mean (moving_average)", "moving_avg")
        self.filter_type_combo.addItem("Savitzky-Golay Polynomial Filter (savgol_filter)", "savgol")
        self.filter_type_combo.currentIndexChanged.connect(self._on_filter_type_changed)
        type_row.addWidget(self.filter_type_combo, stretch=1)
        form_layout.addLayout(type_row)

        # Row 3: Parameter Stack
        self.param_stack = QStackedWidget()

        # Page 0: Gaussian
        p0 = QWidget()
        l0 = QHBoxLayout(p0)
        l0.setContentsMargins(0, 0, 0, 0)
        l0.addWidget(QLabel("Sigma (σ in points):"))
        self.gaussian_sigma_spin = QDoubleSpinBox()
        self.gaussian_sigma_spin.setRange(0.1, 100.0)
        self.gaussian_sigma_spin.setSingleStep(0.5)
        self.gaussian_sigma_spin.setValue(2.0)
        self.gaussian_sigma_spin.valueChanged.connect(self._update_preview)
        l0.addWidget(self.gaussian_sigma_spin)
        l0.addWidget(QLabel("<span style='color: #94a3b8; font-size: 11px;'>(Standard deviation of Gaussian kernel)</span>"))
        l0.addStretch()
        self.param_stack.addWidget(p0)

        # Page 1: Median
        p1 = QWidget()
        l1 = QHBoxLayout(p1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addWidget(QLabel("Kernel Size (Points):"))
        self.median_size_spin = QSpinBox()
        self.median_size_spin.setRange(3, 101)
        self.median_size_spin.setSingleStep(2)
        self.median_size_spin.setValue(3)
        self.median_size_spin.valueChanged.connect(self._update_preview)
        l1.addWidget(self.median_size_spin)
        l1.addWidget(QLabel("<span style='color: #94a3b8; font-size: 11px;'>(Must be odd; removes impulsive noise)</span>"))
        l1.addStretch()
        self.param_stack.addWidget(p1)

        # Page 2: Moving Average
        p2 = QWidget()
        l2 = QHBoxLayout(p2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addWidget(QLabel("Window Size (Points):"))
        self.mavg_window_spin = QSpinBox()
        self.mavg_window_spin.setRange(2, 200)
        self.mavg_window_spin.setValue(5)
        self.mavg_window_spin.valueChanged.connect(self._update_preview)
        l2.addWidget(self.mavg_window_spin)
        l2.addWidget(QLabel("<span style='color: #94a3b8; font-size: 11px;'>(Centered sliding window width)</span>"))
        l2.addStretch()
        self.param_stack.addWidget(p2)

        # Page 3: Savitzky-Golay
        p3 = QWidget()
        l3 = QHBoxLayout(p3)
        l3.setContentsMargins(0, 0, 0, 0)
        l3.addWidget(QLabel("Window Length:"))
        self.savgol_win_spin = QSpinBox()
        self.savgol_win_spin.setRange(3, 101)
        self.savgol_win_spin.setSingleStep(2)
        self.savgol_win_spin.setValue(7)
        self.savgol_win_spin.valueChanged.connect(self._update_preview)
        l3.addWidget(self.savgol_win_spin)

        l3.addWidget(QLabel("Poly Order:"))
        self.savgol_poly_spin = QSpinBox()
        self.savgol_poly_spin.setRange(1, 5)
        self.savgol_poly_spin.setValue(2)
        self.savgol_poly_spin.valueChanged.connect(self._update_preview)
        l3.addWidget(self.savgol_poly_spin)
        l3.addWidget(QLabel("<span style='color: #94a3b8; font-size: 11px;'>(Preserves peak shapes)</span>"))
        l3.addStretch()
        self.param_stack.addWidget(p3)

        form_layout.addWidget(self.param_stack)

        # Row 4: Output Destination
        dest_box = QHBoxLayout()
        self.radio_new_col = QRadioButton("Add as new column:")
        self.radio_new_col.setChecked(True)
        self.radio_new_col.toggled.connect(self._on_dest_mode_toggled)
        dest_box.addWidget(self.radio_new_col)

        self.new_name_edit = QLineEdit()
        dest_box.addWidget(self.new_name_edit, stretch=1)

        self.radio_inplace = QRadioButton("Replace in-place")
        self.radio_inplace.setToolTip("Overwrite the original column values with the smoothed result")
        dest_box.addWidget(self.radio_inplace)
        form_layout.addLayout(dest_box)

        layout.addWidget(form_group)

        # Live Calculation Preview
        preview_group = QGroupBox("Live Calculation Preview (First 8 Rows)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["Row", "Original", "Smoothed", "Diff (Noise)"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.setFixedHeight(140)
        preview_layout.addWidget(self.preview_table)

        self.stats_label = QLabel("RMS Difference: -")
        self.stats_label.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
        preview_layout.addWidget(self.stats_label)

        layout.addWidget(preview_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Smoothing")
        apply_btn.setObjectName("accentBtn")
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)

        layout.addLayout(btn_row)

        self._update_default_name()

    def _on_filter_type_changed(self, idx: int):
        self.param_stack.setCurrentIndex(idx)
        self._update_default_name()
        self._update_preview()

    def _on_target_changed(self):
        self._update_default_name()
        self._update_preview()

    def _on_dest_mode_toggled(self, checked: bool):
        self.new_name_edit.setEnabled(checked)

    def _update_default_name(self):
        col = self.col_combo.currentText()
        col_clean = re.sub(r"\W+", "_", col).strip("_")
        ftype = self.filter_type_combo.currentData()
        suffix_map = {
            "gaussian": f"gauss_s{self.gaussian_sigma_spin.value():.1f}".replace(".", "p"),
            "median": f"med_k{self.median_size_spin.value()}",
            "moving_avg": f"mavg_w{self.mavg_window_spin.value()}",
            "savgol": f"savgol_w{self.savgol_win_spin.value()}"
        }
        suffix = suffix_map.get(ftype, "smoothed")
        self.new_name_edit.setText(f"{col_clean}_{suffix}")

    def _compute_smoothing(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if self.df.empty:
            return None, None
        col = self.col_combo.currentText()
        if col not in self.df.columns:
            return None, None

        orig_vals = pd.to_numeric(self.df[col], errors="coerce").to_numpy()
        ftype = self.filter_type_combo.currentData()

        if ftype == "gaussian":
            smoothed = apply_gaussian_filter(orig_vals, sigma=self.gaussian_sigma_spin.value())
            self.formula_expr = f"gaussian_filter({col}, {self.gaussian_sigma_spin.value()})"
        elif ftype == "median":
            smoothed = apply_median_filter(orig_vals, size=self.median_size_spin.value())
            self.formula_expr = f"median_filter({col}, {self.median_size_spin.value()})"
        elif ftype == "moving_avg":
            smoothed = apply_moving_average(orig_vals, window=self.mavg_window_spin.value())
            self.formula_expr = f"moving_average({col}, {self.mavg_window_spin.value()})"
        elif ftype == "savgol":
            w = self.savgol_win_spin.value()
            p = self.savgol_poly_spin.value()
            smoothed = apply_savgol_filter(orig_vals, window_length=w, polyorder=p)
            self.formula_expr = f"savgol_filter({col}, {w}, {p})"
        else:
            smoothed = orig_vals
            self.formula_expr = f"{col}"

        return orig_vals, smoothed

    def _update_preview(self):
        orig_vals, smoothed = self._compute_smoothing()
        if smoothed is None or len(smoothed) == 0:
            self.preview_table.setRowCount(0)
            self.stats_label.setText("RMS Difference: -")
            return

        nrows = min(8, len(smoothed))
        self.preview_table.setRowCount(nrows)
        diff = orig_vals - smoothed

        for r in range(nrows):
            self.preview_table.setItem(r, 0, QTableWidgetItem(str(r)))
            
            o_str = f"{orig_vals[r]:.5g}" if np.isfinite(orig_vals[r]) else str(orig_vals[r])
            self.preview_table.setItem(r, 1, QTableWidgetItem(o_str))
            
            s_str = f"{smoothed[r]:.5g}" if np.isfinite(smoothed[r]) else str(smoothed[r])
            item_s = QTableWidgetItem(s_str)
            item_s.setForeground(Qt.cyan)
            self.preview_table.setItem(r, 2, item_s)
            
            d_str = f"{diff[r]:.5g}" if np.isfinite(diff[r]) else str(diff[r])
            self.preview_table.setItem(r, 3, QTableWidgetItem(d_str))

        finite_diff = diff[np.isfinite(diff)]
        if len(finite_diff) > 0:
            rms = np.sqrt(np.mean(finite_diff ** 2))
            self.stats_label.setText(f"RMS Noise Removed: {rms:.4g} | Mean Offset: {np.mean(finite_diff):.4g}")
        else:
            self.stats_label.setText("RMS Difference: 0.0")

    def _apply(self):
        orig_vals, smoothed = self._compute_smoothing()
        if smoothed is None or len(smoothed) == 0:
            QMessageBox.critical(self, "Calculation Error", "Failed to compute smoothed values. Check column data.")
            return

        self.result_data = smoothed
        self.replace_inplace = self.radio_inplace.isChecked()

        if self.replace_inplace:
            self.target_col_name = self.col_combo.currentText()
        else:
            name = self.new_name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Invalid Name", "Please enter a valid column name.")
                return
            if name in self.df.columns and not self.replace_inplace:
                ret = QMessageBox.question(
                    self,
                    "Column Exists",
                    f"Column '{name}' already exists. Overwrite it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if ret != QMessageBox.Yes:
                    return
            self.target_col_name = name

        self.accept()
