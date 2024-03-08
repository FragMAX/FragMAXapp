from typing import Optional
import os
import json
import zipstream
import jsonschema
from pathlib import Path
from django.http import (
    HttpRequest,
    JsonResponse,
    HttpResponseServerError,
    HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import render
from fragview.fileio import read_proj_file
from fragview.projects import Project, current_project
from fragview.views.utils import ToolsCombo
from fragview.tools import UnknownToolNameException

#
# partial schema for results.json,
# this schema only include the parts of json
# that we are actively reading
#
RESULTS_JSON_SCHEMA = {
    "type": "object",
    "required": ["events"],
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "dtag",
                    "event_num",
                    "event_fraction",
                    "bdc",
                    "z_peak",
                    "z_mean",
                    "cluster_size",
                    "map_uncertainty",
                ],
                "properties": {
                    "dtag": {"type": "string"},
                    "event_num": {"type": "number"},
                    "event_fraction": {"type": "number"},
                    "bdc": {"type": "number"},
                    "z_peak": {"type": "number"},
                    "z_mean": {"type": "number"},
                    "cluster_size": {"type": "number"},
                    "map_uncertainty": {"type": "number"},
                },
            },
        },
    },
}


class _EventsParseError(Exception):
    pass


def _pandda_result_json(pandda_run_dir: Path) -> Path:
    return Path(pandda_run_dir, "result", "results.json")


def _dir_to_tools_combo(res_dir: Path) -> Optional[ToolsCombo]:
    name = res_dir.name
    if "-" not in name:
        return None

    proc_tool, refine_tool = name.split("-")
    try:
        return ToolsCombo(proc_tool, refine_tool)
    except UnknownToolNameException:
        # this directory name is not a valid tools combination
        return None


def _get_result_combos(pandda_dir: Path):
    if not pandda_dir.is_dir():
        return

    for child in pandda_dir.iterdir():
        if not child.is_dir():
            # we only interested in directories
            continue

        # check if results.json is present
        if not _pandda_result_json(child).is_file():
            # no results.json file found, possibly a failed PanDDA run
            continue

        tools_combo = _dir_to_tools_combo(child)
        if tools_combo is not None:
            yield tools_combo


def results(request: HttpRequest):
    project = current_project(request)

    combos = sorted(
        _get_result_combos(project.pandda_dir), key=lambda k: k.ui_label.lower()
    )

    return render(
        request,
        "pandda_results.html",
        {
            "result_combos": combos,
        },
    )


def _load_events(results_json: Path):
    def parse_results_file():
        with open(results_json) as f:
            data = json.load(f)
            jsonschema.validate(data, RESULTS_JSON_SCHEMA)
            for event in data["events"]:
                # include only the value we'll show to the user
                yield dict(
                    dtag=event["dtag"],
                    event_num=event["event_num"],
                    event_fraction=event["event_fraction"],
                    bdc=event["bdc"],
                    z_peak=event["z_peak"],
                    z_mean=event["z_mean"],
                    cluster_size=event["cluster_size"],
                    map_uncertainty=event["map_uncertainty"],
                )

    try:
        return list(parse_results_file())
    except OSError as ex:
        raise _EventsParseError(f"Error reading data.\n{ex}")
    except json.JSONDecodeError:
        raise _EventsParseError(f"Error parsing {results_json}.\nJSON decode error.")
    except jsonschema.ValidationError as ex:
        raise _EventsParseError(f"Unexpected json schema in {results_json}.\n{ex}")


def _get_pandda_run_dir(project: Project, proc_tool: str, refine_tool: str) -> Path:
    return Path(project.pandda_dir, f"{proc_tool}-{refine_tool}")


def events(request: HttpRequest, proc: str, refine: str):
    project = current_project(request)

    results_json = _pandda_result_json(_get_pandda_run_dir(project, proc, refine))
    try:
        data = dict(events=_load_events(results_json))
        return JsonResponse(data)
    except _EventsParseError as ex:
        return HttpResponseServerError(f"{ex}")


def _dir_archive_entries(root_dir):
    def _file_data(file_path):
        yield read_proj_file(file_path)

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            abs_path = Path(dirpath, filename)
            arch_path = abs_path.relative_to(root_dir)

            yield arch_path, _file_data(abs_path)


def _zipstream_dir(arch_top_dir: str, source_dir):
    z = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED, allowZip64=True)

    for arch_path, data in _dir_archive_entries(source_dir):
        z.write_iter(Path(arch_top_dir, arch_path), data)

    return z


def download(request: HttpRequest, proc: str, refine: str):
    project = current_project(request)
    result_dir = Path(_get_pandda_run_dir(project, proc, refine), "result")

    if not result_dir.is_dir():
        return HttpResponseNotFound(f"no results found for {proc}-{refine} PanDDA run")

    run_name = f"{project.protein}-{proc}-{refine}"
    zip_name = f"{run_name}-PanDDa.zip"

    resp = StreamingHttpResponse(
        _zipstream_dir(run_name, result_dir), content_type="application/zip"
    )
    resp["Content-Disposition"] = f"attachment; filename={zip_name}"

    return resp
