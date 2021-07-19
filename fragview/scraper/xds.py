from typing import Optional
from pathlib import Path
from fragview.fileio import read_text_lines
from fragview.scraper import ProcStats, xia2
from fragview.projects import Project


def _scrape_isa(project, xds_dir: Path) -> Optional[str]:
    log_file = Path(xds_dir, "LogFiles", "AUTOMATIC_DEFAULT_XSCALE.log")

    if not log_file.is_file():
        # log file not found, treat as unknown ISa
        return None

    logfile = list(read_text_lines(project, log_file))

    isa = None
    for n, line in enumerate(logfile):
        if "ISa" in line:
            if logfile[n + 3].split():
                isa = logfile[n + 3].split()[-2]

    return isa


def _get_xds_dir(project: Project, dataset) -> Path:
    return Path(project.get_dataset_process_dir(dataset), "xds")


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    xds_dir = Path(project.get_dataset_process_dir(dataset), "xds")

    stats = xia2.scrape_results(project, _get_xds_dir(project, dataset))
    if stats is None:
        return None

    stats.isa = _scrape_isa(project, xds_dir)

    return stats


def get_processing_log_files(project: Project, dataset):
    return xia2.get_log_files(project, _get_xds_dir(project, dataset))


def get_result_mtz(project: Project, dataset) -> Path:
    return xia2.get_result_mtz(_get_xds_dir(project, dataset))
