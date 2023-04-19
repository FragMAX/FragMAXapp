from typing import Iterable, Optional
from pathlib import Path
from gemmi import cif
from fragview.projects import Project
from fragview.scraper import ToolStatus, ProcStats
from fragview.scraper.utils import get_files_by_suffixes, load_mtz_stats

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

    glob = autoproc_res_dir.glob(
        str(Path("cn*", "AutoPROCv1_0_noanom", "summary.html"))
    )

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


def _parse_cif(stats: ProcStats, cif_path: str):
    def get_cells(block, loop_tag, *indices):
        def gen():
            col = block.find_loop(loop_tag)
            for idx in indices:
                yield col[idx]

        return list(gen())

    def get_block():
        # find a block named  *_truncate,
        # the name prefix seems to vary, e.g.
        # '2_truncate' or '_01_truncate'
        for block in cif.read_file(cif_path):
            if block.name.endswith("truncate"):
                return block

        assert False, f"{cif_path}: no *truncate block found"

    block = get_block()

    stats.low_resolution_overall = block.find_value("_reflns.d_resolution_low")
    stats.low_resolution_inner, stats.low_resolution_out = get_cells(
        block, "_reflns_shell.d_res_low", 0, -1
    )

    stats.high_resolution_overall = block.find_value("_reflns.d_resolution_high")
    stats.high_resolution_inner, stats.high_resolution_out = get_cells(
        block, "_reflns_shell.d_res_high", 0, -1
    )

    stats.reflections = block.find_value("_reflns.pdbx_number_measured_all")
    stats.unique_reflections = block.find_value("_reflns.number_obs")
    stats.multiplicity = block.find_value("_reflns.pdbx_redundancy")
    stats.i_sig_average = block.find_value("_reflns.pdbx_netI_over_sigmaI")
    (stats.i_sig_out,) = get_cells(block, "_reflns_shell.meanI_over_sigI_obs", -1)
    stats.completeness_average = block.find_value("_reflns.percent_possible_obs")
    (stats.completeness_out,) = get_cells(
        block, "_reflns_shell.percent_possible_all", -1
    )
    stats.r_meas_average = block.find_value("_reflns.pdbx_Rmerge_I_obs")
    (stats.r_meas_out,) = get_cells(block, "_reflns_shell.Rmerge_I_obs", -1)


def _parse_statistics(stats: ProcStats, res_dir: Path):
    def is_cif_parse_error(ex: Exception):
        # check if exception seems to be one of the expected
        # CIF parsing errors from gemmi
        msg = str(ex)
        if msg.endswith("Wrong number of values in the loop"):
            return True

        if ": duplicate tag" in msg:
            return True

        return False

    cif = next(res_dir.glob("Data_*autoPROC_TRUNCATE_all.cif"), None)
    if cif is None:
        # CIF file not found, assuming processing error
        stats.status = ToolStatus.FAILURE
        return

    try:
        _parse_cif(stats, str(cif))
        stats.status = ToolStatus.SUCCESS
    except (ValueError, RuntimeError) as e:
        if is_cif_parse_error(e):
            print(f"warning: CIF parse error {e}")
            stats.status = ToolStatus.FAILURE
            return

        # unexpected exception, re-raise
        raise e


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    #
    # Following logic is applied for figuring out state of an autoPROC processing
    # for a dataset.
    #
    # If no 'summary.html' is found,
    # we assume autoPROC have not been run for this dataset
    #
    # If 'summary.html' is found, but 'Data_*autoPROC_TRUNCATE_all.cif'  or MTZ file is missing,
    # we assume autoPROC have failed to process this dataset.
    #
    # If we fail to parse CIF file, we flag this as a failure.
    #
    # Otherwise, we consider processing successful.
    #

    summary_report = _get_summary_report(project, dataset)
    if summary_report is None:
        return None

    stats = ProcStats("autoproc")
    _parse_statistics(stats, summary_report.parent)

    if stats.status != ToolStatus.SUCCESS:
        return stats

    mtz = get_result_mtz(project, dataset)
    if mtz is None:
        # seems that autoPROC failed to produce useful MTZ after all,
        # we need to treat that as failure
        stats.status = ToolStatus.FAILURE
        return stats

    load_mtz_stats(get_result_mtz(project, dataset), stats)

    return stats
