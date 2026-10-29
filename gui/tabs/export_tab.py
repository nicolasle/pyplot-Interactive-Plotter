"""
Code & Export Hub Tab
Displays live-generated Python code and Jupyter Notebook cells.
Provides one-click clipboard copying, saving to .py and .ipynb files,
direct vector/raster figure export, and project session save/load.
"""

import os
import json
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QGroupBox, QFileDialog, QMessageBox,
    QApplication, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from core.models import FigureConfig, Dataset
from core.code_generator import generate_python_code, generate_jupyter_notebook
from core.project_manager import save_project_to_file, load_project_from_file, PROJECT_FILE_FILTER


class ExportTab(QWidget):
    """
    Code & Export Hub:
    - Live Python code preview
    - Live Jupyter Notebook preview
    - Export buttons (.py, .ipynb, PDF/SVG/PNG)
    - Session save/load (.json)
    """
    session_loaded = Signal()

    def __init__(
        self,
        fig_config: FigureConfig,
        datasets: Dict[str, Dataset],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.fig_config = fig_config
        self.datasets = datasets

        self._setup_ui()
        self.refresh_code()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Action Buttons Row 1: Code Exports
        code_btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copy Python Code")
        copy_btn.setObjectName("primaryBtn")
        copy_btn.clicked.connect(self._copy_python_code)

        save_py_btn = QPushButton("Save as .py Script...")
        save_py_btn.clicked.connect(self._save_python_script)

        save_ipynb_btn = QPushButton("Save as Jupyter Notebook (.ipynb)...")
        save_ipynb_btn.setObjectName("accentBtn")
        save_ipynb_btn.clicked.connect(self._save_jupyter_notebook)

        refresh_btn = QPushButton("Refresh Code")
        refresh_btn.clicked.connect(self.refresh_code)

        code_btn_row.addWidget(copy_btn)
        code_btn_row.addWidget(save_py_btn)
        code_btn_row.addWidget(save_ipynb_btn)
        code_btn_row.addWidget(refresh_btn)
        code_btn_row.addStretch()
        main_layout.addLayout(code_btn_row)

        # Action Buttons Row 2: Figure Image & Project Session
        export_btn_row = QHBoxLayout()

        self.copy_svg_btn = QPushButton("📋 Copy as SVG")
        self.copy_svg_btn.setToolTip("Copy vector SVG to clipboard (transparent=True)")
        self.copy_svg_btn.clicked.connect(self._copy_as_svg)

        self.copy_png_btn = QPushButton("📋 Copy as PNG")
        self.copy_png_btn.setToolTip("Copy high-resolution PNG image to clipboard")
        self.copy_png_btn.clicked.connect(self._copy_as_png)

        export_img_btn = QPushButton("Export Figure (PDF, SVG, PNG)...")
        export_img_btn.clicked.connect(self._export_figure_image)

        save_session_btn = QPushButton("💾 Save Project State (.plotproj)...")
        save_session_btn.setToolTip("Save complete workspace with all datasets, formulas, and plot configurations")
        save_session_btn.clicked.connect(self._save_session)

        load_session_btn = QPushButton("📂 Open Project State (.plotproj)...")
        load_session_btn.setToolTip("Open a saved project state file (.plotproj / .json)")
        load_session_btn.clicked.connect(self._load_session)

        export_btn_row.addWidget(self.copy_svg_btn)
        export_btn_row.addWidget(self.copy_png_btn)
        export_btn_row.addWidget(export_img_btn)
        export_btn_row.addWidget(save_session_btn)
        export_btn_row.addWidget(load_session_btn)
        export_btn_row.addStretch()
        main_layout.addLayout(export_btn_row)

        # Code Views Tab Widget
        self.views_tab = QTabWidget()

        # Tab A: Python Script View
        py_widget = QWidget()
        py_layout = QVBoxLayout(py_widget)
        py_layout.setContentsMargins(0, 4, 0, 0)
        self.code_edit = QPlainTextEdit()
        self.code_edit.setReadOnly(True)
        self.code_edit.setFont(QFont("Consolas", 10))
        py_layout.addWidget(self.code_edit)
        self.views_tab.addTab(py_widget, "Python (.py) Code")

        # Tab B: Notebook JSON Structure
        nb_widget = QWidget()
        nb_layout = QVBoxLayout(nb_widget)
        nb_layout.setContentsMargins(0, 4, 0, 0)
        self.nb_edit = QPlainTextEdit()
        self.nb_edit.setReadOnly(True)
        self.nb_edit.setFont(QFont("Consolas", 10))
        nb_layout.addWidget(self.nb_edit)
        self.views_tab.addTab(nb_widget, "Jupyter (.ipynb) Structure")

        main_layout.addWidget(self.views_tab)

    def refresh_code(self):
        """Regenerates Python and Jupyter code from current state."""
        try:
            py_code = generate_python_code(self.fig_config, self.datasets)
            self.code_edit.setPlainText(py_code)

            nb_str = generate_jupyter_notebook(self.fig_config, self.datasets)
            self.nb_edit.setPlainText(nb_str)
        except Exception as e:
            self.code_edit.setPlainText(f"# Error generating code: {e}")

    def _copy_as_svg(self):
        parent_window = self.window()
        if hasattr(parent_window, "plot_canvas"):
            success = parent_window.plot_canvas.copy_as_svg()
            if success:
                orig_text = "📋 Copy as SVG"
                self.copy_svg_btn.setText("✓ Copied SVG!")
                QTimer.singleShot(1500, lambda: self.copy_svg_btn.setText(orig_text))

    def _copy_as_png(self):
        parent_window = self.window()
        if hasattr(parent_window, "plot_canvas"):
            success = parent_window.plot_canvas.copy_as_png()
            if success:
                orig_text = "📋 Copy as PNG"
                self.copy_png_btn.setText("✓ Copied PNG!")
                QTimer.singleShot(1500, lambda: self.copy_png_btn.setText(orig_text))

    def _copy_python_code(self):
        code = self.code_edit.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        QMessageBox.information(self, "Copied", "Python code successfully copied to clipboard!")

    def _save_python_script(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Python Script", "plot_script.py", "Python Scripts (*.py)"
        )
        if not file_path:
            return

        try:
            code = generate_python_code(self.fig_config, self.datasets)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            QMessageBox.information(self, "Saved", f"Python script saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save script:\n{e}")

    def _save_jupyter_notebook(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Jupyter Notebook", "plot_notebook.ipynb", "Jupyter Notebooks (*.ipynb)"
        )
        if not file_path:
            return

        try:
            nb_str = generate_jupyter_notebook(self.fig_config, self.datasets)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(nb_str)
            QMessageBox.information(self, "Saved", f"Jupyter Notebook saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save notebook:\n{e}")

    def _export_figure_image(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export High-Resolution Figure",
            "figure.pdf",
            "PDF Document (*.pdf);;PNG Image (*.png);;SVG Vector (*.svg);;EPS Vector (*.eps);;TIFF Image (*.tiff)"
        )
        if not file_path:
            return

        try:
            # We can request parent window or canvas to save
            parent_window = self.window()
            if hasattr(parent_window, "plot_canvas"):
                parent_window.plot_canvas.figure.savefig(
                    file_path,
                    dpi=self.fig_config.dpi,
                    bbox_inches="tight" if self.fig_config.tight_layout else None
                )
                QMessageBox.information(self, "Exported", f"Figure exported successfully to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export figure:\n{e}")

    def _save_session(self):
        parent = self.window()
        if hasattr(parent, "save_project_state"):
            parent.save_project_state()
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project State", "project.plotproj", PROJECT_FILE_FILTER
        )
        if not file_path:
            return

        try:
            save_project_to_file(file_path, self.fig_config, self.datasets)
            QMessageBox.information(self, "Project Saved", f"Project state saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{e}")

    def _load_session(self):
        parent = self.window()
        if hasattr(parent, "open_project_state"):
            parent.open_project_state()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project State", "", PROJECT_FILE_FILTER
        )
        if not file_path:
            return

        try:
            new_fig, new_datasets, _ = load_project_from_file(file_path)
            self.datasets.clear()
            self.datasets.update(new_datasets)
            self.fig_config.__dict__.update(new_fig.__dict__)
            self.session_loaded.emit()
            self.refresh_code()
            QMessageBox.information(self, "Project Loaded", "Project state successfully restored!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{e}")
