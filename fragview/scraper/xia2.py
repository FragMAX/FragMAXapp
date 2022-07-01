from typing import Optional
from pathlib import Path
from fragview.scraper import ToolStatus, ProcStats
from fragview.fileio import read_text_lines
from fragview.projects import Project
from fragview.scraper.utils import load_mtz_stats


LOG_FILE_SUFFIXES = ["log", "html", "txt"]


def _scrape_outcome(project: Project, logs_dir: Path) -> Optional[ToolStatus]:
    """
    examine xia2 logs, to try to figure the results of the processing run
    """
    if not logs_dir.is_dir():
        return None

    log_file = Path(logs_dir, "xia2.txt")

    if not log_file.exists():
        return None

    #
    # if the log file contains lines:
    #
    # 'Scaled reflection:'
    # 'Status: normal termination'
    #
    # then, most likely, processing was successful
    #
    for line in read_text_lines(project, log_file):
        if line.startswith("Scaled reflections:"):
            return ToolStatus.SUCCESS

        if line.startswith("Status: normal termination"):
            return ToolStatus.SUCCESS

    # magic lines not found, probably something went wrong
    return ToolStatus.FAILURE


def _parse_xia2_html(project: Project, xia2_html: Path, stats: ProcStats):
    for line in read_text_lines(project, xia2_html):
        if "High resolution limit  " in line:
            stats.high_resolution_average = line.split()[-3]
            stats.high_resolution_out = line.split()[-1]
        if "Low resolution limit  " in line:
            stats.low_resolution_average = line.split()[-3]
            stats.low_resolution_out = line.split()[-1]
        if "Completeness  " in line:
            stats.completeness_average = line.split()[-3]
            stats.completeness_out = line.split()[-1]
        if "Multiplicity  " in line:
            stats.multiplicity = line.split()[-3]
        if "Rmeas(I+/-) " in line:
            stats.r_meas_average = line.split()[-3]
            stats.r_meas_out = line.split()[-1]
        if "Total unique" in line:
            stats.unique_reflections = line.split()[-3]
        if "Total observations" in line:
            stats.reflections = line.split()[-3]
        if "Mosaic spread" in line:
            stats.mosaicity = line.split()[-1]
        if "I/sigma  " in line:
            stats.i_sig_average = line.split()[-3]
            stats.i_sig_out = line.split()[-1]


def scrape_results(project: Project, logs_dir: Path) -> Optional[ProcStats]:
    stats = ProcStats()
    stats.status = _scrape_outcome(project, logs_dir)

    if stats.status is None:
        return None

    xia2_html = Path(logs_dir, "xia2.html")
    if not xia2_html.is_file():
        stats.status = ToolStatus.FAILURE
        return stats

    _parse_xia2_html(project, xia2_html, stats)
    load_mtz_stats(get_result_mtz(logs_dir), stats)

    return stats


def get_log_files(project: Project, process_dir: Path):
    project_dir = project.project_dir
    logs_dir = Path(process_dir, "LogFiles")

    if not logs_dir.is_dir():
        # Logs dir does not exist, no logs available
        return None

    for node in logs_dir.iterdir():
        if not node.is_file():
            continue

        suffix = node.suffix[1:].lower()
        if suffix in LOG_FILE_SUFFIXES:
            yield node.relative_to(project_dir)


def get_result_mtz(process_dir: Path) -> Path:
    return Path(process_dir, "DEFAULT", "scale", "AUTOMATIC_DEFAULT_free.mtz")
