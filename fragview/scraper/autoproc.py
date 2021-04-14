from typing import Iterator, Union, TextIO
from pathlib import Path
from fragview.scraper import ProcStats
from fragview.dsets import ToolStatus
from fragview.projects import project_shift_dirs, parse_dataset_name
from fragview.scraper.utils import split_unit_cell_vals, get_files_by_suffixes

ERROR_MSG = '<div class="errorheader">ERROR</div>'
LOG_FILE_SUFFIXES = ["lp", "log", "xml", "html"]


def get_summary_report(project, dataset: str) -> Union[Path, None]:
    sample, run = parse_dataset_name(dataset)

    for shift_dir in project_shift_dirs(project):
        autoproc_res_dir = Path(
            shift_dir,
            "process",
            project.protein,
            sample,
            f"xds_{dataset}_1",
            "autoPROC",
        )

        glob = autoproc_res_dir.glob(
            str(Path("cn*", "AutoPROCv1_0_anom", "summary.html"))
        )

        summary_file = next(glob, None)
        if summary_file is not None and summary_file.is_file():
            return summary_file

    # no autoPROC summary report found
    return None


def get_logs_dir(project, dataset: str):
    summary = get_summary_report(project, dataset)
    if summary is None:
        return None

    return summary.parent


def get_log_files(summary_file: Path) -> Iterator[Path]:
    return get_files_by_suffixes(summary_file.parent, LOG_FILE_SUFFIXES)


def get_result_mtz(project, dataset):
    res_dir = get_logs_dir(project, dataset)
    if res_dir is None:
        return None

    mtzs_dir = Path(res_dir, "HDF5_1")

    #
    # first we look staraniso_alldata.mtz file,
    # if it's not found, we look for aimless_unmerged.mtz
    #

    for mtz_file in ["staraniso_alldata.mtz", "aimless_unmerged.mtz"]:
        mtz = Path(mtzs_dir, mtz_file)
        if mtz.is_file():
            return mtz

    return None


def parse_statistics(summary_file: Path) -> ProcStats:
    with open(summary_file, "r", encoding="utf-8") as r:
        log = r.readlines()

    stats = ProcStats("autoproc", summary_file)

    for n, line in enumerate(log):
        if "Unit cell and space group:" in line:
            stats.spg = "".join(line.split()[11:]).replace("'", "")
            stats.unit_cell = split_unit_cell_vals(",".join(line.split()[5:11]))
        if "Low resolution limit  " in line:
            stats.low_res_avg, stats.low_res_out = line.split()[3], line.split()[5]
        if "High resolution limit  " in line:
            stats.high_res_out, stats.high_res_avg = line.split()[3], line.split()[5]
        if "Total number of observations  " in line:
            stats.total_observations = line.split()[-3]
        if "Total number unique  " in line:
            stats.unique_rflns = line.split()[-3]
        if "Multiplicity  " in line:
            stats.multiplicity = line.split()[1]
        if "Mean(I)/sd(I)" in line:
            stats.isig_avg = line.split()[1]
            stats.isig_out = line.split()[-1]
        if "Completeness (ellipsoidal)" in line or "Completeness (spherical)" in line:
            stats.completeness_avg = line.split()[2]
            stats.completeness_out = line.split()[-1]
        if "Rmeas   (all I+ & I-)" in line:
            stats.rmeas_avg = line.split()[-3]
            stats.rmeas_out = line.split()[-1]
        elif "Rmeas" in line:
            stats.rmeas_avg = line.split()[-3]
            stats.rmeas_out = line.split()[-1]
        if "CRYSTAL MOSAICITY (DEGREES)" in line:
            stats.mosaicity = line.split()[-1]
        if "ISa (" in line:
            stats.ISa = log[n + 1].split()[-1]

    return stats


def _scrape_summary_html(summary_file: Path) -> ToolStatus:
    with summary_file.open() as f:
        for line in f.readlines():
            if ERROR_MSG in line:
                return ToolStatus.FAILURE

    return ToolStatus.SUCCESS


def scrape_outcome(project, dataset: str) -> ToolStatus:
    summary_report = get_summary_report(project, dataset)
    if summary_report is None:
        return ToolStatus.UNKNOWN

    return _scrape_summary_html(summary_report)


def _parse_summary_html(summary_html: TextIO):
    # look for line containing
    for line in summary_html:
        if "ISa (see" not in line:
            continue

        break

    # line after the 'ISa (see' contains our value
    next_line = next(summary_html)
    _, isa = next_line.rsplit(maxsplit=1)
    return isa


def scrape_isa(project, dataset: str):
    summary_report = get_summary_report(project, dataset)
    if summary_report is None:
        # summary report not found, treat as unknown ISa
        return None

    with summary_report.open() as f:
        return _parse_summary_html(f)
