"""
Data Tab (Data Hub)
Manages loaded datasets, initiates the Smart Import Wizard,
provides table/matrix data inspection, manual column renaming,
and executes inline column math/transformations.
"""

import re
from typing import Dict, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QGroupBox, QLineEdit, QSplitter, QMessageBox, QComboBox,
    QHeaderView, QInputDialog, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
import pandas as pd
import numpy as np

from core.models import Dataset
from core.data_loader import evaluate_column_expression
from gui.smart_import_dialog import SmartImportDialog


class DataTab(QWidget):
    """
    Data Manager tab:
    - Lists datasets
    - Smart import launcher
    - Data inspection table with double-click column renaming
    - Explicit manual column renamer tool
    - Calculated column generator (math expressions)
    """
    data_changed = Signal()  # Emitted when datasets are added, removed, or modified
    column_renamed = Signal(str, str, str)  # (dataset_id, old_name, new_name)

    def __init__(self, datasets: Dict[str, Dataset], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.datasets = datasets
        self.active_dataset_id: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)

        # 1. Dataset list & Smart Import button
        top_box = QGroupBox("Imported Datasets")
        top_layout = QVBoxLayout(top_box)

        btn_row = QHBoxLayout()
        import_btn = QPushButton("+ Smart Import Data File...")
        import_btn.setObjectName("primaryBtn")
        import_btn.clicked.connect(self._open_smart_importer)
        
        remove_btn = QPushButton("Remove Dataset")
        remove_btn.setStyleSheet("color: #f87171;")
        remove_btn.clicked.connect(self._remove_selected_dataset)

        save_btn = QPushButton("💾 Save Project State")
        save_btn.setToolTip("Save complete project workspace including all imported data, calculated columns, and plots")
        save_btn.clicked.connect(self._save_project_clicked)

        btn_row.addWidget(import_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        top_layout.addLayout(btn_row)

        self.dataset_list = QListWidget()
        self.dataset_list.currentRowChanged.connect(self._on_dataset_selected)
        top_layout.addWidget(self.dataset_list)

        splitter.addWidget(top_box)

        # 2. Selected Dataset Inspection Table
        preview_box = QGroupBox("Dataset Inspector (Double-click any header to rename column)")
        preview_layout = QVBoxLayout(preview_box)

        self.info_label = QLabel("Select a dataset to inspect")
        self.info_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        preview_layout.addWidget(self.info_label)

        self.inspect_table = QTableWidget()
        self.inspect_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.inspect_table.horizontalHeader().setDefaultSectionSize(95)
        # Connect header double click to rename
        self.inspect_table.horizontalHeader().sectionDoubleClicked.connect(self._on_header_double_clicked)
        preview_layout.addWidget(self.inspect_table)

        # Dedicated Column Renaming Bar
        rename_bar = QHBoxLayout()
        rename_bar.addWidget(QLabel("<b>Rename Column:</b>"))
        self.rename_col_combo = QComboBox()
        self.rename_col_combo.setMinimumWidth(130)
        self.rename_col_combo.currentIndexChanged.connect(self._on_rename_col_selected)
        rename_bar.addWidget(self.rename_col_combo)

        rename_bar.addWidget(QLabel("New Name:"))
        self.rename_new_name_edit = QLineEdit()
        self.rename_new_name_edit.setPlaceholderText("Enter new column name...")
        rename_bar.addWidget(self.rename_new_name_edit)

        apply_rename_btn = QPushButton("Apply Rename")
        apply_rename_btn.setObjectName("primaryBtn")
        apply_rename_btn.clicked.connect(self._apply_column_rename)
        rename_bar.addWidget(apply_rename_btn)
        preview_layout.addLayout(rename_bar)

        splitter.addWidget(preview_box)

        # 3. Column Math & Transformation Tools
        calc_box = QGroupBox("Column Transformation & Math Calculator")
        calc_layout = QVBoxLayout(calc_box)
        calc_layout.setSpacing(6)

        formula_row = QHBoxLayout()
        formula_row.addWidget(QLabel("New Col Name:"))
        self.new_col_edit = QLineEdit("Transformed")
        self.new_col_edit.setFixedWidth(120)
        formula_row.addWidget(self.new_col_edit)

        formula_row.addWidget(QLabel("Expression:"))
        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText("e.g. dedB(col), col * 1e3, np.log10(col), col - col.min()")
        formula_row.addWidget(self.expr_edit)

        quick_combo = QComboBox()
        quick_combo.addItem("Quick Formula Templates...")
        quick_combo.addItem("de-dB (Amplitude/Voltage): dedB(col)", "dedb_amp")
        quick_combo.addItem("de-dB (Power/Intensity): dedB_power(col)", "dedb_pwr")
        quick_combo.addItem("Convert to dB (Amplitude): to_dB(col)", "to_db_amp")
        quick_combo.addItem("Convert to dB (Power): to_dB_power(col)", "to_db_pwr")
        quick_combo.addItem("Scale: col * 1000", "scale_1000")
        quick_combo.addItem("Divide: col / 1000", "div_1000")
        quick_combo.addItem("Normalize: (col - col.min()) / (col.max() - col.min())", "normalize")
        quick_combo.addItem("Relative: col - col.iloc[0]", "relative")
        quick_combo.addItem("Log10: np.log10(np.abs(col) + 1e-12)", "log10")
        quick_combo.addItem("Derivative: np.gradient(col)", "gradient")
        quick_combo.currentIndexChanged.connect(lambda idx: self._apply_quick_formula(quick_combo, idx))
        formula_row.addWidget(quick_combo)

        calc_btn = QPushButton("Calculate & Add")
        calc_btn.setObjectName("accentBtn")
        calc_btn.clicked.connect(self._on_calculate_column)
        formula_row.addWidget(calc_btn)
        calc_layout.addLayout(formula_row)

        # Usable Names Bar (Clickable Pills)
        vars_header_row = QHBoxLayout()
        vars_header_row.addWidget(QLabel("<b>Usable Names in Expressions:</b> (Click any badge to insert into formula)"))
        vars_header_row.addStretch()
        calc_layout.addLayout(vars_header_row)

        self.vars_scroll = QScrollArea()
        self.vars_scroll.setFixedHeight(68)
        self.vars_scroll.setWidgetResizable(True)
        self.vars_scroll.setStyleSheet("QScrollArea { border: 1px solid #334155; background: #141419; border-radius: 4px; }")
        
        self.vars_container = QWidget()
        self.vars_container.setStyleSheet("background: #141419;")
        self.vars_pills_layout = QHBoxLayout(self.vars_container)
        self.vars_pills_layout.setContentsMargins(6, 4, 6, 4)
        self.vars_pills_layout.setSpacing(6)
        self.vars_scroll.setWidget(self.vars_container)
        calc_layout.addWidget(self.vars_scroll)

        splitter.addWidget(calc_box)

        splitter.setSizes([120, 230, 160])
        main_layout.addWidget(splitter)

    def _save_project_clicked(self):
        parent = self.window()
        if hasattr(parent, "save_project_state"):
            parent.save_project_state()

    def _open_smart_importer(self):
        dialog = SmartImportDialog(parent=self)
        if dialog.exec() == SmartImportDialog.Accepted and dialog.imported_dataset:
            ds = dialog.imported_dataset
            self.datasets[ds.id] = ds
            self.refresh_dataset_list(select_id=ds.id)
            self.data_changed.emit()

    def add_dataset(self, ds: Dataset):
        self.datasets[ds.id] = ds
        self.refresh_dataset_list(select_id=ds.id)
        self.data_changed.emit()

    def refresh_dataset_list(self, select_id: Optional[str] = None):
        self.dataset_list.clear()
        selected_row = 0
        for idx, (d_id, ds) in enumerate(self.datasets.items()):
            type_badge = "[1D Table]" if ds.data_type == "1d_table" else "[2D Matrix]"
            item = QListWidgetItem(f"{type_badge} {ds.name}  ({ds.get_shape_str()})")
            item.setData(Qt.UserRole, d_id)
            self.dataset_list.addItem(item)
            if select_id and d_id == select_id:
                selected_row = idx

        if self.dataset_list.count() > 0:
            self.dataset_list.setCurrentRow(selected_row)
        else:
            self.active_dataset_id = None
            self.inspect_table.clear()
            self.inspect_table.setRowCount(0)
            self.inspect_table.setColumnCount(0)
            self.rename_col_combo.clear()
            self.info_label.setText("No datasets loaded. Click 'Smart Import Data File...' to load data.")

    def _on_dataset_selected(self, row: int):
        if row < 0:
            return
        item = self.dataset_list.item(row)
        if not item:
            return
        d_id = item.data(Qt.UserRole)
        self.active_dataset_id = d_id
        self._display_dataset(d_id)

    def _display_dataset(self, d_id: str):
        d = self.datasets.get(d_id)
        if not d:
            return

        self.info_label.setText(
            f"Dataset: <b>{d.name}</b> | Type: {d.data_type} | Shape: {d.get_shape_str()} | File: {d.filepath or 'Memory'}"
        )

        df = d.df
        self.rename_col_combo.clear()

        if df is not None and not df.empty:
            for col in df.columns:
                self.rename_col_combo.addItem(str(col), str(col))

            nrows = min(100, len(df))
            ncols = len(df.columns)
            self.inspect_table.clear()
            self.inspect_table.setRowCount(nrows)
            self.inspect_table.setColumnCount(ncols)
            self.inspect_table.setHorizontalHeaderLabels([str(c) for c in df.columns])

            for r in range(nrows):
                for c in range(ncols):
                    val = df.iloc[r, c]
                    text = f"{val:.5g}" if isinstance(val, (int, float, np.floating, np.integer)) else str(val)
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignRight if isinstance(val, (int, float, np.number)) else Qt.AlignLeft)
                    self.inspect_table.setItem(r, c, item)
            
            # Update usable names pills for this dataset
            self._update_usable_names_pills(d)
        else:
            self.inspect_table.clear()
            self.inspect_table.setRowCount(0)
            self.inspect_table.setColumnCount(0)
            self._update_usable_names_pills(None)

    def _on_rename_col_selected(self, index: int):
        col_name = self.rename_col_combo.currentText()
        if col_name:
            self.rename_new_name_edit.setText(col_name)

    def _on_header_double_clicked(self, logical_index: int):
        """Allow renaming a column by double-clicking its header in the table."""
        if not self.active_dataset_id:
            return
        d = self.datasets.get(self.active_dataset_id)
        if not d or d.df is None or logical_index >= len(d.df.columns):
            return

        old_name = str(d.df.columns[logical_index])
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Column",
            f"Enter new name for column '{old_name}':",
            QLineEdit.Normal,
            old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            self._execute_column_rename(d, old_name, new_name.strip())

    def _apply_column_rename(self):
        """Called from the dedicated rename bar button."""
        if not self.active_dataset_id:
            return
        d = self.datasets.get(self.active_dataset_id)
        if not d or d.df is None:
            return

        old_name = self.rename_col_combo.currentText()
        new_name = self.rename_new_name_edit.text().strip()

        if not old_name:
            QMessageBox.warning(self, "No Column", "Please select a column to rename.")
            return
        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "New column name cannot be empty.")
            return
        if new_name == old_name:
            return

        if new_name in d.df.columns:
            QMessageBox.warning(self, "Name Exists", f"A column named '{new_name}' already exists in this dataset.")
            return

        self._execute_column_rename(d, old_name, new_name)

    def _execute_column_rename(self, dataset: Dataset, old_name: str, new_name: str):
        # 1. Rename column in DataFrame
        dataset.df.rename(columns={old_name: new_name}, inplace=True)

        # 2. Emit signal so FigureConfig can update all trace bindings
        self.column_renamed.emit(dataset.id, old_name, new_name)

        # 3. Refresh inspection table and combo
        self._display_dataset(dataset.id)

        # 4. Trigger plot update
        self.data_changed.emit()

    def _remove_selected_dataset(self):
        if not self.active_dataset_id:
            return
        del self.datasets[self.active_dataset_id]
        self.refresh_dataset_list()
        self.data_changed.emit()

    def _insert_variable(self, text: str):
        self.expr_edit.insert(text)
        self.expr_edit.setFocus()

    def _insert_function(self, func_str: str):
        self.expr_edit.insert(func_str)
        # Move cursor back 1 character if ends with '()' to place inside parentheses
        if func_str.endswith("()"):
            pos = self.expr_edit.cursorPosition() - 1
            self.expr_edit.setCursorPosition(pos)
        self.expr_edit.setFocus()

    def _update_usable_names_pills(self, dataset: Optional[Dataset]):
        """Populates the clickable chips with available column variable names and math functions."""
        # Clear layout
        while self.vars_pills_layout.count():
            item = self.vars_pills_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if dataset is None or dataset.df is None or dataset.df.empty:
            empty_lbl = QLabel("No active columns. Select a dataset above.")
            empty_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            self.vars_pills_layout.addWidget(empty_lbl)
            self.vars_pills_layout.addStretch()
            return

        # 1. Column Pills
        for col in dataset.df.columns:
            col_str = str(col)
            if col_str.isidentifier():
                pill_name = col_str
                insert_text = col_str
                tooltip = f"Column variable: '{col_str}'\nClick to insert into expression"
            else:
                safe_alias = re.sub(r"\W+", "_", col_str).strip("_")
                pill_name = f"{safe_alias} ({col_str})"
                insert_text = safe_alias
                tooltip = f"Column alias: '{safe_alias}' (references '{col_str}')\nClick to insert into expression"

            btn = QPushButton(pill_name)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #38bdf8;
                    border: 1px solid #0284c7;
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda _, t=insert_text: self._insert_variable(t))
            self.vars_pills_layout.addWidget(btn)

        # Separator / Built-in Operations label
        sep_lbl = QLabel("| Math:")
        sep_lbl.setStyleSheet("color: #64748b; font-weight: bold; margin: 0 4px;")
        self.vars_pills_layout.addWidget(sep_lbl)

        # 2. Built-in Math & dedB Function Pills
        math_ops = [
            ("dedB()", "dedB()", "Revert dB for amplitude/voltage: 10 ** (x / 20)"),
            ("dedB_power()", "dedB_power()", "Revert dB for power/intensity: 10 ** (x / 10)"),
            ("to_dB()", "to_dB()", "Convert amplitude to dB: 20 * log10(abs(x))"),
            ("to_dB_power()", "to_dB_power()", "Convert power to dB: 10 * log10(abs(x))"),
            ("np.log10()", "np.log10()", "Base-10 logarithm"),
            ("np.exp()", "np.exp()", "Exponential function e^x"),
            ("np.sqrt()", "np.sqrt()", "Square root"),
            ("np.abs()", "np.abs()", "Absolute value"),
            ("np.gradient()", "np.gradient()", "Numerical gradient / derivative"),
        ]

        for label, insert_code, tip in math_ops:
            m_btn = QPushButton(label)
            m_btn.setToolTip(f"{tip}\nClick to insert")
            m_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #a78bfa;
                    border: 1px solid #7c3aed;
                    border-radius: 10px;
                    padding: 3px 8px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #7c3aed;
                    color: #ffffff;
                }
            """)
            m_btn.clicked.connect(lambda _, t=insert_code: self._insert_function(t))
            self.vars_pills_layout.addWidget(m_btn)

        self.vars_pills_layout.addStretch()

    def _apply_quick_formula(self, combo: QComboBox, idx: int):
        if idx <= 0 or not self.active_dataset_id:
            return
        d = self.datasets.get(self.active_dataset_id)
        if not d or d.df is None or d.df.empty:
            return
        
        raw_col = self.rename_col_combo.currentText() or str(d.df.columns[-1])
        col_var = raw_col if str(raw_col).isidentifier() else re.sub(r"\W+", "_", str(raw_col)).strip("_")
        
        action = combo.itemData(idx)
        if action == "dedb_amp":
            self.expr_edit.setText(f"dedB({col_var})")
            self.new_col_edit.setText(f"{col_var}_lin")
        elif action == "dedb_pwr":
            self.expr_edit.setText(f"dedB_power({col_var})")
            self.new_col_edit.setText(f"{col_var}_lin")
        elif action == "to_db_amp":
            self.expr_edit.setText(f"to_dB({col_var})")
            self.new_col_edit.setText(f"{col_var}_dB")
        elif action == "to_db_pwr":
            self.expr_edit.setText(f"to_dB_power({col_var})")
            self.new_col_edit.setText(f"{col_var}_dB")
        elif action == "scale_1000":
            self.expr_edit.setText(f"{col_var} * 1000")
            self.new_col_edit.setText(f"{col_var}_x1k")
        elif action == "div_1000":
            self.expr_edit.setText(f"{col_var} / 1000")
            self.new_col_edit.setText(f"{col_var}_k")
        elif action == "normalize":
            self.expr_edit.setText(f"({col_var} - {col_var}.min()) / ({col_var}.max() - {col_var}.min())")
            self.new_col_edit.setText(f"{col_var}_norm")
        elif action == "relative":
            self.expr_edit.setText(f"{col_var} - {col_var}.iloc[0]")
            self.new_col_edit.setText(f"{col_var}_rel")
        elif action == "log10":
            self.expr_edit.setText(f"np.log10(np.abs({col_var}) + 1e-12)")
            self.new_col_edit.setText(f"{col_var}_log10")
        elif action == "gradient":
            self.expr_edit.setText(f"np.gradient({col_var})")
            self.new_col_edit.setText(f"d_{col_var}")
        
        combo.setCurrentIndex(0)

    def _on_calculate_column(self):
        if not self.active_dataset_id:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset to transform.")
            return

        d = self.datasets.get(self.active_dataset_id)
        if not d or d.df is None or d.df.empty:
            QMessageBox.warning(self, "Empty Dataset", "Dataset contains no table data.")
            return

        new_name = self.new_col_edit.text().strip()
        expr = self.expr_edit.text().strip()

        if not new_name or not expr:
            QMessageBox.warning(self, "Input Error", "Please provide a column name and an expression.")
            return

        new_df, err = evaluate_column_expression(d.df, new_name, expr)
        if err:
            QMessageBox.critical(self, "Calculation Error", f"Failed to compute expression:\n{err}")
            return

        d.df = new_df
        self._display_dataset(self.active_dataset_id)
        self.data_changed.emit()
        QMessageBox.information(self, "Success", f"Column '{new_name}' added successfully!")
