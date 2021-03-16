from pathlib import Path
from fragview.scraper import get_tool_module, PROC_TOOLS, UnknownToolException


def scrape_proc_logs(project, logs_dir: Path):
    """
    scrape logs for ISa value
    """
    tool = logs_dir.name
    if tool not in PROC_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_logs(project, logs_dir)
