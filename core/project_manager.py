"""
Project Manager Module
Handles saving and opening the complete interactive plotter workspace (.plotproj / .json):
all imported datasets (with full dataframes, formula columns, and 2D matrices),
figure configuration, subplots, channels, reference lines, panel labels, and layout.
"""

import json
import os
from typing import Dict, Tuple, Any, Optional
from core.models import FigureConfig, Dataset


PROJECT_FILE_FILTER = "Plotter Project (*.plotproj);;JSON Project (*.json);;All Files (*.*)"


def serialize_project(
    fig_config: FigureConfig,
    datasets: Dict[str, Dataset],
    active_coord: Tuple[int, int] = (0, 0)
) -> Dict[str, Any]:
    """
    Serializes the entire workspace into a self-contained dictionary:
    FigureConfig + all Datasets (with full DataFrames and matrices) + active state.
    """
    return {
        "format": "pyplot-interactive-plotter",
        "version": "1.1",
        "active_coord": list(active_coord),
        "figure_config": fig_config.to_dict(),
        "datasets": {
            d_id: ds.to_dict() for d_id, ds in datasets.items()
        }
    }


def deserialize_project(
    data: Dict[str, Any]
) -> Tuple[FigureConfig, Dict[str, Dataset], Tuple[int, int]]:
    """
    Deserializes a project dictionary back into FigureConfig, Datasets, and active_coord.
    """
    fig_data = data.get("figure_config", {})
    fig_config = FigureConfig.from_dict(fig_data)
    fig_config.ensure_axes_grid()

    datasets: Dict[str, Dataset] = {}
    datasets_data = data.get("datasets", {})
    for d_id, d_info in datasets_data.items():
        ds = Dataset.from_dict(d_info)
        datasets[ds.id] = ds

    active_coord_list = data.get("active_coord", [0, 0])
    active_coord = (int(active_coord_list[0]), int(active_coord_list[1]))

    return fig_config, datasets, active_coord


def save_project_to_file(
    file_path: str,
    fig_config: FigureConfig,
    datasets: Dict[str, Dataset],
    active_coord: Tuple[int, int] = (0, 0)
) -> None:
    """
    Saves entire project state to a .plotproj or .json file.
    """
    project_dict = serialize_project(fig_config, datasets, active_coord)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project_dict, f, indent=2, ensure_ascii=False)


def load_project_from_file(
    file_path: str
) -> Tuple[FigureConfig, Dict[str, Dataset], Tuple[int, int]]:
    """
    Loads entire project state from a .plotproj or .json file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return deserialize_project(data)
