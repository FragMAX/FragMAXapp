from fragview.scraper import get_tool_module, PROC_TOOLS, UnknownToolException


def scrape_isa(project, tool: str, dataset: str):
    """
    scrape logs for ISa value
    """
    if tool == "xdsxscale":
        # handle the sad fact that 'xds' tools is called 'xdsxscale'
        # in some parts of the code
        # TODO: change all code to use 'xds' name
        tool = "xds"

    if tool not in PROC_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_isa(project, dataset)
