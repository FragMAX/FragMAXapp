from typing import Optional, Iterable
from pathlib import Path
from fragview.projects import Project
from fragview.scraper import ProcStats, xia2


def _get_dials_dir(project: Project, dataset) -> Path:
    return Path(project.get_dataset_process_dir(dataset), "dials")


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    return xia2.scrape_results(project, _get_dials_dir(project, dataset))


def get_processing_log_files(project: Project, dataset) -> Optional[Iterable[int]]:
    return xia2.get_log_files(_get_dials_dir(project, dataset))


def get_result_mtz(project: Project, dataset) -> Path:
    return xia2.get_result_mtz(_get_dials_dir(project, dataset))
