from typing import Iterator, Iterable, Optional
from pathlib import Path
from importlib import import_module
from enum import Enum

#
# we support scraping logs for these tools
#
PROC_TOOLS = {"dials", "xds", "xdsapp", "edna", "autoproc"}
REFINE_TOOLS = {"dimple", "fspipeline"}
LIGFIT_TOOLS = {"rhofit", "ligandfit"}
ALL_TOOLS = set.union(PROC_TOOLS, REFINE_TOOLS, LIGFIT_TOOLS)


class UnknownToolException(Exception):
    pass


class ToolStatus(Enum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILURE = "failure"


class ProcStats:
    def __init__(self, tool=None):
        self.tool = tool
        self.status = None
        self.space_group = None
        self.unique_reflections = None
        self.reflections = None
        self.low_resolution_average = None
        self.low_resolution_out = None
        self.high_resolution_average = None
        self.high_resolution_out = None
        self.unit_cell_a = None
        self.unit_cell_b = None
        self.unit_cell_c = None
        self.unit_cell_alpha = None
        self.unit_cell_beta = None
        self.unit_cell_gamma = None
        self.multiplicity = None
        self.i_sig_average = None
        self.i_sig_out = None
        self.r_meas_average = None
        self.r_meas_out = None
        self.completeness_average = None
        self.completeness_out = None
        self.mosaicity = None
        self.isa = None


class RefineResult:
    def __init__(self, proc_tool, refine_tool, status=None):
        self.proc_tool = proc_tool
        self.refine_tool = refine_tool
        self.status = status
        self.space_group = None
        self.resolution = None
        self.r_work = None
        self.r_free = None
        self.rms_bonds = None
        self.rms_angles = None
        self.cell = None
        self.blobs = None


class LigfitResult:
    def __init__(self, proc_tool, refine_tool, ligfit_tool, status, score, blobs=None):
        self.proc_tool = proc_tool
        self.refine_tool = refine_tool
        self.ligfit_tool = ligfit_tool
        self.status = status
        self.score = score
        self.blobs = blobs


def get_tool_module(tool: str):
    # load the scraping python module dynamically,
    # to avoid importing all scraper modules each time
    # we are scraping a particular tool's logs
    return import_module(f"fragview.scraper.{tool.lower()}")


def scrape_processing_results(project, tool, dataset) -> Optional[ProcStats]:
    if tool not in PROC_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_results(project, dataset)


def scrape_refine_results(project, tool, dataset) -> Iterator[RefineResult]:
    if tool not in REFINE_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_results(project, dataset)


def scrape_ligfit_results(project, tool, dataset) -> Iterator[LigfitResult]:
    if tool not in LIGFIT_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_results(project, dataset)


def get_processing_log_files(project, tool, dataset) -> Optional[Iterable[Path]]:
    if tool not in PROC_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).get_processing_log_files(project, dataset)


def get_refine_log_files(
    project, dataset, processing_tool, refine_tool
) -> Iterator[Path]:
    if refine_tool not in REFINE_TOOLS:
        raise UnknownToolException(refine_tool)

    return get_tool_module(refine_tool).get_refine_log_files(
        project, dataset, processing_tool
    )
