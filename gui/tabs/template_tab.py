"""
Template & Batch Mode Tab
Allows saving and loading figure style templates (.json),
and executing automated batch processing across multiple data files.
"""

import os
import json
from typing import Dict, Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QListWidget, QProgressBar,
    QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
import matplotlib.pyplot as plt

from core.models import FigureConfig, Dataset, AxisConfig, TraceConfig
from core.data_loader import sniff_file_parameters, parse_file
from core.code_generator import generate_python_code


class TemplateTab(QWidget):
    """
    Template & Batch Mode:
    - Save/Load plot configuration templates
    - Batch apply styling to multiple data files and export figures/scripts
    """
    template_applied = Signal()

    def __init__(
        self,
        fig_config: FigureConfig,
        datasets: Dict[str, Dataset],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.fig_config = fig_config
        self.datasets = datasets
        self.batch_files: List[str] = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # 1. Template Management Group
        template_box = QGroupBox("Plot Style Templates")
        t_layout = QVBoxLayout(template_box)

        btn_row = QHBoxLayout()
        save_tmpl_btn = QPushButton("Save Style Template (.json)...")
        save_tmpl_btn.clicked.connect(self._save_template)

        load_tmpl_btn = QPushButton("Load & Apply Template...")
        load_tmpl_btn.setObjectName("primaryBtn")
        load_tmpl_btn.clicked.connect(self._load_template)

        btn_row.addWidget(save_tmpl_btn)
        btn_row.addWidget(load_tmpl_btn)
        btn_row.addStretch()
        t_layout.addLayout(btn_row)

        desc = QLabel(
            "Templates preserve your exact grid layouts, font settings, physical dimensions, "
            "tick directions, colorbars, and channel styles. You can apply them to new datasets instantly."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        t_layout.addWidget(desc)
        main_layout.addWidget(template_box)

        # 2. Batch Processing Group
        batch_box = QGroupBox("Batch Processing & Export")
        b_layout = QVBoxLayout(batch_box)

        file_action_row = QHBoxLayout()
        add_files_btn = QPushButton("+ Select Data Files...")
        add_files_btn.clicked.connect(self._select_batch_files)
        clear_files_btn = QPushButton("Clear Files")
        clear_files_btn.clicked.connect(self._clear_batch_files)

        file_action_row.addWidget(add_files_btn)
        file_action_row.addWidget(clear_files_btn)
        file_action_row.addStretch()
        b_layout.addLayout(file_action_row)

        self.batch_list = QListWidget()
        self.batch_list.setMaximumHeight(130)
        b_layout.addWidget(self.batch_list)

        # Export settings
        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Output Format:"))
        self.batch_fmt_combo = QComboBox()
        self.batch_fmt_combo.addItems(["PDF (Vector)", "PNG (Raster)", "SVG (Vector)", "Standalone .py Script"])
        opt_row.addWidget(self.batch_fmt_combo)

        opt_row.addWidget(QLabel("DPI:"))
        self.batch_dpi_spin = QSpinBox()
        self.batch_dpi_spin.setRange(72, 1200)
        self.batch_dpi_spin.setValue(300)
        opt_row.addWidget(self.batch_dpi_spin)
        opt_row.addStretch()
        b_layout.addLayout(opt_row)

        # Run Batch button
        run_row = QHBoxLayout()
        self.run_batch_btn = QPushButton("Execute Batch Export")
        self.run_batch_btn.setObjectName("accentBtn")
        self.run_batch_btn.clicked.connect(self._run_batch)
        run_row.addWidget(self.run_batch_btn)
        run_row.addStretch()
        b_layout.addLayout(run_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        b_layout.addWidget(self.progress_bar)

        self.batch_status = QLabel("Ready")
        self.batch_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        b_layout.addWidget(self.batch_status)

        main_layout.addWidget(batch_box)
        main_layout.addStretch()

    def _save_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot Template", "my_plot_template.json", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            # We save figure layout and trace styling schemes without raw data arrays
            data = self.fig_config.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Template Saved", f"Saved template successfully to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")

    def _load_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Plot Template", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            new_fig = FigureConfig.from_dict(data)
            
            # Update attributes of existing fig_config in-place
            self.fig_config.nrows = new_fig.nrows
            self.fig_config.ncols = new_fig.ncols
            self.fig_config.width_cm = new_fig.width_cm
            self.fig_config.height_cm = new_fig.height_cm
            self.fig_config.dpi = new_fig.dpi
            self.fig_config.preset_name = new_fig.preset_name
            self.fig_config.sharex = new_fig.sharex
            self.fig_config.sharey = new_fig.sharey
            self.fig_config.style = new_fig.style
            self.fig_config.font_family = new_fig.font_family
            self.fig_config.font_size = new_fig.font_size
            self.fig_config.usetex = new_fig.usetex
            self.fig_config.tight_layout = new_fig.tight_layout
            self.fig_config.figure_title = new_fig.figure_title
            self.fig_config.axes = new_fig.axes
            self.fig_config.ensure_axes_grid()

            self.template_applied.emit()
            QMessageBox.information(self, "Success", "Template loaded and applied successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load template:\n{e}")

    def _select_batch_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files for Batch Export", "",
            "Data Files (*.txt *.dat *.csv *.tsv);;All Files (*.*)"
        )
        if files:
            for f in files:
                if f not in self.batch_files:
                    self.batch_files.append(f)
                    self.batch_list.addItem(os.path.basename(f))

    def _clear_batch_files(self):
        self.batch_files.clear()
        self.batch_list.clear()

    def _run_batch(self):
        if not self.batch_files:
            QMessageBox.warning(self, "No Files", "Please add data files to process.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Batch Export")
        if not out_dir:
            return

        fmt = self.batch_fmt_combo.currentText()
        dpi = self.batch_dpi_spin.value()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.batch_files))
        self.progress_bar.setValue(0)

        success_count = 0
        for idx, file_path in enumerate(self.batch_files):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.batch_status.setText(f"Processing: {base_name} ({idx+1}/{len(self.batch_files)})")

            try:
                # Sniff and parse the file
                sniff = sniff_file_parameters(file_path)
                df, mat, err = parse_file(file_path, sniff)
                if err:
                    continue

                # Create temporary dataset
                d_type = "2d_matrix" if sniff.get("is_2d_matrix") else "1d_table"
                ds = Dataset(name=base_name, data_type=d_type, df=df, matrix=mat, filepath=file_path, meta=sniff)

                # Clone fig_config and rewire traces to this dataset
                batch_fig = FigureConfig.from_dict(self.fig_config.to_dict())
                for ax in batch_fig.axes.values():
                    for tr in ax.traces:
                        tr.dataset_id = ds.id
                        # If column names differ, adapt to available columns
                        cols = ds.get_columns()
                        if cols:
                            if tr.x_col not in cols:
                                tr.x_col = cols[0]
                            if tr.y_col not in cols:
                                tr.y_col = cols[1] if len(cols) > 1 else cols[0]

                if "Script" in fmt:
                    out_file = os.path.join(out_dir, f"{base_name}_plot.py")
                    py_code = generate_python_code(batch_fig, {ds.id: ds}, output_fig_name=f"{base_name}.pdf")
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(py_code)
                else:
                    ext = ".pdf" if "PDF" in fmt else (".png" if "PNG" in fmt else ".svg")
                    out_file = os.path.join(out_dir, f"{base_name}{ext}")
                    
                    # Quick headless matplotlib render
                    fig, axes = plt.subplots(
                        batch_fig.nrows, batch_fig.ncols,
                        figsize=(batch_fig.width_cm / 2.54, batch_fig.height_cm / 2.54),
                        dpi=dpi, squeeze=False
                    )
                    # Render traces
                    for r in range(batch_fig.nrows):
                        for c in range(batch_fig.ncols):
                            ax = axes[r, c]
                            ax_c = batch_fig.get_axis(r, c)
                            for tr in ax_c.traces:
                                if tr.plot_type == "line" and ds.df is not None:
                                    y = ds.df[tr.y_col]
                                    x = ds.df[tr.x_col] if tr.x_col else range(len(y))
                                    ax.plot(x, y, label=tr.label or None)
                            if ax_c.title:
                                ax.set_title(ax_c.title)
                            if ax_c.xlabel:
                                ax.set_xlabel(ax_c.xlabel)
                            if ax_c.ylabel:
                                ax.set_ylabel(ax_c.ylabel)
                    if batch_fig.tight_layout:
                        fig.tight_layout()
                    fig.savefig(out_file, dpi=dpi, bbox_inches="tight")
                    plt.close(fig)

                success_count += 1
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

            self.progress_bar.setValue(idx + 1)

        self.batch_status.setText(f"Batch completed: {success_count}/{len(self.batch_files)} exported.")
        QMessageBox.information(
            self, "Batch Complete",
            f"Successfully processed and exported {success_count} files to:\n{out_dir}"
        )
