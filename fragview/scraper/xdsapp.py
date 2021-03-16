from fragview.projects import project_process_tool_dir
from fragview.dsets import ToolStatus


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
