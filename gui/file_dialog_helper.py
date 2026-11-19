"""
File Dialog Helper Module
Maintains session state for file explorer dialogs:
- Default starting folder is C:\\Users\\Nicolas\\Documents\\Post Doc (with graceful fallback).
- Dynamically updates to the last opened/selected folder during the current application session.
- Seamless drop-in replacement for QFileDialog static methods:
    FileDialogHelper.getOpenFileName(...)
    FileDialogHelper.getOpenFileNames(...)
    FileDialogHelper.getSaveFileName(...)
    FileDialogHelper.getExistingDirectory(...)
"""

import os
from typing import Optional, List, Tuple
from PySide6.QtWidgets import QFileDialog, QWidget

DEFAULT_POST_DOC_DIR = r"C:\Users\Nicolas\Documents\Post Doc"


class FileSessionState:
    _last_dir: str = DEFAULT_POST_DOC_DIR

    @classmethod
    def get_last_dir(cls) -> str:
        """Returns the current session folder, falling back if not found."""
        if os.path.exists(cls._last_dir):
            return cls._last_dir
        # Fallback to user's Documents folder
        user_docs = os.path.expanduser("~/Documents")
        if os.path.exists(user_docs):
            return user_docs
        return os.getcwd()

    @classmethod
    def set_last_dir(cls, path: Optional[str]):
        """Updates the session directory from a selected file path or folder."""
        if not path:
            return
        try:
            abs_path = os.path.abspath(path)
            if os.path.isdir(abs_path):
                cls._last_dir = abs_path
            else:
                parent = os.path.dirname(abs_path)
                if os.path.isdir(parent):
                    cls._last_dir = parent
        except Exception:
            pass

    @classmethod
    def resolve_path(cls, dir_or_file: Optional[str] = "") -> str:
        """
        Resolves the initial directory / filename for QFileDialog.
        - If empty or None: returns get_last_dir()
        - If absolute directory or file path: returns it
        - If relative path / bare filename (e.g. 'figure.pdf'):
          joins it to get_last_dir() so the dialog opens in the session directory with the filename pre-filled.
        """
        base = cls.get_last_dir()
        if not dir_or_file:
            return base

        # Check if already absolute
        if os.path.isabs(dir_or_file):
            return dir_or_file

        return os.path.join(base, dir_or_file)


class FileDialogHelper:
    """
    Drop-in replacement for QFileDialog static methods that preserves
    the session directory across all dialogs in the app session.
    """

    @staticmethod
    def get_last_dir() -> str:
        return FileSessionState.get_last_dir()

    @staticmethod
    def set_last_dir(path: Optional[str]):
        FileSessionState.set_last_dir(path)

    @staticmethod
    def getOpenFileName(
        parent: Optional[QWidget] = None,
        caption: str = "",
        dir: str = "",
        filter: str = "",
        selectedFilter: str = "",
        options: QFileDialog.Option = QFileDialog.Option(0)
    ) -> Tuple[str, str]:
        start_dir = FileSessionState.resolve_path(dir)
        res_file, sel_filter = QFileDialog.getOpenFileName(
            parent, caption, start_dir, filter, selectedFilter, options
        )
        if res_file:
            FileSessionState.set_last_dir(res_file)
        return res_file, sel_filter

    @staticmethod
    def getOpenFileNames(
        parent: Optional[QWidget] = None,
        caption: str = "",
        dir: str = "",
        filter: str = "",
        selectedFilter: str = "",
        options: QFileDialog.Option = QFileDialog.Option(0)
    ) -> Tuple[List[str], str]:
        start_dir = FileSessionState.resolve_path(dir)
        res_files, sel_filter = QFileDialog.getOpenFileNames(
            parent, caption, start_dir, filter, selectedFilter, options
        )
        if res_files:
            FileSessionState.set_last_dir(res_files[0])
        return res_files, sel_filter

    @staticmethod
    def getSaveFileName(
        parent: Optional[QWidget] = None,
        caption: str = "",
        dir: str = "",
        filter: str = "",
        selectedFilter: str = "",
        options: QFileDialog.Option = QFileDialog.Option(0)
    ) -> Tuple[str, str]:
        start_dir = FileSessionState.resolve_path(dir)
        res_file, sel_filter = QFileDialog.getSaveFileName(
            parent, caption, start_dir, filter, selectedFilter, options
        )
        if res_file:
            FileSessionState.set_last_dir(res_file)
        return res_file, sel_filter

    @staticmethod
    def getExistingDirectory(
        parent: Optional[QWidget] = None,
        caption: str = "",
        dir: str = "",
        options: QFileDialog.Option = QFileDialog.ShowDirsOnly
    ) -> str:
        start_dir = FileSessionState.resolve_path(dir)
        res_dir = QFileDialog.getExistingDirectory(
            parent, caption, start_dir, options
        )
        if res_dir:
            FileSessionState.set_last_dir(res_dir)
        return res_dir
