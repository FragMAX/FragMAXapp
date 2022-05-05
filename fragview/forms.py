from typing import Optional, List, Dict
from itertools import count
from django.forms import (
    Form,
    CharField,
    BooleanField,
    IntegerField,
    FloatField,
    FileField,
    ValidationError,
)
from gemmi import UnitCell
from fragview.tools import get_tool_by_name
from fragview.models import Library
from fragview.projects import Project
from fragview.space_groups import SpaceGroup, get_space_group
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV, Crystals
from fragview.fraglibs import parse_fraglib_csv, InvalidLibraryCSV


class _GetFieldMixin:
    def _get_field(self, name):
        return self.cleaned_data[name]


class _JobsForm(Form, _GetFieldMixin):
    pipelines = CharField()

    def __init__(self, project: Project, data):
        super().__init__(data)
        self.project = project

    def clean_pipelines(self):
        def _tool_enums():
            for tool_name in self.get_pipelines().split(","):
                yield get_tool_by_name(tool_name)

        return list(_tool_enums())

    def get_pipelines(self):
        return self._get_field("pipelines")


class ProcessForm(_JobsForm):
    datasets = CharField()
    spaceGroup = CharField(required=False)
    cellParameters = CharField(required=False)

    def clean_datasets(self):
        def _lookup_datasets(dataset_ids: List):
            for dataset_id in dataset_ids:
                yield self.project.get_dataset(dataset_id)

        dataset_ids = self._get_field("datasets").split(",")
        return list(_lookup_datasets(dataset_ids))

    def clean_spaceGroup(self):
        space_group_name = self.get_space_group()
        if space_group_name == "":
            # no space group specified, aka 'auto' space group
            return None

        space_group = get_space_group(space_group_name)
        if space_group is None:
            raise ValidationError(
                f"unsupported space group '{space_group_name}' specified"
            )

        return space_group

    def clean_cellParameters(self):
        cell = self.get_cell_parameters()
        if cell == "":
            # no cell parameters specified, aka 'auto' mode
            return None

        # split cell parameters on comma, and convert to
        a, b, c, alpha, beta, gamma = [float(v) for v in cell.split(",")]
        return UnitCell(a, b, c, alpha, beta, gamma)

    def get_datasets(self):
        return self._get_field("datasets")

    def get_space_group(self) -> Optional[SpaceGroup]:
        return self._get_field("spaceGroup")

    def get_cell_parameters(self) -> Optional[UnitCell]:
        return self._get_field("cellParameters")


class RefineForm(_JobsForm):
    pdb = CharField()
    # ID's of ProcessResult row, i.e. MTZ files to be refined
    processResults = CharField()

    def clean_pdb(self):
        pdb_id = self._get_field("pdb")
        pdb = self.project.get_pdb(pdb_id)
        self.pdb_file = self.project.get_pdb_file(pdb)

    def clean_processResults(self):
        def _lookup_process_results(proc_res_ids: List):
            for res_id in proc_res_ids:
                yield self.project.get_process_result(res_id)

        dataset_ids = self._get_field("processResults").split(",")
        return list(_lookup_process_results(dataset_ids))

    def get_process_results(self):
        return self._get_field("processResults")


class LigfitForm(_JobsForm):
    # ID's of RefineResult row
    refineResults = CharField()
    restrainsTool = CharField(required=False)

    def clean_refineResults(self):
        def _lookup_refine_results(refine_res_ids: List):
            for res_id in refine_res_ids:
                yield self.project.get_refine_result(res_id)

        res_ids = self._get_field("refineResults").split(",")
        return list(_lookup_refine_results(res_ids))

    def clean_restrainsTool(self):
        return get_tool_by_name(self._get_field("restrainsTool"))

    def get_refine_results(self):
        return self._get_field("refineResults")

    def get_restrains_tool(self):
        return self._get_field("restrainsTool")


class PanddaProcessForm(Form, _GetFieldMixin):
    processingTool = CharField()
    refinementTool = CharField()
    restrainsTool = CharField()
    useKnownApo = BooleanField(required=False)
    useDMSODatasets = BooleanField(required=False)
    reprocessZMaps = BooleanField(required=False)
    numOfCores = IntegerField()
    minGroundDatasets = IntegerField()
    maxRFree = FloatField()
    resolutionUpperLimit = FloatField()
    resolutionLowerLimit = FloatField()
    customParameters = CharField(required=False)

    @property
    def processing_tool(self):
        return self._get_field("processingTool")

    @property
    def refinement_tool(self):
        return self._get_field("refinementTool")

    @property
    def restrains_tool(self):
        return self._get_field("restrainsTool")

    @property
    def use_known_apo(self):
        return self._get_field("useKnownApo")

    @property
    def use_dmso_datasets(self):
        return self._get_field("useDMSODatasets")

    @property
    def reprocess_z_maps(self):
        return self._get_field("reprocessZMaps")

    @property
    def num_of_cores(self):
        return self._get_field("numOfCores")

    @property
    def min_ground_datasets(self):
        return self._get_field("minGroundDatasets")

    @property
    def max_r_free(self):
        return self._get_field("maxRFree")

    @property
    def resolution_upper_limit(self):
        return self._get_field("resolutionUpperLimit")

    @property
    def resolution_lower_limit(self):
        return self._get_field("resolutionLowerLimit")

    @property
    def custom_parameters(self):
        return self._get_field("customParameters")


class KillJobForm(Form):
    job_ids = CharField(required=False)

    def clean_job_ids(self):
        return self.cleaned_data["job_ids"].split(",")

    def get_job_ids(self):
        return self.cleaned_data["job_ids"]


def _append_db_libs(project: Optional[Project], libs: Dict) -> Dict:
    for lib in Library.get_all(project):
        libs[lib.name] = lib.as_dict()

    return libs


class ProjectForm(Form):
    protein = CharField()
    proposal = CharField()
    crystals = FileField()
    autoproc = BooleanField(required=False)
    encrypted = BooleanField(required=False)

    def _clean_fraglibs(self):
        def _get_libs():
            for n in count():
                name = self.data.get(f"fragsName{n}")
                csv = self.files.get(f"fragsCSV{n}")
                if name is None:
                    break

                yield name, csv

        libs = {}

        for name, frags_csv in _get_libs():
            try:
                libs[name] = parse_fraglib_csv(frags_csv)
            except InvalidLibraryCSV as e:
                raise ValidationError(
                    f"fragments library '{name}' is invalid,\n{str(e)}"
                )

        self.cleaned_data["libraries"] = libs

    def _clean_crystals(self):
        libs = self.cleaned_data["libraries"].copy()
        _append_db_libs(None, libs)

        csv_file = self.cleaned_data["crystals"]
        try:
            crystals = parse_crystals_csv(libs, csv_file)
        except InvalidCrystalsCSV as e:
            raise ValidationError(f"Could not parse Crystals CSV.\n{e}")

        self.cleaned_data["crystals"] = crystals

    def get_error_message(self):
        assert len(self.errors) == 1
        return list(self.errors.values())[0][0]

    def clean(self):
        self._clean_fraglibs()
        self._clean_crystals()
        return self.cleaned_data

    def get_values(self):
        cdata = self.cleaned_data

        return (
            cdata["protein"],
            cdata["proposal"],
            cdata["crystals"],
            cdata["libraries"],
            cdata["autoproc"],
            cdata["encrypted"],
        )


class CrystalsImportForm(Form):
    def __init__(self, project: Project, data, files):
        super().__init__(data, files)
        self.project = project

    crystals_csv_file = FileField()

    def clean_crystals_csv_file(self):
        csv_file = self.cleaned_data["crystals_csv_file"]
        libs = _append_db_libs(self.project, {})

        try:
            return parse_crystals_csv(libs, csv_file)
        except InvalidCrystalsCSV as e:
            raise ValidationError(f"Could not parse Crystals CSV.\n{e}")

    def get_error_message(self):
        assert len(self.errors) == 1
        return list(self.errors.values())[0][0]

    def get_crystals(self) -> Crystals:
        return self.cleaned_data["crystals_csv_file"]


class LibraryImportForm(Form, _GetFieldMixin):
    name = CharField()
    fragmentsFile = FileField()

    def clean_fragmentsFile(self):
        csv_file = self.cleaned_data["fragmentsFile"]
        try:
            return parse_fraglib_csv(csv_file)
        except InvalidLibraryCSV as e:
            raise ValidationError(str(e))

    def get_error_message(self):
        csv_errors = self.errors.get("fragmentsFile")
        if csv_errors:
            return f"Could not parse Fragment Library CSV.\n{csv_errors[0]}"

        assert False, "unexpected form error"

    def get_library(self):
        return self._get_field("name"), self._get_field("fragmentsFile")
