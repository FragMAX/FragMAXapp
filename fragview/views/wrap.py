from typing import Iterator
from fragview.models import Fragment
from fragview.views.utils import get_crystals_fragment


class Wrapper:
    def __init__(self, orig):
        self.orig = orig

    def __getattr__(self, attr_name):
        """
        give access to all of wrapped object's attributes
        """
        return getattr(self.orig, attr_name)


class DatasetInfo(Wrapper):
    """
    wraps a DataSet object, to give template code
    simple access to required fields
    """

    def crystal(self):
        return self.orig.crystal.id

    def _tool_result(self, tool):
        return self.orig.tool_result(tool)

    def _aggregate_tool_results(self, tool):
        """
        do an optimistic aggregation of results,
        if we have a single ok result then treat it as 'ok'
        if all are 'error', treat as 'error'

        no results, then return None
        """
        results = list(self.orig.tool_results(tool))
        if not results:
            # no results for this tool
            return None

        for res in self.orig.tool_results(tool):
            if res == "ok":
                return "ok"
            assert res == "error"

        return "error"

    def autoproc_result(self):
        return self._tool_result("autoproc")

    def edna_result(self):
        return self._tool_result("edna")

    def dials_result(self):
        return self._tool_result("dials")

    def xds_result(self):
        return self._tool_result("xds")

    def xdsapp_result(self):
        return self._tool_result("xdsapp")

    def dimple_result(self):
        return self._aggregate_tool_results("dimple")

    def fspipeline_result(self):
        return self._aggregate_tool_results("fspipeline")

    def rhofit_result(self):
        return self._aggregate_tool_results("rhofit")

    def ligandfit_result(self):
        return self._aggregate_tool_results("ligandfit")

    def fragment(self) -> Fragment:
        return get_crystals_fragment(self.orig.crystal)


class ProcessingInfo(Wrapper):
    TOOL_NAMES = {"xds": "XIA2/XDS", "dials": "XIA2/DIALS"}

    def tool_name(self):
        tool = self.orig.result.tool
        return self.TOOL_NAMES.get(tool, tool)


class RefineInfo(Wrapper):
    def _get_ligand_fit_score(self, tool: str):
        ligfit_res = self.orig.get_ligfit_result(tool)
        if ligfit_res is None:
            return None

        return ligfit_res.score

    def rhofit_score(self):
        return self._get_ligand_fit_score("rhofit")

    def ligandfit_score(self):
        return self._get_ligand_fit_score("ligandfit")

    def fragment(self) -> Fragment:
        return get_crystals_fragment(self.orig.dataset.crystal)


def wrap_refine_results(results) -> Iterator[RefineInfo]:
    for result in results:
        yield RefineInfo(result)
