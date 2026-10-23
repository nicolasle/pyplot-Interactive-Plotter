"""
Plot Canvas Component
Houses the embedded Matplotlib FigureCanvasQTAgg, NavigationToolbar,
and handles interactive mouse click inspection, coordinate tracking,
and robust centered rendering with full styling support.
"""

from typing import Dict, Any, Optional, Tuple
import matplotlib
matplotlib.use("QtAgg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.offsetbox import AnchoredOffsetbox, DrawingArea, TextArea
from matplotlib.patches import Rectangle
from matplotlib.text import Text

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt
import numpy as np
import pandas as pd

from core.models import FigureConfig, AxisConfig, TraceConfig, ReferenceLineConfig, Dataset


class PlotCanvas(QWidget):
    """
    Interactive Matplotlib canvas widget with live redraws,
    click-to-inspect subplot, and coordinate hover tracking.
    """
    axis_selected = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Use constrained layout engine for automatic, perfect centering of subplots and colorbars
        self.figure = Figure(dpi=100)
        self.figure.set_layout_engine("constrained")

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        self.ax_to_coord: Dict[Any, Tuple[int, int]] = {}
        self.colorbars: list = []

        # Coordinate status label
        self.coord_label = QLabel("Hover over a plot to see coordinates")
        self.coord_label.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 2px 8px;")

        # Active subplot indicator
        self.active_ax_label = QLabel("Active Subplot: (0, 0)")
        self.active_ax_label.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 11px; padding: 2px 8px;")

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.toolbar)
        top_bar.addStretch()
        top_bar.addWidget(self.active_ax_label)
        layout.addLayout(top_bar)

        layout.addWidget(self.canvas)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self.coord_label)
        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)

        # Connect events
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion_notify)

    def _find_coord_for_event(self, event) -> Optional[Tuple[int, int]]:
        """Resolve click location to a subplot (row, col)."""
        # 1. Direct match with event.inaxes
        if event.inaxes is not None:
            coord = self.ax_to_coord.get(event.inaxes)
            if coord is not None:
                return coord

        # 2. Match by canvas pixel coordinate (covers titles, labels, ticks, margins)
        if getattr(event, "x", None) is None or getattr(event, "y", None) is None or not self.ax_to_coord:
            return None

        best_coord = None
        min_dist = float("inf")

        for ax, coord in self.ax_to_coord.items():
            try:
                bbox = ax.get_window_extent()
                if bbox.contains(event.x, event.y):
                    return coord

                # Check expanded margins (up to 35% around axes for titles/labels)
                expanded = bbox.expanded(1.35, 1.35)
                if expanded.contains(event.x, event.y):
                    return coord

                # Distance to center
                cx = (bbox.x0 + bbox.x1) / 2.0
                cy = (bbox.y0 + bbox.y1) / 2.0
                dist = (event.x - cx) ** 2 + (event.y - cy) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_coord = coord
            except Exception:
                continue

        return best_coord

    def _on_button_press(self, event):
        """Detect click inside or near an axis and emit signal."""
        coord = self._find_coord_for_event(event)
        if coord is not None:
            r, c = coord
            self.active_ax_label.setText(f"Active Subplot: ({r}, {c})")
            self.axis_selected.emit(r, c)

    def _on_motion_notify(self, event):
        """Track mouse coordinates in data space."""
        if event.inaxes is not None and event.xdata is not None and event.ydata is not None:
            coord = self.ax_to_coord.get(event.inaxes, ("?", "?"))
            self.coord_label.setText(
                f"Subplot {coord} | X: {event.xdata:.4g} | Y: {event.ydata:.4g}"
            )
        else:
            self.coord_label.setText("Hover over a plot to see coordinates")

    def set_active_subplot_label(self, r: int, c: int):
        self.active_ax_label.setText(f"Active Subplot: ({r}, {c})")

    def render(self, fig_config: FigureConfig, datasets: Dict[str, Dataset]):
        """
        Renders the entire figure and its subplots according to FigureConfig.
        Ensures proper centering, styling, colorbars, and reference lines.
        """
        self.figure.clear()
        self.ax_to_coord.clear()
        self.colorbars.clear()

        # Always re-enforce constrained layout engine for flawless centering
        if fig_config.tight_layout:
            self.figure.set_layout_engine("constrained")
        else:
            self.figure.set_layout_engine(None)

        # Style context application so existing figure adopts style colors/spines
        style_name = fig_config.style if (fig_config.style and fig_config.style != "default") else "default"
        
        with mpl.rc_context():
            if style_name != "default":
                try:
                    mpl.style.use(style_name)
                except Exception:
                    pass

            # Typography overrides
            font_size = float(fig_config.font_size or 10.0)
            mpl.rcParams["font.size"] = font_size
            if fig_config.font_family:
                mpl.rcParams["font.family"] = fig_config.font_family
            mpl.rcParams["text.usetex"] = bool(fig_config.usetex)

            # Update figure facecolor to match the style sheet
            facecolor = mpl.rcParams.get("figure.facecolor", "#ffffff")
            edgecolor = mpl.rcParams.get("figure.edgecolor", "#ffffff")
            self.figure.set_facecolor(facecolor)
            self.figure.set_edgecolor(edgecolor)

            # Figure title
            if fig_config.figure_title:
                self.figure.suptitle(fig_config.figure_title, fontsize=font_size + 3, fontweight="bold")

            # Grid creation
            nrows = max(1, fig_config.nrows)
            ncols = max(1, fig_config.ncols)
            sharex_val = fig_config.sharex if fig_config.sharex != "none" else False
            sharey_val = fig_config.sharey if fig_config.sharey != "none" else False

            axes_grid = self.figure.subplots(
                nrows=nrows,
                ncols=ncols,
                sharex=sharex_val,
                sharey=sharey_val,
                squeeze=False
            )

            for r in range(nrows):
                for c in range(ncols):
                    ax = axes_grid[r, c]
                    self.ax_to_coord[ax] = (r, c)
                    ax_cfg = fig_config.get_axis(r, c)

                    # Twin axis if required by any trace
                    has_twinx = any(tr.twin_axis == "twinx" for tr in ax_cfg.traces if tr.visible)
                    ax_twin = ax.twinx() if has_twinx else None
                    if ax_twin:
                        self.ax_to_coord[ax_twin] = (r, c)

                    # 1. Plot Traces
                    for tr_idx, tr in enumerate(ax_cfg.traces):
                        if not tr.visible:
                            continue
                        dataset = datasets.get(tr.dataset_id)
                        if not dataset:
                            continue

                        target_ax = ax_twin if (tr.twin_axis == "twinx" and ax_twin) else ax
                        label_val = tr.label if tr.label else (tr.name or f"Trace {tr_idx+1}")

                        # Safely parse color
                        color_val = None
                        if tr.color and tr.color != "auto":
                            try:
                                mpl.colors.to_rgba(tr.color)
                                color_val = tr.color
                            except ValueError:
                                color_val = None

                        marker_val = None if (not tr.marker or tr.marker == "None") else tr.marker

                        # 1D Traces
                        if tr.plot_type in ["line", "scatter", "line+scatter", "errorbar", "bar", "step", "fill_between"]:
                            df = dataset.df
                            if df is None or df.empty:
                                continue

                            # Resolve Y column
                            if not tr.y_col or tr.y_col not in df.columns:
                                # Fall back to first available numeric column
                                num_cols = list(df.select_dtypes(include=[np.number]).columns)
                                y_col = num_cols[0] if num_cols else df.columns[0]
                            else:
                                y_col = tr.y_col

                            y_data = pd.to_numeric(df[y_col], errors="coerce").fillna(0).to_numpy()

                            # Resolve X column
                            if tr.x_col and tr.x_col in df.columns:
                                x_data = pd.to_numeric(df[tr.x_col], errors="coerce").fillna(0).to_numpy()
                            else:
                                x_data = np.arange(len(y_data))

                            if tr.plot_type == "line":
                                target_ax.plot(
                                    x_data, y_data,
                                    linestyle=tr.linestyle,
                                    linewidth=tr.linewidth,
                                    color=color_val,
                                    marker=marker_val,
                                    markersize=tr.markersize,
                                    alpha=tr.alpha,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "scatter":
                                target_ax.scatter(
                                    x_data, y_data,
                                    s=(tr.markersize)**2,
                                    marker=marker_val or "o",
                                    color=color_val,
                                    alpha=tr.alpha,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "line+scatter":
                                target_ax.plot(
                                    x_data, y_data,
                                    linestyle=tr.linestyle,
                                    linewidth=tr.linewidth,
                                    marker=marker_val or "o",
                                    markersize=tr.markersize,
                                    color=color_val,
                                    alpha=tr.alpha,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "errorbar":
                                yerr_data = df[tr.yerr_col].to_numpy() if tr.yerr_col and tr.yerr_col in df.columns else None
                                xerr_data = df[tr.xerr_col].to_numpy() if tr.xerr_col and tr.xerr_col in df.columns else None
                                target_ax.errorbar(
                                    x_data, y_data,
                                    yerr=yerr_data,
                                    xerr=xerr_data,
                                    linestyle=tr.linestyle,
                                    linewidth=tr.linewidth,
                                    marker=marker_val,
                                    markersize=tr.markersize,
                                    color=color_val,
                                    alpha=tr.alpha,
                                    capsize=3,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "step":
                                target_ax.step(
                                    x_data, y_data,
                                    where="mid",
                                    linewidth=tr.linewidth,
                                    color=color_val,
                                    alpha=tr.alpha,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "fill_between":
                                target_ax.fill_between(
                                    x_data, y_data,
                                    color=color_val,
                                    alpha=tr.alpha * 0.4,
                                    label=label_val,
                                    zorder=tr.zorder
                                )
                            elif tr.plot_type == "bar":
                                target_ax.bar(
                                    x_data, y_data,
                                    color=color_val,
                                    alpha=tr.alpha,
                                    label=label_val,
                                    zorder=tr.zorder
                                )

                        # 2D Traces
                        elif tr.plot_type in ["imshow", "pcolormesh", "contour", "contourf"]:
                            mat = None
                            if dataset.matrix is not None:
                                mat = dataset.matrix
                            elif dataset.df is not None:
                                try:
                                    mat = dataset.df.select_dtypes(include=[np.number]).to_numpy()
                                except Exception:
                                    pass

                            if mat is None or mat.size == 0:
                                continue

                            vmin = tr.vmin
                            vmax = tr.vmax
                            cmap = tr.cmap or "viridis"

                            im = None
                            if tr.plot_type == "imshow":
                                im = target_ax.imshow(
                                    mat,
                                    cmap=cmap,
                                    vmin=vmin,
                                    vmax=vmax,
                                    interpolation=tr.interpolation or "nearest",
                                    origin="lower",
                                    aspect="auto"
                                )
                            elif tr.plot_type == "contour":
                                im = target_ax.contour(mat, levels=tr.contour_levels or 10, cmap=cmap)
                            elif tr.plot_type == "contourf":
                                im = target_ax.contourf(mat, levels=tr.contour_levels or 10, cmap=cmap)

                            if im and tr.colorbar:
                                cbar = self.figure.colorbar(im, ax=target_ax)
                                if tr.colorbar_label:
                                    cbar.set_label(tr.colorbar_label, fontsize=font_size)
                                cbar.ax.tick_params(labelsize=font_size - 1)
                                self.colorbars.append(cbar)
                                self.ax_to_coord[cbar.ax] = (r, c)

                    # 2. Render Reference Lines & Baselines
                    for ref in ax_cfg.ref_lines:
                        if not getattr(ref, "visible", True):
                            continue
                        
                        ref_color = ref.color or "#ef4444"
                        try:
                            mpl.colors.to_rgba(ref_color)
                        except ValueError:
                            ref_color = "#ef4444"

                        lbl = ref.label if ref.label else None

                        if ref.type == "hline":
                            ax.axhline(
                                ref.val1,
                                color=ref_color,
                                linestyle=ref.linestyle or "--",
                                linewidth=ref.linewidth,
                                alpha=ref.alpha,
                                label=lbl
                            )
                        elif ref.type == "vline":
                            ax.axvline(
                                ref.val1,
                                color=ref_color,
                                linestyle=ref.linestyle or "--",
                                linewidth=ref.linewidth,
                                alpha=ref.alpha,
                                label=lbl
                            )
                        elif ref.type == "hspan":
                            ax.axhspan(
                                min(ref.val1, ref.val2),
                                max(ref.val1, ref.val2),
                                color=ref_color,
                                alpha=ref.alpha,
                                label=lbl
                            )
                        elif ref.type == "vspan":
                            ax.axvspan(
                                min(ref.val1, ref.val2),
                                max(ref.val1, ref.val2),
                                color=ref_color,
                                alpha=ref.alpha,
                                label=lbl
                            )

                    # 3. Subplot Titles & Labels
                    if ax_cfg.title:
                        ax.set_title(ax_cfg.title, fontsize=font_size + 1, fontweight="semibold")
                    if ax_cfg.xlabel:
                        ax.set_xlabel(ax_cfg.xlabel, fontsize=font_size)
                    if ax_cfg.ylabel:
                        ax.set_ylabel(ax_cfg.ylabel, fontsize=font_size)
                    if ax_twin and ax_cfg.y2label:
                        ax_twin.set_ylabel(ax_cfg.y2label, fontsize=font_size)

                    # 4. Scales
                    if ax_cfg.xscale == "log":
                        try:
                            ax.set_xscale("log", nonpositive="clip")
                        except Exception:
                            ax.set_xscale("log")
                    elif ax_cfg.xscale:
                        ax.set_xscale(ax_cfg.xscale)

                    if ax_cfg.yscale == "log":
                        try:
                            ax.set_yscale("log", nonpositive="clip")
                        except Exception:
                            ax.set_yscale("log")
                    elif ax_cfg.yscale:
                        ax.set_yscale(ax_cfg.yscale)

                    if ax_twin and ax_cfg.y2scale:
                        if ax_cfg.y2scale == "log":
                            try:
                                ax_twin.set_yscale("log", nonpositive="clip")
                            except Exception:
                                ax_twin.set_yscale("log")
                        else:
                            ax_twin.set_yscale(ax_cfg.y2scale)

                    # 5. Limits
                    if ax_cfg.xlim_min is not None and ax_cfg.xlim_max is not None:
                        if ax_cfg.xlim_min < ax_cfg.xlim_max:
                            ax.set_xlim(ax_cfg.xlim_min, ax_cfg.xlim_max)
                    elif ax_cfg.xlim_min is not None:
                        ax.set_xlim(left=ax_cfg.xlim_min)
                    elif ax_cfg.xlim_max is not None:
                        ax.set_xlim(right=ax_cfg.xlim_max)

                    if ax_cfg.ylim_min is not None and ax_cfg.ylim_max is not None:
                        if ax_cfg.ylim_min < ax_cfg.ylim_max:
                            ax.set_ylim(ax_cfg.ylim_min, ax_cfg.ylim_max)
                    elif ax_cfg.ylim_min is not None:
                        ax.set_ylim(bottom=ax_cfg.ylim_min)
                    elif ax_cfg.ylim_max is not None:
                        ax.set_ylim(top=ax_cfg.ylim_max)

                    if ax_twin:
                        if ax_cfg.y2lim_min is not None and ax_cfg.y2lim_max is not None:
                            if ax_cfg.y2lim_min < ax_cfg.y2lim_max:
                                ax_twin.set_ylim(ax_cfg.y2lim_min, ax_cfg.y2lim_max)
                        elif ax_cfg.y2lim_min is not None:
                            ax_twin.set_ylim(bottom=ax_cfg.y2lim_min)
                        elif ax_cfg.y2lim_max is not None:
                            ax_twin.set_ylim(top=ax_cfg.y2lim_max)

                    # 6. Gridlines
                    if ax_cfg.grid_major:
                        ax.grid(True, which="major", linestyle=ax_cfg.grid_style, alpha=ax_cfg.grid_alpha)
                    else:
                        ax.grid(False, which="major")
                    if ax_cfg.grid_minor:
                        ax.minorticks_on()
                        ax.grid(True, which="minor", linestyle=":", alpha=max(0.1, ax_cfg.grid_alpha / 2))
                    else:
                        ax.grid(False, which="minor")

                    # 7. Ticks & Typography
                    ax.tick_params(
                        direction=ax_cfg.tick_direction,
                        labelsize=font_size
                    )

                    # X-Ticks visibility and position
                    x_pos = getattr(ax_cfg, "xtick_position", "bottom")
                    show_x_labels = getattr(ax_cfg, "show_xticklabels", True)

                    if x_pos == "none":
                        ax.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False, labeltop=False)
                    elif x_pos == "top":
                        ax.tick_params(axis="x", which="both", bottom=False, top=True, labelbottom=False, labeltop=show_x_labels)
                    elif x_pos == "both":
                        ax.tick_params(axis="x", which="both", bottom=True, top=True, labelbottom=show_x_labels, labeltop=False)
                    else:  # "bottom"
                        ax.tick_params(axis="x", which="both", bottom=True, top=ax_cfg.tick_top, labelbottom=show_x_labels, labeltop=False)

                    # Y-Ticks visibility and position
                    y_pos = getattr(ax_cfg, "ytick_position", "left")
                    show_y_labels = getattr(ax_cfg, "show_yticklabels", True)

                    if y_pos == "none":
                        ax.tick_params(axis="y", which="both", left=False, right=False, labelleft=False, labelright=False)
                    elif y_pos == "right":
                        ax.tick_params(axis="y", which="both", left=False, right=True, labelleft=False, labelright=show_y_labels)
                    elif y_pos == "both":
                        ax.tick_params(axis="y", which="both", left=True, right=True, labelleft=show_y_labels, labelright=False)
                    else:  # "left"
                        ax.tick_params(axis="y", which="both", left=True, right=ax_cfg.tick_right, labelleft=show_y_labels, labelright=False)

                    if ax_twin:
                        ax_twin.tick_params(
                            direction=ax_cfg.tick_direction,
                            labelsize=font_size
                        )

                    # 8. Legend
                    if ax_cfg.show_legend:
                        handles, labels = ax.get_legend_handles_labels()
                        if ax_twin:
                            h2, l2 = ax_twin.get_legend_handles_labels()
                            handles += h2
                            labels += l2
                        if handles:
                            ax.legend(
                                handles, labels,
                                loc=ax_cfg.legend_loc or "best",
                                ncol=ax_cfg.legend_ncol or 1,
                                frameon=ax_cfg.legend_frame,
                                fontsize=font_size - 1
                            )

                    # 9. Panel Label (Publication Tag, e.g. a, b, c...)
                    if getattr(ax_cfg, "show_panel_label", False) and ax_cfg.panel_label:
                        lbl = str(ax_cfg.panel_label).strip()
                        loc = getattr(ax_cfg, "panel_label_loc", "top-left")
                        use_square = getattr(ax_cfg, "panel_label_square", True)
                        label_size = ax_cfg.panel_label_size if ax_cfg.panel_label_size is not None else (font_size + 1)

                        loc_map = {
                            "top-left": "upper left",
                            "top-right": "upper right",
                            "bottom-left": "lower left",
                            "bottom-right": "lower right",
                        }
                        loc_str = loc_map.get(loc, "upper left")

                        if use_square:
                            # Rigorously square box perfectly flush against the axes border
                            custom_box = getattr(ax_cfg, "panel_label_box_size", None)
                            if custom_box is not None and custom_box > 0:
                                side_pt = float(custom_box)
                            else:
                                if len(lbl) > 1:
                                    side_pt = round(max(label_size * (1.1 + 0.65 * len(lbl)), 18.0), 1)
                                else:
                                    side_pt = round(max(label_size * 1.75, 18.0), 1)

                            da = DrawingArea(side_pt, side_pt, 0, 0)
                            rect = Rectangle((0, 0), side_pt, side_pt, facecolor="black", edgecolor="black", linewidth=0)
                            da.add_artist(rect)
                            txt = Text(
                                side_pt / 2.0, side_pt / 2.0, lbl,
                                color="white", fontsize=label_size, fontweight="bold",
                                va="center", ha="center"
                            )
                            da.add_artist(txt)

                            box = AnchoredOffsetbox(loc=loc_str, pad=0.0, borderpad=0.0, child=da, frameon=False)
                            box.set_zorder(100)
                            ax.add_artist(box)
                        else:
                            # Font in plain black without square
                            ta = TextArea(
                                lbl,
                                textprops=dict(color="black", fontweight="bold", fontsize=label_size)
                            )
                            box = AnchoredOffsetbox(loc=loc_str, pad=0.0, borderpad=0.35, child=ta, frameon=False)
                            box.set_zorder(100)
                            ax.add_artist(box)

        self.canvas.draw_idle()
