from importlib import import_module
from fragview.dsets import ToolStatus

#
# we support scraping logs for these tools
#
PROC_TOOLS = {"dials", "xds", "xdsapp", "edna", "autoproc"}
REFINE_TOOLS = {"dimple", "fspipeline"}
LIGFIT_TOOLS = {"rhofit", "ligandfit"}
ALL_TOOLS = set.union(PROC_TOOLS, REFINE_TOOLS, LIGFIT_TOOLS)


class UnknownToolException(Exception):
    pass


class ProcStats:
    def __init__(self, tool, report=None):
        self.tool = tool
        self.report = report
        self.spg = ""
        self.unique_rflns = ""
        self.total_observations = ""
        self.low_res_avg = ""
        self.low_res_out = ""
        self.high_res_avg = ""
        self.high_res_out = ""
        self.unit_cell = ""
        self.multiplicity = ""
        self.isig_avg = ""
        self.isig_out = ""
        self.rmeas_avg = ""
        self.rmeas_out = ""
        self.completeness_avg = ""
        self.completeness_out = ""
        self.mosaicity = ""
        self.ISa = ""


def get_tool_module(tool: str):
    # load the scraping python module dynamically,
    # to avoid importing all scraper modules each time
    # we are scraping a particular tool's logs
    return import_module(f"fragview.scraper.{tool.lower()}")


def scrape_processing_outcome(project, tool, dataset) -> ToolStatus:
    if tool not in ALL_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_outcome(project, dataset)


def scrape_refine_results(project, tool, dataset):
    if tool not in REFINE_TOOLS:
        raise UnknownToolException(tool)

    return get_tool_module(tool).scrape_results(project, dataset)
