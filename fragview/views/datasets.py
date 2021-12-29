from typing import Iterator
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview.projects import current_project
from fragview.projects import Project
from fragview.forms import ProcessForm, RefineForm
from fragview.views.wrap import DatasetInfo


def _get_dataset_info(project: Project) -> Iterator[DatasetInfo]:
    for dataset in project.get_datasets():
        yield DatasetInfo(dataset)


def show_all(request):
    project = current_project(request)

    return render(
        request,
        "datasets.html",
        {
            "datasets": _get_dataset_info(project),
        },
    )


def process(request):
    form = ProcessForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    print(f"{form.get_datasets()=}")
    print(f"{form.get_pipelines()=}")
    print(f"{form.get_space_group()=}")
    print(f"{form.get_cell_parameters()=}")

    from django.http import HttpResponse

    return HttpResponse("okiedokie")


def refine(request):
    form = RefineForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    print(f"{form.get_datasets()=}")
    print(f"{form.get_pipelines()=}")
    print(f"{form.get_ligfit_tools()=}")
    print(f"{form.get_constrains_tool()=}")

    from django.http import HttpResponse

    return HttpResponse("okiedokie")
