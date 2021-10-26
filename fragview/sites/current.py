from typing import Iterable, List, Optional
from pathlib import Path
from fragview.sites import SITE
from fragview.sites.plugin import DatasetMetadata

"""
A utility module for accessing site specific implementation of the
various aspects of the application.

This module wraps the 'current' site-plugin's methods in convenience functions.
"""

#
# features
#


def proposals_disabled() -> bool:
    """
    returns True if 'proposals' feature is disabled for this site
    """
    return "proposals" in SITE.DISABLED_FEATURES


#
# misc
#


def get_diffraction_picture_command(
    project, dataset, angle: int, dest_pic_file
) -> List[str]:
    """
    shell command that will generate a diffraction picture (e.g. jpeg file) for
    specified angle of a dataset
    """
    return SITE.get_diffraction_picture_command(project, dataset, angle, dest_pic_file)


def get_dataset_metadata(
    project, dataset_dir: Path, crystal_id: str, run: int
) -> Optional[DatasetMetadata]:
    return SITE.get_dataset_metadata(project, dataset_dir, crystal_id, run)


def add_pandda_init_commands(batch):
    SITE.add_pandda_init_commands(batch)


def get_pandda_inspect_commands(method_dir: Path) -> str:
    return SITE.get_pandda_inspect_commands(method_dir)


#
# paths
#


def get_project_dir(project) -> Path:
    return SITE.get_project_dir(project)


def get_project_dataset_dirs(project) -> Iterable[Path]:
    return SITE.get_project_dataset_dirs(project)


def get_dataset_runs(data_dir: Path) -> Iterable[int]:
    """
    get all run numbers for a dataset given it's root folder
    """
    return SITE.get_dataset_runs(data_dir)


def get_dataset_master_image(project, dataset) -> Path:
    return SITE.get_dataset_master_image(project, dataset)
