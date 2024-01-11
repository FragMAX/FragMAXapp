from typing import Iterable, Optional
from gemmi import SpaceGroup, UnitCell
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


class PDBInfo(Wrapper):
    def __init__(self, orig):
        super().__init__(orig)

        # overwrite the DB space group string with gemmi SpaceGroup object
        self.space_group = SpaceGroup(orig.space_group)

        # lazy generated property
        self._unit_cell = None

    @property
    def unit_cell(self):
        if self._unit_cell is None:
            self._unit_cell = UnitCell(
                self.unit_cell_a,
                self.unit_cell_b,
                self.unit_cell_c,
                self.unit_cell_alpha,
                self.unit_cell_beta,
                self.unit_cell_gamma,
            )

        return self._unit_cell

    @property
    def point_group(self):
        return self.space_group.point_group_hm()


def wrap_pdbs(pdbs) -> Iterable[PDBInfo]:
    for pdb in pdbs:
        yield PDBInfo(pdb)


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

    def total_exposure(self):
        if self.exposure_time is None:
            # exposure time not available, can't calculate total exposure
            return None

        return self.exposure_time * self.images

    def processed(self) -> bool:
        return len(self.orig.result) > 0

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

    def fragment(self) -> Optional[Fragment]:
        return get_crystals_fragment(self.orig.crystal)


class ProcessingInfo(Wrapper):
    TOOL_NAMES = {"xds": "XIA2/XDS", "dials": "XIA2/DIALS"}

    def __init__(self, orig):
        super().__init__(orig)

        # overwrite the DB space group string with gemmi SpaceGroup object
        self.space_group = SpaceGroup(orig.space_group)

        # lazy generated property
        self._unit_cell = None

    @property
    def unit_cell(self):
        if self._unit_cell is None:
            self._unit_cell = UnitCell(
                self.unit_cell_a,
                self.unit_cell_b,
                self.unit_cell_c,
                self.unit_cell_alpha,
                self.unit_cell_beta,
                self.unit_cell_gamma,
            )

        return self._unit_cell

    @property
    def point_group(self):
        return self.space_group.point_group_hm()

    def tool_name(self):
        tool = self.orig.result.tool
        return self.TOOL_NAMES.get(tool, tool)

    @property
    def crystal(self):
        return self.orig.result.dataset.crystal

    @property
    def dataset(self):
        return self.orig.result.dataset


class RefineInfo(Wrapper):
    def _get_ligand_fit_score(self, tool: str):
        ligfit_res = self.orig.get_ligfit_result(tool)
        if ligfit_res is None:
            return None

        return ligfit_res.score

    def _get_tool_result(self, tool: str) -> Optional[str]:
        tool_res = self.orig.dataset.get_result(tool, self.result)
        if tool_res is None:
            return None

        return tool_res.result

    @property
    def rhofit_result(self) -> Optional[str]:
        return self._get_tool_result("rhofit")

    @property
    def ligandfit_result(self) -> Optional[str]:
        return self._get_tool_result("ligandfit")

    def rhofit_score(self):
        return self._get_ligand_fit_score("rhofit")

    def ligandfit_score(self):
        return self._get_ligand_fit_score("ligandfit")

    def fragment(self) -> Optional[Fragment]:
        return get_crystals_fragment(self.orig.dataset.crystal)

    @property
    def crystal(self):
        return self.orig.result.dataset.crystal


def wrap_refine_results(results) -> Iterable[RefineInfo]:
    for result in results:
        yield RefineInfo(result)
