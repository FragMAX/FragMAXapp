from typing import Iterable, Optional
from pathlib import Path
from fragview.fileio import read_text_lines
from fragview.projects import Project
from fragview.scraper import ToolStatus, ProcStats
from fragview.scraper.utils import get_files_by_suffixes, load_mtz_stats

LOG_FILE_SUFFIXES = ["lp", "log"]


def _get_xscale_logs(logs_dir: Path):
    return sorted(logs_dir.glob("*XSCALE.LP"), reverse=True)


def _scrape_isa(project: Project, dataset):
    edna_dir, _ = _find_results(project, dataset)

    isa = None

    for log in _get_xscale_logs(edna_dir):
        log_lines = list(read_text_lines(project, log))
        for n, line in enumerate(log_lines):
            if "ISa" in line:
                if log_lines[n + 1].split():
                    isa = log_lines[n + 1].split()[-2]
                    if isa == "b":
                        isa = ""
    return isa


def _find_results(project: Project, dataset):
    edna_res_dir = Path(
        project.get_dataset_root_dir(dataset),
        "process",
        project.protein,
        f"{dataset.crystal.id}",
        f"xds_{dataset.name}_1",
        "EDNA_proc",
        "results",
    )

    if edna_res_dir.is_dir():
        mtz_file = next(edna_res_dir.glob("*.mtz"), None)
        return edna_res_dir, mtz_file

    return None, None


def _parse_statistics(log_file: Path, stats: ProcStats):
    with open(log_file, "r", encoding="utf-8") as r:
        log = r.readlines()

    for line in log:
        if "Number of unique reflections" in line:
            stats.unique_reflections = line.split()[-1]
        if "Total number of observations" in line:
            stats.reflections = line.split()[-3]
        if "Low resolution limit" in line:
            stats.low_resolution_average = line.split()[3]
            stats.low_resolution_out = line.split()[-1]
        if "High resolution limit" in line:
            stats.high_resolution_average = line.split()[3]
            stats.high_resolution_out = line.split()[-1]
        if "Multiplicity" in line:
            stats.multiplicity = line.split()[1]
        if "Mean((I)/sd(I))" in line:
            stats.i_sig_average = line.split()[1]
            stats.i_sig_out = line.split()[-1]
        if "Rmeas (all I+ & I-)" in line:
            stats.r_meas_average = line.split()[5]
            stats.r_meas_out = line.split()[-1]
        if "completeness" in line:
            stats.completeness_average = line.split()[-3]
            stats.completeness_out = line.split()[-1]
        if "mosaicity" in line:
            stats.mosaicity = line.split()[-1]

    return stats


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    """
    check auto-processing folder, to try to guesstimate
    if enda was successful processing the specified dataset
    """
    edna_dir, mtz_file = _find_results(project, dataset)

    if edna_dir is None:
        return None

    stats = ProcStats("edna")

    if mtz_file is None:
        stats.status = ToolStatus.FAILURE
        return stats

    log_file = Path(edna_dir, f"ep_{dataset.name}_aimless_anom.log")
    if not log_file.is_file():
        # if there is no aimless log, then probably aimless failed somehow,
        # treat it as failure
        stats.status = ToolStatus.FAILURE
        return stats

    stats.status = ToolStatus.SUCCESS

    _parse_statistics(log_file, stats)
    load_mtz_stats(mtz_file, stats)
    stats.isa = _scrape_isa(project, dataset)

    return stats


def get_processing_log_files(project: Project, dataset) -> Optional[Iterable[Path]]:
    edna_res_dir, _ = _find_results(project, dataset)
    return get_files_by_suffixes(edna_res_dir, LOG_FILE_SUFFIXES)


def get_result_mtz(project: Project, dataset) -> Path:
    _, mtz_file = _find_results(project, dataset)
    return mtz_file
