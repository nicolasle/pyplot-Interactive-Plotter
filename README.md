# Pyplot Interactive Plotter (Scientific Suite)

An interactive, multi-tab desktop application built with **PySide6** and **Matplotlib** for scientific data exploration, publication-quality figure design, and **100% standalone Python (`.py`) & Jupyter Notebook (`.ipynb`) code generation**.

> [!WARNING]
> **Disclaimer**: This project and its codebase were generated with the assistance of AI. It is provided "as is", without warranty of any kind, express or implied. Use at your own risk.

---

## Tab-by-Tab Capabilities & Functionalities

### Persistent Live Plot Preview (Visible on All Tabs)
The Matplotlib figure canvas remains visible on the right side across all workflow tabs via a draggable splitter:
* **Instant Visual Feedback**: Modifying any trace parameter, axis scale, gridline, or layout immediately redraws the figure in real time.
* **Interactive Navigation Toolbar**: Native Matplotlib tools for rectangular zooming, panning, home view reset, navigation history, and quick-save.
* **Hover Coordinate Tracking**: Live readout of data coordinates $(x, y)$ under the cursor.
* **Click-to-Inspect**: Clicking any subplot directly on the figure automatically selects and focuses that subplot in the Configurator tab.

---

### Tab 1: Data & Ultra-Smart Importer (`Data & Variables`)
* **Multi-Format Experimental Data Support**: Loads `.txt`, `.csv`, `.tsv`, `.dat`, space-delimited tables, and 2D matrix grids.
* **Intelligent File Sniffer**: Automatically detects delimiters (whitespace, tabs, commas, semicolons, pipes), skips arbitrary comment preambles (`#`, `%`, `//`, `;`), extracts embedded column headers, and auto-detects European decimal commas (`1,05` vs `1.05`).
* **Interactive Correction Wizard**: Side-by-side dialog featuring the raw text file with line numbers on the left and a live-parsed DataFrame preview table at the bottom. Adjust skip rows, delimiters, headers, or decimal marks with real-time preview before importing.
* **In-Line Column Transformations**: Apply mathematical operations on columns without modifying raw files:
  * One-click presets: Offset, Scale, $\log_{10}(x)$, $\ln(x)$, Normalize to $[0, 1]$, and Numerical Derivative $\frac{\mathrm{d}y}{\mathrm{d}x}$.
  * Custom Python formulas: e.g. `col * 1e3`, `np.sqrt(x)`, `np.exp(-y / 10)`.
* **Safe Column Renaming**: Renaming a column automatically updates all assigned plot traces across all subplots.

---

### Tab 2: Figure Layout & Publication Manager (`Figure & Layout`)
* **Subplot Grid Layout**: Configure $N \times M$ grids of subplots (up to $8 \times 8$) with synchronized axis scaling (`sharex` and `sharey` modes: `none`, `all`, `row`, `col`).
* **Physical Sizing & Resolution**: Specify exact figure width and height in **centimeters** or **inches**, configure DPI (72 to 1200 DPI), and toggle Matplotlib Constrained/Tight layout auto-padding.
* **1-Click Journal Publication Presets**: Standard publication specifications:
  * *Nature Single Column* ($89\text{ mm}$, $7\text{ pt}$ font, $300\text{ DPI}$)
  * *Nature Double Column* ($183\text{ mm}$, $8\text{ pt}$ font, $300\text{ DPI}$)
  * *APS Physical Review Single Column* ($86\text{ mm}$, $8.5\text{ pt}$ font)
  * *APS Physical Review Double Column* ($178\text{ mm}$)
  * *IEEE Transactions Single Column* ($89\text{ mm} / 3.5\text{ in}$)
  * *Elsevier 1.5-Column* ($140\text{ mm}$)
  * *Square Scientific* ($100\times 100\text{ mm}$)
  * *16:9 Presentation Slide* ($22\times 12.5\text{ cm}$, $13\text{ pt}$ font)
  * *Automatic Custom Fallback*: Manually modifying dimensions automatically updates the preset selector to *Custom*.
* **Global Typography & Style Sheets**:
  * Matplotlib style sheets: `default`, `seaborn-v0_8-ticks`, `seaborn-v0_8-whitegrid`, `classic`, `ggplot`, `bmh`, `tableau-colorblind10`.
  * Font family selection, base font size (pt), and native LaTeX text rendering toggle (`text.usetex = True`).
* **Subplot Panel Label Batch Controls**: One-click buttons to batch enable/disable panel tags (`a`, `b`, `c`...) across all subplots, toggle square backgrounds, and reset lettering.

---

### Tab 3: Subplot & Channel Configurator (`Configurator`)
Allows in-depth customization of the active subplot selected via dropdown or canvas **Click-to-Inspect**:

#### Sub-tab 3.1: Channels / Traces (1D & 2D)
* **1D Plot Types**: Line, Scatter, Line + Scatter, Errorbars with independent $x_{\text{err}}$ and $y_{\text{err}}$ columns, Step, Fill-between (confidence bands / shaded areas), and Bar charts.
* **2D Map & Matrix Types**: Heatmaps (`imshow`), Contour, and Filled Contour (`contourf`) with customizable colormaps (`viridis`, `plasma`, `inferno`, `coolwarm`, `jet`, etc.), colorbar toggles, and colorbar labels.
* **Aspect Ratio Controls**: Set subplot aspect ratio to `auto`, `equal` (1:1 pixel scaling for 2D maps and physical geometries), or `scaled`.
* **Color Selector with Matplotlib `tab10` Palette**:
  * Dedicated quick-select bar containing all 10 standard Matplotlib categorical colors (`tab:blue`, `tab:orange`, `tab:green`, `tab:red`, `tab:purple`, `tab:brown`, `tab:pink`, `tab:gray`, `tab:olive`, `tab:cyan`) with name and hex tooltips.
  * Pre-populated Custom Colors grid and full cross-platform color dialog with HTML Hex and RGB/HSV controls.
* **Dual Y-Axis (TwinX)**: Assign any 1D trace or baseline to a secondary $Y$-axis (`twinx()`) with independent scale and limits. Right-axis tick marks appear automatically for TwinX and cleanly disappear when TwinX is removed.

#### Sub-tab 3.2: Baselines & Reference Lines
* Add horizontal/vertical threshold lines (`axhline`, `axvline`) or highlighted regions/bands (`axhspan`, `axvspan`).
* Attach baselines to either the **Primary Axis** or the **Twin Y Axis (`twinx`)**.
* Customize line styles, colors, line widths, opacity, and legend labels.

#### Sub-tab 3.3: Axes, Limits, Scales, Ticks & Panel Labels
* **LaTeX Titles & Labels**: Full math formatting for subplot titles, X-labels, Y-labels, and Twin-Y labels (e.g. `$\lambda\ (\mathrm{nm})$`, `$I_{\mathrm{ph}}\ (\mu\mathrm{A})$`).
* **Axis Scales & Limits**: Linear, $\log_{10}$, and Symlog scales with auto or manual min/max limits for primary and Twin-Y axes.
* **Secondary Mathematical Axes**: Add secondary X or Y axes computed as mathematical transformations of the primary axis (e.g. Wavelength $\text{nm} \leftrightarrow \text{eV}$ Photon Energy, Frequency $\leftrightarrow$ Wavenumber, ${}^\circ\text{C} \leftrightarrow {}^\circ\text{F}$) using forward $f(x)$ and inverse $g(x)$ formulas or built-in presets.
* **Tick Marks & Frame Control**:
  * Inward, outward, or in-out tick directions (`tick_direction: "in"` by default).
  * Configure X-ticks (`both`, `bottom`, `top`, `none`) and Y-ticks (`left`, `both`, `right`, `none`).
  * Independently toggle numeric tick values/numbers.
* **Major & Minor Gridlines**: Toggle major and minor grids with customizable dash styles and opacity.
* **Scientific Panel Labels**: Publication-style corner tags (`a`, `b`, `c`, `d`...):
  * Rendered as solid black squares with centered white lettering (or plain text font).
  * Customizable font size, square ratio (default 130% of font size), and corner position.
  * **"Apply to all subplots"** button to unify panel label sizes across the entire figure in one click.
* **Legend Controls**: Toggle visibility, select placement (`best`, corners, outside right), column count, frame on/off, and custom font size.

---

### Tab 4: Templates & Batch Mode (`Templates & Batch`)
* **Reusable Style Templates (`.json`)**: Save all figure styling, tick parameters, colorbars, and channel configurations to a reusable JSON template file.
* **Apply Template**: Instantly apply any saved template to newly loaded experimental datasets.
* **Automated Folder Batch Processing**: Select an entire folder of measurement files, apply the active template, and automatically generate high-resolution figures (PDF, PNG, SVG) or standalone Python reproduction scripts for every file in the batch.

---

### Tab 5: Code, Export & Project Workspace Hub (`Code & Export`)
* **Real-time Standalone Python Script (`.py`)**:
  * Clean, PEP-8 compliant code using standard idioms (`fig, axes = plt.subplots(...)`).
  * 100% standalone with zero proprietary dependencies: any user with standard Python + Matplotlib + Pandas can run the generated code directly to reproduce the figure.
* **Jupyter Notebook (`.ipynb`) Generator**: Formatted notebook cells separated into imports, styling, data loading, and figure generation.
* **Direct High-Resolution Graphic Export**: Export directly to PDF, SVG, EPS, PNG, and TIFF with customizable DPI and tight bounding box.
* **Complete Project State Persistence (`.plotproj` / `.json`)**:
  * Save the entire workspace state—imported datasets (full DataFrames & matrices), configured subplots, channels, styling, reference lines, panel labels, and layout.
  * Reopen saved projects anytime to resume work without starting over.

---

## Installation & Setup

### 1. Prerequisites
* **Python 3.9+** (recommended: Python 3.10 – 3.12)
* Optional: LaTeX distribution (e.g. MiKTeX, TeX Live) if enabling native LaTeX text rendering (`text.usetex = True`).

### 2. Clone the Repository
```bash
git clone https://github.com/nicolasle/pyplot-Interactive-Plotter.git
cd pyplot-Interactive-Plotter
```

### 3. Create a Virtual Environment (Recommended)

#### Using `venv` (Standard Python):
* **Windows (PowerShell / Command Prompt)**:
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
* **Linux / macOS**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

#### Or using `conda`:
```bash
conda create -n plotter python=3.11 -y
conda activate plotter
```

### 4. Install Dependencies
Install all required packages via `pip`:
```bash
pip install -r requirements.txt
```

*(Alternatively, install the core packages directly: `pip install PySide6 matplotlib numpy pandas nbformat`)*

---

## Running the Application

* **From the Terminal / Command Line**:
  ```bash
  python app.py
  ```

* **On Windows (Direct Launcher)**:
  Double-click `run_plotter.bat` to launch the application directly.

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
├── run_plotter.bat             # Windows one-click launcher
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation
├── core/
│   ├── models.py               # Data models (FigureConfig, AxisConfig, TraceConfig, Dataset)
│   ├── data_loader.py          # Ultra-smart data sniffer & parser (1D & 2D)
│   ├── code_generator.py       # Standalone Python script & Jupyter Notebook generator
│   └── presets.py              # Journal publication presets (Nature, APS, IEEE, etc.)
├── gui/
│   ├── main_window.py          # Main PySide6 window with persistent live plot splitter
│   ├── plot_canvas.py          # Embedded Matplotlib canvas with click-to-select
│   ├── color_dialog.py         # Color selector with Matplotlib tab10 palette
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
