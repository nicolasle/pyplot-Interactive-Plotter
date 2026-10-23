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
