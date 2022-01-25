from typing import Iterable, Optional, TextIO
from pathlib import Path
from fragview.projects import Project
from fragview.scraper import ToolStatus, ProcStats
from fragview.scraper.utils import get_files_by_suffixes, load_mtz_stats

ERROR_MSG = '<div class="errorheader">ERROR</div>'
LOG_FILE_SUFFIXES = ["lp", "log", "xml", "html"]


def _get_summary_report(project: Project, dataset) -> Optional[Path]:
    autoproc_res_dir = Path(
        project.get_dataset_root_dir(dataset),
        "process",
        project.protein,
        f"{dataset.crystal.id}",
        f"xds_{dataset.name}_1",
        "autoPROC",
    )

    glob = autoproc_res_dir.glob(str(Path("cn*", "AutoPROCv1_0_anom", "summary.html")))

    summary_file = next(glob, None)
    if summary_file is not None and summary_file.is_file():
        return summary_file

    # no autoPROC summary report found
    return None


def get_logs_dir(project, dataset):
    summary = _get_summary_report(project, dataset)
    if summary is None:
        return None

    return summary.parent


def get_processing_log_files(project: Project, dataset) -> Optional[Iterable[Path]]:
    summary_file = _get_summary_report(project, dataset)
    if summary_file is None:
        # summary file not found, return an empty iterable
        return None

    return get_files_by_suffixes(summary_file.parent, LOG_FILE_SUFFIXES)


def get_result_mtz(project: Project, dataset):
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


def _parse_statistics(stats: ProcStats, report):
    with open(report, "r", encoding="utf-8") as r:
        log = r.readlines()

    for n, line in enumerate(log):
        if "Low resolution limit  " in line:
            stats.low_resolution_average, stats.low_resolution_out = (
                line.split()[3],
                line.split()[5],
            )
        if "High resolution limit  " in line:
            stats.high_resolution_out, stats.high_resolution_average = (
                line.split()[3],
                line.split()[5],
            )
        if "Total number of observations  " in line:
            stats.reflections = line.split()[-3]
        if "Total number unique  " in line:
            stats.unique_reflections = line.split()[-3]
        if "Multiplicity  " in line:
            stats.multiplicity = line.split()[1]
        if "Mean(I)/sd(I)" in line:
            stats.i_sig_average = line.split()[1]
            stats.i_sig_out = line.split()[-1]
        if "Completeness (ellipsoidal)" in line or "Completeness (spherical)" in line:
            stats.completeness_average = line.split()[2]
            stats.completeness_out = line.split()[-1]
        if "Rmeas   (all I+ & I-)" in line:
            stats.r_meas_average = line.split()[-3]
            stats.r_meas_out = line.split()[-1]
        elif "Rmeas" in line:
            stats.r_meas_average = line.split()[-3]
            stats.r_meas_out = line.split()[-1]
        if "CRYSTAL MOSAICITY (DEGREES)" in line:
            stats.mosaicity = line.split()[-1]
        if "ISa (" in line:
            stats.isa = log[n + 1].split()[-1]

    return stats


def _scrape_summary_html(summary_file: Path) -> ToolStatus:
    with summary_file.open() as f:
        for line in f.readlines():
            if ERROR_MSG in line:
                return ToolStatus.FAILURE

    return ToolStatus.SUCCESS


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


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    summary_report = _get_summary_report(project, dataset)
    if summary_report is None:
        return None

    stats = ProcStats("autoproc")
    stats.status = _scrape_summary_html(summary_report)

    if stats.status != ToolStatus.SUCCESS:
        return stats

    _parse_statistics(stats, summary_report)

    mtz = get_result_mtz(project, dataset)
    if mtz is None:
        # seems that autoPROC failed to produce useful MTZ after all,
        # we need to treat that as failure
        stats.status = ToolStatus.FAILURE
        return stats

    load_mtz_stats(get_result_mtz(project, dataset), stats)

    return stats
