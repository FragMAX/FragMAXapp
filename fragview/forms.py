from typing import Optional
from pathlib import Path
import json
import jsonschema
from itertools import count
from gemmi import UnitCell
import pony.orm
from django.forms import (
    Form,
    CharField,
    BooleanField,
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


class _JobsForm:
    def _validate_json(self, request_body: bytes):
        data = json.loads(request_body.decode())
        jsonschema.validate(data, self.SCHEMA)  # type: ignore

        return data

    @staticmethod
    def _validate_tools(tools):
        for tool in tools:
            yield get_tool_by_name(tool["id"]), tool.get("customParams", "")


class ProcessForm(_JobsForm):
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

    @staticmethod
    def _validate_datasets(project: Project, dataset_ids: list[str]):
        for dataset_id in dataset_ids:
            yield project.get_dataset(dataset_id)

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
    def _validate_cell_params(cell: Optional[dict]) -> Optional[UnitCell]:
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
    SCHEMA = {
        "type": "object",
        "required": ["datasets", "tools", "pdb"],
        "properties": {
            "datasets": {"type": "array", "minItems": 1, "items": {"type": "number"}},
            "pdb": {"type": "number"},
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
        },
    }

    @staticmethod
    def _validate_pdb(project: Project, pdb_id: int) -> Path:
        pdb = project.get_pdb(pdb_id)
        return project.get_pdb_file(pdb)

    @staticmethod
    def _validate_datasets(project: Project, dataset_ids: list[str]):
        for res_id in dataset_ids:
            yield project.get_process_result(res_id)

    def __init__(self, project: Project, request_body: bytes):
        data = self._validate_json(request_body)

        self.pdb_file = self._validate_pdb(project, data["pdb"])
        self.datasets = list(self._validate_datasets(project, data["datasets"]))
        self.tools = list(self._validate_tools(data["tools"]))


class LigfitForm(_JobsForm):
    SCHEMA = {
        "type": "object",
        "required": ["datasets", "tools", "restrains_tool"],
        "properties": {
            "datasets": {"type": "array", "minItems": 1, "items": {"type": "number"}},
            "tools": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                    },
                },
            },
            "restrains_tool": {"type": "string"},
        },
    }

    @staticmethod
    def _validate_datasets(project: Project, dataset_ids: list[str]):
        for res_id in dataset_ids:
            yield project.get_refine_result(res_id)

    def __init__(self, project: Project, request_body: bytes):
        data = self._validate_json(request_body)

        self.datasets = list(self._validate_datasets(project, data["datasets"]))
        self.tools = list(self._validate_tools(data["tools"]))
        self.restrains_tool = get_tool_by_name(data["restrains_tool"])


class PanddaForm(_JobsForm):
    SCHEMA = {
        "type": "object",
        "required": ["proc", "refine"],
        "properties": {
            "proc": {"type": "string"},
            "refine": {"type": "string"},
        },
    }

    def __init__(self, project: Project, request_body: bytes):
        data = self._validate_json(request_body)
        self.proc_tool = data["proc"]
        self.refine_tool = data["refine"]
        self.refine_results = self._refine_results(project)

    def _refine_results(self, project: Project):
        """
        get refine results produced with processing tool {self.proc_tool}
        and refine tool {self.refine_tool}
        """

        def result_match(refine_result):
            return (
                refine_result.result.result == "ok"
                and refine_result.result.tool == self.refine_tool
                and refine_result.result.input.tool == self.proc_tool
            )

        return pony.orm.select(r for r in project.db.RefineResult if result_match(r))


class KillJobForm(Form):
    job_ids = CharField(required=False)

    def clean_job_ids(self):
        return self.cleaned_data["job_ids"].split(",")

    def get_job_ids(self):
        return self.cleaned_data["job_ids"]


def _append_db_libs(project: Optional[Project], libs: dict) -> dict:
    for lib in Library.get_all(project):
        libs[lib.name] = lib.as_dict()

    return libs


class ProjectForm(Form):
    protein = CharField()
    proposal = CharField()
    crystals = FileField()
    autoproc = BooleanField(required=False)

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
