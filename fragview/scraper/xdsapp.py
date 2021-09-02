from typing import Optional, Iterable
import re
from pathlib import Path
from fragview.projects import Project
from fragview.fileio import read_text_lines
from fragview.scraper import ProcStats, ToolStatus
from fragview.scraper.utils import get_files_by_suffixes

LOG_FILE_SUFFIXES = ["txt", "lp", "lp_1", "log", "out", "html"]


SPACE_GROUP = "Space group"
UNIT_CELL = "Unit cell parameters [A]"
RESOLUTION = "Resolution limit [A]"
REFLECTIONS = "No. of reflections"
UNIQUE_REFLECTIONS = "No. of uniques"
I_SIGI = "I/sigI"
MULTIPLICITY = "Multiplicity"
R_MEAS = "R_meas [%]"
COMPLETENESS = "Completeness [%]"
MOSAICITY = "Mosaicity [deg]"
ISA = "ISa"

# match 'N1-N2 (N3-N4)' string, for resolutions line
RESOLUTION_RE = re.compile(r"^([\d\\.]+)-([\d\\.]+) \(([\d\\.]+)-([\d\\.]+)\)")
# match 'N1 (N2)' string, that is a pair of numbers
PAIR_RE = re.compile(r"^([\d\\.]+) \(([\d\\.]+)\)")
# match 'N1 (N2)' string, where second number is optional
OPTIONAL_PAIR_RE = re.compile(r"([\d\.]+)( \([\d\.]+\))?")


def _get_results_log(project: Project, xdsapp_dir, dataset) -> Optional[Path]:
    #
    # handle different versions of XDSAPP,
    # older versions name the report file: 'results_<dataset>_data.txt'
    # newer versions                       'results_<dataset>.txt'
    #
    log_file = next(
        xdsapp_dir.glob(f"results_{project.protein}-{dataset.name}*.txt"), None
    )
    if log_file is None or not log_file.is_file():
        return None

    return log_file


def _parse_results_log(project: Project, results_file: Path, stats: ProcStats):
    def _parse_line(line, prefix, parser_func):
        text = line[len(prefix) :].strip()
        return parser_func(text)

    def _space_group(text):
        # remove all spaces in space group string
        spg = "".join(text.split(" "))
        return spg

    def _unit_cell(text):
        return text.split()

    def _resolution(text):
        return RESOLUTION_RE.match(text).groups()

    def _pair(text):
        return PAIR_RE.match(text).groups()

    def _first_number(text):
        return OPTIONAL_PAIR_RE.match(text).groups()[0]

    for line in read_text_lines(project, results_file):
        if not line.startswith("    "):
            # all lines we want to parse are indented with 4 spaces,
            # ignore all other lines
            continue

        line = line.strip()

        if line.startswith(SPACE_GROUP):
            stats.space_group = _parse_line(line, SPACE_GROUP, _space_group)
        elif line.startswith(UNIT_CELL):
            (
                stats.unit_cell_a,
                stats.unit_cell_b,
                stats.unit_cell_c,
                stats.unit_cell_alpha,
                stats.unit_cell_beta,
                stats.unit_cell_gamma,
            ) = _parse_line(line, UNIT_CELL, _unit_cell)
        elif line.startswith(RESOLUTION):
            (
                stats.low_resolution_average,
                stats.high_resolution_average,
                stats.low_resolution_out,
                stats.high_resolution_out,
            ) = _parse_line(line, RESOLUTION, _resolution)
        elif line.startswith(REFLECTIONS):
            stats.reflections = _parse_line(line, REFLECTIONS, _first_number)
        elif line.startswith(UNIQUE_REFLECTIONS):
            stats.unique_reflections = _parse_line(
                line, UNIQUE_REFLECTIONS, _first_number
            )
        elif line.startswith(I_SIGI):
            stats.i_sig_average, stats.i_sig_out = _parse_line(line, I_SIGI, _pair)
        elif line.startswith(MULTIPLICITY):
            stats.multiplicity = _parse_line(line, MULTIPLICITY, _first_number)
        elif line.startswith(R_MEAS):
            stats.r_meas_average, stats.r_meas_out = _parse_line(line, R_MEAS, _pair)
        elif line.startswith(COMPLETENESS):
            stats.completeness_average, stats.completeness_out = _parse_line(
                line, COMPLETENESS, _pair
            )
        elif line.startswith(MOSAICITY):
            stats.mosaicity = _parse_line(line, MOSAICITY, _first_number)
        elif line.startswith(ISA):
            stats.isa = _parse_line(line, ISA, lambda x: x)

    return stats


def _get_xdsapp_dir(project: Project, dataset) -> Path:
    return Path(project.get_dataset_process_dir(dataset), "xdsapp")


def scrape_results(project: Project, dataset) -> Optional[ProcStats]:
    xdsapp_dir = _get_xdsapp_dir(project, dataset)

    if not xdsapp_dir.is_dir():
        return None

    stats = ProcStats("xdsapp")
    stats.status = ToolStatus.SUCCESS

    mtz = next(xdsapp_dir.glob("*F.mtz"), None)
    if mtz is None:
        # MTZ file found, we assume great success
        stats.status = ToolStatus.FAILURE

    results_log = _get_results_log(project, xdsapp_dir, dataset)
    if results_log is None:
        stats.status = ToolStatus.FAILURE

    if stats.status == ToolStatus.SUCCESS:
        _parse_results_log(project, results_log, stats)  # type: ignore

    return stats


def get_processing_log_files(project: Project, dataset) -> Optional[Iterable[Path]]:
    xdsapp_dir = _get_xdsapp_dir(project, dataset)

    return get_files_by_suffixes(xdsapp_dir, LOG_FILE_SUFFIXES)


def get_result_mtz(project: Project, dataset) -> Path:
    xdsapp_dir = _get_xdsapp_dir(project, dataset)
    return next(xdsapp_dir.glob("*F.mtz"))
