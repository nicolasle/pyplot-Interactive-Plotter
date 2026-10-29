"""
Smart Data Import Dialog
Provides automatic sniffing of scientific data formats with an interactive
side-by-side raw preview and live parsed table preview.
Allows immediate user correction of delimiter, headers, skiprows, and decimal mark.
"""

import os
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QGroupBox, QFileDialog, QMessageBox,
    QRadioButton, QButtonGroup, QLineEdit, QHeaderView, QInputDialog
)
from PySide6.QtCore import Qt, Signal
import pandas as pd
import numpy as np

from core.data_loader import sniff_file_parameters, parse_file
from core.models import Dataset


class SmartImportDialog(QDialog):
    """
    Dialog for importing data files with automatic format detection
    and live real-time correction.
    """
    def __init__(self, filepath: Optional[str] = None, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Smart Scientific Data Importer")
        self.resize(1050, 720)

        self.filepath = filepath
        self.sniffed_params: Dict[str, Any] = {}
        self.current_df: Optional[pd.DataFrame] = None
        self.current_matrix: Optional[np.ndarray] = None
        self.imported_dataset: Optional[Dataset] = None
        self.custom_column_names: Dict[str, str] = {}

        self._setup_ui()

        if self.filepath and os.path.exists(self.filepath):
            self.load_file(self.filepath)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Top file selection bar
        file_bar = QHBoxLayout()
        self.file_label = QLabel("File: No file selected")
        self.file_label.setStyleSheet("font-weight: 600; color: #60a5fa;")
        browse_btn = QPushButton("Browse File...")
        browse_btn.clicked.connect(self._on_browse)
        file_bar.addWidget(self.file_label)
        file_bar.addStretch()
        file_bar.addWidget(browse_btn)
        main_layout.addLayout(file_bar)

        # Main splitter (Top: Raw text & Controls | Bottom: Parsed table preview)
        v_splitter = QSplitter(Qt.Vertical)

        # Upper splitter (Left: Raw Text | Right: Parsing Controls)
        h_splitter = QSplitter(Qt.Horizontal)

        # Left: Raw File Text Preview
        raw_box = QGroupBox("Raw File Content (First lines)")
        raw_layout = QVBoxLayout(raw_box)
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setReadOnly(True)
        self.raw_text_edit.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; background-color: #141419; color: #cbd5e1;"
        )
        raw_layout.addWidget(self.raw_text_edit)
        h_splitter.addWidget(raw_box)

        # Right: Interpretation Controls
        ctrl_box = QGroupBox("Format Interpretation & Overrides")
        ctrl_layout = QVBoxLayout(ctrl_box)
        ctrl_layout.setSpacing(8)

        # Auto detection status banner
        self.sniff_status = QLabel("Sniffer: Select a file to analyze")
        self.sniff_status.setWordWrap(True)
        self.sniff_status.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; padding: 6px; border-radius: 4px; color: #38bdf8;"
        )
        ctrl_layout.addWidget(self.sniff_status)

        # Delimiter
        d_layout = QHBoxLayout()
        d_layout.addWidget(QLabel("Delimiter:"))
        self.delim_combo = QComboBox()
        self.delim_combo.addItem("Auto-Detect", "auto")
        self.delim_combo.addItem("Whitespace / Space (\\s+)", r"\s+")
        self.delim_combo.addItem("Tab (\\t)", "\t")
        self.delim_combo.addItem("Comma (,)", ",")
        self.delim_combo.addItem("Semicolon (;)", ";")
        self.delim_combo.addItem("Pipe (|)", "|")
        self.delim_combo.currentIndexChanged.connect(self._on_params_changed)
        d_layout.addWidget(self.delim_combo)
        ctrl_layout.addLayout(d_layout)

        # Skip rows
        skip_layout = QHBoxLayout()
        skip_layout.addWidget(QLabel("Skip rows at start:"))
        self.skiprows_spin = QSpinBox()
        self.skiprows_spin.setRange(0, 1000)
        self.skiprows_spin.setValue(0)
        self.skiprows_spin.valueChanged.connect(self._on_params_changed)
        skip_layout.addWidget(self.skiprows_spin)
        ctrl_layout.addLayout(skip_layout)

        # Header checkbox
        self.header_cb = QCheckBox("First non-skipped row has column names (Headers)")
        self.header_cb.stateChanged.connect(self._on_params_changed)
        ctrl_layout.addWidget(self.header_cb)

        # Comment Prefix
        c_layout = QHBoxLayout()
        c_layout.addWidget(QLabel("Comment prefix:"))
        self.comment_combo = QComboBox()
        self.comment_combo.addItem("Auto-Detect", "auto")
        self.comment_combo.addItem("None", "none")
        self.comment_combo.addItem("# (Hash)", "#")
        self.comment_combo.addItem("% (Percent)", "%")
        self.comment_combo.addItem("// (Slash)", "//")
        self.comment_combo.addItem("; (Semicolon)", ";")
        self.comment_combo.currentIndexChanged.connect(self._on_params_changed)
        c_layout.addWidget(self.comment_combo)
        ctrl_layout.addLayout(c_layout)

        # Decimal Separator
        dec_layout = QHBoxLayout()
        dec_layout.addWidget(QLabel("Decimal separator:"))
        self.decimal_combo = QComboBox()
        self.decimal_combo.addItem("Point (.) - Standard", ".")
        self.decimal_combo.addItem("Comma (,) - European", ",")
        self.decimal_combo.currentIndexChanged.connect(self._on_params_changed)
        dec_layout.addWidget(self.decimal_combo)
        ctrl_layout.addLayout(dec_layout)

        # Data Type interpretation
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Data Layout:"))
        self.type_1d_radio = QRadioButton("1D Column Table")
        self.type_2d_radio = QRadioButton("2D Matrix Grid")
        self.type_1d_radio.setChecked(True)
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.type_1d_radio)
        self.type_group.addButton(self.type_2d_radio)
        self.type_1d_radio.toggled.connect(self._on_params_changed)
        type_layout.addWidget(self.type_1d_radio)
        type_layout.addWidget(self.type_2d_radio)
        ctrl_layout.addLayout(type_layout)

        # Transpose controls
        t_box = QVBoxLayout()
        t_box.setSpacing(3)
        self.transpose_cb = QCheckBox("Transpose Data (Swap rows ↔ columns)")
        self.transpose_cb.setToolTip("Transpose imported data so rows become columns and columns become rows")
        self.transpose_cb.stateChanged.connect(self._on_transpose_toggled)

        self.transpose_header_cb = QCheckBox("Use first row of transposed data as column headers")
        self.transpose_header_cb.setToolTip("Promote the first row of the transposed data to column header names")
        self.transpose_header_cb.setStyleSheet("margin-left: 20px; color: #94a3b8;")
        self.transpose_header_cb.setEnabled(False)
        self.transpose_header_cb.stateChanged.connect(self._on_params_changed)

        t_box.addWidget(self.transpose_cb)
        t_box.addWidget(self.transpose_header_cb)
        ctrl_layout.addLayout(t_box)

        # Dataset Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Dataset Name:"))
        self.dataset_name_edit = QLineEdit("Dataset")
        name_layout.addWidget(self.dataset_name_edit)
        ctrl_layout.addLayout(name_layout)

        # Reset button
        reset_btn = QPushButton("Reset to Auto-Sniffed Values")
        reset_btn.clicked.connect(self._reset_to_sniffed)
        ctrl_layout.addWidget(reset_btn)

        ctrl_layout.addStretch()
        h_splitter.addWidget(ctrl_box)
        h_splitter.setSizes([450, 550])

        v_splitter.addWidget(h_splitter)

        # Lower Box: Parsed Table Preview
        preview_box = QGroupBox("Live Parsed Data Preview (Double-click any column header to rename)")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.preview_table.horizontalHeader().setDefaultSectionSize(110)
        self.preview_table.horizontalHeader().sectionDoubleClicked.connect(self._on_preview_header_double_clicked)
        preview_layout.addWidget(self.preview_table)

        self.preview_status_label = QLabel("Ready")
        self.preview_status_label.setStyleSheet("color: #10b981; font-weight: 500;")
        preview_layout.addWidget(self.preview_status_label)

        v_splitter.addWidget(preview_box)
        v_splitter.setSizes([320, 320])

        main_layout.addWidget(v_splitter)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.import_btn = QPushButton("Import Dataset")
        self.import_btn.setObjectName("primaryBtn")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import_confirmed)

        action_bar.addStretch()
        action_bar.addWidget(cancel_btn)
        action_bar.addWidget(self.import_btn)
        main_layout.addLayout(action_bar)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Scientific Data File",
            "",
            "All Supported (*.txt *.dat *.csv *.tsv *.xlsx *.xls *.npy *.npz);;Text/CSV Files (*.txt *.dat *.csv *.tsv);;NumPy Arrays (*.npy *.npz);;Excel (*.xlsx *.xls);;All Files (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, filepath: str):
        self.filepath = filepath
        self.file_label.setText(f"File: {os.path.basename(filepath)}")
        self.dataset_name_edit.setText(os.path.splitext(os.path.basename(filepath))[0])

        # Sniff parameters
        self.sniffed_params = sniff_file_parameters(filepath)

        # Display raw preview
        sample_lines = self.sniffed_params.get("sample_lines", [])
        numbered_lines = [f"{i+1:3d} | {line}" for i, line in enumerate(sample_lines)]
        self.raw_text_edit.setPlainText("\n".join(numbered_lines))

        # Populate controls from sniffed values
        self._apply_sniffed_to_controls()

    def _apply_sniffed_to_controls(self):
        p = self.sniffed_params
        if not p:
            return

        # Delimiter
        delim = p.get("delimiter", r"\s+")
        idx = self.delim_combo.findData(delim)
        if idx >= 0:
            self.delim_combo.setCurrentIndex(idx)
        else:
            self.delim_combo.setCurrentIndex(0)

        # Skip rows
        self.skiprows_spin.setValue(p.get("skiprows", 0))

        # Header
        self.header_cb.setChecked(p.get("has_header", False))

        # Comment
        comment = p.get("comment", None)
        if comment:
            idx = self.comment_combo.findData(comment)
            if idx >= 0:
                self.comment_combo.setCurrentIndex(idx)
        else:
            self.comment_combo.setCurrentIndex(self.comment_combo.findData("none"))

        # Decimal
        dec = p.get("decimal", ".")
        idx = self.decimal_combo.findData(dec)
        if idx >= 0:
            self.decimal_combo.setCurrentIndex(idx)

        # 2D matrix
        if p.get("is_2d_matrix", False):
            self.type_2d_radio.setChecked(True)
        else:
            self.type_1d_radio.setChecked(True)

        # Transpose
        self.transpose_cb.setChecked(p.get("transpose", False))
        self.transpose_header_cb.setChecked(p.get("transpose_header", False))
        self.transpose_header_cb.setEnabled(p.get("transpose", False))

        # Status text
        header_desc = "Header detected" if p.get("has_header") else "No header (auto-named)"
        delim_desc = p.get("delimiter")
        if delim_desc == r"\s+":
            delim_desc = "Whitespace"
        elif delim_desc == "\t":
            delim_desc = "Tab"
        elif delim_desc == ",":
            delim_desc = "Comma"

        self.sniff_status.setText(
            f"Auto-Detected: {delim_desc} delimiter | {header_desc} | "
            f"Skip {p.get('skiprows', 0)} rows | Decimal: '{p.get('decimal', '.')}'"
        )

        self._refresh_parsed_preview()

    def _reset_to_sniffed(self):
        self._apply_sniffed_to_controls()

    def _get_current_params(self) -> Dict[str, Any]:
        """Reads user settings from controls."""
        delim_data = self.delim_combo.currentData()
        if delim_data == "auto":
            delimiter = self.sniffed_params.get("delimiter", r"\s+")
        else:
            delimiter = delim_data

        comment_data = self.comment_combo.currentData()
        if comment_data == "auto":
            comment = self.sniffed_params.get("comment", None)
        elif comment_data == "none":
            comment = None
        else:
            comment = comment_data

        return {
            "delimiter": delimiter,
            "skiprows": self.skiprows_spin.value(),
            "has_header": self.header_cb.isChecked(),
            "comment": comment,
            "decimal": self.decimal_combo.currentData(),
            "is_2d_matrix": self.type_2d_radio.isChecked(),
            "transpose": self.transpose_cb.isChecked(),
            "transpose_header": self.transpose_header_cb.isChecked(),
            "encoding": self.sniffed_params.get("encoding", "utf-8")
        }

    def _on_transpose_toggled(self, state):
        is_transposed = self.transpose_cb.isChecked()
        self.transpose_header_cb.setEnabled(is_transposed)
        # When enabling transpose on a file where no header was detected, default transpose_header to True
        if is_transposed and not self.header_cb.isChecked():
            self.transpose_header_cb.setChecked(True)
        elif not is_transposed:
            self.transpose_header_cb.setChecked(False)
        self._on_params_changed()

    def _on_params_changed(self):
        """Called immediately whenever any control is altered."""
        if not self.filepath:
            return
        self._refresh_parsed_preview()

    def _refresh_parsed_preview(self):
        if not self.filepath:
            return

        params = self._get_current_params()
        # Parse first 50 rows for preview
        df, matrix, err = parse_file(self.filepath, params, max_rows=50)

        if err:
            self.preview_table.clear()
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            self.preview_status_label.setText(f"Error: {err}")
            self.preview_status_label.setStyleSheet("color: #ef4444; font-weight: 600;")
            self.import_btn.setEnabled(False)
            self.current_df = None
            self.current_matrix = None
            return

        self.current_df = df
        self.current_matrix = matrix
        self.import_btn.setEnabled(True)

        # Update preview table
        self.preview_table.clear()
        if df is not None and not df.empty:
            nrows = min(50, len(df))
            ncols = len(df.columns)
            self.preview_table.setRowCount(nrows)
            self.preview_table.setColumnCount(ncols)
            # Apply any custom column renames
            for old_c, new_c in self.custom_column_names.items():
                if old_c in df.columns:
                    df.rename(columns={old_c: new_c}, inplace=True)

            self.preview_table.setHorizontalHeaderLabels([str(c) for c in df.columns])

            for r in range(nrows):
                for c in range(ncols):
                    val = df.iloc[r, c]
                    text = f"{val:.5g}" if isinstance(val, (int, float, np.floating, np.integer)) else str(val)
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignRight if isinstance(val, (int, float, np.number)) else Qt.AlignLeft)
                    self.preview_table.setItem(r, c, item)

            mode_str = "2D Matrix Grid" if params["is_2d_matrix"] else "1D Column Table"
            if params.get("transpose", False):
                mode_str += " (Transposed)"
            self.preview_status_label.setText(
                f"Successfully parsed as {mode_str} ({len(df.columns)} columns, {len(df)} preview rows shown)"
            )
            self.preview_status_label.setStyleSheet("color: #10b981; font-weight: 500;")

    def _on_preview_header_double_clicked(self, logical_index: int):
        if self.current_df is None or logical_index >= len(self.current_df.columns):
            return
        old_col = str(self.current_df.columns[logical_index])
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Column",
            f"Enter custom name for column '{old_col}':",
            QLineEdit.Normal,
            old_col
        )
        if ok and new_name.strip() and new_name.strip() != old_col:
            clean_name = new_name.strip()
            self.custom_column_names[old_col] = clean_name
            self.current_df.rename(columns={old_col: clean_name}, inplace=True)
            self.preview_table.setHorizontalHeaderLabels([str(c) for c in self.current_df.columns])

    def _on_import_confirmed(self):
        """Full load without row limit, builds Dataset object, and accepts dialog."""
        if not self.filepath:
            return
        
        params = self._get_current_params()
        df, matrix, err = parse_file(self.filepath, params, max_rows=None)

        if err:
            QMessageBox.critical(self, "Import Error", f"Failed to parse complete file:\n{err}")
            return

        if df is not None and self.custom_column_names:
            df.rename(columns=self.custom_column_names, inplace=True)

        data_type = "2d_matrix" if params["is_2d_matrix"] else "1d_table"
        name = self.dataset_name_edit.text().strip() or os.path.splitext(os.path.basename(self.filepath))[0]

        self.imported_dataset = Dataset(
            name=name,
            data_type=data_type,
            df=df,
            matrix=matrix,
            filepath=self.filepath,
            meta=params
        )
        self.accept()
