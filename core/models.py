"""
Core Data Models for Interactive Plotter
Defines the schema for figures, axes, traces, and datasets.
Includes serialization (to_dict/from_dict) for project saving/loading.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
import uuid
import pandas as pd
import numpy as np


@dataclass
class TraceConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Trace"
    dataset_id: str = ""
    plot_type: str = "line"  # line, scatter, line+scatter, errorbar, bar, step, fill_between, imshow, pcolormesh, contour, contourf
    
    # Column mapping for 1D
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    yerr_col: Optional[str] = None
    xerr_col: Optional[str] = None
    
    # 2D Grid mapping
    z_col: Optional[str] = None  # for 3-column XYZ or 2D matrix
    
    # Styling properties
    color: str = "auto"  # auto or hex '#1f77b4'
    linestyle: str = "-"  # '-', '--', '-.', ':', 'None'
    linewidth: float = 1.5
    marker: str = "None"  # 'None', 'o', 's', '^', 'v', 'D', 'x', '+', '*', 'p'
    markersize: float = 6.0
    markerfacecolor: str = "auto"
    markeredgecolor: str = "auto"
    alpha: float = 1.0
    label: str = ""
    visible: bool = True
    twin_axis: str = "primary"  # 'primary' or 'twinx'
    zorder: int = 2

    # 2D specific properties
    cmap: str = "viridis"
    vmin: Optional[float] = None
    vmax: Optional[float] = None
    colorbar: bool = True
    colorbar_label: str = ""
    interpolation: str = "nearest"
    contour_levels: int = 10
    aspect: str = "equal"  # 'equal', 'auto', 'scaled'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ReferenceLineConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "hline"  # 'hline', 'vline', 'hspan', 'vspan'
    val1: float = 0.0
    val2: float = 1.0  # used for span (start, end)
    color: str = "#ef4444"
    linestyle: str = "--"
    linewidth: float = 1.2
    alpha: float = 0.8
    label: str = "Baseline"
    visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReferenceLineConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AxisConfig:
    row: int = 0
    col: int = 0
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    y2label: str = ""  # For twinx
    
    xscale: str = "linear"  # 'linear', 'log', 'symlog'
    yscale: str = "linear"  # 'linear', 'log', 'symlog'
    y2scale: str = "linear"
    aspect: str = "auto"    # 'auto', 'equal', 'scaled'
    
    xlim_min: Optional[float] = None
    xlim_max: Optional[float] = None
    ylim_min: Optional[float] = None
    ylim_max: Optional[float] = None
    y2lim_min: Optional[float] = None
    y2lim_max: Optional[float] = None

    grid_major: bool = True
    grid_minor: bool = False
    grid_style: str = "--"
    grid_alpha: float = 0.4
    
    tick_direction: str = "in"  # 'in', 'out', 'inout'
    tick_top: bool = False
    tick_right: bool = False

    xtick_position: str = "bottom"  # 'bottom', 'top', 'both', 'none'
    ytick_position: str = "left"    # 'left', 'right', 'both', 'none'
    show_xticklabels: bool = True
    show_yticklabels: bool = True

    # Panel Label (Publication Tag, e.g. a, b, c...)
    show_panel_label: bool = False
    panel_label: str = ""
    panel_label_loc: str = "top-left"   # 'top-left', 'top-right', 'bottom-left', 'bottom-right'
    panel_label_square: bool = True     # True: black square with white letter; False: plain black font
    panel_label_size: Optional[float] = None        # Font size (pt)
    panel_label_box_size: Optional[float] = None    # Square side length in pt (None = auto)
    
    show_legend: bool = True
    legend_loc: str = "best"  # 'best', 'upper right', 'upper left', 'lower left', 'lower right', 'outside right'
    legend_ncol: int = 1
    legend_frame: bool = True
    legend_fontsize: Optional[float] = None

    traces: List[TraceConfig] = field(default_factory=list)
    ref_lines: List[ReferenceLineConfig] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["traces"] = [t.to_dict() for t in self.traces]
        d["ref_lines"] = [r.to_dict() for r in self.ref_lines]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AxisConfig":
        traces_data = data.pop("traces", [])
        ref_lines_data = data.pop("ref_lines", [])
        axis = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        axis.traces = [TraceConfig.from_dict(t) for t in traces_data]
        axis.ref_lines = [ReferenceLineConfig.from_dict(r) for r in ref_lines_data]
        return axis


@dataclass
class FigureConfig:
    nrows: int = 1
    ncols: int = 1
    width_cm: float = 14.0
    height_cm: float = 10.0
    dpi: int = 150
    preset_name: str = "Custom"
    
    sharex: str = "none"  # 'none', 'all', 'row', 'col'
    sharey: str = "none"  # 'none', 'all', 'row', 'col'
    
    style: str = "default"  # 'default', 'seaborn-v0_8-whitegrid', 'seaborn-v0_8-ticks', 'classic'
    font_family: str = "sans-serif"
    font_size: float = 10.0
    usetex: bool = False
    tight_layout: bool = True
    figure_title: str = ""
    
    axes: Dict[Tuple[int, int], AxisConfig] = field(default_factory=dict)

    def __post_init__(self):
        self.ensure_axes_grid()

    def ensure_axes_grid(self):
        """Make sure all (r, c) up to nrows, ncols exist with default panel labels."""
        for r in range(self.nrows):
            for c in range(self.ncols):
                key = (r, c)
                idx = r * self.ncols + c
                default_lbl = chr(ord('a') + idx) if idx < 26 else f"p{idx+1}"
                if key not in self.axes:
                    self.axes[key] = AxisConfig(row=r, col=c, panel_label=default_lbl)
                elif not getattr(self.axes[key], "panel_label", ""):
                    self.axes[key].panel_label = default_lbl

    def reset_default_panel_labels(self):
        """Re-assigns a, b, c, d... to all subplots in current grid order."""
        for r in range(self.nrows):
            for c in range(self.ncols):
                idx = r * self.ncols + c
                self.get_axis(r, c).panel_label = chr(ord('a') + idx) if idx < 26 else f"p{idx+1}"

    def set_all_panel_labels_visible(self, visible: bool):
        """Batch toggle panel labels for all subplots."""
        for r in range(self.nrows):
            for c in range(self.ncols):
                self.get_axis(r, c).show_panel_label = visible

    def set_all_panel_labels_square(self, square: bool):
        """Batch set black square background on all subplots."""
        for r in range(self.nrows):
            for c in range(self.ncols):
                self.get_axis(r, c).panel_label_square = square

    def get_axis(self, r: int, c: int) -> AxisConfig:
        key = (r, c)
        if key not in self.axes:
            self.axes[key] = AxisConfig(row=r, col=c)
        return self.axes[key]

    def rename_column_in_traces(self, dataset_id: str, old_name: str, new_name: str):
        """Update trace column mappings when a dataset column is renamed."""
        for ax in self.axes.values():
            for tr in ax.traces:
                if tr.dataset_id == dataset_id:
                    if tr.x_col == old_name:
                        tr.x_col = new_name
                    if tr.y_col == old_name:
                        tr.y_col = new_name
                    if tr.yerr_col == old_name:
                        tr.yerr_col = new_name
                    if tr.xerr_col == old_name:
                        tr.xerr_col = new_name

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # axes dict tuple keys to string "r,c"
        d["axes"] = {f"{k[0]},{k[1]}": v.to_dict() for k, v in self.axes.items()}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FigureConfig":
        axes_data = data.pop("axes", {})
        fig = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        fig.axes = {}
        for k_str, ax_data in axes_data.items():
            r, c = map(int, k_str.split(","))
            fig.axes[(r, c)] = AxisConfig.from_dict(ax_data)
        fig.ensure_axes_grid()
        return fig


class Dataset:
    """Represents a loaded 1D table or 2D matrix dataset."""
    def __init__(
        self,
        name: str,
        data_type: str = "1d_table",  # '1d_table' or '2d_matrix'
        df: Optional[pd.DataFrame] = None,
        matrix: Optional[np.ndarray] = None,
        filepath: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        dataset_id: Optional[str] = None
    ):
        self.id = dataset_id or str(uuid.uuid4())[:8]
        self.name = name
        self.data_type = data_type
        self.df = df if df is not None else pd.DataFrame()
        self.matrix = matrix
        self.filepath = filepath
        self.meta = meta or {}

    def get_columns(self) -> List[str]:
        if self.data_type == "1d_table" and self.df is not None:
            return list(self.df.columns)
        return []

    def get_shape_str(self) -> str:
        if self.data_type == "1d_table" and self.df is not None:
            return f"{self.df.shape[0]} rows × {self.df.shape[1]} cols"
        elif self.data_type == "2d_matrix" and self.matrix is not None:
            return f"{self.matrix.shape[0]} × {self.matrix.shape[1]} grid"
        return "Empty"
