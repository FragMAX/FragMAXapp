from typing import Union
from pathlib import Path
from fragview.projects import project_process_tool_dir, project_process_dataset_dir
from fragview.dsets import ToolStatus

ISA_LINE = "    ISa"


def scrape_outcome(project, dataset) -> ToolStatus:
    xdsapp_dir = project_process_tool_dir(project, dataset, "xdsapp")

    if not xdsapp_dir.is_dir():
        return ToolStatus.UNKNOWN

    mtz = next(xdsapp_dir.glob("*F.mtz"), None)
    if mtz:
        # MTZ file found, we assume great success
        return ToolStatus.SUCCESS

    # no MTZ found, something probably went wrong
    return ToolStatus.FAILURE


def _get_results_log(project, dataset: str) -> Union[None, Path]:
    logs_dir = Path(project_process_dataset_dir(project, dataset), "xdsapp",)

    #
    # handle different versions of XDSAPP,
    # older versions name the report file: 'results_<dataset>_data.txt'
    # newer versions                       'results_<dataset>.txt'
    #
    log_file = next(logs_dir.glob(f"results_{dataset}*.txt"))
    if log_file is None or not log_file.is_file():
        return None

    return log_file


def scrape_isa(project, dataset: str) -> Union[None, str]:
    log_file = _get_results_log(project, dataset)
    if log_file is None:
        # can't find results log file, treat as unknown ISa value
        return None

    isa = None
    with log_file.open() as f:
        for line in f:
            if not line.startswith(ISA_LINE):
                continue

            isa = line[len(ISA_LINE) :].strip()

    return isa
