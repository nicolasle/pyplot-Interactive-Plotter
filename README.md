# Pyplot Interactive Plotter (Scientific Suite)

An interactive, multi-tab desktop application built with **PySide6** and **Matplotlib** for scientific data exploration, publication-quality figure design, and **100% standalone Python (`.py`) & Jupyter Notebook (`.ipynb`) code generation**.

---

## Key Features

### 1. Persistent Live Plot Preview (Visible on All Tabs)
* The Matplotlib figure preview canvas stays visible on the right side across all workflow tabs.
* **Instant visual feedback**: Changing a color, axis scale, line width, grid, or layout immediately redraws the figure in real-time.
* **Interactive Navigation Toolbar**: Native Matplotlib zoom, pan, home, back/forward, and export tools.
* **Hover coordinate tracking**: Live readout of data coordinates $(x, y)$ under the cursor.
* **Click-to-Inspect**: Clicking any subplot directly on the live figure instantly focuses that subplot in the configurator tab.

---

### 2. "Ultra-Smart" Data Importer (Auto-Interpreted + Manual Override)
Handles real-world messy experimental data:
* **Automatic Sniffer**:
  * Auto-detects delimiters: Whitespace / Multi-space (`\s+`), Tab (`\t`), Comma (`,`), Semicolon (`;`), Pipe (`|`).
  * Auto-detects header presence vs no-header numeric tables.
  * Auto-detects and skips comment preambles (`#`, `%`, `//`, `;`).
  * Auto-extracts column names even if embedded inside `#` comment lines.
  * Auto-detects European decimal commas (`1,234`) vs standard dots (`1.234`).
  * Supports 1D tabular data and 2D matrix grids (for heatmaps/imshow).
* **Live Interactive Correction Dialog**:
  * Side-by-side view: **Raw file text** with line numbers on the left, **Live parsed table** at the bottom.
  * Real-time controls: change delimiter, skip rows, toggle headers, switch decimal mark, or toggle 2D grid. The preview table updates dynamically with every keystroke or click!
* **Inline Column Math & Transformation**:
  * Apply formulas on existing columns without altering raw files (e.g., `col * 1e3`, `np.log10(col)`, `col - col.min()`, `np.gradient(col)`).

---

### 3. Plot Manager & Journal Publication Presets
* **One-Click Paper Ready Presets**:
  * *Nature Single Column* ($89\text{ mm}$, $7\text{ pt}$ font, $300\text{ DPI}$, inward ticks)
  * *Nature Double Column* ($183\text{ mm}$, $8\text{ pt}$ font, $300\text{ DPI}$)
  * *APS Physical Review Single Column* ($86\text{ mm}$, $8.5\text{ pt}$ serif font)
  * *APS Physical Review Double Column* ($178\text{ mm}$)
  * *IEEE Transactions Single Column* ($89\text{ mm} / 3.5\text{ in}$)
  * *Elsevier 1.5-Column* ($140\text{ mm}$)
  * *Square Scientific* ($100\times 100\text{ mm}$)
  * *16:9 Presentation Slide* ($22\times 12.5\text{ cm}$, $13\text{ pt}$ font)
* **Custom Layouts**:
  * $N \times M$ grid of subplots.
  * `sharex` and `sharey` toggles (`none`, `all`, `row`, `col`).
  * Physical dimensions configured in **centimeters** or **inches**.
  * DPI control (72 to 1200 DPI).
  * Matplotlib style sheets (`seaborn-v0_8-ticks`, `classic`, `ggplot`, `default`).
  * Full LaTeX rendering toggle (`text.usetex = True`).

---

### 4. Single Plot Configurator (1D & 2D Channels)
* **Subplot Selector**: Select via dropdown or by clicking the subplot on the canvas.
* **1D Plot Types**: Line, Scatter, Line + Scatter, Errorbars ($y_{\text{err}}, x_{\text{err}}$), Step, Fill-between (confidence bands), Bar.
* **2D Map Types**: Heatmaps (`imshow`), Contour, Filled Contour (`contourf`) with customizable colormaps (`viridis`, `plasma`, `coolwarm`, `jet`, etc.), colorbar toggles, and colorbar labels.
* **Dual Axis (TwinX)**: Assign any channel to a secondary $Y$-axis (`twinx()`) with independent scale, label, and limits.
* **Reference Lines & Spans**: Add horizontal/vertical threshold lines (`axhline`, `axvline`) or highlighted regions (`axhspan`, `axvspan`).
* **Axis Customization**:
  * LaTeX-compatible titles, X-labels, and Y-labels (e.g. `$\lambda\ (\mathrm{nm})$`, `$I_{\mathrm{drain}}\ (\mu\mathrm{A})$`).
  * Linear, Log10, and Symlog scales.
  * Ticks: Inward, Outward, In-Out, Top & Right tick controls.
  * Major and minor gridlines.
  * Legends: Location, frame on/off, multi-column layout.

---

### 5. Template & Batch Mode
* **Save / Load Style Templates**: Save your figure styling as a lightweight `.json` template and reuse it across multiple projects.
* **Automated Batch Export**: Select a folder of measurement files, apply the current layout/styling template, and automatically generate high-resolution figures (PDF, PNG, SVG) or standalone Python scripts for all files.

---

### 6. Code & Export Hub
* **Real-time Standalone Python Script**: Clean, PEP-8 compliant code using standard idioms (`fig, axes = plt.subplots(...)`). Completely standalone with no proprietary dependencies—anyone with standard Python + Matplotlib + Pandas can run it!
* **Jupyter Notebook (`.ipynb`) Generator**: Formatted notebook cells separated into imports, styling, data loading, and figure generation.
* **Direct High-Res Graphic Export**: PDF, SVG, EPS, PNG, and TIFF with customizable DPI and tight bounding box.
* **Project Session Save/Load**: Save entire project state to `.plotproj` / `.json` to resume work anytime.

---

## Quick Start

### Run the Application:
```bash
python app.py
```

### Sample Data Included:
Test files are pre-packaged in the `sample_data/` folder:
* `spectrum_with_comments.txt` – Spectrometer file with `#` comments, metadata preamble, and embedded column headers.
* `messy_whitespace_no_header.dat` – Raw floating-point table with variable whitespace delimiters and no header.
* `european_decimals.tsv` – Tab-separated file using European decimal commas (`1,05`).
* `surface_map_2d.txt` – $30\times 30$ floating-point grid matrix for 2D maps / heatmaps.

---

## Project Structure

```
Interactive plotter/
├── app.py                      # Main desktop application launcher
├── README.md                   # Documentation
├── core/
│   ├── models.py               # Data models (FigureConfig, AxisConfig, TraceConfig, Dataset)
│   ├── data_loader.py          # Ultra-smart data sniffer & parser (1D & 2D)
│   ├── code_generator.py       # Standalone Python script & Jupyter Notebook generator
│   └── presets.py              # Journal publication presets (Nature, APS, IEEE, etc.)
├── gui/
│   ├── main_window.py          # Main PySide6 window with persistent live plot splitter
│   ├── plot_canvas.py          # Embedded Matplotlib canvas with click-to-select
│   ├── smart_import_dialog.py  # Interactive import wizard with raw & live parsed preview
│   ├── styles.py               # Modern dark scientific UI stylesheet
│   └── tabs/
│       ├── data_tab.py         # Tab 1: Datasets, smart import, column math
│       ├── plot_tab.py         # Tab 2: Layout, dimensions, publication presets
│       ├── configurator_tab.py # Tab 3: Subplot selector, 1D/2D channels, axes styling
│       ├── template_tab.py     # Tab 4: Templates & batch export
│       └── export_tab.py       # Tab 5: Code & Export hub (.py, .ipynb, PDF/SVG)
└── sample_data/                # Sample measurement data files
```
