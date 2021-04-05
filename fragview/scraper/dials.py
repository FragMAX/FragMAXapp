from fragview.projects import project_process_tool_dir
from fragview.dsets import ToolStatus
from fragview.scraper import xia2


def scrape_outcome(project, dataset) -> ToolStatus:
    """
    examine xia2/dials logs, to try to figure the results of the processing run
    """
    return xia2.scrape_outcome(
        project, project_process_tool_dir(project, dataset, "dials")
    )


def scrape_isa(*_):
    #
    # we don't know how to scrape dials logs for ISa value,
    # treat is as 'unknown ISa'
    #
    return None
