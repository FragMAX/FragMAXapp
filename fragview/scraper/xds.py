from pathlib import Path
from fragview.projects import project_process_tool_dir, project_process_dataset_dir
from fragview.dsets import ToolStatus
from fragview.fileio import read_text_lines
from fragview.scraper import xia2


def scrape_outcome(project, dataset) -> ToolStatus:
    """
    examine xia2/xds logs, to try to figure the results of the processing run
    """
    return xia2.scrape_outcome(
        project, project_process_tool_dir(project, dataset, "xdsxscale")
    )


def scrape_isa(project, dataset: str):
    log_file = Path(
        project_process_dataset_dir(project, dataset),
        "xdsxscale",
        "LogFiles",
        "AUTOMATIC_DEFAULT_XSCALE.log",
    )

    if not log_file.is_file():
        # log file not found, treat as unknown ISa
        return None

    logfile = list(read_text_lines(project, log_file))

    for n, line in enumerate(logfile):
        if "ISa" in line:
            if logfile[n + 3].split():
                isa = logfile[n + 3].split()[-2]

    return isa
