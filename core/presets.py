"""
Publication & Display Presets for Matplotlib Figures
Standard dimensions, fonts, and DPI for major scientific journals.
"""

from typing import Dict, Any

PUBLICATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "Nature Single Column (89 mm)": {
        "width_cm": 8.9,
        "height_cm": 7.0,
        "dpi": 300,
        "font_family": "sans-serif",
        "font_size": 7.0,
        "style": "seaborn-v0_8-ticks",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Standard 1-column layout for Nature & Nature Research journals."
    },
    "Nature Double Column (183 mm)": {
        "width_cm": 18.3,
        "height_cm": 11.0,
        "dpi": 300,
        "font_family": "sans-serif",
        "font_size": 8.0,
        "style": "seaborn-v0_8-ticks",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Full-width 2-column figure for Nature journals."
    },
    "APS Physical Review Single (86 mm)": {
        "width_cm": 8.6,
        "height_cm": 6.8,
        "dpi": 300,
        "font_family": "serif",
        "font_size": 8.5,
        "style": "classic",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Standard 1-column layout for Phys. Rev. (B, D, E, Lett, etc.)."
    },
    "APS Physical Review Double (178 mm)": {
        "width_cm": 17.8,
        "height_cm": 11.0,
        "dpi": 300,
        "font_family": "serif",
        "font_size": 9.0,
        "style": "classic",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Double-column full-width layout for APS journals."
    },
    "IEEE Transactions Single (89 mm)": {
        "width_cm": 8.89,
        "height_cm": 6.5,
        "dpi": 300,
        "font_family": "serif",
        "font_size": 8.0,
        "style": "seaborn-v0_8-ticks",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Single-column format (3.5 inches) for IEEE journals."
    },
    "Elsevier 1.5-Column (140 mm)": {
        "width_cm": 14.0,
        "height_cm": 9.5,
        "dpi": 300,
        "font_family": "sans-serif",
        "font_size": 8.5,
        "style": "seaborn-v0_8-ticks",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Standard 1.5-column figure width for Elsevier publications."
    },
    "Square Scientific (100×100 mm)": {
        "width_cm": 10.0,
        "height_cm": 10.0,
        "dpi": 300,
        "font_family": "sans-serif",
        "font_size": 8.5,
        "style": "seaborn-v0_8-ticks",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Balanced 1:1 aspect ratio figure for 2D maps or phase diagrams."
    },
    "Presentation Slide (16:9 Widescreen)": {
        "width_cm": 22.0,
        "height_cm": 12.5,
        "dpi": 150,
        "font_family": "sans-serif",
        "font_size": 13.0,
        "style": "seaborn-v0_8-whitegrid",
        "tick_direction": "out",
        "tight_layout": True,
        "description": "Large typography optimized for PowerPoint/Keynote slides."
    },
    "Default Standard": {
        "width_cm": 14.0,
        "height_cm": 10.0,
        "dpi": 150,
        "font_family": "sans-serif",
        "font_size": 10.0,
        "style": "default",
        "tick_direction": "in",
        "tight_layout": True,
        "description": "Standard interactive preview layout."
    }
}


SECONDARY_AXIS_PRESETS: Dict[str, Dict[str, str]] = {
    "Custom Formula": {
        "fwd": "",
        "inv": "",
        "label": "",
    },
    "Wavelength (nm) ⇄ Photon Energy (eV)": {
        "fwd": "1239.84193 / x",
        "inv": "1239.84193 / x",
        "label": "Photon Energy (eV)",
    },
    "Wavelength (μm) ⇄ Wavenumber (cm⁻¹)": {
        "fwd": "10000.0 / x",
        "inv": "10000.0 / x",
        "label": "Wavenumber (cm⁻¹)",
    },
    "Wavelength (nm) ⇄ Wavenumber (cm⁻¹)": {
        "fwd": "1e7 / x",
        "inv": "1e7 / x",
        "label": "Wavenumber (cm⁻¹)",
    },
    "Frequency (Hz) ⇄ Period (s)": {
        "fwd": "1.0 / x",
        "inv": "1.0 / x",
        "label": "Period (s)",
    },
    "Frequency (THz) ⇄ Energy (meV)": {
        "fwd": "x * 4.135667",
        "inv": "x / 4.135667",
        "label": "Energy (meV)",
    },
    "Temperature (°C) ⇄ Fahrenheit (°F)": {
        "fwd": "x * 1.8 + 32",
        "inv": "(x - 32) / 1.8",
        "label": "Temperature (°F)",
    },
    "Temperature (°C) ⇄ Kelvin (K)": {
        "fwd": "x + 273.15",
        "inv": "x - 273.15",
        "label": "Temperature (K)",
    },
    "Angle: Degrees (°) ⇄ Radians (rad)": {
        "fwd": "np.deg2rad(x)",
        "inv": "np.rad2deg(x)",
        "label": "Angle (rad)",
    },
    "Linear Ratio ⇄ Power dB": {
        "fwd": "10 * np.log10(x)",
        "inv": "10**(x / 10)",
        "label": "Power (dB)",
    },
    "Linear Ratio ⇄ Amplitude dB": {
        "fwd": "20 * np.log10(x)",
        "inv": "10**(x / 20)",
        "label": "Amplitude (dB)",
    },
    "Multiply × 1000 (e.g. V to mV / m to mm)": {
        "fwd": "x * 1000",
        "inv": "x / 1000",
        "label": "Scaled (×1000)",
    },
    "Divide by 1000 (e.g. Hz to kHz / nm to μm)": {
        "fwd": "x / 1000",
        "inv": "x * 1000",
        "label": "Scaled (/1000)",
    },
}
