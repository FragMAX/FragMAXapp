from typing import Optional, List, Dict
import json
import jsonschema
from itertools import count
from gemmi import UnitCell
from django.forms import (
    Form,
    CharField,
    BooleanField,
    IntegerField,
    FloatField,
    FileField,
    ValidationError,
)
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


class ProcessForm:
    SCHEMA = {
        "type": "object",
        "required": ["datasets", "tools"],
        "properties": {
            "datasets": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "tools": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "customParams": {"type": "string"},
                    },
                },
            },
            "spaceGroup": {
                "type": "string",
            },
            "cellParams": {
                "type": "object",
                "required": ["a", "b", "c", "alpha", "beta", "gamma"],
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                    "c": {"type": "number"},
                    "alpha": {"type": "number"},
                    "beta": {"type": "number"},
                    "gammma": {"type": "number"},
                },
            },
        },
    }

    def _validate_json(self, request_body: bytes):
        data = json.loads(request_body.decode())
        jsonschema.validate(data, self.SCHEMA)

        return data

    @staticmethod
    def _validate_datasets(project: Project, dataset_ids: List[str]):
        for dataset_id in dataset_ids:
            yield project.get_dataset(dataset_id)

    @staticmethod
    def _validate_tools(tools):
        for tool in tools:
            yield get_tool_by_name(tool["id"]), tool.get("customParams", "")

    @staticmethod
    def _validate_space_group(space_group_name: Optional[str]) -> Optional[SpaceGroup]:
        if space_group_name is None:
            # no space group specified, aka 'auto' space group
            return None

        space_group = get_space_group(space_group_name)
        if space_group is None:
            raise ValidationError(
                f"unsupported space group '{space_group_name}' specified"
            )

        return space_group

    @staticmethod
    def _validate_cell_params(cell: Optional[Dict]) -> Optional[UnitCell]:
        if cell is None:
            # no cell parameters specified, aka 'auto' mode
            return None

        return UnitCell(
            cell["a"], cell["b"], cell["c"], cell["alpha"], cell["beta"], cell["gamma"]
        )

    def __init__(self, project: Project, request_body: bytes):
        data = self._validate_json(request_body)

        self.datasets = list(self._validate_datasets(project, data["datasets"]))
        self.tools = list(self._validate_tools(data["tools"]))
        self.space_group = self._validate_space_group(data.get("spaceGroup"))
        self.cell_params = self._validate_cell_params(data.get("cellParams"))


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
