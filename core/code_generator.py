"""
Code Generator Engine
Generates clean, idiomatic, reproducible Python scripts (.py)
and Jupyter Notebooks (.ipynb) directly from the current FigureConfig and Datasets.
"""

import json
from typing import Dict, Any, Optional
import nbformat as nbf
from core.models import FigureConfig, AxisConfig, TraceConfig, Dataset


def generate_python_code(
    fig_config: FigureConfig,
    datasets: Dict[str, Dataset],
    output_fig_name: Optional[str] = "figure.pdf"
) -> str:
    """
    Generates a standalone, executable Python script reproducing the figure.
    """
    lines = []
    lines.append('"""')
    lines.append('Figure Generation Script')
    lines.append('Generated automatically by Pyplot Interactive Plotter')
    lines.append('"""')
    lines.append('')
    lines.append('import matplotlib.pyplot as plt')
    lines.append('import numpy as np')
    lines.append('import pandas as pd')
    lines.append('from matplotlib.offsetbox import AnchoredOffsetbox, DrawingArea, TextArea')
    lines.append('from matplotlib.patches import Rectangle')
    lines.append('from matplotlib.text import Text')
    lines.append('')
    lines.append('# Helper functions for decibel operations')
    lines.append('def dedB(x, mode=20):')
    lines.append('    """Revert decibels: 10 ** (x / 20) for amplitude or 10 ** (x / 10) for power."""')
    lines.append('    return 10.0 ** (np.asarray(x, dtype=float) / float(mode))')
    lines.append('')
    lines.append('def dedB_power(x):')
    lines.append('    """Revert decibels for power/intensity: 10 ** (x / 10)."""')
    lines.append('    return 10.0 ** (np.asarray(x, dtype=float) / 10.0)')
    lines.append('')
    lines.append('def to_dB(x, mode=20):')
    lines.append('    return float(mode) * np.log10(np.abs(np.asarray(x, dtype=float)) + 1e-18)')
    lines.append('')

    # Styling block
    lines.append('# ==========================================')
    lines.append('# 1. FIGURE STYLE & CONFIGURATION')
    lines.append('# ==========================================')
    if fig_config.style and fig_config.style != "default":
        lines.append(f'plt.style.use("{fig_config.style}")')
    
    rc_params = []
    if fig_config.font_size:
        rc_params.append(f"'font.size': {fig_config.font_size}")
    if fig_config.font_family:
        rc_params.append(f"'font.family': '{fig_config.font_family}'")
    if fig_config.usetex:
        rc_params.append("'text.usetex': True")
    
    if rc_params:
        lines.append('plt.rcParams.update({')
        for p in rc_params:
            lines.append(f'    {p},')
        lines.append('})')
    lines.append('')

    # Dataset loading block
    lines.append('# ==========================================')
    lines.append('# 2. DATA LOADING')
    lines.append('# ==========================================')
    
    # Identify which datasets are actually used in traces
    used_dataset_ids = set()
    for ax_cfg in fig_config.axes.values():
        for tr in ax_cfg.traces:
            if tr.dataset_id:
                used_dataset_ids.add(tr.dataset_id)

    if not used_dataset_ids and datasets:
        used_dataset_ids = set(datasets.keys())

    dataset_var_map = {}
    for idx, d_id in enumerate(used_dataset_ids):
        d = datasets.get(d_id)
        if not d:
            continue
        var_name = f"df_{idx+1}" if d.data_type == "1d_table" else f"matrix_{idx+1}"
        dataset_var_map[d_id] = var_name
        lines.append(f'# Dataset: {d.name}')
        
        if d.filepath:
            fp = d.filepath.replace('\\', '/')
            if d.data_type == "2d_matrix" and d.filepath.endswith((".npy", ".npz")):
                lines.append(f'{var_name} = np.load(r"{fp}")')
            elif d.data_type == "2d_matrix":
                delim = d.meta.get("delimiter", None)
                if delim == r"\s+":
                    lines.append(f'{var_name} = np.loadtxt(r"{fp}")')
                elif delim:
                    lines.append(f'{var_name} = np.loadtxt(r"{fp}", delimiter="{delim}")')
                else:
                    lines.append(f'{var_name} = np.loadtxt(r"{fp}")')
            else:
                # 1D Table
                sep_str = d.meta.get("delimiter", ",")
                skiprows = d.meta.get("skiprows", 0)
                has_header = d.meta.get("has_header", True)
                comment = d.meta.get("comment", None)
                decimal = d.meta.get("decimal", ".")
                
                header_arg = "0" if has_header else "None"
                args = [f'r"{fp}"', f'sep={repr(sep_str)}', f'skiprows={skiprows}', f'header={header_arg}', f'decimal={repr(decimal)}']
                if comment:
                    args.append(f'comment={repr(comment)}')
                if sep_str in [r"\s+", "whitespace"]:
                    args.append('engine="python"')
                
                lines.append(f'{var_name} = pd.read_csv({", ".join(args)})')
                if not has_header and d.df is not None:
                    col_names = [f"Col {i}" for i in range(d.df.shape[1])]
                    lines.append(f'{var_name}.columns = {col_names}')
        else:
            # Inline mock or fallback
            if d.data_type == "1d_table":
                lines.append(f'# Inline mock data')
                lines.append(f'{var_name} = pd.DataFrame({{')
                for col in d.get_columns()[:3]:
                    sample_vals = list(d.df[col].iloc[:5].values) if d.df is not None and col in d.df else [1, 2, 3]
                    lines.append(f'    "{col}": {sample_vals},')
                lines.append('})')
            else:
                lines.append(f'{var_name} = np.zeros((20, 20))')
        lines.append('')

    # Figure initialization block
    lines.append('# ==========================================')
    lines.append('# 3. PLOT INITIALIZATION')
    lines.append('# ==========================================')
    width_in = fig_config.width_cm / 2.54
    height_in = fig_config.height_cm / 2.54
    lines.append(f'# Figure size: {fig_config.width_cm:.1f} cm x {fig_config.height_cm:.1f} cm ({width_in:.2f} in x {height_in:.2f} in)')
    
    sharex_arg = f', sharex="{fig_config.sharex}"' if fig_config.sharex != "none" else ""
    sharey_arg = f', sharey="{fig_config.sharey}"' if fig_config.sharey != "none" else ""
    
    lines.append(
        f'fig, axes = plt.subplots('
        f'nrows={fig_config.nrows}, ncols={fig_config.ncols}, '
        f'figsize=({width_in:.3f}, {height_in:.3f}), dpi={fig_config.dpi}'
        f'{sharex_arg}{sharey_arg}, squeeze=False)'
    )
    if fig_config.figure_title:
        lines.append(f'fig.suptitle(r"{fig_config.figure_title}")')
    lines.append('')

    # Subplot and channel drawing
    lines.append('# ==========================================')
    lines.append('# 4. SUBPLOTS & TRACES')
    lines.append('# ==========================================')
    
    for r in range(fig_config.nrows):
        for c in range(fig_config.ncols):
            ax_cfg = fig_config.get_axis(r, c)
            lines.append(f'# --- Subplot ({r}, {c}) ---')
            lines.append(f'ax = axes[{r}, {c}]')
            
            # Setup twinx if any trace needs it
            has_twinx = any(tr.twin_axis == "twinx" for tr in ax_cfg.traces)
            if has_twinx:
                lines.append('ax_twin = ax.twinx()')

            # Render traces
            for tr in ax_cfg.traces:
                if not tr.visible:
                    continue
                var_name = dataset_var_map.get(tr.dataset_id)
                target_ax = "ax_twin" if tr.twin_axis == "twinx" else "ax"

                # 1D Traces
                if tr.plot_type in ["line", "scatter", "line+scatter", "errorbar", "bar", "step", "fill_between"]:
                    if not var_name or not tr.y_col:
                        continue
                    
                    x_expr = f'{var_name}["{tr.x_col}"]' if tr.x_col else f'range(len({var_name}))'
                    y_expr = f'{var_name}["{tr.y_col}"]'

                    style_kwargs = []
                    if tr.color and tr.color != "auto":
                        style_kwargs.append(f'color="{tr.color}"')
                    if tr.label:
                        style_kwargs.append(f'label=r"{tr.label}"')
                    if tr.alpha < 1.0:
                        style_kwargs.append(f'alpha={tr.alpha}')

                    if tr.plot_type == "line":
                        style_kwargs.append(f'linestyle="{tr.linestyle}"')
                        style_kwargs.append(f'linewidth={tr.linewidth}')
                        if tr.marker and tr.marker != "None":
                            style_kwargs.append(f'marker="{tr.marker}"')
                            style_kwargs.append(f'markersize={tr.markersize}')
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.plot({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "scatter":
                        if tr.marker and tr.marker != "None":
                            style_kwargs.append(f'marker="{tr.marker}"')
                        style_kwargs.append(f's={(tr.markersize)**2:.1f}')
                        if tr.markerfacecolor and tr.markerfacecolor != "auto":
                            style_kwargs.append(f'facecolors="{tr.markerfacecolor}"')
                        if tr.markeredgecolor and tr.markeredgecolor != "auto":
                            style_kwargs.append(f'edgecolors="{tr.markeredgecolor}"')
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.scatter({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "line+scatter":
                        style_kwargs.append(f'linestyle="{tr.linestyle}"')
                        style_kwargs.append(f'linewidth={tr.linewidth}')
                        if tr.marker and tr.marker != "None":
                            style_kwargs.append(f'marker="{tr.marker}"')
                            style_kwargs.append(f'markersize={tr.markersize}')
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.plot({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "errorbar":
                        style_kwargs.append(f'linestyle="{tr.linestyle}"')
                        style_kwargs.append(f'linewidth={tr.linewidth}')
                        if tr.marker and tr.marker != "None":
                            style_kwargs.append(f'marker="{tr.marker}"')
                        style_kwargs.append('capsize=3')
                        if tr.yerr_col:
                            style_kwargs.append(f'yerr={var_name}["{tr.yerr_col}"]')
                        if tr.xerr_col:
                            style_kwargs.append(f'xerr={var_name}["{tr.xerr_col}"]')
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.errorbar({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "step":
                        style_kwargs.append(f'linewidth={tr.linewidth}')
                        style_kwargs.append('where="mid"')
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.step({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "fill_between":
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.fill_between({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                    elif tr.plot_type == "bar":
                        kwargs_str = ", ".join(style_kwargs)
                        lines.append(f'{target_ax}.bar({x_expr}, {y_expr}{", " + kwargs_str if kwargs_str else ""})')

                # 2D Traces
                elif tr.plot_type in ["imshow", "pcolormesh", "contour", "contourf"]:
                    if not var_name:
                        continue
                    
                    # Check if matrix or df
                    mat_expr = f"{var_name}.values" if "df" in var_name else var_name
                    
                    im_kwargs = [f'cmap="{tr.cmap}"']
                    if tr.vmin is not None:
                        im_kwargs.append(f'vmin={tr.vmin}')
                    if tr.vmax is not None:
                        im_kwargs.append(f'vmax={tr.vmax}')

                    if tr.plot_type == "imshow":
                        im_kwargs.append(f'interpolation="{tr.interpolation}"')
                        im_kwargs.append('origin="lower"')
                        im_kwargs.append('aspect="auto"')
                        kwargs_str = ", ".join(im_kwargs)
                        lines.append(f'im = {target_ax}.imshow({mat_expr}, {kwargs_str})')
                    elif tr.plot_type == "contour":
                        im_kwargs.append(f'levels={tr.contour_levels}')
                        kwargs_str = ", ".join(im_kwargs)
                        lines.append(f'im = {target_ax}.contour({mat_expr}, {kwargs_str})')
                    elif tr.plot_type == "contourf":
                        im_kwargs.append(f'levels={tr.contour_levels}')
                        kwargs_str = ", ".join(im_kwargs)
                        lines.append(f'im = {target_ax}.contourf({mat_expr}, {kwargs_str})')

                    if tr.colorbar:
                        cbar_label_arg = f', label=r"{tr.colorbar_label}"' if tr.colorbar_label else ""
                        lines.append(f'cbar = fig.colorbar(im, ax={target_ax}{cbar_label_arg})')

            # Reference Lines & Spans
            for ref in ax_cfg.ref_lines:
                if not getattr(ref, "visible", True):
                    continue
                ref_kwargs = [f'color="{ref.color}"', f'linestyle="{ref.linestyle}"', f'linewidth={ref.linewidth}']
                if ref.alpha < 1.0:
                    ref_kwargs.append(f'alpha={ref.alpha}')
                if ref.label:
                    ref_kwargs.append(f'label=r"{ref.label}"')
                kwargs_str = ", ".join(ref_kwargs)

                if ref.type == "hline":
                    lines.append(f'ax.axhline({ref.val1}, {kwargs_str})')
                elif ref.type == "vline":
                    lines.append(f'ax.axvline({ref.val1}, {kwargs_str})')
                elif ref.type == "hspan":
                    lines.append(f'ax.axhspan({ref.val1}, {ref.val2}, {kwargs_str})')
                elif ref.type == "vspan":
                    lines.append(f'ax.axvspan({ref.val1}, {ref.val2}, {kwargs_str})')

            # Subplot axes styling
            if ax_cfg.title:
                lines.append(f'ax.set_title(r"{ax_cfg.title}")')
            if ax_cfg.xlabel:
                lines.append(f'ax.set_xlabel(r"{ax_cfg.xlabel}")')
            if ax_cfg.ylabel:
                lines.append(f'ax.set_ylabel(r"{ax_cfg.ylabel}")')
            if has_twinx and ax_cfg.y2label:
                lines.append(f'ax_twin.set_ylabel(r"{ax_cfg.y2label}")')

            # Scales
            if ax_cfg.xscale != "linear":
                lines.append(f'ax.set_xscale("{ax_cfg.xscale}")')
            if ax_cfg.yscale != "linear":
                lines.append(f'ax.set_yscale("{ax_cfg.yscale}")')
            if has_twinx and ax_cfg.y2scale != "linear":
                lines.append(f'ax_twin.set_yscale("{ax_cfg.y2scale}")')

            # Limits
            if ax_cfg.xlim_min is not None and ax_cfg.xlim_max is not None:
                lines.append(f'ax.set_xlim({ax_cfg.xlim_min}, {ax_cfg.xlim_max})')
            elif ax_cfg.xlim_min is not None:
                lines.append(f'ax.set_xlim(left={ax_cfg.xlim_min})')
            elif ax_cfg.xlim_max is not None:
                lines.append(f'ax.set_xlim(right={ax_cfg.xlim_max})')

            if ax_cfg.ylim_min is not None and ax_cfg.ylim_max is not None:
                lines.append(f'ax.set_ylim({ax_cfg.ylim_min}, {ax_cfg.ylim_max})')
            elif ax_cfg.ylim_min is not None:
                lines.append(f'ax.set_ylim(bottom={ax_cfg.ylim_min})')
            elif ax_cfg.ylim_max is not None:
                lines.append(f'ax.set_ylim(top={ax_cfg.ylim_max})')

            if has_twinx and ax_cfg.y2lim_min is not None and ax_cfg.y2lim_max is not None:
                lines.append(f'ax_twin.set_ylim({ax_cfg.y2lim_min}, {ax_cfg.y2lim_max})')

            # Grids
            if ax_cfg.grid_major:
                lines.append(f'ax.grid(True, which="major", linestyle="{ax_cfg.grid_style}", alpha={ax_cfg.grid_alpha})')
            if ax_cfg.grid_minor:
                lines.append('ax.minorticks_on()')
                lines.append(f'ax.grid(True, which="minor", linestyle=":", alpha={max(0.1, ax_cfg.grid_alpha/2):.2f})')

            # Ticks direction & position
            lines.append(f'ax.tick_params(direction="{ax_cfg.tick_direction}")')

            x_pos = getattr(ax_cfg, "xtick_position", "bottom")
            show_x_labels = getattr(ax_cfg, "show_xticklabels", True)
            if x_pos == "none":
                lines.append('ax.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False, labeltop=False)')
            elif x_pos == "top":
                lines.append(f'ax.tick_params(axis="x", which="both", bottom=False, top=True, labelbottom=False, labeltop={show_x_labels})')
            elif x_pos == "both":
                lines.append(f'ax.tick_params(axis="x", which="both", bottom=True, top=True, labelbottom={show_x_labels}, labeltop=False)')
            else:  # "bottom"
                lines.append(f'ax.tick_params(axis="x", which="both", bottom=True, top=False, labelbottom={show_x_labels}, labeltop=False)')

            y_pos = getattr(ax_cfg, "ytick_position", "left")
            show_y_labels = getattr(ax_cfg, "show_yticklabels", True)
            if y_pos == "none":
                lines.append('ax.tick_params(axis="y", which="both", left=False, right=False, labelleft=False, labelright=False)')
            elif y_pos == "right":
                lines.append(f'ax.tick_params(axis="y", which="both", left=False, right=True, labelleft=False, labelright={show_y_labels})')
            elif y_pos == "both":
                lines.append(f'ax.tick_params(axis="y", which="both", left=True, right=True, labelleft={show_y_labels}, labelright=False)')
            else:  # "left"
                lines.append(f'ax.tick_params(axis="y", which="both", left=True, right=False, labelleft={show_y_labels}, labelright=False)')

            # Legend
            if ax_cfg.show_legend:
                loc_arg = f'loc="{ax_cfg.legend_loc}"' if ax_cfg.legend_loc != "best" else 'loc="best"'
                lines.append(f'ax.legend({loc_arg}, frameon={ax_cfg.legend_frame}, ncol={ax_cfg.legend_ncol})')

            # Panel Label (Publication Tag, e.g. a, b, c...)
            if getattr(ax_cfg, "show_panel_label", False) and ax_cfg.panel_label:
                lbl = str(ax_cfg.panel_label).strip()
                loc = getattr(ax_cfg, "panel_label_loc", "top-left")
                use_sq = getattr(ax_cfg, "panel_label_square", True)
                lbl_size = ax_cfg.panel_label_size if ax_cfg.panel_label_size is not None else (fig_config.font_size + 1)
                loc_map = {
                    "top-left": "upper left",
                    "top-right": "upper right",
                    "bottom-left": "lower left",
                    "bottom-right": "lower right",
                }
                loc_str = loc_map.get(loc, "upper left")

                if use_sq:
                    custom_box = getattr(ax_cfg, "panel_label_box_size", None)
                    if custom_box is not None and custom_box > 0:
                        side_pt = float(custom_box)
                    else:
                        side_pt = round(lbl_size * 1.30, 1)

                    lines.append('# Panel label: rigorous square flush against the border')
                    lines.append(f'da = DrawingArea({side_pt}, {side_pt}, 0, 0)')
                    lines.append(f'da.add_artist(Rectangle((0, 0), {side_pt}, {side_pt}, facecolor="black", edgecolor="black", linewidth=0))')
                    lines.append(f'da.add_artist(Text({side_pt / 2.0}, {side_pt / 2.0}, "{lbl}", color="white", fontsize={lbl_size}, fontweight="bold", va="center", ha="center"))')
                    lines.append(f'panel_box = AnchoredOffsetbox(loc="{loc_str}", pad=0.0, borderpad=0.0, child=da, frameon=False)')
                    lines.append('panel_box.set_zorder(100)')
                    lines.append('ax.add_artist(panel_box)')
                else:
                    lines.append('# Panel label: plain black font')
                    lines.append(f'ta = TextArea("{lbl}", textprops=dict(color="black", fontweight="bold", fontsize={lbl_size}))')
                    lines.append(f'panel_box = AnchoredOffsetbox(loc="{loc_str}", pad=0.0, borderpad=0.35, child=ta, frameon=False)')
                    lines.append('panel_box.set_zorder(100)')
                    lines.append('ax.add_artist(panel_box)')

            lines.append('')

    # Layout & Show/Save block
    lines.append('# ==========================================')
    lines.append('# 5. RENDER & SAVE')
    lines.append('# ==========================================')
    if fig_config.tight_layout:
        lines.append('plt.tight_layout()')
    
    if output_fig_name:
        lines.append(f'# plt.savefig(r"{output_fig_name}", dpi={fig_config.dpi}, bbox_inches="tight")')
    lines.append('plt.show()')

    return "\n".join(lines)


def generate_jupyter_notebook(
    fig_config: FigureConfig,
    datasets: Dict[str, Dataset],
    output_fig_name: Optional[str] = "figure.pdf"
) -> str:
    """
    Generates a Jupyter Notebook (.ipynb) JSON string with separate cells.
    """
    nb = nbf.v4.new_notebook()
    
    # Title Markdown cell
    md_intro = (
        f"# {fig_config.figure_title or 'Scientific Plot'}\n"
        f"Generated automatically by Pyplot Interactive Plotter.\n\n"
        f"- **Grid layout**: {fig_config.nrows} rows × {fig_config.ncols} cols\n"
        f"- **Dimensions**: {fig_config.width_cm} cm × {fig_config.height_cm} cm\n"
        f"- **DPI**: {fig_config.dpi}\n"
    )
    nb.cells.append(nbf.v4.new_markdown_cell(md_intro))

    # Cell 1: Imports & Styling
    code_cell_1 = (
        "import matplotlib.pyplot as plt\n"
        "import numpy as np\n"
        "import pandas as pd\n\n"
        f"plt.style.use('{fig_config.style}')\n"
        f"plt.rcParams.update({{\n"
        f"    'font.size': {fig_config.font_size},\n"
        f"    'font.family': '{fig_config.font_family}',\n"
        f"    'text.usetex': {fig_config.usetex},\n"
        f"}})"
    )
    nb.cells.append(nbf.v4.new_code_cell(code_cell_1))

    # Full script in Cell 2 or split
    py_code = generate_python_code(fig_config, datasets, output_fig_name)
    # Extract data loading and plotting
    nb.cells.append(nbf.v4.new_markdown_cell("## Data Loading & Plot Generation"))
    nb.cells.append(nbf.v4.new_code_cell(py_code))

    return nbf.writes(nb)
