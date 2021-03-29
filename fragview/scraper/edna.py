from typing import Iterator
from pathlib import Path
from fragview.dsets import ToolStatus
from fragview.fileio import read_text_lines
from fragview.projects import project_shift_dirs, parse_dataset_name
from fragview.scraper import ProcStats
from fragview.scraper.utils import split_unit_cell_vals, get_files_by_suffixes


LOG_FILE_SUFFIXES = ["lp", "log"]


def _get_xscale_logs(logs_dir: Path):
    return sorted(logs_dir.glob("*XSCALE.LP"), reverse=True)


def scrape_logs(project, logs_dir: Path):
    isa = ""

    for log in _get_xscale_logs(logs_dir):
        log_lines = list(read_text_lines(project, log))
        for n, line in enumerate(log_lines):
            if "ISa" in line:
                if log_lines[n + 1].split():
                    isa = log_lines[n + 1].split()[-2]
                    if isa == "b":
                        isa = ""

    return isa


def _find_results(project, sample, run):
    dataset = f"{sample}_{run}"
    for shift_dir in project_shift_dirs(project):
        edna_res_dir = Path(
            shift_dir,
            "process",
            project.protein,
            sample,
            f"xds_{dataset}_1",
            "EDNA_proc",
            "results",
        )

        if edna_res_dir.is_dir():
            mtz_file = next(edna_res_dir.glob("*.mtz"), None)
            return edna_res_dir, mtz_file

    return None, None


def get_result_mtz(project, dataset):
    sample, run = parse_dataset_name(dataset)
    _, mtz_file = _find_results(project, sample, run)
    return mtz_file


def get_report(project, sample, run):
    edna_dir, _ = _find_results(project, sample, run)
    if edna_dir is None:
        return None

    log_file = Path(edna_dir, f"ep_{sample}_{run}_phenix_xtriage_noanom.log")
    if log_file.is_file():
        return log_file

    return None


def get_log_files(edna_report: Path) -> Iterator[Path]:
    return get_files_by_suffixes(edna_report.parent, LOG_FILE_SUFFIXES)


def parse_statistics(project, sample, run):
    edna_dir, _ = _find_results(project, sample, run)
    log_file = Path(edna_dir, f"ep_{sample}_{run}_aimless_anom.log")

    with open(log_file, "r", encoding="utf-8") as r:
        print("log_file", log_file)
        log = r.readlines()

    stats = ProcStats("edna")

    for line in log:
        if "Space group:" in line:
            stats.spg = "".join(line.split()[2:])
        if "Number of unique reflections" in line:
            stats.unique_rflns = line.split()[-1]
        if "Total number of observations" in line:
            stats.total_observations = line.split()[-3]
        if "Low resolution limit" in line:
            stats.low_res_avg = line.split()[3]
            stats.low_res_out = line.split()[-1]
        if "High resolution limit" in line:
            stats.high_res_avg = line.split()[3]
            stats.high_res_out = line.split()[-1]
        if "Average unit cell:" in line:
            stats.unit_cell = split_unit_cell_vals(",".join(line.split()[3:]))
        if "Multiplicity" in line:
            stats.multiplicity = line.split()[1]
        if "Mean((I)/sd(I))" in line:
            stats.isig_avg = line.split()[1]
            stats.isig_out = line.split()[-1]
        if "Rmeas (all I+ & I-)" in line:
            stats.rmeas_avg = line.split()[5]
            stats.rmeas_out = line.split()[-1]
        if "completeness" in line:
            stats.completeness_avg = line.split()[-3]
            stats.completeness_out = line.split()[-1]
        if "mosaicity" in line:
            stats.mosaicity = line.split()[-1]

    return stats


def scrape_outcome(project, dataset: str) -> ToolStatus:
    """
    check autoprocessing folders, for each of the project's
    shifts, to try to guesstimate if enda was successful
    processing the specified dataset
    """
    sample, run = parse_dataset_name(dataset)
    edna_dir, mtz_file = _find_results(project, sample, run)
    if edna_dir is None:
        return ToolStatus.UNKNOWN

    if mtz_file is None:
        return ToolStatus.FAILURE

    return ToolStatus.SUCCESS
