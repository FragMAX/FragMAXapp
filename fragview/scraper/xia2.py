from pathlib import Path
from fragview.dsets import ToolStatus
from fragview.fileio import read_text_lines


def scrape_outcome(project, logs_dir: Path) -> ToolStatus:
    """
    examine xia2 logs, to try to figure the results of the processing run
    """
    if not logs_dir.is_dir():
        return ToolStatus.UNKNOWN

    log_file = Path(logs_dir, "xia2.txt")

    if not log_file.exists():
        return ToolStatus.UNKNOWN

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
